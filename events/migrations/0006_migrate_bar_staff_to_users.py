"""Data migration: copy Event.bar_staff M2M from StaffMember to User.

Uses same name-matching logic as roster migration 0003.
"""

from django.db import migrations


def migrate_forward(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    StaffMember = apps.get_model('roster', 'StaffMember')
    Event = apps.get_model('events', 'Event')

    # Build StaffMember -> User mapping
    staff_to_user = {}
    for staff in StaffMember.objects.all():
        name_parts = staff.name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else staff.name
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        user = User.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
        ).first()

        if not user:
            # Try placeholder email
            email = staff.name.lower().replace(' ', '.') + '@gtyc.local'
            user = User.objects.filter(email=email).first()

        if user:
            staff_to_user[staff.id] = user

    # Copy M2M data
    for event in Event.objects.prefetch_related('bar_staff').all():
        for staff in event.bar_staff.all():
            if staff.id in staff_to_user:
                event.bar_staff_users.add(staff_to_user[staff.id])


def migrate_backward(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0005_add_bar_staff_users_m2m'),
        ('roster', '0003_merge_staff_into_users'),
        ('accounts', '0004_migrate_role_data'),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrate_backward),
    ]
