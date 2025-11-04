"""
LLM service for parsing unstructured text into structured event data.
"""
import json
import os
from datetime import datetime
from typing import Dict, Optional
from decouple import config
from openai import OpenAI


class LLMEventParser:
    """Service to parse unstructured text into structured event JSON using LLM."""
    
    def __init__(self):
        """Initialize the LLM client."""
        api_key = config('OPENAI_API_KEY', default='')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = config('LLM_MODEL', default='gpt-4')
    
    def parse_text_to_event(self, text: str) -> Dict:
        """
        Parse unstructured text into structured event data.
        
        Args:
            text: Unstructured text input from user
            
        Returns:
            Dictionary with event fields: title, description, location, start, end, guest_emails
        """
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
            
            return event_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing text with LLM: {e}")

