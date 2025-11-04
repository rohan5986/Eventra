from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Event(models.Model):
    """Model to store calendar events parsed from unstructured text."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    # Store original text input for reference
    original_text = models.TextField()
    
    # Google Calendar integration
    google_calendar_event_id = models.CharField(max_length=255, blank=True, null=True)
    synced_to_google = models.BooleanField(default=False)
    color_id = models.CharField(max_length=10, blank=True, null=True, help_text='Google Calendar color ID (1-11)')
    guest_emails = models.TextField(blank=True, null=True, help_text='Comma-separated list of guest email addresses')
    
    # Geolocation data
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['user', 'start_datetime']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.start_datetime.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def is_upcoming(self):
        """Check if event is in the future."""
        return self.start_datetime > timezone.now()
