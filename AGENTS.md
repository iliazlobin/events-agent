# Events Agent

NYC event aggregator using web scraping from 9 sources with SQLite storage, smart filtering, and event categorization.

## Key Features

- **9 Event Sources**: Luma, Meetup, Eventbrite, Fever, Cozymeal, Jazz Near You, Songkick, TimeOut NYC, DoNYC
- **SQLite Database**: Primary storage with automatic deduplication (UNIQUE constraint on event_id + source)
- **Smart Filtering**: SQL-based location (NYC) and date filtering (10-100x faster than in-memory)
- **Event Categorization**: Genre, tags, experience types for jazz, Valentine's Day, seasonal events
- **Jazz Venue Index**: 15+ NYC venues with metadata (`src/events_agent/data/jazz_venues.py`)
- **104 Tests**: 93 unit + 11 integration tests

## Quick Start

```bash
python3 -m venv venv && source venv/bin/activate
pip install -e .
playwright install chromium
python -m events_agent.main  # or: events-crawler
```

## Architecture

### Structure
- `src/events_agent/`
  - `models/event.py` - Pydantic Event model (25+ fields)
  - `database/` - Connection, schema, migrations
  - `repositories/` - Repository pattern (base, SQLite, JSON)
  - `data/` - Jazz venues index, seasonal event detection
  - `crawlers/` - Base + 9 source implementations
  - `filters/` - Date and location utilities (legacy)
  - `utils/` - Date parsing, timezone helpers
- `data/events.db` - PRIMARY STORAGE (SQLite with WAL mode)
- `tests/` - 104 tests (unit + integration)
- `queries/` - SQL analysis queries

### Data Flow
Crawlers → SQLite (dedupe on save) → SQL filter (location + date + limit) → Event objects

## Database

**Location**: `data/events.db` (SQLite with WAL mode for concurrent reads)

### Schema
- **events** (22 columns): event_id, source, url, title, start_datetime (required) + location, pricing, organizer (optional). UNIQUE(event_id, source) prevents duplicates. 8 performance indexes.
- **crawl_sessions**: Tracks crawl history
- **schema_version**: Migration tracking

### Usage
```python
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.database.connection import DatabaseConnection

db = DatabaseConnection('data/events.db')
repo = SQLiteEventRepository(db)

# Save with auto-deduplication
repo.save_many(events)

# Query (10-100x faster than in-memory filtering)
nyc_events = repo.find_by_location_and_date(start, end, "new york", "NY", limit=100)
```

**CLI**: `sqlite3 data/events.db` | **GUI**: `open data/events.db` (DB Browser for SQLite)
**Queries**: See `queries/quick_analysis.sql` for examples
**Migration**: `python scripts/migrate_json_to_sqlite.py` (see SQLITE_MIGRATION.md)

## Event Model (Pydantic)

**Required**: event_id, source, url, title, start_datetime
**Optional** (25+ fields):
- Location: location_name, city, state, latitude, longitude, is_online
- Pricing: price_cents, currency, is_free, fee_amount
- Capacity: attendee_count, capacity, spots_remaining
- Categorization: genre, experience_type, category, tags
- Music: performer_names, duration_minutes
- Cooking: chef_name, chef_rating, skill_level, cuisine_type
- Host: organizer_name, host_name, group_name, ratings
- Content: description, image_url, ai_summary, topics

**Validation**: end_datetime > start_datetime, numeric >= 0, valid URLs, non-empty title

## Data Infrastructure

### Jazz Venues (`src/events_agent/data/jazz_venues.py`)
15+ NYC jazz venues with metadata: Village Vanguard, Blue Note, Smalls (G. Village), Birdland, Dizzy's Club (Midtown), Minton's (Harlem), etc.
```python
from events_agent.data import is_known_jazz_venue, get_venue_by_name
if is_known_jazz_venue("Blue Note"):  # Check venue
    venue = get_venue_by_name("Blue Note")  # Get details
```

### Seasonal Events (`src/events_agent/data/seasonal_events.py`)
Valentine's Day detection (30+ keywords: valentine, romantic, couples), date ranges (Feb 7-16), event types (dinner, cooking class, jazz concert), romantic neighborhoods.
```python
from events_agent.data import get_valentines_date_range, is_valentines_event
vday_start, vday_end = get_valentines_date_range(2026)
if is_valentines_event(event.title, event.description, event.tags):
    # Is Valentine's event
```

