"""Town of Mammoth Lakes civic calendar crawler."""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.sync_api import Page

from events_agent.crawlers.base import BaseCrawler
from events_agent.models.event import Event, EventSource


class TownOfMammothCrawler(BaseCrawler):
    """Crawler for Town of Mammoth Lakes calendar events (CivicPlus)."""

    BASE_URL = "https://www.townofmammothlakes.ca.gov"

    def __init__(
        self,
        category_id: Optional[int] = None,
        max_events: int = 100,
        rate_limit_seconds: float = 1.0,
    ):
        super().__init__(rate_limit_seconds)
        self.category_id = category_id
        self.max_events = max_events

    def get_events_url(self, location: str = "mammoth") -> str:
        """Return calendar URL for a category.

        `location` is accepted for BaseCrawler compatibility.
        """
        _ = location
        if self.category_id is None:
            return f"{self.BASE_URL}/Calendar.aspx"
        return f"{self.BASE_URL}/Calendar.aspx?CID={self.category_id}"

    def extract_events_from_page(self, page: Page) -> List[Event]:
        """Extract event links from calendar page and parse detail pages."""
        events: List[Event] = []
        listing_url = page.url

        try:
            page.wait_for_selector('a[href*="Calendar.aspx?EID="]', timeout=20000)
        except Exception:
            pass

        links = page.evaluate(
            """() => {
              const anchors = Array.from(document.querySelectorAll('a[id^="eventTitle_"][href*="Calendar.aspx?EID="]'));
              return anchors.map((a) => ({
                title: a.textContent?.trim() || null,
                href: a.getAttribute('href') || null,
              }));
            }"""
        )

        seen_ids: set[str] = set()
        for link in links:
            if len(events) >= self.max_events:
                break

            event = self._fetch_and_parse_event(page, link)
            if not event:
                continue
            if event.event_id in seen_ids:
                continue
            seen_ids.add(event.event_id)
            events.append(event)

        try:
            page.goto(listing_url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            pass

        return events

    def _fetch_and_parse_event(self, page: Page, link: dict) -> Optional[Event]:
        """Open a calendar detail page and parse event fields."""
        href = (link or {}).get("href")
        if not href:
            return None

        detail_url = urljoin(self.BASE_URL, href)
        try:
            page.goto(detail_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(700)

            detail = page.evaluate(
                """() => {
                  const bodyText = document.body?.innerText || '';
                  const h = document.querySelector('h1, h2, .detailTitle, #ctl00_ContentPlaceHolder1_litName');
                  return {
                    bodyText,
                    title: h?.textContent?.trim() || null,
                  };
                }"""
            )

            return self._parse_event_payload(link, detail, detail_url)
        except Exception:
            return None

    def _parse_event_payload(self, listing: dict, detail: dict, detail_url: str) -> Optional[Event]:
        """Parse listing+detail payload into Event."""
        event_id = self._extract_eid(detail_url)
        if not event_id:
            return None

        title = self._first_non_empty(
            (detail or {}).get("title"),
            (listing or {}).get("title"),
        )
        if title and title.strip().lower() == "calendar":
            title = self._first_non_empty((listing or {}).get("title"), title)
        if not title:
            return None

        body = (detail or {}).get("bodyText") or ""
        date_text = self._extract_labeled_text(body, "Date")
        time_text = self._extract_labeled_text(body, "Time")
        location_name = self._extract_labeled_text(body, "Location")
        address = self._extract_labeled_text(body, "Address")

        start_datetime, end_datetime = self._parse_start_end(date_text, time_text)
        if not start_datetime:
            return None

        city, state = self._parse_city_state(address)
        if city is None:
            city = "Mammoth Lakes"
        if state is None:
            state = "CA"

        return Event(
            event_id=f"toml-{event_id}",
            source=EventSource.TOWNOFMAMMOTH,
            url=detail_url,
            title=title,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location_name=location_name,
            location_address=address,
            city=city,
            state=state,
            is_online=False,
            category="community",
            tags=["mammoth", "town-calendar"],
        )

    @staticmethod
    def _extract_eid(url: str) -> Optional[str]:
        query = parse_qs(urlparse(url).query)
        eid = query.get("EID", [None])[0]
        return str(eid) if eid else None

    @staticmethod
    def _extract_labeled_text(body: str, label: str) -> Optional[str]:
        # CivicPlus detail pages may render either:
        # 1) "Label: value"
        # 2) "Label:" on one line and value on the next line.
        lines = [ln.strip() for ln in body.splitlines() if ln and ln.strip()]
        target = f"{label.lower()}:"
        for i, line in enumerate(lines):
            if line.lower().startswith(target):
                remainder = line[len(target):].strip()
                if remainder:
                    return remainder
                if i + 1 < len(lines):
                    return lines[i + 1].strip() or None
                return None

        pattern = rf"{re.escape(label)}:\s*([^\n\r]+)"
        m = re.search(pattern, body, flags=re.IGNORECASE)
        if not m or not m.group(1):
            return None
        value = m.group(1).strip()
        return value if value else None

    def _parse_start_end(
        self,
        date_text: Optional[str],
        time_text: Optional[str],
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        if not date_text:
            return None, None

        event_date = self._parse_event_date(date_text)
        if not event_date:
            return None, None

        if not time_text:
            return datetime(event_date.year, event_date.month, event_date.day), None

        cleaned = (
            time_text.replace("\u2009", " ")
            .replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace(" to ", "-")
            .strip()
        )
        parts = [p.strip() for p in cleaned.split("-") if p.strip()]
        if not parts:
            return datetime(event_date.year, event_date.month, event_date.day), None

        start_dt = self._parse_time_on_date(event_date, parts[0])
        end_dt = self._parse_time_on_date(event_date, parts[1]) if len(parts) > 1 else None

        if not start_dt:
            return datetime(event_date.year, event_date.month, event_date.day), end_dt
        return start_dt, end_dt

    @staticmethod
    def _parse_event_date(date_text: str) -> Optional[datetime]:
        value = date_text.strip()
        formats = [
            "%A, %B %d, %Y",
            "%A, %b %d, %Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%m/%d/%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_time_on_date(event_date: datetime, time_text: str) -> Optional[datetime]:
        value = time_text.strip().upper().replace(".", "")
        for fmt in ("%I:%M %p", "%I %p"):
            try:
                t = datetime.strptime(value, fmt)
                return datetime(
                    event_date.year,
                    event_date.month,
                    event_date.day,
                    t.hour,
                    t.minute,
                )
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_city_state(address: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not address:
            return None, None

        parts = [p.strip() for p in address.split(",") if p.strip()]
        city = None
        state = None

        for i, part in enumerate(parts):
            if re.fullmatch(r"[A-Z]{2}", part):
                state = part
                city = parts[i - 1] if i > 0 else None
                break

        if not city:
            city_match = re.search(r"\b(Mammoth Lakes|Bishop|June Lake)\b", address, flags=re.IGNORECASE)
            if city_match:
                city = city_match.group(1).title()
        return city, state

    @staticmethod
    def _first_non_empty(*values: Optional[str]) -> Optional[str]:
        for value in values:
            if value and value.strip():
                return value.strip()
        return None
