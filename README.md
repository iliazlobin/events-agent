# Events Agent

SF/NYC event collection system centered on scheduled actors plus SQLite ingestion.

## Direction

The project is converging to a single `src/`-rooted crawler architecture:

- `src/apify/` contains crawler actors, local test inputs, and schedule/config YAML.
- `src/events_agent/` contains shared Python infrastructure:
  - SQLite storage
  - event models
  - import/enrichment logic
  - schedule/config sync helpers
  - quality validation
- New source crawlers should be added in `src/apify/<source>-crawler/`, not in the Python package.

The detailed target structure and quality loop are documented in [docs/APIFY_FIRST_ARCHITECTURE.md](/Users/iliazlobin/Code/events-agent/docs/APIFY_FIRST_ARCHITECTURE.md).

## Project Layout

```text
events-agent/
├── src/
│   ├── apify/                  # Actor code, local inputs, config YAML
│   │   ├── garysguide-crawler/
│   │   ├── luma-crawler/
│   │   ├── meetup-crawler/
│   │   ├── crawler_config.yaml
│   │   └── crawler_schedules.yaml
│   └── events_agent/           # Shared Python infrastructure
│       ├── database/
│       ├── models/
│       ├── repositories/
│       ├── utils/
│       ├── legacy_crawlers/    # Python bridge scrapers for active Python actors
│       └── conference_tracking/
├── scripts/                    # Config sync, migration, validation
├── docs/                       # Current operating docs
├── design/                     # Architecture and migration design notes
└── tests/
```

## Current Operating Model

1. Actors under `src/apify/` collect source data into datasets.
2. Python utilities normalize/import results into `data/events.db`.
3. SQLite queries and enrichment logic deduplicate, promote aggregator metadata, and power downstream analysis.
4. Schedules are managed from versioned YAML in `src/apify/crawler_schedules.yaml`.

## Source Policy

- Production pipeline sources live only in `src/apify/`.
- `src/events_agent/legacy_crawlers/` is reserved for Python actor bridge implementations that still power `src/apify/*/main.py`.
- Conference-specific or one-off scrapers belong in `src/events_agent/conference_tracking/` or should be retired entirely.
- One-off conference or special-purpose scrapers are not part of the production source architecture and should be retired instead of migrated into the scheduled actor lane.

## Key Docs

- [docs/APIFY_FIRST_ARCHITECTURE.md](/Users/iliazlobin/Code/events-agent/docs/APIFY_FIRST_ARCHITECTURE.md)
- [src/apify/README.md](/Users/iliazlobin/Code/events-agent/src/apify/README.md)
- [design/AGGREGATOR_PATTERN.md](/Users/iliazlobin/Code/events-agent/design/AGGREGATOR_PATTERN.md)
- [docs/CRAWLER_CONFIG_OPTIMIZATION.md](/Users/iliazlobin/Code/events-agent/docs/CRAWLER_CONFIG_OPTIMIZATION.md)

## Development

### Actor development

```bash
cd src/apify/garysguide-crawler
npm install
npm run build
npx apify run --input-file=inputs/test-sf-10.json --purge
```

### Python infrastructure

```bash
source .venv/bin/activate
pytest tests/unit -q
pytest tests/integration/test_sqlite_flow.py -q
python3 scripts/sync_apify_schedules.py validate
```

## Quality Loop

Every crawler change should close the loop in this order:

1. Actor-level local test run with a small input file.
2. Output schema inspection against the normalized event contract.
3. SQLite import/upsert validation.
4. Aggregator promotion / missing-direct-source query check.
5. Scheduled dry-run config validation.

That loop is spelled out in [docs/APIFY_FIRST_ARCHITECTURE.md](/Users/iliazlobin/Code/events-agent/docs/APIFY_FIRST_ARCHITECTURE.md).
