-- Quick Analysis Queries for Jazz and Valentine's Day Events
-- Run these in sqlite3 or DB Browser

-- =============================================================================
-- JAZZ EVENTS QUERIES
-- =============================================================================

-- Count jazz events by source
SELECT 
    source,
    COUNT(*) as jazz_event_count,
    COUNT(DISTINCT location_name) as unique_venues
FROM events
WHERE genre = 'jazz' OR tags LIKE '%jazz%'
GROUP BY source
ORDER BY jazz_event_count DESC;

-- Jazz events this week at known venues
SELECT 
    title,
    start_datetime,
    location_name,
    performer_names,
    genre,
    url
FROM events
WHERE (genre = 'jazz' OR tags LIKE '%jazz%')
  AND location_name IN (
    'Village Vanguard', 'Blue Note', 'Smalls', 'Mezzrow',
    'Birdland', 'Iridium', 'Dizzy''s Club', 'Jazz Gallery',
    'Zinc Bar', 'The Django', 'Nublu'
  )
  AND start_datetime >= date('now')
  AND start_datetime < date('now', '+7 days')
ORDER BY start_datetime, location_name;

-- Jazz venues with most events
SELECT 
    location_name,
    COUNT(*) as event_count,
    MIN(start_datetime) as first_event,
    MAX(start_datetime) as last_event
FROM events
WHERE (genre = 'jazz' OR tags LIKE '%jazz%')
  AND location_name IS NOT NULL
  AND city = 'New York'
GROUP BY location_name
ORDER BY event_count DESC
LIMIT 20;

-- Jazz events by neighborhood (based on venue address)
SELECT 
    CASE 
        WHEN location_address LIKE '%Greenwich Village%' OR location_address LIKE '%W 3rd%' OR location_address LIKE '%W 10th%' THEN 'Greenwich Village'
        WHEN location_address LIKE '%Midtown%' OR location_address LIKE '%W 44th%' OR location_address LIKE '%Broadway%' THEN 'Midtown'
        WHEN location_address LIKE '%Harlem%' OR location_address LIKE '%W 118th%' OR location_address LIKE '%W 133rd%' THEN 'Harlem'
        WHEN location_address LIKE '%Brooklyn%' THEN 'Brooklyn'
        WHEN location_address LIKE '%East Village%' OR location_address LIKE '%Avenue C%' THEN 'East Village'
        ELSE 'Other/Unknown'
    END as neighborhood,
    COUNT(*) as event_count,
    GROUP_CONCAT(DISTINCT location_name) as venues
FROM events
WHERE (genre = 'jazz' OR tags LIKE '%jazz%')
  AND location_address IS NOT NULL
GROUP BY neighborhood
ORDER BY event_count DESC;

-- Free jazz events this month
SELECT 
    title,
    start_datetime,
    location_name,
    performer_names,
    url
FROM events
WHERE (genre = 'jazz' OR tags LIKE '%jazz%')
  AND is_free = 1
  AND start_datetime >= date('now', 'start of month')
  AND start_datetime < date('now', 'start of month', '+1 month')
  AND city = 'New York'
ORDER BY start_datetime;

-- Jazz events by price range
SELECT 
    CASE
        WHEN is_free = 1 THEN 'Free'
        WHEN price_cents IS NULL THEN 'Unknown'
        WHEN price_cents < 1000 THEN 'Under $10'
        WHEN price_cents < 2500 THEN '$10-25'
        WHEN price_cents < 5000 THEN '$25-50'
        ELSE 'Over $50'
    END as price_range,
    COUNT(*) as event_count,
    ROUND(AVG(CAST(price_cents AS FLOAT)) / 100, 2) as avg_price
FROM events
WHERE genre = 'jazz' OR tags LIKE '%jazz%'
GROUP BY price_range
ORDER BY 
    CASE price_range
        WHEN 'Free' THEN 1
        WHEN 'Under $10' THEN 2
        WHEN '$10-25' THEN 3
        WHEN '$25-50' THEN 4
        WHEN 'Over $50' THEN 5
        ELSE 6
    END;

