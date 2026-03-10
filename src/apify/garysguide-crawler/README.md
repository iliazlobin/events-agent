# Gary's Guide Events Crawler

Scrapes tech and startup events from Gary's Guide for NYC and SF regions.

## Features

- ✅ Scrapes 80+ events per region (Feb-May 2026 date range)
- ✅ Supports NYC and SF regions
- ✅ Three-stage scraping: listing → detail pages → final event URLs
- ✅ Resolves gary.to redirect links automatically
- ✅ Extracts events from multiple platforms (Luma, Eventbrite, Meetup, etc.)

## How It Works

### Architecture

```
1. Listing Page (garysguide.com/events?region=sf)
   ↓ Scrolls & extracts event detail page URLs

2. Detail Pages (garysguide.com/events/[id]/[slug])
   ↓ Extracts gary.to registration links

3. Gary.to Redirects
   ↓ Resolves to final event URLs

4. Final Event Pages (luma.com, eventbrite.com, meetup.com, etc.)
   ↓ Scrapes event details (title, date, location, description, image)
```

### Key Implementation Details

- **Scrolling**: Auto-scrolls listing page to load all events
- **Redirect Resolution**: Uses HTTP fetch to resolve gary.to links without browser overhead
- **Rate Limiting**: 3 requests/minute to avoid blocking
- **Error Handling**: Gracefully handles missing data, saves partial results
- **Selectors**: Generic CSS selectors work across multiple event platforms

## Input Schema

```json
{
  "region": "sf",           // "sf" or "nyc"
  "maxItems": 100,          // Max events to collect (82+ available per region)
  "lookForwardWindow": 90   // Days to look ahead (not currently used)
}
```

## Output Schema

```json
{
  "url": "https://luma.com/event-id",
  "garyToUrl": "http://gary.to/abc123",
  "garysGuideUrl": "https://www.garysguide.com/events/xyz/event-name",
  "title": "Event Title",
  "dateStr": "Tuesday, Feb 17 · 5:00 PM PST",
  "location": "Venue Name, City, State",
  "description": "Event description...",
  "imageUrl": "https://...",
  "source": "garysguide",
  "scrapedAt": "2026-02-19T12:00:00.000Z"
}
```

## Testing Locally

```bash
# Install dependencies
npm install

# Run with default settings (10 events)
apify run

# Run with custom input
apify run --input-file=inputs/test-sf-full.json

# Run full collection (all 82 events)
apify run --input '{"region":"sf","maxItems":100}'
```

## Test Input Files

- `inputs/test-sf-10.json` - Quick test (10 events, ~2 minutes)
- `inputs/test-sf-full.json` - Full collection (100 events, ~50 minutes)

## Deployment

```bash
# Build TypeScript
npm run build

# Deploy to Apify
apify push
```

## Performance

- **Events per region**: ~82 (Feb 17 - May 18, 2026)
- **Requests per run**: ~165 (1 listing + 82 detail + 82 final)
- **Runtime**: ~50-55 minutes (local, with rate limiting)
- **Success rate**: 98% (80/82 events collected successfully)

## Known Issues

1. Some events may not have gary.to links (skipped)
2. Date format varies by platform (Luma, Eventbrite, Meetup use different formats)
3. Sponsored ads may appear in results (filtered by checking for event detail pages)

## Future Improvements

- [ ] Implement `lookForwardWindow` date filtering
- [ ] Add date normalization for consistent formatting
- [ ] Support additional regions (if Gary's Guide expands)
- [ ] Add retry logic for failed gary.to resolutions
- [ ] Extract more metadata (price, capacity, organizer)
