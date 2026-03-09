"""Conference-specific models for agenda extraction and source discovery."""

from datetime import date, datetime

from pydantic import BaseModel, Field, HttpUrl


class ConferenceAgendaItem(BaseModel):
    """Normalized agenda row for a conference session."""

    conference_slug: str = Field(..., min_length=1)
    conference_name: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    source_url: HttpUrl
    agenda_date: date
    start_datetime: datetime
    end_datetime: datetime
    title: str = Field(..., min_length=1)
    speaker_names: list[str] = Field(default_factory=list)
    company_names: list[str] = Field(default_factory=list)
    description: str | None = None
    venue_name: str | None = None
    city: str | None = None
    state: str | None = None
    crawled_at: datetime = Field(default_factory=datetime.utcnow)


class ConferenceWatchSource(BaseModel):
    """A website or page that should be checked for conference announcements."""

    slug: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    base_url: HttpUrl
    discovery_url: HttpUrl | None = None
    city: str | None = None
    state: str | None = None
    venue_name: str | None = None
    source_type: str | None = None
    discovery_notes: str | None = None
    is_active: bool = True
    last_checked_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
