"""Swap Event.bar_staff from StaffMember M2M to User M2M.

Uses SeparateDatabaseAndState to rename the bar_staff_users table
to bar_staff, avoiding data loss.
"""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0006_migrate_bar_staff_to_users'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Drop old bar_staff M2M table (StaffMember references)
        migrations.RemoveField(
            model_name='event',
            name='bar_staff',
        ),
        # Step 2: Rename bar_staff_users to bar_staff
        migrations.RenameField(
            model_name='event',
            old_name='bar_staff_users',
            new_name='bar_staff',
        ),
        # Step 3: Update field metadata
        migrations.AlterField(
            model_name='event',
            name='bar_staff',
            field=models.ManyToManyField(
                blank=True,
                help_text='1-4 RSA-certified bar staff assigned to this event',
                related_name='bar_events',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
