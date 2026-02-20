# Apify Event Crawlers

This directory contains Apify Actors for scraping events from various platforms.

## Active Crawlers

### 1. Gary's Guide Crawler (`garysguide-crawler/`)

**Status**: ✅ Active & Tested (v2.0)  
**Platform**: Gary's Guide Tech Events  
**Regions**: NYC, SF  
**Events**: ~82 per region  
**Date Range**: Feb 17 - May 18, 2026

**Features**:
- Three-stage scraping (listing → detail → final event URLs)
- Resolves gary.to redirects automatically
- Extracts from multiple platforms (Luma, Eventbrite, Meetup)
- Auto-scrolling to load all events

**Test Results**:
- ✅ 80/82 events collected (98% success rate)
- ✅ Runtime: ~50 minutes (local with rate limiting)
- ✅ Date range verified: Feb 17 - May 18

**Usage**:
```bash
cd garysguide-crawler
apify run --input '{"region":"sf","maxItems":100}'
```

---

### 2. Luma Crawler (`luma-crawler/`)

**Status**: ✅ Deployed to Apify Cloud  
**Platform**: Luma Events  
**Actor Name**: `iliazlobin/events-crawler-luma`

**Features**:
- Scrolls through Luma event listings
- Extracts from Next.js JSON data
- Date-based filtering with `lookForwardWindow`

**Usage**:
```bash
cd luma-crawler
apify run --input '{"urls":["https://lu.ma/nyc"],"maxItems":150,"lookForwardWindow":30}'
```

---

### 3. Meetup Crawler (`meetup-crawler/`)

**Status**: ✅ Deployed to Apify Cloud  
**Platform**: Meetup.com Events  
**Actor Name**: `iliazlobin/events-crawler-meetup`

**Features**:
- GraphQL API integration
- Group-based event discovery
- Date range filtering

**Usage**:
```bash
cd meetup-crawler
apify run --input '{"urls":["https://www.meetup.com/..."],"maxItems":150}'
```

---

## Removed/Deprecated

- ❌ `eventbrite-crawler` - Removed (duplicate/old structure)

---

## Common Workflow

All crawlers follow this pattern:

1. **Install**: `npm install`
2. **Build**: `npm run build`
3. **Test Locally**: `apify run --input-file=inputs/test.json`
4. **Deploy**: `apify push`
5. **Run on Cloud**: `apify actor call iliazlobin/actor-name`

---

## Architecture

All crawlers use:
- **Template**: `ts-crawlee-puppeteer-chrome`
- **Framework**: Crawlee + Puppeteer
- **Language**: TypeScript
- **Pattern**: Router-based handlers (listing → detail)

---

## Input Schema (Common Fields)

```json
{
  "urls": ["https://..."],           // Start URLs
  "maxItems": 150,                   // Max events to collect
  "lookForwardWindow": 30,           // Days to look ahead
  "maxScrolls": 20                   // Max scroll iterations (if applicable)
}
```

---

## Output Schema (Common Fields)

```json
{
  "url": "https://...",
  "title": "Event Title",
  "dateStart": "2026-02-17T17:00:00-08:00",
  "dateEnd": "2026-02-17T19:00:00-08:00",
  "location": "Venue Name",
  "address": "123 Street, City, State",
  "description": "Event description...",
  "price": 25.00,
  "attendees": 50,
  "source": "garysguide|luma|meetup",
  "scrapedAt": "2026-02-19T12:00:00.000Z"
}
```

---

## Performance Comparison

| Crawler | Events/Run | Runtime (Local) | Success Rate |
|---------|-----------|----------------|--------------|
| Gary's Guide | 80-82 | ~50 min | 98% |
| Luma | 150+ | ~30 min | 95%+ |
| Meetup | 100+ | ~25 min | 90%+ |

*Runtime based on local runs with rate limiting (3 req/min)*

---

## Deployment Status

| Crawler | Local | Apify Cloud | Actor ID |
|---------|-------|-------------|----------|
| Gary's Guide | ✅ | ⏳ Pending | - |
| Luma | ✅ | ✅ | `iliazlobin/events-crawler-luma` |
| Meetup | ✅ | ✅ | `iliazlobin/events-crawler-meetup` |

---

## Next Steps

1. Deploy Gary's Guide crawler to Apify Cloud
2. Set up scheduled runs for all crawlers
3. Configure webhooks for data integration
4. Add monitoring/alerting for failures

---

## Documentation

- [Implementation Guide](./IMPLEMENTATION_GUIDE.md)
- [TODO List](./TODO.md)
- Individual crawler READMEs in each subdirectory
