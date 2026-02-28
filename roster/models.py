from django.conf import settings
from django.db import models


class RosterDate(models.Model):
    """A specific date assignment on the roster.

    Sources:
    - 'rotation': A Friday rotation assignment (auto-computed or manual override).
    - 'event': A bar staff assignment from a special event.

    Every Friday has a stored RosterDate row. The is_override flag distinguishes
    auto-computed entries (regenerated on staff changes) from manual overrides
    (preserved during regeneration). Past entries are never recalculated.
    """

    class Source(models.TextChoices):
        ROTATION = 'rotation', 'Rotation'
        EVENT = 'event', 'Special Event'

    date = models.DateField(db_index=True)
    staff_member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='roster_dates',
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.ROTATION,
    )
    is_override = models.BooleanField(
        default=False,
        help_text='True for manual admin overrides, False for auto-computed',
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
        return f"{self.date} — {self.staff_member.display_name} ({self.get_source_display()})"


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
