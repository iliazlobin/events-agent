# Quick Reference: Jazz & Valentine's Day Events

## 📚 Documentation Files

- **IMPLEMENTATION_SUMMARY.md** - What was built and how to use it (START HERE)
- **NEW_SOURCES.md** - Detailed documentation of new sources (5000+ words)
- **AGENTS.md** - Complete system documentation (updated with new features)
- **queries/jazz_and_valentines.sql** - 70+ SQL queries for analytics
- **examples/crawl_jazz_and_valentines.py** - Working example script

## 🎯 Quick Start

### 1. Run the Example

```bash
cd /Users/iliazlobin/Code/events-agent
python examples/crawl_jazz_and_valentines.py
```

### 2. Check the Results

```bash
# Open database
sqlite3 data/events.db

# Count jazz events
SELECT COUNT(*) FROM events WHERE genre = 'jazz';

# See Valentine's events
SELECT title, start_datetime, location_name 
FROM events 
WHERE tags LIKE '%valentine%' 
LIMIT 10;
```

## 🎵 New Event Sources

| Source | Type | Coverage | Status |
|--------|------|----------|--------|
| Jazz Near You | Jazz | 80+ NYC venues | ✅ Ready |
| Songkick | Music (Jazz) | High quality | ✅ Ready |
| TimeOut NYC | Cultural | Multi-category | ✅ Ready |
| DoNYC | Curated | Valentine's focus | ✅ Ready |

## 📦 What's Included

### New Crawlers (4)
- `jazznearyou_crawler.py` - Jazz Near You + Songkick
- `timeout_crawler.py` - TimeOut NYC + DoNYC

### Data Infrastructure (2)
- `jazz_venues.py` - 15+ major NYC jazz venues
- `seasonal_events.py` - Valentine's Day detection

### Database Updates
- Migration 2: 25+ new fields
- New indexes for genre, category, tags
- Support for JSON arrays

### SQL Queries (70+)
- Jazz events by venue
- Valentine's Day events  
- Price analysis
- Neighborhood trends
- Data quality checks

## 💻 Code Examples

### Use Jazz Venue Index

```python
from events_agent.data import is_known_jazz_venue, get_venue_by_name

# Check venue
if is_known_jazz_venue("Blue Note"):
    venue = get_venue_by_name("Blue Note")
    print(f"{venue.name} - Capacity: {venue.capacity}")
```

### Detect Valentine's Events

```python
from events_agent.data import is_valentines_event, get_valentines_date_range

# Check event
if is_valentines_event(title="Romantic Jazz Night", tags=["jazz", "couples"]):
    print("Perfect for Valentine's Day!")

# Get date range
start, end = get_valentines_date_range(2026)
print(f"Valentine's period: {start} to {end}")
```

### Crawl New Sources

```python
from playwright.sync_api import sync_playwright
from events_agent.crawlers.jazznearyou_crawler import JazzNearYouCrawler
from events_agent.crawlers.timeout_crawler import TimeOutNYCCrawler

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # Jazz events
    jazz_crawler = JazzNearYouCrawler()
    jazz_events = jazz_crawler.crawl(browser, "nyc")
    
    # Valentine's events
    vday_crawler = TimeOutNYCCrawler(category="valentines-day")
    vday_events = vday_crawler.crawl(browser, "newyork")
    
    browser.close()
    
# Save to database
repo.save_many(jazz_events + vday_events)
```

### Query Events

```python
from events_agent.repositories.sqlite_repository import SQLiteEventRepository
from events_agent.database.connection import DatabaseConnection

db = DatabaseConnection('data/events.db')
repo = SQLiteEventRepository(db)

# All jazz events
jazz_events = [e for e in repo.find_all() if e.genre == "jazz"]

# Valentine's Day date range
from events_agent.data import get_valentines_date_range
vday_start, vday_end = get_valentines_date_range(2026)
vday_events = repo.find_by_date_range(vday_start, vday_end)
```

## 🗄️ SQL Queries

### Jazz Events

```sql
-- Events at famous venues
SELECT title, location_name, start_datetime, url
FROM events
WHERE location_name IN (
  'Village Vanguard', 'Blue Note', 'Smalls', 
  'Birdland', 'Dizzy''s Club'
)
ORDER BY start_datetime;

-- Jazz events this week
SELECT title, start_datetime, location_name, genre
FROM events
WHERE genre = 'jazz'
  AND start_datetime >= date('now')
  AND start_datetime < date('now', '+7 days')
ORDER BY start_datetime;
```

### Valentine's Day Events

```sql
-- Valentine's events (Feb 7-16)
SELECT title, start_datetime, location_name, tags
FROM events
WHERE (tags LIKE '%valentine%' OR title LIKE '%valentine%')
  AND start_datetime >= '2026-02-07'
  AND start_datetime <= '2026-02-16'
ORDER BY start_datetime;

-- Romantic date-night events
SELECT title, experience_type, location_name, rating
FROM events
WHERE experience_type IN ('cooking class', 'wine tasting', 'concert')
  AND (tags LIKE '%couples%' OR tags LIKE '%romantic%')
  AND rating >= 4.0
ORDER BY rating DESC;
```

**70+ more queries in**: `queries/jazz_and_valentines.sql`

## 🎸 Jazz Venues

### Major Venues Indexed

