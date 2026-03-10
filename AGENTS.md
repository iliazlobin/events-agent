# Events Agent - Agent Instructions

SF/NYC event aggregator using web scraping from multiple sources with SQLite storage.

**Active Sources**: Gary's Guide, Luma, Meetup, Eventbrite, Fever, TimeOut, DoNYC under `src/apify/`
**Planned**: Funcheap SF, SF Travel

## Core Principles

- **Use SQLite**: Primary storage at `data/events.db` with auto-deduplication
- **Use Mermaid**: For architecture diagrams and documentation
- **Follow patterns**: Repository pattern, modular crawlers, Pydantic models, aggregator pattern
- **Test coverage**: Add tests for new features (pytest)
- **Single source tree**: New production crawlers belong in `src/apify/<source>-crawler/`

## Project Direction

The repo is converging to a single `src/`-rooted structure:

- `src/apify/` is the home for source-specific crawlers and scheduled actors.
- `src/events_agent/` is shared infrastructure only:
  - SQLite
  - normalized models
  - import/adaptation
  - enrichment
  - quality validation
- Do **not** add new production source crawlers under `src/events_agent/`; they belong in `src/apify/`.

**Target structure**:
```text
src/apify/<source>-crawler/  # Source crawler actor
src/events_agent/database/   # SQLite + migrations
src/events_agent/models/     # Normalized contracts
src/events_agent/repositories/# Upsert/query/enrichment
scripts/                     # Config sync, import, validation
```

**Migration rule**:
- Recurring pipeline sources become actors under `src/apify/`.
- One-off conference or special-purpose scrapers should be retired, not migrated.

**Quality loop for every crawler change**:
1. Local actor run with small input
2. Dataset contract inspection
3. SQLite import/upsert verification
4. Aggregator/pending-coverage query verification
5. Schedule validation / dry-run sync

**See**: `docs/APIFY_FIRST_ARCHITECTURE.md`

## Aggregator Pattern

**Design**: Gary's Guide acts as event **aggregator**, not direct scraper
- Collects metadata from Gary's Guide (title, date, location, image)
- Resolves gary.to redirects to detect provider (luma.com, meetup.com, etc.)
- **Does NOT** scrape individual event pages from other providers
- Stores with `source=garysguide` + `original_provider=luma/meetup/etc.`
- Dedicated crawlers (Luma, Meetup) handle full event details

**Data Model** (Migration 3):
```python
original_provider: str       # "luma", "meetup", "eventbrite"
aggregated_from: str         # "garysguide"
short_url: str              # "http://gary.to/abc123"
aggregator_detail_url: str  # Gary's Guide detail page
```

**Benefits**:
- ✅ Avoids duplicate scraping of Luma/Meetup events
- ✅ Reduces compute costs (no redundant page visits)
- ✅ Discovery mechanism for events across platforms
- ✅ Metadata enrichment (curation, short URLs)

**See**: `design/AGGREGATOR_PATTERN.md` for full architecture

## Apify Integration

### Overview

**Deployed Actors**: Apify actors sourced from `src/apify/`
**Local Source**: `src/apify/<source>-crawler/`
**Runtime**: TypeScript/Crawlee for existing core actors; Python bridge actors for migrated legacy sources
**MCP Server**: Configured via `~/.claude.json` for API access

### Apify Actor Naming Convention

- **Prefix**: `events-`
- **Format**: `events-<source>` (NO `-crawler` suffix)
- **Examples**:
  - `events-garysguide`
  - `events-luma`
  - `events-eventbrite`
  - `events-meetup`

**Directory structure**: `src/apify/<source>-crawler/` (local directory uses `-crawler` suffix)
- Local: `src/apify/garysguide-crawler/`
- Deployed: `iliazlobin/events-garysguide`
- Title format: "Events <Source>" (e.g., "Events Garysguide", "Events Luma")

### Apify Crawler Architecture

