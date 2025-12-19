import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """Handles the authentication and returns the API service."""
    creds = None
    # 1. Check if we already have a valid token (from a previous login)
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # 2. If not, log in again
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # This opens the browser window for you to click "Allow"
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    # 3. Build the service
    service = build("calendar", "v3", credentials=creds)
    return service

def add_event_to_calendar(summary, start_time_iso, duration_minutes=60):
    """
    Adds an event to the primary calendar.
    start_time_iso needs to be in format: '2023-12-31T15:00:00'
    """
    service = get_calendar_service()

    # Calculate end time based on duration
    # We need to do a little parsing here just to add the hour
    from datetime import datetime, timedelta
    start_dt = datetime.fromisoformat(start_time_iso)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event = {
        "summary": summary,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "America/Guayaquil", # Change this to your timezone!
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "America/New_York",
        },
    }

    # The API Call
    event_result = service.events().insert(calendarId="primary", body=event).execute()
    return event_result.get("htmlLink")
