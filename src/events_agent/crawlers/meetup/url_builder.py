"""URL building utilities for Meetup crawler."""

from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode


class MeetupURLBuilder:
    """Builds Meetup search URLs with filters."""

    @staticmethod
    def build_events_url(
        location: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        distance_miles: int = 10,
        event_type: Optional[str] = None
    ) -> tuple[str, datetime, datetime]:
        """
        Build Meetup URL with filters using correct format.

        Args:
            location: Location string (e.g., "New York, NY" → "us--ny--new-york")
            start_date: Start date filter with timezone
            end_date: End date filter with timezone
            distance_miles: Search radius in miles (default: 10)
            event_type: "inPerson", "online", or "all" (default: None)

        Returns:
            Tuple of (URL string, start_date, end_date)
        """
        # Set default date range
        start = start_date or datetime.now()
        end = end_date or (start + timedelta(days=14))

        # Convert location to Meetup format: "New York, NY" → "us--ny--new-york"
        location_formatted = MeetupURLBuilder._format_location(location)

        # Format dates with timezone (EST/EDT = -05:00)
        start_str = start.strftime("%Y-%m-%dT%H:%M:%S-05:00")
        end_str = end.strftime("%Y-%m-%dT%H:%M:%S-05:00")

        # Build query parameters with correct format
        params = {
            "location": location_formatted,
            "source": "EVENTS",
            "customStartDate": start_str,
            "customEndDate": end_str,
            "distance": "tenMiles" if distance_miles == 10 else f"{distance_miles}Miles"
        }

        # Add event type filter if specified
        if event_type and event_type != "all":
            params["eventType"] = event_type

        # Build URL
        base_url = "https://www.meetup.com/find/"
        query_string = urlencode(params)

        return f"{base_url}?{query_string}", start, end

    @staticmethod
    def _format_location(location: str) -> str:
        """
        Convert location string to Meetup format.

        Examples:
            "New York, NY" → "us--ny--new-york"
            "NYC" → "us--ny--new-york"

        Args:
            location: Raw location string

        Returns:
            Formatted location for Meetup URL
        """
        location_lower = location.lower().replace(" ", "-").replace(",", "")

        # Handle NYC variations
        if "new-york" in location_lower or "nyc" in location_lower:
            return "us--ny--new-york"

        # For other locations, return as-is (simple conversion)
        return location_lower
