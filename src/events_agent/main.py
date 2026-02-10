"""Main CLI entry point for events crawler."""

import json
from datetime import datetime
from playwright.sync_api import sync_playwright
from events_agent.crawlers.luma_crawler import LumaCrawler
from events_agent.crawlers.meetup_crawler import MeetupCrawler
from events_agent.crawlers.fever_crawler import FeverCrawler
from events_agent.crawlers.cozymeal_crawler import CozymealCrawler
from events_agent.crawlers.eventbrite_crawler import EventbriteCrawler
from events_agent.storage.data_manager import DataManager
from events_agent.processors.event_processor import EventProcessor, ProcessingPipeline
from events_agent.utils.event_validator import EventValidator


def main(max_events: int = 100):
    """
    Main entry point for events crawler.

    Process:
    1. Initialize crawlers
    2. Fetch events from Luma and Meetup
    3. Save raw data to data/raw/
    4. Filter by NYC location
    5. Filter by current/next week
    6. Limit to max_events
    7. Save processed data to data/processed/
    8. Output JSON

    Args:
        max_events: Maximum number of events to return (default: 100)
    """
    print("=" * 60)
    print("Events Agent - Crawling Events from 5 Sources")
    print("Sources: Luma, Meetup, Fever, Cozymeal, Eventbrite")
    print(f"Max events: {max_events}")
    print("=" * 60)

    # Initialize components
    data_manager = DataManager()
    processor = EventProcessor(max_events=max_events)
    pipeline = ProcessingPipeline(processor)
    timestamp = datetime.now()

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

    # Process events through pipeline
    print("\n[Processing] Running event processing pipeline...")
    result = pipeline.run(
        raw_events_by_source=sources_events,
        save_raw=True,
        save_processed=True,
        data_manager=data_manager
    )

    filtered_events = result["events"]
    processed_file = result.get("processed_file", "N/A")

    # Validate event coverage and quality
    EventValidator.print_validation_report(filtered_events, target_days=14)

    # Also save to events_output.json for backwards compatibility
    output = {
        "timestamp": timestamp.isoformat(),
        "total_events": len(filtered_events),
        "filters": result.get("filters", {}),
        "stats": result.get("stats", {}),
        "events": [e.model_dump(mode='json') for e in filtered_events]
    }

    output_file = "events_output.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print(f"✓ Results saved to: {output_file}")
    print(f"✓ Processed data: {processed_file}")
    print(f"✓ Total events: {len(filtered_events)}")
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
