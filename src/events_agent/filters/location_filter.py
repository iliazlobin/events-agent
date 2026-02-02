"""Location filtering for events."""

from typing import List
from events_agent.models.event import Event


class LocationFilter:
    """
    Filter events by location.

    Supports:
    - City name matching
    - State/region matching
    - Flexible string matching (case-insensitive, handles variations)
    """

    # NYC variations
    NYC_VARIATIONS = {
        'new york',
        'new york city',
        'nyc',
        'manhattan',
        'brooklyn',
        'queens',
        'bronx',
        'staten island',
    }

    @staticmethod
    def is_nyc_event(event: Event) -> bool:
        """
        Check if event is in NYC.

        Args:
            event: Event to check

        Returns:
            True if event is in NYC area
        """
        # Skip online events for location filtering
        if event.is_online:
            return False

        # Check city
        if event.city:
            city_lower = event.city.lower()
            if any(variation in city_lower for variation in LocationFilter.NYC_VARIATIONS):
                return True

        # Check address
        if event.location_address:
            address_lower = event.location_address.lower()
            if 'new york' in address_lower or 'ny' in address_lower:
                return True

        # Check state
        if event.state:
            state_upper = event.state.upper()
            # Only NY state + city match
            if state_upper == 'NY' and event.city:
                city_lower = event.city.lower()
                if any(variation in city_lower for variation in LocationFilter.NYC_VARIATIONS):
                    return True

        return False

    @staticmethod
    def filter_nyc_events(events: List[Event]) -> List[Event]:
        """
        Filter events to only NYC area.

        Args:
            events: List of events to filter

        Returns:
            List of events in NYC
        """
        return [e for e in events if LocationFilter.is_nyc_event(e)]

    @staticmethod
    def filter_by_city(events: List[Event], city: str) -> List[Event]:
        """
        Filter events by city name (case-insensitive).

        Args:
            events: List of events to filter
            city: City name to match

        Returns:
            Filtered events
        """
        city_lower = city.lower()
        return [e for e in events
                if e.city and city_lower in e.city.lower()]
