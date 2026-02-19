import json
import datetime

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST, require_GET

from accounts.decorators import admin_required
from .models import StaffMember, RosterDate, RosterConfig
from .services import get_roster_for_range


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

def public_roster(request):
    """Public read-only roster — dates + names only, no phone numbers."""
    today = datetime.date.today()
    # Show from start of current month to 3 months ahead
    start = today.replace(day=1)
    end = today + datetime.timedelta(days=90)

    entries = get_roster_for_range(start, end)

    return render(request, 'roster/public.html', {
        'entries': entries,
        'today': today,
    })


# ---------------------------------------------------------------------------
# Admin page
# ---------------------------------------------------------------------------

@admin_required
def admin_page(request):
    """Admin roster management page."""
    staff = StaffMember.objects.filter(is_active=True).order_by('position')
    all_staff = StaffMember.objects.all().order_by('position')
    config = RosterConfig.load()

    return render(request, 'roster/admin.html', {
        'staff_list': list(staff),
        'all_staff': list(all_staff),
        'config': config,
    })


# ---------------------------------------------------------------------------
# Admin API — Staff CRUD
# ---------------------------------------------------------------------------

@admin_required
@require_GET
def api_staff_list(request):
    """Return list of active staff as JSON."""
    staff = StaffMember.objects.filter(is_active=True).order_by('position')
    data = [
        {'id': s.id, 'name': s.name, 'phone': s.phone, 'position': s.position}
        for s in staff
    ]
    return JsonResponse({'staff': data})


@admin_required
@require_POST
def api_staff_add(request):
    """Add a new staff member at the end of the rotation."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name = body.get('name', '').strip()
    phone = body.get('phone', '').strip()
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)

    # Put at end of rotation
    max_pos = StaffMember.objects.filter(is_active=True).order_by('-position').values_list('position', flat=True).first() or 0
    staff = StaffMember.objects.create(
        name=name,
        phone=phone,
        position=max_pos + 1,
    )

    return JsonResponse({
        'success': True,
        'staff': {'id': staff.id, 'name': staff.name, 'phone': staff.phone, 'position': staff.position},
    })


@admin_required
@require_POST
def api_staff_update(request, staff_id):
    """Update a staff member's name and/or phone."""
    try:
        staff = StaffMember.objects.get(pk=staff_id)
    except StaffMember.DoesNotExist:
        return JsonResponse({'error': 'Staff member not found'}, status=404)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if 'name' in body:
        staff.name = body['name'].strip()
    if 'phone' in body:
        staff.phone = body['phone'].strip()
    staff.save()

    return JsonResponse({'success': True})


@admin_required
@require_POST
def api_staff_delete(request, staff_id):
    """Deactivate a staff member (soft delete)."""
    try:
        staff = StaffMember.objects.get(pk=staff_id)
    except StaffMember.DoesNotExist:
        return JsonResponse({'error': 'Staff member not found'}, status=404)

    staff.is_active = False
    staff.save()

    # Re-anchor if needed to preserve rotation continuity
    _re_anchor_after_staff_change()

    return JsonResponse({'success': True})


@admin_required
@require_POST
def api_staff_reorder(request):
    """Reorder staff members. Body: {"order": [id1, id2, id3, ...]}"""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    order = body.get('order', [])
    if not order:
        return JsonResponse({'error': 'Order list is required'}, status=400)

    for i, staff_id in enumerate(order, start=1):
        StaffMember.objects.filter(pk=staff_id).update(position=i)

    # Re-anchor to preserve rotation
    _re_anchor_after_staff_change()

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
            'staff_name': ', '.join(s.name for s in staff_list),
            'staff_id': staff_list[0].id if staff_list else None,
            'staff_phone': staff_list[0].phone if staff_list else '',
            'staff_members': [{'id': s.id, 'name': s.name, 'phone': s.phone} for s in staff_list],
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
    Body: {"staff_id": int} or {"staff_name": str} for ad-hoc.
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
        staff = StaffMember.objects.get(pk=staff_id)
    except StaffMember.DoesNotExist:
        return JsonResponse({'error': 'Staff member not found'}, status=404)

    # Create or update override
    rd, created = RosterDate.objects.update_or_create(
        date=target_date,
        source=RosterDate.Source.ROTATION,
        defaults={'staff_member': staff, 'notes': body.get('notes', '')},
    )

    return JsonResponse({'success': True, 'created': created})


@admin_required
@require_POST
def api_clear_override(request, date_str):
    """Remove a manual override for a Friday, reverting to rotation."""
    try:
        target_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    if target_date < datetime.date.today():
        return JsonResponse({'error': 'Cannot modify past dates'}, status=400)

    deleted, _ = RosterDate.objects.filter(
        date=target_date,
        source=RosterDate.Source.ROTATION,
    ).delete()

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _re_anchor_after_staff_change():
    """Re-anchor the rotation after staff list changes.

    Sets the anchor to today (or the most recent Friday) so that
    past assignments are preserved and the future recalculates
    with the new staff list.
    """
    config = RosterConfig.load()
    if not config:
        return

    active_staff = list(
        StaffMember.objects.filter(is_active=True).order_by('position')
    )
    if not active_staff:
        return

    # Find the most recent Friday (including today if it's Friday)
    today = datetime.date.today()
    days_since_friday = (today.weekday() - 4) % 7
    most_recent_friday = today - datetime.timedelta(days=days_since_friday)

    # The person who would currently be on duty (before the change)
    # should remain anchored. Set anchor_staff_position=1 and anchor
    # to the most recent Friday — this means position 1 in the active
    # list starts there.
    config.anchor_date = most_recent_friday
    config.anchor_staff_position = 1
    config.save()
