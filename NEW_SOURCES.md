# New Event Sources - Jazz & Valentine's Day Events

## Overview

This document describes new event crawlers added to find jazz events and Valentine's Day activities in NYC.

## New Sources

### 🎵 Jazz-Specific Sources

#### 1. Jazz Near You (jazznearyou.com)
**Status**: Implementation ready  
**Crawler**: `JazzNearYouCrawler`  
**Coverage**: NYC jazz venues, national coverage  
**Data Quality**: High - dedicated jazz platform  

**Features**:
- Venue-specific listings
- Artist/performer information
- Date filtering
- 80+ NYC venues tracked

**Usage**:
```python
from events_agent.crawlers.jazznearyou_crawler import JazzNearYouCrawler
crawler = JazzNearYouCrawler()
events = crawler.crawl(browser, "nyc")
```

#### 2. Songkick
**Status**: Implementation ready  
**Crawler**: `SongkickCrawler`  
**Coverage**: All music genres including jazz  
**Data Quality**: Very high - professional platform  

**Features**:
- Genre filtering (jazz, blues, etc.)
- Venue information
- Artist tracking
- Tour dates

**Usage**:
```python
from events_agent.crawlers.jazznearyou_crawler import SongkickCrawler
crawler = SongkickCrawler()
events = crawler.crawl(browser, "nyc")  # Jazz events only
```

### 💝 Valentine's Day & Cultural Events

#### 3. TimeOut NYC
**Status**: Implementation ready  
**Crawler**: `TimeOutNYCCrawler`  
**Coverage**: All NYC cultural events  
**Data Quality**: Very high - professional curation  

**Features**:
- Valentine's Day specific section
- Jazz club listings
- Seasonal events
- Food & drink events
- Category-based browsing

**Usage**:
```python
from events_agent.crawlers.timeout_crawler import TimeOutNYCCrawler

# Valentine's Day events
vday_crawler = TimeOutNYCCrawler(category="valentines-day")
vday_events = vday_crawler.crawl(browser, "newyork")

# Jazz events
jazz_crawler = TimeOutNYCCrawler(category="jazz")
jazz_events = jazz_crawler.crawl(browser, "newyork")

# All events
all_crawler = TimeOutNYCCrawler(category="events-calendar")
all_events = all_crawler.crawl(browser, "newyork")
```

#### 4. DoNYC (donyc.com)
**Status**: Implementation ready  
**Crawler**: `DoNYCCrawler`  
**Coverage**: Curated NYC events  
**Data Quality**: High - human-curated  

**Features**:
- Valentine's Day section
- Galentine's Day events
- Seasonal events
- Singles events
- Curated recommendations

**Usage**:
```python
from events_agent.crawlers.timeout_crawler import DoNYCCrawler

crawler = DoNYCCrawler()
events = crawler.crawl(browser, "valentines-day")
```

## Data Model Enhancements

### New EventSource Values

```python
class EventSource(str, Enum):
    # Existing
    LUMA = "luma"
    MEETUP = "meetup"
    FEVER = "fever"
    COZYMEAL = "cozymeal"
    EVENTBRITE = "eventbrite"
    
    # New sources
    JAZZNEARYOU = "jazznearyou"
    SONGKICK = "songkick"
    TIMEOUT = "timeout"
    DONYC = "donyc"
    RESIDENTADVISOR = "residentadvisor"
    BANDSINTOWN = "bandsintown"
```

### Enhanced Event Fields

The Event model now includes:

**Music/Performance Fields**:
- `genre` (str): "jazz", "blues", "rock", etc.
- `performer_names` (List[str]): Artist names
- `duration_minutes` (int): Event duration

**Categorization**:
- `experience_type` (str): "concert", "cooking class", etc.
- `category` (str): "music", "food", "entertainment"
- `tags` (List[str]): ["jazz", "valentines-day", "date-night"]

**Enhanced Content**:
- `image_url` (str): Event image
- `ai_summary` (str): AI-generated summary
- `topics` (List[str]): Event topics

**See full schema**: `src/events_agent/models/event.py`

## Jazz Venue Index

A comprehensive index of major NYC jazz venues with metadata.

**Location**: `src/events_agent/data/jazz_venues.py`

**Features**:
- 15+ major jazz venues
- Address and location data
- Capacity information
- Venue type classification
- Neighborhood grouping

