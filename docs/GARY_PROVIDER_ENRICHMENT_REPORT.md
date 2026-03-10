# Gary/Provider Enrichment Report

Date: 2026-03-09

## Goal

Verify the end-to-end flow where Gary's Guide discovery rows are imported first, provider rows are imported later, and SQLite closes the loop via:

- `find_aggregated_events_missing_direct_source(...)`
- `promote_aggregator_metadata(...)`

## What Was Tested

### 1. Controlled integration flow

Test file:

- `tests/integration/test_gary_provider_enrichment_flow.py`

Scenario:

- one Gary's Guide Luma discovery row
- one Gary's Guide Eventbrite discovery row
- one matching direct Luma row using the same canonical provider URL

Expected behavior:

- the Luma discovery is no longer pending
- the Eventbrite discovery remains pending
- Gary metadata is promoted onto the direct Luma row
- source-specific provider data remains in `source_extensions`

Result:

- passed

### 2. Real cached local actor datasets

Datasets used:

- `src/apify/garysguide-crawler/storage/datasets/default`
- `src/apify/luma-crawler/storage/datasets/default`
- `src/apify/meetup-crawler/storage/datasets/default`

Imported counts:

- Gary's Guide: 5
- Luma: 47
- Meetup: 12

Observed overlap after URL normalization:

- Gary vs Luma: 0
- Gary vs Meetup: 0

Repository results:

- `pending_all = 5`
- `pending_luma = 2`
- `pending_meetup = 0`
- `pending_eventbrite = 2`
- `promoted = 0`

Pending rows:

- `gdconf.com | GDC Festival Of Gaming | https://gdconf.com/`
- `eventbrite | Ai, ML & DeepTech Mixer | https://www.eventbrite.com/e/ai-ml-deeptech-business-startups-networking-mixer-in-san-francisco-tickets-1981742813101`
- `luma | Py AI Conference | https://luma.com/i3cbt3sz`
- `eventbrite | Elevate Play | https://www.eventbrite.com/e/elevate-play-san-francisco-tickets-1980777173848`
- `luma | Systems Trivia Night | https://luma.com/convex-trivia-night-v1`

## Conclusion

The repository enrichment flow works.

The current local cached provider runs do not cover the specific Gary's Guide URLs in the cached discovery sample, so no promotions occur from those cached runs alone. This is a coverage/orchestration gap, not a repository-model bug.

## Data Model Assessment

The current direction is correct:

- shared identity, timing, location, pricing, organizer, and aggregator provenance live in the normalized `Event` model
- source-only spillover lives in `source_extensions`
- Gary's Guide does not need a separate event model; it uses the same core model plus aggregator provenance fields

## Improvements

1. Add a first-class importer from actor dataset JSON to `Event`.
2. Add targeted provider follow-up crawls based on Gary pending URLs instead of relying on broad provider discovery pages.
3. Extend URL normalization beyond `lu.ma`/`luma.com` if more provider aliases appear.
4. Add one fixture-backed test per provider pair:
   - Gary + Luma
   - Gary + Meetup
   - Gary + Eventbrite
5. Add a quality rule that flags Gary rows older than one run cycle that still have no matching direct-source row.