-- =============================================================================
-- VALENTINE'S DAY EVENTS QUERIES
-- =============================================================================

-- Count Valentine's events by source
SELECT 
    source,
    COUNT(*) as vday_event_count,
    COUNT(DISTINCT experience_type) as unique_types
FROM events
WHERE tags LIKE '%valentine%' 
   OR title LIKE '%valentine%'
   OR description LIKE '%romantic%'
   OR tags LIKE '%couples%'
   OR tags LIKE '%date%night%'
GROUP BY source
ORDER BY vday_event_count DESC;

-- Valentine's Day events (Feb 7-16, 2026)
SELECT 
    title,
    start_datetime,
    experience_type,
    location_name,
    CASE
        WHEN is_free = 1 THEN 'Free'
        WHEN price_cents IS NULL THEN 'See link'
        ELSE '$' || CAST(price_cents / 100 AS TEXT)
    END as price,
    url
FROM events
WHERE (tags LIKE '%valentine%' OR title LIKE '%valentine%' OR description LIKE '%romantic%')
  AND start_datetime >= '2026-02-13'
  AND start_datetime <= '2026-02-16'
  AND city = 'New York'
ORDER BY start_datetime, price_cents;

-- Valentine's events by experience type
SELECT 
    experience_type,
    COUNT(*) as event_count,
    COUNT(DISTINCT location_name) as unique_venues,
    ROUND(AVG(CAST(price_cents AS FLOAT)) / 100, 2) as avg_price,
    MIN(start_datetime) as first_event,
    MAX(start_datetime) as last_event
FROM events
WHERE (tags LIKE '%valentine%' OR title LIKE '%valentine%')
  AND experience_type IS NOT NULL
  AND start_datetime >= '2026-02-07'
  AND start_datetime <= '2026-02-16'
GROUP BY experience_type
ORDER BY event_count DESC;

