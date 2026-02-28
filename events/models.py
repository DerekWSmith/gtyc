from django.db import models
from django.conf import settings


class EventCategory(models.Model):
    """Editable event type/category.

    Admins can add, rename, and remove categories via the UI.
    Each category has a flag indicating whether events of this type
    require Event Officer approval before being confirmed.
    """
    name = models.CharField(max_length=100, unique=True)
    requires_approval = models.BooleanField(
        default=False,
        help_text='Events of this type default to unapproved and need Event Officer sign-off',
    )
    position = models.PositiveIntegerField(
        default=0,
        help_text='Display order in dropdowns',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive categories are hidden from new events but kept for history',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'events_category'
        ordering = ['position', 'name']
        verbose_name_plural = 'event categories'

    def __str__(self):
        return self.name


class Event(models.Model):
    """Yacht club event/booking."""

    title = models.CharField(max_length=200)
    category = models.ForeignKey(
        EventCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        help_text='Event type/category',
    )
    is_approved = models.BooleanField(
        default=True,
        help_text='Approval flag — categories with requires_approval default to False on creation.',
    )

    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField()

    # Contact for the booking
    contact_name = models.CharField(max_length=100, blank=True, default='')
    contact_phone = models.CharField(max_length=20, blank=True, default='')

    # Bar staff assigned (1-4, RSA-certified users)
    bar_staff = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='bar_events',
        help_text='1-4 RSA-certified bar staff assigned to this event',
    )

    notes = models.TextField(blank=True, default='')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_events',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'events_event'
        ordering = ['start_datetime']

    def __str__(self):
        cat_name = self.category.name if self.category else 'Other'
        return f"{self.title} ({cat_name})"

    @property
    def category_name(self):
        """Display name for the category, falls back to 'Other'."""
        return self.category.name if self.category else 'Other'

    @property
    def requires_approval(self):
        return self.category.requires_approval if self.category else False

    @property
    def is_tentative(self):
        """Event is tentative (pending) if its category requires approval and it hasn't been approved."""
        return self.requires_approval and not self.is_approved

    def save(self, *args, **kwargs):
        # New events in a requires_approval category start unapproved
        if self.pk is None and self.requires_approval:
            self.is_approved = False
        super().save(*args, **kwargs)
