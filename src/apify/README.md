# Apify Crawlers

This directory is the production home for source-specific event crawlers.

## Standard

Every production crawler should follow this pattern:

```text
src/apify/<source>-crawler/
├── .actor/
├── inputs/
├── main.py | src/
└── runtime-specific files
```

Naming rules:

- local directory: `<source>-crawler`
- deployed actor: `iliazlobin/events-<source>`
- title: `Events <Source>`

Examples:

- `src/apify/garysguide-crawler/` -> `iliazlobin/events-garysguide`
- `src/apify/luma-crawler/` -> `iliazlobin/events-luma`
- `src/apify/meetup-crawler/` -> `iliazlobin/events-meetup`
- `src/apify/eventbrite-crawler/` -> `iliazlobin/events-eventbrite`
- `src/apify/fever-crawler/` -> `iliazlobin/events-fever`
- `src/apify/timeout-crawler/` -> `iliazlobin/events-timeout`
- `src/apify/donyc-crawler/` -> `iliazlobin/events-donyc`

## Project Boundary

`src/apify/` owns:

- source-specific crawling logic
- actor input schema
- actor-local tests
- Apify deployment metadata

`src/events_agent/` owns:

- normalized event model
- SQLite storage and migrations
- actor output import/adaptation
- aggregator enrichment
- quality validation

Do not add new production crawlers under `src/events_agent/`; source crawling belongs in `src/apify/`.

## Active Actors

### Gary's Guide

- Local: `src/apify/garysguide-crawler/`
- Deployed actor: `iliazlobin/events-garysguide`
- Role: aggregator/discovery feed

### Luma

- Local: `src/apify/luma-crawler/`
- Deployed actor: `iliazlobin/events-luma`
- Role: provider detail crawler

### Meetup

- Local: `src/apify/meetup-crawler/`
- Deployed actor: `iliazlobin/events-meetup`
- Role: provider detail crawler

### Eventbrite

- Local: `src/apify/eventbrite-crawler/`
- Deployed actor: `iliazlobin/events-eventbrite`
- Role: ticketing platform source crawler

### Fever

- Local: `src/apify/fever-crawler/`
- Deployed actor: `iliazlobin/events-fever`
- Role: entertainment platform source crawler

### TimeOut

- Local: `src/apify/timeout-crawler/`
- Deployed actor: `iliazlobin/events-timeout`
- Role: curated editorial source crawler

### DoNYC

- Local: `src/apify/donyc-crawler/`
- Deployed actor: `iliazlobin/events-donyc`
- Role: curated local source crawler

## Workflow

### Local development

```bash
cd src/apify/<source>-crawler
```

TypeScript/Crawlee actors:

```bash
npm install
npm run build
npx apify run --input-file=inputs/test.json --purge
```

Python bridge actors:

```bash
PYTHONPATH=src ACTOR_INPUT_PATH=inputs/test.json python3 main.py
```

### Deploy

```bash
cd src/apify/<source>-crawler
npx apify push --no-prompt
```

### Schedule validation

```bash
python3 scripts/sync_apify_schedules.py validate
python3 scripts/sync_apify_schedules.py sync --dry-run
```

## Quality Loop

Every actor change should close this loop:

1. local actor smoke run
2. dataset sample inspection
3. SQLite import/upsert check
4. aggregator enrichment / pending coverage check
5. schedule dry-run validation

See [docs/APIFY_FIRST_ARCHITECTURE.md](../../docs/APIFY_FIRST_ARCHITECTURE.md) for the full repo-level workflow.

## Config Files

- [crawler_config.yaml](crawler_config.yaml): runtime defaults and crawler overrides
- [crawler_schedules.yaml](crawler_schedules.yaml): actor IDs, inputs, and schedules
- [../../docs/CRAWLER_CONFIG_OPTIMIZATION.md](../../docs/CRAWLER_CONFIG_OPTIMIZATION.md): config operations