## Crawlers

All inherit from `BaseCrawler` (rate limiting, error handling, Playwright management). Return Event objects → save to SQLite via repository.

| Source | Status | Strategy | Features |
|--------|--------|----------|----------|
| **Luma** | ✅ | Next.js `__NEXT_DATA__` JSON | General events |
| **Meetup** | ✅ | DOM + Apollo GraphQL, infinite scroll | Modular (7 files), date filtering |
| **Eventbrite, Fever, Cozymeal** | ✅ | Various | General events |
| **Jazz Near You** | ✅ | HTML parsing | 80+ NYC jazz venues, artist info |
| **Songkick** | ✅ | Infinite scroll | Jazz filtering, tour dates |
| **TimeOut NYC** | ✅ | Multi-category | Valentine's, jazz, seasonal, images |
| **DoNYC** | ✅ | Category-based | Valentine's, galentine's, curated |

```python
# Example usage
from events_agent.crawlers.luma_crawler import LumaCrawler
crawler = LumaCrawler()
events = crawler.crawl(browser, "nyc")
repo.save_many(events)  # Auto-deduplication
```

## Repository API

**SQLiteEventRepository** - Main data access layer:
```python
repo = SQLiteEventRepository(DatabaseConnection('data/events.db'))

# CRUD
repo.save_many(events)  # Auto-dedupe via UNIQUE(event_id, source)
repo.upsert_many(events)  # Insert or update
repo.find_by_id(1)
repo.find_by_event_id("evt-123", "luma")

# Queries (SQL-based, 10-100x faster)
repo.find_by_location_and_date(start, end, "new york", "NY", limit=100)
repo.find_by_date_range(start, end)
repo.find_by_source("luma")

# Analytics
repo.count(), repo.get_sources(), repo.get_cities(), repo.get_date_range()
```

**Filters** (legacy, prefer SQL queries):
- `LocationFilter.filter_nyc_events()` - NYC variations (manhattan, brooklyn, etc.)
- `DateFilter.get_current_week_range()`, `filter_current_and_next_week()`

**JSON Export** (debugging only):
```python
JSONEventRepository("data/debug").export_processed(events, filters, timestamp)
```

## Usage Examples

**Custom event limit**: `main(max_events=50)`

**Adding a new crawler**:
1. Extend `BaseCrawler`, implement `get_events_url()` and `extract_events_from_page()`
2. Save to database: `repo.save_many(crawler.crawl(browser, "nyc"))`
3. Add to `EventSource` enum in `models/event.py`

## Testing

**Run**: `pytest tests/unit/ -v` | `pytest tests/integration/ -v` | `pytest --cov=events_agent`
**Structure**: 93 unit tests (models, filters, utils), 11 integration tests (crawlers)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Playwright not found | `playwright install chromium` |
| Module not found | `source venv/bin/activate && pip install -e .` |
| Timezone errors | Already handled (naive datetime conversion) |
| Rate limiting / 403 | Increase delay, use proxies, respect robots.txt |

**Debug**: `logging.basicConfig(level=logging.DEBUG)` | `page.screenshot(path="debug.png")`

## Configuration

**Environment** (optional `.env`): CRAWL_DELAY=2.0, HEADLESS=true, DATA_DIR=data
**Crawler settings**: `LumaCrawler(rate_limit_seconds=5.0)`, `page.goto(url, timeout=120000)`

## Best Practices

- Use SQLite (10-100x faster queries), backup regularly
- Headless browser, parallel crawling, limit pagination
- Graceful degradation, error logging, Pydantic validation

## Architecture Notes

**SOLID Principles**: Repository pattern, modular crawlers (Meetup refactored from 697 lines → 7 modules: crawler, transformer, extractor, scroller, apollo parser, url builder, constants)
**Tools**: Black (100 char), Ruff, Mypy, pytest
**Key Docs**: README.md, SQLITE_MIGRATION.md, queries/quick_analysis.sql, tests/ (104 examples)

## Future Enhancements

**Completed**: ✅ SQLite, 9 sources, historical tracking, analytics
**Planned**: Facebook/Partiful/Dice.fm sources, FTS5 search, price/category filtering, recommendation engine, PostgreSQL support, REST/GraphQL API, CLI tools, scheduled crawls

---
**Version 0.2.0** | Python 3.10+ | Playwright + Pydantic + pytest | MIT License
