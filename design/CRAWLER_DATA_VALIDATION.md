# Apify Crawler Data Model Validation Report

**Generated**: 2026-02-22
**Python Event Model**: `src/events_agent/models/event.py`
**Apify Crawlers**: garysguide, luma, meetup

---

## Executive Summary

| Crawler | Status | Critical Issues | Warnings |
|---------|--------|----------------|----------|
| **Gary's Guide** | ⚠️ Incomplete | Missing required: event_id, start_datetime | Aggregator metadata fields present |
| **Luma** | ⚠️ Incomplete | Missing required: event_id, source | Field naming mismatches |
| **Meetup** | ⚠️ Incomplete | Missing required: event_id, source | Type mismatches (attendees) |

**Key Finding**: All three crawlers are missing critical required fields and have naming/type inconsistencies with the Python Event model.

---

## Required Fields Analysis

### Python Event Model - Required Fields
```python
event_id: str              # REQUIRED
source: EventSource        # REQUIRED (enum)
url: HttpUrl              # REQUIRED
title: str                # REQUIRED (min_length=1)
start_datetime: datetime  # REQUIRED (UTC)
```

### Crawler Compliance Matrix

| Field | Gary's Guide | Luma | Meetup | Notes |
|-------|--------------|------|--------|-------|
| `event_id` | ✅ | ❌ | ❌ | Gary's: extracted from URL path |
| `source` | ✅ | ❌ | ❌ | Gary's: hardcoded as 'garysguide' |
| `url` | ✅ | ✅ | ✅ | All present |
| `title` | ✅ | ✅ | ✅ | All present |
| `start_datetime` | ❌ | ✅ `dateStart` | ✅ `dateStart` | Gary's: string `dateStr`, not datetime |

---

## Field-by-Field Comparison

### 1. Gary's Guide Crawler (Aggregator Mode)

**Output Schema** (13 fields):
```typescript
{
  title: string,           // ✅ Maps to Event.title
  url: string,            // ✅ Maps to Event.url (final destination)
  shortUrl: string,       // ✅ Maps to Event.short_url
  aggregatorDetailUrl: string, // ✅ Maps to Event.aggregator_detail_url
  dateStr: string,        // ⚠️ Should be datetime, not string
  location: string,       // ⚠️ Maps to Event.location_name (needs parsing)
  description: string,    // ✅ Maps to Event.description
  imageUrl: string,       // ✅ Maps to Event.image_url
  source: 'garysguide',   // ✅ Maps to Event.source
  originalProvider: string, // ✅ Maps to Event.original_provider
  aggregatedFrom: 'garysguide', // ✅ Maps to Event.aggregated_from
  eventId: string,        // ✅ Maps to Event.event_id
  scrapedAt: string,      // ✅ Maps to Event.crawled_at
  isAggregated: true      // ❌ Not in Python model
}
```

**Issues**:
- ❌ `dateStr` is string, should be ISO datetime
- ❌ Missing `start_datetime` (required field)
- ⚠️ `location` needs parsing into city/state
- ℹ️ Aggregator-specific fields are present (good)

**Recommendation**: Parse `dateStr` into ISO datetime before saving


### 2. Luma Crawler

**Output Schema** (18 fields):
```typescript
{
  url: string,           // ✅ Maps to Event.url
  dateStart: string,     // ✅ Maps to Event.start_datetime (ISO format)
  dateEnd: string,       // ✅ Maps to Event.end_datetime (ISO format)
  title: string,         // ✅ Maps to Event.title
  hosts: string[],       // ⚠️ Should map to Event.host_name (first item)
  group: string,         // ⚠️ Maps to Event.organizer_name OR Event.group_name
  address: string,       // ⚠️ Maps to Event.location_address (needs parsing)
  guests: string[],      // ❌ Not in Python model
  attendees: number,     // ✅ Maps to Event.attendee_count
  description: string,   // ✅ Maps to Event.description
  cover: string,         // ✅ Maps to Event.image_url
  price: number,         // ⚠️ Maps to Event.price_cents (needs *100 conversion)
  maxPrice: number,      // ❌ Not in Python model
  minPrice: number,      // ❌ Not in Python model
  spotsLeft: number,     // ✅ Maps to Event.spots_remaining
  waitlist: boolean,     // ❌ Not in Python model
  registrationClosed: boolean // ❌ Not in Python model
}
```

**Issues**:
- ❌ Missing `event_id` (REQUIRED) - need to extract from URL
- ❌ Missing `source` (REQUIRED) - should be 'luma'
- ⚠️ `price` is in dollars, should be cents (multiply by 100)
- ⚠️ `address` needs parsing into city/state components
- ⚠️ `hosts` is array, model expects single `host_name`
- ⚠️ `group` ambiguous: could be organizer_name or group_name

