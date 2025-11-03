# Eventra

**A Web-Based System for Transforming Unstructured Data into Calendar Events**

Jonathan Feldman, Rohan Singhal, Tanush Chintala, Abhishek Mynam, Nikunj Gupta

October 28, 2025

## Introduction

Managing personal and professional schedules increasingly involves parsing fragmented, unstructured information such as emails, messages, and notes. Traditional calendar applications require users to manually extract and input these details, creating cognitive overhead and inefficiency.

To address this gap, we introduce **Eventra**, a browser-based application that transforms natural language inputs into structured calendar entries. By combining the interpretive power of large language models with the event management and geolocation capabilities of Google APIs, Eventra enables automatic event creation and geographic visualization within a single, integrated platform.

## System Overview

Eventra operates as a web application that accepts free-form textual input from users and outputs structured calendar events. The system consists of three major components:

1. **Language Understanding**: A large language model (LLM) processes the user's input and extracts structured information such as event title, date, time, location, and description.
2. **Calendar Integration**: The extracted information is formatted into a JSON object and transmitted to the Google Calendar API, which creates an event automatically.
3. **Geolocation Visualization**: The Google Maps API displays the locations of upcoming events within an interactive map, allowing users to plan travel between commitments.

## API Integration

Eventra employs two distinct APIs to enhance its functionality:

### Google Calendar API

This API facilitates programmatic creation, updating, and deletion of events. Once the LLM outputs a JSON structure representing an event, the backend sends this object directly to the Calendar API endpoint.

```json
{
  "summary": "Lunch with Dr. Rivera",
  "start": "2025-10-17T13:00:00",
  "end": "2025-10-17T14:00:00",
  "location": "Harvard Square, Cambridge, MA",
  "description": "Research discussion."
}
```

### Google Maps API

To support spatial awareness, Eventra integrates the Google Maps API. Event coordinates or location strings are used to render markers on a dynamic map embedded in the user dashboard. This enables route planning and visualization of upcoming engagements.

## User Profiles

The system accommodates at least two user roles:

- **Registered User**: Can submit text inputs, view and edit parsed events, and visualize their schedule on an interactive map.
- **Administrator**: Oversees user management, monitors system performance, and can update API credentials or the LLM backend model.

## User Stories

Eventra's development is guided by the following twelve user stories, covering both functional and administrative perspectives:

1. As a user, I want to enter unstructured text to automatically generate calendar events.
2. As a user, I want automatic extraction of dates and times from natural language.
3. As a user, I want to view a list of upcoming events.
4. As a user, I want event locations visualized on an embedded Google Map.
5. As a user, I want to edit event details before confirming creation.
6. As a user, I want to delete or modify scheduled events.
7. As a user, I want confirmation messages for successfully created events.
8. As a user, I want search functionality for past and future events.
9. As an admin, I want to manage user accounts.
10. As an admin, I want analytics on LLM parsing accuracy and API response rates.
11. As an admin, I want to modify system parameters such as LLM choice or API tokens.
12. As a user, I want notifications for upcoming events, including directions via Google Maps.

## Workflow

The system workflow proceeds as follows:

```
User Input → LLM Parsing → JSON Structuring → Google Calendar API → Google Maps Visualization
```

This pipeline ensures that unstructured data is transformed into actionable calendar events with minimal manual effort.

## Primary Takeaway

Eventra demonstrates how LLMs can enhance productivity by automating the interpretation of human language and bridging it with practical scheduling tools. Through its integration with Google Calendar and Google Maps, the system provides a unified interface for time and location management. Future extensions may include voice-based input and support for collaborative scheduling.
