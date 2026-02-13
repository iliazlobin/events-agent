"""Jazz Near You crawler for NYC jazz events."""

import logging
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

from playwright.sync_api import Page
from bs4 import BeautifulSoup

from events_agent.crawlers.base import BaseCrawler
from events_agent.models.event import Event, EventSource
from events_agent.utils.date_utils import parse_datetime_with_fallback

logger = logging.getLogger(__name__)


class JazzNearYouCrawler(BaseCrawler):
    """
    Crawler for Jazz Near You (jazznearyou.com).
    
    Extracts jazz events in NYC with venue, artist, and date information.
    """
    
    BASE_URL = "https://www.jazznearyou.com"
    
    def get_events_url(self, location: str = "nyc") -> str:
        """
        Get Jazz Near You calendar URL.
        
        Args:
            location: Location code (default: nyc)
            
        Returns:
            Full URL to events page.
        """
        return f"{self.BASE_URL}/{location}"
    
    def extract_events_from_page(self, page: Page) -> List[Event]:
        """
        Extract jazz events from Jazz Near You page.

        Args:
            page: Playwright page instance.

        Returns:
            List of Event objects.
        """
        events = []

        try:
            # Wait for event cards to load
            page.wait_for_selector('.card', timeout=10000)

            # Get page content
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Find event cards
            event_items = soup.find_all('div', class_='card')

            logger.info(f"Found {len(event_items)} event cards")

            for item in event_items:
                try:
                    event = self._parse_event_item(item, self.BASE_URL)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to parse event item: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to extract events from Jazz Near You: {e}")

        logger.info(f"Successfully extracted {len(events)} jazz events")
        return events
    
    def _parse_event_item(self, item, base_url: str) -> Optional[Event]:
        """
        Parse individual event item from HTML.

        Args:
            item: BeautifulSoup element containing event data.
            base_url: Base URL for resolving relative links.

        Returns:
            Event object or None if parsing fails.
        """
        try:
            # Extract title/artist from h5 > a
            title_elem = item.find('h5')
            if not title_elem:
                return None
            title_link = title_elem.find('a')
            if not title_link:
                return None

            title = title_link.get_text(strip=True)
            event_url = title_link.get('href', '')
            if not event_url.startswith('http'):
                event_url = urljoin(base_url, event_url)

            # Extract venue - the <a> tag after h5 in card-body
            card_body = item.find('div', class_='card-body')
            if not card_body:
                return None

            venue_link = card_body.find('a', href=re.compile(r'/venue/'))
            location_name = venue_link.get_text(strip=True) if venue_link else None

            # Extract date - from card-img-title or show-575
            date_elem = item.find('span', class_='card-img-title')
            if not date_elem:
                date_elem = item.find('span', class_='show-575')

            date_str = date_elem.get_text(strip=True) if date_elem else ""

            # Extract time - text in card-body after venue
            time_str = ""
            if card_body:
                # Get all text, extract time pattern
                body_text = card_body.get_text()
                time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm))', body_text, re.IGNORECASE)
                if time_match:
                    time_str = time_match.group(1)

            # Combine date and time
            datetime_str = f"{date_str} {time_str}".strip()
            start_datetime = parse_datetime_with_fallback(datetime_str)
            if not start_datetime:
                # Fallback
                from datetime import timedelta
                start_datetime = datetime.now() + timedelta(days=1)

            # Extract location - from sub_title
            location_elem = item.find('span', class_='sub_title')
            city_state = location_elem.get_text(strip=True) if location_elem else "New York, NY"

            # Generate event ID
            event_id = self._generate_event_id(event_url, title)

            # Create Event object
            event = Event(
                event_id=event_id,
                source=EventSource.JAZZNEARYOU,
                url=event_url,
                title=title,
                start_datetime=start_datetime,
                location_name=location_name,
                city="New York",
                state="NY",
                is_online=False,
                genre="jazz",
                category="music",
                performer_names=[title] if title else None,
                experience_type="concert",
                is_free=True,  # Jazz Near You doesn't show price typically
                tags=["jazz", "live-music"],
            )

            return event

        except Exception as e:
            logger.warning(f"Error parsing event item: {e}")
            return None
    
    def _generate_event_id(self, url: str, title: str) -> str:
        """
        Generate unique event ID from URL or title.
        
        Args:
            url: Event URL.
            title: Event title.
            
        Returns:
            Unique event ID string.
        """
        # Try to extract ID from URL
        url_match = re.search(r'/events?/(\d+)', url)
        if url_match:
            return f"jny-{url_match.group(1)}"
        
        # Generate from title and URL hash
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"jny-{url_hash}"


