#!/usr/bin/env python3
"""
Example script demonstrating how to use the new jazz and Valentine's Day crawlers.

Usage:
    python examples/crawl_jazz_and_valentines.py
"""

from datetime import datetime
from playwright.sync_api import sync_playwright

from events_agent.database.connection import DatabaseConnection
from events_agent.database.schema import SchemaManager
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.crawlers.jazznearyou_crawler import JazzNearYouCrawler, SongkickCrawler
from events_agent.crawlers.timeout_crawler import TimeOutNYCCrawler, DoNYCCrawler
from events_agent.data import (
    is_known_jazz_venue,
    get_valentines_date_range,
    is_valentines_event,
)


def main():
    """Crawl jazz and Valentine's Day events and save to database."""
    
    print("🎵 Jazz & Valentine's Day Event Crawler")
    print("=" * 60)
    
    # Initialize database
    print("\n1️⃣ Initializing database...")
    db = DatabaseConnection('data/events.db')
    schema = SchemaManager(db)
    schema.initialize_schema()
    repo = SQLiteEventRepository(db)
    print("   ✅ Database ready")
    
    # Start browser
    print("\n2️⃣ Starting browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        print("   ✅ Browser started")
        
        all_events = []
        
        # Crawl Jazz Near You
        print("\n3️⃣ Crawling Jazz Near You...")
        try:
            jny_crawler = JazzNearYouCrawler()
            jazz_events = jny_crawler.crawl(browser, "nyc")
            print(f"   ✅ Found {len(jazz_events)} jazz events")
            if jazz_events:
                upserted = repo.upsert_many(jazz_events)
                print(f"   ✅ Upserted {upserted} to database")
            all_events.extend(jazz_events)
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

        # Crawl Songkick
        print("\n4️⃣ Crawling Songkick (Jazz)...")
        try:
            songkick_crawler = SongkickCrawler()
            songkick_events = songkick_crawler.crawl(browser, "nyc")
            print(f"   ✅ Found {len(songkick_events)} events from Songkick")
            if songkick_events:
                upserted = repo.upsert_many(songkick_events)
                print(f"   ✅ Upserted {upserted} to database")
            all_events.extend(songkick_events)
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

        # Crawl TimeOut Valentine's Day
        print("\n5️⃣ Crawling TimeOut NYC (Valentine's Day)...")
        try:
            timeout_vday = TimeOutNYCCrawler(category="valentines-day")
            vday_events = timeout_vday.crawl(browser, "newyork")
            print(f"   ✅ Found {len(vday_events)} Valentine's events")
            if vday_events:
                upserted = repo.upsert_many(vday_events)
                print(f"   ✅ Upserted {upserted} to database")
            all_events.extend(vday_events)
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

        # Crawl TimeOut Jazz
        print("\n6️⃣ Crawling TimeOut NYC (Jazz)...")
        try:
            timeout_jazz = TimeOutNYCCrawler(category="jazz")
            jazz_events_to = timeout_jazz.crawl(browser, "newyork")
            print(f"   ✅ Found {len(jazz_events_to)} jazz events")
            if jazz_events_to:
                upserted = repo.upsert_many(jazz_events_to)
                print(f"   ✅ Upserted {upserted} to database")
            all_events.extend(jazz_events_to)
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

        # Crawl DoNYC
        print("\n7️⃣ Crawling DoNYC (Valentine's Day)...")
        try:
            donyc_crawler = DoNYCCrawler()
            donyc_events = donyc_crawler.crawl(browser, "valentines-day")
            print(f"   ✅ Found {len(donyc_events)} events from DoNYC")
            if donyc_events:
                upserted = repo.upsert_many(donyc_events)
                print(f"   ✅ Upserted {upserted} to database")
            all_events.extend(donyc_events)
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
        
        browser.close()
    
    # Analysis
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    
    # Total events
    total_in_db = repo.count()
    print(f"\n📈 Total events in database: {total_in_db}")
    print(f"📥 Events crawled this session: {len(all_events)}")
    
    # Jazz events
    jazz_events_count = len([e for e in all_events if e.genre == "jazz" or (e.tags and "jazz" in e.tags)])
    print(f"\n🎷 Jazz events found: {jazz_events_count}")
    
    # Events at known venues
    venue_events = [e for e in all_events if e.location_name and is_known_jazz_venue(e.location_name)]
    print(f"🏛️ Events at famous jazz venues: {len(venue_events)}")
    if venue_events:
        print("\n   Famous venues with events:")
        venues = {}
        for event in venue_events:
            venue = event.location_name
            if venue not in venues:
                venues[venue] = 0
            venues[venue] += 1
        for venue, count in sorted(venues.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   - {venue}: {count} event(s)")
    
    # Valentine's events
    vday_start, vday_end = get_valentines_date_range(2026)
    vday_events = [e for e in all_events if e.start_datetime >= vday_start and e.start_datetime <= vday_end]
    vday_tagged = [e for e in vday_events if is_valentines_event(e.title, e.description, e.tags)]
    print(f"\n💝 Valentine's Day events (Feb 7-16): {len(vday_events)}")
    print(f"💕 Valentine's tagged events: {len(vday_tagged)}")
    
    # Show some examples
    print("\n🎵 Sample Jazz Events:")
    jazz_sample = [e for e in all_events if e.genre == "jazz"][:3]
    for event in jazz_sample:
        print(f"   - {event.title}")
        print(f"     📍 {event.location_name or 'TBA'}")
        print(f"     📅 {event.start_datetime.strftime('%b %d, %Y at %I:%M %p')}")
        print(f"     🔗 {event.url}")
        print()
    
    print("\n💝 Sample Valentine's Events:")
    vday_sample = vday_tagged[:3]
    for event in vday_sample:
        print(f"   - {event.title}")
        print(f"     📍 {event.location_name or 'TBA'}")
        print(f"     📅 {event.start_datetime.strftime('%b %d, %Y at %I:%M %p')}")
        price = "Free" if event.is_free else f"${event.price_cents/100:.2f}" if event.price_cents else "See link"
        print(f"     💰 {price}")
        print(f"     🔗 {event.url}")
        print()
    
    # SQL query examples
    print("\n" + "=" * 60)
    print("📝 Try these SQL queries:")
    print("=" * 60)
    print("""
    # Open database
    sqlite3 data/events.db
    
    # Find jazz events this week
    SELECT title, start_datetime, location_name, genre
    FROM events
    WHERE genre = 'jazz'
      AND start_datetime >= date('now')
      AND start_datetime < date('now', '+7 days')
    ORDER BY start_datetime;
    
    # Find Valentine's Day events
    SELECT title, start_datetime, location_name, tags
    FROM events
    WHERE (tags LIKE '%valentine%' OR title LIKE '%valentine%')
      AND start_datetime >= '2026-02-07'
      AND start_datetime <= '2026-02-16'
    ORDER BY start_datetime;
    
    # More queries in: queries/jazz_and_valentines.sql
    """)
    
    print("\n✅ Done! Check data/events.db for all events.")
    db.close()


if __name__ == "__main__":
    main()
