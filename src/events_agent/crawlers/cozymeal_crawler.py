"""Cozymeal (cozymeal.com) cooking class crawler."""

from typing import List, Optional
import json
import re
import time
from playwright.sync_api import Page, Browser
from events_agent.crawlers.base import BaseCrawler
from events_agent.models.event import Event, EventSource
from events_agent.utils.date_utils import parse_iso_datetime


class CozymealCrawler(BaseCrawler):
    """
    Crawler for Cozymeal (cozymeal.com) cooking classes.

    Strategy:
    - Cozymeal lists cooking classes with FoodEvent Schema.org data on each page
    - Main page has ~12 classes, with pagination for more
    - Extract FoodEvent JSON-LD blocks from each page
    - Handle pagination to get more classes
    """

    def __init__(self, rate_limit_seconds: float = 2.0, max_events: int = 100, max_pages: int = 10):
        """
        Initialize Cozymeal crawler.

        Args:
            rate_limit_seconds: Minimum delay between requests
            max_events: Maximum number of events to crawl (default: 100)
            max_pages: Maximum number of pages to crawl (default: 10)
        """
        super().__init__(rate_limit_seconds)
        self.max_events = max_events
        self.max_pages = max_pages

    def get_events_url(self, location: str) -> str:
        """
        Get Cozymeal URL for a location.

        Args:
            location: Location identifier (e.g., 'nyc')

        Returns:
            Full Cozymeal URL
        """
        return f"https://www.cozymeal.com/{location}/cooking-classes"

    def crawl(self, browser: Browser, location: str) -> List[Event]:
        """
        Custom crawl method for Cozymeal (overrides BaseCrawler.crawl).

        Crawl multiple pages with pagination to collect cooking classes.

        Args:
            browser: Playwright Browser instance
            location: Location to search (e.g., 'nyc')

        Returns:
            List of Event objects
        """
        events = []

        try:
            base_url = self.get_events_url(location)
            page_num = 1

            while page_num <= self.max_pages and len(events) < self.max_events:
                try:
                    # Construct URL with page number
                    if page_num == 1:
                        url = base_url
                    else:
                        url = f"{base_url}?page={page_num}"

                    print(f"    Crawling page {page_num}: {url}")

                    # Load page
                    page = browser.new_page()

                    try:
                        page.set_extra_http_headers({
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        })

                        page.goto(url, wait_until='networkidle', timeout=60000)
                        page.wait_for_timeout(2000)

                        # Extract FoodEvent blocks from page
                        page_events = self.extract_events_from_page(page)

                        if not page_events:
                            print(f"      No events found on page {page_num}, stopping pagination")
                            break

                        print(f"      Found {len(page_events)} classes on page {page_num}")
                        events.extend(page_events)

                        # Check if we've reached max_events
                        if len(events) >= self.max_events:
                            print(f"      Reached max_events limit ({self.max_events})")
                            break

                    finally:
                        page.close()

                    # Rate limiting between pages
                    time.sleep(self.rate_limit_seconds)
                    page_num += 1

                except Exception as e:
                    print(f"      Error crawling page {page_num}: {e}")
                    break

            # Trim to max_events
            events = events[:self.max_events]
            print(f"    Extracted {len(events)} total cooking classes from Cozymeal")

        except Exception as e:
            print(f"    Error crawling Cozymeal: {e}")

        return events

    def extract_events_from_page(self, page: Page) -> List[Event]:
        """
        Extract cooking classes from a Cozymeal page.

        Args:
            page: Playwright Page object with cooking classes loaded

        Returns:
            List of Event objects
        """
        events = []

        try:
            # Get HTML content
            html_content = page.content()

            # Extract Schema.org JSON-LD blocks
            schema_blocks = self._extract_schema_org_blocks(html_content)

            # Parse FoodEvent blocks
            for block in schema_blocks:
                if isinstance(block, dict) and block.get('@type') == 'FoodEvent':
                    event = self._parse_cozymeal_class(block)
                    if event:
                        events.append(event)

        except Exception as e:
            print(f"      Error extracting events from page: {e}")

        return events

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

    def _parse_cozymeal_class(self, event_data: dict) -> Optional[Event]:
        """
        Transform Cozymeal FoodEvent to Event model.

        Cozymeal FoodEvent fields:
        - @type: FoodEvent
        - name: Class title
        - description: Class description
        - startDate, endDate: ISO 8601 timestamps
        - url: Class URL
        - image: Image URL
        - offers: {price, priceCurrency}
        - location: {name, address: {addressLocality}}
        - performer: {name, url} - The chef
        - organizer: {name} - Cozymeal company

        Args:
            event_data: Raw FoodEvent Schema.org data

        Returns:
            Event object or None if parsing fails
        """
        try:
            # Required fields
            title = event_data.get('name')
            start_date = event_data.get('startDate')
            url = event_data.get('url')

            if not all([title, start_date, url]):
                return None

            # Parse datetimes
            start_datetime = parse_iso_datetime(start_date)
            if not start_datetime:
                return None

            end_datetime = None
            if event_data.get('endDate'):
                end_datetime = parse_iso_datetime(event_data['endDate'])

            # Extract event ID from URL
            event_id = self._extract_event_id_from_url(url)
            if not event_id:
                # Fallback: use hash of title + start date
                event_id = f"cozymeal-{hash(title + start_date) % 1000000}"

            # Location info
            location_name = None
            city = None
            state = None

            location_data = event_data.get('location', {})
            if isinstance(location_data, dict):
                location_name = location_data.get('name')

                # Address
                address_data = location_data.get('address', {})
                if isinstance(address_data, dict):
                    address_locality = address_data.get('addressLocality')
                    # addressLocality format: "City, ST" or "City"
                    if address_locality:
                        parts = address_locality.split(',')
                        if len(parts) >= 2:
                            city = parts[0].strip()
                            state = parts[1].strip()
                        else:
                            city = address_locality.strip()

            # Check if online
            is_online = False
            attendance_mode = event_data.get('eventAttendanceMode', '')
            if 'Online' in str(attendance_mode):
                is_online = True

            # Pricing
            price_cents = 0
            currency = 'USD'
            is_free = True

            offers = event_data.get('offers', {})
            if isinstance(offers, dict):
                price = offers.get('price')
                if price is not None:
                    try:
                        # Convert price to cents
                        price_float = float(price)
                        price_cents = int(price_float * 100)
                        is_free = (price_cents == 0)
                    except (ValueError, TypeError):
                        pass

                currency = offers.get('priceCurrency', 'USD')

            # Chef information (from performer field)
            chef_name = None
            chef_url = None

            performer = event_data.get('performer', {})
            if isinstance(performer, dict):
                chef_name = performer.get('name')
                chef_url = performer.get('url')

            # Organizer is always Cozymeal
            organizer_name = "Cozymeal"

            # Image
            image_url = event_data.get('image')

            # Infer cuisine type from title
            cuisine_type = self._infer_cuisine_type(title, event_data.get('description', ''))

            return Event(
                event_id=event_id,
                source=EventSource.COZYMEAL,
                url=url,
                title=title,
                description=event_data.get('description'),
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                location_name=location_name,
                city=city,
                state=state,
                is_online=is_online,
                price_cents=price_cents,
                currency=currency,
                is_free=is_free,
                organizer_name=organizer_name,
                image_url=image_url,
                experience_type="cooking",
                chef_name=chef_name,
                cuisine_type=cuisine_type,
            )

        except Exception as e:
            print(f"        Error parsing Cozymeal class: {e}")
            return None

    def _extract_event_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract event ID from Cozymeal URL.

        Cozymeal URLs: https://www.cozymeal.com/cooking-class/{class_id}/...

        Args:
            url: Class URL

        Returns:
            Event ID or None
        """
        try:
            # Pattern: /cooking-class/{id}/
            match = re.search(r'/cooking-class/(\d+)/', url)
            if match:
                return f"cozymeal-{match.group(1)}"

        except Exception:
            pass

        return None

    def _infer_cuisine_type(self, title: str, description: str) -> Optional[str]:
        """
        Infer cuisine type from title and description.

        Args:
            title: Class title
            description: Class description

        Returns:
            Cuisine type string or None
        """
        # Combine title and description for analysis
        text = (title + ' ' + (description or '')).lower()

        # Keywords for different cuisines
        if any(keyword in text for keyword in ['italian', 'pasta', 'pizza', 'risotto']):
            return 'Italian'
        elif any(keyword in text for keyword in ['french', 'croissant', 'macaron']):
            return 'French'
        elif any(keyword in text for keyword in ['japanese', 'sushi', 'ramen']):
            return 'Japanese'
        elif any(keyword in text for keyword in ['chinese', 'dim sum', 'dumpling']):
            return 'Chinese'
        elif any(keyword in text for keyword in ['mexican', 'taco', 'burrito']):
            return 'Mexican'
        elif any(keyword in text for keyword in ['indian', 'curry', 'tikka']):
            return 'Indian'
        elif any(keyword in text for keyword in ['thai', 'pad thai']):
            return 'Thai'
        elif any(keyword in text for keyword in ['greek', 'mediterranean']):
            return 'Greek/Mediterranean'
        elif any(keyword in text for keyword in ['spanish', 'paella', 'tapas']):
            return 'Spanish'
        elif any(keyword in text for keyword in ['vegan', 'vegetarian']):
            return 'Vegan/Vegetarian'
        else:
            return 'Various'
