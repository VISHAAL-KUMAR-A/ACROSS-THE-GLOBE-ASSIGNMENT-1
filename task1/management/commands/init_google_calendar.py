from django.core.management.base import BaseCommand
from task1.google_calendar import get_calendar_service
from datetime import datetime


class Command(BaseCommand):
    help = 'Initialize Google Calendar authentication'

    def handle(self, *args, **options):
        self.stdout.write('Initializing Google Calendar authentication...')
        try:
            service = get_calendar_service()
            self.stdout.write(self.style.SUCCESS(
                'Successfully authenticated with Google Calendar!'))

            # Test by listing upcoming events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=datetime.utcnow().isoformat() + 'Z',
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            if not events:
                self.stdout.write('No upcoming events found.')
            else:
                self.stdout.write('Upcoming events:')
                for event in events:
                    start = event['start'].get(
                        'dateTime', event['start'].get('date'))
                    self.stdout.write(f"{start} - {event['summary']}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
