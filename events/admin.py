from django.contrib import admin
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'start_datetime', 'location', 'synced_to_google']
    list_filter = ['synced_to_google', 'start_datetime', 'created_at']
    search_fields = ['title', 'description', 'location', 'user__username']
    date_hierarchy = 'start_datetime'
    readonly_fields = ['created_at', 'updated_at', 'original_text']
