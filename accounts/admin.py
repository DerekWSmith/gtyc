from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for custom User model (email-based, no username)."""

    list_display = ('email', 'display_name', 'role', 'title', 'can_admin_club', 'is_event_officer', 'is_active')
    list_filter = ('role', 'title', 'can_admin_club', 'is_event_officer', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'preferred_name')
    ordering = ('email',)

    # Override fieldsets to remove username
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'preferred_name', 'phone')}),
        ('Club role', {'fields': ('role', 'title', 'can_admin_club', 'is_event_officer')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'title', 'can_admin_club', 'is_event_officer'),
        }),
    )