**File Structure**:
```
src/apify/garysguide-crawler/
├── .actor/
│   ├── actor.json           # Actor metadata (name, version, input schema)
│   └── input_schema.json    # Input parameter definitions
├── src/
│   ├── main.ts             # Crawler initialization & configuration
│   └── routes.ts           # Request handlers & scraping logic
├── inputs/
│   └── test-50.json        # Test input files
├── package.json            # Dependencies & scripts
└── storage/                # Local test data (gitignored)
    └── datasets/default/   # Scraped events (JSON files)
```

**Design Pattern**:
1. **Router-based handlers**: Separate handlers for different page types
2. **Request enqueueing**: Use `crawler.addRequests()` to queue event URLs
3. **Data extraction**: Parse DOM/JSON and save via `Dataset.pushData()`
4. **Error handling**: Retry logic, graceful degradation, detailed logging

**Key Components** (`src/main.ts`):
```typescript
// Initialize Apify actor
await Actor.init()

// Read input parameters
const input = await Actor.getInput<InputSchema>()
const { urls, maxItems, lookForwardWindow, maxScrolls } = input

// Configure PuppeteerCrawler
const crawler = new PuppeteerCrawler({
  requestHandler: router,              // Route to handlers
  maxRequestsPerCrawl: maxItems + 10, // Limit total requests
  maxRequestsPerMinute: 3,            // Rate limiting
  requestHandlerTimeoutSecs: 300,     // Timeout for long operations
  useSessionPool: true,               // Session management
  browserPoolOptions: {               // Anti-blocking
    useFingerprints: true
  }
})

// Run crawler
await crawler.run(urls)
await Actor.exit()
```

**Router Pattern** (`src/routes.ts`):
```typescript
export const router = createPuppeteerRouter()

// Handler for listing pages (scrolls & enqueues events)
router.addDefaultHandler(async ({ page, log, crawler }) => {
  // Scroll to load more events
  for (let i = 0; i < maxScrolls; i++) {
    await scrollPageToBottom()
    // Check if target date reached
    if (lastDate >= targetDate) break
  }

  // Extract event URLs and enqueue them
  for (const event of events) {
    await crawler.addRequests([{
      url: event.url,
      label: 'event',          // Route to event handler
      userData: { ...metadata } // Pass context
    }])
  }
})

// Handler for individual event pages
router.addHandler('event', async ({ page, log, request }) => {
  // Extract event details
  const title = await page.$eval('h1.title', el => el.textContent)
  const dateStart = parseDateTimeRange(dateStr, timeStr)
  const price = await page.$eval('.price', el => el.textContent)

  // Save to dataset
  await Dataset.pushData({
    url: request.url,
    title,
    dateStart,
    price,
    // ... other fields
  })
})
```

### Development Workflow

#### 1. Writing a New Crawler

**Create from template**:
```bash
# Initialize new actor
apify create funcheap-crawler --template ts-crawlee-puppeteer-chrome
cd src/apify/funcheap-crawler
```

**Define input schema** (`.actor/input_schema.json`):
```json
{
  "title": "Funcheap Events Crawler",
  "type": "object",
  "properties": {
    "region": {
      "title": "Region",
      "type": "string",
      "description": "Region to crawl (sf, nyc, etc.)",
      "default": "sf"
    },
    "maxItems": {
      "title": "Maximum Items",
      "type": "integer",
      "default": 100,
      "minimum": 1
    },
    "lookForwardWindow": {
      "title": "Look Forward Window (days)",
      "type": "integer",
      "default": 30
    }
  }
}
```

**Implement scraping logic** (`src/routes.ts`):
- **List page handler**: Scroll, extract URLs, enqueue with `crawler.addRequests()`
- **Detail page handler**: Extract fields, save with `Dataset.pushData()`
- **Error handling**: Try/catch, validation, skip malformed data

**Critical fixes for reliable crawling**:
- ✅ Use `crawler.addRequests()` not `enqueueLinks()` for programmatic URLs
- ✅ Set `requestHandlerTimeoutSecs: 300` for extensive scrolling
- ✅ Use `maxRequestsPerCrawl: maxItems + buffer` to control limits
- ✅ Add error handling for missing DOM elements

#### 2. Testing Locally

