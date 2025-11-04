from django.db import models
from django.contrib.auth.models import User
import json


class UserProfile(models.Model):
    """Extended user profile to store Google Calendar OAuth credentials."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Google Calendar OAuth credentials (stored as JSON)
    google_calendar_credentials = models.TextField(blank=True, null=True)
    google_calendar_connected = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Google Calendar: {'Connected' if self.google_calendar_connected else 'Not Connected'}"
    
    def get_credentials_dict(self):
        """Get Google Calendar credentials as dictionary."""
        if self.google_calendar_credentials:
            try:
                return json.loads(self.google_calendar_credentials)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_credentials_dict(self, creds_dict):
        """Store Google Calendar credentials as JSON string."""
        if creds_dict:
            self.google_calendar_credentials = json.dumps(creds_dict)
            self.google_calendar_connected = True
        else:
            self.google_calendar_credentials = None
            self.google_calendar_connected = False
        self.save()
