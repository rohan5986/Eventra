# User Story 8 Implementation

**User Story:** As a user, I want search functionality for past and future events.

## Features Implemented

### 1. Comprehensive Search
- **Text Search**: Search events by title, description, or location
- **Time Filtering**: Filter events by:
  - All Events (default)
  - Upcoming Events only
  - Past Events only

### 2. Search Capabilities
- Searches both **Eventra events** and **Google Calendar events**
- Case-insensitive search
- Real-time results
- Shows event count

### 3. User Interface
- Clean, modern search interface
- Search bar with instant submit
- Time filter dropdown
- Clear button to reset search
- Visual badges to distinguish:
  - Past vs Upcoming events
  - Google Calendar events
  - Eventra events

### 4. Results Display
- Events shown with all details (title, description, location, date/time)
- Past events shown with reduced opacity for visual distinction
- Edit and Delete actions for Eventra events
- Responsive layout

## How to Use

### Accessing Search
1. Navigate to the **My Events** page
2. Click the **🔍 Search Events** button at the top

### Searching for Events
1. Enter search terms in the search box (title, description, or location)
2. Select a time filter:
   - **All Events**: Shows both past and upcoming events
   - **Upcoming Events**: Shows only future events
   - **Past Events**: Shows only past events
3. Click **Search** or press Enter

### Search Tips
- Leave the search box empty to see all events in the selected time range
- Use partial words (e.g., "meet" will find "meeting")
- Search is case-insensitive
- Click **Clear** to reset all filters

## Technical Implementation

### Files Modified/Created
1. **`events/views.py`**: Added `search_events()` view
2. **`events/urls.py`**: Added search URL route
3. **`events/templates/events/search_events.html`**: New search results template
4. **`events/templates/events/list_events.html`**: Added search button

### Key Features
- Django ORM queries with `Q` objects for multi-field search
- Integration with Google Calendar API for unified search
- Duplicate prevention (events synced to Google Calendar)
- Smart sorting (chronological for upcoming, reverse for past)
- Time-aware filtering using Django's timezone utilities

## Example Queries

### Search Examples
- `"lunch"` - Finds all events with "lunch" in title, description, or location
- `"conference room"` - Finds events in conference rooms
- `"doctor"` - Finds doctor appointments

### Filter Combinations
- Search: `"meeting"`, Filter: `Upcoming Events` - Finds upcoming meetings only
- Search: (empty), Filter: `Past Events` - Shows all past events
- Search: `"Atlanta"`, Filter: `All Events` - Finds all events in Atlanta

## Benefits
- Quickly find specific events without scrolling
- Review past events for reference
- Filter future events for planning
- Search across both Eventra and Google Calendar
- Improved productivity and event management

