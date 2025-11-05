from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from .forms import EventTextInputForm
from .models import Event
from .services.llm_parser import LLMEventParser
from .services.google_calendar import GoogleCalendarService


def home(request):
    """Home page - requires Google Calendar connection before accessing app."""
    # Require login first
    if not request.user.is_authenticated:
        return redirect(f'/admin/login/?next=/events/home/')
    
    # Check if Google Calendar is connected
    from accounts.models import UserProfile
    google_calendar_connected = False
    try:
        profile = request.user.profile
        google_calendar_connected = profile.google_calendar_connected
    except UserProfile.DoesNotExist:
        pass
    
    # If connected, redirect to events page
    if google_calendar_connected:
        return redirect('events:list_events')
    
    # Otherwise, show landing page with connect button
    return render(request, 'events/landing.html', {
        'google_calendar_connected': google_calendar_connected
    })


@login_required
def create_event_from_text(request):
    """
    View to handle user text input and generate calendar events.
    Implements User Story #1: Enter unstructured text to automatically generate calendar events.
    """
    # Require Google Calendar connection
    from accounts.models import UserProfile
    try:
        profile = request.user.profile
        if not profile.google_calendar_connected:
            messages.info(request, 'Please connect your Google Calendar to use Eventra.')
            return redirect('events:home')
    except UserProfile.DoesNotExist:
        messages.info(request, 'Please connect your Google Calendar to use Eventra.')
        return redirect('events:home')
    
    if request.method == 'POST':
        form = EventTextInputForm(request.POST)
        if form.is_valid():
            text_input = form.cleaned_data['text_input']
            
            try:
                # Parse text using LLM
                parser = LLMEventParser()
                event_data = parser.parse_text_to_event(text_input)
                
                # Convert ISO datetime strings to datetime objects
                start_dt = datetime.fromisoformat(event_data['start'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(event_data['end'].replace('Z', '+00:00'))
                
                # Make timezone-aware if needed
                if timezone.is_naive(start_dt):
                    start_dt = timezone.make_aware(start_dt)
                if timezone.is_naive(end_dt):
                    end_dt = timezone.make_aware(end_dt)
                
                # Store event in session for preview/edit before saving
                request.session['pending_event'] = {
                    'title': event_data.get('title', 'Untitled Event'),
                    'description': event_data.get('description', ''),
                    'location': event_data.get('location', ''),
                    'start_datetime': start_dt.isoformat(),
                    'end_datetime': end_dt.isoformat(),
                    'original_text': text_input,
                    'guest_emails': event_data.get('guest_emails', ''),
                    'color_id': event_data.get('color_id', '1'),  # Default color
                }
                
                # If user is not logged in, redirect to login first
                if not request.user.is_authenticated:
                    messages.info(request, 'Please log in to save your event.')
                    return redirect(f'/admin/login/?next=/events/preview/')
                
                return redirect('events:preview_event')
                
            except ValueError as e:
                messages.error(request, f'Error parsing event: {str(e)}')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred: {str(e)}')
    
    else:
        form = EventTextInputForm()
    
    return render(request, 'events/create_event.html', {'form': form})


@login_required
def preview_event(request):
    """Preview parsed event before saving."""
    # Require Google Calendar connection
    from accounts.models import UserProfile
    try:
        profile = request.user.profile
        if not profile.google_calendar_connected:
            messages.info(request, 'Please connect your Google Calendar to use Eventra.')
            return redirect('events:home')
    except UserProfile.DoesNotExist:
        messages.info(request, 'Please connect your Google Calendar to use Eventra.')
        return redirect('events:home')
    
    if 'pending_event' not in request.session:
        messages.warning(request, 'No pending event to preview.')
        return redirect('events:list_events')
    
    event_data = request.session['pending_event']
    
    if request.method == 'POST':
        # User confirmed - save the event
        if 'confirm' in request.POST:
            # Get edited values from form (or use defaults from session)
            edited_title = request.POST.get('title', event_data['title']).strip()
            edited_description = request.POST.get('description', event_data['description']).strip()
            edited_location = request.POST.get('location', event_data['location']).strip()
            edited_color_id = request.POST.get('color_id', event_data.get('color_id', '1')).strip()
            edited_guest_emails = request.POST.get('guest_emails', event_data.get('guest_emails', '')).strip()
            
            # Parse edited dates from datetime-local input
            start_datetime_str = request.POST.get('start_datetime')
            end_datetime_str = request.POST.get('end_datetime')
            
            try:
                # datetime-local returns format: YYYY-MM-DDTHH:mm (no timezone, assumed local)
                if start_datetime_str:
                    # Parse as naive datetime (assumed local timezone)
                    start_dt_naive = datetime.strptime(start_datetime_str, '%Y-%m-%dT%H:%M')
                    # Make aware in local timezone, then convert to UTC if needed
                    start_dt = timezone.make_aware(start_dt_naive)
                else:
                    # Fallback to original if not provided
                    start_dt = datetime.fromisoformat(event_data['start_datetime'])
                    if timezone.is_naive(start_dt):
                        start_dt = timezone.make_aware(start_dt)
                
                if end_datetime_str:
                    # Parse as naive datetime (assumed local timezone)
                    end_dt_naive = datetime.strptime(end_datetime_str, '%Y-%m-%dT%H:%M')
                    # Make aware in local timezone
                    end_dt = timezone.make_aware(end_dt_naive)
                else:
                    # Fallback to original if not provided
                    end_dt = datetime.fromisoformat(event_data['end_datetime'])
                    if timezone.is_naive(end_dt):
                        end_dt = timezone.make_aware(end_dt)
                
                # Validate that end is after start
                if end_dt <= start_dt:
                    messages.error(request, 'End date/time must be after start date/time.')
                    # Preserve user's edits in the form
                    event_data['title'] = edited_title
                    event_data['description'] = edited_description
                    event_data['location'] = edited_location
                    event_data['color_id'] = edited_color_id
                    event_data['guest_emails'] = edited_guest_emails
                    # Format dates for display (using edited values)
                    start_dt_local = timezone.localtime(start_dt)
                    end_dt_local = timezone.localtime(end_dt)
                    event_data['start_formatted'] = start_dt_local.strftime('%B %d, %Y at %I:%M %p')
                    event_data['end_formatted'] = end_dt_local.strftime('%B %d, %Y at %I:%M %p')
                    event_data['start_datetime_local'] = start_datetime_str if start_datetime_str else start_dt_local.strftime('%Y-%m-%dT%H:%M')
                    event_data['end_datetime_local'] = end_datetime_str if end_datetime_str else end_dt_local.strftime('%Y-%m-%dT%H:%M')
                    return render(request, 'events/preview_event.html', {'event_data': event_data})
                
            except ValueError as e:
                messages.error(request, f'Invalid date/time format: {str(e)}')
                # Preserve user's edits in the form
                event_data['title'] = request.POST.get('title', event_data['title']).strip()
                event_data['description'] = request.POST.get('description', event_data['description']).strip()
                event_data['location'] = request.POST.get('location', event_data['location']).strip()
                event_data['color_id'] = request.POST.get('color_id', event_data.get('color_id', '1')).strip()
                event_data['guest_emails'] = request.POST.get('guest_emails', event_data.get('guest_emails', '')).strip()
                # Re-format dates for display (fallback to original)
                start_dt_display = datetime.fromisoformat(event_data['start_datetime'])
                end_dt_display = datetime.fromisoformat(event_data['end_datetime'])
                if timezone.is_naive(start_dt_display):
                    start_dt_display = timezone.make_aware(start_dt_display)
                if timezone.is_naive(end_dt_display):
                    end_dt_display = timezone.make_aware(end_dt_display)
                start_dt_local = timezone.localtime(start_dt_display)
                end_dt_local = timezone.localtime(end_dt_display)
                event_data['start_formatted'] = start_dt_local.strftime('%B %d, %Y at %I:%M %p')
                event_data['end_formatted'] = end_dt_local.strftime('%B %d, %Y at %I:%M %p')
                event_data['start_datetime_local'] = start_datetime_str if start_datetime_str else start_dt_local.strftime('%Y-%m-%dT%H:%M')
                event_data['end_datetime_local'] = end_datetime_str if end_datetime_str else end_dt_local.strftime('%Y-%m-%dT%H:%M')
                return render(request, 'events/preview_event.html', {'event_data': event_data})
            
            event = Event.objects.create(
                user=request.user,
                title=edited_title,
                description=edited_description,
                location=edited_location,
                start_datetime=start_dt,
                end_datetime=end_dt,
                original_text=event_data['original_text'],
                color_id=edited_color_id if edited_color_id else None,
                guest_emails=edited_guest_emails if edited_guest_emails else None
            )
            
            # Sync to Google Calendar if connected
            try:
                from accounts.models import UserProfile
                try:
                    profile = request.user.profile
                except UserProfile.DoesNotExist:
                    profile = None
                
                if profile and profile.google_calendar_connected:
                    creds_dict = profile.get_credentials_dict()
                    if creds_dict:
                        service = GoogleCalendarService.from_credentials_dict(creds_dict)
                        
                        # Prepare attendees list from guest emails
                        attendees = []
                        if event.guest_emails:
                            email_list = [email.strip() for email in event.guest_emails.split(',') if email.strip()]
                            attendees = [{'email': email} for email in email_list]
                        
                        google_event = service.create_event({
                            'summary': event.title,
                            'description': event.description,
                            'location': event.location,
                            'start': event.start_datetime.isoformat(),
                            'end': event.end_datetime.isoformat(),
                            'colorId': event.color_id if event.color_id else '1',
                            'attendees': attendees,
                        })
                        event.google_calendar_event_id = google_event['id']
                        event.synced_to_google = True
                        event.save()
                        messages.success(request, f'Event "{event.title}" created and synced to Google Calendar!')
                    else:
                        messages.success(request, f'Event "{event.title}" created successfully!')
                else:
                    messages.success(request, f'Event "{event.title}" created successfully!')
            except Exception as e:
                # Event created locally even if Google sync fails
                messages.warning(request, f'Event created but Google Calendar sync failed: {str(e)}')
            
            del request.session['pending_event']
            return redirect('events:list_events')
        
        # User cancelled
        elif 'cancel' in request.POST:
            del request.session['pending_event']
            return redirect('events:create_event')
    
    # Format dates for display and datetime-local input
    start_dt = datetime.fromisoformat(event_data['start_datetime'])
    end_dt = datetime.fromisoformat(event_data['end_datetime'])
    
    # Make timezone-aware if needed
    if timezone.is_naive(start_dt):
        start_dt = timezone.make_aware(start_dt)
    if timezone.is_naive(end_dt):
        end_dt = timezone.make_aware(end_dt)
    
    # Convert to local timezone for display
    start_dt_local = timezone.localtime(start_dt)
    end_dt_local = timezone.localtime(end_dt)
    
    event_data['start_formatted'] = start_dt_local.strftime('%B %d, %Y at %I:%M %p')
    event_data['end_formatted'] = end_dt_local.strftime('%B %d, %Y at %I:%M %p')
    # Format for datetime-local input (YYYY-MM-DDTHH:mm)
    event_data['start_datetime_local'] = start_dt_local.strftime('%Y-%m-%dT%H:%M')
    event_data['end_datetime_local'] = end_dt_local.strftime('%Y-%m-%dT%H:%M')
    
    # Set default values for color and guest emails if not present
    if 'color_id' not in event_data:
        event_data['color_id'] = '1'
    if 'guest_emails' not in event_data:
        event_data['guest_emails'] = ''
    
    return render(request, 'events/preview_event.html', {'event_data': event_data})


@login_required
def list_events(request):
    """List all events for the logged-in user, including Google Calendar events if connected."""
    # Require Google Calendar connection
    from accounts.models import UserProfile
    google_calendar_connected = False
    try:
        profile = request.user.profile
        google_calendar_connected = profile.google_calendar_connected
    except UserProfile.DoesNotExist:
        pass
    
    # Redirect to home/landing if not connected
    if not google_calendar_connected:
        messages.info(request, 'Please connect your Google Calendar to use Eventra.')
        return redirect('events:home')
    
    # Filter events from today onwards and exclude events imported from Google Calendar
    now = timezone.now()
    events = Event.objects.filter(
        user=request.user,
        start_datetime__gte=now
    ).exclude(
        original_text__startswith='Imported from Google Calendar'
    ).order_by('start_datetime')
    
    # Check if Google Calendar is connected and fetch Google Calendar events
    from accounts.models import UserProfile
    google_calendar_events = []
    google_calendar_connected = False
    
    try:
        profile = request.user.profile
        google_calendar_connected = profile.google_calendar_connected
        
        # Fetch events from Google Calendar if connected
        if google_calendar_connected:
            try:
                creds_dict = profile.get_credentials_dict()
                if creds_dict:
                    service = GoogleCalendarService.from_credentials_dict(creds_dict)
                    # Get events from the past month to next 3 months
                    from datetime import timedelta
                    now = timezone.now()
                    # Format as UTC datetime objects for Google Calendar API
                    time_min = now - timedelta(days=30)
                    time_max = now + timedelta(days=90)
                    google_events = service.get_events(time_min=time_min, time_max=time_max)
                    
                    print(f"DEBUG: Fetched {len(google_events)} events from Google Calendar")
                    
                    # Get all Google Calendar event IDs that currently exist
                    google_event_ids = {g_event.get('id') for g_event in google_events if g_event.get('id')}
                    
                    # Check for Eventra events that were synced to Google Calendar but no longer exist there
                    synced_events = events.filter(synced_to_google=True).exclude(google_calendar_event_id__isnull=True)
                    for event in synced_events:
                        if event.google_calendar_event_id not in google_event_ids:
                            # Event was deleted from Google Calendar, delete it from Eventra too
                            print(f"DEBUG: Event '{event.title}' deleted from Google Calendar, removing from Eventra")
                            event.delete()
                    
                    # Update events list after deletions (apply filter to exclude imported Google Calendar events)
                    events = Event.objects.filter(
                        user=request.user,
                        start_datetime__gte=now
                    ).exclude(
                        original_text__startswith='Imported from Google Calendar'
                    ).order_by('start_datetime')
                    
                    # Convert Google Calendar events to a format compatible with our template
                    for g_event in google_events:
                        # Parse start/end times
                        start = g_event.get('start', {})
                        end = g_event.get('end', {})
                        
                        # Handle both dateTime and date formats
                        if 'dateTime' in start:
                            start_str = start['dateTime']
                        elif 'date' in start:
                            start_str = start['date'] + 'T00:00:00'
                        else:
                            continue
                        
                        if 'dateTime' in end:
                            end_str = end['dateTime']
                        elif 'date' in end:
                            end_str = end['date'] + 'T23:59:59'
                        else:
                            continue
                        
                        # Parse datetime strings
                        try:
                            start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                            end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                            if timezone.is_naive(start_dt):
                                start_dt = timezone.make_aware(start_dt)
                            if timezone.is_naive(end_dt):
                                end_dt = timezone.make_aware(end_dt)
                            
                            # Get color from Google Calendar event
                            color_id = g_event.get('colorId', '1')  # Default to colorId 1 if not specified
                            
                            # Map Google Calendar colorId to hex colors
                            # Google Calendar color palette (colorId 1-11)
                            color_map = {
                                '1': '#a4bdfc',  # Lavender
                                '2': '#7ae7bf',  # Sage
                                '3': '#dbadff',  # Grape
                                '4': '#ff887c',  # Flamingo
                                '5': '#fbd75b',  # Banana
                                '6': '#ffb878',  # Tangerine
                                '7': '#46d6db',  # Peacock
                                '8': '#e1e1e1',  # Graphite
                                '9': '#5484ed',  # Blueberry
                                '10': '#51b749',  # Basil
                                '11': '#dc2127',  # Tomato
                            }
                            
                            # Default Google Calendar blue if no colorId or invalid colorId
                            event_color = color_map.get(str(color_id), '#4285f4')
                            
                            google_calendar_events.append({
                                'title': g_event.get('summary', 'Untitled Event'),
                                'description': g_event.get('description', ''),
                                'location': g_event.get('location', ''),
                                'start_datetime': start_dt,
                                'end_datetime': end_dt,
                                'from_google': True,
                                'google_event_id': g_event.get('id', ''),
                                'color': event_color
                            })
                        except (ValueError, AttributeError):
                            # Skip events with invalid dates
                            continue
            except Exception as e:
                # Log error but don't break the page
                import traceback
                print(f"Error fetching Google Calendar events: {e}")
                print(traceback.format_exc())
                # Don't show error message to user - fail silently
    
    except UserProfile.DoesNotExist:
        pass
    
    # Combine Eventra events and Google Calendar events
    # Create a list of all events with a flag to indicate source
    all_events = []
    
    # Create a mapping of Google Calendar event IDs to their colors
    google_event_color_map = {}
    for g_event in google_calendar_events:
        google_event_id = g_event.get('google_event_id')
        if google_event_id:
            event_color = g_event.get('color', '#4285f4')
            google_event_color_map[google_event_id] = event_color
            print(f"DEBUG: Added color {event_color} for Google Calendar event ID {google_event_id}")
    
    print(f"DEBUG: Color map has {len(google_event_color_map)} entries")
    
    # Add Eventra events
    for event in events:
        # Check if this event is synced from Google Calendar and get its color
        event_color = None
        if event.synced_to_google and event.google_calendar_event_id:
            event_color = google_event_color_map.get(event.google_calendar_event_id)
            if event_color:
                print(f"DEBUG: Found color {event_color} for Eventra event {event.title} (GC ID: {event.google_calendar_event_id})")
            else:
                print(f"DEBUG: No color found for Eventra event {event.title} (GC ID: {event.google_calendar_event_id}) in color map")
        
        all_events.append({
            'title': event.title or '',
            'description': event.description or '',
            'location': event.location or '',
            'start_datetime': event.start_datetime,
            'end_datetime': event.end_datetime,
            'from_google': event.synced_to_google,
            'event_id': event.id,
            'color': event_color
        })
    
    # Add Google Calendar events to all_events for calendar view
    # Get Eventra events that are synced to Google Calendar to avoid duplicates
    eventra_google_ids = set(events.filter(synced_to_google=True).exclude(google_calendar_event_id__isnull=True).values_list('google_calendar_event_id', flat=True))
    print(f"DEBUG: Eventra Google Calendar IDs: {eventra_google_ids}")
    print(f"DEBUG: Google Calendar events to process: {len(google_calendar_events)}")
    
    # Get all Eventra events (including imported) to check for sync
    all_eventra_events = Event.objects.filter(user=request.user).exclude(google_calendar_event_id__isnull=True)
    all_eventra_google_ids = set(all_eventra_events.values_list('google_calendar_event_id', flat=True))
    
    for g_event in google_calendar_events:
        google_event_id = g_event.get('google_event_id')
        
        # Add ALL Google Calendar events to calendar view (all_events)
        # But skip if already in Eventra events list (to avoid duplicates)
        if google_event_id not in eventra_google_ids:
            all_events.append({
                'title': g_event.get('title', ''),
                'description': g_event.get('description', ''),
                'location': g_event.get('location', ''),
                'start_datetime': g_event.get('start_datetime'),
                'end_datetime': g_event.get('end_datetime'),
                'from_google': True,
                'event_id': None,  # Not in Eventra yet
                'color': g_event.get('color', '#4285f4')
            })
        
        # Only create Eventra event if it doesn't exist yet (for bidirectional sync)
        if google_event_id not in all_eventra_google_ids:
            try:
                event = Event.objects.create(
                    user=request.user,
                    title=g_event.get('title', 'Untitled Event'),
                    description=g_event.get('description', ''),
                    location=g_event.get('location', ''),
                    start_datetime=g_event.get('start_datetime'),
                    end_datetime=g_event.get('end_datetime'),
                    original_text=f"Imported from Google Calendar: {g_event.get('title', '')}",
                    google_calendar_event_id=google_event_id,
                    synced_to_google=True
                )
                print(f"DEBUG: Created Eventra event from Google Calendar: {g_event.get('title')}")
            except Exception as e:
                print(f"DEBUG: Error creating event from Google Calendar: {e}")
        else:
            print(f"DEBUG: Google Calendar event already exists in Eventra: {g_event.get('title')} (ID: {google_event_id})")
    
    # Refresh events list after creating new events from Google Calendar
    # Apply the same filter to exclude imported Google Calendar events
    events = Event.objects.filter(
        user=request.user,
        start_datetime__gte=now
    ).exclude(
        original_text__startswith='Imported from Google Calendar'
    ).order_by('start_datetime')
    
    # Sort all events by start_datetime
    all_events.sort(key=lambda x: x['start_datetime'])
    
    print(f"DEBUG: Total events in all_events: {len(all_events)} (Eventra: {len(events)}, Google: {len(google_calendar_events)})")
    print(f"DEBUG: Eventra events in list view (filtered): {len(events)}")
    for event in events:
        print(f"DEBUG: Eventra event: {event.title} - original_text starts with: '{event.original_text[:50]}...'")
    
    return render(request, 'events/list_events.html', {
        'events': events,  # Keep original for list view - only Eventra-created events
        'all_events': all_events,  # Combined events for calendar view
        'google_calendar_connected': google_calendar_connected
    })


@login_required
def delete_event(request, event_id):
    """Delete an event, including from Google Calendar if synced."""
    # Require Google Calendar connection
    from accounts.models import UserProfile
    try:
        profile = request.user.profile
        if not profile.google_calendar_connected:
            messages.info(request, 'Please connect your Google Calendar to use Eventra.')
            return redirect('events:home')
    except UserProfile.DoesNotExist:
        messages.info(request, 'Please connect your Google Calendar to use Eventra.')
        return redirect('events:home')
    
    try:
        event = Event.objects.get(id=event_id, user=request.user)
    except Event.DoesNotExist:
        messages.error(request, 'Event not found.')
        return redirect('events:home')
    
    event_title = event.title
    google_calendar_event_id = event.google_calendar_event_id
    
    # Delete from Google Calendar if synced
    if event.synced_to_google and google_calendar_event_id:
        try:
            from accounts.models import UserProfile
            try:
                profile = request.user.profile
                if profile and profile.google_calendar_connected:
                    creds_dict = profile.get_credentials_dict()
                    if creds_dict:
                        service = GoogleCalendarService.from_credentials_dict(creds_dict)
                        service.delete_event(google_calendar_event_id)
                        messages.success(request, f'Event "{event_title}" deleted from Eventra and Google Calendar.')
                    else:
                        # Delete locally even if Google Calendar sync fails
                        event.delete()
                        messages.success(request, f'Event "{event_title}" deleted from Eventra.')
                else:
                    # Not connected to Google Calendar, just delete locally
                    event.delete()
                    messages.success(request, f'Event "{event_title}" deleted.')
            except UserProfile.DoesNotExist:
                # No profile, just delete locally
                event.delete()
                messages.success(request, f'Event "{event_title}" deleted.')
        except Exception as e:
            # Delete locally even if Google Calendar deletion fails
            print(f"Error deleting from Google Calendar: {e}")
            event.delete()
            messages.warning(request, f'Event "{event_title}" deleted from Eventra, but Google Calendar deletion failed.')
    else:
        # Not synced to Google Calendar, just delete locally
        event.delete()
        messages.success(request, f'Event "{event_title}" deleted.')
    
    return redirect('events:list_events')


@login_required
def edit_event(request, event_id):
    """Edit an existing event."""
    # Require Google Calendar connection
    from accounts.models import UserProfile
    try:
        profile = request.user.profile
        if not profile.google_calendar_connected:
            messages.info(request, 'Please connect your Google Calendar to use Eventra.')
            return redirect('events:home')
    except UserProfile.DoesNotExist:
        messages.info(request, 'Please connect your Google Calendar to use Eventra.')
        return redirect('events:home')
    
    try:
        event = Event.objects.get(id=event_id, user=request.user)
    except Event.DoesNotExist:
        messages.error(request, 'Event not found.')
        return redirect('events:home')
    
    if request.method == 'POST':
        # User confirmed - update the event
        if 'confirm' in request.POST:
            # Get edited values from form
            edited_title = request.POST.get('title', event.title).strip()
            edited_description = request.POST.get('description', event.description).strip()
            edited_location = request.POST.get('location', event.location).strip()
            edited_color_id = request.POST.get('color_id', event.color_id or '1').strip()
            edited_guest_emails = request.POST.get('guest_emails', event.guest_emails or '').strip()
            
            # Parse edited dates from datetime-local input
            start_datetime_str = request.POST.get('start_datetime')
            end_datetime_str = request.POST.get('end_datetime')
            
            try:
                # datetime-local returns format: YYYY-MM-DDTHH:mm (no timezone, assumed local)
                if start_datetime_str:
                    start_dt_naive = datetime.strptime(start_datetime_str, '%Y-%m-%dT%H:%M')
                    start_dt = timezone.make_aware(start_dt_naive)
                else:
                    start_dt = event.start_datetime
                
                if end_datetime_str:
                    end_dt_naive = datetime.strptime(end_datetime_str, '%Y-%m-%dT%H:%M')
                    end_dt = timezone.make_aware(end_dt_naive)
                else:
                    end_dt = event.end_datetime
                
                # Validate that end is after start
                if end_dt <= start_dt:
                    messages.error(request, 'End date/time must be after start date/time.')
                    # Re-render with errors
                    start_dt_local = timezone.localtime(start_dt)
                    end_dt_local = timezone.localtime(end_dt)
                    event_data = {
                        'title': edited_title,
                        'description': edited_description,
                        'location': edited_location,
                        'color_id': edited_color_id,
                        'guest_emails': edited_guest_emails,
                        'start_datetime_local': start_datetime_str if start_datetime_str else start_dt_local.strftime('%Y-%m-%dT%H:%M'),
                        'end_datetime_local': end_datetime_str if end_datetime_str else end_dt_local.strftime('%Y-%m-%dT%H:%M'),
                    }
                    return render(request, 'events/edit_event.html', {'event': event, 'event_data': event_data})
                
            except ValueError as e:
                messages.error(request, f'Invalid date/time format: {str(e)}')
                start_dt_local = timezone.localtime(event.start_datetime)
                end_dt_local = timezone.localtime(event.end_datetime)
                event_data = {
                    'title': request.POST.get('title', event.title).strip(),
                    'description': request.POST.get('description', event.description).strip(),
                    'location': request.POST.get('location', event.location).strip(),
                    'color_id': request.POST.get('color_id', event.color_id or '1').strip(),
                    'guest_emails': request.POST.get('guest_emails', event.guest_emails or '').strip(),
                    'start_datetime_local': start_datetime_str if start_datetime_str else start_dt_local.strftime('%Y-%m-%dT%H:%M'),
                    'end_datetime_local': end_datetime_str if end_datetime_str else end_dt_local.strftime('%Y-%m-%dT%H:%M'),
                }
                return render(request, 'events/edit_event.html', {'event': event, 'event_data': event_data})
            
            # Update event fields
            event.title = edited_title
            event.description = edited_description
            event.location = edited_location
            event.start_datetime = start_dt
            event.end_datetime = end_dt
            event.color_id = edited_color_id if edited_color_id else None
            event.guest_emails = edited_guest_emails if edited_guest_emails else None
            event.save()
            
            # Update Google Calendar if synced
            if event.synced_to_google and event.google_calendar_event_id:
                try:
                    from accounts.models import UserProfile
                    try:
                        profile = request.user.profile
                    except UserProfile.DoesNotExist:
                        profile = None
                    
                    if profile and profile.google_calendar_connected:
                        creds_dict = profile.get_credentials_dict()
                        if creds_dict:
                            service = GoogleCalendarService.from_credentials_dict(creds_dict)
                            
                            # Prepare attendees list from guest emails
                            attendees = []
                            if event.guest_emails:
                                email_list = [email.strip() for email in event.guest_emails.split(',') if email.strip()]
                                attendees = [{'email': email} for email in email_list]
                            
                            service.update_event(event.google_calendar_event_id, {
                                'summary': event.title,
                                'description': event.description,
                                'location': event.location,
                                'start': event.start_datetime.isoformat(),
                                'end': event.end_datetime.isoformat(),
                                'colorId': event.color_id if event.color_id else '1',
                                'attendees': attendees,
                            })
                            messages.success(request, f'Event "{event.title}" updated and synced to Google Calendar!')
                        else:
                            messages.success(request, f'Event "{event.title}" updated successfully!')
                    else:
                        messages.success(request, f'Event "{event.title}" updated successfully!')
                except Exception as e:
                    messages.warning(request, f'Event updated but Google Calendar sync failed: {str(e)}')
            else:
                messages.success(request, f'Event "{event.title}" updated successfully!')
            
            return redirect('events:list_events')
        
        # User cancelled
        elif 'cancel' in request.POST:
            return redirect('events:list_events')
    
    # Format dates for display and datetime-local input
    start_dt_local = timezone.localtime(event.start_datetime)
    end_dt_local = timezone.localtime(event.end_datetime)
    
    event_data = {
        'title': event.title,
        'description': event.description,
        'location': event.location,
        'color_id': event.color_id or '1',
        'guest_emails': event.guest_emails or '',
        'start_datetime_local': start_dt_local.strftime('%Y-%m-%dT%H:%M'),
        'end_datetime_local': end_dt_local.strftime('%Y-%m-%dT%H:%M'),
    }
    
    return render(request, 'events/edit_event.html', {'event': event, 'event_data': event_data})


@login_required
def search_events(request):
    """
    Search functionality for events.
    Implements User Story #8: As a user, I want search functionality for past and future events.
    """
    # Require Google Calendar connection
    from accounts.models import UserProfile
    google_calendar_connected = False
    try:
        profile = request.user.profile
        google_calendar_connected = profile.google_calendar_connected
    except UserProfile.DoesNotExist:
        pass
    
    # Redirect to home/landing if not connected
    if not google_calendar_connected:
        messages.info(request, 'Please connect your Google Calendar to use Eventra.')
        return redirect('events:home')
    
    # Get search parameters
    query = request.GET.get('q', '').strip()
    time_filter = request.GET.get('time', 'all')  # 'all', 'upcoming', 'past'
    
    # Start with all user events
    events = Event.objects.filter(user=request.user).exclude(
        original_text__startswith='Imported from Google Calendar'
    )
    
    # Apply time filter
    now = timezone.now()
    if time_filter == 'upcoming':
        events = events.filter(start_datetime__gte=now)
    elif time_filter == 'past':
        events = events.filter(start_datetime__lt=now)
    
    # Apply search query if provided
    if query:
        from django.db.models import Q
        events = events.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query)
        )
    
    # Order events
    if time_filter == 'past':
        events = events.order_by('-start_datetime')  # Most recent first for past events
    else:
        events = events.order_by('start_datetime')  # Chronological for upcoming/all
    
    # Fetch Google Calendar events if connected
    google_calendar_events = []
    if google_calendar_connected:
        try:
            creds_dict = profile.get_credentials_dict()
            if creds_dict:
                service = GoogleCalendarService.from_credentials_dict(creds_dict)
                from datetime import timedelta
                
                # Set time range based on filter
                if time_filter == 'past':
                    time_min = now - timedelta(days=365)  # Past year
                    time_max = now
                elif time_filter == 'upcoming':
                    time_min = now
                    time_max = now + timedelta(days=365)  # Next year
                else:
                    time_min = now - timedelta(days=365)
                    time_max = now + timedelta(days=365)
                
                google_events = service.get_events(time_min=time_min, time_max=time_max)
                
                # Color map for Google Calendar events
                color_map = {
                    '1': '#a4bdfc', '2': '#7ae7bf', '3': '#dbadff', '4': '#ff887c',
                    '5': '#fbd75b', '6': '#ffb878', '7': '#46d6db', '8': '#e1e1e1',
                    '9': '#5484ed', '10': '#51b749', '11': '#dc2127',
                }
                
                # Filter and process Google Calendar events
                for g_event in google_events:
                    start = g_event.get('start', {})
                    end = g_event.get('end', {})
                    
                    if 'dateTime' in start:
                        start_str = start['dateTime']
                    elif 'date' in start:
                        start_str = start['date'] + 'T00:00:00'
                    else:
                        continue
                    
                    if 'dateTime' in end:
                        end_str = end['dateTime']
                    elif 'date' in end:
                        end_str = end['date'] + 'T23:59:59'
                    else:
                        continue
                    
                    try:
                        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                        if timezone.is_naive(start_dt):
                            start_dt = timezone.make_aware(start_dt)
                        if timezone.is_naive(end_dt):
                            end_dt = timezone.make_aware(end_dt)
                        
                        title = g_event.get('summary', 'Untitled Event')
                        description = g_event.get('description', '')
                        location = g_event.get('location', '')
                        
                        # Apply search query to Google Calendar events
                        if query:
                            query_lower = query.lower()
                            if not (query_lower in title.lower() or 
                                   query_lower in description.lower() or 
                                   query_lower in location.lower()):
                                continue
                        
                        color_id = g_event.get('colorId', '1')
                        event_color = color_map.get(str(color_id), '#4285f4')
                        
                        google_calendar_events.append({
                            'title': title,
                            'description': description,
                            'location': location,
                            'start_datetime': start_dt,
                            'end_datetime': end_dt,
                            'from_google': True,
                            'google_event_id': g_event.get('id', ''),
                            'color': event_color
                        })
                    except (ValueError, AttributeError):
                        continue
                        
        except Exception as e:
            print(f"Error fetching Google Calendar events for search: {e}")
    
    # Combine results
    all_search_results = []
    
    # Add Eventra events
    for event in events:
        all_search_results.append({
            'title': event.title or '',
            'description': event.description or '',
            'location': event.location or '',
            'start_datetime': event.start_datetime,
            'end_datetime': event.end_datetime,
            'from_google': event.synced_to_google,
            'event_id': event.id,
            'is_past': event.start_datetime < now
        })
    
    # Add Google Calendar events (avoid duplicates)
    eventra_google_ids = set(events.filter(synced_to_google=True).exclude(
        google_calendar_event_id__isnull=True
    ).values_list('google_calendar_event_id', flat=True))
    
    for g_event in google_calendar_events:
        google_event_id = g_event.get('google_event_id')
        if google_event_id not in eventra_google_ids:
            all_search_results.append({
                'title': g_event.get('title', ''),
                'description': g_event.get('description', ''),
                'location': g_event.get('location', ''),
                'start_datetime': g_event.get('start_datetime'),
                'end_datetime': g_event.get('end_datetime'),
                'from_google': True,
                'event_id': None,
                'is_past': g_event.get('start_datetime') < now
            })
    
    # Sort results
    if time_filter == 'past':
        all_search_results.sort(key=lambda x: x['start_datetime'], reverse=True)
    else:
        all_search_results.sort(key=lambda x: x['start_datetime'])
    
    context = {
        'search_results': all_search_results,
        'query': query,
        'time_filter': time_filter,
        'google_calendar_connected': google_calendar_connected,
        'result_count': len(all_search_results)
    }
    
    return render(request, 'events/search_events.html', context)
