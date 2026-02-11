"""Event data utilities and reference data.

This module contains reference data and utilities for event categorization,
venue lookups, and seasonal event detection.
"""

from events_agent.data.jazz_venues import (
    JazzVenue,
    NYC_JAZZ_VENUES,
    JAZZ_NEIGHBORHOODS,
    get_venue_by_name,
    get_venues_by_neighborhood,
    get_all_venue_names,
    get_venue_neighborhoods,
    is_known_jazz_venue,
)

from events_agent.data.seasonal_events import (
    SeasonalCategory,
    VALENTINES_KEYWORDS,
    VALENTINES_EVENT_TYPES,
    ROMANTIC_NEIGHBORHOODS,
    get_valentines_date_range,
    is_valentines_event,
    is_date_night_event,
    get_upcoming_seasonal_dates,
)

__all__ = [
    # Jazz venues
    "JazzVenue",
    "NYC_JAZZ_VENUES",
    "JAZZ_NEIGHBORHOODS",
    "get_venue_by_name",
    "get_venues_by_neighborhood",
    "get_all_venue_names",
    "get_venue_neighborhoods",
    "is_known_jazz_venue",
    # Seasonal events
    "SeasonalCategory",
    "VALENTINES_KEYWORDS",
    "VALENTINES_EVENT_TYPES",
    "ROMANTIC_NEIGHBORHOODS",
    "get_valentines_date_range",
    "is_valentines_event",
    "is_date_night_event",
    "get_upcoming_seasonal_dates",
]