**Recommendation**: Add event_id extraction and source field, convert price to cents


### 3. Meetup Crawler

**Output Schema** (20 fields):
```typescript
{
  url: string,           // ✅ Maps to Event.url
  dateStart: string,     // ✅ Maps to Event.start_datetime (ISO format)
  dateEnd: string,       // ✅ Maps to Event.end_datetime (ISO format)
  title: string,         // ✅ Maps to Event.title
  hosts: string[],       // ⚠️ Should map to Event.host_name (first item)
  group: string,         // ✅ Maps to Event.group_name (Meetup-specific)
  address: string,       // ⚠️ Maps to Event.location_address (needs parsing)
  guests: string[],      // ❌ Not in Python model (max 20)
  attendees: string,     // ⚠️ Type mismatch: string vs int
  description: string,   // ✅ Maps to Event.description
  cover: string,         // ✅ Maps to Event.image_url
  tags: string[],        // ✅ Maps to Event.tags
  venue: string,         // ✅ Maps to Event.location_name
  online: boolean,       // ✅ Maps to Event.is_online
  eventSeriesDates: string[], // ❌ Not in Python model
  price: number,         // ⚠️ Maps to Event.price_cents (needs *100 conversion)
  minPrice: number,      // ❌ Not in Python model
  maxPrice: number,      // ❌ Not in Python model
  spotsLeft: number,     // ✅ Maps to Event.spots_remaining
  waitlist: boolean,     // ❌ Not in Python model
  registrationClosed: boolean // ❌ Not in Python model
}
```

**Issues**:
- ❌ Missing `event_id` (REQUIRED) - need to extract from URL
- ❌ Missing `source` (REQUIRED) - should be 'meetup'
- ❌ `attendees` is string, should be int (type mismatch)
- ⚠️ `price` is in dollars, should be cents (multiply by 100)
- ⚠️ `address` needs parsing into city/state components
- ⚠️ `hosts` is array, model expects single `host_name`

**Recommendation**: Add event_id extraction and source field, convert attendees to int, price to cents

---

## Missing Fields in Python Model

These fields exist in crawlers but NOT in Python Event model:

| Field | Crawlers | Recommendation |
|-------|----------|----------------|
| `isAggregated` | Gary's Guide | ✅ KEEP - useful for aggregator pattern |
| `guests` | Luma, Meetup | ❌ DROP - use attendee_count instead |
| `maxPrice` / `minPrice` | Luma, Meetup | ⚠️ CONSIDER - useful for price ranges |
| `waitlist` | Luma, Meetup | ⚠️ CONSIDER - useful status indicator |
| `registrationClosed` | Luma, Meetup | ⚠️ CONSIDER - useful status indicator |
| `eventSeriesDates` | Meetup | ❌ DROP - out of scope |

---

## Type Mismatches

| Field | Crawler Type | Python Type | Fix Required |
|-------|--------------|-------------|--------------|
| `dateStr` (Gary's) | string | datetime | ✅ Parse to ISO datetime |
| `dateStart` (Luma) | string (ISO) | datetime | ✅ Already ISO, validate |
| `dateStart` (Meetup) | string (ISO) | datetime | ✅ Already ISO, validate |
| `price` (Luma/Meetup) | number (dollars) | int (cents) | ✅ Multiply by 100 |
| `attendees` (Meetup) | string | int | ✅ Convert to int |
| `cover` | string | string (image_url) | ✅ Just rename |

---

## Field Name Mapping

### Recommended Mapping Table

| Crawler Field | Python Event Field | Transformation |
|---------------|-------------------|----------------|
| `cover` | `image_url` | Direct rename |
| `hosts[0]` | `host_name` | Take first element |
| `dateStart` | `start_datetime` | Validate ISO format |
| `dateEnd` | `end_datetime` | Validate ISO format |
| `venue` | `location_name` | Direct mapping |
| `online` | `is_online` | Direct mapping |
| `address` | `location_address` | Direct mapping |
| `address` (parsed) | `city`, `state` | Parse "City, State" |

---

## Critical Fixes Required

### Priority 1 (Blocking)
1. **Luma & Meetup**: Add `event_id` extraction from URL
   ```typescript
   const eventId = url.split('/').pop() || 'unknown'
   ```

2. **Luma & Meetup**: Add `source` field
   ```typescript
   source: 'luma',  // or 'meetup'
   ```

3. **Gary's Guide**: Convert `dateStr` to ISO datetime
   ```typescript
   dateStart: new Date(dateStr).toISOString()
   ```

### Priority 2 (Data Quality)
1. **All**: Parse `address` into `city` and `state`
   ```typescript
   const [city, state] = address.split(', ')
   ```

2. **Luma & Meetup**: Convert price to cents
   ```typescript
   priceCents: Math.round(price * 100)
   ```

3. **Meetup**: Convert `attendees` to int
   ```typescript
   attendeeCount: parseInt(attendees)
   ```

### Priority 3 (Nice to Have)
1. Add `is_free` boolean based on price
2. Set `currency: "USD"` default
3. Populate `crawled_at` with current UTC time

---

## Recommendations

### Short Term (This Sprint)
1. ✅ Add missing required fields (`event_id`, `source`) to Luma & Meetup
2. ✅ Fix type mismatches (price to cents, attendees to int)
3. ✅ Parse Gary's Guide `dateStr` to ISO datetime
4. ✅ Rename `cover` → `image_url` consistently

### Medium Term (Next Sprint)
1. ⚠️ Consider adding `waitlist`, `registrationClosed` to Python model
2. ⚠️ Consider adding price range fields (`min_price_cents`, `max_price_cents`)
3. ✅ Implement address parsing for city/state extraction
4. ✅ Add data validation layer between Apify output → Python Event model

### Long Term (Backlog)
1. Create shared TypeScript schema that mirrors Python Event model
2. Add runtime validation using Zod or similar
3. Generate TypeScript types from Python Pydantic model
4. Implement automated integration tests validating crawler output

---

## Validation Checklist

Before importing Apify data to SQLite:

- [ ] All required fields present (event_id, source, url, title, start_datetime)
- [ ] Datetime fields in ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ)
- [ ] Price in cents (integer), not dollars
- [ ] Attendee count is integer, not string
- [ ] City and state parsed from address
- [ ] Image URL uses `image_url` field name
- [ ] Source matches EventSource enum values
- [ ] Event ID is unique within source
- [ ] URL is valid HttpUrl format

