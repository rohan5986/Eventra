from django.shortcuts import redirect, render
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from decouple import config
from events.services.google_calendar import GoogleCalendarService
from .forms import UserRegistrationForm, UserLoginForm


def signup(request):
    """User registration view."""
    # Allow access even if logged in (in case user wants to create another account)
    # But show a message if already logged in
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            from .models import UserProfile
            UserProfile.objects.create(user=user)
            
            # Auto-login the user
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, f'Welcome to Eventra, {username}!')
                return redirect('events:home')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


def user_login(request):
    """User login view."""
    # Allow access even if logged in (in case user wants to switch accounts)
    # But redirect after successful login if already logged in
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                
                # Redirect to next page if specified, otherwise check if calendar is connected
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                
                # Check if Google Calendar is connected and redirect accordingly
                from .models import UserProfile
                try:
                    profile = request.user.profile
                    if profile.google_calendar_connected:
                        return redirect('events:list_events')
                except UserProfile.DoesNotExist:
                    pass
                
                return redirect('events:home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    """User logout view."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('events:home')


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
