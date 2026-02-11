# Events Agent - Comprehensive Guide

## Overview

The Events Agent is a web scraping system that automatically discovers, filters, and organizes event data from multiple sources (Luma.com and Meetup.com). It's designed to help you find relevant events in NYC for the current and next week.

### Key Features

- **Multi-Source Crawling**: Fetches events from 9 sources:
  - General: Luma, Meetup, Eventbrite, Fever, Cozymeal
  - Jazz: Jazz Near You, Songkick
  - Cultural/Seasonal: TimeOut NYC, DoNYC
- **Smart Filtering**: Location-based (NYC) and date-based (current + next week) filtering via SQL
- **Event Categorization**: Genre, experience type, tags for jazz, Valentine's Day, and more
- **Jazz Venue Index**: 15+ major NYC jazz venues with metadata
- **Seasonal Detection**: Valentine's Day and holiday event identification
- **Data Organization**: SQLite database with automatic deduplication
- **Event Limits**: Configurable maximum events (default: 100)
- **Structured Output**: Pydantic-validated JSON with comprehensive event details
- **Comprehensive Testing**: 104 tests (93 unit + 11 integration)

## Quick Start

### Installation

```bash
# 1. Clone or navigate to the project directory
cd /Users/iliazlobin/Code/events-agent

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -e .

# 4. Install Playwright browsers (required for web scraping)
playwright install chromium
```

### Basic Usage

```bash
# Run the crawler (default: 100 event limit)
python -m events_agent.main

# Or use the CLI command
events-crawler
```

## Architecture

### Project Structure

```
events-agent/
├── src/events_agent/
│   ├── models/
│   │   └── event.py              # Pydantic Event model with validation
│   ├── database/                 # Database management
│   │   ├── connection.py         # Thread-safe connection pooling
│   │   ├── schema.py             # Schema definitions + migrations
│   │   └── __init__.py
│   ├── repositories/             # Repository pattern
│   │   ├── base.py               # Abstract Repository interface
│   │   ├── event_repository.py   # Event repository interface (CRUD + queries)
│   │   ├── sqlite_repository.py  # SQLite implementation
│   │   ├── json_repository.py    # JSON export for debugging
│   │   └── __init__.py
│   ├── data/                     # Reference data & utilities
│   │   ├── jazz_venues.py        # NYC jazz venue index (15+ venues)
│   │   ├── seasonal_events.py    # Valentine's Day & holiday detection
│   │   └── __init__.py
│   ├── crawlers/
│   │   ├── base.py               # Abstract base crawler class
│   │   ├── luma_crawler.py       # Luma.com implementation
│   │   ├── meetup_crawler.py     # Meetup.com re-export (refactored)
│   │   ├── fever_crawler.py      # Fever.com implementation
│   │   ├── cozymeal_crawler.py   # Cozymeal.com implementation
│   │   ├── eventbrite_crawler.py # Eventbrite.com implementation
│   │   ├── jazznearyou_crawler.py # Jazz Near You + Songkick
│   │   ├── timeout_crawler.py    # TimeOut NYC + DoNYC
│   │   └── meetup/               # Meetup crawler module (SOLID refactor)
│   │       ├── __init__.py       # Module exports
│   │       ├── meetup_crawler.py # Main orchestration (~230 lines)
│   │       ├── url_builder.py    # URL construction
│   │       ├── page_scroller.py  # Infinite scroll handling
│   │       ├── dom_extractor.py  # DOM event extraction
│   │       ├── apollo_parser.py  # Apollo state parsing
│   │       ├── event_transformer.py # Raw data → Event model
│   │       └── constants.py      # Configuration constants
│   ├── filters/
│   │   ├── date_filter.py        # Date utilities (kept for compatibility)
│   │   └── location_filter.py    # Location utilities (kept for compatibility)
│   ├── storage/
│   │   └── data_manager.py       # Legacy JSON storage (deprecated)
│   ├── utils/
│   │   └── date_utils.py         # Date parsing and timezone helpers
│   └── main.py                   # CLI entry point
├── tests/
│   ├── fixtures/                 # HTML samples for testing
│   ├── unit/                     # Unit tests (93 tests)
│   │   ├── test_database.py      # Database connection & schema tests
│   │   ├── test_repositories.py  # Repository tests
│   │   └── ...
│   └── integration/              # Integration tests (11 tests)
│       ├── test_sqlite_flow.py   # Full SQLite flow tests
│       └── ...
├── data/
│   ├── events.db                 # SQLite database (PRIMARY STORAGE)
│   ├── events.db-shm             # Shared memory file (WAL mode)
│   ├── events.db-wal             # Write-ahead log (WAL mode)
│   ├── raw/                      # Legacy JSON files (deprecated)
│   ├── processed/                # Legacy JSON files (deprecated)
│   └── debug/                    # Debug JSON exports (gitignored)
├── queries/
│   ├── quick_analysis.sql        # SQL queries for analysis
│   └── jazz_and_valentines.sql   # Jazz & Valentine's queries (70+ examples)
├── examples/
│   └── crawl_jazz_and_valentines.py # Example usage script
├── scripts/                      # Ad-hoc utility scripts
│   └── migrate_json_to_sqlite.py # JSON to SQLite migration
├── docs/archive/                 # Old implementation docs
├── pyproject.toml                # Dependencies and tool configuration
├── SQLITE_MIGRATION.md           # SQLite migration documentation
├── NEW_SOURCES.md                # Jazz & Valentine's Day sources documentation
├── IMPLEMENTATION_SUMMARY.md     # Implementation summary
└── README.md                     # User documentation
```

### Data Flow

