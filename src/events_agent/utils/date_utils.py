"""Date parsing and formatting utilities."""

from datetime import datetime
from typing import Optional


def parse_iso_datetime(date_string: str) -> Optional[datetime]:
    """
    Parse ISO 8601 datetime string.

    Handles common variations:
    - 2026-02-05T18:00:00Z
    - 2026-02-05T18:00:00+00:00
    - 2026-02-05T18:00:00.123Z

    Args:
        date_string: ISO 8601 formatted datetime string

    Returns:
        datetime object or None if parsing fails
    """
    if not date_string:
        return None

    try:
        # Replace Z with +00:00 for fromisoformat compatibility
        normalized = date_string.replace('Z', '+00:00')
        return datetime.fromisoformat(normalized)
    except (ValueError, AttributeError):
        return None


def format_event_date(dt: datetime) -> str:
    """
    Format datetime for display.

    Args:
        dt: datetime object

    Returns:
        Formatted string like "Mon, Feb 05, 2026 at 06:00 PM"
    """
    return dt.strftime("%a, %b %d, %Y at %I:%M %p")


def to_naive_datetime(dt: datetime) -> datetime:
    """
    Convert timezone-aware datetime to naive for comparison.

    Args:
        dt: datetime object (aware or naive)

    Returns:
        Naive datetime object
    """
    return dt.replace(tzinfo=None) if dt.tzinfo else dt
