"""Data migration: merge StaffMember data into User model.

For each StaffMember:
1. Match to existing User by first_name + last_name
2. Set is_rsa=True, is_in_rotation, rotation_position on matched User
3. Create placeholder User if no match found
4. Populate RosterDate.user from the mapping
"""

from django.contrib.auth.hashers import make_password
from django.db import migrations


def merge_forward(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    StaffMember = apps.get_model('roster', 'StaffMember')
    RosterDate = apps.get_model('roster', 'RosterDate')

    staff_to_user = {}

    for staff in StaffMember.objects.all():
        name_parts = staff.name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else staff.name
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Try to match by name
        user = User.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
        ).first()

        if user:
            user.is_rsa = True
            if staff.is_active:
                user.is_in_rotation = True
                user.rotation_position = staff.position
            else:
                user.is_in_rotation = False
            # Copy phone if User's phone is empty
            if not user.phone and staff.phone:
                user.phone = staff.phone
            user.save()
            staff_to_user[staff.id] = user
        else:
            # Create placeholder User for unmatched staff
            email = staff.name.lower().replace(' ', '.') + '@gtyc.local'
            new_user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=staff.phone,
                membership_type='none',
                is_committee=False,
                is_rsa=True,
                is_in_rotation=staff.is_active,
                rotation_position=staff.position if staff.is_active else None,
                is_active=False,
                password=make_password(None),
            )
            new_user.save()
            staff_to_user[staff.id] = new_user

    # Migrate RosterDate.staff_member -> RosterDate.user
    for rd in RosterDate.objects.all():
        if rd.staff_member_id in staff_to_user:
            rd.user = staff_to_user[rd.staff_member_id]
            rd.save()


def merge_backward(apps, schema_editor):
    # No reverse — this is a one-way migration
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('roster', '0002_add_user_fk_to_rosterdate'),
        ('accounts', '0004_migrate_role_data'),
    ]

    operations = [
        migrations.RunPython(merge_forward, merge_backward),
    ]
