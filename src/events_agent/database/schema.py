"""Database schema definitions and migration management."""

import logging
from typing import Optional

from events_agent.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages database schema creation and migrations.

    Handles schema versioning, table creation, and index creation.
    Ensures database schema is up-to-date.

    Example:
        >>> db = DatabaseConnection("data/events.db")
        >>> schema = SchemaManager(db)
        >>> schema.initialize_schema()
    """

    CURRENT_VERSION = 3

    def __init__(self, db: DatabaseConnection):
        """Initialize schema manager.

        Args:
            db: Database connection instance.
        """
        self.db = db

    def initialize_schema(self) -> None:
        """Initialize database schema if not exists.

        Creates schema_version table and applies all migrations up to current version.
        """
        # Create schema_version table first
        self._create_schema_version_table()

        # Get current schema version
        current_version = self._get_schema_version()

        # Apply migrations if needed
        if current_version < self.CURRENT_VERSION:
            logger.info(
                f"Upgrading schema from version {current_version} to {self.CURRENT_VERSION}"
            )
            self._apply_migrations(current_version)
        else:
            logger.debug(f"Schema already at version {self.CURRENT_VERSION}")

    def _create_schema_version_table(self) -> None:
        """Create schema_version table to track migrations."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.db.commit()

    def _get_schema_version(self) -> int:
        """Get current schema version.

        Returns:
            Current schema version, or 0 if no migrations applied.
        """
        cursor = self.db.execute(
            "SELECT MAX(version) as version FROM schema_version"
        )
        row = cursor.fetchone()
        return row["version"] if row["version"] is not None else 0

    def _set_schema_version(self, version: int) -> None:
        """Set schema version after applying migration.

        Args:
            version: Schema version to set.
        """
        self.db.execute(
            "INSERT INTO schema_version (version) VALUES (?)", (version,)
        )
        self.db.commit()

    def _apply_migrations(self, from_version: int) -> None:
        """Apply all migrations from current version to latest.

        Args:
            from_version: Current schema version.
        """
        # Migration 1: Create initial schema
        if from_version < 1:
            logger.info("Applying migration 1: Create initial schema")
            self._create_initial_schema()
            self._set_schema_version(1)

        # Migration 2: Add enhanced fields for music/jazz/seasonal events
        if from_version < 2:
            logger.info("Applying migration 2: Add enhanced event fields")
            self._add_enhanced_event_fields()
            self._set_schema_version(2)

        # Migration 3: Add aggregator fields for events from aggregators like Gary's Guide
        if from_version < 3:
            logger.info("Applying migration 3: Add aggregator metadata fields")
            self._add_aggregator_fields()
            self._set_schema_version(3)

    def _create_initial_schema(self) -> None:
        """Create initial database schema with events and crawl_sessions tables."""
        # Events table - stores all event data
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Required fields
                event_id TEXT NOT NULL,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                start_datetime TIMESTAMP NOT NULL,

                -- Optional fields
                description TEXT,
                end_datetime TIMESTAMP,
                location_name TEXT,
                location_address TEXT,
                city TEXT,
                state TEXT,
                is_online INTEGER DEFAULT 0,

                -- Attendance fields
                attendee_count INTEGER,
                capacity INTEGER,
                spots_remaining INTEGER,

                -- Pricing fields
                price_cents INTEGER,
                currency TEXT DEFAULT 'USD',
                is_free INTEGER DEFAULT 1,

                -- Organizer fields
                organizer_name TEXT,
                organizer_url TEXT,

                -- Metadata
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Unique constraint to prevent duplicates
                UNIQUE(event_id, source)
            )
            """
        )

        # Create indexes for efficient queries
        indexes = [
            # Individual field indexes
            "CREATE INDEX IF NOT EXISTS idx_events_start_datetime ON events(start_datetime)",
            "CREATE INDEX IF NOT EXISTS idx_events_city ON events(city)",
            "CREATE INDEX IF NOT EXISTS idx_events_state ON events(state)",
            "CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)",
            "CREATE INDEX IF NOT EXISTS idx_events_is_online ON events(is_online)",
            # Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS idx_events_location_datetime ON events(city, state, start_datetime)",
            "CREATE INDEX IF NOT EXISTS idx_events_source_datetime ON events(source, start_datetime)",
            "CREATE INDEX IF NOT EXISTS idx_events_city_datetime ON events(city, start_datetime)",
        ]

        for index_sql in indexes:
            self.db.execute(index_sql)

        # Crawl sessions table - tracks each crawl operation
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS crawl_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                location TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                events_found INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                error_message TEXT
            )
            """
        )

        # Index for crawl sessions
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_crawl_sessions_source ON crawl_sessions(source)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_crawl_sessions_started_at ON crawl_sessions(started_at)"
        )

        self.db.commit()
        logger.info("Initial schema created successfully")

    def drop_all_tables(self) -> None:
        """Drop all tables. USE WITH CAUTION - only for testing."""
        logger.warning("Dropping all tables")
        self.db.execute("DROP TABLE IF EXISTS events")
        self.db.execute("DROP TABLE IF EXISTS crawl_sessions")
        self.db.execute("DROP TABLE IF EXISTS schema_version")
        self.db.commit()

    def _add_enhanced_event_fields(self) -> None:
        """Add enhanced fields for music, performance, and cooking events (Migration 2)."""
        # Add new columns to events table
        new_columns = [
            # Enhanced content
            "ALTER TABLE events ADD COLUMN ai_summary TEXT",
            "ALTER TABLE events ADD COLUMN image_url TEXT",
            "ALTER TABLE events ADD COLUMN topics TEXT",  # JSON array stored as text
            
            # Categorization
            "ALTER TABLE events ADD COLUMN experience_type TEXT",
            "ALTER TABLE events ADD COLUMN category TEXT",
            "ALTER TABLE events ADD COLUMN tags TEXT",  # JSON array stored as text
            
            # Cooking class fields
            "ALTER TABLE events ADD COLUMN chef_name TEXT",
            "ALTER TABLE events ADD COLUMN chef_rating REAL",
            "ALTER TABLE events ADD COLUMN chef_bio TEXT",
            "ALTER TABLE events ADD COLUMN skill_level TEXT",
            "ALTER TABLE events ADD COLUMN cuisine_type TEXT",
            
            # Performance fields (jazz, comedy, concerts)
            "ALTER TABLE events ADD COLUMN performer_names TEXT",  # JSON array
            "ALTER TABLE events ADD COLUMN genre TEXT",
            "ALTER TABLE events ADD COLUMN duration_minutes INTEGER",
            
            # Host information
            "ALTER TABLE events ADD COLUMN host_name TEXT",
            "ALTER TABLE events ADD COLUMN host_bio TEXT",
            
            # Group details (Meetup)
            "ALTER TABLE events ADD COLUMN group_name TEXT",
            "ALTER TABLE events ADD COLUMN group_rating REAL",
            "ALTER TABLE events ADD COLUMN group_review_count INTEGER",
            
            # Enhanced ratings
            "ALTER TABLE events ADD COLUMN rating REAL",
            "ALTER TABLE events ADD COLUMN review_count INTEGER",
            
            # Enhanced location
            "ALTER TABLE events ADD COLUMN latitude REAL",
            "ALTER TABLE events ADD COLUMN longitude REAL",
            "ALTER TABLE events ADD COLUMN directions TEXT",
            
            # Enhanced pricing
            "ALTER TABLE events ADD COLUMN fee_amount REAL",
            "ALTER TABLE events ADD COLUMN fee_required INTEGER",
            "ALTER TABLE events ADD COLUMN payment_methods TEXT",
            
            # External links
            "ALTER TABLE events ADD COLUMN registration_url TEXT",
            
            # Metadata
            "ALTER TABLE events ADD COLUMN detail_crawled INTEGER DEFAULT 0",
        ]
        
        for sql in new_columns:
            try:
                self.db.execute(sql)
            except Exception as e:
                # Column might already exist
                logger.debug(f"Could not add column (may already exist): {e}")
        
        # Add indexes for new filterable fields
        new_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_events_genre ON events(genre)",
            "CREATE INDEX IF NOT EXISTS idx_events_category ON events(category)",
            "CREATE INDEX IF NOT EXISTS idx_events_experience_type ON events(experience_type)",
            "CREATE INDEX IF NOT EXISTS idx_events_rating ON events(rating)",
        ]
        
        for index_sql in new_indexes:
            self.db.execute(index_sql)
        
        self.db.commit()
        logger.info("Enhanced event fields added successfully")

    def _add_aggregator_fields(self) -> None:
        """Add aggregator metadata fields (Migration 3).

        These fields support events discovered via aggregators like Gary's Guide
        that point to events on other platforms (Luma, Meetup, etc.)
        """
        aggregator_columns = [
            # Original provider info
            "ALTER TABLE events ADD COLUMN original_provider TEXT",  # Domain: luma.com, meetup.com
            "ALTER TABLE events ADD COLUMN aggregated_from TEXT",    # Aggregator: garysguide
            "ALTER TABLE events ADD COLUMN short_url TEXT",          # Short URL: gary.to/abc123
            "ALTER TABLE events ADD COLUMN aggregator_detail_url TEXT",  # Gary's Guide detail page
        ]

        for sql in aggregator_columns:
            try:
                self.db.execute(sql)
            except Exception as e:
                logger.debug(f"Could not add column (may already exist): {e}")

        # Add index for aggregator queries
        aggregator_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_events_original_provider ON events(original_provider)",
            "CREATE INDEX IF NOT EXISTS idx_events_aggregated_from ON events(aggregated_from)",
        ]

        for index_sql in aggregator_indexes:
            self.db.execute(index_sql)

        self.db.commit()
        logger.info("Aggregator metadata fields added successfully")

    def get_table_info(self, table_name: str) -> list:
        """Get table schema information.

        Args:
            table_name: Name of the table to inspect.

        Returns:
            List of column information dictionaries.
        """
        cursor = self.db.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists.

        Args:
            table_name: Name of the table to check.

        Returns:
            True if table exists, False otherwise.
        """
        cursor = self.db.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
            """,
            (table_name,),
        )
        return cursor.fetchone() is not None