**Install dependencies**:
```bash
npm install
```

**Create test input** (`inputs/test.json`):
```json
{
  "region": "sf",
  "maxItems": 50,
  "lookForwardWindow": 30
}
```

**Run locally**:
```bash
# Run with test input
apify run --input-file=inputs/test.json

# Or use npm script
npm run start:dev

# Debug mode with purge
apify run --input-file=inputs/test.json --purge
```

**Check results**:
```bash
# Count collected items
find storage/datasets/default -name "*.json" | wc -l

# View sample data
cat storage/datasets/default/*.json | jq -s '.[0:3]'

# Check for errors
cat apify_storage/key_value_stores/default/SDK_CRAWLER_STATISTICS_0.json | jq
```

#### 3. Building & Deploying

**Build TypeScript**:
```bash
npm run build
```

**Deploy to Apify**:
```bash
# First time - creates new actor
apify push

# Subsequent updates
apify push
```

**Verify deployment**:
```bash
# List your actors
apify actors ls

# Get actor info
apify info
```

#### 4. Running on Apify Platform

**Via CLI**:
```bash
# Run specific actor
apify actors call iliazlobin/events-garysguide

# Run with input
apify actors call iliazlobin/events-garysguide --input '{"region":"sf","maxItems":100,"lookForwardWindow":30}'
```

**Via Console**: https://console.apify.com/actors → Select actor → Run

**Via MCP Server**: See "MCP Server Configuration" section below

### MCP Server Configuration

#### Setup

**Already configured in `~/.claude.json`**:
```json
{
  "mcpServers": {
    "apify": {
      "url": "https://mcp.apify.com",
      "headers": {
        "Authorization": "Bearer apify_api_XXX..."
      }
    }
  }
}
```

**Verify connection**:
```bash
# List available MCP tools
claude mcp list

# Should show: apify-slash-rag-web-browser, call-actor, etc.
```

#### Using MCP Server

**List your actors**:
```
"Show me my Apify actors"
```

**Run actor via MCP**:
```
"Run my Events Gary's Guide crawler with these settings:
- Region: sf
- Max items: 100
- Look forward: 30 days"
```

**Get results**:
```
"Get the dataset from my last Gary's Guide crawler run"
```

**MCP tools available**:
- `search-actors` - Find actors in Apify Store
- `fetch-actor-details` - Get actor info, input schema, README
- `call-actor` - Run actor with input (supports async mode)
- `get-actor-run` - Get run status and metadata
- `get-actor-output` - Fetch dataset items from a run

#### Testing MCP Integration

**Single run test** (final validation):
```
"Run iliazlobin/events-garysguide with input:
{
  'region': 'sf',
  'maxItems': 50,
  'lookForwardWindow': 30
}

Wait for completion and show me the first 5 events."
```

**Expected output**:
- Run starts (shows runId and widget)
- Crawls ~50 events from Gary's Guide SF
- Returns dataset preview with event details

### Scheduling & Automation

#### Creating a Schedule (Web Console)

**Via Apify Console**:
1. Navigate to https://console.apify.com/schedules
2. Click **"Create new schedule"**
3. Configure:
   - **Name**: "Gary's Guide SF Daily Crawl"
   - **Actor**: `iliazlobin/events-garysguide`
   - **Cron expression**: `0 2 * * *` (2 AM daily)
   - **Timezone**: America/Los_Angeles
   - **Input**:
     ```json
     {
       "region": "sf",
       "maxItems": 100,
       "lookForwardWindow": 30
     }
     ```
4. Click **"Create"**

**Common cron patterns**:
- `0 2 * * *` - Daily at 2 AM
- `0 */6 * * *` - Every 6 hours
- `0 9 * * 1` - Every Monday at 9 AM
- `0 0 1 * *` - First day of month at midnight

#### Creating a Schedule (API)

