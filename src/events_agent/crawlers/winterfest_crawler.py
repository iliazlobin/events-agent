"""Tahoe SnowFest (Winterfest) event crawler."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from playwright.sync_api import Page

from events_agent.crawlers.base import BaseCrawler
from events_agent.models.event import Event, EventSource
from events_agent.utils.date_utils import parse_iso_datetime


class WinterfestCrawler(BaseCrawler):
    """Crawler for Tahoe SnowFest events page.

    SnowFest uses Squarespace event-list markup on:
    https://www.tahoesnowfest.org/events

    Each event block contains a Google Calendar export link with a `dates`
    parameter in UTC (`YYYYMMDDTHHMMSSZ/YYYYMMDDTHHMMSSZ`) and a `location`
    parameter. This is the most stable source for start/end and address data.
    """

    BASE_URL = "https://www.tahoesnowfest.org"

    def get_events_url(self, location: str = "tahoe") -> str:
        """Return SnowFest events URL.

        `location` is accepted for compatibility with `BaseCrawler`.
        """
        _ = location
        return f"{self.BASE_URL}/events"

    def extract_events_from_page(self, page: Page) -> List[Event]:
        """Extract SnowFest events from Squarespace event list markup."""
        events: List[Event] = []
        seen_ids: set[str] = set()

        try:
            page.wait_for_selector("article.eventlist-event", timeout=30000)
        except Exception:
            # Continue with available content even if selector wait times out.
            pass

        payloads = page.evaluate(
            """() => {
              const cards = Array.from(document.querySelectorAll("article.eventlist-event"));
              return cards.map((card) => {
                const titleLink = card.querySelector("h1.eventlist-title a.eventlist-title-link");
                const gcalLink = card.querySelector("a.eventlist-meta-export-google");
                const excerpt = card.querySelector("div.eventlist-excerpt");
                const img = card.querySelector("a.eventlist-column-thumbnail img");
                const eventDate = card.querySelector("time.event-date");
                const locationNode = card.querySelector("li.eventlist-meta-address");
                return {
                  title: titleLink?.textContent?.trim() || null,
                  href: titleLink?.getAttribute("href") || null,
                  gcalHref: gcalLink?.getAttribute("href") || null,
                  description: excerpt?.textContent?.trim() || null,
                  imageUrl: img?.getAttribute("src") || img?.getAttribute("data-src") || null,
                  eventDate: eventDate?.getAttribute("datetime") || null,
                  locationName: locationNode ? locationNode.childNodes[0]?.textContent?.trim() || null : null
                };
              });
            }"""
        )

        for payload in payloads:
            event = self._parse_event_payload(payload)
            if not event:
                continue
            if event.event_id in seen_ids:
                continue
            seen_ids.add(event.event_id)
            events.append(event)

        return events

    def _parse_event_payload(self, payload: dict) -> Optional[Event]:
        """Parse one extracted event payload into Event."""
        try:
            title = payload.get("title")
            href = payload.get("href")
            if not title or not href:
                return None

            url = urljoin(self.BASE_URL, href)
            slug = href.rstrip("/").split("/")[-1] if "/" in href else href
            event_id = f"winterfest-{slug}" if slug else self._hash_event_id(url)

            gcal_href = payload.get("gcalHref") or ""

            start_dt, end_dt = self._extract_datetimes_from_gcal(gcal_href)
            if not start_dt:
                # Fallback to page-level date if gcal metadata is missing.
                start_dt = self._extract_start_from_event_date(payload.get("eventDate"))
            if not start_dt:
                return None

            location_name = payload.get("locationName")
            location_param = self._extract_gcal_location(gcal_href)

            location_address = location_param
            city, state = self._parse_city_state(location_param)

            description = payload.get("description")
            if description == title:
                description = None

            image_url = payload.get("imageUrl")

            return Event(
                event_id=event_id,
                source=EventSource.WINTERFEST,
                url=url,
                title=title,
                description=description,
                start_datetime=start_dt,
                end_datetime=end_dt,
                location_name=location_name,
                location_address=location_address,
                city=city,
                state=state,
                is_online=False,
                image_url=image_url,
                category="winter festival",
                tags=["snowfest", "winterfest", "tahoe"],
            )
        except Exception:
            return None

    def _extract_datetimes_from_gcal(self, gcal_href: str) -> tuple[Optional[datetime], Optional[datetime]]:
        if not gcal_href:
            return None, None

        parsed = urlparse(gcal_href)
        query = parse_qs(parsed.query)
        dates = query.get("dates", [""])[0]
        if not dates or "/" not in dates:
            return None, None

        raw_start, raw_end = dates.split("/", 1)
        start_dt = parse_iso_datetime(self._google_utc_to_iso(raw_start))
        end_dt = parse_iso_datetime(self._google_utc_to_iso(raw_end)) if raw_end else None
        return start_dt, end_dt

    @staticmethod
    def _google_utc_to_iso(value: str) -> str:
        # Google calendar export datetime: YYYYMMDDTHHMMSSZ
        if re.fullmatch(r"\d{8}T\d{6}Z", value):
            return (
                f"{value[0:4]}-{value[4:6]}-{value[6:8]}"
                f"T{value[9:11]}:{value[11:13]}:{value[13:15]}Z"
            )
        return value

    def _extract_start_from_event_date(self, date_value: Optional[str]) -> Optional[datetime]:
        if not date_value:
            return None
        # date_value typically YYYY-MM-DD; default to midnight UTC.
        return parse_iso_datetime(f"{date_value}T00:00:00Z")

    def _extract_gcal_location(self, gcal_href: str) -> Optional[str]:
        if not gcal_href:
            return None
        query = parse_qs(urlparse(gcal_href).query)
        raw_location = query.get("location", [""])[0]
        if not raw_location:
            return None
        return unquote(raw_location).strip()

    @staticmethod
    def _parse_city_state(address: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not address:
            return None, None

        # Typical format:
        # "925 Country club, Tahoe City, CA, 96145, United States"
        parts = [p.strip() for p in address.split(",") if p.strip()]
        city = parts[1] if len(parts) >= 2 else None

        state = None
        for part in parts:
            m = re.fullmatch(r"[A-Z]{2}", part)
            if m:
                state = part
                break
        return city, state

    @staticmethod
    def _hash_event_id(url: str) -> str:
        return f"winterfest-{hashlib.md5(url.encode()).hexdigest()[:12]}"
