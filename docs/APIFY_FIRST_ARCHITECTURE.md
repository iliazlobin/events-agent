# Apify-First Architecture

## Goal

Converge the project so every production crawler follows the same shape under `src/`:

- source crawler lives in `src/apify/<source>-crawler/`
- actor is scheduled on Apify
- actor output is imported into SQLite
- Python code remains shared infrastructure, not crawler-specific scraping logic

## Target Structure

```text
src/
  apify/
    <source>-crawler/
      .actor/
      inputs/
      src/
      package.json
    crawler_config.yaml
    crawler_schedules.yaml
  events_agent/
    database/           # SQLite schema and connections
    models/             # normalized event model
    repositories/       # import, query, enrichment
    utils/              # validation and helpers
    legacy_crawlers/    # Python bridge scrapers still used by src/apify Python actors
    conference_tracking/# one-off conference monitors outside the recurring source lane

scripts/
  sync_apify_schedules.py
  manage_crawler_config.py
  migrate_json_to_sqlite.py
  validate_crawl.py
```

## Repository Rules

### `src/apify/`

Use for:

- new crawlers
- source-specific scraping logic
- actor-local tests and sample inputs
- Apify deployment metadata

Do not use for:

- SQLite schema logic
- cross-source enrichment
- downstream filtering/query logic

### `src/events_agent/`

Use for:

- normalized `Event` contract
- SQLite storage and migrations
- import/adaptation from actor outputs
- aggregator enrichment
- quality checks and reporting

Do not use for:

- new source-specific crawler implementations unless the source is explicitly still legacy

## Migration Rule

When a source exists in both places, the Apify actor becomes the target implementation and the Python crawler becomes legacy until removed.

Recommended phases:

1. keep Python shared model and SQLite ingestion stable
2. port source scraper into `src/apify/<source>-crawler/`
3. align actor output to normalized event contract
4. import actor output into SQLite
5. stop using the Python source crawler
6. remove legacy crawler after coverage is proven

## Retirement Rule

Not every scraper should become an actor.

Retire instead of migrating when the code is:

- conference-specific
- one-off research/support tooling
- venue-specific monitoring outside the recurring event pipeline
- bespoke detail scraping that does not represent a durable source feed

Examples in this repo include `daytona_compute`, `winterfest`, `townofmammoth`, `jazznearyou`, `songkick`, and `event_detail_scraper`.

## Actor Output Contract

Each actor should emit fields that map cleanly into the normalized event model.

Preferred output shape:

```json
{
  "eventId": "source-specific-id",
  "source": "luma",
  "url": "https://...",
  "title": "Event title",
  "startDatetime": "2026-03-10T16:00:00.000Z",
  "endDatetime": null,
  "locationName": "Venue",
  "locationAddress": "Full address",
  "city": "San Francisco",
  "state": "CA",
  "isOnline": false,
  "description": "Description",
  "imageUrl": "https://...",
  "priceCents": null,
  "currency": "USD",
  "isFree": true,
  "originalProvider": null,
  "aggregatedFrom": null,
  "shortUrl": null,
  "aggregatorDetailUrl": null,
  "crawledAt": "2026-03-09T21:31:08.173Z",
  "detailCrawled": false
}
```

If the actor uses camelCase, keep a single importer/adapter in Python rather than letting every downstream consumer remap fields ad hoc.

Core-model rule:

- shared event identity, time, location, pricing, organizer, and aggregator provenance stay in the normalized `Event` model
- source-only spillover belongs in `sourceExtensions`
- do not create parallel source-specific top-level event models unless the extension proves reusable across multiple sources

## Quality Loop

Every crawler change should pass this loop before scheduling:

1. Local actor smoke test
   - `npx apify run --input-file=inputs/test.json --purge`
   - use a small deterministic input

2. Contract validation
   - inspect dataset items
   - verify required fields: `eventId`, `source`, `url`, `title`, `startDatetime`
   - verify source-specific expectations such as provider detection or price flags

3. SQLite import validation
   - map dataset items into `Event`
   - run repository upsert
   - confirm rows can round-trip through SQLite

4. Coverage / enrichment validation
   - for aggregators: run `promote_aggregator_metadata()`
   - inspect `find_aggregated_events_missing_direct_source()`
   - verify provider URL normalization issues are handled
   - verify provider rows and Gary's Guide rows agree on the same canonical URL/core fields

5. Schedule validation
   - `python3 scripts/sync_apify_schedules.py validate`
   - `python3 scripts/sync_apify_schedules.py sync --dry-run`

6. Scheduled smoke run
   - small scheduled input in Apify
   - inspect run logs and dataset sample

## Testing Strategy

### Actor tests

Inside each actor:

- parser/unit tests for route helpers
- minimal fixture-based tests where practical
- one small local smoke input under `inputs/`

### Python tests

Inside `tests/`:

- repository tests for import/upsert/enrichment
- integration test for SQLite flow
- importer tests for actor-output mapping when field names differ

### Release gate

A crawler is ready for scheduling only if:

- local actor run succeeds
- dataset sample is structurally correct
- import to SQLite succeeds
- no major pending coverage gaps are unexplained
- schedule config validates cleanly

## Documentation Rule

Any crawler migration or new actor should update:

- `README.md`
- `AGENTS.md`
- `src/apify/README.md`
- `src/apify/crawler_config.yaml` and/or `src/apify/crawler_schedules.yaml`
- any source-specific design doc if the architecture changes

## Naming

Apify actor naming standard:

- deployed actor: `events-<source>`
- local directory: `src/apify/<source>-crawler/`

Examples:

- `iliazlobin/events-garysguide`
- `iliazlobin/events-luma`
- `iliazlobin/events-meetup`
- `iliazlobin/events-eventbrite`
