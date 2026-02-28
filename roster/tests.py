import datetime
from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import RosterDate, RosterConfig
from .services import (
    get_roster_for_range, get_fridays_in_range,
    regenerate_future_roster, compute_rotation_for_date,
)

User = get_user_model()


class FridayHelperTests(TestCase):
    def test_get_fridays_in_range(self):
        # 2026-02-20 is a Friday
        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 3, 13)
        fridays = get_fridays_in_range(start, end)
        self.assertEqual(len(fridays), 4)
        self.assertEqual(fridays[0], datetime.date(2026, 2, 20))
        self.assertEqual(fridays[3], datetime.date(2026, 3, 13))

    def test_get_fridays_start_not_friday(self):
        start = datetime.date(2026, 2, 16)  # Monday
        end = datetime.date(2026, 2, 27)
        fridays = get_fridays_in_range(start, end)
        self.assertEqual(len(fridays), 2)
        self.assertEqual(fridays[0], datetime.date(2026, 2, 20))


def _create_rotation_user(letter, position):
    """Create a User in the rotation with a single-letter name."""
    user = User.objects.create_user(
        email=f'{letter.lower()}@test.com',
        first_name=letter,
        last_name='',
        is_rsa=True,
        is_in_rotation=True,
        rotation_position=position,
    )
    return user


class RotationBaseTestCase(TestCase):
    """Base with 4 active rotation users: A(pos 1), B(pos 2), C(pos 3), D(pos 4)."""

    def setUp(self):
        self.staff_a = _create_rotation_user('A', 1)
        self.staff_b = _create_rotation_user('B', 2)
        self.staff_c = _create_rotation_user('C', 3)
        self.staff_d = _create_rotation_user('D', 4)

        # Anchor: position 1 (A) on 2026-02-20 (Friday)
        self.anchor_date = datetime.date(2026, 2, 20)
        RosterConfig.objects.create(
            anchor_date=self.anchor_date,
            anchor_staff_position=1,
        )


class BasicRotationTests(RotationBaseTestCase):
    def test_simple_rotation_fallback(self):
        """On-the-fly fallback: A->B->C->D->A->B over 6 weeks (no stored entries)."""
        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 3, 27)
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].display_name for e in rotation_entries]
        self.assertEqual(names, ['A', 'B', 'C', 'D', 'A', 'B'])

    def test_no_overrides_means_no_override_flag(self):
        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 2, 27)
        entries = get_roster_for_range(start, end)
        for e in entries:
            self.assertFalse(e['is_override'])

    def test_stored_auto_entries_used(self):
        """When auto entries exist in the DB, they're used instead of on-the-fly."""
        # Create stored auto entries
        staff = list(User.objects.filter(
            is_in_rotation=True, is_active=True,
        ).order_by('rotation_position'))
        config = RosterConfig.load()

        fri1 = datetime.date(2026, 2, 20)
        fri2 = datetime.date(2026, 2, 27)
        RosterDate.objects.create(
            date=fri1, staff_member=staff[0],
            source='rotation', is_override=False,
        )
        RosterDate.objects.create(
            date=fri2, staff_member=staff[1],
            source='rotation', is_override=False,
        )

        entries = get_roster_for_range(fri1, fri2)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].display_name for e in rotation_entries]
        self.assertEqual(names, ['A', 'B'])
        self.assertFalse(rotation_entries[0]['is_override'])


class OverrideTests(RotationBaseTestCase):
    def test_override_with_external_sub(self):
        """Override Wk2 with external substitute X (not in rotation).
        X replaces B for that week only. Rotation continues: C, D, A, B...
        """
        staff_x = User.objects.create_user(
            email='x@test.com', first_name='X', last_name='',
            is_rsa=True, is_in_rotation=False,
        )
        RosterDate.objects.create(
            date=datetime.date(2026, 2, 27),
            staff_member=staff_x,
            source=RosterDate.Source.ROTATION,
            is_override=True,
        )

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 4, 3)  # 7 weeks
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].display_name for e in rotation_entries]
        # Wk1=A(fallback), Wk2=X(override for B), Wk3=C(fallback), ...
        self.assertEqual(names, ['A', 'X', 'C', 'D', 'A', 'B', 'C'])

    def test_override_with_rotation_member(self):
        """Override Wk2 with D (who is in the rotation).
        D replaces B for that week. D also appears at normal Wk4 turn.
        """
        RosterDate.objects.create(
            date=datetime.date(2026, 2, 27),
            staff_member=self.staff_d,
            source=RosterDate.Source.ROTATION,
            is_override=True,
        )

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 4, 3)  # 7 weeks
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].display_name for e in rotation_entries]
        self.assertEqual(names, ['A', 'D', 'C', 'D', 'A', 'B', 'C'])

    def test_override_is_flagged(self):
        staff_x = User.objects.create_user(
            email='x@test.com', first_name='X', last_name='',
            is_rsa=True, is_in_rotation=False,
        )
        RosterDate.objects.create(
            date=datetime.date(2026, 2, 27),
            staff_member=staff_x,
            source=RosterDate.Source.ROTATION,
            is_override=True,
        )

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 3, 6)
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']

        self.assertFalse(rotation_entries[0]['is_override'])  # Wk1 A (fallback)
        self.assertTrue(rotation_entries[1]['is_override'])    # Wk2 X (override)
        self.assertFalse(rotation_entries[2]['is_override'])   # Wk3 C (fallback)

    def test_multiple_overrides(self):
        """Two consecutive overrides replace B and C. Rotation continues from D."""
        staff_x = User.objects.create_user(
            email='x@test.com', first_name='X', last_name='',
            is_rsa=True, is_in_rotation=False,
        )
        staff_y = User.objects.create_user(
            email='y@test.com', first_name='Y', last_name='',
            is_rsa=True, is_in_rotation=False,
        )

        RosterDate.objects.create(
            date=datetime.date(2026, 2, 27),
            staff_member=staff_x,
            source=RosterDate.Source.ROTATION,
            is_override=True,
        )
        RosterDate.objects.create(
            date=datetime.date(2026, 3, 6),
            staff_member=staff_y,
            source=RosterDate.Source.ROTATION,
            is_override=True,
        )

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 4, 10)  # 8 weeks
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].display_name for e in rotation_entries]
        self.assertEqual(names, ['A', 'X', 'Y', 'D', 'A', 'B', 'C', 'D'])


