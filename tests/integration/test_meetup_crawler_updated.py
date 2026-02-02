"""Integration tests for updated Meetup crawler with filter-based approach."""

import pytest
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from events_agent.crawlers.meetup_crawler import MeetupCrawler
from events_agent.models.event import EventSource


class TestMeetupCrawlerUpdated:
    """Test suite for updated Meetup crawler implementation."""

    def test_get_events_url_without_custom_dates(self):
        """Test URL building without custom date filters."""
        crawler = MeetupCrawler(
            max_events_total=100,
            max_events_per_day=50,
            distance_miles=10,
            event_type="inPerson"
        )

        url = crawler.get_events_url("New York, NY")

        # Should NOT contain customStartDate or customEndDate
        assert "customStartDate" not in url
        assert "customEndDate" not in url

        # Should contain other filters
        assert "location=New+York" in url
        assert "eventType=inPerson" in url
        assert "distance=10" in url
        assert "source=EVENTS" in url

    def test_get_events_url_stores_date_range(self):
        """Test that date range is stored for post-extraction filtering."""
        crawler = MeetupCrawler()

        start = datetime(2026, 2, 1)
        end = datetime(2026, 2, 15)

        crawler.get_events_url("New York, NY", start_date=start, end_date=end)

        # Should store dates internally
        assert hasattr(crawler, '_start_date')
        assert hasattr(crawler, '_end_date')
        assert crawler._start_date == start
        assert crawler._end_date == end

    def test_crawler_parameters(self):
        """Test crawler initialization with custom parameters."""
        crawler = MeetupCrawler(
            rate_limit_seconds=1.0,
            max_events_total=50,
            max_events_per_day=25,
            distance_miles=5,
            event_type="online"
        )

        assert crawler.max_events_total == 50
        assert crawler.max_events_per_day == 25
        assert crawler.distance_miles == 5
        assert crawler.event_type == "online"

    @pytest.mark.integration
    def test_live_crawl_with_limits(self):
        """
        Test live crawling with total and daily limits.

        This test:
        1. Crawls real Meetup page
        2. Verifies scrolling works
        3. Checks daily limit enforcement
        4. Validates event data quality
        """
        crawler = MeetupCrawler(
            rate_limit_seconds=0,  # No delay for testing
            max_events_total=20,  # Lower limit for testing
            max_events_per_day=10,
            distance_miles=10,
            event_type="inPerson"
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = context.new_page()

            # Build URL and navigate
            start_date = datetime.now()
            end_date = start_date + timedelta(days=14)
            url = crawler.get_events_url("New York, NY", start_date, end_date)

            page.goto(url, wait_until='domcontentloaded', timeout=60000)

            # Extract events
            events = crawler.extract_events_from_page(page)

            browser.close()

        # Assertions
        assert len(events) <= 20, "Should respect max_events_total limit"
        assert len(events) > 0, "Should find at least some events"

        # Check that all events are within date range
        for event in events:
            event_dt = event.start_datetime.replace(tzinfo=None)
            start_dt = start_date.replace(tzinfo=None)
            end_dt = end_date.replace(tzinfo=None)

            assert start_dt <= event_dt <= end_dt, \
                f"Event {event.event_id} ({event_dt}) outside range {start_dt} to {end_dt}"

        # Check daily limit enforcement
        events_by_day = {}
        for event in events:
            day = event.start_datetime.date()
            events_by_day[day] = events_by_day.get(day, 0) + 1

        for day, count in events_by_day.items():
            assert count <= 10, f"Day {day} has {count} events, exceeds daily limit of 10"

        # Check event data quality
        for event in events:
            assert event.event_id
            assert event.source == EventSource.MEETUP
            assert event.url
            assert event.title
            assert event.start_datetime
            # Location should be present for in-person events
            assert event.location_name or event.city

    @pytest.mark.integration
    def test_live_crawl_date_filtering(self):
        """Test that post-extraction date filtering works correctly."""
        crawler = MeetupCrawler(max_events_total=50)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = context.new_page()

            # Use a specific 7-day range
            start_date = datetime.now()
            end_date = start_date + timedelta(days=7)
            url = crawler.get_events_url("New York, NY", start_date, end_date)

            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            events = crawler.extract_events_from_page(page)

            browser.close()

        # All events should be within the 7-day range
        for event in events:
            event_dt = event.start_datetime.replace(tzinfo=None)
            start_dt = start_date.replace(tzinfo=None)
            end_dt = end_date.replace(tzinfo=None)

            assert start_dt <= event_dt <= end_dt, \
                f"Event outside 7-day range: {event.title} on {event_dt}"

    def test_url_with_different_locations(self):
        """Test URL building with different location strings."""
        crawler = MeetupCrawler()

        locations = [
            "New York, NY",
            "Manhattan, NY",
            "Brooklyn, NY",
            "10001"  # ZIP code
        ]

        for location in locations:
            url = crawler.get_events_url(location)
            assert f"location={location.replace(' ', '+').replace(',', '%2C')}" in url

    def test_url_with_different_event_types(self):
        """Test URL building with different event types."""
        test_cases = [
            ("inPerson", "eventType=inPerson"),
            ("online", "eventType=online"),
            ("all", None),  # Should not include eventType
        ]

        for event_type, expected in test_cases:
            crawler = MeetupCrawler(event_type=event_type)
            url = crawler.get_events_url("New York, NY")

            if expected:
                assert expected in url
            else:
                assert "eventType" not in url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
