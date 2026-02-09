# Events Agent - Comprehensive Guide

## Overview

The Events Agent is a web scraping system that automatically discovers, filters, and organizes event data from multiple sources (Luma.com and Meetup.com). It's designed to help you find relevant events in NYC for the current and next week.

### Key Features

- **Multi-Source Crawling**: Fetches events from Luma.com and Meetup.com (both working)
- **Smart Filtering**: Location-based (NYC) and date-based (current + next week) filtering
- **Data Organization**: Separate raw and processed data storage
- **Event Limits**: Configurable maximum events (default: 100)
- **Structured Output**: Pydantic-validated JSON with comprehensive event details
- **Comprehensive Testing**: 33 unit tests + 4 integration tests

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
│   ├── crawlers/
│   │   ├── base.py               # Abstract base crawler class
│   │   ├── luma_crawler.py       # Luma.com implementation
│   │   ├── meetup_crawler.py     # Meetup.com re-export (refactored)
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
│   │   ├── date_filter.py        # Current/next week filtering
│   │   └── location_filter.py    # NYC location filtering
│   ├── storage/
│   │   └── data_manager.py       # Raw/processed data management
│   ├── utils/
│   │   └── date_utils.py         # Date parsing and timezone helpers
│   └── main.py                   # CLI entry point
├── tests/
│   ├── fixtures/                 # HTML samples for testing
│   ├── unit/                     # Unit tests (33 tests)
│   └── integration/              # Integration tests (4 tests)
├── data/
│   ├── raw/                      # Raw crawled events by source
│   ├── processed/                # Filtered and processed events
│   └── debug/                    # Debug JSON files (gitignored)
├── scripts/                      # Ad-hoc utility scripts
├── docs/archive/                 # Old implementation docs
├── pyproject.toml                # Dependencies and tool configuration
└── README.md                     # User documentation
```

### Data Flow

```
┌─────────────────┐
│ Luma.com        │──┐
│ Meetup.com      │  │  1. Crawl Sources
└─────────────────┘  │
                     ▼
              ┌──────────────┐
              │ Raw Events   │  2. Save Raw Data
              │ data/raw/    │
              └──────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ NYC Filter   │  3. Location Filtering
              └──────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ Date Filter  │  4. Current/Next Week
              └──────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ Limit (100)  │  5. Apply Event Limit
              └──────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ Processed    │  6. Save Processed
              │ data/proc/   │
              └──────────────┘
```

## Data Organization

### Directory Structure

```
data/
├── raw/
│   ├── luma_20260131_213554.json      # Raw Luma events
│   ├── meetup_20260131_213554.json    # Raw Meetup events
│   └── ...
└── processed/
    ├── events_20260131_213554.json    # Filtered events
    └── ...
```

### Raw Data Format

**File**: `data/raw/{source}_{timestamp}.json`

```json
{
  "source": "luma",
  "timestamp": "2026-01-31T21:35:54.504309",
  "count": 29,
  "events": [
    {
      "event_id": "evt-abc123",
      "source": "luma",
      "url": "https://lu.ma/event-slug",
      "title": "Event Title",
      "description": "Event description...",
      "start_datetime": "2026-02-05T18:00:00Z",
      "end_datetime": "2026-02-05T20:00:00Z",
      "location_name": "Venue Name",
      "location_address": "123 Main St, New York, NY 10001",
      "city": "New York",
      "state": "NY",
      "is_online": false,
      "attendee_count": 50,
      "capacity": 100,
      "spots_remaining": 50,
      "price_cents": 0,
      "currency": "USD",
      "is_free": true,
      "organizer_name": "Organizer Name",
      "organizer_url": "https://...",
      "crawled_at": "2026-02-01T02:35:59.682954"
    }
  ]
}
```

### Processed Data Format

**File**: `data/processed/events_{timestamp}.json`

```json
{
  "timestamp": "2026-01-31T21:35:54.504309",
  "total_events": 25,
  "filters": {
    "location": "NYC",
    "date_range": "current_and_next_week",
    "max_events": 100
  },
  "events": [
    // Same event structure as raw
  ]
}
```

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

### Validation Rules

- `end_datetime` must be after `start_datetime`
- Numeric fields must be >= 0
- URLs must be valid
- Title cannot be empty

## Crawlers

### Base Crawler

All crawlers inherit from `BaseCrawler` which provides:

- **Rate limiting**: 2-second delay between requests
- **Error handling**: Catches and logs errors
- **Browser management**: Playwright page lifecycle
- **User agent spoofing**: Avoids bot detection

### Luma Crawler

**Status**: ✅ Working

**Strategy**: Extracts embedded JSON from Next.js `__NEXT_DATA__` script tag

**URL Pattern**: `https://lu.ma/{location}`