```
┌─────────────────────────────────────┐
│ 5 Event Sources                     │
│ - Luma.com                          │
│ - Meetup.com                        │  1. Crawl Sources
│ - Eventbrite.com                    │
│ - Fever.com                         │
│ - Cozymeal.com                      │
└─────────────────────────────────────┘
                     │
                     ▼
              ┌──────────────────────┐
              │ SQLite Repository    │  2. Save to Database
              │ (Automatic Dedupe)   │     (data/events.db)
              └──────────────────────┘
                     │
                     ▼
              ┌──────────────────────┐
              │ SQL Query            │  3. Filter Events
              │ - Location: NYC      │     (Single Query)
              │ - Date: Current/Next │
              │ - Limit: 100         │
              └──────────────────────┘
                     │
                     ▼
              ┌──────────────────────┐
              │ Filtered Events      │  4. Return Results
              │ (Event objects)      │
              └──────────────────────┘
                     │
                     ▼
              ┌──────────────────────┐
              │ JSON Export          │  5. Debug/Backwards
              │ data/debug/          │     Compatibility
              └──────────────────────┘
```

## Data Organization

### Primary Storage: SQLite Database

**Location**: `/Users/iliazlobin/Code/events-agent/data/events.db`

The SQLite database is the **primary storage** for all event data. All crawlers save directly to this database.

**Database Schema**:

```sql
-- events table (22 columns)
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Required fields
    event_id TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    start_datetime TIMESTAMP NOT NULL,
    -- Optional fields
    description TEXT,
    end_datetime TIMESTAMP,
    location_name TEXT,
    location_address TEXT,
    city TEXT,
    state TEXT,
    is_online BOOLEAN DEFAULT 0,
    attendee_count INTEGER,
    capacity INTEGER,
    spots_remaining INTEGER,
    price_cents INTEGER,
    currency TEXT DEFAULT 'USD',
    is_free BOOLEAN DEFAULT 1,
    organizer_name TEXT,
    organizer_url TEXT,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Prevents duplicates
    UNIQUE(event_id, source)
);

-- Performance indexes
CREATE INDEX idx_events_location_datetime ON events(city, state, start_datetime);
CREATE INDEX idx_events_source_datetime ON events(source, start_datetime);
-- + 6 more indexes

-- Tracks each crawl operation
CREATE TABLE crawl_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    events_crawled INTEGER DEFAULT 0,
    status TEXT DEFAULT 'in_progress'
);

-- Manages database migrations
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
```

### Directory Structure

```
data/
├── events.db                 # SQLite database (PRIMARY STORAGE)
├── events.db-shm             # Shared memory file (WAL mode)
├── events.db-wal             # Write-ahead log (WAL mode)
├── raw/                      # DEPRECATED: Legacy JSON files
├── processed/                # DEPRECATED: Legacy JSON files
└── debug/                    # JSON exports for debugging (gitignored)
```

**Important**:
- JSON files in `data/raw/` and `data/processed/` are deprecated
- All crawlers now save to SQLite database
- JSON export is available in `data/debug/` for debugging only

### Querying the Database

**Using SQL directly**:

```bash
# Open database in sqlite3 CLI
sqlite3 data/events.db

# Or use DB Browser for SQLite (GUI)
open data/events.db
```

**Example SQL queries** (see `queries/quick_analysis.sql` for more):

```sql
-- Count events by source
SELECT source, COUNT(*) as count
FROM events
GROUP BY source
ORDER BY count DESC;

-- NYC events this weekend
SELECT title, start_datetime, location_name, url
FROM events
WHERE city LIKE '%New York%'
  AND state = 'NY'
  AND DATE(start_datetime) >= date('now', 'weekday 5')  -- This Friday
  AND DATE(start_datetime) <= date('now', 'weekday 6')  -- This Saturday
ORDER BY start_datetime;

-- Price distribution
SELECT
    CASE
        WHEN is_free = 1 THEN 'Free'
        WHEN price_cents < 1000 THEN '$0-10'
        WHEN price_cents < 2500 THEN '$10-25'
        ELSE '$25+'
    END as price_range,
    COUNT(*) as count
FROM events
GROUP BY price_range;
```

### Legacy JSON Format (Deprecated)

JSON files are no longer used for primary storage, but are still available for debugging.

**Debug Export**: `data/debug/{source}_{timestamp}.json`

```json
{
  "source": "luma",
  "timestamp": "2026-02-10T21:35:54.504309",
  "count": 29,
  "events": [
    {
      "event_id": "evt-abc123",
      "source": "luma",
      "url": "https://lu.ma/event-slug",
      "title": "Event Title",
      // ... same structure as database
    }
  ]
}
```

## SQLite Database

### Database Location

**Primary database**: `/Users/iliazlobin/Code/events-agent/data/events.db`

All crawled events are stored in this SQLite database with automatic deduplication.

### Key Benefits

✅ **10-100x faster queries** - SQL indexes vs in-memory filtering
✅ **Automatic deduplication** - UNIQUE(event_id, source) constraint
✅ **Historical tracking** - Query any past crawl
✅ **Analytics support** - Count, aggregate, trend analysis
✅ **Concurrent reads** - WAL mode supports multiple readers
✅ **No new dependencies** - SQLite built into Python

### Schema Overview

**events table** (22 columns):
- Required: event_id, source, url, title, start_datetime
- Optional: location, pricing, organizer, description
- Automatic: crawled_at timestamp, auto-incrementing id
- Constraint: UNIQUE(event_id, source) prevents duplicates

**crawl_sessions table**:
- Tracks each crawl operation
- Stores source, timestamps, events_crawled count

**schema_version table**:
- Manages database migrations
- Tracks applied schema versions

