# Changes Summary - 2026-02-19

## Overview

Refocused the events-agent project on **tech/startup/professional networking events** (Gary's Guide style), removing music/concert and niche sources.

## ✅ Completed Work

### 1. Fixed Gary's Guide Crawler (Priority #1)
**Problem**: gary.to shortlinks were blocked by Puppeteer (`ERR_BLOCKED_BY_CLIENT`)

**Solution**: Extract all event data directly from listing page instead of following redirects
- Modified `/apify/garysguide-crawler/src/routes.ts`
- Removed event-detail handler (not needed)
- Single-page extraction: title, date, location, description, image
- Updated README with new approach

**Status**: ✅ Ready to test and deploy
- Build completes successfully
- Test input file created (`inputs/test-10.json`)
- Documentation updated

**Next Steps**:
```bash
cd /Users/iliazlobin/Code/events-agent/apify/garysguide-crawler
npm install  # if needed
apify run --input-file=inputs/test-10.json --purge
apify push   # when tests pass
```

### 2. Cleaned Up Event Sources
**Removed from `EventSource` enum**:
- ❌ SONGKICK (music/concerts)
- ❌ RESIDENTADVISOR (electronic music)
- ❌ BANDSINTOWN (concerts)
- ❌ JAZZNEARYOU (jazz events)
- ❌ COZYMEAL (cooking classes - too niche)

**Added to `EventSource` enum**:
- ✅ GARYSGUIDE
- ✅ FUNCHEAP
- ✅ SFTRAVEL

**Python Crawlers Archived** (documented but not removed):
- `jazznearyou_crawler.py` - Music/jazz only
- `cozymeal_crawler.py` - Cooking classes only

See `/REMOVED_SOURCES.md` for full details

### 3. Updated Documentation

**New Files**:
- `/REMOVED_SOURCES.md` - Explains what was removed and why
- `/apify/IMPLEMENTATION_GUIDE.md` - Step-by-step crawler implementation guide
- `/CHANGES_SUMMARY.md` - This file

**Updated Files**:
- `/apify/TODO.md` - Updated status, added implementation notes
- `/apify/garysguide-crawler/README.md` - Documented new approach
- `/src/events_agent/models/event.py` - Updated EventSource enum
- `/CLAUDE.md` (AGENTS.md) - Clarified exclusions

### 4. Prioritized TODO

**Phase 1 - Core Tech/Community** (High Priority):
- [x] Luma (deployed)
- [x] Meetup (deployed)
- [x] Gary's Guide (ready to deploy) ⭐ **SUPER IMPORTANT**
- [ ] DoNYC (implementation guide provided)
- [ ] Funcheap SF (implementation guide provided)
- [ ] SF Travel (implementation guide provided)

**Phase 2 - General Aggregators** (Medium Priority):
- [ ] Eventbrite (has Python reference)
- [ ] Fever (has Python reference)

## 📝 Sources Requested by User

All requested sources are now in the TODO:

✅ **sf.funcheap.com/events/** - TODO item #5, Priority 1
✅ **sftravel.com/things-to-do/events** - TODO item #6, Priority 1
✅ **donyc.com** - TODO item #4, Priority 1 (Python crawler exists as reference)
✅ **garysguide.com** - TODO item #3, **FIXED AND READY**
❓ **Kyosuke's Newsletter** - Marked as not crawlable (Substack newsletter format)

## 🎯 Focus

**What We're Building**: Tech/startup/professional event aggregator
**Target Events**: Meetups, workshops, talks, networking, tech conferences
**Excluded**: Music/concerts, niche activities (cooking classes, etc.)

## 🚀 Next Steps

### Immediate (Deploy Gary's Guide)
```bash
cd apify/garysguide-crawler
apify run --input-file=inputs/test-10.json --purge  # Test locally
apify push  # Deploy to Apify cloud
```

### Next Crawlers to Implement

Use the template in `/apify/IMPLEMENTATION_GUIDE.md`:

1. **DoNYC** (NYC events, community-focused)
   - Copy `garysguide-crawler/` structure
   - Reference Python `DoNYCCrawler` class in `timeout_crawler.py:215`
   - Update selectors for donyc.com

2. **Funcheap SF** (SF free/cheap events)
   - Copy `garysguide-crawler/` structure
   - Inspect sf.funcheap.com/events/ for selectors
   - Adapt extraction logic

3. **SF Travel** (SF official tourism)
   - Copy `garysguide-crawler/` structure
   - Inspect sftravel.com/things-to-do/events for selectors

### Future Enhancements

- Port Eventbrite crawler to Apify (high volume, 1000+ events/month)
- Port Fever crawler to Apify (curated experiences)
- Add scheduling for daily/weekly automated runs
- Set up data export to Python SQLite integration

## 📊 Current Crawler Status

| Source | Type | Status | Volume | Platform |
|--------|------|--------|--------|----------|
| Luma | Tech/Community | ✅ Deployed | 100+/mo | Apify |
| Meetup | Professional | ✅ Deployed | 500+/mo | Apify |
| Gary's Guide | Tech/Startup ⭐ | ✅ Ready | 500+/mo | Apify |
| DoNYC | NYC Community | 📝 Planned | 300+/mo | - |
| Funcheap SF | SF Community | 📝 Planned | 200+/mo | - |
| SF Travel | SF Tourism | 📝 Planned | 150+/mo | - |
| Eventbrite | General | 📝 Planned | 1000+/mo | Python (port to Apify) |
| Fever | Curated | 📝 Planned | 150+/mo | Python (port to Apify) |
| TimeOut | City Events | ⏸️ Low Priority | 200+/mo | Python (adequate) |

## 🔗 Key Files

- **Main TODO**: `/apify/TODO.md`
- **Implementation Guide**: `/apify/IMPLEMENTATION_GUIDE.md`
- **Project Instructions**: `/CLAUDE.md`
- **Removed Sources**: `/REMOVED_SOURCES.md`
- **Gary's Guide Crawler**: `/apify/garysguide-crawler/`
- **Event Model**: `/src/events_agent/models/event.py`

## 💡 Implementation Pattern

All new crawlers should follow the Gary's Guide pattern:
1. Copy `garysguide-crawler/` directory
2. Update `package.json`, `.actor/actor.json`, `README.md`
3. Modify `src/main.ts` start URL
4. Adapt `src/routes.ts` selectors for target site
5. Test with `apify run --input-file=inputs/test-10.json --purge`
6. Deploy with `apify push`

See `/apify/IMPLEMENTATION_GUIDE.md` for detailed steps.
