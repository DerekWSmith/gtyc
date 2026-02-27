"""
Seed bar roster staff and config.

If a staff member already exists (by name), update their details.
If not, create them.
"""
import datetime
from django.core.management.base import BaseCommand
from roster.models import StaffMember, RosterConfig


# All 9 committee members are also bar staff (rotation order)
INITIAL_STAFF = [
    {'name': 'Peter Shields', 'phone': '0409 001 319', 'position': 1},
    {'name': 'Paul Hardy', 'phone': '0417 503 901', 'position': 2},
    {'name': 'Geoff Coogan', 'phone': '0419 511 832', 'position': 3},
    {'name': 'Matt Potito', 'phone': '0429823771', 'position': 4},
    {'name': 'Graeme Butcher', 'phone': '0438 092 238', 'position': 5},
    {'name': 'Derek Smith', 'phone': '0435617733', 'position': 6},
    {'name': 'Tanya Flanagan', 'phone': '', 'position': 7},
    {'name': 'Tim Barrenger', 'phone': '', 'position': 8},
    {'name': 'Dick Woolcock', 'phone': '', 'position': 9},
]


class Command(BaseCommand):
    help = 'Seed bar roster staff and rotation config'

    def handle(self, *args, **options):
        for person in INITIAL_STAFF:
            staff, created = StaffMember.objects.update_or_create(
                name=person['name'],
                defaults={
                    'phone': person['phone'],
                    'position': person['position'],
                    'is_active': True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"Created staff: {person['name']} (pos {person['position']})"
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"Updated staff: {person['name']} (pos {person['position']})"
                ))

        # Deactivate old staff not in current list
        current_names = [p['name'] for p in INITIAL_STAFF]
        old_staff = StaffMember.objects.filter(is_active=True).exclude(name__in=current_names)
        for s in old_staff:
            s.is_active = False
            s.save()
            self.stdout.write(self.style.WARNING(f"Deactivated: {s.name}"))

        # Set anchor: Paul Hardy (position 2) was on duty 2025-12-19
        config = RosterConfig.load()
        if config is None:
            RosterConfig.objects.create(
                anchor_date=datetime.date(2025, 12, 19),
                anchor_staff_position=2,
            )
            self.stdout.write(self.style.SUCCESS(
                'Created roster config: anchor position 2 on 2025-12-19'
            ))
        else:
            self.stdout.write('Roster config already exists')

        self.stdout.write(self.style.SUCCESS('\nRoster seeded successfully.'))
