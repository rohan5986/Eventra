"""
Google Calendar API service for creating and managing calendar events.
"""
import os
from datetime import datetime, timezone as dt_timezone
from typing import Dict, Optional
from django.utils import timezone as django_timezone
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from decouple import config


class GoogleCalendarService:
    """Service to interact with Google Calendar API."""
    
    # OAuth2 scopes required for Calendar access
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self, credentials: Optional[Credentials] = None):
        """
        Initialize Google Calendar service.
        
        Args:
            credentials: OAuth2 credentials object. If None, will use stored credentials.
        """
        self.credentials = credentials
        self.service = None
        
        if credentials:
            self.service = build('calendar', 'v3', credentials=credentials)
    
    @classmethod
    def get_oauth_flow(cls, redirect_uri: str):
        """
        Create OAuth2 flow for Google Calendar authentication.
        
        Args:
            redirect_uri: The redirect URI registered in Google Cloud Console
            
        Returns:
            Flow object for OAuth2
        """
        client_id = config('GOOGLE_CALENDAR_CLIENT_ID', default='')
        client_secret = config('GOOGLE_CALENDAR_CLIENT_SECRET', default='')
        
        if not client_id or not client_secret:
            raise ValueError("Google Calendar OAuth credentials not configured")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=cls.SCOPES
        )
        flow.redirect_uri = redirect_uri
        return flow
    
    @classmethod
    def from_credentials_dict(cls, credentials_dict: Dict):
        """
        Create service instance from stored credentials dictionary.
        
        Args:
            credentials_dict: Dictionary containing token, refresh_token, etc.
            
        Returns:
            GoogleCalendarService instance
        """
        creds = Credentials.from_authorized_user_info(credentials_dict)
        
        # Refresh token if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
        
        return cls(credentials=creds)
    
    def create_event(self, event_data: Dict) -> Dict:
        """
        Create an event in Google Calendar.
        
        Args:
            event_data: Dictionary with event details:
                - summary: Event title
                - description: Event description
                - location: Event location
                - start: Start datetime (ISO format or dict with dateTime)
                - end: End datetime (ISO format or dict with dateTime)
                
        Returns:
            Created event object from Google Calendar API
        """
        if not self.service:
            raise ValueError("Google Calendar service not initialized. Authenticate first.")
        
        # Format event body for Google Calendar API
        event_body = {
            'summary': event_data.get('summary', 'Untitled Event'),
            'description': event_data.get('description', ''),
            'location': event_data.get('location', ''),
        }
        
        # Add color if specified
        if event_data.get('colorId'):
            event_body['colorId'] = event_data.get('colorId')
        
        # Add attendees if specified
        if event_data.get('attendees'):
            event_body['attendees'] = event_data.get('attendees')
        
        # Format start/end times
        def format_datetime(dt):
            """Convert datetime to Google Calendar API format."""
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            if isinstance(dt, datetime):
                return {
                    'dateTime': dt.isoformat(),
                    'timeZone': 'UTC'
                }
            return dt
        
        event_body['start'] = format_datetime(event_data.get('start'))
        event_body['end'] = format_datetime(event_data.get('end'))
        
        try:
            event = self.service.events().insert(
                calendarId='primary',
                body=event_body
            ).execute()
            
            return event
            
        except HttpError as error:
            raise Exception(f"Error creating Google Calendar event: {error}")
    
    def update_event(self, event_id: str, event_data: Dict) -> Dict:
        """
        Update an existing event in Google Calendar.
        
        Args:
            event_id: Google Calendar event ID
            event_data: Updated event data
            
        Returns:
            Updated event object
        """
        if not self.service:
            raise ValueError("Google Calendar service not initialized.")
        
        # Get existing event first
        try:
            event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            # Update fields
            event['summary'] = event_data.get('summary', event.get('summary', ''))
            event['description'] = event_data.get('description', event.get('description', ''))
            event['location'] = event_data.get('location', event.get('location', ''))
            
            # Update color if specified
            if 'colorId' in event_data:
                event['colorId'] = event_data.get('colorId')
            
            # Update attendees if specified
            if 'attendees' in event_data:
                event['attendees'] = event_data.get('attendees')
            
            # Update start/end times
            def format_datetime(dt):
                if isinstance(dt, str):
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                if isinstance(dt, datetime):
                    return {
                        'dateTime': dt.isoformat(),
                        'timeZone': 'UTC'
                    }
                return dt
            
            if 'start' in event_data:
                event['start'] = format_datetime(event_data['start'])
            if 'end' in event_data:
                event['end'] = format_datetime(event_data['end'])
            
            # Update event
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()
            
            return updated_event
            
        except HttpError as error:
            raise Exception(f"Error updating Google Calendar event: {error}")
    
    def delete_event(self, event_id: str):
        """
        Delete an event from Google Calendar.
        
        Args:
            event_id: Google Calendar event ID
        """
        if not self.service:
            raise ValueError("Google Calendar service not initialized.")
        
        try:
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
        except HttpError as error:
            raise Exception(f"Error deleting Google Calendar event: {error}")
    
    def get_events(self, time_min=None, time_max=None, max_results=250) -> list:
        """
        Fetch events from Google Calendar.
        
        Args:
            time_min: Lower bound (exclusive) for an event's end time (RFC3339 timestamp or datetime)
            time_max: Upper bound (exclusive) for an event's start time (RFC3339 timestamp or datetime)
            max_results: Maximum number of events to return (default 250)
            
        Returns:
            List of event objects from Google Calendar
        """
        if not self.service:
            raise ValueError("Google Calendar service not initialized. Authenticate first.")
        
        # Format datetime to RFC3339 if needed
        def format_rfc3339(dt):
            """Convert datetime to RFC3339 format for Google Calendar API."""
            if isinstance(dt, str):
                # If already a string, try to parse and reformat
                try:
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                except:
                    return dt  # Return as-is if can't parse
            if isinstance(dt, datetime):
                # Convert to UTC and format as RFC3339: YYYY-MM-DDTHH:MM:SSZ (no microseconds, no offset)
                # Google Calendar API expects UTC timezone
                if django_timezone.is_aware(dt):
                    # Convert to UTC
                    dt = dt.astimezone(dt_timezone.utc)
                elif django_timezone.is_naive(dt):
                    # If naive, assume it's already UTC
                    dt = dt.replace(tzinfo=dt_timezone.utc)
                # Format without microseconds
                return dt.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
            return dt
        
        time_min_formatted = format_rfc3339(time_min) if time_min else None
        time_max_formatted = format_rfc3339(time_max) if time_max else None
        
        try:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min_formatted,
                timeMax=time_max_formatted,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return events
            
        except HttpError as error:
            raise Exception(f"Error fetching Google Calendar events: {error}")
    
    def get_credentials_dict(self) -> Dict:
        """
        Get credentials as a dictionary for storage.
        
        Returns:
            Dictionary with token information
        """
        if not self.credentials:
            raise ValueError("No credentials available")
        
        return {
            'token': self.credentials.token,
            'refresh_token': self.credentials.refresh_token,
            'token_uri': self.credentials.token_uri,
            'client_id': self.credentials.client_id,
            'client_secret': self.credentials.client_secret,
            'scopes': self.credentials.scopes
        }

