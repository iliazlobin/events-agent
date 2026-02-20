# Removed Event Sources

## Overview

These sources were removed from the events-agent project to focus on tech/startup/professional community events (Gary's Guide style).

## Removed from EventSource Enum

The following event source types were removed from `src/events_agent/models/event.py`:

1. **SONGKICK** - Music/concert tracking only
2. **RESIDENTADVISOR** - Electronic music/nightlife only
3. **BANDSINTOWN** - Concert tracking only
4. **JAZZNEARYOU** - Jazz events only
5. **COZYMEAL** - Cooking classes only (too niche)

## Python Crawlers Archived

The following Python crawlers exist in the codebase but are **NOT RECOMMENDED** for use:

### `/src/events_agent/crawlers/jazznearyou_crawler.py`
- Contains: `JazzNearYouCrawler` and `SongkickCrawler`
- Reason: Music/jazz focus doesn't align with tech/professional events
- Status: Keep file for reference, but don't use in main.py

### `/src/events_agent/crawlers/cozymeal_crawler.py`
- Contains: `CozymealCrawler`
- Reason: Cooking classes only - too niche, low volume
- Status: Keep file for reference, but don't use in main.py

## Why These Were Removed

**Project Focus Shift**: The events-agent project is now focused on **tech/startup/professional networking events** similar to Gary's Guide. Sources that only cover music, concerts, or niche activities don't fit this focus.

**Music Sources Specifically**:
- Songkick, Resident Advisor, Bandsintown, Jazz Near You are excellent for music discovery
- However, they don't provide the tech/startup/professional events we're targeting
- Users seeking tech events aren't interested in concerts/nightlife

**Niche Sources**:
- Cozymeal (cooking classes) has low volume and narrow appeal
- Better to focus on general aggregators that include various event types

## Recommended Sources (Current Focus)

### ✅ Tech/Startup/Professional Focus
1. **Gary's Guide** - Premier tech/startup aggregator (NYC, SF, Boston, etc.)
2. **Luma** - Tech/community events platform
3. **Meetup** - Professional networking and community groups
4. **Eventbrite** - General aggregator with strong tech presence
5. **DoNYC** - NYC local events (community focus)

### ✅ Curated General Sources
6. **Fever** - Curated experiences (workshops, talks, cultural)
7. **TimeOut** - City events (filterable for relevant categories)
8. **Funcheap SF** - Free/cheap SF community events
9. **SF Travel** - Official SF tourism (major events)

## Migration Notes

If you need to re-enable these sources in the future:

1. Add back to `EventSource` enum in `models/event.py`
2. Import crawlers in `main.py`
3. Add to crawler execution flow
4. Update database queries to handle music-specific fields

## Data Already Collected

Any events already crawled from these sources remain in the database with their original source values. The database schema still supports these fields:
- `genre` (str) - For music genre
- `performer_names` (List[str]) - For artists/performers
- `chef_name`, `chef_rating`, etc. - For cooking classes

You can query old data, but new crawls will not collect from these sources.

---

**Removed**: 2026-02-19
**Reason**: Focus shift to tech/startup/professional events
