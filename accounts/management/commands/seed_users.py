"""
Seed initial users: superuser + 8 committee members with titles and permissions.

If a user already exists (by email), update their title and permission flags.
If not, create them.
"""
from django.core.management.base import BaseCommand
from accounts.models import User, Role, Title


# The 8 committee members
COMMITTEE_MEMBERS = [
    {
        'first_name': 'Tanya', 'last_name': 'Flanagan',
        'title': '', 'can_admin_club': False, 'is_event_officer': False,
    },
    {
        'first_name': 'Tim', 'last_name': 'Barrenger',
        'title': Title.TREASURER, 'can_admin_club': False, 'is_event_officer': False,
    },
    {
        'first_name': 'Matt', 'last_name': 'Potito',
        'title': Title.COMMODORE, 'can_admin_club': False, 'is_event_officer': False,
    },
    {
        'first_name': 'Geoff', 'last_name': 'Coogan',
        'title': '', 'can_admin_club': False, 'is_event_officer': False,
    },
    {
        'first_name': 'Paul', 'last_name': 'Hardy',
        'title': Title.SECRETARY, 'can_admin_club': True, 'is_event_officer': False,
    },
    {
        'first_name': 'Dick', 'last_name': 'Woolcock',
        'title': '', 'can_admin_club': False, 'is_event_officer': False,
    },
    {
        'first_name': 'Graeme', 'last_name': 'Butcher',
        'title': '', 'can_admin_club': False, 'is_event_officer': False,
    },
    {
        'first_name': 'Peter', 'last_name': 'Shields',
        'title': Title.EVENTS_OFFICER, 'can_admin_club': True, 'is_event_officer': True,
    },
    {
        'first_name': 'Derek', 'last_name': 'Smith',
        'title': '', 'can_admin_club': True, 'is_event_officer': False,
    },
    {
        'first_name': 'Shyle', 'last_name': 'Wood',
        'title': '', 'can_admin_club': False, 'is_event_officer': False,
    },
]

DEFAULT_PASSWORD = 'lake.last.night'


class Command(BaseCommand):
    help = 'Create/update initial users: superuser + 8 committee members with titles'

    def handle(self, *args, **options):
        # Create or update superuser
        admin, created = User.objects.get_or_create(
            email='admin@gtyc.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'GTYC',
                'role': Role.COMMITTEE,
                'title': Title.EVENTS_OFFICER,
                'can_admin_club': True,
                'is_event_officer': True,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            admin.set_password(DEFAULT_PASSWORD)
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created superuser: admin@gtyc.com'))
        else:
            # Update permissions on existing admin
            admin.title = Title.EVENTS_OFFICER
            admin.can_admin_club = True
            admin.is_event_officer = True
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
                    'role': Role.COMMITTEE,
                    'title': person['title'],
                    'can_admin_club': person['can_admin_club'],
                    'is_event_officer': person['is_event_officer'],
                },
            )
            if created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
                action = 'Created'
            else:
                # Update title and permissions on existing user
                user.title = person['title']
                user.can_admin_club = person['can_admin_club']
                user.is_event_officer = person['is_event_officer']
                user.first_name = person['first_name']
                user.last_name = person['last_name']
                user.save()
                action = 'Updated'

            title_display = person['title'] or 'no title'
            flags = []
            if person['can_admin_club']:
                flags.append('admin')
            if person['is_event_officer']:
                flags.append('event officer')
            flags_str = f" [{', '.join(flags)}]" if flags else ''

            self.stdout.write(self.style.SUCCESS(
                f"{action}: {person['first_name']} {person['last_name']} "
                f"({email}) - {title_display}{flags_str}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nAll new user passwords set to: {DEFAULT_PASSWORD}'
        ))
