from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for custom User model (email-based, no username)."""

    list_display = (
        'email', 'display_name', 'membership_type', 'is_committee',
        'admin_level', 'title', 'is_rsa', 'is_in_rotation', 'is_active',
    )
    list_filter = (
        'membership_type', 'is_committee', 'admin_level', 'title',
        'is_rsa', 'is_in_rotation', 'is_active', 'is_staff',
    )
    search_fields = ('email', 'first_name', 'last_name', 'preferred_name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'preferred_name', 'phone')}),
        ('Club', {'fields': ('membership_type', 'is_committee', 'admin_level', 'title')}),
        ('Bar Staff', {'fields': ('is_rsa', 'is_in_rotation', 'rotation_position')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2', 'membership_type',
                'is_committee', 'admin_level', 'title',
            ),
        }),
    )
