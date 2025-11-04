from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from decouple import config
from events.services.google_calendar import GoogleCalendarService


@login_required
def google_calendar_connect(request):
    """Initiate Google Calendar OAuth flow."""
    redirect_uri = request.build_absolute_uri(reverse('accounts:google_calendar_callback'))
    
    # Normalize to 127.0.0.1 instead of localhost to match Google Console
    if 'localhost' in redirect_uri:
        redirect_uri = redirect_uri.replace('localhost', '127.0.0.1')
    
    try:
        flow = GoogleCalendarService.get_oauth_flow(redirect_uri)
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent to get refresh token
        )
        
        # Store state in session for security
        request.session['google_oauth_state'] = state
        
        return redirect(authorization_url)
        
    except ValueError as e:
        messages.error(request, f"Google Calendar not configured: {str(e)}")
        return redirect('events:home')
    except Exception as e:
        messages.error(request, f"Error connecting to Google Calendar: {str(e)}")
        return redirect('events:home')


@login_required
def google_calendar_callback(request):
    """Handle Google Calendar OAuth callback."""
    # Verify state
    state = request.session.get('google_oauth_state')
    if not state or state != request.GET.get('state'):
        messages.error(request, 'Invalid OAuth state. Please try again.')
        return redirect('events:list_events')
    
    # Get authorization code
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Authorization failed. Please try again.')
        return redirect('events:list_events')
    
    try:
        redirect_uri = request.build_absolute_uri(reverse('accounts:google_calendar_callback'))
        
        # Normalize to 127.0.0.1 instead of localhost to match Google Console
        if 'localhost' in redirect_uri:
            redirect_uri = redirect_uri.replace('localhost', '127.0.0.1')
        
        flow = GoogleCalendarService.get_oauth_flow(redirect_uri)
        flow.fetch_token(code=code)
        
        # Get credentials
        credentials = flow.credentials
        service = GoogleCalendarService(credentials=credentials)
        
        # Store credentials in user profile
        from accounts.models import UserProfile
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'user': request.user}
        )
        profile.set_credentials_dict(service.get_credentials_dict())
        
        messages.success(request, 'Successfully connected to Google Calendar!')
        return redirect('events:home')
        
    except Exception as e:
        messages.error(request, f"Error saving Google Calendar credentials: {str(e)}")
        return redirect('events:home')


@login_required
def google_calendar_disconnect(request):
    """Disconnect Google Calendar."""
    try:
        profile = getattr(request.user, 'profile', None)
        if profile:
            profile.set_credentials_dict(None)
            messages.success(request, 'Google Calendar disconnected successfully.')
        else:
            messages.info(request, 'Google Calendar was not connected.')
    except Exception as e:
        messages.error(request, f"Error disconnecting: {str(e)}")
    
    return redirect('events:home')