**Usage**:
```python
from events_agent.data.jazz_venues import (
    NYC_JAZZ_VENUES,
    get_venue_by_name,
    get_venues_by_neighborhood,
    is_known_jazz_venue,
)

# Check if venue is known jazz venue
if is_known_jazz_venue("Blue Note"):
    print("This is a famous jazz club!")

# Get venue details
venue = get_venue_by_name("Village Vanguard")
print(f"{venue.name} - {venue.address}")
print(f"Capacity: {venue.capacity}")

# Get all Greenwich Village jazz venues
gv_venues = get_venues_by_neighborhood("Greenwich Village")
```

**Venues Included**:
- **Greenwich Village**: Village Vanguard, Blue Note, Smalls, Mezzrow, Zinc Bar
- **Midtown**: Birdland, Iridium, Dizzy's Club, Somethin' Jazz
- **Harlem**: Minton's Playhouse, Bill's Place
- **Other**: The Jazz Gallery, Roulette, Nublu, The Django

## Seasonal Event Detection

Utilities for detecting and filtering seasonal/holiday events.

**Location**: `src/events_agent/data/seasonal_events.py`

**Features**:
- Valentine's Day date range calculation
- Keyword-based event detection
- Date-night event identification
- Popular romantic neighborhood list

**Usage**:
```python
from events_agent.data.seasonal_events import (
    get_valentines_date_range,
    is_valentines_event,
    is_date_night_event,
    ROMANTIC_NEIGHBORHOODS,
)

# Get Valentine's Day date range (Feb 7-16)
start, end = get_valentines_date_range(2026)

# Check if event is Valentine's related
if is_valentines_event(
    title="Romantic Jazz Night for Couples",
    description="Perfect date night experience",
    tags=["jazz", "romantic"]
):
    print("This is a Valentine's event!")

# Check if event type is date-night appropriate
if is_date_night_event(
    event_type="cooking class",
    tags=["couples", "date-night"]
):
    print("Great for a date!")
```

## Database Schema Update

The database schema has been upgraded to version 2 with enhanced fields.

**Migration**: Automatic on next run  
**New Fields**: 25+ new columns for music, performance, and enhanced data  
**Indexes**: New indexes on genre, category, experience_type, rating  

**SQL Queries**:

```sql
-- Find all jazz events this week
SELECT title, start_datetime, location_name, genre, performer_names
FROM events
WHERE genre = 'jazz'
  AND city = 'New York'
  AND start_datetime >= date('now', 'weekday 1')
  AND start_datetime < date('now', 'weekday 1', '+7 days')
ORDER BY start_datetime;

-- Find Valentine's Day events
SELECT title, start_datetime, location_name, tags
FROM events
WHERE tags LIKE '%valentines%'
  AND start_datetime >= '2026-02-07'
  AND start_datetime <= '2026-02-16'
ORDER BY start_datetime;

-- Find events at known jazz venues
SELECT e.title, e.start_datetime, e.location_name, e.genre
FROM events e
WHERE e.location_name IN (
  'Village Vanguard', 'Blue Note', 'Smalls', 'Birdland',
  'Dizzy''s Club', 'Jazz Gallery', 'Mezzrow'
)
ORDER BY e.start_datetime;

-- Find high-rated date-night events
SELECT title, rating, experience_type, price_cents, location_name
FROM events
WHERE rating >= 4.0
  AND experience_type IN ('cooking class', 'wine tasting', 'concert', 'comedy')
  AND city = 'New York'
ORDER BY rating DESC, review_count DESC
LIMIT 20;
```

## Integration Guide

### Add to main.py

```python
# In main.py, add new crawlers:

from events_agent.crawlers.jazznearyou_crawler import JazzNearYouCrawler, SongkickCrawler
from events_agent.crawlers.timeout_crawler import TimeOutNYCCrawler, DoNYCCrawler

def main(max_events: int = 100):
    # ... existing setup ...
    
    all_events = []
    
    # Existing crawlers
    luma_events = luma_crawler.crawl(browser, "nyc")
    meetup_events = meetup_crawler.crawl(browser, "new-york-ny")
    # ... etc ...
    
    # NEW: Jazz-specific sources
    print("\n📀 Crawling Jazz Near You...")
    jazznearyou_crawler = JazzNearYouCrawler()
    jazz_events = jazznearyou_crawler.crawl(browser, "nyc")
    repo.save_many(jazz_events)
    all_events.extend(jazz_events)
    
    print("\n🎸 Crawling Songkick (Jazz)...")
    songkick_crawler = SongkickCrawler()
    songkick_events = songkick_crawler.crawl(browser, "nyc")
    repo.save_many(songkick_events)
    all_events.extend(songkick_events)
    
    # NEW: Cultural/seasonal events
    print("\n💝 Crawling TimeOut NYC (Valentine's Day)...")
    timeout_vday = TimeOutNYCCrawler(category="valentines-day")
    vday_events = timeout_vday.crawl(browser, "newyork")
    repo.save_many(vday_events)
    all_events.extend(vday_events)
    
    print("\n🎭 Crawling TimeOut NYC (Jazz)...")
    timeout_jazz = TimeOutNYCCrawler(category="jazz")
    timeout_jazz_events = timeout_jazz.crawl(browser, "newyork")
    repo.save_many(timeout_jazz_events)
    all_events.extend(timeout_jazz_events)
    
    print("\n❤️ Crawling DoNYC (Valentine's Day)...")
    donyc_crawler = DoNYCCrawler()
    donyc_events = donyc_crawler.crawl(browser, "valentines-day")
    repo.save_many(donyc_events)
    all_events.extend(donyc_events)
    
    # ... rest of filtering/processing ...
```

