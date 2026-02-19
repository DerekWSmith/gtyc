from django.contrib import admin
from .models import Event, EventCategory


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'requires_approval', 'position', 'is_active')
    list_filter = ('requires_approval', 'is_active')
    list_editable = ('position', 'requires_approval')
    ordering = ('position',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'start_datetime', 'is_approved', 'created_by')
    list_filter = ('category', 'is_approved')
    search_fields = ('title', 'contact_name')
    ordering = ('-start_datetime',)
    date_hierarchy = 'start_datetime'
    filter_horizontal = ('bar_staff',)
