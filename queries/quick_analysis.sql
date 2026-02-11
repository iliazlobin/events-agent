-- Quick Analysis Queries for events.db
-- Run these in VSCode with SQLite extension

-- =============================================================================
-- OVERVIEW
-- =============================================================================

-- Database summary
SELECT
    'Total Events' as metric,
    COUNT(*) as value
FROM events
UNION ALL
SELECT
    'Date Range',
    MIN(DATE(start_datetime)) || ' to ' || MAX(DATE(start_datetime))
FROM events
UNION ALL
SELECT
    'Sources',
    COUNT(DISTINCT source)
FROM events
UNION ALL
SELECT
    'Cities',
    COUNT(DISTINCT city)
FROM events
WHERE city IS NOT NULL;

-- =============================================================================
-- BY SOURCE
-- =============================================================================

-- Events by source with stats
SELECT
    source,
    COUNT(*) as total_events,
    COUNT(CASE WHEN is_free = 1 THEN 1 END) as free_events,
    COUNT(CASE WHEN is_online = 1 THEN 1 END) as online_events,
    MIN(DATE(start_datetime)) as earliest_date,
    MAX(DATE(start_datetime)) as latest_date
FROM events
GROUP BY source
ORDER BY total_events DESC;

-- =============================================================================
-- NYC CURRENT/NEXT WEEK
-- =============================================================================

-- NYC events for current and next week (update dates as needed)
SELECT
    title,
    source,
    city,
    DATE(start_datetime) as date,
    TIME(start_datetime) as time,
    CASE WHEN is_free = 1 THEN 'Free' ELSE '$' || (price_cents / 100.0) END as price,
    url
FROM events
WHERE city LIKE '%New York%'
  AND state = 'NY'
  AND is_online = 0
  AND start_datetime >= date('now', 'weekday 1')  -- Next Monday
  AND start_datetime < date('now', 'weekday 1', '+14 days')  -- +2 weeks
ORDER BY start_datetime;

-- =============================================================================
-- DAILY BREAKDOWN
-- =============================================================================

-- Events per day with source breakdown
SELECT
    DATE(start_datetime) as date,
    strftime('%w', start_datetime) as day_num,
    CASE CAST(strftime('%w', start_datetime) AS INTEGER)
        WHEN 0 THEN 'Sun'
        WHEN 1 THEN 'Mon'
        WHEN 2 THEN 'Tue'
        WHEN 3 THEN 'Wed'
        WHEN 4 THEN 'Thu'
        WHEN 5 THEN 'Fri'
        WHEN 6 THEN 'Sat'
    END as day,
    COUNT(*) as total,
    COUNT(CASE WHEN source = 'luma' THEN 1 END) as luma,
    COUNT(CASE WHEN source = 'meetup' THEN 1 END) as meetup,
    COUNT(CASE WHEN source = 'fever' THEN 1 END) as fever,
    COUNT(CASE WHEN source = 'cozymeal' THEN 1 END) as cozymeal,
    COUNT(CASE WHEN source = 'eventbrite' THEN 1 END) as eventbrite
FROM events
GROUP BY DATE(start_datetime)
ORDER BY date;

-- =============================================================================
-- TOP CITIES
-- =============================================================================

-- Top cities by event count
SELECT
    city,
    state,
    COUNT(*) as event_count,
    COUNT(CASE WHEN is_free = 1 THEN 1 END) as free_count,
    GROUP_CONCAT(DISTINCT source) as sources
FROM events
WHERE city IS NOT NULL
GROUP BY city, state
ORDER BY event_count DESC
LIMIT 15;

-- =============================================================================
-- DUPLICATES CHECK
-- =============================================================================

-- Check for any duplicate events (should be 0 due to UNIQUE constraint)
SELECT
    event_id,
    source,
    COUNT(*) as count
FROM events
GROUP BY event_id, source
HAVING COUNT(*) > 1;

-- =============================================================================
-- RECENT CRAWLS
-- =============================================================================

-- Most recently crawled events
SELECT
    title,
    source,
    city,
    start_datetime,
    crawled_at,
    ROUND((julianday('now') - julianday(crawled_at)) * 24, 1) as hours_ago
FROM events
ORDER BY crawled_at DESC
LIMIT 20;

-- =============================================================================
-- SEARCH EXAMPLES
-- =============================================================================

-- Search by keyword (change 'tech' to your search term)
SELECT
    title,
    source,
    city,
    DATE(start_datetime) as date,
    url
FROM events
WHERE title LIKE '%tech%'
   OR description LIKE '%tech%'
ORDER BY start_datetime
LIMIT 20;

-- =============================================================================
-- PRICE ANALYSIS
-- =============================================================================

-- Price distribution
SELECT
    CASE
        WHEN is_free = 1 THEN 'Free'
        WHEN price_cents < 1000 THEN '$0-10'
        WHEN price_cents < 2500 THEN '$10-25'
        WHEN price_cents < 5000 THEN '$25-50'
        WHEN price_cents < 10000 THEN '$50-100'
        ELSE '$100+'
    END as price_range,
    COUNT(*) as count
FROM events
GROUP BY price_range
ORDER BY
    CASE price_range
        WHEN 'Free' THEN 0
        WHEN '$0-10' THEN 1
        WHEN '$10-25' THEN 2
        WHEN '$25-50' THEN 3
        WHEN '$50-100' THEN 4
        WHEN '$100+' THEN 5
    END;

-- =============================================================================
-- VALENTINE'S DAY IDEAS
-- =============================================================================

-- NYC events this Friday & Saturday (Valentine's Day weekend) that could be good for dates
-- Looks for date-friendly activities: dining, art, music, comedy, etc.
SELECT
    title,
    source,
    location_name,
    location_address,
    DATE(start_datetime) as date,
    CASE CAST(strftime('%w', start_datetime) AS INTEGER)
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END as day,
    TIME(start_datetime) as time,
    CASE
        WHEN is_free = 1 THEN 'Free'
        ELSE '$' || ROUND(price_cents / 100.0, 2)
    END as price,
    attendee_count,
    url
FROM events
WHERE city LIKE '%New York%'
  AND state = 'NY'
  AND is_online = 0
  -- This Friday and Saturday only (Valentine's weekend)
  AND DATE(start_datetime) >= date('now', 'weekday 5')  -- This Friday
  AND DATE(start_datetime) <= date('now', 'weekday 6')  -- This Saturday
  AND (
    -- Date-friendly keywords in title or description
    title LIKE '%dinner%' OR description LIKE '%dinner%'
    OR title LIKE '%wine%' OR description LIKE '%wine%'
    OR title LIKE '%cocktail%' OR description LIKE '%cocktail%'
    OR title LIKE '%music%' OR description LIKE '%music%'
    OR title LIKE '%jazz%' OR description LIKE '%jazz%'
    OR title LIKE '%comedy%' OR description LIKE '%comedy%'
    OR title LIKE '%art%' OR description LIKE '%art%'
    OR title LIKE '%gallery%' OR description LIKE '%gallery%'
    OR title LIKE '%cooking%' OR description LIKE '%cooking%'
    OR title LIKE '%dance%' OR description LIKE '%dance%'
    OR title LIKE '%romantic%' OR description LIKE '%romantic%'
    OR title LIKE '%date%' OR description LIKE '%date night%'
    OR title LIKE '%couples%' OR description LIKE '%couples%'
  )
ORDER BY start_datetime, price_cents;
