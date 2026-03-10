"""Shared runtime entry point for the events agent."""

from pathlib import Path

from events_agent.database.connection import DatabaseConnection
from events_agent.database.schema import SchemaManager


def main() -> int:
    """Initialize shared runtime state and print the current architecture contract."""
    db_path = Path("data/events.db")
    db = DatabaseConnection(str(db_path))
    schema = SchemaManager(db)
    schema.initialize_schema()

    print("Events Agent runtime initialized")
    print(f"SQLite: {db_path}")
    print("Production crawlers: src/apify/<source>-crawler")
    print("Shared runtime: src/events_agent/{database,models,repositories,utils}")
    print("Python actor bridges: events_agent.legacy_crawlers")
    print("Conference-specific trackers: events_agent.conference_tracking")
    print("Run actor code from src/apify and import datasets into SQLite.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
