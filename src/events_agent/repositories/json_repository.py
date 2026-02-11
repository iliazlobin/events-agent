"""JSON export repository for debugging and backwards compatibility."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from events_agent.models.event import Event

logger = logging.getLogger(__name__)


class JSONEventRepository:
    """JSON file-based event repository for debugging and exports.

    Maintains backwards compatibility with existing JSON format.
    Used only for debug exports, not as primary storage.

    Example:
        >>> json_repo = JSONEventRepository("data/debug")
        >>> json_repo.export_events(events, "luma", timestamp)
    """

    def __init__(self, base_dir: str = "data/debug"):
        """Initialize JSON repository.

        Args:
            base_dir: Base directory for JSON exports.
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def export_events(
        self,
        events: List[Event],
        source: str,
        timestamp: datetime = None,
    ) -> str:
        """Export events to JSON file.

        Args:
            events: List of events to export.
            source: Source name (luma, meetup, etc.).
            timestamp: Optional timestamp for filename.

        Returns:
            Path to exported JSON file.
        """
        if timestamp is None:
            timestamp = datetime.now()

        filename = f"{source}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.base_dir / filename

        # Convert events to dictionaries
        events_data = [event.model_dump(mode="json") for event in events]

        # Create export structure
        export_data = {
            "source": source,
            "timestamp": timestamp.isoformat(),
            "count": len(events),
            "events": events_data,
        }

        # Write to file
        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Exported {len(events)} events to {filepath}")
        return str(filepath)

    def export_processed(
        self,
        events: List[Event],
        filters: dict,
        timestamp: datetime = None,
    ) -> str:
        """Export processed/filtered events to JSON.

        Args:
            events: List of processed events.
            filters: Dictionary describing applied filters.
            timestamp: Optional timestamp for filename.

        Returns:
            Path to exported JSON file.
        """
        if timestamp is None:
            timestamp = datetime.now()

        filename = f"processed_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.base_dir / filename

        # Convert events to dictionaries
        events_data = [event.model_dump(mode="json") for event in events]

        # Create export structure
        export_data = {
            "timestamp": timestamp.isoformat(),
            "total_events": len(events),
            "filters": filters,
            "events": events_data,
        }

        # Write to file
        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Exported {len(events)} processed events to {filepath}")
        return str(filepath)

    def load_events(self, filepath: str) -> List[Event]:
        """Load events from JSON file.

        Args:
            filepath: Path to JSON file.

        Returns:
            List of Event objects.
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        # Parse events
        events = [Event(**event_data) for event_data in data["events"]]

        logger.info(f"Loaded {len(events)} events from {filepath}")
        return events
