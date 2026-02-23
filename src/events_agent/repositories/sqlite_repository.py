"""SQLite implementation of EventRepository."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from events_agent.database.connection import DatabaseConnection
from events_agent.models.event import Event, EventSource
from events_agent.repositories.event_repository import EventRepository

logger = logging.getLogger(__name__)


class SQLiteEventRepository(EventRepository):
    """SQLite implementation of EventRepository.

    Provides efficient event storage and querying using SQLite with indexes.
    Handles automatic deduplication via UNIQUE(event_id, source) constraint.

    Example:
        >>> db = DatabaseConnection("data/events.db")
        >>> repo = SQLiteEventRepository(db)
        >>> repo.upsert_many(events)
        >>> nyc_events = repo.find_by_location_and_date(
        ...     start=datetime(2026, 2, 1),
        ...     end=datetime(2026, 2, 28),
        ...     city="new york",
        ...     state="NY"
        ... )
    """

    def __init__(self, db: DatabaseConnection):
        """Initialize repository with database connection.

        Args:
            db: Database connection instance.
        """
        self.db = db

    # --- CRUD Methods ---

    def save(self, event: Event) -> Event:
        """Save a single event.

        Args:
            event: Event to save.

        Returns:
            Saved event with ID populated.
        """
        cursor = self.db.execute(
            """
            INSERT INTO events (
                event_id, source, url, title, start_datetime,
                description, end_datetime, location_name, location_address,
                city, state, is_online, attendee_count, capacity,
                spots_remaining, price_cents, currency, is_free,
                organizer_name, organizer_url, crawled_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._event_to_tuple(event),
        )
        self.db.commit()

        # Return event with ID
        event_dict = event.model_dump()
        event_dict["id"] = cursor.lastrowid
        return Event(**event_dict)

    def save_many(self, events: List[Event]) -> int:
        """Save multiple events in a batch.

        Note: This does NOT handle duplicates. Use upsert_many for deduplication.

        Args:
            events: List of events to save.

        Returns:
            Number of events saved.
        """
        if not events:
            return 0

        tuples = [self._event_to_tuple(event) for event in events]

        self.db.execute_many(
            """
            INSERT INTO events (
                event_id, source, url, title, start_datetime,
                description, end_datetime, location_name, location_address,
                city, state, is_online, attendee_count, capacity,
                spots_remaining, waitlist, registration_closed,
                price_cents, min_price_cents, max_price_cents, currency, is_free,
                organizer_name, organizer_url, crawled_at,
                ai_summary, image_url, topics, experience_type, category, tags,
                chef_name, chef_rating, chef_bio, skill_level, cuisine_type,
                performer_names, genre, duration_minutes, host_name, host_bio,
                group_name, group_rating, group_review_count, rating, review_count,
                latitude, longitude, directions, fee_amount, fee_required,
                payment_methods, registration_url, detail_crawled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuples,
        )
        self.db.commit()

        return len(events)

    def find_by_id(self, id: int) -> Optional[Event]:
        """Find event by primary key ID.

        Args:
            id: Primary key ID.

        Returns:
            Event if found, None otherwise.
        """
        cursor = self.db.execute("SELECT * FROM events WHERE id = ?", (id,))
        row = cursor.fetchone()

        return self._row_to_event(row) if row else None

    def find_all(self) -> List[Event]:
        """Retrieve all events.

        Returns:
            List of all events (may be empty).
        """
        cursor = self.db.execute("SELECT * FROM events ORDER BY start_datetime")
        rows = cursor.fetchall()

        return [self._row_to_event(row) for row in rows]

    def delete(self, id: int) -> bool:
        """Delete event by primary key ID.

        Args:
            id: Primary key ID.

        Returns:
            True if deleted, False if not found.
        """
        cursor = self.db.execute("DELETE FROM events WHERE id = ?", (id,))
        self.db.commit()

        return cursor.rowcount > 0

    def count(self) -> int:
        """Count total number of events.

        Returns:
            Total event count.
        """
        cursor = self.db.execute("SELECT COUNT(*) as count FROM events")
        row = cursor.fetchone()
        return row["count"]

    # --- Domain-specific queries ---

    def find_by_event_id(
        self, event_id: str, source: EventSource
    ) -> Optional[Event]:
        """Find event by event_id and source (unique combination).

        Args:
            event_id: Event ID from source platform.
            source: Event source.

        Returns:
            Event if found, None otherwise.
        """
        cursor = self.db.execute(
            "SELECT * FROM events WHERE event_id = ? AND source = ?",
            (event_id, source.value),
        )
        row = cursor.fetchone()

        return self._row_to_event(row) if row else None

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
            List of events starting between start and end dates.
        """
        sql = """
            SELECT * FROM events
            WHERE start_datetime >= ? AND start_datetime <= ?
            ORDER BY start_datetime
        """

        if limit is not None:
            sql += f" LIMIT {limit}"

        cursor = self.db.execute(
            sql, (start.isoformat(), end.isoformat())
        )
        rows = cursor.fetchall()

        return [self._row_to_event(row) for row in rows]

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
            exclude_online: If True, exclude online events.

        Returns:
            List of events matching location criteria.
        """
        where_clauses = []
        params = []

        if city:
            where_clauses.append("LOWER(city) LIKE LOWER(?)")
            params.append(f"%{city}%")

        if state:
            where_clauses.append("state = ?")
            params.append(state)

        if exclude_online:
            where_clauses.append("is_online = 0")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        sql = f"""
            SELECT * FROM events
            WHERE {where_sql}
            ORDER BY start_datetime
        """

        cursor = self.db.execute(sql, tuple(params))
        rows = cursor.fetchall()

        return [self._row_to_event(row) for row in rows]

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

        Uses composite index idx_events_location_datetime for optimal performance.

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
        where_clauses = [
            "start_datetime >= ?",
            "start_datetime <= ?",
        ]
        params = [start.isoformat(), end.isoformat()]

        if city:
            where_clauses.append("LOWER(city) LIKE LOWER(?)")
            params.append(f"%{city}%")

        if state:
            where_clauses.append("state = ?")
            params.append(state)

        if exclude_online:
            where_clauses.append("is_online = 0")

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT * FROM events
            WHERE {where_sql}
            ORDER BY start_datetime
        """

        if limit is not None:
            sql += f" LIMIT {limit}"

        cursor = self.db.execute(sql, tuple(params))
        rows = cursor.fetchall()

        return [self._row_to_event(row) for row in rows]

    def find_by_source(self, source: EventSource) -> List[Event]:
        """Find all events from a specific source.

        Args:
            source: Event source.

        Returns:
            List of events from the specified source.
        """
        cursor = self.db.execute(
            "SELECT * FROM events WHERE source = ? ORDER BY start_datetime",
            (source.value,),
        )
        rows = cursor.fetchall()

        return [self._row_to_event(row) for row in rows]

    # --- Deduplication methods ---

    def exists(self, event_id: str, source: EventSource) -> bool:
        """Check if event exists (by event_id and source).

        Args:
            event_id: Event ID from source platform.
            source: Event source.

        Returns:
            True if event exists, False otherwise.
        """
        cursor = self.db.execute(
            "SELECT 1 FROM events WHERE event_id = ? AND source = ?",
            (event_id, source.value),
        )
        return cursor.fetchone() is not None

    def upsert(self, event: Event) -> Event:
        """Insert or update event (by event_id and source).

        Uses INSERT OR REPLACE to handle deduplication.

        Args:
            event: Event to upsert.

        Returns:
            Upserted event with ID populated.
        """
        cursor = self.db.execute(
            """
            INSERT INTO events (
                event_id, source, url, title, start_datetime,
                description, end_datetime, location_name, location_address,
                city, state, is_online, attendee_count, capacity,
                spots_remaining, price_cents, currency, is_free,
                organizer_name, organizer_url, crawled_at,
                ai_summary, image_url, topics, experience_type, category, tags,
                chef_name, chef_rating, chef_bio, skill_level, cuisine_type,
                performer_names, genre, duration_minutes, host_name, host_bio,
                group_name, group_rating, group_review_count, rating, review_count,
                latitude, longitude, directions, fee_amount, fee_required,
                payment_methods, registration_url, detail_crawled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id, source) DO UPDATE SET
                url = excluded.url,
                title = excluded.title,
                start_datetime = excluded.start_datetime,
                description = excluded.description,
                end_datetime = excluded.end_datetime,
                location_name = excluded.location_name,
                location_address = excluded.location_address,
                city = excluded.city,
                state = excluded.state,
                is_online = excluded.is_online,
                attendee_count = excluded.attendee_count,
                capacity = excluded.capacity,
                spots_remaining = excluded.spots_remaining,
                waitlist = excluded.waitlist,
                registration_closed = excluded.registration_closed,
                price_cents = excluded.price_cents,
                min_price_cents = excluded.min_price_cents,
                max_price_cents = excluded.max_price_cents,
                currency = excluded.currency,
                is_free = excluded.is_free,
                organizer_name = excluded.organizer_name,
                organizer_url = excluded.organizer_url,
                crawled_at = excluded.crawled_at,
                ai_summary = excluded.ai_summary,
                image_url = excluded.image_url,
                topics = excluded.topics,
                experience_type = excluded.experience_type,
                category = excluded.category,
                tags = excluded.tags,
                chef_name = excluded.chef_name,
                chef_rating = excluded.chef_rating,
                chef_bio = excluded.chef_bio,
                skill_level = excluded.skill_level,
                cuisine_type = excluded.cuisine_type,
                performer_names = excluded.performer_names,
                genre = excluded.genre,
                duration_minutes = excluded.duration_minutes,
                host_name = excluded.host_name,
                host_bio = excluded.host_bio,
                group_name = excluded.group_name,
                group_rating = excluded.group_rating,
                group_review_count = excluded.group_review_count,
                rating = excluded.rating,
                review_count = excluded.review_count,
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                directions = excluded.directions,
                fee_amount = excluded.fee_amount,
                fee_required = excluded.fee_required,
                payment_methods = excluded.payment_methods,
                registration_url = excluded.registration_url,
                detail_crawled = excluded.detail_crawled
            """,
            self._event_to_tuple(event),
        )
        self.db.commit()

        # Get the ID of the upserted event
        event_dict = event.model_dump()
        event_dict["id"] = cursor.lastrowid
        return Event(**event_dict)

    def upsert_many(self, events: List[Event]) -> int:
        """Insert or update multiple events in a batch.

        Efficiently handles bulk upserts with automatic deduplication.

        Args:
            events: List of events to upsert.

        Returns:
            Number of events upserted.
        """
        if not events:
            return 0

        tuples = [self._event_to_tuple(event) for event in events]

        self.db.execute_many(
            """
            INSERT INTO events (
                event_id, source, url, title, start_datetime,
                description, end_datetime, location_name, location_address,
                city, state, is_online, attendee_count, capacity,
                spots_remaining, waitlist, registration_closed,
                price_cents, min_price_cents, max_price_cents, currency, is_free,
                organizer_name, organizer_url, crawled_at,
                ai_summary, image_url, topics, experience_type, category, tags,
                chef_name, chef_rating, chef_bio, skill_level, cuisine_type,
                performer_names, genre, duration_minutes, host_name, host_bio,
                group_name, group_rating, group_review_count, rating, review_count,
                latitude, longitude, directions, fee_amount, fee_required,
                payment_methods, registration_url, detail_crawled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id, source) DO UPDATE SET
                url = excluded.url,
                title = excluded.title,
                start_datetime = excluded.start_datetime,
                description = excluded.description,
                end_datetime = excluded.end_datetime,
                location_name = excluded.location_name,
                location_address = excluded.location_address,
                city = excluded.city,
                state = excluded.state,
                is_online = excluded.is_online,
                attendee_count = excluded.attendee_count,
                capacity = excluded.capacity,
                spots_remaining = excluded.spots_remaining,
                waitlist = excluded.waitlist,
                registration_closed = excluded.registration_closed,
                price_cents = excluded.price_cents,
                min_price_cents = excluded.min_price_cents,
                max_price_cents = excluded.max_price_cents,
                currency = excluded.currency,
                is_free = excluded.is_free,
                organizer_name = excluded.organizer_name,
                organizer_url = excluded.organizer_url,
                crawled_at = excluded.crawled_at,
                ai_summary = excluded.ai_summary,
                image_url = excluded.image_url,
                topics = excluded.topics,
                experience_type = excluded.experience_type,
                category = excluded.category,
                tags = excluded.tags,
                chef_name = excluded.chef_name,
                chef_rating = excluded.chef_rating,
                chef_bio = excluded.chef_bio,
                skill_level = excluded.skill_level,
                cuisine_type = excluded.cuisine_type,
                performer_names = excluded.performer_names,
                genre = excluded.genre,
                duration_minutes = excluded.duration_minutes,
                host_name = excluded.host_name,
                host_bio = excluded.host_bio,
                group_name = excluded.group_name,
                group_rating = excluded.group_rating,
                group_review_count = excluded.group_review_count,
                rating = excluded.rating,
                review_count = excluded.review_count,
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                directions = excluded.directions,
                fee_amount = excluded.fee_amount,
                fee_required = excluded.fee_required,
                payment_methods = excluded.payment_methods,
                registration_url = excluded.registration_url,
                detail_crawled = excluded.detail_crawled
            """,
            tuples,
        )
        self.db.commit()

        return len(events)

    # --- Analytics methods ---

    def count_by_filters(self, filters: Optional[Dict] = None) -> int:
        """Count events matching filters.

        Args:
            filters: Optional dictionary of filter criteria.

        Returns:
            Number of events matching filters.
        """
        if not filters:
            return self.count()

        where_clauses = []
        params = []

        if "source" in filters:
            where_clauses.append("source = ?")
            params.append(filters["source"].value)

        if "city" in filters:
            where_clauses.append("LOWER(city) LIKE LOWER(?)")
            params.append(f"%{filters['city']}%")

        if "state" in filters:
            where_clauses.append("state = ?")
            params.append(filters["state"])

        if "start_after" in filters:
            where_clauses.append("start_datetime >= ?")
            params.append(filters["start_after"].isoformat())

        if "start_before" in filters:
            where_clauses.append("start_datetime <= ?")
            params.append(filters["start_before"].isoformat())

        if "is_online" in filters:
            where_clauses.append("is_online = ?")
            params.append(1 if filters["is_online"] else 0)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        sql = f"SELECT COUNT(*) as count FROM events WHERE {where_sql}"

        cursor = self.db.execute(sql, tuple(params))
        row = cursor.fetchone()
        return row["count"]

    def get_sources(self) -> List[str]:
        """Get list of all unique event sources in database.

        Returns:
            List of source names.
        """
        cursor = self.db.execute(
            "SELECT DISTINCT source FROM events ORDER BY source"
        )
        rows = cursor.fetchall()
        return [row["source"] for row in rows]

    def get_cities(self) -> List[str]:
        """Get list of all unique cities in database.

        Returns:
            List of city names (excluding None/empty).
        """
        cursor = self.db.execute(
            """
            SELECT DISTINCT city FROM events
            WHERE city IS NOT NULL AND city != ''
            ORDER BY city
            """
        )
        rows = cursor.fetchall()
        return [row["city"] for row in rows]

    def get_date_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """Get min and max event start datetimes in database.

        Returns:
            Tuple of (earliest_start, latest_start) or (None, None) if no events.
        """
        cursor = self.db.execute(
            """
            SELECT
                MIN(start_datetime) as min_date,
                MAX(start_datetime) as max_date
            FROM events
            """
        )
        row = cursor.fetchone()

        if row["min_date"] and row["max_date"]:
            return (
                datetime.fromisoformat(row["min_date"]),
                datetime.fromisoformat(row["max_date"]),
            )
        return (None, None)

    # --- Helper methods ---

    def _event_to_tuple(self, event: Event) -> tuple:
        """Convert Event model to tuple for SQL insertion.

        Args:
            event: Event model instance.

        Returns:
            Tuple of event field values in correct order for SQL.
        """
        import json

        return (
            event.event_id,
            event.source.value,
            str(event.url),
            event.title,
            event.start_datetime.isoformat(),
            event.description,
            event.end_datetime.isoformat() if event.end_datetime else None,
            event.location_name,
            event.location_address,
            event.city,
            event.state,
            1 if event.is_online else 0,
            event.attendee_count,
            event.capacity,
            event.spots_remaining,
            1 if event.waitlist else 0 if event.waitlist is not None else None,
            1 if event.registration_closed else 0 if event.registration_closed is not None else None,
            event.price_cents,
            event.min_price_cents,
            event.max_price_cents,
            event.currency,
            1 if event.is_free else 0,
            event.organizer_name,
            str(event.organizer_url) if event.organizer_url else None,
            event.crawled_at.isoformat(),
            # Additional fields
            event.ai_summary,
            str(event.image_url) if event.image_url else None,
            json.dumps(event.topics) if event.topics else None,
            event.experience_type,
            event.category,
            json.dumps(event.tags) if event.tags else None,
            event.chef_name,
            event.chef_rating,
            event.chef_bio,
            event.skill_level,
            event.cuisine_type,
            json.dumps(event.performer_names) if event.performer_names else None,
            event.genre,
            event.duration_minutes,
            event.host_name,
            event.host_bio,
            event.group_name,
            event.group_rating,
            event.group_review_count,
            event.rating,
            event.review_count,
            event.latitude,
            event.longitude,
            event.directions,
            event.fee_amount,
            1 if event.fee_required else 0 if event.fee_required is not None else None,
            json.dumps(event.payment_methods) if event.payment_methods else None,
            str(event.registration_url) if event.registration_url else None,
            1 if event.detail_crawled else 0,
        )

    def _row_to_event(self, row) -> Event:
        """Convert database row to Event model.

        Args:
            row: Database row (sqlite3.Row or dict).

        Returns:
            Event model instance.
        """
        import json

        # sqlite3.Row doesn't support .get(); convert to dict
        r = dict(row)

        return Event(
            event_id=r["event_id"],
            source=EventSource(r["source"]),
            url=r["url"],
            title=r["title"],
            start_datetime=datetime.fromisoformat(r["start_datetime"]),
            description=r["description"],
            end_datetime=datetime.fromisoformat(r["end_datetime"])
            if r.get("end_datetime")
            else None,
            location_name=r["location_name"],
            location_address=r["location_address"],
            city=r["city"],
            state=r["state"],
            is_online=bool(r["is_online"]),
            attendee_count=r["attendee_count"],
            capacity=r["capacity"],
            spots_remaining=r["spots_remaining"],
            waitlist=bool(r["waitlist"]) if r.get("waitlist") is not None else None,
            registration_closed=bool(r["registration_closed"]) if r.get("registration_closed") is not None else None,
            price_cents=r["price_cents"],
            min_price_cents=r.get("min_price_cents"),
            max_price_cents=r.get("max_price_cents"),
            currency=r["currency"],
            is_free=bool(r["is_free"]),
            organizer_name=r["organizer_name"],
            organizer_url=r["organizer_url"],
            crawled_at=datetime.fromisoformat(r["crawled_at"]),
            # Additional fields
            ai_summary=r.get("ai_summary"),
            image_url=r.get("image_url"),
            topics=json.loads(r["topics"]) if r.get("topics") else None,
            experience_type=r.get("experience_type"),
            category=r.get("category"),
            tags=json.loads(r["tags"]) if r.get("tags") else None,
            chef_name=r.get("chef_name"),
            chef_rating=r.get("chef_rating"),
            chef_bio=r.get("chef_bio"),
            skill_level=r.get("skill_level"),
            cuisine_type=r.get("cuisine_type"),
            performer_names=json.loads(r["performer_names"])
            if r.get("performer_names")
            else None,
            genre=r.get("genre"),
            duration_minutes=r.get("duration_minutes"),
            host_name=r.get("host_name"),
            host_bio=r.get("host_bio"),
            group_name=r.get("group_name"),
            group_rating=r.get("group_rating"),
            group_review_count=r.get("group_review_count"),
            rating=r.get("rating"),
            review_count=r.get("review_count"),
            latitude=r.get("latitude"),
            longitude=r.get("longitude"),
            directions=r.get("directions"),
            fee_amount=r.get("fee_amount"),
            fee_required=bool(r["fee_required"])
            if r.get("fee_required") is not None
            else None,
            payment_methods=json.loads(r["payment_methods"])
            if r.get("payment_methods")
            else None,
            registration_url=r.get("registration_url"),
            detail_crawled=bool(r.get("detail_crawled")),
        )
