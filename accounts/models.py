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


class MembershipType(models.TextChoices):
    NONE = 'none', 'Contact Only'
    FULL = 'full', 'Full Member'
    SOCIAL = 'social', 'Social Member'
    FAMILY = 'family', 'Family Member'


class AdminLevel(models.TextChoices):
    NONE = '', 'None'
    EVENT_OFFICER = 'event_officer', 'Events Officer'
    SECRETARY = 'secretary', 'Secretary'


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

    # Membership
    membership_type = models.CharField(
        max_length=20,
        choices=MembershipType.choices,
        default=MembershipType.FULL,
    )
    is_committee = models.BooleanField(
        default=False,
        help_text='Is a committee member',
    )

    # Admin level (controls access)
    admin_level = models.CharField(
        max_length=20,
        choices=AdminLevel.choices,
        blank=True,
        default='',
        help_text='Secretary: full admin. Event Officer: roster + events.',
    )

    # Honorific title (display only)
    title = models.CharField(
        max_length=20,
        choices=Title.choices,
        blank=True,
        default='',
        help_text='Honorary committee title (display only, does not control access)',
    )

    # RSA / Bar rotation
    is_rsa = models.BooleanField(
        default=False,
        help_text='Has RSA certification, can serve alcohol',
    )
    is_in_rotation = models.BooleanField(
        default=False,
        help_text='In the Friday bar rotation (must also have RSA)',
    )
    rotation_position = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Order in the rotation cycle (1-based)',
    )

    # Contact
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
    def can_admin(self):
        """Can access admin pages (Secretary, Event Officer, or superuser)."""
        return self.is_superuser or self.admin_level in (AdminLevel.SECRETARY, AdminLevel.EVENT_OFFICER)

    @property
    def can_approve_events(self):
        """Can approve/reject/delete events."""
        return self.is_superuser or self.admin_level in (AdminLevel.SECRETARY, AdminLevel.EVENT_OFFICER)

    @property
    def can_manage_members(self):
        """Can manage User CRUD (secretary or superuser)."""
        return self.is_superuser or self.admin_level == AdminLevel.SECRETARY
