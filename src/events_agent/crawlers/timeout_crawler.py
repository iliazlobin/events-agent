"""TimeOut NYC crawler for cultural events including jazz and special occasions."""

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


class TimeOutNYCCrawler(BaseCrawler):
    """
    Crawler for TimeOut NYC events.
    
    Excellent for:
    - Cultural events (music, art, comedy)
    - Seasonal/holiday events (Valentine's Day, etc.)
    - Jazz and live music
    - Food & drink events
    """
    
    BASE_URL = "https://www.timeout.com"
    
    def __init__(self, category: str = "music", rate_limit_seconds: float = 2.0):
        """
        Initialize TimeOut crawler.
        
        Args:
            category: Event category (music, valentines-day, events-calendar, etc.)
            rate_limit_seconds: Delay between requests.
        """
        super().__init__(rate_limit_seconds)
        self.category = category
    
    def get_events_url(self, location: str = "newyork") -> str:
        """
        Get TimeOut events URL.
        
        Args:
            location: Location slug (default: newyork)
            
        Returns:
            Full URL to events page.
        """
        if self.category == "valentines-day":
            return f"{self.BASE_URL}/{location}/valentines-day"
        elif self.category == "jazz":
            return f"{self.BASE_URL}/{location}/music/best-jazz-clubs-in-nyc"
        else:
            return f"{self.BASE_URL}/{location}/events-calendar"
    
    def extract_events_from_page(self, page: Page) -> List[Event]:
        """
        Extract events from TimeOut page.
        
        Args:
            page: Playwright page instance.
            
        Returns:
            List of Event objects.
        """
        events = []
        
        try:
            # Wait for content to load
            page.wait_for_selector('article, .card, .event-card', timeout=15000)
            
            # Scroll to load more events
            self._scroll_page(page)
            
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find event cards/articles
            event_items = soup.find_all(['article', 'div'], class_=re.compile(r'card|event|listing'))
            
            logger.info(f"Found {len(event_items)} items on TimeOut NYC")
            
            for item in event_items:
                try:
                    event = self._parse_event_item(item)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to parse TimeOut event: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to extract events from TimeOut NYC: {e}")
        
        logger.info(f"Successfully extracted {len(events)} events from TimeOut")
        return events
    
    def _scroll_page(self, page: Page, scrolls: int = 3) -> None:
        """Scroll page to load lazy-loaded content."""
        for _ in range(scrolls):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
    
    def _parse_event_item(self, item) -> Optional[Event]:
        """
        Parse individual event from HTML.
        
        Args:
            item: BeautifulSoup element.
            
        Returns:
            Event object or None.
        """
        try:
            # Extract title
            title_elem = item.find(['h2', 'h3', 'h4'], class_=re.compile(r'title|heading'))
            if not title_elem:
                title_elem = item.find('a')
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            
            # Extract URL
            url_elem = item.find('a', href=True)
            if not url_elem:
                return None
            event_url = urljoin(self.BASE_URL, url_elem['href'])
            
            # Skip if not an event URL
            if '/things-to-do/' not in event_url and '/events/' not in event_url:
                return None
            
            # Extract description
            desc_elem = item.find(['p', 'div'], class_=re.compile(r'description|excerpt|summary'))
            description = desc_elem.get_text(strip=True) if desc_elem else None
            
            # Extract venue/location
            venue_elem = item.find(['span', 'div', 'p'], class_=re.compile(r'venue|location|where'))
            location_name = venue_elem.get_text(strip=True) if venue_elem else None
            
            # Extract date
            date_elem = item.find(['time', 'span', 'div'], class_=re.compile(r'date|when'))
            date_str = None
            if date_elem:
                if date_elem.has_attr('datetime'):
                    date_str = date_elem['datetime']
                else:
                    date_str = date_elem.get_text(strip=True)
            
            start_datetime = parse_datetime_with_fallback(date_str) if date_str else datetime.now()
            
            # Extract image
            img_elem = item.find('img', src=True)
            image_url = img_elem['src'] if img_elem else None
            
            # Determine category and tags
            category = self.category if self.category != "events-calendar" else "entertainment"
            tags = [category]
            
            # Detect jazz from title/description
            text_content = (title + " " + (description or "")).lower()
            if any(word in text_content for word in ["jazz", "blues", "swing", "bebop"]):
                tags.append("jazz")
                category = "music"
            
            # Detect Valentine's related
            if any(word in text_content for word in ["valentine", "romantic", "couples", "date night"]):
                tags.append("valentines-day")
            
            # Generate event ID
            event_id = self._generate_event_id(event_url)
            
            # Create Event
            event = Event(
                event_id=event_id,
                source=EventSource.TIMEOUT,
                url=event_url,
                title=title,
                description=description,
                start_datetime=start_datetime,
                location_name=location_name,
                city="New York",
                state="NY",
                is_online=False,
                category=category,
                image_url=image_url,
                tags=tags if tags else None,
            )
            
            return event
            
        except Exception as e:
            logger.warning(f"Error parsing TimeOut event: {e}")
            return None
    
    def _generate_event_id(self, url: str) -> str:
        """Generate unique event ID from URL."""
        # Extract slug from URL
        match = re.search(r'/things-to-do/([^/]+)', url)
        if not match:
            match = re.search(r'/events/([^/]+)', url)
        
        if match:
            return f"to-{match.group(1)}"
        
        # Fallback: hash URL
        import hashlib
        return f"to-{hashlib.md5(url.encode()).hexdigest()[:8]}"


