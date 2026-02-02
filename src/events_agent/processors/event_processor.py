"""Event processing pipeline - transforms raw events to processed events."""

from typing import List, Dict, Any
from datetime import datetime
from events_agent.models.event import Event
from events_agent.filters.date_filter import DateFilter
from events_agent.filters.location_filter import LocationFilter


class EventProcessor:
    """
    Centralized event processing pipeline.

    Takes raw events and applies filters, sorting, and limits to produce
    a final processed dataset.
    """

    def __init__(self, max_events: int = 100):
        """
        Initialize event processor.

        Args:
            max_events: Maximum number of events to return (default: 100)
        """
        self.max_events = max_events
        self.processing_stats = {}

    def process(
        self,
        raw_events: List[Event],
        location_filter: str = "NYC",
        date_filter: str = "current_and_next_week"
    ) -> Dict[str, Any]:
        """
        Process raw events through the full pipeline.

        Args:
            raw_events: List of raw Event objects from crawlers
            location_filter: Location to filter for (default: "NYC")
            date_filter: Date range to filter (default: "current_and_next_week")

        Returns:
            Dictionary containing:
                - events: List of processed Event objects
                - stats: Processing statistics
                - filters: Applied filter configuration
        """
        stats = {
            "raw_count": len(raw_events),
            "after_location": 0,
            "after_date": 0,
            "after_limit": 0,
            "filtered_out": {}
        }

        # Step 1: Location filtering
        if location_filter == "NYC":
            location_events = LocationFilter.filter_nyc_events(raw_events)
        else:
            # For future: support other cities
            location_events = LocationFilter.filter_by_city(raw_events, location_filter)

        stats["after_location"] = len(location_events)
        stats["filtered_out"]["location"] = stats["raw_count"] - stats["after_location"]

        # Step 2: Date filtering
        if date_filter == "current_and_next_week":
            date_events = DateFilter.filter_current_and_next_week(location_events)
        else:
            # For future: support custom date ranges
            date_events = location_events

        stats["after_date"] = len(date_events)
        stats["filtered_out"]["date"] = stats["after_location"] - stats["after_date"]

        # Step 3: Sort by date
        sorted_events = sorted(date_events, key=lambda e: e.start_datetime)

        # Step 4: Apply limit
        limited_events = sorted_events[:self.max_events]

        stats["after_limit"] = len(limited_events)
        stats["filtered_out"]["limit"] = stats["after_date"] - stats["after_limit"]

        # Build result
        result = {
            "events": limited_events,
            "stats": stats,
            "filters": {
                "location": location_filter,
                "date_range": date_filter,
                "max_events": self.max_events
            }
        }

        self.processing_stats = stats
        return result

    def process_from_sources(
        self,
        sources_events: Dict[str, List[Event]],
        location_filter: str = "NYC",
        date_filter: str = "current_and_next_week"
    ) -> Dict[str, Any]:
        """
        Process events from multiple sources.

        Args:
            sources_events: Dict mapping source name to list of events
                          e.g., {"luma": [...], "meetup": [...]}
            location_filter: Location to filter for
            date_filter: Date range to filter

        Returns:
            Dictionary with processed events and per-source stats
        """
        # Combine all sources
        all_events = []
        source_counts = {}

        for source, events in sources_events.items():
            source_counts[source] = len(events)
            all_events.extend(events)

        # Process combined events
        result = self.process(all_events, location_filter, date_filter)

        # Add source breakdown to stats
        result["stats"]["sources"] = source_counts

        # Calculate final source distribution
        final_sources = {}
        for event in result["events"]:
            source = event.source.value
            final_sources[source] = final_sources.get(source, 0) + 1

        result["stats"]["final_sources"] = final_sources

        return result

    def get_stats_summary(self) -> str:
        """
        Get human-readable processing statistics.

        Returns:
            Formatted string with processing stats
        """
        if not self.processing_stats:
            return "No processing has been performed yet."

        stats = self.processing_stats
        lines = [
            "Processing Statistics:",
            f"  Raw events:        {stats['raw_count']}",
            f"  After location:    {stats['after_location']} (-{stats['filtered_out']['location']})",
            f"  After date:        {stats['after_date']} (-{stats['filtered_out']['date']})",
            f"  After limit:       {stats['after_limit']} (-{stats['filtered_out']['limit']})",
            f"  Final output:      {stats['after_limit']} events"
        ]

        return "\n".join(lines)

    def validate_processed_events(self, events: List[Event]) -> Dict[str, Any]:
        """
        Validate that processed events meet all criteria.

        Args:
            events: List of processed events to validate

        Returns:
            Dictionary with validation results
        """
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Check event count
        if len(events) > self.max_events:
            validation["valid"] = False
            validation["errors"].append(
                f"Too many events: {len(events)} > {self.max_events}"
            )

        # Check NYC location
        for i, event in enumerate(events):
            if not LocationFilter.is_nyc_event(event):
                validation["valid"] = False
                validation["errors"].append(
                    f"Event {i} '{event.title}' is not in NYC: {event.city}, {event.state}"
                )

        # Check date range
        current_start, current_end = DateFilter.get_current_week_range()
        next_start, next_end = DateFilter.get_next_week_range()

        for i, event in enumerate(events):
            event_datetime = event.start_datetime.replace(tzinfo=None) if event.start_datetime.tzinfo else event.start_datetime

            in_current_week = current_start <= event_datetime <= current_end
            in_next_week = next_start <= event_datetime <= next_end

            if not (in_current_week or in_next_week):
                validation["warnings"].append(
                    f"Event {i} '{event.title}' is outside current/next week: {event.start_datetime}"
                )

        # Check for duplicates
        event_ids = [e.event_id for e in events]
        if len(event_ids) != len(set(event_ids)):
            validation["warnings"].append("Duplicate event IDs found")

        return validation