class RegenerationTests(RotationBaseTestCase):
    def test_regenerate_creates_auto_entries(self):
        """regenerate_future_roster() populates the table with auto entries."""
        regenerate_future_roster()

        # Should have created entries for future Fridays
        auto_count = RosterDate.objects.filter(
            source='rotation', is_override=False,
        ).count()
        self.assertGreater(auto_count, 0)

    def test_regenerate_preserves_overrides(self):
        """Overrides are NOT deleted during regeneration."""
        staff_x = User.objects.create_user(
            email='x@test.com', first_name='X', last_name='',
            is_rsa=True, is_in_rotation=False,
        )
        # Create a future override
        future_fri = datetime.date.today() + datetime.timedelta(days=30)
        while future_fri.weekday() != 4:
            future_fri += datetime.timedelta(days=1)

        RosterDate.objects.create(
            date=future_fri,
            staff_member=staff_x,
            source=RosterDate.Source.ROTATION,
            is_override=True,
        )

        regenerate_future_roster()

        # Override should still exist
        override = RosterDate.objects.filter(
            date=future_fri, source='rotation', is_override=True,
        ).first()
        self.assertIsNotNone(override)
        self.assertEqual(override.staff_member.id, staff_x.id)

        # No auto entry should exist for the overridden date
        auto = RosterDate.objects.filter(
            date=future_fri, source='rotation', is_override=False,
        ).first()
        self.assertIsNone(auto)

    def test_reorder_only_swaps_affected_people(self):
        """Swapping A and B positions: only A and B's future dates change."""
        # First, generate entries
        regenerate_future_roster()

        # Record who's on each future Friday before the swap
        before = {}
        for rd in RosterDate.objects.filter(source='rotation', is_override=False).order_by('date')[:8]:
            before[rd.date] = rd.staff_member.display_name

        # Swap A (pos 1) and B (pos 2) — DON'T re-anchor
        self.staff_a.rotation_position = 2
        self.staff_a.save()
        self.staff_b.rotation_position = 1
        self.staff_b.save()

        regenerate_future_roster()

        # Check after swap
        after = {}
        for rd in RosterDate.objects.filter(source='rotation', is_override=False).order_by('date')[:8]:
            after[rd.date] = rd.staff_member.display_name

        for date in before:
            if date in after:
                if before[date] == 'A':
                    self.assertEqual(after[date], 'B', f'{date}: A should become B')
                elif before[date] == 'B':
                    self.assertEqual(after[date], 'A', f'{date}: B should become A')
                else:
                    self.assertEqual(after[date], before[date],
                                     f'{date}: {before[date]} should be unchanged')


class StaffChangeTests(RotationBaseTestCase):
    def test_removing_staff_with_on_the_fly(self):
        """On-the-fly fallback: remove A, re-anchor so B starts."""
        self.staff_a.is_in_rotation = False
        self.staff_a.save()

        config = RosterConfig.load()
        config.anchor_staff_position = 1
        config.save()

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 3, 27)
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].display_name for e in rotation_entries]
        self.assertEqual(names, ['B', 'C', 'D', 'B', 'C', 'D'])

    def test_adding_staff_extends_cycle(self):
        """Add E at position 5. Cycle: A->B->C->D->E->A."""
        _create_rotation_user('E', 5)

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 3, 27)
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].display_name for e in rotation_entries]
        self.assertEqual(names, ['A', 'B', 'C', 'D', 'E', 'A'])


class EmptyRosterTests(TestCase):
    def test_no_staff_returns_empty(self):
        RosterConfig.objects.create(
            anchor_date=datetime.date(2026, 2, 20),
            anchor_staff_position=1,
        )
        entries = get_roster_for_range(
            datetime.date(2026, 2, 20),
            datetime.date(2026, 3, 20),
        )
        self.assertEqual(entries, [])

    def test_no_config_returns_empty(self):
        _create_rotation_user('A', 1)
        entries = get_roster_for_range(
            datetime.date(2026, 2, 20),
            datetime.date(2026, 3, 20),
        )
        self.assertEqual(entries, [])
