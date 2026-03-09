#!/usr/bin/env python3
"""Run Town of Mammoth calendar crawler locally."""

from playwright.sync_api import sync_playwright

from events_agent.crawlers.townofmammoth_crawler import TownOfMammothCrawler


def main() -> None:
    """Run crawler and print sample events."""
    crawler = TownOfMammothCrawler(category_id=None, max_events=40)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        events = crawler.crawl(browser, "mammoth")
        browser.close()

    print("=" * 60)
    print(f"Collected {len(events)} Town of Mammoth events")
    print("=" * 60)
    for i, event in enumerate(events[:10], 1):
        print(f"{i}. {event.title}")
        print(f"   Date: {event.start_datetime}")
        print(f"   Location: {event.location_name or 'N/A'}")
        print(f"   URL: {event.url}")


if __name__ == "__main__":
    main()
