import datetime
from django.test import TestCase
from .models import StaffMember, RosterDate, RosterConfig
from .services import get_roster_for_range, get_fridays_in_range


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


class RotationBaseTestCase(TestCase):
    """Base with 4 active staff: A(pos 1), B(pos 2), C(pos 3), D(pos 4)."""

    def setUp(self):
        self.staff_a = StaffMember.objects.create(name='A', position=1)
        self.staff_b = StaffMember.objects.create(name='B', position=2)
        self.staff_c = StaffMember.objects.create(name='C', position=3)
        self.staff_d = StaffMember.objects.create(name='D', position=4)

        # Anchor: position 1 (A) on 2026-02-20 (Friday)
        self.anchor_date = datetime.date(2026, 2, 20)
        RosterConfig.objects.create(
            anchor_date=self.anchor_date,
            anchor_staff_position=1,
        )


class BasicRotationTests(RotationBaseTestCase):
    def test_simple_rotation(self):
        """A->B->C->D->A->B over 6 weeks."""
        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 3, 27)
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].name for e in rotation_entries]
        self.assertEqual(names, ['A', 'B', 'C', 'D', 'A', 'B'])

    def test_no_overrides_means_no_override_flag(self):
        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 2, 27)
        entries = get_roster_for_range(start, end)
        for e in entries:
            self.assertFalse(e['is_override'])


class OverrideTests(RotationBaseTestCase):
    def test_override_with_external_sub(self):
        """Override Wk2 with external substitute X (inactive, not in rotation).
        X replaces B for that week only. Rotation continues: C, D, A, B...
        """
        staff_x = StaffMember.objects.create(name='X', position=99, is_active=False)
        RosterDate.objects.create(
            date=datetime.date(2026, 2, 27),
            staff_member=staff_x,
            source=RosterDate.Source.ROTATION,
        )

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 4, 3)  # 7 weeks
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].name for e in rotation_entries]
        # Wk1=A, Wk2=X(override for B), Wk3=C, Wk4=D, Wk5=A, Wk6=B, Wk7=C
        self.assertEqual(names, ['A', 'X', 'C', 'D', 'A', 'B', 'C'])

    def test_override_with_rotation_member(self):
        """Override Wk2 with D (who is in the rotation).
        D replaces B for that week. D also appears at normal Wk4 turn.
        """
        RosterDate.objects.create(
            date=datetime.date(2026, 2, 27),
            staff_member=self.staff_d,
            source=RosterDate.Source.ROTATION,
        )

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 4, 3)  # 7 weeks
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].name for e in rotation_entries]
        # Wk1=A, Wk2=D(override for B), Wk3=C, Wk4=D(normal), Wk5=A, Wk6=B, Wk7=C
        self.assertEqual(names, ['A', 'D', 'C', 'D', 'A', 'B', 'C'])

    def test_override_is_flagged(self):
        staff_x = StaffMember.objects.create(name='X', position=99, is_active=False)
        RosterDate.objects.create(
            date=datetime.date(2026, 2, 27),
            staff_member=staff_x,
            source=RosterDate.Source.ROTATION,
        )

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 3, 6)
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']

        self.assertFalse(rotation_entries[0]['is_override'])  # Wk1 A
        self.assertTrue(rotation_entries[1]['is_override'])    # Wk2 X
        self.assertFalse(rotation_entries[2]['is_override'])   # Wk3 C

    def test_multiple_overrides(self):
        """Two consecutive overrides replace B and C. Rotation continues from D."""
        staff_x = StaffMember.objects.create(name='X', position=98, is_active=False)
        staff_y = StaffMember.objects.create(name='Y', position=99, is_active=False)

        RosterDate.objects.create(
            date=datetime.date(2026, 2, 27),
            staff_member=staff_x,
            source=RosterDate.Source.ROTATION,
        )
        RosterDate.objects.create(
            date=datetime.date(2026, 3, 6),
            staff_member=staff_y,
            source=RosterDate.Source.ROTATION,
        )

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 4, 10)  # 8 weeks
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].name for e in rotation_entries]
        # Wk1=A, Wk2=X(for B), Wk3=Y(for C), Wk4=D, Wk5=A, Wk6=B, Wk7=C, Wk8=D
        self.assertEqual(names, ['A', 'X', 'Y', 'D', 'A', 'B', 'C', 'D'])


class StaffChangeTests(RotationBaseTestCase):
    def test_removing_staff_recalculates(self):
        """Deactivate A. Active staff become B,C,D (ordered by position).
        Re-anchor so index 0 of the new active list (B) starts on anchor date.
        """
        self.staff_a.is_active = False
        self.staff_a.save()

        # anchor_staff_position=1 means index 0 in active list = B
        config = RosterConfig.load()
        config.anchor_staff_position = 1
        config.save()

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 3, 27)
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].name for e in rotation_entries]
        self.assertEqual(names, ['B', 'C', 'D', 'B', 'C', 'D'])

    def test_adding_staff_recalculates(self):
        """Add E at position 5. Cycle: A->B->C->D->E->A."""
        StaffMember.objects.create(name='E', position=5)

        start = datetime.date(2026, 2, 20)
        end = datetime.date(2026, 3, 27)
        entries = get_roster_for_range(start, end)
        rotation_entries = [e for e in entries if e['source'] == 'rotation']
        names = [e['staff_members'][0].name for e in rotation_entries]
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
        StaffMember.objects.create(name='A', position=1)
        entries = get_roster_for_range(
            datetime.date(2026, 2, 20),
            datetime.date(2026, 3, 20),
        )
        self.assertEqual(entries, [])
