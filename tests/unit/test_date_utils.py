"""Unit tests for date utilities."""

import pytest
from datetime import datetime
from events_agent.utils.date_utils import (
    parse_iso_datetime,
    parse_datetime_with_fallback,
    format_event_date,
)


def test_parse_iso_datetime_with_z():
    """Test parsing ISO datetime with Z suffix."""
    dt = parse_iso_datetime("2026-02-05T18:00:00Z")

    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 2
    assert dt.day == 5
    assert dt.hour == 18
    assert dt.minute == 0
    assert dt.second == 0


def test_parse_iso_datetime_with_offset():
    """Test parsing ISO datetime with timezone offset."""
    dt = parse_iso_datetime("2026-02-05T18:00:00+00:00")

    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 2
    assert dt.day == 5


def test_parse_iso_datetime_with_milliseconds():
    """Test parsing ISO datetime with milliseconds."""
    dt = parse_iso_datetime("2026-02-05T18:00:00.123Z")

    assert dt is not None
    assert dt.year == 2026
    assert dt.microsecond == 123000


def test_parse_iso_datetime_invalid():
    """Test parsing invalid datetime string returns None."""
    assert parse_iso_datetime("not-a-date") is None
    assert parse_iso_datetime("2026-13-45") is None
    assert parse_iso_datetime("") is None
    assert parse_iso_datetime(None) is None


def test_format_event_date():
    """Test formatting datetime for display."""
    dt = datetime(2026, 2, 5, 18, 30, 0)
    formatted = format_event_date(dt)

    # Expected format: "Thu, Feb 05, 2026 at 06:30 PM"
    assert "Feb" in formatted
    assert "2026" in formatted
    assert "06:30 PM" in formatted


def test_format_event_date_morning():
    """Test formatting morning time."""
    dt = datetime(2026, 2, 5, 9, 0, 0)
    formatted = format_event_date(dt)

    assert "09:00 AM" in formatted


def test_format_event_date_noon():
    """Test formatting noon time."""
    dt = datetime(2026, 2, 5, 12, 0, 0)
    formatted = format_event_date(dt)

    assert "12:00 PM" in formatted


def test_parse_datetime_with_fallback_iso():
    """Test parse_datetime_with_fallback with ISO format."""
    dt = parse_datetime_with_fallback("2026-02-05T18:00:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 2
    assert dt.day == 5
    assert dt.hour == 18


def test_parse_datetime_with_fallback_display_format():
    """Test parse_datetime_with_fallback with display format."""
    dt = parse_datetime_with_fallback("Feb 15, 2026 7:00 PM")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 2
    assert dt.day == 15
    assert dt.hour == 19


def test_parse_datetime_with_fallback_invalid():
    """Test parse_datetime_with_fallback returns None for invalid input."""
    assert parse_datetime_with_fallback("not-a-date") is None
    assert parse_datetime_with_fallback("") is None
    assert parse_datetime_with_fallback(None) is None
