"""Abstract base class for event crawlers."""

from abc import ABC, abstractmethod
from typing import List
from playwright.sync_api import Page, Browser
import time
from events_agent.models.event import Event


class BaseCrawler(ABC):
    """
    Abstract base class for event crawlers.

    Defines the interface that all crawler implementations must follow.
    Uses Playwright for JavaScript-rendered pages.
    """

    def __init__(self, rate_limit_seconds: float = 2.0):
        """
        Initialize crawler.

        Args:
            rate_limit_seconds: Minimum delay between requests
        """
        self.rate_limit_seconds = rate_limit_seconds

    @abstractmethod
    def get_events_url(self, location: str) -> str:
        """
        Construct the URL for fetching events in a specific location.

        Args:
            location: Location identifier (e.g., 'nyc', 'new-york')

        Returns:
            Full URL to fetch events
        """
        pass

    @abstractmethod
    def extract_events_from_page(self, page: Page) -> List[Event]:
        """
        Extract event data from a loaded Playwright page.

        Args:
            page: Playwright Page object with loaded content

        Returns:
            List of Event objects extracted from the page
        """
        pass

    def crawl(self, browser: Browser, location: str) -> List[Event]:
        """
        Main crawl method - fetches and extracts events.

        Args:
            browser: Playwright Browser instance
            location: Location to search (e.g., 'nyc')

        Returns:
            List of Event objects
        """
        url = self.get_events_url(location)
        page = browser.new_page()

        try:
            # Set user agent to avoid bot detection
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })

            # Navigate and wait for network idle
            print(f"  Fetching URL: {url}")
            page.goto(url, wait_until='domcontentloaded', timeout=90000)

            # Additional wait for JavaScript execution
            page.wait_for_timeout(3000)

            # Extract events (may include scrolling for infinite scroll pages)
            events = self.extract_events_from_page(page)

            # Rate limiting
            time.sleep(self.rate_limit_seconds)

            return events

        except Exception as e:
            print(f"  Error crawling {url}: {e}")
            return []

        finally:
            page.close()

    def scroll_to_load_more(self, page: Page, max_scrolls: int = 10) -> int:
        """
        Scroll page to trigger infinite scroll loading.

        Args:
            page: Playwright Page object
            max_scrolls: Maximum number of scroll attempts

        Returns:
            Number of successful scrolls performed
        """
        scrolls = 0
        for i in range(max_scrolls):
            # Get current scroll height
            prev_height = page.evaluate('document.body.scrollHeight')

            # Scroll to bottom
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')

            # Wait for new content to load
            page.wait_for_timeout(2000)

            # Check if new content loaded
            new_height = page.evaluate('document.body.scrollHeight')

            if new_height == prev_height:
                # No new content loaded, we've reached the end
                break

            scrolls += 1

        return scrolls
