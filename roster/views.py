import json
import datetime

from django.contrib.auth import get_user_model
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST, require_GET

from accounts.decorators import admin_required
from .models import RosterDate, RosterConfig
from .services import (
    get_roster_for_range, regenerate_future_roster,
    compute_rotation_for_date, fridays_between,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

def public_roster(request):
    """Public read-only roster — dates + names only, no phone numbers."""
    today = datetime.date.today()
    # Show from 2 weeks ago to 3 months ahead
    start = today - datetime.timedelta(days=14)
    end = today + datetime.timedelta(days=90)

    entries = get_roster_for_range(start, end)

    # Next Friday (today if Friday, otherwise the coming Friday)
    days_until_friday = (4 - today.weekday()) % 7
    next_friday = today + datetime.timedelta(days=days_until_friday)

    return render(request, 'roster/public.html', {
        'entries': entries,
        'today': today,
        'next_friday': next_friday,
    })


# ---------------------------------------------------------------------------
# Admin page
# ---------------------------------------------------------------------------

@admin_required
def admin_page(request):
    """Admin roster management page."""
    staff = User.objects.filter(
        is_in_rotation=True, is_active=True,
    ).order_by('rotation_position')
    rsa_users = User.objects.filter(
        is_rsa=True, is_active=True,
    ).order_by('last_name', 'first_name')
    config = RosterConfig.load()

    return render(request, 'roster/admin.html', {
        'staff_list': list(staff),
        'rsa_users': list(rsa_users),
        'config': config,
    })


# ---------------------------------------------------------------------------
# Admin API — Staff CRUD
# ---------------------------------------------------------------------------

@admin_required
@require_GET
def api_staff_list(request):
    """Return list of active rotation staff as JSON."""
    staff = User.objects.filter(
        is_in_rotation=True, is_active=True,
    ).order_by('rotation_position')
    data = [
        {
            'id': s.id,
            'name': s.display_name,
            'phone': s.phone,
            'position': s.rotation_position,
        }
        for s in staff
    ]
    return JsonResponse({'staff': data})


@admin_required
@require_POST
def api_staff_add(request):
    """Add a user to the rotation.

    Body: {"user_id": int} to add existing RSA user,
    or {"name": str, "phone": str} to create a new contact and add.
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_id = body.get('user_id')
    if user_id:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
    else:
        name = body.get('name', '').strip()
        phone = body.get('phone', '').strip()
        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)

        parts = name.split(' ', 1)
        email = name.lower().replace(' ', '.') + '@gtyc.local'
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': parts[0],
                'last_name': parts[1] if len(parts) > 1 else '',
                'phone': phone,
                'membership_type': 'none',
                'is_active': True,
            },
        )
        if not created and phone:
            user.phone = phone
            user.save()

    # Set rotation fields
    max_pos = User.objects.filter(
        is_in_rotation=True,
    ).aggregate(m=Max('rotation_position'))['m'] or 0
    user.is_rsa = True
    user.is_in_rotation = True
    user.rotation_position = max_pos + 1
    user.save()

    # Regenerate future roster (adding at end doesn't change anchor)
    regenerate_future_roster()

    return JsonResponse({
        'success': True,
        'staff': {
            'id': user.id,
            'name': user.display_name,
            'phone': user.phone,
            'position': user.rotation_position,
        },
    })


@admin_required
@require_POST
def api_staff_update(request, staff_id):
    """Update a rotation staff member's name and/or phone."""
    try:
        user = User.objects.get(pk=staff_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Staff member not found'}, status=404)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if 'name' in body:
        parts = body['name'].strip().split(' ', 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ''
    if 'phone' in body:
        user.phone = body['phone'].strip()
    user.save()

    return JsonResponse({'success': True})


@admin_required
@require_POST
def api_staff_delete(request, staff_id):
    """Remove a user from rotation (soft remove, not delete)."""
    try:
        user = User.objects.get(pk=staff_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Staff member not found'}, status=404)

    # BEFORE removal: compute who should be on the next future Friday
    config = RosterConfig.load()
    old_staff = list(
        User.objects.filter(is_in_rotation=True, is_active=True)
        .order_by('rotation_position')
    )
    old_count = len(old_staff)

    today = datetime.date.today()
    days_until_friday = (4 - today.weekday()) % 7
    next_fri = today + datetime.timedelta(days=days_until_friday)

    # Who's on next Friday in the current rotation?
    next_fri_person = compute_rotation_for_date(config, old_staff, next_fri)

    # If that person is being removed, take the next person in rotation
    if next_fri_person and next_fri_person.id == user.id and old_count > 1:
        anchor_index = config.anchor_staff_position - 1
        weeks = fridays_between(config.anchor_date, next_fri)
        old_idx = (anchor_index + weeks) % old_count
        fallback_idx = (old_idx + 1) % old_count
        next_fri_person = old_staff[fallback_idx]

    # Remove from rotation
    user.is_in_rotation = False
    user.rotation_position = None
    user.save()

    # Recompact positions
    remaining = User.objects.filter(
        is_in_rotation=True, is_active=True,
    ).order_by('rotation_position')
    for i, s in enumerate(remaining, start=1):
        if s.rotation_position != i:
            s.rotation_position = i
            s.save()

    # Re-anchor: set anchor so next_fri_person stays on next_fri
    if config and next_fri_person and next_fri_person.is_in_rotation:
        next_fri_person.refresh_from_db()
        config.anchor_date = next_fri
        config.anchor_staff_position = next_fri_person.rotation_position
        config.save()

    # Regenerate future roster entries
    regenerate_future_roster()

    return JsonResponse({'success': True})


@admin_required
@require_POST
def api_staff_reorder(request):
    """Reorder rotation staff. Body: {"order": [id1, id2, id3, ...]}

    Does NOT re-anchor. The existing anchor + new positions means only
    the swapped people's future dates change — everyone else is unaffected.
    Past dates are stored and never recalculated.
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    order = body.get('order', [])
    if not order:
        return JsonResponse({'error': 'Order list is required'}, status=400)

    for i, user_id in enumerate(order, start=1):
        User.objects.filter(pk=user_id).update(rotation_position=i)

    # Regenerate future only — past is frozen, anchor unchanged
    regenerate_future_roster()

    return JsonResponse({'success': True})


# ---------------------------------------------------------------------------
# Admin API — Roster dates
# ---------------------------------------------------------------------------

@admin_required
@require_GET
def api_dates(request):
    """Return roster entries for a date range.
    Query params: start (YYYY-MM-DD), end (YYYY-MM-DD)
    """
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    try:
        start = datetime.date.fromisoformat(start_str)
        end = datetime.date.fromisoformat(end_str)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

    entries = get_roster_for_range(start, end)

    data = []
    for e in entries:
        staff_list = e['staff_members']
        entry = {
            'date': e['date'].isoformat(),
            'date_display': e['date'].strftime('%d/%m/%Y'),
            'day_name': e['date'].strftime('%A'),
            'staff_name': ', '.join(s.display_name for s in staff_list),
            'staff_id': staff_list[0].id if staff_list else None,
            'staff_phone': staff_list[0].phone if staff_list else '',
            'staff_members': [
                {'id': s.id, 'name': s.display_name, 'phone': s.phone}
                for s in staff_list
            ],
            'source': e['source'],
            'is_override': e['is_override'],
            'event_title': e['event'].title if e['event'] else None,
            'notes': e['notes'],
            'is_past': e['date'] < datetime.date.today(),
        }
        data.append(entry)

    return JsonResponse({'entries': data})


@admin_required
@require_POST
def api_override(request, date_str):
    """Set a manual override for a Friday.
    Body: {"staff_id": int}

    Deletes any existing rotation entry for this date (auto or override)
    and creates a new override entry.
    """
    try:
        target_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    if target_date < datetime.date.today():
        return JsonResponse({'error': 'Cannot override past dates'}, status=400)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    staff_id = body.get('staff_id')
    if not staff_id:
        return JsonResponse({'error': 'staff_id is required'}, status=400)

    try:
        user = User.objects.get(pk=staff_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Staff member not found'}, status=404)

    # Replace any existing rotation entry with a manual override
    RosterDate.objects.filter(
        date=target_date,
        source=RosterDate.Source.ROTATION,
    ).delete()

    RosterDate.objects.create(
        date=target_date,
        source=RosterDate.Source.ROTATION,
        staff_member=user,
        is_override=True,
        notes=body.get('notes', ''),
    )

    return JsonResponse({'success': True})


@admin_required
@require_POST
def api_clear_override(request, date_str):
    """Remove a manual override for a Friday, reverting to auto rotation."""
    try:
        target_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    if target_date < datetime.date.today():
        return JsonResponse({'error': 'Cannot modify past dates'}, status=400)

    # Delete the override
    deleted, _ = RosterDate.objects.filter(
        date=target_date,
        source=RosterDate.Source.ROTATION,
        is_override=True,
    ).delete()

    if deleted:
        # Compute and create the correct auto entry for this date
        config = RosterConfig.load()
        active_staff = list(
            User.objects.filter(is_in_rotation=True, is_active=True)
            .order_by('rotation_position')
        )
        person = compute_rotation_for_date(config, active_staff, target_date)
        if person:
            RosterDate.objects.create(
                date=target_date,
                source=RosterDate.Source.ROTATION,
                staff_member=person,
                is_override=False,
            )

    return JsonResponse({'success': True, 'deleted': deleted > 0})


# ---------------------------------------------------------------------------
# Print view
# ---------------------------------------------------------------------------

@admin_required
@xframe_options_sameorigin
def print_view(request):
    """Printable A4 roster — 8 months from today."""
    today = datetime.date.today()
    end = today + datetime.timedelta(days=240)
    entries = get_roster_for_range(today, end)

    return render(request, 'roster/print.html', {
        'entries': entries,
        'today': today,
    })


