from django.db import models


class StaffMember(models.Model):
    """A bar staff member in the rotation.

    NOT linked to User — bar staff are often non-members who won't log in.
    The 'position' field defines the rotation order.
    """
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, default='')
    position = models.PositiveIntegerField(
        help_text='Order in the rotation cycle (1-based)',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive staff are excluded from rotation but kept for history',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roster_staff'
        ordering = ['position']

    def __str__(self):
        return f"{self.name} (pos {self.position})"


class RosterDate(models.Model):
    """A specific date assignment on the roster.

    Two sources:
    - 'rotation': A manual override of a Friday's auto-rotation assignment.
    - 'event': A bar staff assignment from a special event.

    For regular Fridays WITHOUT an override, the rotation algorithm computes
    the assignment on-the-fly — no RosterDate row exists.
    """

    class Source(models.TextChoices):
        ROTATION = 'rotation', 'Friday Rotation Override'
        EVENT = 'event', 'Special Event'

    date = models.DateField(db_index=True)
    staff_member = models.ForeignKey(
        StaffMember,
        on_delete=models.CASCADE,
        related_name='roster_dates',
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.ROTATION,
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='roster_assignments',
        help_text='Set when source=event',
    )
    notes = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'roster_dates'
        ordering = ['date']
        indexes = [
            models.Index(fields=['date', 'source']),
        ]

    def __str__(self):
        return f"{self.date} — {self.staff_member.name} ({self.get_source_display()})"


class RosterConfig(models.Model):
    """Singleton config for the roster rotation.

    Stores the anchor point: which staff position was assigned to which
    date, as the starting point for the rotation algorithm.
    """
    anchor_date = models.DateField(
        help_text='A known Friday where the rotation position is established',
    )
    anchor_staff_position = models.PositiveIntegerField(
        default=1,
        help_text='The staff position number assigned to anchor_date',
    )

    class Meta:
        db_table = 'roster_config'

    def __str__(self):
        return f"Anchor: position {self.anchor_staff_position} on {self.anchor_date}"

    def save(self, *args, **kwargs):
        """Enforce singleton — only one RosterConfig can exist."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Get the singleton config, or None if not set up yet."""
        try:
            return cls.objects.get(pk=1)
        except cls.DoesNotExist:
            return None
