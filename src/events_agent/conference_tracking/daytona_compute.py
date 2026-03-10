"""Parser for Daytona Compute conference agenda pages."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from events_agent.models.conference import ConferenceAgendaItem, ConferenceWatchSource


TIME_RANGE_RE = re.compile(r"^\d{2}:\d{2}\s*[AP]M\s*-\s*\d{2}:\d{2}\s*[AP]M$")
ROLE_KEYWORDS = (
    "founder",
    "co-founder",
    "cofounder",
    "ceo",
    "cto",
    "partner",
    "investor",
    "president",
    "head",
    "engineer",
    "director",
    "analyst",
    "operator",
)
NOISE_TOKENS = {"~", "location", "tickets", "get tickets", "sponsors"}


@dataclass
class ParsedSession:
    """Intermediate parsed session before conversion to Pydantic models."""

    title: str
    time_range: str
    speaker_names: list[str]
    company_names: list[str]
    description: str | None = None


class DaytonaComputeCrawler:
    """Extract agenda items from Daytona's conference landing page."""

    conference_slug = "daytona-compute"
    conference_name = "Compute Conference by Daytona"
    source = "daytona"
    source_url = "https://compute.daytona.io/"
    venue_name = "Chase Center"
    city = "San Francisco"
    state = "CA"
    timezone = ZoneInfo("America/Los_Angeles")
    agenda_date = date(2026, 3, 9)

    def fetch_html(self) -> str:
        request = Request(
            self.source_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
            },
        )
        with urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")

    def extract_agenda_items(self, html_content: str) -> list[ConferenceAgendaItem]:
        sessions = self._parse_sessions(self._extract_text_lines(html_content))
        return [self._to_agenda_item(session) for session in sessions]

    def get_default_watch_sources(self) -> list[ConferenceWatchSource]:
        return [
            ConferenceWatchSource(
                slug="daytona-compute",
                name="Daytona Compute landing page",
                base_url="https://compute.daytona.io/",
                discovery_url="https://compute.daytona.io/",
                city="San Francisco",
                state="CA",
                venue_name="Chase Center",
                source_type="conference-landing-page",
                discovery_notes="Conference microsite with agenda and venue details.",
            ),
            ConferenceWatchSource(
                slug="chase-center-events",
                name="Chase Center events calendar",
                base_url="https://www.chasecenter.com/events",
                discovery_url="https://www.chasecenter.com/events",
                city="San Francisco",
                state="CA",
                venue_name="Chase Center",
                source_type="venue-calendar",
                discovery_notes="Primary venue page for major arena-scale conferences and events.",
            ),
            ConferenceWatchSource(
                slug="luma-san-francisco",
                name="Luma San Francisco",
                base_url="https://lu.ma/sf",
                discovery_url="https://lu.ma/sf",
                city="San Francisco",
                state="CA",
                source_type="event-platform-city-hub",
                discovery_notes="High-signal source for startup and AI conferences in SF.",
            ),
            ConferenceWatchSource(
                slug="eventbrite-sf-conferences",
                name="Eventbrite SF conferences",
                base_url="https://www.eventbrite.com/d/ca--san-francisco/conferences/",
                discovery_url="https://www.eventbrite.com/d/ca--san-francisco/conferences/",
                city="San Francisco",
                state="CA",
                source_type="event-platform-category-hub",
                discovery_notes="Broad catch-all for ticketed conferences and summits.",
            ),
        ]

    def sessions_to_json(self, items: list[ConferenceAgendaItem]) -> str:
        return json.dumps([item.model_dump(mode="json") for item in items], indent=2)

    def _extract_text_lines(self, html_content: str) -> list[str]:
        text = re.sub(r"<script\b.*?</script>", " ", html_content, flags=re.S | re.I)
        text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = html.unescape(text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        deduped: list[str] = []
        for line in lines:
            if not deduped or deduped[-1] != line:
                deduped.append(line)
        return deduped

    def _parse_sessions(self, lines: list[str]) -> list[ParsedSession]:
        sessions: list[ParsedSession] = []
        time_indexes = [index for index, line in enumerate(lines) if TIME_RANGE_RE.fullmatch(line)]

        for position, start_index in enumerate(time_indexes):
            end_index = time_indexes[position + 1] if position + 1 < len(time_indexes) else len(lines)
            session = self._parse_session_block(lines[start_index:end_index])
            if session:
                sessions.append(session)

        return sessions

    def _parse_session_block(self, block: list[str]) -> ParsedSession | None:
        if len(block) < 2:
            return None

        time_range = re.sub(r"\s+", " ", block[0].replace("PM-", "PM -")).strip()
        title = block[1]
        payload = [value for value in block[2:] if value != "//"]

        metadata_payload: list[str] = []
        description = None
        for value in payload:
            if description is None and self._looks_like_description(value):
                description = value
                continue
            metadata_payload.append(value)

        speaker_names: list[str] = []
        company_names: list[str] = []
        for offset in range(0, len(metadata_payload), 3):
            chunk = metadata_payload[offset : offset + 3]
            if len(chunk) == 3 and self._looks_like_speaker_triplet(*chunk):
                speaker_names.append(chunk[0])
                company_names.append(chunk[2])

        return ParsedSession(
            title=title,
            time_range=time_range,
            speaker_names=speaker_names,
            company_names=company_names,
            description=description,
        )

    def _to_agenda_item(self, session: ParsedSession) -> ConferenceAgendaItem:
        start_text, end_text = session.time_range.split(" - ", maxsplit=1)
        session_date = self._agenda_date_for_session(session)
        return ConferenceAgendaItem(
            conference_slug=self.conference_slug,
            conference_name=self.conference_name,
            source=self.source,
            source_url=self.source_url,
            agenda_date=session_date,
            start_datetime=self._combine_date_and_time(session_date, start_text),
            end_datetime=self._combine_date_and_time(session_date, end_text),
            title=session.title,
            speaker_names=session.speaker_names,
            company_names=session.company_names,
            description=session.description,
            venue_name=self.venue_name,
            city=self.city,
            state=self.state,
        )

    def _combine_date_and_time(self, session_date: date, value: str) -> datetime:
        parsed_time = datetime.strptime(value, "%I:%M %p").time()
        return datetime.combine(session_date, parsed_time, self.timezone)

    def _agenda_date_for_session(self, session: ParsedSession) -> date:
        lowered_title = session.title.lower()
        if (
            session.time_range.startswith("05:00 PM")
            and ("badge pickup" in lowered_title or "opening reception" in lowered_title)
        ):
            return self.agenda_date - timedelta(days=1)
        return self.agenda_date

    def _looks_like_description(self, value: str) -> bool:
        lowered = value.lower()
        return len(value) > 80 or ". " in value or "we explore" in lowered

    def _looks_like_speaker_triplet(self, name: str, role: str, company: str) -> bool:
        return (
            self._looks_like_name(name)
            and self._looks_like_role(role)
            and self._looks_like_company(company)
        )

    def _looks_like_name(self, value: str) -> bool:
        if any(char.isdigit() for char in value):
            return False
        if value.lower() in NOISE_TOKENS:
            return False
        words = value.replace(".", "").split()
        if not 2 <= len(words) <= 5:
            return False
        return all(word[:1].isupper() or "'" in word for word in words)

    def _looks_like_role(self, value: str) -> bool:
        lowered = value.lower()
        return any(re.search(rf"\b{re.escape(keyword)}\b", lowered) for keyword in ROLE_KEYWORDS)

    def _looks_like_company(self, value: str) -> bool:
        lowered = value.lower()
        if lowered in NOISE_TOKENS:
            return False
        if len(value) == 1 or len(value) > 60:
            return False
        if any(char.isdigit() for char in value) and "$" in value:
            return False
        return not self._looks_like_role(value)
