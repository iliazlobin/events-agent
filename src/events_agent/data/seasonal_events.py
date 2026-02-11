"""Valentine's Day and seasonal event categories and filters.

Provides data structures and utilities for finding holiday/seasonal events.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum


class SeasonalCategory(str, Enum):
    """Seasonal/holiday event categories."""
    VALENTINES_DAY = "valentines-day"
    CHRISTMAS = "christmas"
    NEW_YEARS = "new-years"
    HALLOWEEN = "halloween"
    THANKSGIVING = "thanksgiving"
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"


# Keywords for detecting Valentine's Day events
VALENTINES_KEYWORDS = [
    "valentine",
    "valentines",
    "valentine's",
    "romantic",
    "couples",
    "date night",
    "romance",
    "love",
    "sweetheart",
    "galentine",
    "singles",
    "anti-valentine",
]

# Event types popular for Valentine's Day
VALENTINES_EVENT_TYPES = [
    "dinner",
    "cooking class",
    "wine tasting",
    "cocktail class",
    "paint and sip",
    "comedy show",
    "jazz concert",
    "concert",
    "theater",
    "dance class",
    "pottery class",
    "spa",
    "cruise",
    "rooftop",
]


def get_valentines_date_range(year: int) -> tuple[datetime, datetime]:
    """
    Get date range for Valentine's Day events.
    
    Typically includes:
    - Valentine's Day weekend (Feb 14-16)
    - Week leading up to Valentine's Day (Feb 7-16)
    
    Args:
        year: Year to get date range for.
        
    Returns:
        Tuple of (start_date, end_date).
    """
    valentines_day = datetime(year, 2, 14)
    
    # Start 7 days before Valentine's Day
    start_date = valentines_day - timedelta(days=7)
    
    # End on the Sunday after Valentine's Day
    end_date = valentines_day + timedelta(days=(6 - valentines_day.weekday()) % 7 + 2)
    
    return (start_date, end_date)


def is_valentines_event(title: str, description: Optional[str] = None, tags: Optional[List[str]] = None) -> bool:
    """
    Check if an event is Valentine's Day related.
    
    Args:
        title: Event title.
        description: Event description.
        tags: Event tags/keywords.
        
    Returns:
        True if event is Valentine's related.
    """
    # Combine searchable text
    searchable = title.lower()
    if description:
        searchable += " " + description.lower()
    if tags:
        searchable += " " + " ".join(tags).lower()
    
    # Check for Valentine's keywords
    return any(keyword in searchable for keyword in VALENTINES_KEYWORDS)


def is_date_night_event(event_type: Optional[str], tags: Optional[List[str]] = None) -> bool:
    """
    Check if event type is suitable for date night/couples.
    
    Args:
        event_type: Event experience type.
        tags: Event tags.
        
    Returns:
        True if event is date-night appropriate.
    """
    if not event_type:
        return False
    
    event_type_lower = event_type.lower()
    
    # Check event type
    if any(vtype in event_type_lower for vtype in VALENTINES_EVENT_TYPES):
        return True
    
    # Check tags
    if tags:
        tags_str = " ".join(tags).lower()
        if any(vtype in tags_str for vtype in VALENTINES_EVENT_TYPES):
            return True
    
    return False


# Popular Valentine's Day venues/neighborhoods in NYC
ROMANTIC_NEIGHBORHOODS = [
    "Greenwich Village",
    "West Village",
    "SoHo",
    "Tribeca",
    "Chelsea",
    "Upper West Side",
    "Brooklyn Heights",
    "DUMBO",
    "Williamsburg",
    "Long Island City",  # Rooftop views
]


def get_upcoming_seasonal_dates() -> Dict[str, datetime]:
    """
    Get dates for upcoming seasonal events.
    
    Returns:
        Dictionary mapping seasonal category to date.
    """
    now = datetime.now()
    year = now.year
    
    dates = {
        SeasonalCategory.VALENTINES_DAY: datetime(year, 2, 14),
        SeasonalCategory.HALLOWEEN: datetime(year, 10, 31),
        SeasonalCategory.THANKSGIVING: _get_thanksgiving_date(year),
        SeasonalCategory.CHRISTMAS: datetime(year, 12, 25),
        SeasonalCategory.NEW_YEARS: datetime(year + 1, 1, 1),
    }
    
    # Return only future dates
    return {k: v for k, v in dates.items() if v > now}


def _get_thanksgiving_date(year: int) -> datetime:
    """Get Thanksgiving date (4th Thursday of November)."""
    nov_1 = datetime(year, 11, 1)
    # Find first Thursday
    first_thursday = nov_1 + timedelta(days=(3 - nov_1.weekday()) % 7)
    # Add 3 weeks for 4th Thursday
    return first_thursday + timedelta(weeks=3)
