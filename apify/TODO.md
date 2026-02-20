# Apify Event Crawlers - Implementation Roadmap

**Focus**: Tech/startup/professional community events (Gary's Guide style)
**Excluded**: Music/concert-only sites (Songkick, Bandsintown, Resident Advisor, Jazz Near You), cooking classes (Cozymeal)

## Status Legend
- ✅ Deployed & Tested
- 🚧 In Progress
- 📝 Planned
- ⏸️ On Hold
- ❌ Blocked

## Current Status

### ✅ Completed
1. **Luma** (`luma-crawler/`)
   - Source: lu.ma
   - Volume: 100+ events/month (NYC)
   - Status: Deployed to Apify cloud
   - Notes: Next.js JSON data extraction, tech/community focus

2. **Meetup** (`meetup-crawler/`)
   - Source: meetup.com
   - Volume: 500+ events/month (NYC)
   - Status: Deployed to Apify cloud
   - Notes: GraphQL API integration, professional/community events

---

## 📝 Priority 1: Gary's Guide-Style Aggregators (FOCUS)

3. **Gary's Guide** (`garysguide-crawler/`) ⭐ **SUPER IMPORTANT**
   - Source: garysguide.com
   - Volume: 500+ events/month (NYC/SF)
   - Python crawler: NO
   - Target URLs:
     - NYC: https://www.garysguide.com/events?region=nyc
     - SF: https://www.garysguide.com/events?region=sf
   - Test maxItems: 5-10
   - Notes: THE premier tech/startup event aggregator, highly curated
   - Status: ✅ **AGGREGATOR MODE IMPLEMENTED** - Ready for testing
   - **NEW Pattern**: Acts as metadata aggregator, NOT direct scraper
     * Collects: Title, date, location, image from Gary's Guide pages
     * Resolves: gary.to redirects to detect provider (Luma, Meetup, etc.)
     * **Does NOT** visit/scrape individual Luma/Meetup event pages
     * Stores: `source=garysguide`, `original_provider=luma/meetup/etc.`
     * Benefits: No duplicate scraping, cost reduction, discovery mechanism
   - Database: Migration 3 adds aggregator fields (original_provider, aggregated_from, short_url)
   - TypeScript: ✅ Compiles successfully
   - Docs: See `design/AGGREGATOR_PATTERN.md` and `design/AGGREGATOR_IMPLEMENTATION_SUMMARY.md`
   - Next Steps:
     1. Test locally: `apify run --input-file=inputs/test-aggregator.json`
     2. Verify provider detection in output
     3. Deploy: `apify push`
     4. Test on Apify with 10-20 events
     5. Import to SQLite and verify aggregator fields populated

4. **DoNYC** (`donyc-crawler/`)
   - Source: donyc.com
   - Volume: 300+ events/month (NYC)
   - Python crawler: EXISTS (see `/src/events_agent/crawlers/timeout_crawler.py:215`)
   - Target URL: https://donyc.com/
   - Test maxItems: 10
   - Notes: NYC local events, community-focused
   - Status: 📝 Planned
   - Implementation: Copy `garysguide-crawler/`, reference Python `DoNYCCrawler` class for scraping logic

5. **Funcheap SF** (`funcheap-crawler/`)
   - Source: sf.funcheap.com
   - Volume: 200+ events/month (SF)
   - Python crawler: NO
   - Target URL: https://sf.funcheap.com/events/
   - Test maxItems: 10
   - Notes: Free/cheap SF events, community activities
   - Status: 📝 Planned
   - Implementation: Copy `garysguide-crawler/` structure, update:
     * `package.json`: name, description
     * `.actor/actor.json`: name, title, description
     * `src/main.ts`: update start URL to sf.funcheap.com/events/
     * `src/routes.ts`: adapt selectors for Funcheap's HTML structure
     * `README.md`: update documentation

6. **SF Travel** (`sftravel-crawler/`)
   - Source: sftravel.com
   - Volume: 150+ events/month (SF)
   - Python crawler: NO
   - Target URL: https://www.sftravel.com/things-to-do/events
   - Test maxItems: 10
   - Notes: Official SF tourism board, major events
   - Status: 📝 Planned
   - Implementation: Copy `garysguide-crawler/` structure, similar modifications as Funcheap

7. **Kyosuke's Newsletter**
   - Source: https://kyosuketogami.substack.com/
   - Volume: 90+ tech events per bi-weekly issue (SF Bay Area)
   - Python crawler: NO
   - Target URL: N/A - Substack newsletter format
   - Notes: Curated newsletter, not suitable for crawling. Focus on sources they aggregate FROM
   - Status: ❌ Not crawlable - Newsletter format only
   - Alternative: Already covered via Gary's Guide, Luma, Meetup, Eventbrite

---

## 📝 Priority 2: General Aggregators (Multi-category)

8. **Eventbrite** (`eventbrite-crawler/`)
   - Source: eventbrite.com
   - Volume: 1000+ events/month (NYC/SF)
   - Python crawler: EXISTS
   - Target URLs:
     - NYC: https://www.eventbrite.com/d/ny--new-york/all-events/
     - SF: https://www.eventbrite.com/d/ca--san-francisco/all-events/
   - Test maxItems: 10
   - Notes: Largest general aggregator, includes tech/professional
   - Status: 📝 Planned

9. **Fever** (`fever-crawler/`)
   - Source: feverup.com
   - Volume: 150+ events/month (NYC/SF)
   - Python crawler: EXISTS
   - Target URLs:
     - NYC: https://feverup.com/new-york
     - SF: https://feverup.com/san-francisco
   - Test maxItems: 10
   - Notes: Curated experiences, workshops, talks
   - Status: 📝 Planned

---

## ⏸️ On Hold / Lower Priority

10. **TimeOut NYC** (`timeout-crawler/`)
    - Source: timeout.com/newyork
    - Volume: 200+ events/month
    - Python crawler: EXISTS
    - Status: ⏸️ Python adequate for now

11. **Jazz Near You** (`jazznearyou-crawler/`)
    - Source: jazznearyou.com
    - Python crawler: EXISTS
    - Status: ⏸️ Too niche

12. **Cozymeal** (`cozymeal-crawler/`)
    - Source: cozymeal.com
    - Python crawler: EXISTS
    - Status: ⏸️ Small volume

---

## ❌ Removed (Not Target Audience)

- ~~Resident Advisor~~ - Electronic music/nightlife only
- ~~Bandsintown~~ - Concert tracking only
- ~~Dice~~ - Music/concert ticketing only
- ~~Songkick~~ - Music events only

---

## Implementation Plan

### Phase 1: Core Tech/Community Aggregators
- [x] Luma (DEPLOYED)
- [x] Meetup (DEPLOYED)
- [x] **Gary's Guide** (NYC + SF) ⭐ **READY TO TEST & DEPLOY**
- [ ] DoNYC (copy structure from Gary's Guide)
- [ ] Funcheap SF (copy structure from Gary's Guide) - **skeleton created**
- [ ] SF Travel (copy structure from Gary's Guide)

### Phase 2: General Aggregators with Tech Focus
- [ ] Eventbrite (NYC + SF)
- [ ] Fever (NYC + SF)

### Phase 3: Research & Expand
- [ ] Research Kyosuke's Newsletter source
- [ ] Evaluate additional tech-focused sources
- [ ] Consider: NYC Tech Meetup, TechCrunch events, Startup Grind

### Phase 4: Multi-Region Support
- [ ] Add SF support to existing crawlers
- [ ] Standardize region parameter across all crawlers
- [ ] Test cross-region deduplication

---

## Testing Protocol

For each new crawler:
1. **Local Development**
   - Create from `ts-crawlee-puppeteer-chrome` template
   - Implement with `maxItems: 10` for testing
   - Test with `apify run --input-file=inputs/test-10.json --purge`
   - Verify: 10 events collected, all required fields present

2. **Validation**
   - Check event quality (valid dates, URLs, titles)
   - Verify no duplicates in dataset
   - Confirm rate limiting (3 requests/min)
   - Review error logs

3. **Integration**
   - Add source to `EventSource` enum (if not exists)
   - Test import to SQLite
   - Verify auto-deduplication works

4. **Deployment**
   - Push to Apify: `apify push`
   - Run cloud test with maxItems: 50
   - Monitor compute unit usage

---

## Notes

- **Test Setting**: All crawlers should default to `maxItems: 10` for development
- **Production**: Increase to 100-200 after validation
- **Rate Limiting**: Keep at 3 requests/min to avoid blocking
- **Timeout**: Use 300s for scroll-heavy pages
- **Anti-blocking**: Always use `useFingerprints: true`