### Query Examples

```python
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.data.jazz_venues import is_known_jazz_venue
from events_agent.data.seasonal_events import is_valentines_event

# Get all jazz events
jazz_events = repo.find_by_filters({"genre": "jazz", "city": "New York"})

# Get Valentine's Day events
from datetime import datetime
vday_start, vday_end = get_valentines_date_range(2026)
vday_events = repo.find_by_date_range(vday_start, vday_end)
vday_events = [e for e in vday_events if is_valentines_event(e.title, e.description, e.tags)]

# Get events at known jazz venues
all_events = repo.find_all()
jazz_venue_events = [e for e in all_events if e.location_name and is_known_jazz_venue(e.location_name)]
```

## Future Enhancements

### Additional Jazz Sources

1. **Hot House Jazz Guide** (hothousejazzguide.com)
   - Very current NYC jazz calendar
   - Neighborhood filtering
   - Venue details

2. **Jazz Listings** (jazzlistings.com)
   - Comprehensive NYC coverage
   - 80+ venues tracked
   - Genre filtering

3. **Resident Advisor**
   - Electronic/experimental music
   - Some jazz/fusion events
   - Has scraper available (Apify)

4. **Bandsintown**
   - Artist-based event discovery
   - Has official API
   - Good for tracking specific artists

### Individual Venue Crawlers

Create dedicated crawlers for major venues:
- Blue Note Jazz Club
- Village Vanguard
- Birdland
- Smalls/Mezzrow
- Jazz at Lincoln Center

### Enhanced Filtering

Add repository methods for:
- Genre-based queries
- Venue-based queries
- Price range filtering
- Rating/review filtering
- Tag-based search

### Event Enrichment

- Fetch performer bios from MusicBrainz
- Add Spotify links for artists
- Fetch venue photos from Google Places
- AI-generate event summaries
- Sentiment analysis on reviews

## Testing

### Unit Tests

```bash
# Test new crawlers
pytest tests/unit/test_jazznearyou_crawler.py
pytest tests/unit/test_timeout_crawler.py
pytest tests/unit/test_jazz_venues.py
pytest tests/unit/test_seasonal_events.py
```

### Integration Tests

```bash
# Test full flow with new sources
pytest tests/integration/test_new_sources_flow.py -v
```

## Troubleshooting

### Common Issues

1. **No events returned from Jazz Near You**
   - Check if site structure has changed
   - Verify CSS selectors
   - Check for bot detection

2. **TimeOut returns non-event pages**
   - Filter by URL pattern (`/things-to-do/`, `/events/`)
   - Check category parameter

3. **Genre detection not working**
   - Update keyword lists in parsers
   - Check if genre field is populated
   - Verify tags are being extracted

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug logging for new crawlers
logging.getLogger("events_agent.crawlers.jazznearyou_crawler").setLevel(logging.DEBUG)
logging.getLogger("events_agent.crawlers.timeout_crawler").setLevel(logging.DEBUG)
```

## Resources

- **Jazz Near You**: https://www.jazznearyou.com/nyc
- **Songkick NYC Jazz**: https://www.songkick.com/metro-areas/7644-us-new-york-nyc/genre/jazz
- **TimeOut NYC Events**: https://www.timeout.com/newyork/events-calendar
- **TimeOut Valentine's**: https://www.timeout.com/newyork/valentines-day
- **DoNYC Valentine's**: https://donyc.com/valentines-day
- **Hot House Jazz**: https://hothousejazzguide.com/calendar
- **Jazz Listings**: https://jazzlistings.com/

---

**Last Updated**: 2026-02-10  
**Version**: 0.2.0  
**Status**: ✅ Ready for integration