---

## Example Transform Code

### Luma Event Transform
```typescript
const lumaEvent = {
  // Required fields
  eventId: url.split('/').filter(Boolean).pop() || 'unknown',
  source: 'luma',
  url: url,
  title: title,
  startDatetime: dateStart, // Already ISO format

  // Optional fields
  endDatetime: dateEnd,
  locationName: venue,
  locationAddress: address,
  city: address.split(', ')[0],
  state: address.split(', ')[1],
  isOnline: false, // Luma doesn't track this yet

  attendeeCount: attendees,
  capacity: null,
  spotsRemaining: spotsLeft,

  priceCents: price ? Math.round(price * 100) : null,
  currency: 'USD',
  isFree: !price || price === 0,

  hostName: hosts[0] || null,
  organizerName: group,

  description: description,
  imageUrl: cover,

  crawledAt: new Date().toISOString(),
  detailCrawled: true
}
```

### Meetup Event Transform
```typescript
const meetupEvent = {
  // Required fields
  eventId: url.split('/').filter(Boolean).pop() || 'unknown',
  source: 'meetup',
  url: url,
  title: title,
  startDatetime: dateStart,

  // Optional fields
  endDatetime: dateEnd,
  locationName: venue,
  locationAddress: address,
  city: address.split(', ')[0],
  state: address.split(', ')[1],
  isOnline: online,

  attendeeCount: parseInt(attendees) || 0,
  spotsRemaining: spotsLeft,

  priceCents: price ? Math.round(price * 100) : null,
  currency: 'USD',
  isFree: !price || price === 0,

  hostName: hosts[0] || null,
  groupName: group,

  description: description,
  imageUrl: cover,
  tags: tags,

  crawledAt: new Date().toISOString(),
  detailCrawled: true
}
```

---

## Appendix: Python Event Model Reference

**Required Fields**:
- `event_id: str`
- `source: EventSource` (enum)
- `url: HttpUrl`
- `title: str` (min_length=1)
- `start_datetime: datetime` (UTC)

**Optional Core Fields** (45 total):
- Dates: `end_datetime`
- Location: `location_name`, `location_address`, `city`, `state`, `is_online`, `latitude`, `longitude`, `directions`
- Attendance: `attendee_count`, `capacity`, `spots_remaining`
- Pricing: `price_cents`, `currency`, `is_free`, `fee_amount`, `fee_required`, `payment_methods`
- Organizer: `organizer_name`, `organizer_url`, `host_name`, `host_bio`
- Group: `group_name`, `group_rating`, `group_review_count`
- Content: `description`, `ai_summary`, `image_url`, `topics`, `tags`
- Categorization: `experience_type`, `category`, `genre`
- Chef/Cooking: `chef_name`, `chef_rating`, `chef_bio`, `skill_level`, `cuisine_type`
- Performance: `performer_names`, `duration_minutes`
- Rating: `rating`, `review_count`
- Links: `registration_url`
- Aggregator: `original_provider`, `aggregated_from`, `short_url`, `aggregator_detail_url`
- Metadata: `crawled_at`, `detail_crawled`

**Full source**: `src/events_agent/models/event.py`
