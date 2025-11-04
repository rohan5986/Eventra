# Google Calendar Integration Setup Guide

## Prerequisites

1. A Google Cloud Project
2. Google Calendar API enabled
3. OAuth 2.0 credentials configured

## Step-by-Step Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Calendar API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

### 2. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Configure the OAuth consent screen:
   - Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" (unless you have a Google Workspace)
   - Fill in required fields:
     - App name: "Eventra"
     - User support email: (your email)
     - Developer contact information: (your email)
   - Click "Save and Continue" through the Scopes page
   - On the "Test users" page, click "+ ADD USERS"
   - **IMPORTANT:** Add your Google account email address as a test user
   - Click "Save and Continue"
   
   **Note:** If you're in "Testing" mode (which you should be for development), you MUST add yourself as a test user, otherwise you'll get a 403 access_denied error!
4. Create OAuth 2.0 Client ID:
   - Application type: **Web application**
   - Name: "Eventra Calendar Integration"
   - Authorized redirect URIs:
     - `http://127.0.0.1:8000/accounts/google-calendar/callback/` (development - **use this**)
     - You can add production URLs later when you deploy (e.g., `https://yourdomain.com/accounts/google-calendar/callback/`)
   
   **Note:** The code normalizes to `127.0.0.1`, so make sure that's the redirect URI you register in Google Cloud Console.
5. Copy the **Client ID** and **Client Secret**

### 3. Configure Eventra

1. Update your `.env` file with the credentials:

```env
GOOGLE_CALENDAR_CLIENT_ID=699070549671-o7nnrt5hv4et753gm8qjqom9fvpnson1.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret-here
GOOGLE_CALENDAR_REDIRECT_URI=http://127.0.0.1:8000/accounts/google-calendar/callback/
```

### 4. Run Migrations

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

### 5. Connect Google Calendar

1. Start your Django server: `python manage.py runserver`
2. Log in to Eventra
3. Go to your events list: `http://localhost:8000/events/`
4. Click "Connect Google Calendar"
5. Authorize Eventra to access your calendar
6. You'll be redirected back to Eventra

### 6. Test Integration

1. Create a new event using text input
2. Confirm the event
3. Check your Google Calendar - the event should appear automatically!

## How It Works

- When you create an event in Eventra, it's automatically synced to your Google Calendar
- The event ID from Google Calendar is stored so updates/deletes can be synced later
- Your OAuth credentials are securely stored in the database (encrypted in production)

## Troubleshooting

### "Invalid OAuth state" error
- Clear your browser cookies/session and try again
- Make sure the redirect URI in Google Cloud Console matches exactly

### "Access denied" error
- Make sure you've added yourself as a test user in OAuth consent screen
- Check that the Google Calendar API is enabled

### Events not syncing
- Check that your credentials are valid in `.env`
- Verify the redirect URI matches exactly
- Check Django logs for error messages

### Refresh Token Issues
- Make sure `prompt='consent'` is used (already configured) to get a refresh token
- Re-authenticate if your refresh token expires

## Security Notes

- Never commit `.env` file to git
- Use environment variables in production
- Consider encrypting credentials in the database for production
- Regularly rotate OAuth credentials

