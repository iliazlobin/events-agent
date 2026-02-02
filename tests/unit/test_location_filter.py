"""Unit tests for LocationFilter."""

import pytest
from datetime import datetime
from events_agent.models.event import Event, EventSource
from events_agent.filters.location_filter import LocationFilter


def create_event(city=None, state=None, address=None, is_online=False):
    """Helper to create test events with location info."""
    return Event(
        event_id="test",
        source=EventSource.LUMA,
        url="https://test.com/event",
        title="Test Event",
        start_datetime=datetime.now(),
        city=city,
        state=state,
        location_address=address,
        is_online=is_online,
    )


def test_nyc_event_by_city_name():
    """Test NYC detection by various city name variations."""
    assert LocationFilter.is_nyc_event(create_event(city="New York")) is True
    assert LocationFilter.is_nyc_event(create_event(city="new york")) is True
    assert LocationFilter.is_nyc_event(create_event(city="NYC")) is True
    assert LocationFilter.is_nyc_event(create_event(city="nyc")) is True
    assert LocationFilter.is_nyc_event(create_event(city="Brooklyn")) is True
    assert LocationFilter.is_nyc_event(create_event(city="Manhattan")) is True
    assert LocationFilter.is_nyc_event(create_event(city="Queens")) is True
    assert LocationFilter.is_nyc_event(create_event(city="Bronx")) is True
    assert LocationFilter.is_nyc_event(create_event(city="Staten Island")) is True


def test_nyc_event_by_address():
    """Test NYC detection by address containing New York or NY."""
    assert LocationFilter.is_nyc_event(
        create_event(address="123 Broadway, New York, NY 10001")
    ) is True

    assert LocationFilter.is_nyc_event(
        create_event(address="456 Main St, Brooklyn, NY 11201")
    ) is True


def test_nyc_event_by_state_and_city():
    """Test NYC detection by state NY combined with city."""
    assert LocationFilter.is_nyc_event(
        create_event(city="Brooklyn", state="NY")
    ) is True

    assert LocationFilter.is_nyc_event(
        create_event(city="Manhattan", state="NY")
    ) is True


def test_non_nyc_event():
    """Test non-NYC events are correctly identified."""
    assert LocationFilter.is_nyc_event(create_event(city="Boston")) is False
    assert LocationFilter.is_nyc_event(create_event(city="San Francisco")) is False
    assert LocationFilter.is_nyc_event(create_event(city="Los Angeles")) is False
    assert LocationFilter.is_nyc_event(create_event(city="Chicago")) is False


def test_ny_state_but_not_nyc_city():
    """Test that NY state without NYC city name is not considered NYC."""
    # Albany is in NY state but not NYC
    assert LocationFilter.is_nyc_event(
        create_event(city="Albany", state="NY")
    ) is False

    # Buffalo is in NY state but not NYC
    assert LocationFilter.is_nyc_event(
        create_event(city="Buffalo", state="NY")
    ) is False


def test_online_event_excluded():
    """Test online events are excluded from location filtering."""
    assert LocationFilter.is_nyc_event(
        create_event(city="New York", is_online=True)
    ) is False

    assert LocationFilter.is_nyc_event(
        create_event(city="Brooklyn", state="NY", is_online=True)
    ) is False


def test_event_with_no_location_info():
    """Test event with no location info is not NYC."""
    assert LocationFilter.is_nyc_event(create_event()) is False


def test_filter_nyc_events():
    """Test filtering list of events for NYC only."""
    events = [
        create_event(city="New York"),
        create_event(city="Brooklyn"),
        create_event(city="Boston"),
        create_event(city="Manhattan"),
        create_event(city="San Francisco"),
        create_event(city="Queens"),
    ]

    nyc_events = LocationFilter.filter_nyc_events(events)

    assert len(nyc_events) == 4
    cities = [e.city for e in nyc_events]
    assert "New York" in cities
    assert "Brooklyn" in cities
    assert "Manhattan" in cities
    assert "Queens" in cities


def test_filter_empty_list():
    """Test filtering empty event list."""
    filtered = LocationFilter.filter_nyc_events([])
    assert filtered == []


def test_filter_by_city():
    """Test filtering by arbitrary city name."""
    events = [
        create_event(city="Boston"),
        create_event(city="New York"),
        create_event(city="Boston"),
        create_event(city="San Francisco"),
    ]

    boston_events = LocationFilter.filter_by_city(events, "Boston")

    assert len(boston_events) == 2
    assert all(e.city == "Boston" for e in boston_events)


def test_filter_by_city_case_insensitive():
    """Test that city filtering is case-insensitive."""
    events = [
        create_event(city="Boston"),
        create_event(city="BOSTON"),
        create_event(city="boston"),
    ]

    filtered = LocationFilter.filter_by_city(events, "boston")
    assert len(filtered) == 3

    filtered = LocationFilter.filter_by_city(events, "BOSTON")
    assert len(filtered) == 3
