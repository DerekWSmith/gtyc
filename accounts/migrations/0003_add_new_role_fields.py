"""Add new role/membership fields to User model.

Adds: membership_type, is_committee, admin_level, is_rsa, is_in_rotation, rotation_position.
Old fields (role, can_admin_club, is_event_officer) kept temporarily for data migration.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_title_and_can_admin_club'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='membership_type',
            field=models.CharField(
                choices=[('none', 'Contact Only'), ('full', 'Full Member'),
                         ('social', 'Social Member'), ('family', 'Family Member')],
                default='full',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='is_committee',
            field=models.BooleanField(default=False, help_text='Is a committee member'),
        ),
        migrations.AddField(
            model_name='user',
            name='admin_level',
            field=models.CharField(
                blank=True,
                choices=[('', 'None'), ('event_officer', 'Event Officer'),
                         ('secretary', 'Secretary')],
                default='',
                help_text='Secretary: full admin. Event Officer: roster + events.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='is_rsa',
            field=models.BooleanField(default=False, help_text='Has RSA certification, can serve alcohol'),
        ),
        migrations.AddField(
            model_name='user',
            name='is_in_rotation',
            field=models.BooleanField(default=False, help_text='In the Friday bar rotation (must also have RSA)'),
        ),
        migrations.AddField(
            model_name='user',
            name='rotation_position',
            field=models.PositiveIntegerField(
                blank=True, null=True,
                help_text='Order in the rotation cycle (1-based)',
            ),
        ),
    ]