**Via Apify API**:
```bash
curl -X POST https://api.apify.com/v2/schedules \
  -H "Authorization: Bearer $APIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gary'\''s Guide SF Daily Crawl",
    "isEnabled": true,
    "isExclusive": false,
    "cronExpression": "0 2 * * *",
    "timezone": "America/Los_Angeles",
    "actorId": "iliazlobin/events-garysguide",
    "input": {
      "region": "sf",
      "maxItems": 100,
      "lookForwardWindow": 30
    }
  }'
```

#### Creating a Schedule (MCP)

**Via Claude Code**:
```
"Create a daily schedule for my Gary's Guide crawler:
- Run at 2 AM PST every day
- Collect up to 100 events
- Look 30 days ahead
- Crawl SF region"
```

#### Monitoring & Notifications

**Enable notifications**:
1. Go to Schedule settings
2. Enable **"Notify on run failure"**
3. Add email/Slack webhook

**Monitor runs**:
```bash
# List recent runs
apify actor runs ls iliazlobin/events-garysguide

# Get run details
apify actor run info <run-id>

# Get dataset from run
apify dataset get-items <dataset-id> --format json > events.json
```

**Via MCP**:
```
"Show me the last 5 runs of my Gary's Guide crawler and their status"
```

### Integration with Python SQLite

**Export from Apify**:
```bash
# Get dataset from latest run
apify dataset get-items <dataset-id> --format json > garysguide_events.json
```

**Import to SQLite**:
```python
import json
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.database.connection import DatabaseConnection
from events_agent.models.event import Event

# Load Apify dataset
with open('garysguide_events.json', 'r') as f:
    apify_events = json.load(f)

# Transform to Event objects
events = []
for item in apify_events:
    events.append(Event(
        event_id=item['url'].split('/')[-1],
        source='garysguide',
        url=item['url'],
        title=item['title'],
        start_datetime=item.get('dateStr'),
        location_name=item.get('location'),
        description=item.get('description'),
        image_url=item.get('imageUrl'),
        # ... map other fields
    ))

# Save to SQLite (auto-deduplication via UNIQUE constraint)
db = DatabaseConnection('data/events.db')
repo = SQLiteEventRepository(db)
repo.save_many(events)

print(f"Imported {len(events)} events from Apify")
```

### Configuration Management

**Configuration Files**:

1. **`src/apify/crawler_config.yaml`** - Crawler runtime settings
   - Rate limits, retries, timeouts
   - Session pool configuration
   - Autoscaling parameters
   - Managed via `scripts/manage_crawler_config.py`

2. **`src/apify/crawler_schedules.yaml`** - Apify platform settings
   - Memory allocation (default: 1024 MB)
   - Schedule definitions (cron, timezone)
   - Input configurations
   - Notification settings
   - Managed via `scripts/sync_apify_schedules.py`

**Key Pattern**: Defaults + per-crawler overrides
```yaml
defaults:
  memory_mbytes: 1024  # Default for all crawlers
  timeout_secs: 3600

schedules:
  garysguide:
    memory_mbytes: 2048  # Override for this crawler
```

**Management Commands**:

```bash
# List all crawler configs
python3 scripts/manage_crawler_config.py list

# Show specific crawler
python3 scripts/manage_crawler_config.py show --crawler garysguide

# Validate all configs
python3 scripts/manage_crawler_config.py validate

# List all schedules
python3 scripts/sync_apify_schedules.py list

# Sync schedules to Apify (dry run)
python3 scripts/sync_apify_schedules.py sync --dry-run

# Sync schedules to Apify (live)
export APIFY_API_TOKEN="your_token"
python3 scripts/sync_apify_schedules.py sync
```

**Benefits**:
- ✅ Explicit, version-controlled configuration
- ✅ No hardcoded values in crawler code
- ✅ Validation prevents invalid settings
- ✅ Easy to update multiple crawlers
- ✅ Cost optimization via explicit memory limits

**See**: `docs/CRAWLER_CONFIG_OPTIMIZATION.md` for full details

### Best Practices

**Performance**:
- Use `maxRequestsPerMinute: 3` to avoid rate limiting
- Set `requestHandlerTimeoutSecs: 300` for extensive scrolling
- Use `useFingerprints: true` for anti-blocking

