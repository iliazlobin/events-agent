"""Crawl Feb 1-14 events with full details from individual pages."""

import sys
sys.path.insert(0, 'src')

from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
from events_agent.crawlers.meetup_crawler import MeetupCrawler
from events_agent.crawlers.event_detail_scraper import EventDetailScraper
from events_agent.models.event import Event
import json

def crawl_feb1_14_with_details():
    """Crawl Feb 1-14 with detailed data from event pages."""

    print("="*60)
    print("Meetup Crawler: Feb 1-14 with Full Details")
    print("="*60)

    # Create crawlers
    list_crawler = MeetupCrawler(
        rate_limit_seconds=0,
        max_events_total=100,  # Limit to 100 total
        max_events_per_day=10,  # 10 per day to spread across 14 days
        distance_miles=10,
        event_type="inPerson"
    )

    detail_scraper = EventDetailScraper(rate_limit_seconds=1.0)

    # Date range: Feb 1-14
    start_date = datetime(2026, 2, 1, 0, 0, 0)
    end_date = datetime(2026, 2, 14, 23, 59, 59)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        list_page = context.new_page()
        detail_page = context.new_page()

        # Step 1: Get list of events
        print(f"\n[Step 1] Crawling event list (Feb 1-14)...")
        url = list_crawler.get_events_url("New York, NY", start_date, end_date)
        print(f"URL: {url[:80]}...")

        list_page.goto(url, wait_until='domcontentloaded', timeout=120000)
        basic_events = list_crawler.extract_events_from_page(list_page)

        print(f"\n✓ Found {len(basic_events)} events from list page")

        # Step 2: Scrape details for each event
        print(f"\n[Step 2] Scraping details for each event...")
        print(f"(This will take ~{len(basic_events)} seconds with 1s rate limit)\n")

        enhanced_events = []
        failed_count = 0

        for i, event in enumerate(basic_events, 1):
            print(f"[{i}/{len(basic_events)}] {event.title[:50]}")

            # Scrape detail page
            details = detail_scraper.scrape_event_details(detail_page, str(event.url))

            if details:
                # Convert event to dict
                event_dict = event.model_dump(mode='json')

                # Enhance with details
                enhanced_dict = detail_scraper.enhance_event(event_dict, details)

                # Create enhanced Event object
                try:
                    enhanced_event = Event(**enhanced_dict)
                    enhanced_events.append(enhanced_event)

                    # Show what we got
                    print(f"  ✓ Attendees: {details.get('attendee_count', 'N/A')}, "
                          f"Fee: ${details.get('fee_amount') or 0}, "
                          f"Topics: {len(details.get('topics', []))}")

                except Exception as e:
                    print(f"  ✗ Error creating Event: {e}")
                    enhanced_events.append(event)  # Use basic event
                    failed_count += 1
            else:
                print(f"  ⚠️  Using basic data (detail scrape failed)")
                enhanced_events.append(event)
                failed_count += 1

        browser.close()

    # Step 3: Save results
    print(f"\n[Step 3] Saving results...")

    output = {
        "date_range": {
            "start": "2026-02-01",
            "end": "2026-02-14"
        },
        "location": "New York, NY",
        "total_events": len(enhanced_events),
        "detail_scraped": len(enhanced_events) - failed_count,
        "basic_only": failed_count,
        "events": [e.model_dump(mode='json') for e in enhanced_events]
    }

    filename = "data/raw/meetup_feb1_14_detailed.json"
    with open(filename, "w") as f:
        json.dump(output, f, indent=2)

    print(f"✓ Saved to {filename}")

    # Statistics
    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"  Total events: {len(enhanced_events)}")
    print(f"  With full details: {len(enhanced_events) - failed_count}")
    print(f"  Basic data only: {failed_count}")

    # Date distribution
    by_date = {}
    for event in enhanced_events:
        date = event.start_datetime.date()
        by_date[date] = by_date.get(date, 0) + 1

    print(f"\n  Date distribution:")
    for date in sorted(by_date.keys()):
        count = by_date[date]
        print(f"    {date}: {count} events")

    # Data completeness
    with_desc = sum(1 for e in enhanced_events if e.description)
    with_host = sum(1 for e in enhanced_events if e.host_name)
    with_fee = sum(1 for e in enhanced_events if e.fee_amount is not None)
    with_topics = sum(1 for e in enhanced_events if e.topics)

    print(f"\n  Data completeness:")
    print(f"    Descriptions: {with_desc}/{len(enhanced_events)}")
    print(f"    Host names: {with_host}/{len(enhanced_events)}")
    print(f"    Fee info: {with_fee}/{len(enhanced_events)}")
    print(f"    Topics: {with_topics}/{len(enhanced_events)}")

    print(f"{'='*60}")

    return len(enhanced_events)

if __name__ == "__main__":
    count = crawl_feb1_14_with_details()
    print(f"\n✅ Successfully crawled {count} events with detailed data!")
