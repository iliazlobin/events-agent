#!/usr/bin/env python3
"""Migrate existing JSON event data to SQLite database.

This script reads all JSON files from data/raw/ and imports them into
the SQLite database, handling deduplication automatically.

Usage:
    python scripts/migrate_json_to_sqlite.py [--db-path data/events.db] [--dry-run]

Options:
    --db-path PATH    Path to SQLite database (default: data/events.db)
    --dry-run         Show what would be imported without actually importing
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from events_agent.database.connection import DatabaseConnection
from events_agent.database.schema import SchemaManager
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.actor_runtime import actor_item_to_event
from events_agent.models.event import Event


def load_json_file(filepath: Path) -> list[Event]:
    """Load events from JSON file.

    Args:
        filepath: Path to JSON file.

    Returns:
        List of Event objects.
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    if isinstance(data, dict):
        items = data.get("events", data.get("items"))
        if items is None:
            raise ValueError("Expected top-level 'events' or 'items' key")
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("Expected JSON array or object containing event items")

    events = []
    for item in items:
        try:
            events.append(actor_item_to_event(item))
        except Exception as e:
            print(f"  ⚠️  Skipping invalid event: {e}")

    return events


def main():
    """Run migration."""
    parser = argparse.ArgumentParser(
        description="Migrate JSON event data to SQLite database"
    )
    parser.add_argument(
        "--db-path",
        default="data/events.db",
        help="Path to SQLite database (default: data/events.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without actually importing",
    )
    parser.add_argument(
        "--data-dir",
        default="data/raw",
        help="Directory containing JSON files (default: data/raw)",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("JSON to SQLite Migration Script")
    print("=" * 70)
    print(f"Database: {args.db_path}")
    print(f"Data directory: {args.data_dir}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 70)

    # Find all JSON files
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"\n❌ Error: Data directory not found: {data_dir}")
        sys.exit(1)

    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        print(f"\n⚠️  No JSON files found in {data_dir}")
        sys.exit(0)

    print(f"\nFound {len(json_files)} JSON files:")
    for filepath in json_files:
        print(f"  - {filepath.name}")

    # Initialize database (if not dry run)
    if not args.dry_run:
        print("\n[1/3] Initializing database...")
        db = DatabaseConnection(args.db_path)
        schema = SchemaManager(db)
        schema.initialize_schema()
        repository = SQLiteEventRepository(db)
        print("  ✓ Database initialized")

    # Load all events from JSON files
    print("\n[2/3] Loading events from JSON files...")
    all_events = []
    file_stats = {}

    for filepath in json_files:
        try:
            events = load_json_file(filepath)
            all_events.extend(events)
            file_stats[filepath.name] = len(events)
            print(f"  ✓ {filepath.name}: {len(events)} events")
        except Exception as e:
            print(f"  ✗ {filepath.name}: Error - {e}")
            file_stats[filepath.name] = 0

    print(f"\n  Total events loaded: {len(all_events)}")

    # Count by source
    source_counts = {}
    for event in all_events:
        source = event.source.value
        source_counts[source] = source_counts.get(source, 0) + 1

    print("\n  Events by source:")
    for source, count in sorted(source_counts.items()):
        print(f"    - {source}: {count}")

    # Import to database (if not dry run)
    if args.dry_run:
        print("\n[3/3] Dry run complete - no data imported")
        print("\nRun without --dry-run to import data to database")
    else:
        print("\n[3/3] Importing events to database...")
        start_time = datetime.now()

        # Get count before import
        before_count = repository.count()
        print(f"  Events in database before: {before_count}")

        # Upsert all events (handles deduplication)
        upserted = repository.upsert_many(all_events)

        # Get count after import
        after_count = repository.count()

        # Calculate statistics
        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"  Events upserted: {upserted}")
        print(f"  Events in database after: {after_count}")
        print(f"  New events added: {after_count - before_count}")
        print(f"  Duplicates handled: {upserted - (after_count - before_count)}")
        print(f"  Time elapsed: {elapsed:.2f}s")
        print(f"\n  ✓ Migration complete!")

        # Verify data
        print("\n[Verification] Checking database integrity...")

        # Check sources
        db_sources = repository.get_sources()
        print(f"  Sources in database: {', '.join(db_sources)}")

        # Check date range
        min_date, max_date = repository.get_date_range()
        if min_date and max_date:
            print(f"  Date range: {min_date.date()} to {max_date.date()}")

        # Check cities
        cities = repository.get_cities()
        print(f"  Cities: {len(cities)} unique cities")

        print("\n  ✓ Verification complete")

    # Summary
    print("\n" + "=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"JSON files processed: {len(json_files)}")
    print(f"Total events loaded: {len(all_events)}")
    if not args.dry_run:
        print(f"Events in database: {after_count}")
        print(f"Database file: {args.db_path}")
        print("\nYou can now query the database using:")
        print("  - DB Browser for SQLite (GUI)")
        print("  - Python scripts using SQLiteEventRepository")
        print("  - SQL queries directly")
    print("=" * 70)


if __name__ == "__main__":
    main()
