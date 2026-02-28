"""
Seed initial users: superuser + committee members with titles and permissions.

If a user already exists (by email), update their fields.
If not, create them.
"""
from django.core.management.base import BaseCommand
from accounts.models import User, AdminLevel, Title


# Committee members
COMMITTEE_MEMBERS = [
    {
        'first_name': 'Tanya', 'last_name': 'Flanagan',
        'title': '', 'admin_level': '',
    },
    {
        'first_name': 'Tim', 'last_name': 'Barrenger',
        'title': Title.TREASURER, 'admin_level': '',
    },
    {
        'first_name': 'Matt', 'last_name': 'Potito',
        'title': Title.COMMODORE, 'admin_level': '',
    },
    {
        'first_name': 'Geoff', 'last_name': 'Coogan',
        'title': '', 'admin_level': '',
    },
    {
        'first_name': 'Paul', 'last_name': 'Hardy',
        'title': Title.SECRETARY, 'admin_level': AdminLevel.SECRETARY,
    },
    {
        'first_name': 'Dick', 'last_name': 'Woolcock',
        'title': '', 'admin_level': '',
    },
    {
        'first_name': 'Graeme', 'last_name': 'Butcher',
        'title': '', 'admin_level': '',
    },
    {
        'first_name': 'Peter', 'last_name': 'Shields',
        'title': Title.EVENTS_OFFICER, 'admin_level': AdminLevel.EVENT_OFFICER,
    },
    {
        'first_name': 'Derek', 'last_name': 'Smith',
        'title': '', 'admin_level': AdminLevel.SECRETARY,
    },
    {
        'first_name': 'Shyle', 'last_name': 'Wood',
        'title': '', 'admin_level': '',
    },
]

DEFAULT_PASSWORD = 'lake.last.night'


class Command(BaseCommand):
    help = 'Create/update initial users: superuser + committee members with titles'

    def handle(self, *args, **options):
        # Create or update superuser
        admin, created = User.objects.get_or_create(
            email='admin@gtyc.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'GTYC',
                'is_committee': True,
                'title': Title.EVENTS_OFFICER,
                'admin_level': AdminLevel.SECRETARY,
                'membership_type': 'full',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            admin.set_password(DEFAULT_PASSWORD)
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created superuser: admin@gtyc.com'))
        else:
            admin.title = Title.EVENTS_OFFICER
            admin.admin_level = AdminLevel.SECRETARY
            admin.is_committee = True
            admin.save()
            self.stdout.write('Updated superuser: admin@gtyc.com')

        # Create or update committee members
        for person in COMMITTEE_MEMBERS:
            email = f"{person['first_name'].lower()}.{person['last_name'].lower()}@gtyc.com"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': person['first_name'],
                    'last_name': person['last_name'],
                    'is_committee': True,
                    'membership_type': 'full',
                    'title': person['title'],
                    'admin_level': person['admin_level'],
                },
            )
            if created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
                action = 'Created'
            else:
                user.title = person['title']
                user.admin_level = person['admin_level']
                user.is_committee = True
                user.first_name = person['first_name']
                user.last_name = person['last_name']
                user.save()
                action = 'Updated'

            title_display = person['title'] or 'no title'
            flags = []
            if person['admin_level']:
                flags.append(person['admin_level'])
            flags_str = f" [{', '.join(flags)}]" if flags else ''

            self.stdout.write(self.style.SUCCESS(
                f"{action}: {person['first_name']} {person['last_name']} "
                f"({email}) - {title_display}{flags_str}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nAll new user passwords set to: {DEFAULT_PASSWORD}'
        ))
