from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Email-based user manager. No username field."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.is_active = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class Role(models.TextChoices):
    MEMBER = 'member', 'Member'
    COMMITTEE = 'committee', 'Committee Member'


class Title(models.TextChoices):
    COMMODORE = 'commodore', 'Commodore'
    VICE_COMMODORE = 'vice_commodore', 'Vice-Commodore'
    SECRETARY = 'secretary', 'Secretary'
    TREASURER = 'treasurer', 'Treasurer'
    EVENTS_OFFICER = 'events_officer', 'Events Officer'


class User(AbstractUser):
    """Custom user: email auth, role-based permissions."""

    username = None
    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    title = models.CharField(
        max_length=20,
        choices=Title.choices,
        blank=True,
        default='',
        help_text='Honorary committee title (display only, does not control access)',
    )
    is_event_officer = models.BooleanField(
        default=False,
        help_text='Can approve/reject/delete events',
    )
    can_admin_club = models.BooleanField(
        default=False,
        help_text='Can administer events and roster',
    )
    phone = models.CharField(max_length=20, blank=True, default='')
    preferred_name = models.CharField(max_length=100, blank=True, default='')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        ordering = ['email']

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        if self.preferred_name:
            return self.preferred_name
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        return self.email

    @property
    def is_committee(self):
        return self.role == Role.COMMITTEE

    @property
    def can_admin(self):
        """Can access admin pages (Events Officer or Secretary or explicit flag)."""
        return self.can_admin_club or self.is_event_officer

    @property
    def can_approve_events(self):
        return self.is_event_officer