class DoNYCCrawler(BaseCrawler):
    """
    Crawler for DoNYC (donyc.com) events.
    
    Curated NYC events including Valentine's Day and seasonal events.
    """
    
    BASE_URL = "https://donyc.com"
    
    def get_events_url(self, location: str = "valentines-day") -> str:
        """
        Get DoNYC events URL.
        
        Args:
            location: Category/theme (valentines-day, events, etc.)
            
        Returns:
            Full URL to events page.
        """
        return f"{self.BASE_URL}/{location}"
    
    def extract_events_from_page(self, page: Page) -> List[Event]:
        """
        Extract events from DoNYC page.
        
        Args:
            page: Playwright page instance.
            
        Returns:
            List of Event objects.
        """
        events = []
        
        try:
            # Wait for events to load
            page.wait_for_selector('.event-card, article, .listing', timeout=15000)
            
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find event listings
            event_items = soup.find_all(['article', 'div'], class_=re.compile(r'event|card|listing'))
            
            logger.info(f"Found {len(event_items)} items on DoNYC")
            
            for item in event_items:
                try:
                    event = self._parse_donyc_event(item)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to parse DoNYC event: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to extract events from DoNYC: {e}")
        
        logger.info(f"Successfully extracted {len(events)} events from DoNYC")
        return events
    
    def _parse_donyc_event(self, item) -> Optional[Event]:
        """Parse individual DoNYC event."""
        try:
            # Extract title
            title_elem = item.find(['h2', 'h3', 'a'])
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            
            # Extract URL
            url_elem = item.find('a', href=True)
            if not url_elem:
                return None
            event_url = urljoin(self.BASE_URL, url_elem['href'])
            
            # Extract date
            date_elem = item.find(['time', 'span'], class_=re.compile(r'date'))
            date_str = None
            if date_elem:
                date_str = date_elem.get('datetime') if date_elem.has_attr('datetime') else date_elem.get_text(strip=True)
            
            start_datetime = parse_datetime_with_fallback(date_str) if date_str else datetime.now()
            
            # Extract venue
            venue_elem = item.find(['span', 'p'], class_=re.compile(r'venue|location'))
            location_name = venue_elem.get_text(strip=True) if venue_elem else None
            
            # Generate event ID
            import hashlib
            event_id = f"donyc-{hashlib.md5(event_url.encode()).hexdigest()[:8]}"
            
            # Create Event
            event = Event(
                event_id=event_id,
                source=EventSource.DONYC,
                url=event_url,
                title=title,
                start_datetime=start_datetime,
                location_name=location_name,
                city="New York",
                state="NY",
                is_online=False,
                tags=["valentines-day", "curated"],
            )
            
            return event
            
        except Exception as e:
            logger.warning(f"Error parsing DoNYC event: {e}")
            return None
