from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.urls import path
from django.shortcuts import render
from django.utils.html import format_html
from .models import UserProfile, SystemSettings, LLMParsingLog


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'google_calendar_connected', 'created_at']
    list_filter = ['google_calendar_connected']
    search_fields = ['user__username', 'user__email']


class SystemSettingsAdminForm(forms.ModelForm):
    """Custom form for SystemSettings with password field for API key."""
    
    class Meta:
        model = SystemSettings
        fields = '__all__'
        widgets = {
            'llm_api_key': forms.PasswordInput(render_value=True, attrs={
                'placeholder': 'Leave empty to use OPENAI_API_KEY from environment'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form and handle password field for existing instances."""
        super().__init__(*args, **kwargs)
        # If editing an existing instance, we need to handle the password field
        # Since it's a password field, we'll show a placeholder text
        if self.instance and self.instance.pk and self.instance.llm_api_key:
            # Don't show the actual value, but indicate it's set
            self.fields['llm_api_key'].widget.attrs['placeholder'] = 'Enter new API key or leave blank to keep current/use environment'
    
    def clean(self):
        """Ensure only one instance exists and handle password field."""
        cleaned_data = super().clean()
        
        # Ensure only one instance exists
        if SystemSettings.objects.exists():
            existing = SystemSettings.objects.first()
            # When creating a new instance, self.instance.pk will be None
            # When editing existing, self.instance.pk will match existing.id
            if self.instance.pk is None or (self.instance.pk != existing.pk):
                raise ValidationError('Only one SystemSettings instance is allowed.')
        
        # If editing and API key field is empty, preserve existing value
        if self.instance and self.instance.pk:
            if not cleaned_data.get('llm_api_key'):
                # User left the field blank, keep the existing value
                cleaned_data['llm_api_key'] = self.instance.llm_api_key
        
        return cleaned_data


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    form = SystemSettingsAdminForm
    
    list_display = ['llm_provider', 'llm_model', 'updated_at']
    fields = ['llm_provider', 'llm_model', 'llm_api_key']
    
    def has_add_permission(self, request):
        """Prevent adding multiple instances."""
        if SystemSettings.objects.exists():
            return False
        return super().has_add_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting the singleton instance."""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Redirect to the singleton instance if it exists."""
        if SystemSettings.objects.exists():
            obj = SystemSettings.objects.first()
            return self.changeform_view(request, object_id=str(obj.id), extra_context=extra_context)
        return super().changelist_view(request, extra_context)


@admin.register(LLMParsingLog)
class LLMParsingLogAdmin(admin.ModelAdmin):
    """Admin interface for LLM parsing logs."""
    
    list_display = ['created_at', 'user', 'success_badge', 'llm_provider', 'llm_model', 'response_time_display', 'error_type']
    list_filter = ['success', 'error_type', 'llm_provider', 'llm_model', 'created_at']
    search_fields = ['input_text', 'error_message', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'user', 'input_text', 'input_text_length', 'llm_provider', 
                       'llm_model', 'success', 'response_time_ms', 'error_type', 'error_message', 
                       'parsed_data_display']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('created_at', 'user', 'input_text', 'input_text_length')
        }),
        ('LLM Configuration', {
            'fields': ('llm_provider', 'llm_model')
        }),
        ('Results', {
            'fields': ('success', 'response_time_ms', 'error_type', 'error_message', 'parsed_data_display')
        }),
    )
    
    def success_badge(self, obj):
        """Display success status with color coding."""
        if obj.success:
            return format_html('<span style="color: green; font-weight: bold;">✓ Success</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">✗ Failed</span>')
    success_badge.short_description = 'Status'
    
    def response_time_display(self, obj):
        """Display response time in a readable format."""
        if obj.response_time_ms:
            if obj.response_time_ms < 1000:
                return f"{obj.response_time_ms:.0f} ms"
            else:
                return f"{obj.response_time_ms / 1000:.2f} s"
        return "-"
    response_time_display.short_description = 'Response Time'
    
    def parsed_data_display(self, obj):
        """Display parsed data in a readable format."""
        if obj.parsed_data:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.parsed_data, indent=2))
        return "-"
    parsed_data_display.short_description = 'Parsed Data'
    
    def has_add_permission(self, request):
        """Prevent manual addition of logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of logs."""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Add analytics link to changelist."""
        extra_context = extra_context or {}
        extra_context['show_analytics_link'] = True
        return super().changelist_view(request, extra_context)
    
    def get_urls(self):
        """Add custom analytics URL."""
        urls = super().get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        custom_urls = [
            path('analytics/', self.admin_site.admin_view(self.analytics_view), name='%s_%s_analytics' % info),
        ]
        return custom_urls + urls
    
    def analytics_view(self, request):
        """Display analytics dashboard."""
        from django.contrib.admin.views.decorators import staff_member_required
        
        if not request.user.is_staff:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        days = int(request.GET.get('days', 30))
        analytics = LLMParsingLog.get_analytics(days=days)
        
        context = {
            **self.admin_site.each_context(request),
            'title': 'LLM Parsing Analytics',
            'analytics': analytics,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        
        return render(request, 'admin/accounts/llmparsinglog/analytics.html', context)
