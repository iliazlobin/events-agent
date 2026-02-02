"""Meetup.com event crawler with filter-based approach."""

from typing import List, Optional
from datetime import datetime
from playwright.sync_api import Page

from events_agent.crawlers.base import BaseCrawler
from events_agent.models.event import Event

from .constants import (
    DEFAULT_MAX_EVENTS_TOTAL,
    DEFAULT_MAX_EVENTS_PER_DAY,
    DEFAULT_DISTANCE_MILES,
    EVENT_TYPE_IN_PERSON
)
from .url_builder import MeetupURLBuilder
from .page_scroller import PageScroller
from .dom_extractor import DOMExtractor
from .apollo_parser import ApolloParser
from .event_transformer import EventTransformer


class MeetupCrawler(BaseCrawler):
    """
    Crawler for Meetup.com events using URL filters.

    Strategy:
    - Build URL with filters (date, location, distance, event type)
    - Scroll page to load all events
    - Extract events from rendered DOM and Apollo state
    - Respect daily and total event limits
    """

    def __init__(
        self,
        rate_limit_seconds: float = 2.0,
        max_events_total: int = DEFAULT_MAX_EVENTS_TOTAL,
        max_events_per_day: int = DEFAULT_MAX_EVENTS_PER_DAY,
        distance_miles: int = DEFAULT_DISTANCE_MILES,
        event_type: str = EVENT_TYPE_IN_PERSON
    ):
        """
        Initialize Meetup crawler with filters.

        Args:
            rate_limit_seconds: Delay between requests
            max_events_total: Maximum total events to crawl
            max_events_per_day: Maximum events per day
            distance_miles: Search radius in miles
            event_type: "inPerson", "online", or "all"
        """
        super().__init__(rate_limit_seconds)
        self.max_events_total = max_events_total
        self.max_events_per_day = max_events_per_day
        self.distance_miles = distance_miles
        self.event_type = event_type
        self.transformer = EventTransformer(event_type)

        # Date range storage
        self._start_date: Optional[datetime] = None
        self._end_date: Optional[datetime] = None

    def get_events_url(
        self,
        location: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        Build Meetup URL with filters using correct format.

        Args:
            location: Location string (e.g., "New York, NY")
            start_date: Start date filter with timezone
            end_date: End date filter with timezone

        Returns:
            Full Meetup URL with filters
        """
        url, start, end = MeetupURLBuilder.build_events_url(
            location=location,
            start_date=start_date,
            end_date=end_date,
            distance_miles=self.distance_miles,
            event_type=self.event_type
        )

        # Store date range for filtering
        self._start_date = start
        self._end_date = end

        return url

    def extract_events_from_page(self, page: Page) -> List[Event]:
        """
        Extract events from Meetup page with aggressive scrolling.

        Process:
        1. Scroll page to load all events (up to limits)
        2. Extract event data from DOM and Apollo state
        3. Parse and validate events
        4. Respect daily and total limits

        Args:
            page: Playwright Page object

        Returns:
            List of Event objects
        """
        all_events = []
        seen_event_ids = set()
        events_by_day = {}  # Track events per day for daily limit
        scroll_count = 0
        no_change_count = 0

        # Print status
        date_range_str = self._get_date_range_string()
        print(f"    Crawling Meetup (total limit: {self.max_events_total}, "
              f"daily limit: {self.max_events_per_day}){date_range_str}...")

        try:
            # Initial wait for content
            PageScroller.initial_wait(page)

            # Debug info
            self._print_debug_info(page)

            # Aggressive scrolling to load all events
            prev_event_count = 0

            while PageScroller.should_continue_scrolling(
                scroll_count, no_change_count, len(all_events), self.max_events_total
            ):
                # Extract events from current page state
                new_events = self._extract_and_filter_events(page, seen_event_ids, events_by_day)

                if new_events:
                    all_events.extend(new_events)
                    print(f"    Scroll {scroll_count + 1}: {len(all_events)} total events")
                    no_change_count = 0
                else:
                    no_change_count += 1

                # Check if we've reached total limit
                if len(all_events) >= self.max_events_total:
                    print(f"    ✓ Reached total limit of {self.max_events_total} events")
                    break

                # Scroll and track progress
                PageScroller.scroll_to_bottom(page)
                scroll_count += 1

                current_event_count = PageScroller.get_event_link_count(page)

                # Check if no new links appeared
                if current_event_count == prev_event_count:
                    no_change_count += 1
                    if no_change_count >= 3:
                        print(f"    No more events loading (scrolled {scroll_count} times)")
                        break
                else:
                    prev_event_count = current_event_count
                    no_change_count = 0

            # Final extraction to catch any remaining events
            final_events = self._extract_and_filter_events(page, seen_event_ids, events_by_day)
            all_events.extend(final_events)

            # Apply total limit
            limited_events = all_events[:self.max_events_total]

            print(f"    ✓ Collected {len(limited_events)} Meetup events")
            print(f"    Daily distribution: {dict(sorted(events_by_day.items())[:7])}")

            return limited_events

        except Exception as e:
            print(f"    Error extracting Meetup events: {e}")
            import traceback
            traceback.print_exc()
            return all_events[:self.max_events_total] if all_events else []

    def _extract_and_filter_events(
        self,
        page: Page,
        seen_event_ids: set,
        events_by_day: dict
    ) -> List[Event]:
        """
        Extract event data from DOM/Apollo and apply filters.

        Args:
            page: Playwright Page object
            seen_event_ids: Set of already seen event IDs
            events_by_day: Dict tracking events per day for daily limit

        Returns:
            List of newly found Event objects
        """
        new_events = []

        try:
            # Get Apollo state
            apollo_state = ApolloParser.extract_apollo_state(page)
            apollo_event_count = ApolloParser.get_event_count(apollo_state)

            if apollo_event_count > 0:
                print(f"      Apollo state has {apollo_event_count} events")

            # Extract events from DOM
            dom_events = DOMExtractor.extract_events(page)

            if dom_events:
                print(f"      Extracted {len(dom_events)} events from DOM")
                if len(dom_events) > 0:
                    sample = dom_events[0]
                    print(f"      Sample: {sample.get('event_id', 'N/A')} - "
                          f"{sample.get('title', 'N/A')[:50]}")

            # Process each DOM event
            for event_data in dom_events:
                event_id = str(event_data.get('event_id', ''))

                # Skip if already seen
                if event_id in seen_event_ids:
                    continue

                # Try Apollo state first, fall back to DOM data
                event = self._parse_event(event_id, event_data, apollo_state)

                if event and self._passes_filters(event, events_by_day):
                    new_events.append(event)
                    seen_event_ids.add(event_id)
                    event_date = event.start_datetime.date()
                    events_by_day[event_date] = events_by_day.get(event_date, 0) + 1

        except Exception as e:
            print(f"      Error extracting from DOM: {e}")

        return new_events

    def _parse_event(
        self,
        event_id: str,
        dom_data: dict,
        apollo_state: dict
    ) -> Optional[Event]:
        """
        Parse event using Apollo state or DOM data.

        Args:
            event_id: Event ID
            dom_data: Data extracted from DOM
            apollo_state: Apollo state dictionary

        Returns:
            Event object or None
        """
        # Try Apollo state first (more reliable)
        apollo_data = ApolloParser.get_event_data(apollo_state, event_id)
        if apollo_data:
            return self.transformer.from_apollo_data(apollo_data, apollo_state)

        # Fall back to DOM data
        return self.transformer.from_dom_data(dom_data)

    def _passes_filters(self, event: Event, events_by_day: dict) -> bool:
        """
        Check if event passes date range and daily limit filters.

        Args:
            event: Event to check
            events_by_day: Dict tracking events per day

        Returns:
            True if event passes filters
        """
        # Filter by date range (if specified)
        if self._start_date and self._end_date:
            event_dt = event.start_datetime.replace(tzinfo=None) if event.start_datetime.tzinfo else event.start_datetime
            start_dt = self._start_date.replace(tzinfo=None) if self._start_date.tzinfo else self._start_date
            end_dt = self._end_date.replace(tzinfo=None) if self._end_date.tzinfo else self._end_date

            if not (start_dt <= event_dt <= end_dt):
                return False

        # Check daily limit
        event_date = event.start_datetime.date()
        day_count = events_by_day.get(event_date, 0)

        if day_count >= self.max_events_per_day:
            return False

        return True

    def _get_date_range_string(self) -> str:
        """Get formatted date range string for logging."""
        if self._start_date and self._end_date:
            return f" (filtering {self._start_date.strftime('%Y-%m-%d')} " \
                   f"to {self._end_date.strftime('%Y-%m-%d')})"
        return ""

    def _print_debug_info(self, page: Page) -> None:
        """Print debug information about the page."""
        page_title = page.title()
        print(f"    Page title: {page_title}")

        initial_link_count = PageScroller.get_event_link_count(page)
        print(f"    Initial event links found: {initial_link_count}")
