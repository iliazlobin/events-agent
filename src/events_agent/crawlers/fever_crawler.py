"""Fever (feverup.com) event crawler."""

from typing import List, Optional
import json
import re
import time
from playwright.sync_api import Page, Browser
from events_agent.crawlers.base import BaseCrawler
from events_agent.models.event import Event, EventSource
from events_agent.utils.date_utils import parse_iso_datetime


class FeverCrawler(BaseCrawler):
    """
    Crawler for Fever (feverup.com) events.

    Strategy:
    - Main page lists events but doesn't have full data
    - Individual event pages (/m/{plan_id}) have complete Schema.org Event data
    - Extract event URLs from main page, then visit each event page for details
    """

    def __init__(self, rate_limit_seconds: float = 2.0, max_events: int = 100):
        """
        Initialize Fever crawler.

        Args:
            rate_limit_seconds: Minimum delay between requests
            max_events: Maximum number of events to crawl (default: 100)
        """
        super().__init__(rate_limit_seconds)
        self.max_events = max_events

    def get_events_url(self, location: str) -> str:
        """
        Get Fever URL for a location.

        Args:
            location: Location identifier (e.g., 'nyc', 'new-york')

        Returns:
            Full Fever URL
        """
        # Fever uses language/location pattern like /en/new-york
        # Convert 'nyc' to 'new-york' if needed
        if location.lower() == 'nyc':
            location = 'new-york'
        return f"https://feverup.com/en/{location}"

    def crawl(self, browser: Browser, location: str) -> List[Event]:
        """
        Custom crawl method for Fever (overrides BaseCrawler.crawl).

        Two-step process:
        1. Extract event URLs from main page
        2. Visit each event page and extract Schema.org data

        Args:
            browser: Playwright Browser instance
            location: Location to search (e.g., 'nyc')

        Returns:
            List of Event objects
        """
        events = []

        try:
            # Step 1: Get event URLs from main page
            print(f"    Step 1: Extracting event URLs from Fever main page...")
            main_url = self.get_events_url(location)
            page = browser.new_page()

            try:
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })

                page.goto(main_url, wait_until='networkidle', timeout=60000)
                page.wait_for_timeout(3000)

                # Extract event URLs from DOM
                event_urls = self._extract_event_urls(page)
                print(f"    Found {len(event_urls)} event URLs")

                # Limit to max_events
                event_urls = event_urls[:self.max_events]

            finally:
                page.close()

            # Step 2: Visit each event page and extract Schema.org data
            print(f"    Step 2: Extracting event details from {len(event_urls)} event pages...")
            for i, event_url in enumerate(event_urls, 1):
                try:
                    if i % 10 == 0:
                        print(f"      Processed {i}/{len(event_urls)} events...")

                    event = self._extract_event_from_url(browser, event_url)
                    if event:
                        events.append(event)

                    # Rate limiting
                    time.sleep(self.rate_limit_seconds)

                except Exception as e:
                    print(f"      Error extracting event from {event_url}: {e}")
                    continue

            print(f"    Extracted {len(events)} total events from Fever")

        except Exception as e:
            print(f"    Error crawling Fever: {e}")

        return events

    def extract_events_from_page(self, page: Page) -> List[Event]:
        """
        Not used for Fever (uses custom crawl method).

        Args:
            page: Playwright Page object

        Returns:
            Empty list
        """
        return []

    def _extract_event_urls(self, page: Page) -> List[str]:
        """
        Extract all event URLs from Fever main page.

        Args:
            page: Playwright Page object with main page loaded

        Returns:
            List of event URLs
        """
        try:
            # Extract URLs with /m/ pattern (Fever event pages)
            event_urls = page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a[href*="/m/"]'));
                const uniqueUrls = new Set();
                links.forEach(link => {
                    // Get full URL
                    const url = link.href;
                    // Only include /m/{id} pages (not /m/category or other variants)
                    if (url.match(/\\/m\\/\\d+/)) {
                        uniqueUrls.add(url);
                    }
                });
                return Array.from(uniqueUrls);
            }''')

            return event_urls

        except Exception as e:
            print(f"      Error extracting event URLs: {e}")
            return []

    def _extract_event_from_url(self, browser: Browser, event_url: str) -> Optional[Event]:
        """
        Visit an event page and extract Schema.org Event data.

        Args:
            browser: Playwright Browser instance
            event_url: Full URL to event page

        Returns:
            Event object or None
        """
        page = browser.new_page()

        try:
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })

            page.goto(event_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2000)

            # Get HTML content
            html_content = page.content()

            # Extract Schema.org blocks
            schema_blocks = self._extract_schema_org_blocks(html_content)

            # Find Event block
            for block in schema_blocks:
                if isinstance(block, dict) and block.get('@type') == 'Event':
                    return self._parse_fever_event(block, event_url)

            return None

        except Exception as e:
            print(f"        Error loading {event_url}: {e}")
            return None

        finally:
            page.close()

    def _extract_schema_org_blocks(self, html_content: str) -> List[dict]:
        """
        Extract all Schema.org JSON-LD script blocks from HTML.

        Args:
            html_content: HTML page content

        Returns:
            List of parsed JSON objects
        """
        blocks = []

        try:
            # Pattern to match <script type="application/ld+json">...</script>
            pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)

            for match in matches:
                try:
                    # Parse JSON
                    data = json.loads(match)
                    blocks.append(data)
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"      Error extracting Schema.org blocks: {e}")

        return blocks

    def _parse_fever_event(self, event_data: dict, event_url: str) -> Optional[Event]:
        """
        Transform Fever Schema.org event to Event model.

        Schema.org Event fields from Fever:
        - @type: Event
        - name: Event title
        - description: Event description
        - startDate, endDate: ISO 8601 timestamps with timezone
        - url: Event URL
        - image: Image URL
        - offers: [{price, priceCurrency}]
        - location: {name, address: {addressLocality}, geo: {latitude, longitude}}

        Args:
            event_data: Raw Schema.org event data from Fever page
            event_url: Full URL to the event page

        Returns:
            Event object or None if parsing fails
        """
        try:
            # Required fields
            title = event_data.get('name')
            start_date = event_data.get('startDate')

            if not all([title, start_date]):
                return None

            # Parse datetimes
            start_datetime = parse_iso_datetime(start_date)
            if not start_datetime:
                return None

            end_datetime = None
            if event_data.get('endDate'):
                end_datetime = parse_iso_datetime(event_data['endDate'])

            # Extract event ID from URL
            event_id = self._extract_event_id_from_url(event_url)
            if not event_id:
                # Fallback: use hash of title + start date
                event_id = f"fever-{hash(title + start_date) % 1000000}"

            # Location info
            location_name = None
            location_address = None
            city = None
            state = None
            latitude = None
            longitude = None
            is_online = False

            location_data = event_data.get('location', {})
            if isinstance(location_data, dict):
                location_name = location_data.get('name')

                # Address
                address_data = location_data.get('address', {})
                if isinstance(address_data, dict):
                    location_address = address_data.get('streetAddress')
                    city = address_data.get('addressLocality')
                    state = address_data.get('addressRegion')

                # Geo coordinates
                geo_data = location_data.get('geo', {})
                if isinstance(geo_data, dict):
                    latitude = geo_data.get('latitude')
                    longitude = geo_data.get('longitude')

                # Check if virtual location
                if 'Virtual' in str(location_data.get('@type', '')):
                    is_online = True

            # Pricing
            price_cents = 0
            currency = 'USD'
            is_free = True

            offers = event_data.get('offers', [])
            if isinstance(offers, list) and len(offers) > 0:
                offer = offers[0]
                if isinstance(offer, dict):
                    price = offer.get('price')
                    if price is not None:
                        try:
                            # Convert price to cents
                            price_float = float(price)
                            price_cents = int(price_float * 100)
                            is_free = (price_cents == 0)
                        except (ValueError, TypeError):
                            pass

                    currency = offer.get('priceCurrency', 'USD')

            # Image
            image_url = event_data.get('image')

            # Infer experience type from title and description
            experience_type = self._infer_experience_type(title, event_data.get('description', ''))

            return Event(
                event_id=event_id,
                source=EventSource.FEVER,
                url=event_url,
                title=title,
                description=event_data.get('description'),
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                location_name=location_name,
                location_address=location_address,
                city=city,
                state=state,
                latitude=latitude,
                longitude=longitude,
                is_online=is_online,
                price_cents=price_cents,
                currency=currency,
                is_free=is_free,
                image_url=image_url,
                experience_type=experience_type,
            )

        except Exception as e:
            print(f"    Error parsing Fever event: {e}")
            return None

    def _extract_event_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract event ID from Fever URL.

        Fever URLs: https://feverup.com/m/{event_id}

        Args:
            url: Event URL

        Returns:
            Event ID or None
        """
        try:
            # Pattern: /m/{id}
            match = re.search(r'/m/(\d+)', url)
            if match:
                return f"fever-{match.group(1)}"

        except Exception:
            pass

        return None

    def _infer_experience_type(self, title: str, description: str) -> Optional[str]:
        """
        Infer experience type from title and description.

        Args:
            title: Event title
            description: Event description

        Returns:
            Experience type string or None
        """
        # Combine title and description for analysis
        text = (title + ' ' + (description or '')).lower()

        # Keywords for different experience types
        if any(keyword in text for keyword in ['candlelight', 'concert', 'symphony', 'orchestra', 'music', 'jazz', 'classical']):
            return 'concert'
        elif any(keyword in text for keyword in ['magic', 'magician', 'illusion']):
            return 'magic'
        elif any(keyword in text for keyword in ['comedy', 'comedian', 'stand-up', 'improv']):
            return 'comedy'
        elif any(keyword in text for keyword in ['cooking', 'culinary', 'chef', 'food', 'cuisine', 'recipe']):
            return 'cooking'
        elif any(keyword in text for keyword in ['theater', 'theatre', 'play', 'musical', 'performance', 'show']):
            return 'theater'
        elif any(keyword in text for keyword in ['museum', 'exhibit', 'art', 'gallery', 'immersive']):
            return 'art'
        elif any(keyword in text for keyword in ['workshop', 'class', 'lesson', 'training']):
            return 'workshop'
        elif any(keyword in text for keyword in ['tour', 'walking', 'sightseeing']):
            return 'tour'
        else:
            return 'event'
