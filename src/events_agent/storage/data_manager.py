"""Data storage and management."""

import json
from datetime import datetime
from pathlib import Path
from typing import List
from events_agent.models.event import Event


class DataManager:
    """
    Manages raw and processed event data storage.

    Directory structure:
    - data/raw/{source}_{timestamp}.json - Raw crawled events
    - data/processed/events_{timestamp}.json - Filtered and processed events
    """

    def __init__(self, base_dir: str = "data"):
        """
        Initialize data manager.

        Args:
            base_dir: Base directory for data storage
        """
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"

        # Create directories if they don't exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def save_raw_events(self, source: str, events: List[Event], timestamp: datetime = None) -> str:
        """
        Save raw events from a source.

        Args:
            source: Source name (e.g., 'luma', 'meetup')
            events: List of Event objects
            timestamp: Optional timestamp (defaults to now)

        Returns:
            Path to saved file
        """
        if timestamp is None:
            timestamp = datetime.now()

        filename = f"{source}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.raw_dir / filename

        # Convert events to dict format
        events_data = {
            "source": source,
            "timestamp": timestamp.isoformat(),
            "count": len(events),
            "events": [e.model_dump(mode='json') for e in events]
        }

        with open(filepath, 'w') as f:
            json.dump(events_data, f, indent=2, default=str)

        return str(filepath)

    def save_processed_events(self, events: List[Event], filters: dict, timestamp: datetime = None) -> str:
        """
        Save processed/filtered events.

        Args:
            events: List of Event objects
            filters: Dictionary describing applied filters
            timestamp: Optional timestamp (defaults to now)

        Returns:
            Path to saved file
        """
        if timestamp is None:
            timestamp = datetime.now()

        filename = f"events_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.processed_dir / filename

        # Create output structure
        output = {
            "timestamp": timestamp.isoformat(),
            "total_events": len(events),
            "filters": filters,
            "events": [e.model_dump(mode='json') for e in events]
        }

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2, default=str)

        return str(filepath)

    def get_latest_raw_file(self, source: str = None) -> Path | None:
        """
        Get the most recent raw data file.

        Args:
            source: Optional source filter

        Returns:
            Path to latest file or None
        """
        pattern = f"{source}_*.json" if source else "*.json"
        files = sorted(self.raw_dir.glob(pattern), reverse=True)
        return files[0] if files else None

    def load_raw_events(self, filepath: str) -> List[Event]:
        """
        Load events from a raw data file.

        Args:
            filepath: Path to raw data file

        Returns:
            List of Event objects
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        events = []
        for event_data in data.get('events', []):
            try:
                event = Event(**event_data)
                events.append(event)
            except Exception as e:
                print(f"Error loading event: {e}")
                continue

        return events
