"""Add is_override field and populate stored rotation entries.

1. Add is_override BooleanField to RosterDate
2. Mark existing rotation entries as overrides (is_override=True)
3. Populate auto entries for all Fridays from anchor to today + 8 months
"""

import datetime
from django.db import migrations, models

from roster.services import get_fridays_in_range, fridays_between


def populate_auto_entries(apps, schema_editor):
    RosterDate = apps.get_model('roster', 'RosterDate')
    RosterConfig = apps.get_model('roster', 'RosterConfig')
    User = apps.get_model('accounts', 'User')

    # Mark existing rotation entries as manual overrides
    RosterDate.objects.filter(source='rotation').update(is_override=True)

    config = RosterConfig.objects.filter(pk=1).first()
    if not config:
        return

    active_staff = list(
        User.objects.filter(is_in_rotation=True, is_active=True)
        .order_by('rotation_position')
    )
    if not active_staff:
        return

    staff_count = len(active_staff)
    anchor_index = config.anchor_staff_position - 1

    today = datetime.date.today()
    end = today + datetime.timedelta(days=240)  # ~8 months

    # Get dates that already have rotation entries (overrides)
    overridden = set(
        RosterDate.objects.filter(source='rotation')
        .values_list('date', flat=True)
    )

    # Compute all Fridays from anchor to end
    fridays = get_fridays_in_range(config.anchor_date, end)

    to_create = []
    for friday in fridays:
        if friday in overridden:
            continue
        weeks = fridays_between(config.anchor_date, friday)
        idx = (anchor_index + weeks) % staff_count
        to_create.append(RosterDate(
            date=friday,
            staff_member=active_staff[idx],
            source='rotation',
            is_override=False,
        ))

    if to_create:
        RosterDate.objects.bulk_create(to_create)


def reverse_populate(apps, schema_editor):
    RosterDate = apps.get_model('roster', 'RosterDate')
    # Remove auto-computed entries
    RosterDate.objects.filter(source='rotation', is_override=False).delete()
    # Revert overrides back to normal
    RosterDate.objects.filter(source='rotation', is_override=True).update(is_override=False)


class Migration(migrations.Migration):

    dependencies = [
        ('roster', '0004_finalize_staff_to_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='rosterdate',
            name='is_override',
            field=models.BooleanField(
                default=False,
                help_text='True for manual admin overrides, False for auto-computed',
            ),
        ),
        migrations.RunPython(populate_auto_entries, reverse_populate),
    ]
