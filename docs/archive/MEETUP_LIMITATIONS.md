# Meetup Crawler - Implementation & Limitations

## Current Status ✅

**Meetup Events Extracted**: ~10 events per crawl (from 300+ event IDs found)

**Coverage**: 42.9% (6/14 days) - Limited but functional

**Strategy**: Filter-based URL without custom dates + post-extraction date filtering

## Current Working Solution ✅

**URL Strategy**: Use filter-based URL WITHOUT custom date parameters
```
https://www.meetup.com/find/?location=New+York%2C+NY&source=EVENTS&eventType=inPerson&distance=10
```

**Why this works**:
- Meetup's `customStartDate`/`customEndDate` parameters return 0 events (API returns empty results)
- Using default parameters loads Meetup's upcoming events
- Post-extraction filtering by date range works reliably

**Implementation**:
```python
# Build URL without custom dates
url = f"https://www.meetup.com/find/?location={location}&source=EVENTS&eventType={event_type}&distance={miles}"

# Filter after extraction
events = [e for e in all_events if start_date <= e.start_datetime <= end_date]
```

**Results**:
- ✓ 318 event IDs extracted from DOM via scrolling
- ✓ 19 events in Apollo state (full data)
- ✓ ~10 events successfully parsed within date range
- ✓ Daily limit (50) and total limit (100) enforced
- ✓ Data saved to `data/raw/meetup_*.json`

## The Technical Challenge

Meetup.com uses a hybrid rendering approach:

1. **Initial Load**: ~13 events embedded in `__APOLLO_STATE__` (server-side rendered)
   - These have FULL event data (title, date, location, etc.)

2. **Infinite Scroll**: Additional events loaded via GraphQL API
   - Event IDs appear in DOM (we can extract 60+ IDs after scrolling)
   - But **data is NOT in Apollo state** - it's rendered directly to DOM
   - DOM only contains partial data (title + date mixed in text, no structured datetime)

### What We Tried

✅ **Extracting from Apollo State** - Works, but only gets initial 13 events
✅ **Detecting Event IDs from DOM** - Works, finds 60+ event IDs after scrolling
❌ **Getting Full Data for DOM Events** - Fails, data not in Apollo state
❌ **Parsing Datetime from DOM Text** - Too unreliable (e.g., "Sun, Feb 8 · 5:00 PM")

## Why This Matters

Your requirement: **"Crawl 100 events for the next 2 weeks"**

Current reality: **~9-13 events** with full data

### Validation Results

```
📅 Date Coverage: 42.9% (6/14 days)
📊 Events: 9 Meetup events
⚠️  Gaps: 9 days with no events
```

**This is insufficient for full 2-week coverage.**

## Remaining Limitation

**Low Success Rate**: Only ~10 events successfully parsed out of 318 event IDs found

**Root Cause**:
- Apollo state has only 19 events with full data
- Remaining 299 events require DOM text parsing
- Date parsing from text (e.g., "Sun, Feb 1 · 5:00 PM EST") is unreliable
- Many events lack proper datetime attributes in DOM

**Impact**: Can collect ~10 Meetup events per crawl instead of target 100

## Future Improvement Options

### Option 1: Use Meetup Official API (Best Solution)

**Pros**:
- Full event data
- Reliable and maintained
- Can get 100+ events easily
- Proper pagination

**Cons**:
- Requires Meetup Pro account ($15-30/month)
- Need API approval process
- Requires authentication

**Implementation**:
```python
# Would use Meetup GraphQL API
query = {
    "operationName": "getEvents",
    "variables": {
        "lat": 40.7128,
        "lon": -74.0060,
        "first": 100,
        "endDateRange": "2026-02-14"
    }
}
```

### Option 2: Intercept GraphQL Requests (Advanced)

**Pros**:
- No API fees
- Gets real-time data

**Cons**:
- Complex implementation
- Fragile (breaks if Meetup changes API)
- May violate terms of service

**Implementation**: Would need to capture network responses during scrolling

### Option 3: Focus on Luma + Other Sources

**Pros**:
- Luma crawler works perfectly (29 events)
- Can add other sources (Eventbrite, Partiful, etc.)
- Diversify event sources

**Cons**:
- No Meetup events
- Need to implement new crawlers

### Option 4: Accept Current Limitation

**Pros**:
- Works now
- No additional costs
- Some Meetup coverage

**Cons**:
- Limited Meetup events (9-13)
- May not cover full 2 weeks

## Current Workaround

To maximize Meetup event coverage with current approach:

1. **Multiple Location Searches**: Run crawler for different NYC areas
   ```python
   meetup_crawler.crawl(browser, "Manhattan, NY")
   meetup_crawler.crawl(browser, "Brooklyn, NY")
   meetup_crawler.crawl(browser, "Queens, NY")
   ```

2. **Run Multiple Times**: Meetup's "popular events" rotate
   - Run crawler at different times
   - Combine results

3. **Use Luma as Primary Source**:
   - Luma: 29 events (excellent coverage)
   - Meetup: 9 events (supplementary)
   - **Total: 38 events**

## Recommendations

### Short Term (Now)
- ✅ Use current crawler (gets 9-13 Meetup events)
- ✅ Rely primarily on Luma (29 events, good coverage)
- ✅ Add more sources (Eventbrite, etc.)

### Medium Term (1-2 weeks)
- 🔄 Implement Eventbrite crawler
- 🔄 Implement Partiful crawler
- 🔄 Try multiple NYC location queries for Meetup

### Long Term (1 month+)
- 🎯 Apply for Meetup API access
- 🎯 Implement proper GraphQL API integration
- 🎯 Build comprehensive multi-source aggregator

## Current Performance (Feb 1, 2026)

```
Source     Events  Coverage     Quality        Data Saved
─────────  ──────  ───────────  ─────────────  ─────────────────────
Luma       29      ✓ Excellent  ✓ Excellent    data/raw/luma_*.json
Meetup     10      ⚠️ Limited    ✓ Good         data/raw/meetup_*.json
─────────  ──────  ───────────  ─────────────  ─────────────────────
TOTAL      39      6/14 days    Good           33 after filtering
           (42.9%)
```

**To reach 100 events with full 2-week coverage**: Need 2-3 additional sources OR Meetup API

## Next Steps

**Immediate**:
1. Document this limitation in CLAUDE.md
2. Add event source priority (Luma > others > Meetup)
3. Implement basic Eventbrite crawler

**Question for User**:
- Are you willing to pay for Meetup Pro + API access?
- Should we prioritize other free sources (Eventbrite, Partiful)?
- Is 38 events (from Luma + limited Meetup) acceptable for MVP?

---

**Last Updated**: 2026-01-31
**Status**: Meetup limited to ~9-13 events, Luma working excellently
