"""Date filtering for events."""

from datetime import datetime, timedelta
from typing import List
from events_agent.models.event import Event


class DateFilter:
    """
    Filter events by date range.

    Supports filtering for:
    - Current week (Monday to Sunday)
    - Next week
    - Custom date ranges
    """

    @staticmethod
    def get_current_week_range() -> tuple[datetime, datetime]:
        """
        Get date range for current week (Monday to Sunday).

        Returns:
            Tuple of (start_of_week, end_of_week) as timezone-naive datetimes
        """
        now = datetime.now()
        # Find Monday of current week
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

        # Find Sunday of current week
        end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)

        return start_of_week, end_of_week

    @staticmethod
    def get_next_week_range() -> tuple[datetime, datetime]:
        """
        Get date range for next week (Monday to Sunday).

        Returns:
            Tuple of (start_of_week, end_of_week)
        """
        current_start, _ = DateFilter.get_current_week_range()
        next_start = current_start + timedelta(days=7)
        next_end = next_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        return next_start, next_end

    @staticmethod
    def filter_current_and_next_week(events: List[Event]) -> List[Event]:
        """
        Filter events to only include current week and next week.

        Args:
            events: List of events to filter

        Returns:
            Filtered list of events
        """
        current_start, current_end = DateFilter.get_current_week_range()
        next_start, next_end = DateFilter.get_next_week_range()

        filtered = []
        for event in events:
            # Remove timezone info for comparison (convert to naive datetime)
            event_datetime = event.start_datetime.replace(tzinfo=None) if event.start_datetime.tzinfo else event.start_datetime

            # Check if event falls within current or next week
            if (current_start <= event_datetime <= current_end or
                next_start <= event_datetime <= next_end):
                filtered.append(event)

        return filtered

    @staticmethod
    def filter_by_range(events: List[Event], start: datetime, end: datetime) -> List[Event]:
        """
        Filter events by custom date range.

        Args:
            events: List of events to filter
            start: Start datetime (inclusive)
            end: End datetime (inclusive)

        Returns:
            Filtered list of events
        """
        return [e for e in events
                if start <= (e.start_datetime.replace(tzinfo=None) if e.start_datetime.tzinfo else e.start_datetime) <= end]