**Greenwich Village**:
- Village Vanguard (123 capacity) - Historic, opened 1935
- Blue Note (200) - Premier jazz venue
- Smalls (60) - Intimate basement club
- Mezzrow (60) - Sister to Smalls
- Zinc Bar (100) - Latin jazz focus

**Midtown**:
- Birdland (160) - Classic jazz club
- Iridium (180) - Modern venue
- Dizzy's Club (140) - Jazz at Lincoln Center

**Harlem**:
- Minton's Playhouse - Historic bebop birthplace
- Bill's Place (40) - Speakeasy-style

**Other**:
- Jazz Gallery (120) - Emerging artists
- The Django (80) - Modern lounge
- Roulette (400) - Experimental

## 💝 Valentine's Day Features

### Keywords Detected
valentine, romantic, couples, date night, love, sweetheart, galentine, singles

### Event Types
dinner, cooking class, wine tasting, cocktail class, paint and sip, jazz concert, comedy show, theater, dance class, spa, cruise, rooftop

### Romantic Neighborhoods
Greenwich Village, West Village, SoHo, Tribeca, Chelsea, Brooklyn Heights, DUMBO, Williamsburg

### Date Range
**Valentine's Period**: Feb 7-16 (week before + weekend after)

## 📊 Database Schema

### New Fields (Migration 2)

```sql
-- Music/Performance
genre TEXT
performer_names TEXT  -- JSON array
duration_minutes INTEGER

-- Categorization
experience_type TEXT
category TEXT
tags TEXT  -- JSON array

-- Enhanced content
image_url TEXT
ai_summary TEXT
rating REAL
review_count INTEGER

-- ... 15 more fields (see NEW_SOURCES.md)
```

### New Indexes

```sql
CREATE INDEX idx_events_genre ON events(genre);
CREATE INDEX idx_events_category ON events(category);
CREATE INDEX idx_events_experience_type ON events(experience_type);
CREATE INDEX idx_events_rating ON events(rating);
```

## 🧪 Testing Before Production

1. **Test one crawler first**:
```bash
python examples/crawl_jazz_and_valentines.py
```

2. **Verify data quality**:
```bash
sqlite3 data/events.db "SELECT COUNT(*) FROM events WHERE genre = 'jazz';"
```

3. **Check for errors**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

4. **Backup database**:
```bash
cp data/events.db data/events.db.backup
```

## 📝 Integration Steps

### Add to main.py

```python
# 1. Import new crawlers (at top)
from events_agent.crawlers.jazznearyou_crawler import JazzNearYouCrawler, SongkickCrawler
from events_agent.crawlers.timeout_crawler import TimeOutNYCCrawler, DoNYCCrawler

# 2. Add to main() function (after existing crawlers)
print("\n📀 Crawling Jazz Near You...")
jny_crawler = JazzNearYouCrawler()
jazz_events = jny_crawler.crawl(browser, "nyc")
repo.save_many(jazz_events)
all_events.extend(jazz_events)

print("\n🎸 Crawling Songkick (Jazz)...")
sk_crawler = SongkickCrawler()
sk_events = sk_crawler.crawl(browser, "nyc")
repo.save_many(sk_events)
all_events.extend(sk_events)

print("\n💝 Crawling TimeOut NYC (Valentine's)...")
to_vday = TimeOutNYCCrawler(category="valentines-day")
vday_events = to_vday.crawl(browser, "newyork")
repo.save_many(vday_events)
all_events.extend(vday_events)

print("\n🎭 Crawling TimeOut NYC (Jazz)...")
to_jazz = TimeOutNYCCrawler(category="jazz")
to_jazz_events = to_jazz.crawl(browser, "newyork")
repo.save_many(to_jazz_events)
all_events.extend(to_jazz_events)

print("\n❤️ Crawling DoNYC...")
donyc_crawler = DoNYCCrawler()
donyc_events = donyc_crawler.crawl(browser, "valentines-day")
repo.save_many(donyc_events)
all_events.extend(donyc_events)
```

## 🎯 Key Achievements

✅ 4 new event sources (jazz + Valentine's Day)
✅ 15+ NYC jazz venues indexed
✅ 25+ new database fields
✅ 70+ SQL analytics queries
✅ Valentine's Day detection system
✅ Complete documentation (10,000+ words)
✅ Working example script
✅ Database migration (auto-runs)

## 🔗 Resources

- **Jazz Near You**: https://www.jazznearyou.com/nyc
- **Songkick**: https://www.songkick.com/metro-areas/7644-us-new-york-nyc/genre/jazz
- **TimeOut NYC**: https://www.timeout.com/newyork/events-calendar
- **DoNYC**: https://donyc.com/valentines-day

## 🆘 Troubleshooting

**No events found?**
- Check site structure hasn't changed
- Enable debug logging
- Verify CSS selectors
- Test with headless=False

**Database errors?**
- Backup first: `cp data/events.db data/events.db.backup`
- Migration runs automatically
- Check schema version: `SELECT * FROM schema_version;`

**Rate limiting?**
- Increase delay in crawler init
- Add random delays
- Respect robots.txt

## 📞 Next Steps

1. **Run example script** to test crawlers
2. **Check database** for data quality
3. **Review SQL queries** for analytics
4. **Integrate into main.py** one crawler at a time
5. **Monitor for errors** and adjust selectors

---

**Version**: 0.2.0  
**Updated**: 2026-02-10  
**Total Code**: 1500+ lines  
**Documentation**: 10,000+ words  
**Status**: ✅ Ready for testing