class ProcessingPipeline:
    """
    High-level processing pipeline orchestrator.

    Combines crawler results, applies processing, and manages data storage.
    """

    def __init__(self, processor: EventProcessor = None):
        """
        Initialize pipeline.

        Args:
            processor: EventProcessor instance (creates default if None)
        """
        self.processor = processor or EventProcessor()

    def run(
        self,
        raw_events_by_source: Dict[str, List[Event]],
        save_raw: bool = True,
        save_processed: bool = True,
        data_manager = None
    ) -> Dict[str, Any]:
        """
        Run full processing pipeline.

        Args:
            raw_events_by_source: Dict of source -> events
            save_raw: Whether to save raw data
            save_processed: Whether to save processed data
            data_manager: DataManager instance for saving

        Returns:
            Processing result with events and stats
        """
        timestamp = datetime.now()

        # Save raw data
        if save_raw and data_manager:
            for source, events in raw_events_by_source.items():
                if events:
                    filepath = data_manager.save_raw_events(source, events, timestamp)
                    print(f"  ✓ Saved raw {source} data: {filepath}")

        # Process events
        result = self.processor.process_from_sources(raw_events_by_source)

        # Validate
        validation = self.processor.validate_processed_events(result["events"])
        result["validation"] = validation

        # Save processed data
        if save_processed and data_manager:
            filepath = data_manager.save_processed_events(
                result["events"],
                result["filters"],
                timestamp
            )
            print(f"  ✓ Saved processed data: {filepath}")
            result["processed_file"] = filepath

        # Print stats
        print("\n" + self.processor.get_stats_summary())

        if not validation["valid"]:
            print("\n⚠️  Validation errors:")
            for error in validation["errors"]:
                print(f"  - {error}")

        if validation["warnings"]:
            print("\n⚠️  Validation warnings:")
            for warning in validation["warnings"]:
                print(f"  - {warning}")

        return result
