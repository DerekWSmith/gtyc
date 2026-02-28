"""
Seed bar roster: set RSA/rotation flags on users and create config.

Matches users by first_name + last_name. If no user found, creates a
contact-only user with @gtyc.local email.
"""
import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from roster.models import RosterConfig, RosterDate
from roster.services import (
    regenerate_future_roster, get_fridays_in_range,
    compute_rotation_for_date, fridays_between,
)

User = get_user_model()

# Rotation order — these users get is_rsa=True and is_in_rotation=True
INITIAL_STAFF = [
    {'first_name': 'Peter', 'last_name': 'Shields', 'phone': '0409 001 319', 'position': 1},
    {'first_name': 'Paul', 'last_name': 'Hardy', 'phone': '0417 503 901', 'position': 2},
    {'first_name': 'Geoff', 'last_name': 'Coogan', 'phone': '0419 511 832', 'position': 3},
    {'first_name': 'Matt', 'last_name': 'Potito', 'phone': '0429823771', 'position': 4},
    {'first_name': 'Graeme', 'last_name': 'Butcher', 'phone': '0438 092 238', 'position': 5},
    {'first_name': 'Derek', 'last_name': 'Smith', 'phone': '0435617733', 'position': 6},
    {'first_name': 'Tanya', 'last_name': 'Flanagan', 'phone': '', 'position': 7},
    {'first_name': 'Tim', 'last_name': 'Barrenger', 'phone': '', 'position': 8},
    {'first_name': 'Dick', 'last_name': 'Woolcock', 'phone': '', 'position': 9},
]


class Command(BaseCommand):
    help = 'Seed bar roster: set RSA/rotation flags on users and create config'

    def handle(self, *args, **options):
        for person in INITIAL_STAFF:
            # Try to find existing user
            user = User.objects.filter(
                first_name__iexact=person['first_name'],
                last_name__iexact=person['last_name'],
            ).first()

            if not user:
                # Create a contact-only user
                email = f"{person['first_name'].lower()}.{person['last_name'].lower()}@gtyc.local"
                user = User.objects.create_user(
                    email=email,
                    first_name=person['first_name'],
                    last_name=person['last_name'],
                    membership_type='none',
                )
                self.stdout.write(self.style.WARNING(
                    f"Created contact: {person['first_name']} {person['last_name']} ({email})"
                ))

            user.is_rsa = True
            user.is_in_rotation = True
            user.rotation_position = person['position']
            if person['phone'] and not user.phone:
                user.phone = person['phone']
            user.save()

            self.stdout.write(self.style.SUCCESS(
                f"Set rotation pos {person['position']}: "
                f"{person['first_name']} {person['last_name']}"
            ))

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

        # Populate roster table: past entries + future entries
        config = RosterConfig.load()
        active_staff = list(
            User.objects.filter(is_in_rotation=True, is_active=True)
            .order_by('rotation_position')
        )

        if config and active_staff:
            today = datetime.date.today()
            end = today + datetime.timedelta(days=240)

            # Past entries (anchor to yesterday)
            past_fridays = get_fridays_in_range(config.anchor_date, today - datetime.timedelta(days=1))
            future_fridays = get_fridays_in_range(today, end)

            existing = set(
                RosterDate.objects.filter(source='rotation')
                .values_list('date', flat=True)
            )

            to_create = []
            for friday in past_fridays + future_fridays:
                if friday in existing:
                    continue
                person = compute_rotation_for_date(config, active_staff, friday)
                if person:
                    to_create.append(RosterDate(
                        date=friday,
                        staff_member=person,
                        source='rotation',
                        is_override=False,
                    ))

            if to_create:
                RosterDate.objects.bulk_create(to_create)
                self.stdout.write(self.style.SUCCESS(
                    f'Populated {len(to_create)} roster table entries'
                ))

        self.stdout.write(self.style.SUCCESS('\nRoster seeded successfully.'))
