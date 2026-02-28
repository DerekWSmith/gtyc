"""Finalize StaffMember → User migration on RosterDate.

1. Remove old staff_member FK (points to StaffMember with StaffMember IDs)
2. Rename user FK to staff_member (has User IDs from data migration)
3. Delete StaffMember model
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('roster', '0003_merge_staff_into_users'),
        ('events', '0007_swap_bar_staff_to_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Remove old staff_member FK (to StaffMember)
        migrations.RemoveField(
            model_name='rosterdate',
            name='staff_member',
        ),
        # Step 2: Rename user → staff_member
        migrations.RenameField(
            model_name='rosterdate',
            old_name='user',
            new_name='staff_member',
        ),
        # Step 3: Make it non-nullable and set proper attributes
        migrations.AlterField(
            model_name='rosterdate',
            name='staff_member',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='roster_dates',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Step 4: Delete StaffMember model
        migrations.DeleteModel(
            name='StaffMember',
        ),
    ]
