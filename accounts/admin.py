from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'google_calendar_connected', 'created_at']
    list_filter = ['google_calendar_connected']
    search_fields = ['user__username', 'user__email']
