"""Event data transformation for Meetup crawler."""

from typing import Optional, Dict, Any
from datetime import datetime
import re

from events_agent.models.event import Event, EventSource
from events_agent.utils.date_utils import parse_iso_datetime
from .apollo_parser import ApolloParser


class EventTransformer:
    """Transforms raw Meetup data into Event objects."""

    def __init__(self, event_type: Optional[str] = None):
        """
        Initialize transformer.

        Args:
            event_type: Event type filter ("inPerson", "online", "all")
        """
        self.event_type = event_type

    def from_apollo_data(
        self,
        event_data: Dict[str, Any],
        apollo_state: Dict[str, Any]
    ) -> Optional[Event]:
        """
        Transform Meetup event data from Apollo state to Event model.

        Args:
            event_data: Raw Meetup event data from Apollo
            apollo_state: Full Apollo state for resolving references

        Returns:
            Event object or None if parsing fails
        """
        try:
            event_id = str(event_data.get('id', ''))
            if not event_id:
                return None

            # Get title
            title = event_data.get('title') or event_data.get('name') or f"Meetup Event {event_id}"

            # Parse datetime
            start_datetime = self._parse_datetime(event_data)
            if not start_datetime:
                return None

            # Resolve references
            venue = ApolloParser.resolve_reference(event_data.get('venue'), apollo_state)
            group = ApolloParser.resolve_reference(event_data.get('group'), apollo_state)

            # Extract location info
            location_name, location_address, city, state = self._extract_location(venue)

            # Determine if online
            event_type = event_data.get('eventType', '').upper()
            is_online = event_type in ('ONLINE', 'VIRTUAL')

            # Extract organizer info
            organizer_name, organizer_url = self._extract_organizer(group)

            # Build event URL
            event_url = self._build_event_url(event_data, event_id)

            # Get description
            description = event_data.get('description') or event_data.get('shortDescription')

            return Event(
                event_id=event_id,
                source=EventSource.MEETUP,
                url=event_url,
                title=title[:200] if title else f"Event {event_id}",
                description=description,
                start_datetime=start_datetime,
                location_name=location_name[:200] if location_name else None,
                location_address=location_address[:200] if location_address else None,
                city=city,
                state=state,
                is_online=is_online,
                attendee_count=event_data.get('going') or event_data.get('rsvpCount'),
                is_free=True,  # Most Meetup events are free
                organizer_name=organizer_name[:200] if organizer_name else None,
                organizer_url=organizer_url
            )

        except Exception as e:
            print(f"      Error parsing event {event_data.get('id', 'unknown')}: {e}")
            return None

    def from_dom_data(self, event_data: Dict[str, Any]) -> Optional[Event]:
        """
        Parse event from DOM-extracted data.

        Args:
            event_data: Event data extracted from DOM

        Returns:
            Event object or None if parsing fails
        """
        try:
            event_id = str(event_data.get('event_id', ''))
            title = event_data.get('title', '').strip()
            url = event_data.get('url', '')

            if not all([event_id, title, url]):
                return None

            # Parse datetime
            date_text = event_data.get('date_text', '')
            start_datetime = self._parse_datetime_from_text(date_text)

            if not start_datetime:
                return None

            # Create event
            return Event(
                event_id=event_id,
                source=EventSource.MEETUP,
                url=url,
                title=title[:200] if title else f"Meetup Event {event_id}",
                start_datetime=start_datetime,
                location_name=event_data.get('location', '')[:200] if event_data.get('location') else None,
                attendee_count=event_data.get('attendees') if event_data.get('attendees', 0) > 0 else None,
                is_online=(self.event_type == "online"),
                city="New York" if self.event_type == "inPerson" else None,
                state="NY" if self.event_type == "inPerson" else None
            )

        except Exception:
            return None

    def _parse_datetime(self, event_data: Dict[str, Any]) -> Optional[datetime]:
        """
        Parse datetime from Apollo event data.

        Tries multiple fields in order of preference.

        Args:
            event_data: Apollo event data

        Returns:
            Parsed datetime or None
        """
        # Try dateTime field first
        date_time = event_data.get('dateTime')
        if date_time:
            dt = parse_iso_datetime(date_time)
            if dt:
                return dt

        # Try alternative fields
        for field in ['time', 'startTime', 'eventTime']:
            if field in event_data:
                dt = parse_iso_datetime(str(event_data[field]))
                if dt:
                    return dt

        return None

    def _parse_datetime_from_text(self, date_text: str) -> Optional[datetime]:
        """
        Parse datetime from Meetup's text format.

        Example formats:
        - "Sun, Feb 1 · 5:00 PM EST"
        - "Mon, Feb 2 · 10:00 AM EST"
        - "Every Sun · Feb 1 · 3:00 PM EST"
        - ISO format with timezone: "2026-02-01T17:00:00-05:00[America/New_York]"

        Args:
            date_text: Date text string

        Returns:
            datetime object or None
        """
        if not date_text:
            return None

        # Try ISO format first (from datetime attribute)
        # Clean datetime - remove timezone name suffix like [America/New_York]
        clean_date_text = date_text.split('[')[0] if '[' in date_text else date_text
        dt = parse_iso_datetime(clean_date_text)
        if dt:
            return dt

        # Try text format: "Sun, Feb 1 · 5:00 PM EST"
        try:
            match = re.search(
                r'([A-Z][a-z]+),?\s+([A-Z][a-z]+)\s+(\d+)\s*·?\s*(\d+):(\d+)\s+(AM|PM)',
                date_text
            )

            if match:
                month_str = match.group(2)
                day = int(match.group(3))
                hour = int(match.group(4))
                minute = int(match.group(5))
                am_pm = match.group(6)

                # Convert to 24-hour format
                if am_pm == 'PM' and hour != 12:
                    hour += 12
                elif am_pm == 'AM' and hour == 12:
                    hour = 0

                # Map month name to number
                months = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
                    'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
                    'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }

                month = months.get(month_str)
                if not month:
                    return None

                # Assume current year or next year
                current_year = datetime.now().year
                current_month = datetime.now().month

                year = current_year
                if month < current_month:
                    year += 1

                return datetime(year, month, day, hour, minute)

        except Exception:
            pass

        return None

    def _extract_location(self, venue: Dict[str, Any]) -> tuple:
        """
        Extract location information from venue data.

        Args:
            venue: Venue data from Apollo state

        Returns:
            Tuple of (location_name, location_address, city, state)
        """
        if not venue:
            return None, None, None, None

        location_name = venue.get('name') or venue.get('title')
        location_address = venue.get('address') or venue.get('location')
        city = venue.get('city')
        state = venue.get('state')

        return location_name, location_address, city, state

    def _extract_organizer(self, group: Dict[str, Any]) -> tuple:
        """
        Extract organizer information from group data.

        Args:
            group: Group data from Apollo state

        Returns:
            Tuple of (organizer_name, organizer_url)
        """
        if not group:
            return None, None

        organizer_name = group.get('name') or group.get('title')
        url_name = group.get('urlname') or group.get('slug')

        organizer_url = None
        if url_name:
            organizer_url = f"https://www.meetup.com/{url_name}/"

        return organizer_name, organizer_url

    def _build_event_url(self, event_data: Dict[str, Any], event_id: str) -> str:
        """
        Build event URL from various sources.

        Args:
            event_data: Apollo event data
            event_id: Event ID

        Returns:
            Event URL string
        """
        event_url = event_data.get('eventUrl')
        if event_url:
            return event_url

        event_url = event_data.get('url')
        if event_url:
            return event_url

        return f"https://www.meetup.com/events/{event_id}/"
