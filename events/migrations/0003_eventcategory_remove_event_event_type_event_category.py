# Custom migration: Create EventCategory, seed categories, migrate existing
# event_type data, then swap to FK.

import django.db.models.deletion
from django.db import migrations, models


# Seed categories and map old event_type values
INITIAL_CATEGORIES = [
    {'name': 'Club Function', 'requires_approval': False, 'position': 1},
    {'name': 'Club Hire with Bar', 'requires_approval': True, 'position': 2},
    {'name': 'Club Hire without Bar', 'requires_approval': False, 'position': 3},
    {'name': 'Working Bee', 'requires_approval': False, 'position': 4},
    {'name': 'Other', 'requires_approval': False, 'position': 5},
]

# Map old TextChoices values to category names
OLD_TYPE_TO_CATEGORY = {
    'club_function': 'Club Function',
    'club_hire_bar': 'Club Hire with Bar',
    'club_hire_no_bar': 'Club Hire without Bar',
    'working_bee': 'Working Bee',
    'other': 'Other',
}


def seed_and_migrate(apps, schema_editor):
    EventCategory = apps.get_model('events', 'EventCategory')
    Event = apps.get_model('events', 'Event')

    # Create categories
    cat_map = {}
    for cat_data in INITIAL_CATEGORIES:
        cat, _ = EventCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'requires_approval': cat_data['requires_approval'],
                'position': cat_data['position'],
            },
        )
        cat_map[cat_data['name']] = cat

    # Migrate existing events
    for event in Event.objects.all():
        old_type = event.event_type or ''
        cat_name = OLD_TYPE_TO_CATEGORY.get(old_type, 'Other')
        event.category = cat_map.get(cat_name)
        event.save(update_fields=['category'])


def reverse_migrate(apps, schema_editor):
    # Reverse is lossy — just clear categories
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_initial'),
    ]

    operations = [
        # 1. Create EventCategory table
        migrations.CreateModel(
            name='EventCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('requires_approval', models.BooleanField(default=False, help_text='Events of this type default to unapproved and need Event Officer sign-off')),
                ('position', models.PositiveIntegerField(default=0, help_text='Display order in dropdowns')),
                ('is_active', models.BooleanField(default=True, help_text='Inactive categories are hidden from new events but kept for history')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'event categories',
                'db_table': 'events_category',
                'ordering': ['position', 'name'],
            },
        ),
        # 2. Add new category FK (alongside old event_type, for data migration)
        migrations.AddField(
            model_name='event',
            name='category',
            field=models.ForeignKey(
                blank=True,
                help_text='Event type/category',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='events',
                to='events.eventcategory',
            ),
        ),
        # 3. Seed categories + migrate existing event data
        migrations.RunPython(seed_and_migrate, reverse_migrate),
        # 4. Remove old event_type field
        migrations.RemoveField(
            model_name='event',
            name='event_type',
        ),
    ]