### Indexes for Performance

```sql
CREATE INDEX idx_events_location_datetime ON events(city, state, start_datetime);
CREATE INDEX idx_events_source_datetime ON events(source, start_datetime);
CREATE INDEX idx_events_start_datetime ON events(start_datetime);
CREATE INDEX idx_events_city ON events(city);
CREATE INDEX idx_events_source ON events(source);
CREATE INDEX idx_events_event_id ON events(event_id);
CREATE INDEX idx_events_is_online ON events(is_online);
CREATE INDEX idx_events_is_free ON events(is_free);
```

### Querying Options

**1. Python via Repository** (Recommended):
```python
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.database.connection import DatabaseConnection

db = DatabaseConnection('data/events.db')
repo = SQLiteEventRepository(db)
events = repo.find_by_location_and_date(start, end, "new york", "NY")
```

**2. SQL CLI**:
```bash
sqlite3 data/events.db "SELECT title, start_datetime FROM events LIMIT 10"
```

**3. DB Browser for SQLite** (GUI):
```bash
open data/events.db  # macOS
# Or download from https://sqlitebrowser.org/
```

**4. Pre-written SQL queries**:
```bash
# See queries/quick_analysis.sql for ready-to-use queries
# Open in VSCode with SQLite extension
```

### WAL Mode

The database uses Write-Ahead Logging (WAL) mode for better concurrency:
- Multiple processes can read simultaneously
- Readers don't block writers
- Creates `.db-shm` and `.db-wal` files (normal behavior)

### Migration

To migrate existing JSON files to SQLite:

```bash
python scripts/migrate_json_to_sqlite.py
```

See `SQLITE_MIGRATION.md` for detailed migration documentation.

## Event Model

### Required Fields

- `event_id` (str): Unique ID from source platform
- `source` (EventSource): "luma" or "meetup"
- `url` (HttpUrl): Full event page URL
- `title` (str): Event title (min length: 1)
- `start_datetime` (datetime): Event start time (UTC)

### Optional Fields

- `description` (str): Event description
- `end_datetime` (datetime): Event end time
- `location_name` (str): Venue name
- `location_address` (str): Full address
- `city` (str): City name
- `state` (str): State/Province
- `is_online` (bool): Virtual event flag (default: False)
- `attendee_count` (int): Number of attendees/RSVPs
- `capacity` (int): Max capacity
- `spots_remaining` (int): Available spots
- `price_cents` (int): Price in cents
- `currency` (str): Currency code (default: "USD")
- `is_free` (bool): Free event flag (default: True)
- `organizer_name` (str): Host/organizer name
- `organizer_url` (HttpUrl): Organizer profile URL

### Enhanced Event Fields

The Event model now includes 25+ additional fields for music, performance, and seasonal events:

**Music/Performance Fields**:
- `genre` (str): "jazz", "blues", "rock", "classical", etc.
- `performer_names` (List[str]): List of artist/performer names
- `duration_minutes` (int): Event duration in minutes

**Categorization Fields**:
- `experience_type` (str): "concert", "cooking class", "comedy", "magic", etc.
- `category` (str): "music", "food", "entertainment", "art"
- `tags` (List[str]): ["jazz", "valentines-day", "date-night", "romantic"]

**Enhanced Content**:
- `image_url` (str): Main event image URL
- `ai_summary` (str): AI-generated event summary
- `topics` (List[str]): Event topics/keywords

**Host/Organizer Details**:
- `host_name` (str): Individual host name
- `host_bio` (str): Host biography
- `group_name` (str): Meetup group name
- `group_rating` (float): Group rating (0-5)
- `group_review_count` (int): Number of group reviews

**Cooking Class Fields**:
- `chef_name` (str): Chef name
- `chef_rating` (float): Chef rating (0-5)
- `chef_bio` (str): Chef biography
- `skill_level` (str): "beginner", "intermediate", "advanced"
- `cuisine_type` (str): "Italian", "French", "Asian", etc.

**Enhanced Ratings**:
- `rating` (float): Event rating (0-5)
- `review_count` (int): Number of reviews

**Enhanced Location**:
- `latitude` (float): Venue latitude
- `longitude` (float): Venue longitude
- `directions` (str): Directions to venue

**Enhanced Pricing**:
- `fee_amount` (float): Additional fee amount
- `fee_required` (bool): Whether fee is required
- `payment_methods` (str): Accepted payment methods

**External Links**:
- `registration_url` (str): External registration URL

**Metadata**:
- `detail_crawled` (bool): Whether detail page was crawled

### Validation Rules

- `end_datetime` must be after `start_datetime`
- Numeric fields must be >= 0
- URLs must be valid
- Title cannot be empty

## Data Infrastructure

### Jazz Venue Index

A comprehensive index of major NYC jazz venues with metadata for venue-based filtering and enrichment.

**Location**: `src/events_agent/data/jazz_venues.py`

**Features**:
- 15+ major NYC jazz venues with complete metadata
- Neighborhood groupings (Greenwich Village, Midtown, Harlem, etc.)
- Capacity information
- Venue type classification (club, bar, concert-hall, restaurant)
- Website URLs
- Historic notes

**Venues Included**:
- **Greenwich Village**: Village Vanguard, Blue Note, Smalls, Mezzrow, Zinc Bar
- **Midtown**: Birdland, Iridium, Dizzy's Club, Somethin' Jazz Club
- **Harlem**: Minton's Playhouse, Bill's Place
- **Other**: Jazz Gallery, Roulette, Nublu, The Django