-- Romantic date-night events (not Valentine's specific)
SELECT 
    title,
    start_datetime,
    experience_type,
    location_name,
    rating,
    CASE
        WHEN is_free = 1 THEN 'Free'
        ELSE '$' || CAST(price_cents / 100 AS TEXT)
    END as price,
    url
FROM events
WHERE experience_type IN ('cooking class', 'wine tasting', 'concert', 'jazz', 'comedy', 'dinner', 'theater')
  AND (tags LIKE '%couples%' OR tags LIKE '%date%' OR tags LIKE '%romantic%')
  AND start_datetime >= date('now')
  AND start_datetime < date('now', '+14 days')
  AND city = 'New York'
ORDER BY COALESCE(rating, 0) DESC, start_datetime
LIMIT 30;

-- Valentine's events in romantic neighborhoods
SELECT 
    CASE 
        WHEN location_address LIKE '%Greenwich Village%' OR location_address LIKE '%West Village%' THEN 'Greenwich/West Village'
        WHEN location_address LIKE '%SoHo%' THEN 'SoHo'
        WHEN location_address LIKE '%Tribeca%' THEN 'Tribeca'
        WHEN location_address LIKE '%Chelsea%' THEN 'Chelsea'
        WHEN location_address LIKE '%DUMBO%' OR location_address LIKE '%Brooklyn Heights%' THEN 'DUMBO/Brooklyn Heights'
        WHEN location_address LIKE '%Williamsburg%' THEN 'Williamsburg'
        ELSE 'Other'
    END as neighborhood,
    COUNT(*) as event_count,
    ROUND(AVG(CAST(price_cents AS FLOAT)) / 100, 2) as avg_price
FROM events
WHERE (tags LIKE '%valentine%' OR title LIKE '%valentine%' OR description LIKE '%romantic%')
  AND start_datetime >= '2026-02-07'
  AND start_datetime <= '2026-02-16'
  AND location_address IS NOT NULL
GROUP BY neighborhood
ORDER BY event_count DESC;

-- =============================================================================
-- COMBINED QUERIES: ROMANTIC JAZZ EVENTS
-- =============================================================================

-- Jazz events perfect for Valentine's Day
SELECT 
    title,
    start_datetime,
    location_name,
    performer_names,
    CASE
        WHEN is_free = 1 THEN 'Free'
        WHEN price_cents IS NULL THEN 'See link'
        ELSE '$' || CAST(price_cents / 100 AS TEXT)
    END as price,
    rating,
    url
FROM events
WHERE (genre = 'jazz' OR tags LIKE '%jazz%')
  AND start_datetime >= '2026-02-07'
  AND start_datetime <= '2026-02-16'
  AND city = 'New York'
  AND is_online = 0
ORDER BY 
    CASE 
        WHEN location_name IN ('Village Vanguard', 'Blue Note', 'Birdland', 'Jazz Gallery') THEN 1
        ELSE 2
    END,
    start_datetime;

-- Date-night jazz events this month
SELECT 
    title,
    start_datetime,
    location_name,
    performer_names,
    genre,
    CASE
        WHEN is_free = 1 THEN 'Free'
        ELSE '$' || CAST(COALESCE(price_cents, 0) / 100 AS TEXT)
    END as price,
    url
FROM events
WHERE (genre = 'jazz' OR tags LIKE '%jazz%')
  AND (tags LIKE '%date%' OR tags LIKE '%romantic%' OR tags LIKE '%couples%'
       OR description LIKE '%intimate%' OR description LIKE '%romantic%')
  AND start_datetime >= date('now', 'start of month')
  AND start_datetime < date('now', 'start of month', '+1 month')
  AND city = 'New York'
ORDER BY start_datetime;

-- =============================================================================
-- DATA QUALITY CHECKS
-- =============================================================================

-- Check coverage of new event fields
SELECT 
    COUNT(*) as total_events,
    COUNT(genre) as has_genre,
    COUNT(category) as has_category,
    COUNT(experience_type) as has_experience_type,
    COUNT(performer_names) as has_performers,
    COUNT(tags) as has_tags,
    COUNT(rating) as has_rating,
    ROUND(100.0 * COUNT(genre) / COUNT(*), 1) as genre_pct,
    ROUND(100.0 * COUNT(tags) / COUNT(*), 1) as tags_pct
FROM events;

-- Events missing key categorization
SELECT 
    source,
    COUNT(*) as events_without_category,
    COUNT(DISTINCT title) as unique_titles
FROM events
WHERE category IS NULL AND genre IS NULL AND tags IS NULL
GROUP BY source
ORDER BY events_without_category DESC;

-- =============================================================================
-- ANALYTICS
-- =============================================================================

-- Most popular jazz performers (if data available)
SELECT 
    performer_names,
    COUNT(*) as event_count,
    COUNT(DISTINCT location_name) as venues,
    MIN(start_datetime) as first_show,
    MAX(start_datetime) as last_show
FROM events
WHERE performer_names IS NOT NULL
  AND (genre = 'jazz' OR tags LIKE '%jazz%')
GROUP BY performer_names
ORDER BY event_count DESC
LIMIT 20;

-- Event trends by date for Valentine's period
SELECT 
    DATE(start_datetime) as event_date,
    COUNT(*) as total_events,
    SUM(CASE WHEN tags LIKE '%valentine%' THEN 1 ELSE 0 END) as valentine_events,
    SUM(CASE WHEN genre = 'jazz' THEN 1 ELSE 0 END) as jazz_events,
    SUM(CASE WHEN is_free = 1 THEN 1 ELSE 0 END) as free_events
FROM events
WHERE start_datetime >= '2026-02-07'
  AND start_datetime <= '2026-02-16'
  AND city = 'New York'
GROUP BY event_date
ORDER BY event_date;

-- Top rated events (any category)
SELECT 
    title,
    category,
    experience_type,
    rating,
    review_count,
    location_name,
    start_datetime,
    url
FROM events
WHERE rating IS NOT NULL
  AND rating >= 4.0
  AND start_datetime >= date('now')
  AND start_datetime < date('now', '+30 days')
  AND city = 'New York'
ORDER BY rating DESC, review_count DESC
LIMIT 50;
