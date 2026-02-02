"""Test event detail scraper."""

import sys
sys.path.insert(0, 'src')

from playwright.sync_api import sync_playwright
from events_agent.crawlers.event_detail_scraper import EventDetailScraper
import json

def test_detail_scraper():
    """Test scraping event details."""

    # Test URLs
    test_events = [
        {
            "event_id": "312850971",
            "url": "https://www.meetup.com/psychedelic-yoga/events/312850971/",
            "title": "PSYCHEDELIC YOGA In-Person Workshop!"
        },
        {
            "event_id": "311953474",
            "url": "https://www.meetup.com/imeditateny/events/311953474/",
            "title": "Full Moon Meditation"
        },
        {
            "event_id": "312929997",
            "url": "https://www.meetup.com/nycconnects-social/events/312929997/",
            "title": "Museum Visit"
        }
    ]

    scraper = EventDetailScraper(rate_limit_seconds=1.0)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        results = []

        for i, event in enumerate(test_events, 1):
            print(f"\n[{i}/3] Scraping: {event['title']}")
            print(f"         URL: {event['url']}")

            details = scraper.scrape_event_details(page, event['url'])

            if details:
                # Enhance the base event
                enhanced = scraper.enhance_event(event, details)
                results.append(enhanced)

                # Show what we got
                print(f"  ✓ Description: {len(details.get('description', '') or '')} chars")
                ai_summary = details.get('ai_summary') or 'N/A'
                print(f"  ✓ AI Summary: {ai_summary[:60]}...")
                print(f"  ✓ Host: {details.get('host_name', 'N/A')}")
                print(f"  ✓ Group: {details.get('group_name', 'N/A')} ({details.get('group_rating', 'N/A')} stars)")
                print(f"  ✓ Venue: {details.get('venue_name', 'N/A')}")
                print(f"  ✓ Address: {details.get('full_address', 'N/A')}")
                print(f"  ✓ Attendees: {details.get('attendee_count', 'N/A')}")
                print(f"  ✓ Fee: ${details.get('fee_amount', 0)} ({details.get('payment_methods', 'N/A')})")
                print(f"  ✓ Topics: {', '.join(details.get('topics', [])[:3])}")
                if details.get('registration_url'):
                    print(f"  ✓ Registration: {details['registration_url'][:60]}...")
            else:
                print(f"  ✗ Failed to scrape details")

        browser.close()

        # Save results
        with open("detail_scraper_test_results.json", "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n{'='*60}")
        print(f"✓ Saved {len(results)} enhanced events to detail_scraper_test_results.json")
        print(f"{'='*60}")

if __name__ == "__main__":
    test_detail_scraper()
