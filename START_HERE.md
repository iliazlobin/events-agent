# 🎵💝 Jazz & Valentine's Day Events - Ready to Use!

## ✅ What's Ready

I've implemented a complete system for finding **jazz events** and **Valentine's Day activities** in NYC. Here's what you have:

### 🎯 4 New Event Sources
- **Jazz Near You** - 80+ NYC jazz venues
- **Songkick** - High-quality jazz concert data
- **TimeOut NYC** - Cultural events (jazz + Valentine's)
- **DoNYC** - Curated Valentine's Day events

### 🗄️ Enhanced Data Model
- **25+ new fields** for music/performance events
- **Genre tagging** (jazz, blues, etc.)
- **Performer names** extraction
- **Tags** for categorization (valentines-day, romantic, date-night)
- **Database migration** (auto-runs next time)

### 🎸 Jazz Infrastructure
- **15+ major venues** indexed (Village Vanguard, Blue Note, Birdland, etc.)
- **Venue lookup** utilities
- **Neighborhood grouping** (Greenwich Village, Midtown, Harlem)

### 💝 Valentine's Day Infrastructure
- **30+ keywords** for detection
- **Date range** calculator (Feb 7-16)
- **Date-night event** identification
- **Romantic neighborhoods** list

## 🚀 Quick Start (3 Steps)

### 1. Run the Example Script

```bash
cd /Users/iliazlobin/Code/events-agent
python examples/crawl_jazz_and_valentines.py
```

This will:
- Crawl all 4 new sources
- Save events to database (with auto-deduplication)
- Show you sample results
- Give you SQL query examples

### 2. Check the Results

```bash
# Open database
sqlite3 data/events.db

# Count jazz events
SELECT COUNT(*) FROM events WHERE genre = 'jazz';

# See jazz venues
SELECT DISTINCT location_name FROM events WHERE genre = 'jazz';

# Valentine's events
SELECT title, start_datetime FROM events 
WHERE tags LIKE '%valentine%' 
ORDER BY start_datetime 
LIMIT 10;
```

### 3. Use the SQL Queries

```bash
# Run pre-made queries
sqlite3 data/events.db < queries/jazz_and_valentines.sql
```

This file has **70+ queries** for:
- Jazz events by venue
- Valentine's Day filtering
- Price analysis
- Neighborhood trends
- Data quality checks

## 📚 Documentation (Start Here)

### Quick Reference (3 minutes)
👉 **`QUICK_REFERENCE.md`** - Fast lookup guide with code snippets

### Implementation Summary (10 minutes)
👉 **`IMPLEMENTATION_SUMMARY.md`** - What was built and how to use it

### Complete Guide (30 minutes)
👉 **`NEW_SOURCES.md`** - Deep dive into all new sources (5,000 words)

### Files Created
👉 **`FILES_CREATED.md`** - List of all 11 new files and what they do

## 💻 Code Examples

### Find Jazz Events

```python
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.database.connection import DatabaseConnection

db = DatabaseConnection('data/events.db')
repo = SQLiteEventRepository(db)

# All jazz events
jazz_events = [e for e in repo.find_all() if e.genre == "jazz"]
print(f"Found {len(jazz_events)} jazz events")

# Events at famous venues
from events_agent.data import is_known_jazz_venue

famous_venue_events = [
    e for e in jazz_events 
    if e.location_name and is_known_jazz_venue(e.location_name)
]

for event in famous_venue_events[:5]:
    print(f"- {event.title} at {event.location_name}")
```

### Find Valentine's Day Events

```python
from events_agent.data import get_valentines_date_range, is_valentines_event

# Get date range (Feb 7-16)
vday_start, vday_end = get_valentines_date_range(2026)

# Query events in that range
vday_events = repo.find_by_date_range(vday_start, vday_end)

# Filter by Valentine's keywords
valentine_events = [
    e for e in vday_events
    if is_valentines_event(e.title, e.description, e.tags)
]

print(f"Found {len(valentine_events)} Valentine's Day events")
```

## 🗂️ What You Have Now

### Source Code (5 files, ~1,500 lines)
- ✅ `jazznearyou_crawler.py` - Jazz Near You + Songkick crawlers
- ✅ `timeout_crawler.py` - TimeOut NYC + DoNYC crawlers  
- ✅ `jazz_venues.py` - 15+ NYC jazz venues with metadata
- ✅ `seasonal_events.py` - Valentine's Day detection utilities
- ✅ `data/__init__.py` - Clean module exports

### Documentation (4 files, ~12,000 words)
- ✅ `NEW_SOURCES.md` - Comprehensive guide (5K words)
- ✅ `IMPLEMENTATION_SUMMARY.md` - Overview (4K words)
- ✅ `QUICK_REFERENCE.md` - Fast lookup (3K words)
- ✅ `FILES_CREATED.md` - File listing

### SQL & Examples (2 files)
- ✅ `jazz_and_valentines.sql` - 70+ production queries
- ✅ `crawl_jazz_and_valentines.py` - Working example script

### Database Updates
- ✅ 25+ new fields (genre, performer_names, tags, etc.)
- ✅ 4 new indexes (genre, category, experience_type, rating)
- ✅ Migration 2 (auto-runs on next use)

## 🎸 Jazz Venues Indexed

**Greenwich Village**:
- Village Vanguard (123 cap) - Historic, opened 1935
- Blue Note (200) - Premier jazz venue
- Smalls (60) - Intimate basement club
- Mezzrow (60) - Sister to Smalls
- Zinc Bar (100) - Latin jazz

**Midtown**:
- Birdland (160) - Classic jazz club
- Iridium (180) - Modern venue
- Dizzy's Club (140) - Jazz at Lincoln Center

**Other**: Jazz Gallery, The Django, Nublu, Roulette, Minton's Playhouse, Bill's Place

## 📊 SQL Query Examples

```sql
-- Jazz events this week
SELECT title, start_datetime, location_name, genre
FROM events
WHERE genre = 'jazz'
  AND start_datetime >= date('now')
  AND start_datetime < date('now', '+7 days')
ORDER BY start_datetime;

-- Valentine's Day events (Feb 7-16)
SELECT title, start_datetime, location_name, tags
FROM events
WHERE (tags LIKE '%valentine%' OR title LIKE '%valentine%')
  AND start_datetime >= '2026-02-07'
  AND start_datetime <= '2026-02-16'
ORDER BY start_datetime;

-- Events at famous jazz venues
SELECT title, location_name, start_datetime
FROM events
WHERE location_name IN (
  'Village Vanguard', 'Blue Note', 'Smalls', 'Birdland'
)
ORDER BY start_datetime;
```

**70+ more in**: `queries/jazz_and_valentines.sql`

## 🔧 Integration with Main System

To add these crawlers to your main crawler:

```python
# In main.py, add imports
from events_agent.crawlers.jazznearyou_crawler import JazzNearYouCrawler, SongkickCrawler
from events_agent.crawlers.timeout_crawler import TimeOutNYCCrawler, DoNYCCrawler

# In main() function, after existing crawlers:
print("\n📀 Crawling Jazz Near You...")
jny_crawler = JazzNearYouCrawler()
jazz_events = jny_crawler.crawl(browser, "nyc")
repo.save_many(jazz_events)

print("\n🎸 Crawling Songkick...")
sk_crawler = SongkickCrawler()
sk_events = sk_crawler.crawl(browser, "nyc")
repo.save_many(sk_events)

print("\n💝 Crawling TimeOut NYC...")
to_vday = TimeOutNYCCrawler(category="valentines-day")
vday_events = to_vday.crawl(browser, "newyork")
repo.save_many(vday_events)

print("\n❤️ Crawling DoNYC...")
donyc = DoNYCCrawler()
donyc_events = donyc.crawl(browser, "valentines-day")
repo.save_many(donyc_events)
```

See full integration guide in `NEW_SOURCES.md`.

## ⚠️ Before Running in Production

1. **Test crawlers individually** (example script does this)
2. **Backup database**: `cp data/events.db data/events.db.backup`
3. **Check for site changes** (CSS selectors may need adjustment)
4. **Monitor rate limits** (2-second delay by default)
5. **Enable logging** for debugging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

## 🎯 What You Can Do Now

### Find Jazz Events
- ✅ By venue (Village Vanguard, Blue Note, etc.)
- ✅ By neighborhood (Greenwich Village, Midtown, Harlem)
- ✅ By artist/performer
- ✅ By date range
- ✅ By price

### Find Valentine's Day Events
- ✅ Date range filtering (Feb 7-16)
- ✅ Keyword detection (romantic, couples, date night)
- ✅ Event type filtering (cooking class, concert, etc.)
- ✅ Neighborhood filtering (romantic areas)
- ✅ Free vs paid

### Analytics
- ✅ Count events by source
- ✅ Price distributions
- ✅ Venue popularity
- ✅ Neighborhood trends
- ✅ Date trends

## 📞 Next Steps

1. **Read**: `QUICK_REFERENCE.md` (3 min)
2. **Run**: `python examples/crawl_jazz_and_valentines.py`
3. **Query**: `sqlite3 data/events.db < queries/jazz_and_valentines.sql`
4. **Explore**: Browse the 70+ SQL queries
5. **Integrate**: Add crawlers to your main.py (see `NEW_SOURCES.md`)
6. **Customize**: Modify venue index, keywords, or crawlers as needed

## 🎉 Summary

✅ **4 new event sources** (jazz + Valentine's)  
✅ **15+ jazz venues** indexed  
✅ **25+ new database fields**  
✅ **70+ SQL queries** ready to use  
✅ **12,000 words** of documentation  
✅ **Working example** script  
✅ **Database migration** ready  

**Status**: ✅ Complete and ready for testing

**Need help?** Check the documentation files:
- Quick start → `QUICK_REFERENCE.md`
- Overview → `IMPLEMENTATION_SUMMARY.md`  
- Details → `NEW_SOURCES.md`
- Files → `FILES_CREATED.md`

---

**Version**: 0.2.0  
**Date**: 2026-02-10  
**Ready to use**: ✅ Yes!
