"""Data migration: populate new role fields from old fields.

Maps:
- role='committee' → is_committee=True, membership_type='full'
- is_event_officer=True → admin_level='event_officer'
- can_admin_club=True (only) → admin_level='secretary'
"""

from django.db import migrations


def migrate_forward(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        # Membership
        if user.role == 'committee':
            user.is_committee = True
            user.membership_type = 'full'
        else:
            user.membership_type = 'full'

        # Admin level
        if user.is_event_officer:
            user.admin_level = 'event_officer'
        elif user.can_admin_club:
            user.admin_level = 'secretary'

        user.save()


def migrate_backward(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        # Reverse mapping
        if user.is_committee:
            user.role = 'committee'
        else:
            user.role = 'member'

        if user.admin_level == 'event_officer':
            user.is_event_officer = True
            user.can_admin_club = True
        elif user.admin_level == 'secretary':
            user.can_admin_club = True
            user.is_event_officer = False

        user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_new_role_fields'),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrate_backward),
    ]
