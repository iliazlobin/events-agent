"""Main CLI entry point for events crawler."""

import json
from datetime import datetime
from playwright.sync_api import sync_playwright
from events_agent.crawlers.luma_crawler import LumaCrawler
from events_agent.crawlers.meetup_crawler import MeetupCrawler
from events_agent.crawlers.fever_crawler import FeverCrawler
from events_agent.crawlers.cozymeal_crawler import CozymealCrawler
from events_agent.crawlers.eventbrite_crawler import EventbriteCrawler
from events_agent.database.connection import DatabaseConnection
from events_agent.database.schema import SchemaManager
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.repositories.json_repository import JSONEventRepository
from events_agent.filters.date_filter import DateFilter
from events_agent.processors.event_processor import EventProcessor, ProcessingPipeline
from events_agent.utils.event_validator import EventValidator


def main(max_events: int = 100):
    """
    Main entry point for events crawler.

    Process:
    1. Initialize database and repository
    2. Fetch events from 5 sources (Luma, Meetup, Fever, Cozymeal, Eventbrite)
    3. Save raw data to SQLite (with automatic deduplication)
    4. Query filtered events using SQL (by NYC location and current/next week)
    5. Limit to max_events
    6. Export to JSON for debugging
    7. Output results

    Args:
        max_events: Maximum number of events to return (default: 100)
    """
    print("=" * 60)
    print("Events Agent - Crawling Events from 5 Sources")
    print("Sources: Luma, Meetup, Fever, Cozymeal, Eventbrite")
    print(f"Max events: {max_events}")
    print("=" * 60)

    # Initialize database and repository
    print("\n[Initialization] Setting up SQLite database...")
    db = DatabaseConnection("data/events.db")
    schema = SchemaManager(db)
    schema.initialize_schema()
    repository = SQLiteEventRepository(db)
    json_repo = JSONEventRepository("data/debug")
    timestamp = datetime.now()
    print("  ✓ Database initialized")

    # Get date range for filtering (current and next week)
    current_start, current_end = DateFilter.get_current_week_range()
    next_start, next_end = DateFilter.get_next_week_range()
    filter_start = current_start
    filter_end = next_end

    # Crawl events from all sources
    sources_events = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Crawl Luma
        print("\n[1/2] Crawling Luma.com...")
        luma_crawler = LumaCrawler()
        try:
            luma_events = luma_crawler.crawl(browser, "nyc")
            print(f"  ✓ Found {len(luma_events)} Luma events")
            sources_events["luma"] = luma_events
        except Exception as e:
            print(f"  ✗ Error crawling Luma: {e}")
            sources_events["luma"] = []

        # Crawl Meetup (with max_events limit for infinite scroll)
        print("\n[2/5] Crawling Meetup.com...")
        meetup_crawler = MeetupCrawler(
            max_events_total=max_events,
            max_events_per_day=50,
            distance_miles=10,
            event_type="inPerson"
        )
        try:
            meetup_events = meetup_crawler.crawl(browser, "New York, NY")
            print(f"  ✓ Found {len(meetup_events)} Meetup events")
            sources_events["meetup"] = meetup_events
        except Exception as e:
            print(f"  ✗ Error crawling Meetup: {e}")
            sources_events["meetup"] = []

        # Crawl Fever
        print("\n[3/5] Crawling Fever...")
        fever_crawler = FeverCrawler(max_events=max_events)
        try:
            fever_events = fever_crawler.crawl(browser, "nyc")
            print(f"  ✓ Found {len(fever_events)} Fever events")
            sources_events["fever"] = fever_events
        except Exception as e:
            print(f"  ✗ Error crawling Fever: {e}")
            sources_events["fever"] = []

        # Crawl Cozymeal
        print("\n[4/5] Crawling Cozymeal...")
        cozymeal_crawler = CozymealCrawler(max_events=max_events, max_pages=10)
        try:
            cozymeal_events = cozymeal_crawler.crawl(browser, "nyc")
            print(f"  ✓ Found {len(cozymeal_events)} Cozymeal cooking classes")
            sources_events["cozymeal"] = cozymeal_events
        except Exception as e:
            print(f"  ✗ Error crawling Cozymeal: {e}")
            sources_events["cozymeal"] = []

        # Crawl Eventbrite
        print("\n[5/5] Crawling Eventbrite...")
        eventbrite_crawler = EventbriteCrawler(max_events=max_events)
        try:
            eventbrite_events = eventbrite_crawler.crawl(browser, "nyc")
            print(f"  ✓ Found {len(eventbrite_events)} Eventbrite events")
            sources_events["eventbrite"] = eventbrite_events
        except Exception as e:
            print(f"  ✗ Error crawling Eventbrite: {e}")
            sources_events["eventbrite"] = []

        browser.close()

    print("\n" + "=" * 60)
    total_raw = sum(len(events) for events in sources_events.values())
    print(f"Total events collected: {total_raw}")
    print("=" * 60)

    # Save all events to SQLite (with automatic deduplication)
    print("\n[Storage] Saving events to SQLite database...")
    all_events = []
    for source, events in sources_events.items():
        if events:
            all_events.extend(events)
            # Optional: Export raw data to JSON for debugging
            json_file = json_repo.export_events(events, source, timestamp)
            print(f"  ✓ Saved {len(events)} {source} events (debug: {json_file})")

    if all_events:
        upserted_count = repository.upsert_many(all_events)
        print(f"  ✓ Upserted {upserted_count} events to database (deduplication applied)")

    # Query filtered events using SQL (replaces in-memory filtering)
    print("\n[Filtering] Querying NYC events for current and next week...")
    filtered_events = repository.find_by_location_and_date(
        start=filter_start,
        end=filter_end,
        city="new york",
        state="NY",
        exclude_online=True,
        limit=max_events
    )
    print(f"  ✓ Found {len(filtered_events)} events matching criteria")

    # Validate event coverage and quality
    EventValidator.print_validation_report(filtered_events, target_days=14)

    # Export processed events to JSON for backwards compatibility
    filters_applied = {
        "location": "NYC (New York, NY)",
        "date_range": "current_and_next_week",
        "max_events": max_events,
        "start_date": filter_start.isoformat(),
        "end_date": filter_end.isoformat()
    }

    processed_file = json_repo.export_processed(
        filtered_events,
        filters_applied,
        timestamp
    )

    # Also save to events_output.json for backwards compatibility
    output = {
        "timestamp": timestamp.isoformat(),
        "total_events": len(filtered_events),
        "filters": filters_applied,
        "database": "data/events.db",
        "total_in_database": repository.count(),
        "events": [e.model_dump(mode='json') for e in filtered_events]
    }

    output_file = "events_output.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print(f"✓ Results saved to: {output_file}")
    print(f"✓ Processed data: {processed_file}")
    print(f"✓ Total filtered events: {len(filtered_events)}")
    print(f"✓ Total events in database: {repository.count()}")
    print(f"✓ Database: data/events.db")
    print("=" * 60)

    # Print sample events
    if filtered_events:
        print("\nSample events:")
        for i, event in enumerate(filtered_events[:5], 1):
            print(f"\n  {i}. {event.title}")
            print(f"     Source: {event.source.value}")
            print(f"     Date: {event.start_datetime.strftime('%a, %b %d at %I:%M %p')}")
            if event.city:
                print(f"     Location: {event.city}, {event.state}")
            print(f"     URL: {event.url}")

        if len(filtered_events) > 5:
            print(f"\n  ... and {len(filtered_events) - 5} more events")

    return filtered_events


if __name__ == "__main__":
    main()
