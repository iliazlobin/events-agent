"""Event validation utilities."""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from events_agent.models.event import Event


class EventValidator:
    """
    Validates event collections for completeness and quality.
    """

    @staticmethod
    def validate_date_coverage(
        events: List[Event],
        target_days: int = 14,
        min_coverage_pct: float = 0.8
    ) -> Dict[str, Any]:
        """
        Validate that events cover the target date range.

        Args:
            events: List of Event objects
            target_days: Expected number of days to cover (default: 14)
            min_coverage_pct: Minimum coverage percentage required (default: 80%)

        Returns:
            Dictionary with validation results
        """
        if not events:
            return {
                "valid": False,
                "coverage_pct": 0,
                "days_covered": 0,
                "target_days": target_days,
                "gaps": [],
                "message": "No events to validate"
            }

        # Get date range from events
        start_dates = [e.start_datetime for e in events]
        min_date = min(start_dates)
        max_date = max(start_dates)

        # Calculate coverage
        date_range_days = (max_date - min_date).days + 1
        coverage_pct = (date_range_days / target_days) * 100

        # Find gaps (days with no events)
        current_date = min_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = current_date + timedelta(days=target_days)

        days_with_events = set()
        for event in events:
            event_date = event.start_datetime.replace(tzinfo=None) if event.start_datetime.tzinfo else event.start_datetime
            event_day = event_date.replace(hour=0, minute=0, second=0, microsecond=0)
            days_with_events.add(event_day)

        # Find gap days
        gaps = []
        check_date = current_date
        while check_date < end_date:
            if check_date not in days_with_events:
                gaps.append(check_date.strftime("%Y-%m-%d"))
            check_date += timedelta(days=1)

        days_covered = len(days_with_events)
        coverage_pct = (days_covered / target_days) * 100
        is_valid = coverage_pct >= (min_coverage_pct * 100)

        return {
            "valid": is_valid,
            "coverage_pct": round(coverage_pct, 1),
            "days_covered": days_covered,
            "target_days": target_days,
            "gaps": gaps,
            "date_range": {
                "start": min_date.strftime("%Y-%m-%d"),
                "end": max_date.strftime("%Y-%m-%d")
            },
            "message": f"Coverage: {days_covered}/{target_days} days ({coverage_pct:.1f}%)"
        }

    @staticmethod
    def validate_event_distribution(
        events: List[Event],
        min_events_per_day: int = 2
    ) -> Dict[str, Any]:
        """
        Validate that events are well-distributed across days.

        Args:
            events: List of Event objects
            min_events_per_day: Minimum events expected per day

        Returns:
            Dictionary with distribution analysis
        """
        if not events:
            return {
                "valid": False,
                "days_analyzed": 0,
                "avg_events_per_day": 0,
                "distribution": {}
            }

        # Group events by day
        events_by_day = {}
        for event in events:
            event_date = event.start_datetime.replace(tzinfo=None) if event.start_datetime.tzinfo else event.start_datetime
            day = event_date.strftime("%Y-%m-%d")
            events_by_day[day] = events_by_day.get(day, 0) + 1

        # Calculate statistics
        days_analyzed = len(events_by_day)
        total_events = sum(events_by_day.values())
        avg_events_per_day = total_events / days_analyzed if days_analyzed > 0 else 0

        # Find days below minimum
        low_days = {day: count for day, count in events_by_day.items() if count < min_events_per_day}

        return {
            "valid": len(low_days) == 0,
            "days_analyzed": days_analyzed,
            "avg_events_per_day": round(avg_events_per_day, 1),
            "distribution": events_by_day,
            "low_days": low_days,
            "message": f"Average {avg_events_per_day:.1f} events/day across {days_analyzed} days"
        }

    @staticmethod
    def validate_event_quality(events: List[Event]) -> Dict[str, Any]:
        """
        Validate event data quality.

        Checks:
        - Missing titles
        - Missing dates
        - Missing locations (for in-person events)
        - Duplicate event IDs

        Args:
            events: List of Event objects

        Returns:
            Dictionary with quality metrics
        """
        issues = []
        duplicate_ids = []

        # Check for duplicates
        event_ids = [e.event_id for e in events]
        seen_ids = set()
        for event_id in event_ids:
            if event_id in seen_ids:
                duplicate_ids.append(event_id)
            seen_ids.add(event_id)

        if duplicate_ids:
            issues.append(f"{len(duplicate_ids)} duplicate event IDs found")

        # Check required fields
        missing_title = sum(1 for e in events if not e.title)
        if missing_title > 0:
            issues.append(f"{missing_title} events missing title")

        # Check location for in-person events
        in_person_events = [e for e in events if not e.is_online]
        missing_location = sum(1 for e in in_person_events if not e.city and not e.location_address)
        if missing_location > 0:
            issues.append(f"{missing_location} in-person events missing location")

        return {
            "valid": len(issues) == 0,
            "total_events": len(events),
            "issues": issues,
            "duplicate_ids": list(set(duplicate_ids)),
            "online_pct": round((sum(1 for e in events if e.is_online) / len(events)) * 100, 1) if events else 0
        }

    @staticmethod
    def print_validation_report(events: List[Event], target_days: int = 14):
        """
        Print comprehensive validation report.

        Args:
            events: List of Event objects
            target_days: Target days to cover
        """
        print("\n" + "=" * 60)
        print("EVENT VALIDATION REPORT")
        print("=" * 60)

        # Date coverage
        coverage = EventValidator.validate_date_coverage(events, target_days)
        print(f"\n📅 Date Coverage:")
        print(f"  {coverage['message']}")
        print(f"  Date range: {coverage['date_range']['start']} to {coverage['date_range']['end']}")
        if coverage['gaps']:
            print(f"  ⚠️  Gaps on: {', '.join(coverage['gaps'][:5])}")
            if len(coverage['gaps']) > 5:
                print(f"            ... and {len(coverage['gaps']) - 5} more days")
        else:
            print(f"  ✓ No gaps detected")

        # Distribution
        distribution = EventValidator.validate_event_distribution(events)
        print(f"\n📊 Event Distribution:")
        print(f"  {distribution['message']}")
        if distribution['low_days']:
            print(f"  ⚠️  Days with few events: {len(distribution['low_days'])}")

        # Quality
        quality = EventValidator.validate_event_quality(events)
        print(f"\n✨ Data Quality:")
        print(f"  Total events: {quality['total_events']}")
        print(f"  Online events: {quality['online_pct']}%")
        if quality['issues']:
            print(f"  ⚠️  Issues found:")
            for issue in quality['issues']:
                print(f"      - {issue}")
        else:
            print(f"  ✓ No quality issues")

        print("\n" + "=" * 60)
