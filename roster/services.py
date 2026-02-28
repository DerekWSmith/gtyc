"""
Roster rotation algorithm.

Every Friday has a stored RosterDate row in the database. The is_override
flag distinguishes auto-computed entries from manual admin overrides.

On staff changes (reorder/add/remove), regenerate_future_roster() deletes
future auto entries and recomputes them. Past entries are NEVER recalculated.

Manual overrides are preserved during regeneration. The underlying rotation
continues unchanged — an override just substitutes one person for one week.
"""

import datetime
from django.contrib.auth import get_user_model
from .models import RosterDate, RosterConfig


def get_fridays_in_range(start_date, end_date):
    """Generate all Fridays between start_date and end_date inclusive."""
    current = start_date
    # Advance to first Friday (weekday 4 = Friday)
    while current.weekday() != 4:
        current += datetime.timedelta(days=1)
    fridays = []
    while current <= end_date:
        fridays.append(current)
        current += datetime.timedelta(days=7)
    return fridays


def fridays_between(date_a, date_b):
    """Count the number of Fridays between two Friday dates (signed)."""
    delta = (date_b - date_a).days
    return delta // 7


def compute_rotation_for_date(config, active_staff, friday):
    """Compute which staff member is on duty for a given Friday.

    Returns the User object for the rotation slot, ignoring overrides.
    """
    staff_count = len(active_staff)
    if staff_count == 0 or not config:
        return None
    anchor_index = config.anchor_staff_position - 1
    weeks = fridays_between(config.anchor_date, friday)
    idx = (anchor_index + weeks) % staff_count
    return active_staff[idx]


def regenerate_future_roster():
    """Delete future auto entries and recompute from the anchor.

    Called after any staff change (reorder, add, remove).
    Past entries are never touched — only dates >= today are regenerated.
    """
    User = get_user_model()
    config = RosterConfig.load()
    if not config:
        return

    active_staff = list(
        User.objects.filter(is_in_rotation=True, is_active=True)
        .order_by('rotation_position')
    )
    if not active_staff:
        return

    today = datetime.date.today()
    end = today + datetime.timedelta(days=240)  # ~8 months

    # Delete future auto entries (preserve overrides)
    RosterDate.objects.filter(
        date__gte=today,
        source=RosterDate.Source.ROTATION,
        is_override=False,
    ).delete()

    # Get future dates that have manual overrides (skip these)
    overridden = set(
        RosterDate.objects.filter(
            date__gte=today,
            source=RosterDate.Source.ROTATION,
            is_override=True,
        ).values_list('date', flat=True)
    )

    # Compute and store new auto entries
    fridays = get_fridays_in_range(today, end)
    to_create = []
    for friday in fridays:
        if friday in overridden:
            continue
        person = compute_rotation_for_date(config, active_staff, friday)
        if person:
            to_create.append(RosterDate(
                date=friday,
                staff_member=person,
                source=RosterDate.Source.ROTATION,
                is_override=False,
            ))

    if to_create:
        RosterDate.objects.bulk_create(to_create)


def get_roster_for_range(start_date, end_date):
    """
    Get the full roster for a date range.

    Returns a list of dicts, sorted by date:
        {
            'date': date,
            'staff_members': [User, ...],
            'source': 'rotation' | 'event',
            'is_override': bool,
            'event': Event or None,
            'notes': str,
        }

    Uses stored RosterDate entries. Falls back to on-the-fly computation
    for any Friday without a stored entry (e.g., dates outside stored range).
    """
    User = get_user_model()
    active_staff = list(
        User.objects.filter(
            is_in_rotation=True,
            is_active=True,
        ).order_by('rotation_position')
    )

    config = RosterConfig.load()

    # Fetch all stored RosterDate records in range
    stored_dates = list(
        RosterDate.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
        ).select_related('staff_member', 'event')
    )

    # Index rotation entries by date (override takes priority over auto)
    rotation_by_date = {}
    event_entries = []
    for rd in stored_dates:
        if rd.source == RosterDate.Source.ROTATION:
            # Override wins if both exist for same date
            if rd.is_override or rd.date not in rotation_by_date:
                rotation_by_date[rd.date] = rd
        elif rd.source == RosterDate.Source.EVENT:
            event_entries.append(rd)

    entries = []

    # 1. Friday rotation — use stored entries, fallback to on-the-fly
    fridays = get_fridays_in_range(start_date, end_date)
    for friday in fridays:
        if friday in rotation_by_date:
            rd = rotation_by_date[friday]
            entries.append({
                'date': friday,
                'staff_members': [rd.staff_member],
                'source': 'rotation',
                'is_override': rd.is_override,
                'event': None,
                'notes': rd.notes,
            })
        else:
            # Fallback: compute on-the-fly for dates outside stored range
            person = compute_rotation_for_date(config, active_staff, friday)
            if person:
                entries.append({
                    'date': friday,
                    'staff_members': [person],
                    'source': 'rotation',
                    'is_override': False,
                    'event': None,
                    'notes': '',
                })

    # 2. Event assignments — group by (date, event) so multiple staff
    #    appear on a single row instead of duplicate date lines.
    from collections import OrderedDict
    event_groups = OrderedDict()
    for rd in event_entries:
        key = (rd.date, rd.event_id)
        if key not in event_groups:
            event_groups[key] = {
                'date': rd.date,
                'staff_members': [],
                'source': 'event',
                'is_override': False,
                'event': rd.event,
                'notes': rd.notes,
            }
        event_groups[key]['staff_members'].append(rd.staff_member)

    for group in event_groups.values():
        entries.append(group)

    # Sort by date, then source (rotation before event on same date)
    entries.sort(key=lambda e: (e['date'], 0 if e['source'] == 'rotation' else 1))

    return entries
