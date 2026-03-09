#!/usr/bin/env python3
"""Run Tahoe SnowFest (Winterfest) crawler locally and save raw storage file.

Usage:
    python scripts/run_winterfest_crawler.py
"""

from __future__ import annotations

from datetime import datetime

from playwright.sync_api import sync_playwright

from events_agent.crawlers.winterfest_crawler import WinterfestCrawler
from events_agent.storage.data_manager import DataManager


def main() -> None:
    print("=" * 60)
    print("Winterfest Crawler - Tahoe SnowFest")
    print("=" * 60)

    crawler = WinterfestCrawler(rate_limit_seconds=1.0)
    data_manager = DataManager("data")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            events = crawler.crawl(browser, "tahoe")
        finally:
            browser.close()

    timestamp = datetime.now()
    raw_path = data_manager.save_raw_events("winterfest", events, timestamp)

    print(f"\nCollected: {len(events)} events")
    print(f"Raw file: {raw_path}")

    if events:
        print("\nSample events:")
        for i, event in enumerate(events[:5], 1):
            print(f"  {i}. {event.title}")
            print(f"     {event.start_datetime} | {event.city or 'N/A'}, {event.state or 'N/A'}")
            print(f"     {event.url}")


if __name__ == "__main__":
    main()
