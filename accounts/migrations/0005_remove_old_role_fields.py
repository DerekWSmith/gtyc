"""Remove old role/permission fields from User model.

Removes: role, can_admin_club, is_event_officer.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_migrate_role_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='role',
        ),
        migrations.RemoveField(
            model_name='user',
            name='can_admin_club',
        ),
        migrations.RemoveField(
            model_name='user',
            name='is_event_officer',
        ),
    ]
