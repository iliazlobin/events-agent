# Meetup Crawler - FIXED ✅

## Issue Resolved

**Problem**: Crawler was only extracting 10 events for Feb 1 when 113+ events were actually available.

**Root Cause**: Was relying only on Apollo state which contained 10 complete events. The other 103 events were rendered in DOM with full datetime but not in Apollo state.

**Solution**: Implemented DOM extraction using `<time datetime>` elements to capture ALL visible events.

## Results

### Feb 1, 2026 - NYC In-Person Events

```
✅ Extracted: 100 events (hit limit!)
📍 Location: New York, NY
⏰ Time range: 10:00 AM - 11:00 PM
📊 Data quality: 100% complete

Time distribution:
  10:00 AM - 11 events
  11:00 AM - 4 events
  12:00 PM - 9 events
  01:00 PM - 16 events
  02:00 PM - 10 events
  03:00 PM - 12 events
  04:00 PM - 11 events
  05:00 PM - 9 events
  06:00 PM - 9 events
  07:00 PM - 5 events
  08:00 PM - 2 events
  09:00 PM - 1 event
  11:00 PM - 1 event
```

### Data Files

- **Raw data**: `data/raw/meetup_feb1_20260201.json` (100 events)
- **Full extraction**: `data/raw/meetup_feb1_full.json` (113 events)

## Technical Implementation

### URL Format (Fixed)

```python
url = "https://www.meetup.com/find/" + urlencode({
    "location": "us--ny--new-york",  # Fixed format
    "source": "EVENTS",
    "eventType": "inPerson",
    "customStartDate": "2026-02-01T00:00:00-05:00",  # With timezone
    "customEndDate": "2026-02-01T23:59:59-05:00",    # With timezone
    "distance": "tenMiles"  # Fixed format
})
```

### Extraction Strategy (New)

**Before** (only Apollo state):
- Found: 10 events
- Source: `__APOLLO_STATE__` JSON
- Limitation: Only initial server-rendered events

**After** (DOM + Apollo):
- Found: 113 events (limited to 100)
- Source: `<time datetime>` elements in rendered DOM
- Improvement: Captures ALL visible events after scrolling

### Key Code Changes

**DOM Extraction** (`_extract_from_dom`):
```python
# Find all time elements with datetime attributes
timeElements = document.querySelectorAll('time[datetime]');

timeElements.forEach(timeEl => {
    const datetime = timeEl.getAttribute('datetime');

    // Find parent event link
    let link = parent.querySelector('a[href*="/events/"]');

    // Extract event ID, title, location from container
    ...
});
```

**Datetime Parsing** (fixed):
```python
# Clean datetime - remove timezone suffix [America/New_York]
clean_date_text = date_text.split('[')[0] if '[' in date_text else date_text
start_datetime = parse_iso_datetime(clean_date_text)
```

## Verification

### Test Command

```bash
python -m events_agent.main
```

### Expected Output

```
[2/2] Crawling Meetup.com...
  Fetching URL: https://www.meetup.com/find/?location=us--ny--new-york...
    Crawling Meetup (total limit: 100, daily limit: 50)...
    Scrolling to load events...
    ✓ Collected 100 Meetup events
```

### Data Quality Checks

```bash
# Count events
cat data/raw/meetup_feb1_*.json | python -m json.tool | grep '"event_id"' | wc -l
# Should output: 100

# Check completeness
cat data/raw/meetup_feb1_*.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
events = data['events']
print(f'Events: {len(events)}')
print(f'With titles: {sum(1 for e in events if e[\"title\"])}')
print(f'With datetimes: {sum(1 for e in events if e[\"start_datetime\"])}')
print(f'With URLs: {sum(1 for e in events if e[\"url\"])}')
"
```

Expected output:
```
Events: 100
With titles: 100
With datetimes: 100
With URLs: 100
```

## Performance

- **Scrolls**: ~30 times
- **Time**: ~90 seconds
- **Events found**: 113 total (100 with limit)
- **Success rate**: 100% data completeness

## Comparison

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Events extracted | 10 | 100 | **10x** |
| Data sources | Apollo only | DOM + Apollo | Hybrid |
| Time coverage | 5 hours | 13 hours | Full day |
| Hit limit | No | Yes ✅ | Target met |

## Next Steps

1. ✅ **DONE**: Extract 100 events for single day
2. **Next**: Extend to 2-week range
3. **Future**: Implement daily crawl scheduler

---

**Status**: ✅ **FIXED AND WORKING**
**Date**: February 1, 2026
**Events Crawled**: 100/100 (limit reached)
