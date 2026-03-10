# Apify Crawler Implementation Guide

Quick reference for implementing new event crawlers using the Gary's Guide template.

## ✅ Completed Crawlers

1. **Luma** - Deployed, collecting 100+ NYC events/month
2. **Meetup** - Deployed, collecting 500+ NYC events/month
3. **Gary's Guide** - Fixed redirect blocking, ready to deploy

## 🚀 Quick Start: New Crawler from Template

### Step 1: Copy Gary's Guide Structure

```bash
cd /Users/iliazlobin/Code/events-agent/apify
cp -r garysguide-crawler/ your-crawler-name/
cd your-crawler-name
```

### Step 2: Update Package Configuration

**`package.json`**:
```json
{
  "name": "your-crawler-name",
  "description": "Apify Actor to crawl [Source] events"
}
```

**`.actor/actor.json`**:
```json
{
  "actorSpecification": 1,
  "name": "your-crawler-name",
  "title": "Your Source Crawler",
  "description": "Crawls events from [source]",
  "version": "1.0.0"
}
```

**`.actor/input_schema.json`**:
- Update title and description
- Keep region/maxItems/lookForwardWindow parameters (standard)

### Step 3: Update Main Entry Point

**`src/main.ts`**:
```typescript
const startUrl = `https://your-source.com/events?param=${param}`
await crawler.run([startUrl])
```

### Step 4: Implement Scraping Logic

**`src/routes.ts`** - Two approaches:

#### Approach A: Single-Page Extraction (Like Gary's Guide)
Best for: Sites that show all event info on listing page

```typescript
router.addDefaultHandler(async ({ page, log }) => {
  const events = await page.evaluate(() => {
    const eventData: any[] = []

    // Find event containers
    const containers = document.querySelectorAll('.event-item')

    containers.forEach((el) => {
      eventData.push({
        url: el.querySelector('a')?.href || '',
        title: el.querySelector('.title')?.textContent?.trim() || '',
        dateStr: el.querySelector('.date')?.textContent?.trim() || '',
        location: el.querySelector('.location')?.textContent?.trim() || '',
        description: el.querySelector('.desc')?.textContent?.trim() || '',
      })
    })

    return eventData
  })

  // Save directly to dataset
  for (const event of events.slice(0, maxItems)) {
    await Dataset.pushData({
      ...event,
      source: 'your-source',
      scrapedAt: new Date().toISOString(),
    })
  }
})
```

#### Approach B: Two-Stage Extraction (Like Luma)
Best for: Sites that require clicking into event detail pages

```typescript
// Step 1: Extract event URLs from listing
router.addDefaultHandler(async ({ page, log, crawler }) => {
  const eventUrls = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('.event-link'))
      .map(el => el.getAttribute('href'))
      .filter(Boolean)
  })

  // Enqueue detail pages
  for (const url of eventUrls.slice(0, maxItems)) {
    await crawler.addRequests([{
      url,
      label: 'event-detail',
    }])
  }
})

// Step 2: Extract details from each event page
router.addHandler('event-detail', async ({ page, log, request }) => {
  const eventData = await page.evaluate(() => ({
    title: document.querySelector('h1')?.textContent?.trim(),
    dateStr: document.querySelector('.date')?.textContent?.trim(),
    location: document.querySelector('.venue')?.textContent?.trim(),
    description: document.querySelector('.description')?.textContent?.trim(),
  }))

  await Dataset.pushData({
    url: request.url,
    ...eventData,
    source: 'your-source',
    scrapedAt: new Date().toISOString(),
  })
})
```

### Step 5: Update Documentation

**`README.md`**:
- Update title, source URL, and description
- Update example output
- Add any source-specific notes

**`inputs/test-10.json`**:
```json
{
  "region": "sf",
  "maxItems": 10,
  "lookForwardWindow": 30
}
```

### Step 6: Test Locally

```bash
# Install dependencies (first time only)
npm install

# Build TypeScript
npm run build

# Test with 10 events
apify run --input-file=inputs/test-10.json --purge