**Usage**:
```python
from events_agent.data import (
    NYC_JAZZ_VENUES,
    get_venue_by_name,
    get_venues_by_neighborhood,
    is_known_jazz_venue,
)

# Check if venue is a known jazz venue
if is_known_jazz_venue("Blue Note"):
    print("This is a famous jazz club!")

# Get venue details
venue = get_venue_by_name("Village Vanguard")
print(f"{venue.name} - {venue.address}")
print(f"Capacity: {venue.capacity}, Type: {venue.venue_type}")
print(f"Neighborhood: {venue.neighborhood}")

# Get all venues in a neighborhood
gv_venues = get_venues_by_neighborhood("Greenwich Village")
for venue in gv_venues:
    print(f"- {venue.name} ({venue.capacity} capacity)")

# Get all venue names for filtering
all_venue_names = get_all_venue_names()
```

**Data Structure**:
```python
@dataclass
class JazzVenue:
    name: str
    address: str
    city: str
    state: str
    neighborhood: str
    venue_type: str  # club, bar, concert-hall, restaurant
    website: Optional[str] = None
    capacity: Optional[int] = None
    notes: Optional[str] = None
```

### Seasonal Event Detection

Utilities for detecting and filtering Valentine's Day and other seasonal/holiday events.

**Location**: `src/events_agent/data/seasonal_events.py`

