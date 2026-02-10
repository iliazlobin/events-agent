"""Validation script for crawled event data."""

import json
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta


def validate_crawl(filepath: str):
    """
    Validate crawled event data from a processed JSON file.

    Checks:
    - Count events by source
    - Count events by experience_type
    - Field completeness (% of events with each field)
    - Detect duplicates (same title+date+location)
    - Validate date coverage (events across days)
    - Check URL validity (basic check)

    Args:
        filepath: Path to processed events JSON file
    """
    print("=" * 70)
    print("Event Data Validation Report")
    print("=" * 70)

    # Load data
    print(f"\nLoading data from: {filepath}")
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        sys.exit(1)

    events = data.get('events', [])
    total_events = len(events)
    filters = data.get('filters', {})

    print(f"Total events: {total_events}")
    print(f"Filters applied: {filters}")

    if total_events == 0:
        print("\nWARNING: No events to validate!")
        return

    print("\n" + "=" * 70)
    print("1. Events by Source")
    print("=" * 70)

    source_counts = Counter(event.get('source') for event in events)
    for source, count in sorted(source_counts.items()):
        pct = (count / total_events) * 100
        print(f"  {source:15s}: {count:4d} events ({pct:5.1f}%)")

    print("\n" + "=" * 70)
    print("2. Events by Experience Type")
    print("=" * 70)

    exp_type_counts = Counter(event.get('experience_type') or 'unknown' for event in events)
    for exp_type, count in sorted(exp_type_counts.items(), key=lambda x: -x[1]):
        pct = (count / total_events) * 100
        print(f"  {exp_type:20s}: {count:4d} events ({pct:5.1f}%)")

    print("\n" + "=" * 70)
    print("3. Field Completeness")
    print("=" * 70)

    # Key fields to check
    fields_to_check = [
        'event_id', 'source', 'url', 'title', 'start_datetime',  # Required
        'description', 'end_datetime',  # Core optional
        'location_name', 'city', 'state', 'latitude', 'longitude',  # Location
        'price_cents', 'is_free', 'currency',  # Pricing
        'experience_type', 'category', 'image_url',  # Content
        'chef_name', 'cuisine_type', 'performer_names',  # Specific
    ]

    field_coverage = {}
    for field in fields_to_check:
        populated = sum(1 for e in events if e.get(field) is not None and e.get(field) != "")
        coverage_pct = (populated / total_events) * 100
        field_coverage[field] = coverage_pct

    # Print by category
    print("\nRequired Fields:")
    for field in ['event_id', 'source', 'url', 'title', 'start_datetime']:
        pct = field_coverage.get(field, 0)
        status = "✓" if pct >= 99 else "✗"
        print(f"  {status} {field:20s}: {pct:5.1f}%")

    print("\nCore Optional Fields:")
    for field in ['description', 'end_datetime']:
        pct = field_coverage.get(field, 0)
        status = "✓" if pct >= 70 else "⚠"
        print(f"  {status} {field:20s}: {pct:5.1f}%")

    print("\nLocation Fields:")
    for field in ['location_name', 'city', 'state', 'latitude', 'longitude']:
        pct = field_coverage.get(field, 0)
        status = "✓" if pct >= 80 else "⚠"
        print(f"  {status} {field:20s}: {pct:5.1f}%")

    print("\nPricing Fields:")
    for field in ['price_cents', 'is_free', 'currency']:
        pct = field_coverage.get(field, 0)
        status = "✓" if pct >= 80 else "⚠"
        print(f"  {status} {field:20s}: {pct:5.1f}%")

    print("\nExperience Fields:")
    for field in ['experience_type', 'category', 'image_url']:
        pct = field_coverage.get(field, 0)
        status = "✓" if pct >= 60 else "⚠"
        print(f"  {status} {field:20s}: {pct:5.1f}%")

    print("\n" + "=" * 70)
    print("4. Duplicate Detection")
    print("=" * 70)

    # Detect duplicates by title + date + city
    seen = {}
    duplicates = []

    for event in events:
        title = event.get('title', '').lower().strip()
        start_date = event.get('start_datetime', '')[:10] if event.get('start_datetime') else ''
        city = event.get('city', '').lower().strip() if event.get('city') else ''

        key = (title, start_date, city)

        if key in seen:
            duplicates.append((seen[key], event))
        else:
            seen[key] = event

    duplicate_count = len(duplicates)
    duplicate_pct = (duplicate_count / total_events) * 100 if total_events > 0 else 0

    print(f"  Total duplicates found: {duplicate_count} ({duplicate_pct:.1f}%)")

    if duplicates:
        print(f"\n  Sample duplicates (showing first 3):")
        for i, (event1, event2) in enumerate(duplicates[:3], 1):
            print(f"\n  Duplicate {i}:")
            print(f"    Event 1: {event1.get('title')} ({event1.get('source')})")
            print(f"    Event 2: {event2.get('title')} ({event2.get('source')})")

    print("\n" + "=" * 70)
    print("5. Date Coverage")
    print("=" * 70)

    # Parse dates and check coverage
    dates_with_events = set()

    for event in events:
        start_dt = event.get('start_datetime')
        if start_dt:
            try:
                # Parse ISO datetime
                dt = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
                dates_with_events.add(dt.date())
            except:
                pass

    if dates_with_events:
        min_date = min(dates_with_events)
        max_date = max(dates_with_events)
        date_range_days = (max_date - min_date).days + 1

        print(f"  Date range: {min_date} to {max_date} ({date_range_days} days)")
        print(f"  Days with events: {len(dates_with_events)} / {date_range_days}")

        coverage_pct = (len(dates_with_events) / date_range_days) * 100 if date_range_days > 0 else 0
        status = "✓" if coverage_pct >= 60 else "⚠"
        print(f"  {status} Coverage: {coverage_pct:.1f}%")

        # Show distribution by day of week
        print("\n  Events by day of week:")
        day_counts = Counter()
        for date in dates_with_events:
            day_counts[date.strftime('%A')] += 1

        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            count = day_counts.get(day, 0)
            print(f"    {day:10s}: {count:3d} days")

    print("\n" + "=" * 70)
    print("6. URL Validity Check")
    print("=" * 70)

    valid_urls = sum(1 for e in events if e.get('url') and e['url'].startswith('http'))
    url_validity_pct = (valid_urls / total_events) * 100 if total_events > 0 else 0
    status = "✓" if url_validity_pct >= 99 else "✗"

    print(f"  {status} Valid URLs: {valid_urls} / {total_events} ({url_validity_pct:.1f}%)")

    # URL by source
    print("\n  URLs by source:")
    for source in source_counts.keys():
        source_events = [e for e in events if e.get('source') == source]
        source_valid = sum(1 for e in source_events if e.get('url') and e['url'].startswith('http'))
        total_source = len(source_events)
        pct = (source_valid / total_source) * 100 if total_source > 0 else 0
        print(f"    {source:15s}: {source_valid:4d} / {total_source:4d} ({pct:5.1f}%)")

    print("\n" + "=" * 70)
    print("7. Summary & Recommendations")
    print("=" * 70)

    # Calculate overall score
    scores = []

    # Required field coverage (weight: 40%)
    required_coverage = sum(field_coverage.get(f, 0) for f in ['event_id', 'source', 'url', 'title', 'start_datetime']) / 5
    scores.append(('Required fields', required_coverage, 40))

    # Location coverage (weight: 20%)
    location_coverage = (field_coverage.get('city', 0) + field_coverage.get('location_name', 0)) / 2
    scores.append(('Location data', location_coverage, 20))

    # Duplicate rate (weight: 15%)
    duplicate_score = max(0, 100 - duplicate_pct * 10)  # Penalize duplicates heavily
    scores.append(('Duplicate check', duplicate_score, 15))

    # Date coverage (weight: 15%)
    date_score = coverage_pct if dates_with_events else 0
    scores.append(('Date coverage', date_score, 15))

    # URL validity (weight: 10%)
    scores.append(('URL validity', url_validity_pct, 10))

    # Calculate weighted score
    total_score = sum(score * weight for _, score, weight in scores) / 100

    print(f"\n  Overall Data Quality Score: {total_score:.1f}/100")

    print("\n  Component Scores:")
    for name, score, weight in scores:
        status = "✓" if score >= 80 else "⚠" if score >= 60 else "✗"
        print(f"    {status} {name:20s}: {score:5.1f}/100 (weight: {weight}%)")

    # Recommendations
    print("\n  Recommendations:")
    if total_score >= 85:
        print("    ✓ Excellent data quality! Ready for production use.")
    elif total_score >= 70:
        print("    ⚠ Good data quality with some areas for improvement.")
    else:
        print("    ✗ Data quality needs improvement before production use.")

    if duplicate_pct > 5:
        print(f"    - High duplicate rate ({duplicate_pct:.1f}%) - consider deduplication")

    if field_coverage.get('city', 0) < 90:
        print(f"    - Low city coverage ({field_coverage.get('city', 0):.1f}%) - check location parsing")

    if url_validity_pct < 99:
        print(f"    - Some invalid URLs ({100 - url_validity_pct:.1f}%) - verify URL extraction")

    print("\n" + "=" * 70)
    print("Validation Complete!")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        # Find latest processed file
        processed_dir = Path("data/processed")
        if processed_dir.exists():
            files = list(processed_dir.glob("events_*.json"))
            if files:
                filepath = str(max(files, key=lambda p: p.stat().st_mtime))
                print(f"Using latest processed file: {filepath}\n")
            else:
                print("ERROR: No processed event files found in data/processed/")
                sys.exit(1)
        else:
            print("ERROR: data/processed/ directory not found")
            sys.exit(1)

    validate_crawl(filepath)