# Check results
find storage/datasets/default -name "*.json" | wc -l
cat storage/datasets/default/*.json | jq -s '.[0:3]'
```

### Step 7: Deploy to Apify

```bash
# First deployment
apify push

# Subsequent updates
npm run build && apify push
```

## 📋 Next Crawlers to Implement

### 1. DoNYC (Priority: High)
- **URL**: https://donyc.com/
- **Reference**: Python crawler at `/src/events_agent/crawlers/timeout_crawler.py:215`
- **Approach**: Two-stage (listing + detail pages)
- **Volume**: 300+ events/month

### 2. Funcheap SF (Priority: High)
- **URL**: https://sf.funcheap.com/events/
- **Reference**: None (new source)
- **Approach**: Check site structure, likely two-stage
- **Volume**: 200+ events/month

### 3. SF Travel (Priority: Medium)
- **URL**: https://www.sftravel.com/things-to-do/events
- **Reference**: None (new source)
- **Approach**: Check site structure
- **Volume**: 150+ events/month

### 4. Eventbrite (Priority: Medium)
- **URL**: https://www.eventbrite.com/d/ca--san-francisco/all-events/
- **Reference**: Python crawler at `/src/events_agent/crawlers/eventbrite_crawler.py`
- **Approach**: Two-stage
- **Volume**: 1000+ events/month (large!)

### 5. Fever (Priority: Low)
- **URL**: https://feverup.com/san-francisco
- **Reference**: Python crawler at `/src/events_agent/crawlers/fever_crawler.py`
- **Approach**: Two-stage
- **Volume**: 150+ events/month

## 🛠️ Common Patterns

### Scrolling for More Events
```typescript
// Scroll to load infinite scroll content
for (let i = 0; i < maxScrolls; i++) {
  await page.evaluate(() => {
    window.scrollTo(0, document.body.scrollHeight)
  })
  await new Promise(resolve => setTimeout(resolve, 2000))
}
```

### Handling Dynamic Content
```typescript
// Wait for dynamic content to load
await page.waitForSelector('.event-item', { timeout: 10000 })
await new Promise(resolve => setTimeout(resolve, 2000))
```

### Extracting Dates
```typescript
const dateStr = element.querySelector('.date')?.textContent?.trim() || ''
// Let Python handle date parsing later
```

### Handling Errors Gracefully
```typescript
try {
  // Extraction logic
  eventData.push({...})
} catch (err) {
  log.error(`Error extracting event: ${err}`)
  // Skip this event, continue with others
}
```

## 📊 Standard Output Format

All crawlers should output events with these fields:

```typescript
{
  "url": string,              // Event URL (required)
  "title": string,            // Event title (required)
  "dateStr": string,          // Date/time as string (required)
  "location": string,         // Venue/location (optional)
  "description": string,      // Event description (optional)
  "imageUrl": string,         // Event image URL (optional)
  "source": string,           // Crawler source name (required)
  "scrapedAt": string,        // ISO timestamp (required)

  // Optional fields:
  "price": string,            // Price text
  "organizer": string,        // Organizer/host name
  "category": string,         // Event category
  "tags": string[]            // Event tags
}
```

## 🔧 Troubleshooting

### Build Errors
```bash
# Clean build
rm -rf dist/
npm run build
```

### Blocked Requests (Like Gary's Guide)
- Use single-page extraction instead of following links
- Extract all data from listing page HTML
- Avoid navigating to external domains

### No Events Found
- Check CSS selectors with browser DevTools
- Log page HTML: `log.info(await page.content())`
- Take screenshot: `await page.screenshot({ path: 'debug.png' })`

### Rate Limiting
- Increase delays: `await new Promise(resolve => setTimeout(resolve, 5000))`
- Reduce `maxRequestsPerMinute` in `main.ts`
- Use `maxRequestsPerCrawl` to limit total requests

## 📚 Resources

- **Crawlee Docs**: https://crawlee.dev/
- **Apify Docs**: https://docs.apify.com/
- **Project Instructions**: `/Users/iliazlobin/Code/events-agent/CLAUDE.md`
- **TODO Status**: `/Users/iliazlobin/Code/events-agent/src/apify/TODO.md`