class SongkickCrawler(BaseCrawler):
    """
    Crawler for Songkick jazz events in NYC.
    
    Songkick has comprehensive music event data with venue and artist info.
    """
    
    BASE_URL = "https://www.songkick.com"
    
    def get_events_url(self, location: str = "nyc") -> str:
        """
        Get Songkick events URL for jazz genre in NYC.
        
        Args:
            location: Location (default: nyc)
            
        Returns:
            Full URL to events page.
        """
        # NYC metro area ID is 7644
        return f"{self.BASE_URL}/metro-areas/7644-us-new-york-nyc/genre/jazz"
    
    def extract_events_from_page(self, page: Page) -> List[Event]:
        """
        Extract events from Songkick page.

        Args:
            page: Playwright page instance.

        Returns:
            List of Event objects.
        """
        events = []

        try:
            # Wait for event listings
            page.wait_for_selector('.event-listings-element', timeout=15000)

            # Scroll to load more events
            self._scroll_to_load_events(page)

            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Find event items
            event_items = soup.find_all('li', class_='event-listings-element')

            logger.info(f"Found {len(event_items)} event items on Songkick")

            for item in event_items:
                try:
                    event = self._parse_songkick_event(item)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to parse Songkick event: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to extract events from Songkick: {e}")

        logger.info(f"Successfully extracted {len(events)} events from Songkick")
        return events
    
    def _scroll_to_load_events(self, page: Page, max_scrolls: int = 3) -> None:
        """
        Scroll page to trigger lazy loading of more events.
        
        Args:
            page: Playwright page instance.
            max_scrolls: Maximum number of scroll attempts.
        """
        for i in range(max_scrolls):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)  # Wait for content to load
    
    def _parse_songkick_event(self, item) -> Optional[Event]:
        """
        Parse individual Songkick event.

        Args:
            item: BeautifulSoup element.

        Returns:
            Event object or None.
        """
        try:
            # Extract artist/title from .artists strong
            artists_elem = item.find('p', class_='artists')
            if not artists_elem:
                return None

            artist_strong = artists_elem.find('strong')
            if not artist_strong:
                return None

            title = artist_strong.get_text(strip=True)

            # Extract URL from event-link
            url_elem = item.find('a', class_='event-link')
            if not url_elem:
                return None

            event_url = url_elem.get('href', '')
            if not event_url.startswith('http'):
                event_url = urljoin(self.BASE_URL, event_url)

            # Extract venue from .venue-link
            venue_elem = item.find('a', class_='venue-link')
            location_name = venue_elem.get_text(strip=True) if venue_elem else None

            # Extract city from .city-name
            city_elem = item.find('span', class_='city-name')
            city_state = city_elem.get_text(strip=True) if city_elem else "New York (NYC), NY, US"

            # Extract date from time[datetime]
            time_elem = item.find('time', datetime=True)
            date_str = time_elem.get('datetime') if time_elem else None

            start_datetime = parse_datetime_with_fallback(date_str) if date_str else datetime.now()

            # Generate event ID
            event_id = self._generate_event_id_from_url(event_url)

            # Create Event
            event = Event(
                event_id=event_id,
                source=EventSource.SONGKICK,
                url=event_url,
                title=title,
                start_datetime=start_datetime,
                location_name=location_name,
                city="New York",
                state="NY",
                is_online=False,
                genre="jazz",
                category="music",
                performer_names=[title] if title else None,
                experience_type="concert",
                tags=["jazz", "live-music", "concert"],
            )

            return event

        except Exception as e:
            logger.warning(f"Error parsing Songkick event: {e}")
            return None
    
    def _generate_event_id_from_url(self, url: str) -> str:
        """Generate event ID from Songkick URL."""
        # Songkick URLs contain event ID: /concerts/123456-artist-name
        match = re.search(r'/concerts/(\d+)', url)
        if match:
            return f"sk-{match.group(1)}"
        
        # Fallback: hash the URL
        import hashlib
        return f"sk-{hashlib.md5(url.encode()).hexdigest()[:8]}"
