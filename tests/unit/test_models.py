"""Unit tests for Event model."""

import pytest
from datetime import datetime
from pydantic import ValidationError
from events_agent.models.event import Event, EventSource


def test_event_creation_valid():
    """Test creating a valid event with minimal required fields."""
    event = Event(
        event_id="test-123",
        source=EventSource.LUMA,
        url="https://luma.com/event/test-123",
        title="Test Event",
        start_datetime=datetime(2026, 2, 5, 18, 0),
    )

    assert event.event_id == "test-123"
    assert event.source == EventSource.LUMA
    assert event.title == "Test Event"
    assert event.is_free is True  # Default
    assert event.currency == "USD"  # Default
    assert event.is_online is False  # Default


def test_event_creation_full():
    """Test creating an event with all fields populated."""
    event = Event(
        event_id="test-456",
        source=EventSource.MEETUP,
        url="https://meetup.com/events/test-456",
        title="Python Meetup",
        description="Monthly Python meetup",
        start_datetime=datetime(2026, 2, 5, 18, 0),
        end_datetime=datetime(2026, 2, 5, 20, 0),
        location_name="Tech Hub",
        location_address="123 Main St",
        city="New York",
        state="NY",
        is_online=False,
        attendee_count=50,
        capacity=100,
        spots_remaining=50,
        price_cents=1000,
        currency="USD",
        is_free=False,
        organizer_name="NYC Python",
        organizer_url="https://meetup.com/nyc-python",
    )

    assert event.title == "Python Meetup"
    assert event.city == "New York"
    assert event.attendee_count == 50
    assert event.price_cents == 1000
    assert event.is_free is False


def test_event_end_before_start_fails():
    """Test that end_datetime before start_datetime raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        Event(
            event_id="test-123",
            source=EventSource.LUMA,
            url="https://luma.com/event/test-123",
            title="Test Event",
            start_datetime=datetime(2026, 2, 5, 18, 0),
            end_datetime=datetime(2026, 2, 5, 17, 0),  # Before start!
        )

    assert "end_datetime must be after start_datetime" in str(exc_info.value)


def test_event_missing_required_fields():
    """Test that missing required fields raises validation error."""
    with pytest.raises(ValidationError):
        Event(
            # Missing event_id, source, url, title, start_datetime
            event_id="test-123",
        )


def test_event_invalid_url():
    """Test that invalid URL raises validation error."""
    with pytest.raises(ValidationError):
        Event(
            event_id="test-123",
            source=EventSource.LUMA,
            url="not-a-valid-url",
            title="Test Event",
            start_datetime=datetime(2026, 2, 5, 18, 0),
        )


def test_event_empty_title_fails():
    """Test that empty title raises validation error."""
    with pytest.raises(ValidationError):
        Event(
            event_id="test-123",
            source=EventSource.LUMA,
            url="https://luma.com/event/test-123",
            title="",  # Empty title
            start_datetime=datetime(2026, 2, 5, 18, 0),
        )


def test_event_negative_attendee_count_fails():
    """Test that negative attendee count raises validation error."""
    with pytest.raises(ValidationError):
        Event(
            event_id="test-123",
            source=EventSource.LUMA,
            url="https://luma.com/event/test-123",
            title="Test Event",
            start_datetime=datetime(2026, 2, 5, 18, 0),
            attendee_count=-5,  # Negative count
        )


def test_event_source_enum():
    """Test EventSource enum values."""
    assert EventSource.LUMA.value == "luma"
    assert EventSource.MEETUP.value == "meetup"


def test_event_model_dump():
    """Test that Event can be serialized to dict."""
    event = Event(
        event_id="test-123",
        source=EventSource.LUMA,
        url="https://luma.com/event/test-123",
        title="Test Event",
        start_datetime=datetime(2026, 2, 5, 18, 0),
    )

    data = event.model_dump()
    assert isinstance(data, dict)
    assert data['event_id'] == "test-123"
    assert data['source'] == EventSource.LUMA
    assert data['title'] == "Test Event"