**Example**:
```python
from events_agent.crawlers.luma_crawler import LumaCrawler
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    crawler = LumaCrawler()
    events = crawler.crawl(browser, "nyc")
    browser.close()
```

### Meetup Crawler

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

### DataManager Class

**Purpose**: Centralized data storage and retrieval

**Key Methods**:

```python
from events_agent.storage.data_manager import DataManager

manager = DataManager(base_dir="data")

# Save raw events from a source
file_path = manager.save_raw_events("luma", events, timestamp)

# Save processed events
file_path = manager.save_processed_events(events, filters, timestamp)

# Load events from file
events = manager.load_raw_events("data/raw/luma_20260131_213554.json")

# Get latest raw file for a source
latest = manager.get_latest_raw_file("luma")
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
from events_agent.filters.date_filter import DateFilter
from events_agent.filters.location_filter import LocationFilter
from events_agent.storage.data_manager import DataManager

# Initialize
manager = DataManager()
timestamp = datetime.now()

# Crawl
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    crawler = LumaCrawler()
    events = crawler.crawl(browser, "nyc")
    browser.close()

# Save raw data
manager.save_raw_events("luma", events, timestamp)

# Filter
nyc_events = LocationFilter.filter_nyc_events(events)
week_events = DateFilter.filter_current_and_next_week(nyc_events)

# Limit
final_events = week_events[:100]

# Save processed
manager.save_processed_events(final_events, {"location": "NYC"}, timestamp)
```

### Adding a New Crawler

1. **Create crawler class**:

```python
from events_agent.crawlers.base import BaseCrawler
from events_agent.models.event import Event, EventSource

class MySourceCrawler(BaseCrawler):
    def get_events_url(self, location: str) -> str:
        return f"https://mysource.com/{location}/events"

    def extract_events_from_page(self, page: Page) -> List[Event]:
        events = []
        # Extract and parse events from page
        # Transform to Event objects
        return events
```

2. **Update main.py**:

```python
from events_agent.crawlers.my_source_crawler import MySourceCrawler

# In main():
my_crawler = MySourceCrawler()
my_events = my_crawler.crawl(browser, "nyc")
manager.save_raw_events("mysource", my_events, timestamp)
all_events.extend(my_events)
```

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

### DataManager

```python
class DataManager:
    def __init__(self, base_dir: str = "data")

    def save_raw_events(self, source: str, events: List[Event],
                       timestamp: datetime = None) -> str

    def save_processed_events(self, events: List[Event], filters: dict,
                             timestamp: datetime = None) -> str

    def get_latest_raw_file(self, source: str = None) -> Path | None

    def load_raw_events(self, filepath: str) -> List[Event]
```

## Future Enhancements

### Planned Features

1. **More Event Sources**:
   - Eventbrite
   - Facebook Events
   - Partiful
   - Custom event feeds

2. **Enhanced Filtering**:
   - Category/tag filtering
   - Price range filtering
   - Attendee count filtering
   - Keyword search

3. **Recommendation Engine**:
   - User preferences
   - Event prestige scoring
   - Attendee quality metrics
   - Personalized suggestions

4. **Database Integration**:
   - PostgreSQL storage
   - Event deduplication
   - Historical tracking
   - Analytics

5. **API Server**:
   - REST API endpoints
   - GraphQL API
   - Real-time updates
   - Webhook notifications

6. **Scheduling**:
   - Cron job integration
   - Automated daily crawls
   - Email digests
   - Calendar exports

## Support

### Resources

- **Documentation**: This file (CLAUDE.md)
- **README**: User-facing documentation (README.md)
- **Tests**: See `tests/` for examples
- **Plan**: Implementation plan at `~/.claude/plans/hazy-roaming-charm.md`

### Getting Help

1. Check error messages and stack traces
2. Review test files for usage examples
3. Enable debug logging
4. Check data files for structure issues
5. Verify virtual environment is activated

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

**Last Updated**: 2026-02-02

**Version**: 0.1.0

**Status**: ✅ Luma working, ✅ Meetup working (refactored)
