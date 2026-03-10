"""Eventbrite (eventbrite.com) event crawler."""

from typing import List, Optional
import re
from playwright.sync_api import Page, Browser
from events_agent.legacy_crawlers.base import BaseCrawler
from events_agent.models.event import Event, EventSource
from events_agent.utils.date_utils import parse_iso_datetime


class EventbriteCrawler(BaseCrawler):
    """
    Crawler for Eventbrite (eventbrite.com) events.

    Strategy:
    - Eventbrite embeds event data in window.__SERVER_DATA__.search_data.events
    - Paginate through pages (?page=N) to collect 100+ events within 5 min SLA
    """

    def __init__(
        self,
        rate_limit_seconds: float = 1.0,
        max_events: int = 150,
        max_pages: int = 6,
    ):
        """
        Initialize Eventbrite crawler.

        Args:
            rate_limit_seconds: Minimum delay between page requests
            max_events: Maximum number of events to crawl (default: 150)
            max_pages: Maximum pages to fetch for pagination (default: 6, ~20 events/page)
        """
        super().__init__(rate_limit_seconds)
        self.max_events = max_events
        self.max_pages = max_pages

    def crawl(self, browser: Browser, location: str) -> List[Event]:
        """
        Custom crawl with pagination to load 100+ events within 5 min SLA.

        Fetches multiple pages (?page=1, 2, ...) since each page has ~20 events.
        """
        import time as _time

        base_url = self.get_events_url(location)
        all_events: List[Event] = []
        seen_ids: set = set()

        for page_num in range(1, self.max_pages + 1):
            if len(all_events) >= self.max_events:
                break

            url = f"{base_url.rstrip('/')}/?page={page_num}" if page_num > 1 else base_url
            page = browser.new_page()

            try:
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })

                print(f"  Fetching page {page_num}: {url}")
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(2500)

                page_events = self.extract_events_from_page(page)
                new_count = 0
                for ev in page_events:
                    if ev.event_id not in seen_ids:
                        seen_ids.add(ev.event_id)
                        all_events.append(ev)
                        new_count += 1
                        if len(all_events) >= self.max_events:
                            break

                print(f"    Page {page_num}: {len(page_events)} events ({new_count} new), total {len(all_events)}")
                if len(page_events) == 0:
                    break

                _time.sleep(self.rate_limit_seconds)

            except Exception as e:
                print(f"  Error on page {page_num}: {e}")
            finally:
                page.close()

        return all_events[: self.max_events]

    def get_events_url(self, location: str) -> str:
        """
        Get Eventbrite URL for a location.

        Args:
            location: Location identifier (e.g., 'nyc', 'new-york')

        Returns:
            Full Eventbrite URL
        """
        # Eventbrite uses state codes in URL
        # For NYC, use "ny--new-york"
        if location.lower() in ['nyc', 'new-york']:
            location = 'ny--new-york'

        return f"https://www.eventbrite.com/d/{location}/all-events/"

    def extract_events_from_page(self, page: Page) -> List[Event]:
        """
        Extract events from Eventbrite page using __SERVER_DATA__.search_data.events.

        Eventbrite structure (2024+): search_data.events.results and promoted_results.

        Args:
            page: Playwright Page object

        Returns:
            List of Event objects
        """
        events = []

        try:
            # Extract from search_data.events (current Eventbrite structure)
            results = page.evaluate('''() => {
                const sd = window.__SERVER_DATA__?.search_data?.events;
                if (!sd) return { results: [], promoted: [] };
                return {
                    results: sd.results || [],
                    promoted: sd.promoted_results || []
                };
            }''')

            for event_data in results.get('results', []) + results.get('promoted', []):
                event = self._parse_eventbrite_event(event_data)
                if event:
                    events.append(event)

            if events:
                print(f"      Extracted {len(events)} events from Eventbrite")

        except Exception as e:
            print(f"      Error extracting Eventbrite events: {e}")

        return events

    def _parse_eventbrite_event(self, event_data: dict) -> Optional[Event]:
        """
        Transform Eventbrite event data to Event model.

        Eventbrite event fields from __SERVER_DATA__:
        - id or eventbrite_event_id: Event ID
        - name: Event title
        - summary: Event description
        - url: Event URL
        - start_date, start_time: Date and time
        - end_date, end_time: End date and time
        - timezone: Timezone string
        - primary_venue: {name, address: {city, region, latitude, longitude}}
        - is_online_event: Boolean
        - tags: [{display_name, prefix}]
        - image: {url}

        Args:
            event_data: Raw Eventbrite event data from __SERVER_DATA__

        Returns:
            Event object or None if parsing fails
        """
        try:
            # Required fields
            event_id = event_data.get('id') or event_data.get('eventbrite_event_id')
            title = event_data.get('name')
            start_date = event_data.get('start_date')
            start_time = event_data.get('start_time')
            url = event_data.get('url')

            if not all([event_id, title, start_date, url]):
                return None

            # Combine date and time
            # start_date format: "2026-02-13"
            # start_time format: "05:00" or None
            if start_time:
                datetime_str = f"{start_date}T{start_time}:00"
            else:
                datetime_str = f"{start_date}T00:00:00"

            # Add timezone if available
            timezone = event_data.get('timezone')
            if timezone:
                # Convert timezone to offset (simplified - assume EST for NYC)
                # This is a simplification - ideally would use pytz
                if 'America/New_York' in timezone:
                    datetime_str += "-05:00"  # EST
                else:
                    datetime_str += "Z"  # UTC fallback
            else:
                datetime_str += "Z"

            start_datetime = parse_iso_datetime(datetime_str)
            if not start_datetime:
                return None

            # End datetime
            end_datetime = None
            end_date = event_data.get('end_date')
            end_time = event_data.get('end_time')
            if end_date:
                if end_time:
                    end_datetime_str = f"{end_date}T{end_time}:00"
                else:
                    end_datetime_str = f"{end_date}T23:59:59"

                if timezone and 'America/New_York' in timezone:
                    end_datetime_str += "-05:00"
                else:
                    end_datetime_str += "Z"

                end_datetime = parse_iso_datetime(end_datetime_str)

            # Location info
            location_name = None
            location_address = None
            city = None
            state = None
            latitude = None
            longitude = None

            primary_venue = event_data.get('primary_venue', {})
            if isinstance(primary_venue, dict):
                location_name = primary_venue.get('name')

                address = primary_venue.get('address', {})
                if isinstance(address, dict):
                    location_address = address.get('address_1')
                    city = address.get('city')
                    state = address.get('region')

                    lat = address.get('latitude')
                    lon = address.get('longitude')
                    if lat:
                        try:
                            latitude = float(lat)
                        except (ValueError, TypeError):
                            pass
                    if lon:
                        try:
                            longitude = float(lon)
                        except (ValueError, TypeError):
                            pass

            # Online event flag
            is_online = event_data.get('is_online_event', False)

            # Image
            image_url = None
            image_data = event_data.get('image', {})
            if isinstance(image_data, dict):
                image_url = image_data.get('url')

            # Experience type from tags
            experience_type = self._infer_experience_type_from_tags(event_data.get('tags', []))

            # Category from tags
            category = None
            tags = event_data.get('tags', [])
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, dict) and tag.get('prefix') == 'EventbriteCategory':
                        category = tag.get('display_name')
                        break

            return Event(
                event_id=f"eventbrite-{event_id}",
                source=EventSource.EVENTBRITE,
                url=url,
                title=title,
                description=event_data.get('summary') or event_data.get('full_description'),
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                location_name=location_name,
                location_address=location_address,
                city=city,
                state=state,
                latitude=latitude,
                longitude=longitude,
                is_online=is_online,
                image_url=image_url,
                experience_type=experience_type,
                category=category,
                # Eventbrite doesn't provide price in search results
                is_free=False,  # Unknown, default to False
            )

        except Exception as e:
            print(f"        Error parsing Eventbrite event: {e}")
            return None

    def _infer_experience_type_from_tags(self, tags: list) -> Optional[str]:
        """
        Infer experience type from Eventbrite tags.

        Args:
            tags: List of tag objects

        Returns:
            Experience type string or None
        """
        if not isinstance(tags, list):
            return None

        # Collect all tag display names
        tag_names = []
        for tag in tags:
            if isinstance(tag, dict):
                display_name = tag.get('display_name', '').lower()
                if display_name:
                    tag_names.append(display_name)

        tag_text = ' '.join(tag_names)

        # Map to experience types
        if any(keyword in tag_text for keyword in ['music', 'concert', 'festival']):
            return 'concert'
        elif any(keyword in tag_text for keyword in ['comedy', 'stand-up']):
            return 'comedy'
        elif any(keyword in tag_text for keyword in ['food', 'drink', 'cooking', 'culinary']):
            return 'cooking'
        elif any(keyword in tag_text for keyword in ['theater', 'theatre', 'performing arts']):
            return 'theater'
        elif any(keyword in tag_text for keyword in ['party', 'social']):
            return 'party'
        elif any(keyword in tag_text for keyword in ['class', 'workshop', 'seminar']):
            return 'workshop'
        elif any(keyword in tag_text for keyword in ['sports', 'fitness']):
            return 'sports'
        else:
            return 'event'
