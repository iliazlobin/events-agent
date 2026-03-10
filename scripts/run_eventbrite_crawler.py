#!/usr/bin/env python3
"""Run Eventbrite crawler only - for local testing and SLA verification.

SLA: 100+ events within 5 minutes.
Usage: python scripts/run_eventbrite_crawler.py
"""

import time
from playwright.sync_api import sync_playwright

from events_agent.legacy_crawlers.eventbrite_crawler import EventbriteCrawler


def main() -> None:
    """Run Eventbrite crawler and report timing + event count."""
    sla_events = 100
    sla_seconds = 300  # 5 minutes

    print("=" * 60)
    print("Eventbrite Crawler - Local Run")
    print(f"SLA: {sla_events}+ events within {sla_seconds // 60} minutes")
    print("=" * 60)

    crawler = EventbriteCrawler(
        rate_limit_seconds=1.0,
        max_events=150,
        max_pages=6,
    )

    start = time.perf_counter()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        events = crawler.crawl(browser, "nyc")
        browser.close()
    elapsed = time.perf_counter() - start

    print("\n" + "=" * 60)
    print(f"Collected: {len(events)} events")
    print(f"Duration: {elapsed:.1f}s ({elapsed / 60:.1f} min)")
    print("=" * 60)

    if len(events) >= sla_events and elapsed <= sla_seconds:
        print(f"✓ SLA MET: {len(events)} events in {elapsed:.1f}s")
    else:
        status = []
        if len(events) < sla_events:
            status.append(f"events={len(events)} < {sla_events}")
        if elapsed > sla_seconds:
            status.append(f"time={elapsed:.1f}s > {sla_seconds}s")
        print(f"✗ SLA NOT MET: {', '.join(status)}")

    if events:
        print("\nSample events:")
        for i, e in enumerate(events[:5], 1):
            print(f"  {i}. {e.title[:60]}...")
            print(f"     {e.start_datetime} | {e.city or 'N/A'}")


if __name__ == "__main__":
    main()
