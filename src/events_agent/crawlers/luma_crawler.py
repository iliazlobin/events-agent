"""Luma.com event crawler."""

from typing import List
import json
import re
from playwright.sync_api import Page
from events_agent.crawlers.base import BaseCrawler
from events_agent.models.event import Event, EventSource
from events_agent.utils.date_utils import parse_iso_datetime


class LumaCrawler(BaseCrawler):
    """
    Crawler for Luma.com events.

    Strategy:
    - Luma embeds event data in script tags with __NEXT_DATA__ or similar
    - Extract JSON from these script tags
    - Parse event objects and transform to Event model
    """

    def get_events_url(self, location: str) -> str:
        """
        Get Luma URL for a location.

        Args:
            location: Location identifier (e.g., 'nyc')

        Returns:
            Full Luma URL
        """
        # Luma uses location-based paths like /nyc, /sf, etc.
        return f"https://lu.ma/{location}"

    def extract_events_from_page(self, page: Page) -> List[Event]:
        """
        Extract events from Luma page.

        Process:
        1. Find <script> tags with embedded JSON data
        2. Look for __NEXT_DATA__ or other Next.js data structures
        3. Parse JSON to extract event objects
        4. Transform each event to Event model

        Args:
            page: Playwright Page object

        Returns:
            List of Event objects
        """
        events = []

        try:
            # Try to extract __NEXT_DATA__ which contains page props
            next_data = page.evaluate('''() => {
                const scriptTag = document.getElementById('__NEXT_DATA__');
                if (scriptTag) {
                    return JSON.parse(scriptTag.textContent);
                }
                return null;
            }''')

            if next_data:
                events = self._parse_next_data(next_data)

            # Fallback: Try to find event data in other script tags
            if not events:
                content = page.content()
                events = self._parse_script_tags(content)

        except Exception as e:
            print(f"    Error extracting Luma events: {e}")

        return events

    def _parse_next_data(self, next_data: dict) -> List[Event]:
        """
        Parse __NEXT_DATA__ structure from Next.js.

        Args:
            next_data: Parsed __NEXT_DATA__ JSON object

        Returns:
            List of Event objects
        """
        events = []

        try:
            # Navigate through Next.js data structure to find events
            # Common paths: props.pageProps.events or props.pageProps.initialData.events
            page_props = next_data.get('props', {}).get('pageProps', {})

            # Try different possible locations for events data
            events_data = (
                page_props.get('events') or
                page_props.get('initialData', {}).get('events') or
                page_props.get('calendar', {}).get('events') or
                []
            )

            for event_data in events_data:
                event = self._parse_luma_event(event_data)
                if event:
                    events.append(event)

        except Exception as e:
            print(f"    Error parsing Next.js data: {e}")

        return events

    def _parse_script_tags(self, html_content: str) -> List[Event]:
        """
        Fallback: Parse event data from script tags in HTML.

        Args:
            html_content: HTML page content

        Returns:
            List of Event objects
        """
        events = []

        try:
            # Find all script tags
            script_pattern = r'<script[^>]*>(.*?)</script>'
            scripts = re.findall(script_pattern, html_content, re.DOTALL)

            for script_content in scripts:
                # Look for JSON objects with event-like structure
                if 'api_id' in script_content and 'start_at' in script_content:
                    # Try to extract JSON arrays or objects
                    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                    matches = re.finditer(json_pattern, script_content)

                    for match in matches:
                        try:
                            obj = json.loads(match.group(0))
                            if isinstance(obj, dict) and 'api_id' in obj:
                                event = self._parse_luma_event(obj)
                                if event:
                                    events.append(event)
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            print(f"    Error parsing script tags: {e}")

        return events

    def _parse_luma_event(self, event_data: dict) -> Event | None:
        """
        Transform Luma event data to Event model.

        Luma event fields (common):
        - api_id: Event ID
        - name: Title
        - start_at, end_at: ISO 8601 timestamps
        - geo_address_info: {full_address, city, region, ...}
        - url: Event URL
        - description: Event description
        - cover_url: Image
        - hosts: [{name, ...}]

        Args:
            event_data: Raw Luma event data

        Returns:
            Event object or None if parsing fails
        """
        try:
            # Required fields
            event_id = event_data.get('api_id')
            title = event_data.get('name')
            start_at = event_data.get('start_at')

            if not all([event_id, title, start_at]):
                return None

            start_datetime = parse_iso_datetime(start_at)
            if not start_datetime:
                return None

            # Parse end datetime
            end_datetime = None
            if event_data.get('end_at'):
                end_datetime = parse_iso_datetime(event_data['end_at'])

            # Location info
            geo_info = event_data.get('geo_address_info', {}) or {}
            location_name = geo_info.get('venue_name')
            location_address = geo_info.get('full_address')
            city = geo_info.get('city')
            state = geo_info.get('region')

            # Check if online
            is_online = bool(event_data.get('meeting_url'))

            # Pricing
            ticket_info = event_data.get('ticket_info', {}) or {}
            price_info = ticket_info.get('price', {}) or {}
            price_cents = price_info.get('cents', 0)
            currency = price_info.get('currency', 'USD')

            # Organizer
            hosts = event_data.get('hosts', []) or []
            organizer_name = hosts[0].get('name') if hosts else None

            # Build URL - Luma's url field is just the slug, need to construct full URL
            url_slug = event_data.get('url') or event_id
            # If url_slug already starts with http, use it as-is, otherwise construct full URL
            if url_slug.startswith('http'):
                url = url_slug
            else:
                url = f"https://lu.ma/{url_slug}"

            return Event(
                event_id=event_id,
                source=EventSource.LUMA,
                url=url,
                title=title,
                description=event_data.get('description'),
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                location_name=location_name,
                location_address=location_address,
                city=city,
                state=state,
                is_online=is_online,
                spots_remaining=event_data.get('spots_remaining'),
                price_cents=price_cents,
                currency=currency,
                is_free=(price_cents == 0),
                organizer_name=organizer_name,
            )

        except Exception as e:
            print(f"    Error parsing Luma event: {e}")
            return None
