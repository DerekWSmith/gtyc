from django.contrib import admin
from .models import StaffMember, RosterDate, RosterConfig


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'position', 'is_active')
    list_filter = ('is_active',)
    ordering = ('position',)


@admin.register(RosterDate)
class RosterDateAdmin(admin.ModelAdmin):
    list_display = ('date', 'staff_member', 'source', 'event', 'notes')
    list_filter = ('source',)
    ordering = ('-date',)


@admin.register(RosterConfig)
class RosterConfigAdmin(admin.ModelAdmin):
    list_display = ('anchor_date', 'anchor_staff_position')
