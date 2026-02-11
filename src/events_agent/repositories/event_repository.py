"""Event repository interface with domain-specific queries."""

from abc import abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from events_agent.models.event import Event, EventSource
from events_agent.repositories.base import Repository


class EventRepository(Repository[Event]):
    """Event repository interface with domain-specific queries.

    Extends base repository with event-specific query methods for:
    - Date range filtering
    - Location-based queries
    - Source-based queries
    - Deduplication (upsert operations)
    - Analytics and statistics

    Implementations: SQLiteEventRepository, JSONEventRepository (for exports)
    """

    # --- Domain-specific queries ---

    @abstractmethod
    def find_by_event_id(
        self, event_id: str, source: EventSource
    ) -> Optional[Event]:
        """Find event by event_id and source (unique combination).

        Args:
            event_id: Event ID from source platform.
            source: Event source (luma, meetup, etc.).

        Returns:
            Event if found, None otherwise.
        """
        pass

    @abstractmethod
    def find_by_date_range(
        self,
        start: datetime,
        end: datetime,
        limit: Optional[int] = None,
    ) -> List[Event]:
        """Find events within a date range.

        Args:
            start: Start datetime (inclusive).
            end: End datetime (inclusive).
            limit: Optional maximum number of events to return.

        Returns:
            List of events starting between start and end dates, ordered by start_datetime.
        """
        pass

    @abstractmethod
    def find_by_location(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        exclude_online: bool = True,
    ) -> List[Event]:
        """Find events by location.

        Args:
            city: City name (case-insensitive partial match).
            state: State code (exact match).
            exclude_online: If True, exclude online events (is_online=True).

        Returns:
            List of events matching location criteria.
        """
        pass

    @abstractmethod
    def find_by_location_and_date(
        self,
        start: datetime,
        end: datetime,
        city: Optional[str] = None,
        state: Optional[str] = None,
        exclude_online: bool = True,
        limit: Optional[int] = None,
    ) -> List[Event]:
        """Find events by location AND date range (most efficient query).

        Combines location and date filtering in a single indexed SQL query.
        This is the primary query method for filtering events.

        Args:
            start: Start datetime (inclusive).
            end: End datetime (inclusive).
            city: City name (case-insensitive partial match).
            state: State code (exact match).
            exclude_online: If True, exclude online events.
            limit: Optional maximum number of events to return.

        Returns:
            List of events matching all criteria, ordered by start_datetime.
        """
        pass

    @abstractmethod
    def find_by_source(self, source: EventSource) -> List[Event]:
        """Find all events from a specific source.

        Args:
            source: Event source (luma, meetup, etc.).

        Returns:
            List of events from the specified source.
        """
        pass

    # --- Deduplication methods ---

    @abstractmethod
    def exists(self, event_id: str, source: EventSource) -> bool:
        """Check if event exists (by event_id and source).

        Args:
            event_id: Event ID from source platform.
            source: Event source.

        Returns:
            True if event exists, False otherwise.
        """
        pass

    @abstractmethod
    def upsert(self, event: Event) -> Event:
        """Insert or update event (by event_id and source).

        If event with same event_id and source exists, updates it.
        Otherwise, inserts new event.

        Args:
            event: Event to upsert.

        Returns:
            Upserted event with ID populated.
        """
        pass

    @abstractmethod
    def upsert_many(self, events: List[Event]) -> int:
        """Insert or update multiple events in a batch.

        Efficiently handles bulk upserts with automatic deduplication.

        Args:
            events: List of events to upsert.

        Returns:
            Number of events upserted (inserted or updated).
        """
        pass

    # --- Analytics methods ---

    @abstractmethod
    def count_by_filters(self, filters: Optional[Dict] = None) -> int:
        """Count events matching filters.

        Args:
            filters: Optional dictionary of filter criteria:
                - source: EventSource
                - city: str
                - state: str
                - start_after: datetime
                - start_before: datetime
                - is_online: bool

        Returns:
            Number of events matching filters.
        """
        pass

    @abstractmethod
    def get_sources(self) -> List[str]:
        """Get list of all unique event sources in database.

        Returns:
            List of source names.
        """
        pass

    @abstractmethod
    def get_cities(self) -> List[str]:
        """Get list of all unique cities in database.

        Returns:
            List of city names (excluding None/empty).
        """
        pass

    @abstractmethod
    def get_date_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """Get min and max event start datetimes in database.

        Returns:
            Tuple of (earliest_start, latest_start) or (None, None) if no events.
        """
        pass
