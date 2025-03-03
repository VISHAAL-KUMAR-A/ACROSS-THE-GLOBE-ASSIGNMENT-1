import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from django.conf import settings

# Path to token storage
TOKEN_PATH = os.path.join(settings.BASE_DIR, 'task1', 'google_token.json')
# Path to credentials file
CREDENTIALS_PATH = os.path.join(
    settings.BASE_DIR, 'acrosstheglobe', 'google_calendar_credentials.json')


def get_calendar_service():
    """Get an authorized Google Calendar API service instance."""
    creds = None

    # Load credentials from the saved file if it exists
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'r') as token:
            creds = Credentials.from_authorized_user_info(
                json.load(token),
                ['https://www.googleapis.com/auth/calendar']
            )

    # If there are no valid credentials, we need to authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Load client secrets from file
            flow = Flow.from_client_secrets_file(
                CREDENTIALS_PATH,
                scopes=['https://www.googleapis.com/auth/calendar'],
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )

            # Generate authorization URL
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(
                f'Please go to this URL and authorize the application: {auth_url}')

            # Get authorization code from user
            code = input('Enter the authorization code: ')

            # Exchange authorization code for access token
            flow.fetch_token(code=code)
            creds = flow.credentials

            # Save the credentials for the next run
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())

    # Build and return the service
    service = build('calendar', 'v3', credentials=creds)
    return service
