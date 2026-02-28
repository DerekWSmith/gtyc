from django.contrib import admin
from .models import RosterDate, RosterConfig


@admin.register(RosterDate)
class RosterDateAdmin(admin.ModelAdmin):
    list_display = ('date', 'staff_member', 'source', 'event', 'notes')
    list_filter = ('source',)
    ordering = ('-date',)


@admin.register(RosterConfig)
class RosterConfigAdmin(admin.ModelAdmin):
    list_display = ('anchor_date', 'anchor_staff_position')