**Features**:
- Valentine's Day keyword detection (30+ keywords)
- Date range calculation (Feb 7-16 for Valentine's)
- Date-night event type identification
- Romantic neighborhood list
- Support for multiple holidays

**Valentine's Day Keywords**:
- valentine, valentines, valentine's
- romantic, couples, date night
- romance, love, sweetheart
- galentine, singles, anti-valentine

**Valentine's Event Types**:
- dinner, cooking class, wine tasting
- cocktail class, paint and sip
- jazz concert, comedy show, theater
- dance class, pottery class, spa
- cruise, rooftop

**Usage**:
```python
from events_agent.data import (
    get_valentines_date_range,
    is_valentines_event,
    is_date_night_event,
    ROMANTIC_NEIGHBORHOODS,
)

# Get Valentine's Day date range (Feb 7-16)
vday_start, vday_end = get_valentines_date_range(2026)
print(f"Valentine's period: {vday_start} to {vday_end}")

# Check if event is Valentine's related
event_title = "Romantic Jazz Night for Couples"
event_desc = "Perfect date night experience with live music"
event_tags = ["jazz", "romantic", "couples"]

if is_valentines_event(event_title, event_desc, event_tags):
    print("This is a Valentine's event!")

# Check if event type is date-night appropriate
if is_date_night_event("cooking class", ["couples", "date-night"]):
    print("Great for a date!")

# Filter by romantic neighborhoods
if event.location_address:
    for neighborhood in ROMANTIC_NEIGHBORHOODS:
        if neighborhood in event.location_address:
            print(f"Event in romantic {neighborhood}!")
```

**Supported Seasonal Categories**:
```python
class SeasonalCategory(str, Enum):
    VALENTINES_DAY = "valentines-day"
    CHRISTMAS = "christmas"
    NEW_YEARS = "new-years"
    HALLOWEEN = "halloween"
    THANKSGIVING = "thanksgiving"
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
```

**Romantic NYC Neighborhoods**:
- Greenwich Village, West Village, SoHo
- Tribeca, Chelsea, Upper West Side
- Brooklyn Heights, DUMBO, Williamsburg
- Long Island City (rooftop views)

### Combined Usage Examples

**Find jazz events at known venues**:
```python
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.data import is_known_jazz_venue

repo = SQLiteEventRepository(db)
all_events = repo.find_all()

# Filter by known jazz venues
jazz_venue_events = [
    e for e in all_events 
    if e.location_name and is_known_jazz_venue(e.location_name)
]

print(f"Found {len(jazz_venue_events)} events at famous jazz venues")
```

**Find Valentine's Day events**:
```python
from events_agent.data import get_valentines_date_range, is_valentines_event

# Get date range
vday_start, vday_end = get_valentines_date_range(2026)

# Query database
date_range_events = repo.find_by_date_range(vday_start, vday_end)

# Filter by Valentine's keywords
vday_events = [
    e for e in date_range_events
    if is_valentines_event(e.title, e.description, e.tags)
]

print(f"Found {len(vday_events)} Valentine's Day events")
```

**Find romantic jazz events for Valentine's**:
```python
from events_agent.data import (
    get_valentines_date_range,
    is_known_jazz_venue,
    is_date_night_event,
)

vday_start, vday_end = get_valentines_date_range(2026)
vday_events = repo.find_by_date_range(vday_start, vday_end)

romantic_jazz = [
    e for e in vday_events
    if (e.genre == "jazz" or (e.tags and "jazz" in e.tags))
    and (is_known_jazz_venue(e.location_name) or is_date_night_event(e.experience_type, e.tags))
]

print(f"Found {len(romantic_jazz)} romantic jazz events for Valentine's")
for event in romantic_jazz[:5]:
    print(f"- {event.title} at {event.location_name}")
```

## Crawlers

### Base Crawler

All crawlers inherit from `BaseCrawler` which provides:

- **Rate limiting**: 2-second delay between requests
- **Error handling**: Catches and logs errors
- **Browser management**: Playwright page lifecycle
- **User agent spoofing**: Avoids bot detection

**Important**: Crawlers return Event objects that should be saved to the SQLite database via the repository pattern.

### General Event Sources

#### Luma Crawler

**Status**: ✅ Working

**Strategy**: Extracts embedded JSON from Next.js `__NEXT_DATA__` script tag

**URL Pattern**: `https://lu.ma/{location}`

**Example**:
```python
from events_agent.crawlers.luma_crawler import LumaCrawler
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.database.connection import DatabaseConnection
from playwright.sync_api import sync_playwright

# Initialize database and repository
db = DatabaseConnection('data/events.db')
repo = SQLiteEventRepository(db)

# Crawl events
with sync_playwright() as p:
 browser = p.chromium.launch(headless=True)
 crawler = LumaCrawler()
 events = crawler.crawl(browser, "nyc")
 browser.close()

# Save to database (automatic deduplication)
repo.save_many(events)
print(f"Saved {len(events)} events to database")
```

#### Meetup Crawler

**Status**: ✅ Working

**Strategy**: Extracts events from DOM with Apollo GraphQL state fallback, using infinite scroll

**URL Pattern**: `https://www.meetup.com/find/?location={location}&customStartDate={start}&customEndDate={end}`

**Implementation**: Refactored into modular components following SOLID principles:
- `url_builder.py`: URL construction with filters
- `page_scroller.py`: Infinite scroll handling
- `dom_extractor.py`: DOM event extraction
- `apollo_parser.py`: Apollo state parsing
- `event_transformer.py`: Data transformation to Event model
- `constants.py`: Configuration constants

**Features**:
- Date range filtering with timezone support
- Daily and total event limits
- Automatic scrolling to load more events
- Dual extraction (DOM + Apollo state)

#### Other General Crawlers

**Eventbrite, Fever, Cozymeal**: ✅ Working

All crawlers follow the same pattern:
1. Inherit from `BaseCrawler`
2. Return list of `Event` objects
3. Events are saved to SQLite via repository
4. Automatic deduplication via UNIQUE(event_id, source) constraint

### 🎵 Jazz-Specific Sources

#### Jazz Near You Crawler

**Status**: ✅ Ready for testing
**Source**: jazznearyou.com
**Coverage**: NYC jazz venues, national coverage
**Data Quality**: High - dedicated jazz platform

**Features**:
- Venue-specific listings (80+ NYC venues tracked)
- Artist/performer information extraction
- Date filtering
- Genre tagging (jazz, blues, swing)
- Price extraction

**Usage**:
```python
from events_agent.crawlers.jazznearyou_crawler import JazzNearYouCrawler

crawler = JazzNearYouCrawler()
events = crawler.crawl(browser, "nyc")
repo.save_many(events)
```

#### Songkick Crawler

**Status**: ✅ Ready for testing
**Source**: songkick.com
**Coverage**: All music genres with jazz filtering
**Data Quality**: Very high - professional platform

**Features**:
- Genre filtering (jazz, blues, etc.)
- Venue information
- Artist tracking
- Tour dates
- Infinite scroll support

**Usage**:
```python
from events_agent.crawlers.jazznearyou_crawler import SongkickCrawler

crawler = SongkickCrawler()
events = crawler.crawl(browser, "nyc")  # Jazz events only
repo.save_many(events)
```

### 💝 Cultural & Seasonal Event Sources

#### TimeOut NYC Crawler

**Status**: ✅ Ready for testing
**Source**: timeout.com
**Coverage**: All NYC cultural events
**Data Quality**: Very high - professional curation

**Features**:
- Valentine's Day specific section
- Jazz club listings
- Seasonal events
- Food & drink events
- Category-based browsing
- Image extraction
- Multi-category support

**Usage**:
```python
from events_agent.crawlers.timeout_crawler import TimeOutNYCCrawler

# Valentine's Day events
vday_crawler = TimeOutNYCCrawler(category="valentines-day")
vday_events = vday_crawler.crawl(browser, "newyork")
repo.save_many(vday_events)

# Jazz events
jazz_crawler = TimeOutNYCCrawler(category="jazz")
jazz_events = jazz_crawler.crawl(browser, "newyork")
repo.save_many(jazz_events)

# All events
all_crawler = TimeOutNYCCrawler(category="events-calendar")
all_events = all_crawler.crawl(browser, "newyork")
repo.save_many(all_events)
```

#### DoNYC Crawler

**Status**: ✅ Ready for testing
**Source**: donyc.com
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
repo.save_many(events)
```

## Filtering

### NYC Location Filter

**Includes**:
- City variations: "new york", "nyc", "manhattan", "brooklyn", "queens", "bronx", "staten island"
- Checks: city, address, state fields
- Case-insensitive matching

**Excludes**:
- Online events (no physical location)
- Non-NYC NY state cities (Buffalo, Albany, etc.)

**Example**:
```python
from events_agent.filters.location_filter import LocationFilter

nyc_events = LocationFilter.filter_nyc_events(all_events)
is_nyc = LocationFilter.is_nyc_event(event)
```

### Date Filter

**Current Week**: Monday 00:00 to Sunday 23:59
**Next Week**: Following Monday 00:00 to Sunday 23:59

**Example**:
```python
from events_agent.filters.date_filter import DateFilter

# Get date ranges
current_start, current_end = DateFilter.get_current_week_range()
next_start, next_end = DateFilter.get_next_week_range()

# Filter events
filtered = DateFilter.filter_current_and_next_week(events)

# Custom range
custom_filtered = DateFilter.filter_by_range(events, start_date, end_date)
```

## Data Management

### SQLite Repository (Primary)

**Purpose**: Database access with automatic deduplication and efficient querying

**Repository Pattern**: Clean abstraction following SOLID principles

**Key Methods**:

```python
from events_agent.database.connection import DatabaseConnection
from events_agent.database.schema import SchemaManager
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from datetime import datetime

# Initialize database
db = DatabaseConnection('data/events.db')
schema = SchemaManager(db)
schema.initialize_schema()

# Create repository
repo = SQLiteEventRepository(db)

# Save events (automatic deduplication via UNIQUE constraint)
repo.save(event)                    # Save single event
repo.save_many(events)              # Save multiple events
repo.upsert(event)                  # Insert or update
repo.upsert_many(events)            # Bulk upsert

# Query events
all_events = repo.find_all()
event = repo.find_by_id(1)
event = repo.find_by_event_id("evt-abc123", "luma")

# Filter events (10-100x faster than JSON)
nyc_events = repo.find_by_location_and_date(
    start=datetime(2026, 2, 13),
    end=datetime(2026, 2, 14),
    city="new york",
    state="NY",
    exclude_online=True,
    limit=100
)

# Analytics
total = repo.count()
sources = repo.get_sources()        # List of unique sources
cities = repo.get_cities()          # List of unique cities
date_range = repo.get_date_range()  # (min_date, max_date)

# Check for duplicates
exists = repo.exists("evt-abc123", "luma")
```

### Legacy DataManager (Deprecated)

**Purpose**: Old JSON-based storage (kept for backwards compatibility)

**Status**: Deprecated - use SQLite repository instead

```python
from events_agent.storage.data_manager import DataManager

manager = DataManager(base_dir="data")

# Save raw events from a source (DEPRECATED)
file_path = manager.save_raw_events("luma", events, timestamp)

# Save processed events (DEPRECATED)
file_path = manager.save_processed_events(events, filters, timestamp)

# Load events from file (DEPRECATED)
events = manager.load_raw_events("data/raw/luma_20260131_213554.json")
```

### JSON Export for Debugging

```python
from events_agent.repositories.json_repository import JSONEventRepository

json_repo = JSONEventRepository("data/debug")
json_repo.export_events(events, "luma", timestamp)
json_repo.export_processed(filtered_events, filters, timestamp)
```

## Advanced Usage

### Custom Event Limit

```python
from events_agent.main import main

# Crawl up to 50 events
events = main(max_events=50)

# Crawl up to 200 events
events = main(max_events=200)
```

### Programmatic Usage

```python
from datetime import datetime
from playwright.sync_api import sync_playwright
from events_agent.crawlers.luma_crawler import LumaCrawler
from events_agent.database.connection import DatabaseConnection
from events_agent.database.schema import SchemaManager
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.filters.date_filter import DateFilter

# Initialize database
db = DatabaseConnection('data/events.db')
schema = SchemaManager(db)
schema.initialize_schema()
repo = SQLiteEventRepository(db)

# Crawl events from source
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    crawler = LumaCrawler()
    events = crawler.crawl(browser, "nyc")
    browser.close()

print(f"Crawled {len(events)} events")

# Save to database (automatic deduplication)
repo.save_many(events)
print(f"Saved to database")

# Query filtered events using SQL (10-100x faster than in-memory filtering)
current_start, current_end = DateFilter.get_current_week_range()
next_start, next_end = DateFilter.get_next_week_range()

filtered_events = repo.find_by_location_and_date(
    start=current_start,
    end=next_end,
    city="new york",
    state="NY",
    exclude_online=True,
    limit=100
)

print(f"Found {len(filtered_events)} NYC events for current and next week")

# Export to JSON for debugging (optional)
from events_agent.repositories.json_repository import JSONEventRepository
json_repo = JSONEventRepository("data/debug")
json_repo.export_processed(filtered_events, {"location": "NYC"}, datetime.now())
```

### Adding a New Crawler

1. **Create crawler class**:

```python
from events_agent.crawlers.base import BaseCrawler
from events_agent.models.event import Event, EventSource
from playwright.sync_api import Page
from typing import List

class MySourceCrawler(BaseCrawler):
    def get_events_url(self, location: str) -> str:
        return f"https://mysource.com/{location}/events"

    def extract_events_from_page(self, page: Page) -> List[Event]:
        events = []
        # Extract and parse events from page
        # Transform to Event objects with proper fields:
        #   event_id, source, url, title, start_datetime (required)
        #   location_name, city, state, price_cents, etc. (optional)
        return events
```

2. **Update main.py to use the new crawler**:

```python
from events_agent.crawlers.my_source_crawler import MySourceCrawler
from events_agent.repositories.sqlite_repository import SQLiteEventRepository

# In main():
# Initialize repository
repo = SQLiteEventRepository(db)

# Crawl from new source
my_crawler = MySourceCrawler()
my_events = my_crawler.crawl(browser, "nyc")

# Save to database (automatic deduplication)
repo.save_many(my_events)
print(f"Saved {len(my_events)} events from MySource")

# Query combined results from all sources
all_events = repo.find_all()
```

3. **Add to EventSource enum** (optional):

```python
# In src/events_agent/models/event.py
class EventSource(str, Enum):
    LUMA = "luma"
    MEETUP = "meetup"
    EVENTBRITE = "eventbrite"
    FEVER = "fever"
    COZYMEAL = "cozymeal"
    MYSOURCE = "mysource"  # Add new source
```

**Important**: Crawlers should save directly to SQLite database via repository, not to JSON files.

## Testing

### Run Tests

```bash
# All unit tests
pytest tests/unit/ -v

# Specific test file
pytest tests/unit/test_models.py -v

# Integration tests (mocked)
pytest tests/integration/ -v -k "not real_request"

# Integration tests with real requests (slow, uses network)
pytest -m integration

# With coverage
pytest --cov=events_agent
```

### Test Structure

**Unit Tests** (`tests/unit/`):
- `test_models.py`: Event model validation
- `test_date_filter.py`: Date filtering logic
- `test_location_filter.py`: NYC location detection
- `test_date_utils.py`: Date parsing utilities

**Integration Tests** (`tests/integration/`):
- `test_crawlers.py`: Full crawler flow with mocked pages

### Writing Tests

```python
import pytest
from datetime import datetime
from events_agent.models.event import Event, EventSource

def test_my_feature():
    """Test description."""
    # Arrange
    event = Event(
        event_id="test-123",
        source=EventSource.LUMA,
        url="https://test.com",
        title="Test Event",
        start_datetime=datetime(2026, 2, 5, 18, 0)
    )

    # Act
    result = my_function(event)

    # Assert
    assert result == expected_value
```

## Troubleshooting

### Common Issues

#### 1. Playwright Not Installed

**Error**: `playwright._impl._api_types.Error: Executable doesn't exist`

**Solution**:
```bash
playwright install chromium
```

#### 2. Virtual Environment Issues

**Error**: `ModuleNotFoundError: No module named 'events_agent'`

**Solution**:
```bash
source venv/bin/activate  # Ensure venv is activated
pip install -e .           # Reinstall package
```

#### 3. Timezone Comparison Errors

**Error**: `TypeError: can't compare offset-naive and offset-aware datetimes`

**Solution**: Already handled in code - events are converted to naive datetime for comparison

#### 4. Meetup Not Returning Events

**Current Status**: Meetup loads the page but doesn't extract events

**Why**: Meetup loads events dynamically via API calls after initial page load

**Workarounds**:
- Use Luma crawler (fully functional)
- Wait for Meetup API endpoint implementation
- Use Meetup official API (requires application approval)

#### 5. Rate Limiting / IP Blocking

**Symptoms**: Timeouts, 403 errors, empty results

**Solutions**:
- Increase rate limit delay in crawler
- Use residential proxies
- Respect robots.txt
- Add random delays between requests

### Debug Mode

Enable verbose output:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

Save page screenshots for debugging:

```python
# In crawler
page.screenshot(path="debug_screenshot.png")
```

## Configuration

### Environment Variables

Create `.env` file (optional):

```bash
# Rate limiting
CRAWL_DELAY=2.0

# Browser settings
HEADLESS=true

# Data directory
DATA_DIR=data
```

### Crawler Settings

Modify in crawler initialization:

```python
# Longer rate limit delay
crawler = LumaCrawler(rate_limit_seconds=5.0)

# In base crawler
page.goto(url, timeout=120000)  # 2 minute timeout
```

## Best Practices

### Data Management

1. **Keep raw data**: Never modify raw event files
2. **Version processed data**: Use timestamps in filenames
3. **Backup regularly**: Raw data is expensive to recrawl
4. **Clean old data**: Set up data retention policy

### Performance

1. **Use headless browser**: Faster than headed mode
2. **Implement caching**: Cache raw data, refilter as needed
3. **Parallel crawling**: Crawl sources simultaneously
4. **Limit pagination**: Don't crawl all pages if unnecessary

### Error Handling

1. **Graceful degradation**: Continue if one source fails
2. **Log errors**: Track what went wrong
3. **Retry logic**: Implement exponential backoff for transient errors
4. **Validate data**: Use Pydantic models to catch bad data early

## API Reference

### Event Model

```python
class Event(BaseModel):
    # Required
    event_id: str
    source: EventSource  # "luma" or "meetup"
    url: HttpUrl
    title: str
    start_datetime: datetime

    # Optional
    description: Optional[str] = None
    end_datetime: Optional[datetime] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    is_online: bool = False
    attendee_count: Optional[int] = None
    capacity: Optional[int] = None
    spots_remaining: Optional[int] = None
    price_cents: Optional[int] = None
    currency: str = "USD"
    is_free: bool = True
    organizer_name: Optional[str] = None
    organizer_url: Optional[HttpUrl] = None
    crawled_at: datetime = Field(default_factory=datetime.utcnow)
```

### BaseCrawler

```python
class BaseCrawler(ABC):
    def __init__(self, rate_limit_seconds: float = 2.0)

    @abstractmethod
    def get_events_url(self, location: str) -> str

    @abstractmethod
    def extract_events_from_page(self, page: Page) -> List[Event]

    def crawl(self, browser: Browser, location: str) -> List[Event]
```

### DateFilter

```python
class DateFilter:
    @staticmethod
    def get_current_week_range() -> tuple[datetime, datetime]

    @staticmethod
    def get_next_week_range() -> tuple[datetime, datetime]

    @staticmethod
    def filter_current_and_next_week(events: List[Event]) -> List[Event]

    @staticmethod
    def filter_by_range(events: List[Event], start: datetime, end: datetime) -> List[Event]
```

### LocationFilter

```python
class LocationFilter:
    NYC_VARIATIONS = {
        'new york', 'new york city', 'nyc', 'manhattan',
        'brooklyn', 'queens', 'bronx', 'staten island'
    }

    @staticmethod
    def is_nyc_event(event: Event) -> bool

    @staticmethod
    def filter_nyc_events(events: List[Event]) -> List[Event]

    @staticmethod
    def filter_by_city(events: List[Event], city: str) -> List[Event]
```

### DatabaseConnection

```python
class DatabaseConnection:
    def __init__(self, db_path: str = "data/events.db")

    def get_connection(self) -> sqlite3.Connection
    def close(self)
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor
    def executemany(self, query: str, params: List[tuple]) -> sqlite3.Cursor
    def commit(self)
    def rollback(self)
```

### SQLiteEventRepository

```python
class SQLiteEventRepository(EventRepository):
    def __init__(self, db: DatabaseConnection)

    # CRUD methods
    def save(self, event: Event) -> int
    def save_many(self, events: List[Event]) -> List[int]
    def find_by_id(self, id: int) -> Event | None
    def find_all(self, limit: int = None, offset: int = 0) -> List[Event]
    def delete(self, id: int) -> bool
    def count(self) -> int

    # Domain queries
    def find_by_event_id(self, event_id: str, source: str) -> Event | None
    def find_by_date_range(self, start: datetime, end: datetime,
                          limit: int = None) -> List[Event]
    def find_by_location(self, city: str, state: str = None,
                        exclude_online: bool = False,
                        limit: int = None) -> List[Event]
    def find_by_location_and_date(self, start: datetime, end: datetime,
                                  city: str, state: str = None,
                                  exclude_online: bool = False,
                                  limit: int = None) -> List[Event]
    def find_by_source(self, source: str, limit: int = None) -> List[Event]

    # Deduplication
    def exists(self, event_id: str, source: str) -> bool
    def upsert(self, event: Event) -> int
    def upsert_many(self, events: List[Event]) -> List[int]

    # Analytics
    def count_by_filters(self, filters: dict) -> int
    def get_sources(self) -> List[str]
    def get_cities(self) -> List[str]
    def get_date_range(self) -> tuple[datetime, datetime]
```

### DataManager (Deprecated)

```python
class DataManager:
    def __init__(self, base_dir: str = "data")

    # DEPRECATED: Use SQLiteEventRepository instead
    def save_raw_events(self, source: str, events: List[Event],
                       timestamp: datetime = None) -> str

    def save_processed_events(self, events: List[Event], filters: dict,
                             timestamp: datetime = None) -> str

    def get_latest_raw_file(self, source: str = None) -> Path | None

    def load_raw_events(self, filepath: str) -> List[Event]
```

## Future Enhancements

### Completed ✅

1. **Database Integration**: ✅ SQLite with automatic deduplication
2. **More Event Sources**: ✅ Eventbrite, Fever, Cozymeal
3. **Historical Tracking**: ✅ Query any past crawl via database
4. **Analytics**: ✅ Count, aggregate, trend analysis via SQL

### Planned Features

1. **More Event Sources**:
   - Facebook Events
   - Partiful
   - Dice.fm
   - Custom event feeds

2. **Enhanced Filtering**:
   - Category/tag filtering
   - Price range filtering (via SQL)
   - Attendee count filtering
   - Full-text search (SQLite FTS5)

3. **Recommendation Engine**:
   - User preferences
   - Event prestige scoring
   - Attendee quality metrics
   - Personalized suggestions

4. **Advanced Database Features**:
   - PostgreSQL support via same repository interface
   - Relationship tables (normalize venues, organizers)
   - Event history tracking (changes over time)
   - Caching layer (Redis)

5. **API Server**:
   - REST API endpoints
   - GraphQL API
   - Real-time updates
   - Webhook notifications

6. **CLI & Tools**:
   - Query commands (search, filter, export)
   - Analytics dashboard (web UI)
   - Export formats (CSV, iCal, Google Calendar)

7. **Scheduling**:
   - Cron job integration
   - Automated daily crawls
   - Email digests
   - Calendar exports

## Support

### Resources

- **Documentation**: This file (AGENTS.md / CLAUDE.md)
- **README**: User-facing documentation (README.md)
- **SQLite Migration**: Database migration guide (SQLITE_MIGRATION.md)
- **SQL Queries**: Pre-written analysis queries (queries/quick_analysis.sql)
- **Tests**: See `tests/` for examples (104 tests)
- **Database**: Browse data with DB Browser for SQLite

### Getting Help

1. Check error messages and stack traces
2. Review test files for usage examples
3. Enable debug logging
4. Query database directly with SQL
5. Check SQLITE_MIGRATION.md for database issues
6. Verify virtual environment is activated

## Project Organization and Refactoring

### Clean Architecture

The project follows SOLID principles with clear separation of concerns:

**Modular Structure**: The Meetup crawler was refactored from a monolithic 697-line file into 7 focused modules:
- Each module has a single responsibility
- Easy to test, understand, and maintain
- Reusable components across crawlers

**Directory Organization**:
- `scripts/` - Ad-hoc utility scripts (not part of main package)
- `data/debug/` - Debug JSON files (gitignored)
- `docs/archive/` - Historical implementation documentation
- Clean root directory with only essential files

**No Code Duplication**:
- Centralized date utilities in `date_utils.py`
- Shared constants in `constants.py`
- Reusable transformation logic

**Development Tools**:
- Black for code formatting (100 char line length)
- Ruff for linting
- Mypy for type checking
- pytest for testing

### Meetup Crawler Refactoring

**Before**: Single 697-line file
**After**: 7 modules totaling ~900 lines (with better separation)

**Modules**:
1. `meetup_crawler.py` (309 lines) - Main orchestration
2. `event_transformer.py` (297 lines) - Data transformation
3. `dom_extractor.py` (149 lines) - DOM extraction
4. `url_builder.py` (84 lines) - URL construction
5. `apollo_parser.py` (76 lines) - Apollo state parsing
6. `page_scroller.py` (64 lines) - Scroll handling
7. `constants.py` (21 lines) - Configuration

**Benefits**:
- Each file has single responsibility
- Easy to unit test individual components
- Clear interfaces between modules
- Can reuse components for other GraphQL sources

## License

MIT License - See project root for details

## Credits

Built with:
- **Playwright**: Browser automation
- **Pydantic**: Data validation
- **pytest**: Testing framework
- **Python 3.10+**: Core language

---

**Last Updated**: 2026-02-10

**Version**: 0.2.0

**Status**: ✅ SQLite database integrated, ✅ 5 sources working (Luma, Meetup, Eventbrite, Fever, Cozymeal), ✅ Repository pattern implemented
