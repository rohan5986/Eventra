from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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


class SystemSettings(models.Model):
    """System-wide settings for LLM configuration and API tokens.
    
    This model uses a singleton pattern - only one instance should exist.
    """
    
    LLM_PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('google', 'Google'),
    ]
    
    # Singleton ID to ensure only one instance exists
    id = models.IntegerField(primary_key=True, default=1, editable=False)
    
    # LLM Configuration
    llm_provider = models.CharField(
        max_length=50,
        choices=LLM_PROVIDER_CHOICES,
        default='openai',
        verbose_name='LLM Provider',
        help_text='The LLM provider to use for parsing text into events'
    )
    
    llm_model = models.CharField(
        max_length=100,
        default='gpt-4',
        verbose_name='LLM Model',
        help_text='The specific model to use (e.g., gpt-4, gpt-3.5-turbo)'
    )
    
    llm_api_key = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='LLM API Key',
        help_text='API key for the LLM provider. Leave empty to use environment variable OPENAI_API_KEY.'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return f"System Settings - LLM: {self.llm_provider} ({self.llm_model})"
    
    def clean(self):
        """Ensure only one instance exists."""
        if SystemSettings.objects.exists() and self.id != SystemSettings.objects.first().id:
            raise ValidationError('Only one SystemSettings instance is allowed.')
    
    def save(self, *args, **kwargs):
        """Override save to ensure singleton pattern."""
        self.id = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get the singleton SystemSettings instance, creating it if it doesn't exist."""
        settings, created = cls.objects.get_or_create(id=1)
        return settings
    
    def get_api_key(self):
        """Get the API key, falling back to environment variable if not set."""
        from decouple import config
        if self.llm_api_key:
            return self.llm_api_key
        # Fallback to environment variable for backward compatibility
        return config('OPENAI_API_KEY', default='')


class LLMParsingLog(models.Model):
    """Log of LLM parsing attempts for analytics.
    
    Tracks parsing accuracy, response times, and error rates.
    """
    
    ERROR_TYPE_CHOICES = [
        ('json_decode', 'JSON Decode Error'),
        ('missing_field', 'Missing Required Field'),
        ('api_error', 'API Error'),
        ('timeout', 'Timeout'),
        ('rate_limit', 'Rate Limit'),
        ('auth_error', 'Authentication Error'),
        ('other', 'Other Error'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='llm_parsing_logs',
        help_text='User who made the parsing request'
    )
    
    # Input data
    input_text = models.TextField(
        help_text='Original text input that was parsed'
    )
    input_text_length = models.IntegerField(
        help_text='Length of input text in characters'
    )
    
    # LLM Configuration used
    llm_provider = models.CharField(
        max_length=50,
        help_text='LLM provider used (e.g., openai)'
    )
    llm_model = models.CharField(
        max_length=100,
        help_text='LLM model used (e.g., gpt-4)'
    )
    
    # Results
    success = models.BooleanField(
        default=False,
        help_text='Whether parsing was successful'
    )
    response_time_ms = models.FloatField(
        null=True,
        blank=True,
        help_text='Response time in milliseconds'
    )
    
    # Error information (if failed)
    error_type = models.CharField(
        max_length=50,
        choices=ERROR_TYPE_CHOICES,
        null=True,
        blank=True,
        help_text='Type of error if parsing failed'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if parsing failed'
    )
    
    # Response data (if successful)
    parsed_data = models.JSONField(
        null=True,
        blank=True,
        help_text='Parsed event data if successful'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'LLM Parsing Log'
        verbose_name_plural = 'LLM Parsing Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['success']),
            models.Index(fields=['llm_provider', 'llm_model']),
        ]
    
    def __str__(self):
        status = "Success" if self.success else f"Failed ({self.error_type})"
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M')} - {status} - {self.llm_provider}/{self.llm_model}"
    
    @classmethod
    def get_analytics(cls, days=30):
        """Get analytics data for the last N days.
        
        Returns:
            Dictionary with analytics metrics
        """
        from django.utils import timezone
        from django.db.models import Count, Avg, Q, F
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        logs = cls.objects.filter(created_at__gte=cutoff_date)
        
        total = logs.count()
        successful = logs.filter(success=True).count()
        failed = logs.filter(success=False).count()
        
        success_rate = (successful / total * 100) if total > 0 else 0
        avg_response_time = logs.filter(success=True).aggregate(
            avg_time=Avg('response_time_ms')
        )['avg_time'] or 0
        
        # Error breakdown
        error_breakdown = logs.filter(success=False).values('error_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Provider/Model performance
        provider_stats = logs.values('llm_provider', 'llm_model').annotate(
            total=Count('id'),
            successful=Count('id', filter=Q(success=True)),
            avg_response_time=Avg('response_time_ms', filter=Q(success=True))
        ).order_by('-total')
        
        # Daily statistics
        from django.db.models.functions import TruncDate
        daily_stats = logs.annotate(
            day=TruncDate('created_at')
        ).values('day').annotate(
            total=Count('id'),
            successful=Count('id', filter=Q(success=True)),
            failed=Count('id', filter=Q(success=False))
        ).order_by('day')
        
        return {
            'total_requests': total,
            'successful_requests': successful,
            'failed_requests': failed,
            'success_rate': round(success_rate, 2),
            'avg_response_time_ms': round(avg_response_time, 2),
            'error_breakdown': list(error_breakdown),
            'provider_stats': list(provider_stats),
            'daily_stats': list(daily_stats),
            'period_days': days,
        }
