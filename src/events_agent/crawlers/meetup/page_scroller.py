"""Page scrolling utilities for Meetup infinite scroll."""

from playwright.sync_api import Page
from .constants import DEFAULT_SCROLL_WAIT_MS, MAX_SCROLL_ATTEMPTS, PAGE_LOAD_WAIT_MS


class PageScroller:
    """Handles infinite scroll on Meetup pages."""

    @staticmethod
    def initial_wait(page: Page) -> None:
        """Wait for initial page load."""
        page.wait_for_timeout(PAGE_LOAD_WAIT_MS)

    @staticmethod
    def scroll_to_bottom(page: Page) -> None:
        """Scroll to the bottom of the page."""
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(DEFAULT_SCROLL_WAIT_MS)

    @staticmethod
    def get_event_link_count(page: Page) -> int:
        """
        Count event links on the page.

        Returns:
            Number of event links found
        """
        return page.evaluate('''() => {
            return document.querySelectorAll('a[href*="/events/"]').length;
        }''')

    @staticmethod
    def should_continue_scrolling(
        scroll_count: int,
        no_change_count: int,
        total_events: int,
        max_events: int
    ) -> bool:
        """
        Determine if scrolling should continue.

        Args:
            scroll_count: Number of scrolls performed
            no_change_count: Number of scrolls with no new content
            total_events: Total events collected so far
            max_events: Maximum events to collect

        Returns:
            True if scrolling should continue
        """
        # Stop if reached max scrolls
        if scroll_count >= MAX_SCROLL_ATTEMPTS:
            return False

        # Stop if reached event limit
        if total_events >= max_events:
            return False

        # Stop if no new content after 3 scrolls
        if no_change_count >= 3:
            return False

        return True
