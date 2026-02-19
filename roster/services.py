"""
Roster rotation algorithm.

The rotation is computed on-the-fly from an anchor point. Only manual
overrides and event assignments are stored in the database.

KEY BEHAVIOUR: Manual overrides REPLACE the rostered person for that
week only. The rotation continues unchanged — nobody's turn is
shifted or lost, the override just substitutes one person for one week.

Example with staff A→B→C→D:
  Wk1=A (rotation), override Wk2=X → Wk3=C, Wk4=D, Wk5=A, Wk6=B...
  (B's rotation slot was overridden by X, but C follows B as normal)
"""

import datetime
from .models import StaffMember, RosterDate, RosterConfig


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


def get_roster_for_range(start_date, end_date):
    """
    Compute the full roster for a date range.

    Returns a list of dicts, sorted by date:
        {
            'date': date,
            'staff_members': [StaffMember, ...],
            'source': 'rotation' | 'event',
            'is_override': bool,
            'event': Event or None,
            'notes': str,
        }

    Rotation entries always have exactly one staff member.
    Event entries may have multiple (grouped by date + event).

    The list merges:
    1. Friday rotation assignments (with override handling)
    2. Special event bar staff assignments (grouped by event)
    """
    active_staff = list(
        StaffMember.objects.filter(is_active=True).order_by('position')
    )
    staff_count = len(active_staff)

    config = RosterConfig.load()

    # Fetch all stored RosterDate records in range
    stored_dates = list(
        RosterDate.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
        ).select_related('staff_member', 'event')
    )

    # Index overrides by date for quick lookup
    overrides_by_date = {}
    event_entries = []
    for rd in stored_dates:
        if rd.source == RosterDate.Source.ROTATION:
            overrides_by_date[rd.date] = rd
        elif rd.source == RosterDate.Source.EVENT:
            event_entries.append(rd)

    entries = []

    # 1. Friday rotation — walk forward, respecting overrides
    if staff_count > 0 and config:
        fridays = get_fridays_in_range(start_date, end_date)

        # Since overrides don't shift the rotation, we can calculate the
        # rotation index for any Friday directly from the anchor — no need
        # to walk from the anchor counting overrides.
        anchor_index = config.anchor_staff_position - 1  # 0-based

        for friday in fridays:
            if friday in overrides_by_date:
                # Override — substitute this week only, rotation unaffected
                rd = overrides_by_date[friday]
                entries.append({
                    'date': friday,
                    'staff_members': [rd.staff_member],
                    'source': 'rotation',
                    'is_override': True,
                    'event': None,
                    'notes': rd.notes,
                })
            else:
                # Normal rotation — compute index directly from anchor
                weeks_from_anchor = fridays_between(config.anchor_date, friday)
                rotation_index = (anchor_index + weeks_from_anchor) % staff_count
                entries.append({
                    'date': friday,
                    'staff_members': [active_staff[rotation_index]],
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
