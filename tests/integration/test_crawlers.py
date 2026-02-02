"""Integration tests for crawlers."""

import pytest
from unittest.mock import Mock, MagicMock
from events_agent.crawlers.luma_crawler import LumaCrawler
from events_agent.crawlers.meetup_crawler import MeetupCrawler


def test_luma_crawler_get_events_url():
    """Test LumaCrawler URL construction."""
    crawler = LumaCrawler()
    url = crawler.get_events_url("nyc")

    assert url == "https://lu.ma/nyc"


def test_meetup_crawler_get_events_url():
    """Test MeetupCrawler URL construction."""
    crawler = MeetupCrawler()
    url = crawler.get_events_url("new-york")

    assert url == "https://www.meetup.com/find/?location=us--ny--new-york&source=EVENTS"


def test_luma_crawler_with_mock_page():
    """Test LumaCrawler with mocked Playwright page."""
    crawler = LumaCrawler()

    # Create mock page
    mock_page = Mock()
    mock_page.evaluate.return_value = {
        "props": {
            "pageProps": {
                "events": [
                    {
                        "api_id": "test-event-1",
                        "name": "Test Event",
                        "start_at": "2026-02-05T18:00:00Z",
                        "url": "https://lu.ma/test-event-1",
                        "geo_address_info": {
                            "city": "New York",
                            "region": "NY"
                        }
                    }
                ]
            }
        }
    }

    events = crawler.extract_events_from_page(mock_page)

    assert len(events) > 0
    assert events[0].title == "Test Event"
    assert events[0].city == "New York"


def test_meetup_crawler_with_mock_page():
    """Test MeetupCrawler with mocked Playwright page."""
    crawler = MeetupCrawler()

    # Create mock page with Apollo state
    mock_page = Mock()
    apollo_state = {
        "Event:123": {
            "id": "123",
            "title": "Python Meetup",
            "dateTime": "2026-02-05T18:00:00Z",
            "eventType": "PHYSICAL",
            "venue": {
                "__ref": "Venue:456"
            },
            "group": {
                "__ref": "Group:789"
            }
        },
        "Venue:456": {
            "name": "Tech Hub",
            "city": "New York",
            "state": "NY"
        },
        "Group:789": {
            "name": "NYC Python",
            "urlname": "nyc-python"
        }
    }
    mock_page.evaluate.return_value = apollo_state
    mock_page.content.return_value = "<html></html>"

    events = crawler.extract_events_from_page(mock_page)

    assert len(events) > 0
    assert events[0].title == "Python Meetup"
    assert events[0].city == "New York"
    assert events[0].organizer_name == "NYC Python"


@pytest.mark.integration
def test_luma_crawler_real_request():
    """
    Integration test with real browser request.

    Run with: pytest -m integration
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        crawler = LumaCrawler()

        try:
            events = crawler.crawl(browser, "nyc")
            print(f"\nFetched {len(events)} events from Luma")

            if events:
                print(f"Sample event: {events[0].title}")

        finally:
            browser.close()


@pytest.mark.integration
def test_meetup_crawler_real_request():
    """
    Integration test with real browser request.

    Run with: pytest -m integration
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        crawler = MeetupCrawler()

        try:
            events = crawler.crawl(browser, "new-york")
            print(f"\nFetched {len(events)} events from Meetup")

            if events:
                print(f"Sample event: {events[0].title}")

        finally:
            browser.close()
