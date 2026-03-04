import json
import datetime

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import localtime
from django.views.decorators.http import require_POST, require_GET

from accounts.decorators import admin_required, event_officer_required
from roster.models import RosterDate
from .models import Event, EventCategory

User = get_user_model()


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

def public_events(request):
    """Public read-only events list — title + date/time only."""
    now = timezone.now()
    events = Event.objects.filter(
        start_datetime__gte=now,
    ).select_related('category').order_by('start_datetime')

    return render(request, 'events/public.html', {
        'events': events,
    })


# ---------------------------------------------------------------------------
# Admin page
# ---------------------------------------------------------------------------

@admin_required
def admin_page(request):
    """Admin events management page."""
    staff = User.objects.filter(is_rsa=True, is_active=True).order_by(
        'last_name', 'first_name',
    )
    categories = EventCategory.objects.filter(is_active=True)

    # Pre-load upcoming events for initial render (avoid loading flash)
    now = timezone.now()
    upcoming = Event.objects.filter(
        start_datetime__gte=now,
    ).select_related('category').prefetch_related('bar_staff').order_by('start_datetime')

    # Event dates for calendar dot indicators (12 months back + 12 months ahead)
    start_window = now - datetime.timedelta(days=365)
    end_window = now + datetime.timedelta(days=365)
    event_dates = list(
        Event.objects.filter(
            start_datetime__gte=start_window,
            start_datetime__lte=end_window,
        ).values_list('start_datetime', flat=True)
    )
    # Convert to date strings for JS
    event_date_strings = list(set(
        localtime(dt).strftime('%Y-%m-%d') for dt in event_dates
    ))

    return render(request, 'events/admin.html', {
        'staff_list': list(staff),
        'categories': categories,
        'events': upcoming,
        'event_date_strings_json': json.dumps(event_date_strings),
        'user': request.user,
    })


# ---------------------------------------------------------------------------
# Admin API — Event CRUD
# ---------------------------------------------------------------------------

@admin_required
@require_GET
def api_event_list(request):
    """Return events as JSON. Optional filter: ?filter=upcoming|needs_approval"""
    filter_type = request.GET.get('filter', 'upcoming')
    now = timezone.now()

    qs = Event.objects.all().select_related('category').order_by('start_datetime')

    # Allow caller to specify a start date (from calendar selection)
    from_date_str = request.GET.get('from_date')
    if from_date_str:
        try:
            from_dt = datetime.datetime.fromisoformat(from_date_str)
            if timezone.is_naive(from_dt):
                from_dt = timezone.make_aware(from_dt)
        except ValueError:
            from_dt = now
    else:
        from_dt = now

    if filter_type == 'upcoming':
        qs = qs.filter(start_datetime__gte=from_dt)
    elif filter_type == 'needs_approval':
        qs = qs.filter(
            is_approved=False,
            category__requires_approval=True,
            start_datetime__gte=from_dt,
        )

    events = []
    for e in qs.prefetch_related('bar_staff'):
        events.append({
            'id': e.id,
            'title': e.title,
            'category_id': e.category_id,
            'category_name': e.category_name,
            'is_approved': e.is_approved,
            'is_tentative': e.is_tentative,
            'requires_approval': e.requires_approval,
            'start_datetime': e.start_datetime.isoformat(),
            'end_datetime': e.end_datetime.isoformat(),
            'start_display': localtime(e.start_datetime).strftime('%d/%m/%Y %H:%M'),
            'end_display': localtime(e.end_datetime).strftime('%H:%M'),
            'contact_name': e.contact_name,
            'contact_phone': e.contact_phone,
            'bar_staff': [{'id': s.id, 'name': s.display_name} for s in e.bar_staff.all()],
            'notes': e.notes,
            'created_by': e.created_by.display_name if e.created_by else '',
        })

    return JsonResponse({'events': events})


@admin_required
@require_GET
def api_event_detail(request, event_id):
    """Return single event detail as JSON."""
    try:
        e = Event.objects.select_related('category').prefetch_related('bar_staff').get(pk=event_id)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)

    data = {
        'id': e.id,
        'title': e.title,
        'category_id': e.category_id,
        'is_approved': e.is_approved,
        'requires_approval': e.requires_approval,
        'start_datetime': localtime(e.start_datetime).strftime('%Y-%m-%dT%H:%M'),
        'end_datetime': localtime(e.end_datetime).strftime('%Y-%m-%dT%H:%M'),
        'contact_name': e.contact_name,
        'contact_phone': e.contact_phone,
        'bar_staff_ids': [s.id for s in e.bar_staff.all()],
        'notes': e.notes,
    }

    return JsonResponse({'event': data})


