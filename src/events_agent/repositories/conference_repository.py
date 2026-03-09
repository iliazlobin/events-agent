"""SQLite repository for conference agendas and watch-source registry."""

import json
from typing import List

from events_agent.database.connection import DatabaseConnection
from events_agent.models.conference import ConferenceAgendaItem, ConferenceWatchSource


class SQLiteConferenceRepository:
    """Persists conference agenda items and discovery sources in SQLite."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def upsert_watch_sources(self, sources: List[ConferenceWatchSource]) -> int:
        """Insert or update watched conference source definitions."""
        if not sources:
            return 0

        self.db.execute_many(
            """
            INSERT INTO conference_watch_sources (
                slug, name, base_url, discovery_url, city, state, venue_name,
                source_type, discovery_notes, is_active, last_checked_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                name = excluded.name,
                base_url = excluded.base_url,
                discovery_url = excluded.discovery_url,
                city = excluded.city,
                state = excluded.state,
                venue_name = excluded.venue_name,
                source_type = excluded.source_type,
                discovery_notes = excluded.discovery_notes,
                is_active = excluded.is_active,
                last_checked_at = excluded.last_checked_at
            """,
            [
                (
                    source.slug,
                    source.name,
                    str(source.base_url),
                    str(source.discovery_url) if source.discovery_url else None,
                    source.city,
                    source.state,
                    source.venue_name,
                    source.source_type,
                    source.discovery_notes,
                    1 if source.is_active else 0,
                    source.last_checked_at.isoformat() if source.last_checked_at else None,
                    source.created_at.isoformat(),
                )
                for source in sources
            ],
        )
        self.db.commit()
        return len(sources)

    def list_watch_sources(self, active_only: bool = True) -> List[ConferenceWatchSource]:
        """List known conference discovery sources."""
        sql = "SELECT * FROM conference_watch_sources"
        params: tuple[int, ...] | tuple[()] = ()
        if active_only:
            sql += " WHERE is_active = ?"
            params = (1,)
        sql += " ORDER BY city, name"

        rows = self.db.execute(sql, params).fetchall()
        return [
            ConferenceWatchSource(
                slug=row["slug"],
                name=row["name"],
                base_url=row["base_url"],
                discovery_url=row["discovery_url"],
                city=row["city"],
                state=row["state"],
                venue_name=row["venue_name"],
                source_type=row["source_type"],
                discovery_notes=row["discovery_notes"],
                is_active=bool(row["is_active"]),
                last_checked_at=row["last_checked_at"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def upsert_agenda_items(self, items: List[ConferenceAgendaItem]) -> int:
        """Insert or update conference agenda items."""
        if not items:
            return 0

        self.db.execute_many(
            """
            INSERT INTO conference_agenda_items (
                conference_slug, conference_name, source, source_url, agenda_date,
                start_datetime, end_datetime, title, speaker_names, company_names,
                description, venue_name, city, state, crawled_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(conference_slug, start_datetime, title) DO UPDATE SET
                conference_name = excluded.conference_name,
                source = excluded.source,
                source_url = excluded.source_url,
                agenda_date = excluded.agenda_date,
                end_datetime = excluded.end_datetime,
                speaker_names = excluded.speaker_names,
                company_names = excluded.company_names,
                description = excluded.description,
                venue_name = excluded.venue_name,
                city = excluded.city,
                state = excluded.state,
                crawled_at = excluded.crawled_at
            """,
            [self._agenda_item_to_tuple(item) for item in items],
        )
        self.db.commit()
        return len(items)

    def replace_agenda_items(
        self, conference_slug: str, items: List[ConferenceAgendaItem]
    ) -> int:
        """Replace all agenda rows for a conference with a fresh scrape."""
        self.db.execute(
            "DELETE FROM conference_agenda_items WHERE conference_slug = ?",
            (conference_slug,),
        )
        self.db.commit()
        return self.upsert_agenda_items(items)

    def find_agenda_by_slug(self, conference_slug: str) -> List[ConferenceAgendaItem]:
        """Load agenda rows for a conference."""
        rows = self.db.execute(
            """
            SELECT * FROM conference_agenda_items
            WHERE conference_slug = ?
            ORDER BY start_datetime
            """,
            (conference_slug,),
        ).fetchall()
        return [self._row_to_agenda_item(row) for row in rows]

    def _agenda_item_to_tuple(self, item: ConferenceAgendaItem) -> tuple:
        return (
            item.conference_slug,
            item.conference_name,
            item.source,
            str(item.source_url),
            item.agenda_date.isoformat(),
            item.start_datetime.isoformat(),
            item.end_datetime.isoformat(),
            item.title,
            json.dumps(item.speaker_names),
            json.dumps(item.company_names),
            item.description,
            item.venue_name,
            item.city,
            item.state,
            item.crawled_at.isoformat(),
        )

    def _row_to_agenda_item(self, row) -> ConferenceAgendaItem:
        return ConferenceAgendaItem(
            conference_slug=row["conference_slug"],
            conference_name=row["conference_name"],
            source=row["source"],
            source_url=row["source_url"],
            agenda_date=row["agenda_date"],
            start_datetime=row["start_datetime"],
            end_datetime=row["end_datetime"],
            title=row["title"],
            speaker_names=json.loads(row["speaker_names"]) if row["speaker_names"] else [],
            company_names=json.loads(row["company_names"]) if row["company_names"] else [],
            description=row["description"],
            venue_name=row["venue_name"],
            city=row["city"],
            state=row["state"],
            crawled_at=row["crawled_at"],
        )
