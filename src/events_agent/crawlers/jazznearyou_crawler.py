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
            # Wait for events to load
            page.wait_for_selector('.event-item, .show-listing, article', timeout=10000)
            
            # Get page content
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find event listings (adjust selectors based on actual site structure)
            event_items = soup.find_all(['article', 'div'], class_=re.compile(r'event|show'))
            
            logger.info(f"Found {len(event_items)} potential event items")
            
            for item in event_items:
                try:
                    event = self._parse_event_item(item, page.url)
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
            # Extract title and artist
            title_elem = item.find(['h2', 'h3', 'a'], class_=re.compile(r'title|name|artist'))
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            
            # Extract URL
            url_elem = item.find('a', href=True)
            if not url_elem:
                return None
            event_url = urljoin(base_url, url_elem['href'])
            
            # Extract venue
            venue_elem = item.find(['span', 'div', 'p'], class_=re.compile(r'venue|location'))
            location_name = venue_elem.get_text(strip=True) if venue_elem else None
            
            # Extract date/time
            date_elem = item.find(['time', 'span', 'div'], class_=re.compile(r'date|time'))
            date_str = date_elem.get_text(strip=True) if date_elem else None
            
            # Parse datetime with fallback
            start_datetime = None
            if date_str:
                start_datetime = parse_datetime_with_fallback(date_str)
            if not start_datetime:
                # Use tomorrow as fallback
                from datetime import timedelta
                start_datetime = datetime.now() + timedelta(days=1)
            
            # Extract performer names (may be in title or separate element)
            performer_names = []
            artist_elems = item.find_all(['span', 'div'], class_=re.compile(r'artist|performer'))
            for artist_elem in artist_elems:
                performer = artist_elem.get_text(strip=True)
                if performer:
                    performer_names.append(performer)
            
            # Generate event ID from URL or title
            event_id = self._generate_event_id(event_url, title)
            
            # Extract price if available
            price_elem = item.find(['span', 'div'], class_=re.compile(r'price|cost'))
            price_cents = None
            is_free = True
            if price_elem:
                price_text = price_elem.get_text(strip=True).lower()
                if 'free' not in price_text:
                    is_free = False
                    # Try to extract numeric price
                    price_match = re.search(r'\$?(\d+(?:\.\d{2})?)', price_text)
                    if price_match:
                        price_cents = int(float(price_match.group(1)) * 100)
            
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
                performer_names=performer_names if performer_names else None,
                experience_type="concert",
                price_cents=price_cents,
                is_free=is_free,
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
            page.wait_for_selector('.event-listings li, .event-listing', timeout=15000)
            
            # Scroll to load more events
            self._scroll_to_load_events(page)
            
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find event items
            event_items = soup.find_all('li', class_=re.compile(r'event'))
            
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
            # Extract artist/title
            artist_elem = item.find(['strong', 'a'], class_=re.compile(r'artist|summary'))
            if not artist_elem:
                return None
            title = artist_elem.get_text(strip=True)
            
            # Extract URL
            url_elem = item.find('a', href=True)
            if not url_elem:
                return None
            event_url = urljoin(self.BASE_URL, url_elem['href'])
            
            # Extract venue
            venue_elem = item.find(['span', 'p'], class_=re.compile(r'venue|location'))
            location_name = venue_elem.get_text(strip=True) if venue_elem else None
            
            # Extract date
            date_elem = item.find(['time', 'span'], class_=re.compile(r'date'))
            date_str = date_elem.get('datetime') if date_elem and date_elem.has_attr('datetime') else None
            if not date_str and date_elem:
                date_str = date_elem.get_text(strip=True)
            
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