@admin_required
@require_POST
def api_event_create(request):
    """Create a new event."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    title = body.get('title', '').strip()
    if not title:
        return JsonResponse({'error': 'Title is required'}, status=400)

    try:
        start = datetime.datetime.fromisoformat(body['start_datetime'])
        end = datetime.datetime.fromisoformat(body['end_datetime'])
    except (KeyError, ValueError):
        return JsonResponse({'error': 'Invalid date/time format'}, status=400)

    if timezone.is_naive(start):
        start = timezone.make_aware(start)
    if timezone.is_naive(end):
        end = timezone.make_aware(end)

    # Resolve category
    category = None
    category_id = body.get('category_id')
    if category_id:
        try:
            category = EventCategory.objects.get(pk=category_id)
        except EventCategory.DoesNotExist:
            pass

    event = Event(
        title=title,
        category=category,
        start_datetime=start,
        end_datetime=end,
        contact_name=body.get('contact_name', ''),
        contact_phone=body.get('contact_phone', ''),
        notes=body.get('notes', ''),
        created_by=request.user,
    )
    event.save()  # save() sets is_approved based on category

    # Assign bar staff (from RSA users)
    staff_ids = body.get('bar_staff_ids', [])
    if staff_ids:
        event.bar_staff.set(User.objects.filter(pk__in=staff_ids[:4], is_rsa=True))
        _sync_event_roster_dates(event)

    return JsonResponse({'success': True, 'id': event.id})


@admin_required
@require_POST
def api_event_update(request, event_id):
    """Update an existing event."""
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if 'title' in body:
        event.title = body['title'].strip()
    if 'category_id' in body:
        cat_id = body['category_id']
        if cat_id:
            try:
                event.category = EventCategory.objects.get(pk=cat_id)
            except EventCategory.DoesNotExist:
                event.category = None
        else:
            event.category = None
    if 'start_datetime' in body:
        start = datetime.datetime.fromisoformat(body['start_datetime'])
        event.start_datetime = timezone.make_aware(start) if timezone.is_naive(start) else start
    if 'end_datetime' in body:
        end = datetime.datetime.fromisoformat(body['end_datetime'])
        event.end_datetime = timezone.make_aware(end) if timezone.is_naive(end) else end
    if 'contact_name' in body:
        event.contact_name = body['contact_name']
    if 'contact_phone' in body:
        event.contact_phone = body['contact_phone']
    if 'notes' in body:
        event.notes = body['notes']

    event.save()

    if 'bar_staff_ids' in body:
        event.bar_staff.set(User.objects.filter(pk__in=body['bar_staff_ids'][:4], is_rsa=True))
        _sync_event_roster_dates(event)

    return JsonResponse({'success': True})


@event_officer_required
@require_POST
def api_event_delete(request, event_id):
    """Delete an event (Event Officer only)."""
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)

    event.delete()  # Cascade deletes RosterDate records too
    return JsonResponse({'success': True})


@event_officer_required
@require_POST
def api_event_approve(request, event_id):
    """Toggle approval flag (Event Officer only)."""
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)

    event.is_approved = not event.is_approved
    event.save()

    return JsonResponse({'success': True, 'is_approved': event.is_approved})


# ---------------------------------------------------------------------------
# Admin API — Event Categories CRUD
# ---------------------------------------------------------------------------

@admin_required
@require_GET
def api_category_list(request):
    """Return all event categories as JSON."""
    cats = EventCategory.objects.filter(is_active=True)
    data = [
        {
            'id': c.id,
            'name': c.name,
            'requires_approval': c.requires_approval,
            'position': c.position,
        }
        for c in cats
    ]
    return JsonResponse({'categories': data})


@admin_required
@require_POST
def api_category_create(request):
    """Create a new event category."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name = body.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)

    if EventCategory.objects.filter(name__iexact=name, is_active=True).exists():
        return JsonResponse({'error': 'A category with this name already exists'}, status=400)

    # Put at end
    max_pos = EventCategory.objects.filter(is_active=True).order_by('-position').values_list('position', flat=True).first() or 0
    cat = EventCategory.objects.create(
        name=name,
        requires_approval=body.get('requires_approval', False),
        position=max_pos + 1,
    )

    return JsonResponse({
        'success': True,
        'category': {'id': cat.id, 'name': cat.name, 'requires_approval': cat.requires_approval, 'position': cat.position},
    })


@admin_required
@require_POST
def api_category_update(request, category_id):
    """Update an event category."""
    try:
        cat = EventCategory.objects.get(pk=category_id)
    except EventCategory.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if 'name' in body:
        name = body['name'].strip()
        if name and EventCategory.objects.filter(name__iexact=name, is_active=True).exclude(pk=category_id).exists():
            return JsonResponse({'error': 'A category with this name already exists'}, status=400)
        cat.name = name
    if 'requires_approval' in body:
        was_required = cat.requires_approval
        cat.requires_approval = body['requires_approval']

        # When switching a category TO requires_approval, mark all upcoming
        # events in this category as unapproved so they enter the approval queue.
        if cat.requires_approval and not was_required:
            from django.utils import timezone as tz
            Event.objects.filter(
                category=cat,
                start_datetime__gte=tz.now(),
            ).update(is_approved=False)

    cat.save()
    return JsonResponse({'success': True})


@admin_required
@require_POST
def api_category_delete(request, category_id):
    """Soft-delete a category. FK references stay intact so existing events keep their type name."""
    try:
        cat = EventCategory.objects.get(pk=category_id)
    except EventCategory.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)

    # Soft delete — events keep their FK reference, category name still displays
    cat.is_active = False
    cat.save()

    return JsonResponse({'success': True})


# ---------------------------------------------------------------------------
# Roster integration
# ---------------------------------------------------------------------------

def _sync_event_roster_dates(event):
    """Sync RosterDate records for an event's bar staff assignments."""
    event_date = event.start_datetime.date()

    # Remove old assignments for this event
    RosterDate.objects.filter(event=event).delete()

    # Create new ones — bar_staff now contains User objects
    for user in event.bar_staff.all():
        RosterDate.objects.create(
            date=event_date,
            staff_member=user,
            source=RosterDate.Source.EVENT,
            event=event,
            notes=event.title,
        )
