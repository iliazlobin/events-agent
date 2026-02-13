"""Date parsing and formatting utilities."""

import re
from datetime import datetime
from typing import Optional


def parse_datetime_with_fallback(date_string: Optional[str]) -> Optional[datetime]:
    """
    Parse datetime from various string formats with fallback.

    Tries ISO format first, then common display formats like:
    - "Feb 15, 2026 7:00 PM"
    - "Saturday, February 15 at 7:00 PM"
    - "2/15/2026 7:00 PM"

    Args:
        date_string: Date string in various formats

    Returns:
        datetime object or None if parsing fails
    """
    if not date_string or not str(date_string).strip():
        return None

    # Try ISO format first
    dt = parse_iso_datetime(str(date_string))
    if dt:
        return dt

    # Try common formats
    formats = [
        "%b %d, %Y %I:%M %p",  # Feb 15, 2026 7:00 PM
        "%B %d, %Y %I:%M %p",  # February 15, 2026 7:00 PM
        "%m/%d/%Y %I:%M %p",  # 2/15/2026 7:00 PM
        "%Y-%m-%d %H:%M:%S",  # 2026-02-15 19:00:00
        "%Y-%m-%d %H:%M",  # 2026-02-15 19:00
        "%b %d, %Y",  # Feb 15, 2026
        "%B %d, %Y",  # February 15, 2026
        "%m/%d/%Y",  # 2/15/2026
    ]

    for fmt in formats:
        try:
            return datetime.strptime(str(date_string).strip(), fmt)
        except ValueError:
            continue

    # Try formats without year (assume current year)
    formats_no_year = [
        ("%a, %b %d %I:%M %p", "%a, %b %d, %Y %I:%M %p"),  # Thu, Feb 12 7:00 pm
        ("%b %d %I:%M %p", "%b %d, %Y %I:%M %p"),  # Feb 12 7:00 pm
        ("%a, %b %d", "%a, %b %d, %Y"),  # Thu, Feb 12
        ("%b %d", "%b %d, %Y"),  # Feb 12
    ]

    current_year = datetime.now().year
    for fmt_without_year, fmt_with_year in formats_no_year:
        try:
            # Parse without year first to extract month/day
            temp_str = str(date_string).strip()
            # Try parsing and add current year
            parsed = datetime.strptime(temp_str, fmt_without_year)
            # Reconstruct with current year
            return parsed.replace(year=current_year)
        except ValueError:
            continue

    # Try extracting ISO-like pattern
    iso_match = re.search(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?", str(date_string))
    if iso_match:
        dt = parse_iso_datetime(iso_match.group(0).replace(" ", "T"))
        if dt:
            return dt

    return None


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