**Error Handling**:
- Gracefully skip events with missing required fields
- Log errors but don't fail entire run
- Use retry logic with `maxRequestRetries: 3`

**Data Quality**:
- Validate dates before saving (avoid "Invalid time value")
- Handle missing DOM elements with try/catch
- Normalize data formats (dates, prices, locations)

**Cost Optimization** (Free tier: $5/month, 625 compute units):
- Use `maxItems` to limit crawl scope
- Schedule during off-peak hours
- Export datasets regularly (7-day retention on free plan)

## Architecture

**Structure**: `src/events_agent/` → `models/`, `database/`, `repositories/`, `processors/`, `utils/`, `legacy_crawlers/`
**Data Flow**: Crawlers → SQLite (auto-dedupe) → SQL queries → Event objects
**Storage**: `data/events.db` (SQLite with WAL mode)

## Key Components

**Database** (`data/events.db`):
- `events` table: UNIQUE(event_id, source) constraint for deduplication
- 8 performance indexes for fast queries
- Use `SQLiteEventRepository` for all data access

**Event Model** (`models/event.py`):
- Required: event_id, source, url, title, start_datetime
- Optional: 25+ fields for location, pricing, capacity, categorization

**Data Utilities** (`data/`):
- `jazz_venues.py`: 15+ NYC jazz venues with metadata
- `seasonal_events.py`: Valentine's Day detection (keywords, date ranges)

## Crawlers

### Active Sources

**Apify Cloud Crawlers** (target production form):
- **Gary's Guide** - Tech/startup events (SF, NYC regions)
- **Luma** - Provider crawler
- **Meetup** - Provider crawler
- **Eventbrite / Fever / TimeOut / DoNYC** - migrate toward this same actor model

**Legacy Local Python Crawlers**:
- Existing implementations under `src/events_agent/legacy_crawlers/` are transitional infrastructure and should be treated as migration candidates, not the default place for new crawler work.

**Planned**:
- **Funcheap SF** - Free/cheap SF events
- **SF Travel** - SF tourism and events

**Pattern**: All extend `BaseCrawler` with rate limiting, error handling, Playwright
**Usage**: `crawler.crawl(browser, "nyc")` → `repo.save_many(events)`

### Local Crawler SLAs

| Crawler | SLA | Run Command |
|---------|-----|-------------|
| **Eventbrite** | 100+ events within 5 minutes | `python scripts/run_eventbrite_crawler.py` |
| **Fever** | All events (~225) in ~12 min | Legacy local run only; migrate to Apify actor |

Eventbrite uses pagination (`?page=N`); ~20 events per page. Default: 6 pages → ~120 events in ~30s.
Fever uses `domcontentloaded` (not `networkidle`) to avoid timeout; DOM fallback when Schema.org fails.

**Adding new crawler**:
1. Extend `BaseCrawler`, implement `get_events_url()` and `extract_events_from_page()`
2. Add to `EventSource` enum in `models/event.py`
3. Add tests using `/unit-testing` skill

## Repository Pattern

**Primary**: `SQLiteEventRepository(DatabaseConnection('data/events.db'))`
- `save_many(events)` - Auto-dedupe via UNIQUE constraint
- `find_by_location_and_date(start, end, city, state, limit)` - Fast SQL queries
- `find_by_source(source)`, `find_by_date_range(start, end)`

**Legacy**: Avoid in-memory filters (`LocationFilter`, `DateFilter`) - use SQL queries instead

## Development

**Testing**: `pytest tests/unit/ -v` or use `/unit-testing` skill for new classes
**Tools**: Black (100 char), Ruff, Mypy, pytest
**Debug**: `logging.basicConfig(level=logging.DEBUG)`, `page.screenshot(path="debug.png")`

## Quick Reference

**Main command**: Apify actor runs plus Python import/validation scripts
**Database**: `data/events.db` (SQLite, open with `sqlite3` or DB Browser)
**Tests**: 104 tests (93 unit, 11 integration)
**Docs**: README.md, SQLITE_MIGRATION.md, queries/quick_analysis.sql
