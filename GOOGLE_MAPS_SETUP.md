# Google Maps API Setup Guide

## Overview

Eventra now includes interactive map visualization of your event locations! To enable this feature, you need to set up the Google Maps API.

## Features

- **Map View Tab**: See all your events with locations on an interactive map
- **Event Markers**: Each event appears as a colored marker on the map
- **Info Windows**: Click on markers to see event details (title, location, time)
- **Auto-fit Bounds**: Map automatically zooms to show all event locations
- **Geocoding**: Addresses are automatically converted to map coordinates

## Setup Instructions

### Step 1: Go to Google Cloud Console

1. Visit: **https://console.cloud.google.com/**
2. Sign in with your Google account
3. Select your existing project (e.g., "Eventra") or create a new one

### Step 2: Enable Required APIs

You need to enable **TWO APIs**:

#### A. Maps JavaScript API

1. In the left sidebar, go to **"APIs & Services"** → **"Library"**
2. Search for: **"Maps JavaScript API"**
3. Click on it and click **"ENABLE"**

#### B. Geocoding API

1. Still in the Library, search for: **"Geocoding API"**
2. Click on it and click **"ENABLE"**

### Step 3: Create API Key

1. In the left sidebar, go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** at the top
3. Select **"API key"**
4. An API key will be created and shown to you
5. **Copy the API key** - you'll need it in the next step

### Step 4: Restrict API Key (Recommended for Security)

1. Click on the newly created API key to edit it
2. Under **"API restrictions"**:
   - Select **"Restrict key"**
   - Choose **"Maps JavaScript API"** and **"Geocoding API"**
3. Under **"Application restrictions"** (optional):
   - For development: Choose **"None"**
   - For production: Choose **"HTTP referrers"** and add your domain
4. Click **"SAVE"**

### Step 5: Add API Key to Eventra

1. Open your `.env` file in the project root
2. Find the line: `GOOGLE_MAPS_API_KEY=your-google-maps-api-key-here`
3. Replace `your-google-maps-api-key-here` with your actual API key
4. Save the file

Example:
```env
GOOGLE_MAPS_API_KEY=AIzaSyAbc123Def456Ghi789Jkl012Mno345Pqr678
```

### Step 6: Restart the Server

1. Stop your Django server (if running)
2. Start it again: `python3 manage.py runserver`
3. Open the app: http://127.0.0.1:8000/

### Step 7: Test the Map

1. Go to your events list
2. Click the **"🗺️ Map View"** tab
3. You should see all your events with locations displayed on an interactive map!

## Troubleshooting

### "Google Maps Not Configured" message

**Solution**: Make sure you've added the API key to your `.env` file and restarted the server.

### No events showing on map

**Possible reasons:**
- Your events don't have location information
- The Geocoding API couldn't find coordinates for the addresses
- The Geocoding API is not enabled in your Google Cloud project

**Solution**: 
- Make sure your events have location data (e.g., "123 Main St, New York, NY")
- Check that both Maps JavaScript API AND Geocoding API are enabled
- Use specific addresses rather than vague locations

### "This page can't load Google Maps correctly" error

**Reasons:**
- Invalid API key
- APIs not enabled
- Billing not set up on Google Cloud (required for production use)

**Solution**:
- Verify your API key is correct in `.env`
- Make sure both required APIs are enabled
- For production use, enable billing in Google Cloud Console (Google provides $200/month free credit)

### Map shows but no markers appear

**Solution**: 
- Check browser console for errors (F12)
- Verify events have valid addresses
- Try adding more specific location information to events

## API Usage and Costs

### Free Tier

Google Maps provides a generous free tier:
- **$200 in free credit per month** (covers most development/small app usage)
- Maps JavaScript API: **28,000 map loads free per month**
- Geocoding API: **40,000 requests free per month**

### Cost Management

For a small-to-medium app like Eventra, you'll likely stay within the free tier. To manage costs:

1. **Cache geocoded coordinates**: Eventra automatically saves coordinates to the database after first geocoding, so addresses are only geocoded once
2. **Restrict API key**: Set API restrictions to prevent unauthorized use
3. **Set usage quotas**: In Google Cloud Console, you can set daily quotas to prevent unexpected charges

## Privacy Note

- The Google Maps API requires an API key, which is embedded in the frontend JavaScript
- For production, use HTTP referer restrictions to prevent unauthorized use
- No personal data is sent to Google Maps (only event titles and locations you choose to share)

## Next Steps

Once the map is working, you can:
- Create events with specific addresses to see them on the map
- Use the map to visualize your schedule geographically
- Plan your commute between events by seeing them all at once

## Support

If you run into issues:
1. Check the browser console (F12) for JavaScript errors
2. Check Django logs for geocoding errors
3. Verify your API key has the correct APIs enabled
4. Make sure billing is enabled in Google Cloud Console (required even for free tier)

Enjoy your new map visualization feature! 🗺️✨


