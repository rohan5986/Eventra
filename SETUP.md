# Eventra Setup Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation Steps

1. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   - Create a `.env` file in the project root
   - Add your API keys:
     ```
     OPENAI_API_KEY=your-openai-api-key-here
     LLM_MODEL=gpt-4
     SECRET_KEY=your-secret-key-here
     ```

4. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser** (for admin access):
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

7. **Access the application**:
   - Main app: http://localhost:8000/events/
   - Admin panel: http://localhost:8000/admin/
   - Create event: http://localhost:8000/events/create/

## First User Story Implementation

The first user story is now implemented:

**"As a user, I want to enter unstructured text to automatically generate calendar events."**

### How it works:

1. Navigate to `/events/create/` (requires login)
2. Enter unstructured text like: "Lunch with Dr. Rivera on October 17th at 1pm at Harvard Square"
3. The LLM parses the text and extracts:
   - Event title
   - Date and time
   - Location
   - Description
4. Review the parsed event on the preview page
5. Edit if needed, then confirm to save

### API Requirements:

- **OpenAI API Key**: Required for LLM text parsing
  - Get one at: https://platform.openai.com/api-keys
  - Set in `.env` as `OPENAI_API_KEY`

## Next Steps

To continue development, you can work on:
- User Story #2: Automatic extraction of dates and times (partially done via LLM)
- User Story #3: View list of upcoming events (already implemented)
- User Story #4: Event locations on Google Map
- User Story #5: Edit event details before confirming (already implemented)
- Google Calendar API integration
- User authentication improvements


