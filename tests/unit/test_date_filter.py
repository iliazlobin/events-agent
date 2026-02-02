"""Unit tests for DateFilter."""

import pytest
from datetime import datetime, timedelta
from events_agent.models.event import Event, EventSource
from events_agent.filters.date_filter import DateFilter


def create_test_event(start_datetime: datetime) -> Event:
    """Helper to create test events with specific start datetime."""
    return Event(
        event_id="test",
        source=EventSource.LUMA,
        url="https://test.com/event",
        title="Test Event",
        start_datetime=start_datetime,
    )


def test_current_week_range():
    """Test getting current week range."""
    start, end = DateFilter.get_current_week_range()

    # Start should be Monday 00:00:00
    assert start.weekday() == 0  # Monday
    assert start.hour == 0
    assert start.minute == 0
    assert start.second == 0

    # End should be Sunday 23:59:59
    assert end.weekday() == 6  # Sunday
    assert end.hour == 23
    assert end.minute == 59
    assert end.second == 59

    # End should be 6 days after start
    assert (end - start).days == 6


def test_next_week_range():
    """Test getting next week range."""
    current_start, _ = DateFilter.get_current_week_range()
    next_start, next_end = DateFilter.get_next_week_range()

    # Next week should start 7 days after current week
    assert (next_start - current_start).days == 7

    # Next week should also be Monday to Sunday
    assert next_start.weekday() == 0  # Monday
    assert next_end.weekday() == 6  # Sunday

    # Time should be properly set
    assert next_start.hour == 0
    assert next_end.hour == 23


def test_filter_current_and_next_week():
    """Test filtering events for current and next week."""
    current_start, _ = DateFilter.get_current_week_range()

    events = [
        create_test_event(current_start + timedelta(days=2)),   # This week (Wed)
        create_test_event(current_start + timedelta(days=9)),   # Next week (Wed)
        create_test_event(current_start + timedelta(days=20)),  # 3 weeks away
        create_test_event(current_start - timedelta(days=5)),   # Last week
        create_test_event(current_start),                        # Monday this week
        create_test_event(current_start + timedelta(days=13)),  # Sunday next week
    ]

    filtered = DateFilter.filter_current_and_next_week(events)

    # Should include events 0, 1, 4, 5 (current and next week)
    assert len(filtered) == 4

    # Verify the right events are included
    assert filtered[0].start_datetime == events[0].start_datetime
    assert filtered[1].start_datetime == events[1].start_datetime
    assert filtered[2].start_datetime == events[4].start_datetime
    assert filtered[3].start_datetime == events[5].start_datetime


def test_filter_empty_list():
    """Test filtering empty event list."""
    filtered = DateFilter.filter_current_and_next_week([])
    assert filtered == []


def test_filter_by_range():
    """Test filtering by custom date range."""
    start_range = datetime(2026, 2, 1, 0, 0)
    end_range = datetime(2026, 2, 10, 23, 59)

    events = [
        create_test_event(datetime(2026, 2, 5, 12, 0)),   # Within range
        create_test_event(datetime(2026, 2, 1, 0, 0)),    # Exactly at start
        create_test_event(datetime(2026, 2, 10, 23, 59)), # Exactly at end
        create_test_event(datetime(2026, 1, 31, 23, 59)), # Before range
        create_test_event(datetime(2026, 2, 11, 0, 0)),   # After range
    ]

    filtered = DateFilter.filter_by_range(events, start_range, end_range)

    # Should include first 3 events
    assert len(filtered) == 3


def test_filter_by_range_no_matches():
    """Test filtering when no events match the range."""
    start_range = datetime(2026, 3, 1, 0, 0)
    end_range = datetime(2026, 3, 10, 23, 59)

    events = [
        create_test_event(datetime(2026, 2, 5, 12, 0)),
        create_test_event(datetime(2026, 2, 10, 18, 0)),
    ]

    filtered = DateFilter.filter_by_range(events, start_range, end_range)
    assert len(filtered) == 0
