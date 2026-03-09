"""Event data model with Pydantic validation."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator
from enum import Enum


class EventSource(str, Enum):
    """Event source platform."""
    LUMA = "luma"
    MEETUP = "meetup"
    FEVER = "fever"
    EVENTBRITE = "eventbrite"
    COZYMEAL = "cozymeal"
    JAZZNEARYOU = "jazznearyou"
    SONGKICK = "songkick"
    TIMEOUT = "timeout"
    DONYC = "donyc"
    GARYSGUIDE = "garysguide"
    WINTERFEST = "winterfest"
    TOWNOFMAMMOTH = "townofmammoth"
    FUNCHEAP = "funcheap"
    SFTRAVEL = "sftravel"


class Event(BaseModel):
    """
    Structured event model with validation.

    All events from different sources are normalized to this schema.
    """
    # Core identifiers
    event_id: str = Field(..., description="Unique event ID from source platform")
    source: EventSource = Field(..., description="Platform source (luma/meetup)")
    url: HttpUrl = Field(..., description="Event page URL")

    # Event details
    title: str = Field(..., min_length=1, description="Event title")
    description: Optional[str] = Field(None, description="Event description")

    # Date and time
    start_datetime: datetime = Field(..., description="Event start time (UTC)")
    end_datetime: Optional[datetime] = Field(None, description="Event end time (UTC)")

    # Location
    location_name: Optional[str] = Field(None, description="Venue name")
    location_address: Optional[str] = Field(None, description="Full address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    is_online: bool = Field(False, description="Whether event is virtual")

    # Attendance
    attendee_count: Optional[int] = Field(None, ge=0, description="Number of attendees/RSVPs")
    capacity: Optional[int] = Field(None, ge=0, description="Max capacity")
    spots_remaining: Optional[int] = Field(None, ge=0, description="Available spots")
    waitlist: Optional[bool] = Field(None, description="Whether event has a waitlist")
    registration_closed: Optional[bool] = Field(None, description="Whether registration is closed")

    # Pricing
    price_cents: Optional[int] = Field(None, ge=0, description="Price in cents")
    min_price_cents: Optional[int] = Field(None, ge=0, description="Minimum price in cents (for price ranges)")
    max_price_cents: Optional[int] = Field(None, ge=0, description="Maximum price in cents (for price ranges)")
    currency: str = Field("USD", description="Currency code")
    is_free: bool = Field(True, description="Whether event is free")

    # Organizer/Group
    organizer_name: Optional[str] = Field(None, description="Group/organizer name")
    organizer_url: Optional[HttpUrl] = Field(None, description="Group/organizer profile URL")

    # Host (individual person)
    host_name: Optional[str] = Field(None, description="Event host name")
    host_bio: Optional[str] = Field(None, description="Host biography")

    # Group details (Meetup-specific)
    group_name: Optional[str] = Field(None, description="Meetup group name")
    group_rating: Optional[float] = Field(None, ge=0, le=5, description="Group rating (0-5)")
    group_review_count: Optional[int] = Field(None, ge=0, description="Number of group reviews")

    # Enhanced content
    ai_summary: Optional[str] = Field(None, description="AI-generated event summary")
    image_url: Optional[str] = Field(None, description="Main event image URL")
    topics: Optional[list[str]] = Field(None, description="Event topics/tags")

    # Experience type and categorization
    experience_type: Optional[str] = Field(None, description="Type: concert, magic, comedy, cooking, etc.")
    category: Optional[str] = Field(None, description="Event category or genre")
    tags: Optional[list[str]] = Field(None, description="Event tags/keywords")

    # Cooking class specific fields
    chef_name: Optional[str] = Field(None, description="Chef name for cooking classes")
    chef_rating: Optional[float] = Field(None, ge=0, le=5, description="Chef rating (0-5)")
    chef_bio: Optional[str] = Field(None, description="Chef biography")
    skill_level: Optional[str] = Field(None, description="Skill level: beginner/intermediate/advanced")
    cuisine_type: Optional[str] = Field(None, description="Cuisine type: Italian, French, etc.")

    # Performance specific fields (comedy, magic, concerts)
    performer_names: Optional[list[str]] = Field(None, description="List of performer names")
    genre: Optional[str] = Field(None, description="Performance genre")
    duration_minutes: Optional[int] = Field(None, ge=0, description="Event duration in minutes")

    # Enhanced rating (some aggregators have ratings)
    rating: Optional[float] = Field(None, ge=0, le=5, description="Event rating (0-5)")
    review_count: Optional[int] = Field(None, ge=0, description="Number of reviews")

    # Enhanced location
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Venue latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Venue longitude")
    directions: Optional[str] = Field(None, description="How to find the venue")

    # Enhanced pricing
    fee_amount: Optional[float] = Field(None, ge=0, description="Fee amount (if any)")
    fee_required: Optional[bool] = Field(None, description="Whether fee is required")
    payment_methods: Optional[str] = Field(None, description="Accepted payment methods")

    # External links
    registration_url: Optional[str] = Field(None, description="External registration URL")

    # Aggregator metadata (for events found via aggregators like Gary's Guide)
    original_provider: Optional[str] = Field(None, description="Original provider domain (luma.com, meetup.com, etc.)")
    aggregated_from: Optional[str] = Field(None, description="Aggregator that listed this event (garysguide, etc.)")
    short_url: Optional[str] = Field(None, description="Short URL from aggregator (e.g., gary.to link)")
    aggregator_detail_url: Optional[str] = Field(None, description="Detail page on aggregator site")

    # Metadata
    crawled_at: datetime = Field(default_factory=datetime.utcnow, description="When this was crawled")
    detail_crawled: bool = Field(False, description="Whether detail page was crawled")

    @field_validator('end_datetime')
    @classmethod
    def validate_end_after_start(cls, v, info):
        """Ensure end datetime is after start datetime."""
        if v and info.data.get('start_datetime') and v < info.data['start_datetime']:
            raise ValueError('end_datetime must be after start_datetime')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt-abc123",
                "source": "luma",
                "url": "https://luma.com/event/evt-abc123",
                "title": "Python Meetup NYC",
                "description": "Monthly Python developers meetup",
                "start_datetime": "2026-02-05T18:00:00Z",
                "end_datetime": "2026-02-05T20:00:00Z",
                "location_name": "Tech Hub NYC",
                "location_address": "123 Broadway, New York, NY 10001",
                "city": "New York",
                "state": "NY",
                "is_online": False,
                "attendee_count": 45,
                "capacity": 100,
                "spots_remaining": 55,
                "price_cents": 0,
                "currency": "USD",
                "is_free": True,
                "organizer_name": "NYC Python Group",
            }
        }
