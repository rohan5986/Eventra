"""
LLM service for parsing unstructured text into structured event data.
"""
import json
import os
import time
from datetime import datetime
from typing import Dict, Optional
from decouple import config
from openai import OpenAI


class LLMEventParser:
    """Service to parse unstructured text into structured event JSON using LLM."""
    
    def __init__(self):
        """Initialize the LLM client.
        
        Reads configuration from SystemSettings model in the database,
        falling back to environment variables for backward compatibility.
        """
        # Try to get settings from database first
        try:
            from accounts.models import SystemSettings
            settings = SystemSettings.get_settings()
            api_key = settings.get_api_key()
            self.model = settings.llm_model
            self.provider = settings.llm_provider
        except Exception:
            # Fallback to environment variables if database settings not available
            api_key = config('OPENAI_API_KEY', default='')
            self.model = config('LLM_MODEL', default='gpt-4')
            self.provider = 'openai'
        
        if not api_key:
            raise ValueError(
                "LLM API key not found. Please configure it in Admin > System Settings "
                "or set OPENAI_API_KEY in environment variables."
            )
        
        # Currently only OpenAI is supported, but this can be extended
        if self.provider == 'openai':
            self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def parse_text_to_event(self, text: str, user=None) -> Dict:
        """
        Parse unstructured text into structured event data.
        
        Args:
            text: Unstructured text input from user
            user: Optional User object for logging purposes
            
        Returns:
            Dictionary with event fields: title, description, location, start, end, guest_emails
        """
        # Start timing
        start_time = time.time()
        
        # Get today's date to help the LLM default to today when no date is specified
        today = datetime.now().strftime('%Y-%m-%d')
        today_readable = datetime.now().strftime('%B %d, %Y')
        
        prompt = f"""Parse the following text into a calendar event. Extract:
- title: Event title/summary
- description: If the text contains a URL/link (http:// or https://), put that link in the description. Otherwise, leave description as an empty string.
- location: Event location (if available)
- start: Start date and time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
- end: End date and time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
- guest_emails: If the text contains email addresses, extract them as a comma-separated string (e.g., "email1@example.com, email2@example.com"). If no emails are found, use an empty string.

IMPORTANT RULES:
1. If no date is specified (e.g., "gym at 9pm"), use TODAY'S DATE ({today_readable}, which is {today}).
2. If a time is specified but no date, assume the date is today.
3. If no time is specified, assume a 1-hour duration starting at a reasonable time (e.g., 9:00 AM if morning context, 2:00 PM if afternoon, etc.).
4. If the text contains any URLs/links (starting with http:// or https://), include them in the description field.
5. If the text contains email addresses, extract them and put them in the guest_emails field as a comma-separated string.
6. If no description content exists (no links), description should be an empty string "".

Text to parse:
{text}

Return ONLY a valid JSON object with these exact fields:
{{
    "title": "...",
    "description": "...",
    "location": "...",
    "start": "YYYY-MM-DDTHH:MM:SS",
    "end": "YYYY-MM-DDTHH:MM:SS",
    "guest_emails": "..."
}}
"""
        
        # Prepare log entry
        log_data = {
            'user': user,
            'input_text': text,
            'input_text_length': len(text),
            'llm_provider': self.provider,
            'llm_model': self.model,
            'success': False,
            'response_time_ms': None,
            'error_type': None,
            'error_message': None,
            'parsed_data': None,
        }
        
        try:
            # Some models don't support custom temperature, so we'll omit it
            # and let the model use its default
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that parses text into structured calendar events. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response (handle markdown code blocks if present)
            if content.startswith("```"):
                # Remove markdown code block formatting
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1])
            
            event_data = json.loads(content)
            
            # Validate required fields
            required_fields = ['title', 'start', 'end']
            for field in required_fields:
                if field not in event_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure guest_emails field exists (default to empty string if not provided)
            if 'guest_emails' not in event_data:
                event_data['guest_emails'] = ''
            
            # Ensure description field exists (default to empty string if not provided)
            if 'description' not in event_data:
                event_data['description'] = ''
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Log success
            log_data.update({
                'success': True,
                'response_time_ms': response_time_ms,
                'parsed_data': event_data,
            })
            self._log_parsing_attempt(log_data)
            
            return event_data
            
        except json.JSONDecodeError as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Failed to parse LLM response as JSON: {e}"
            log_data.update({
                'response_time_ms': response_time_ms,
                'error_type': 'json_decode',
                'error_message': str(e),
            })
            self._log_parsing_attempt(log_data)
            raise ValueError(error_msg)
        except ValueError as e:
            # This includes validation errors
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            error_type = 'missing_field' if 'Missing required field' in error_msg else 'other'
            log_data.update({
                'response_time_ms': response_time_ms,
                'error_type': error_type,
                'error_message': error_msg,
            })
            self._log_parsing_attempt(log_data)
            raise
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Error parsing text with LLM: {e}"
            
            # Determine error type
            error_type = 'other'
            error_str = str(e).lower()
            if 'rate limit' in error_str or 'quota' in error_str:
                error_type = 'rate_limit'
            elif 'timeout' in error_str:
                error_type = 'timeout'
            elif 'auth' in error_str or 'api key' in error_str or 'unauthorized' in error_str:
                error_type = 'auth_error'
            elif 'api' in error_str:
                error_type = 'api_error'
            
            log_data.update({
                'response_time_ms': response_time_ms,
                'error_type': error_type,
                'error_message': error_msg,
            })
            self._log_parsing_attempt(log_data)
            raise ValueError(error_msg)
    
    def _log_parsing_attempt(self, log_data):
        """Log a parsing attempt to the database."""
        try:
            from accounts.models import LLMParsingLog
            LLMParsingLog.objects.create(**log_data)
        except Exception as e:
            # Don't fail the parsing if logging fails
            # Log to console in development
            import sys
            print(f"Warning: Failed to log parsing attempt: {e}", file=sys.stderr)

