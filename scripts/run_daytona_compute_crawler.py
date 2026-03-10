#!/usr/bin/env python3
"""Fetch and persist Daytona Compute agenda plus discovery sources."""

from pathlib import Path

from events_agent.conference_tracking.daytona_compute import DaytonaComputeCrawler
from events_agent.database.connection import DatabaseConnection
from events_agent.database.schema import SchemaManager
from events_agent.repositories.conference_repository import SQLiteConferenceRepository


def main() -> None:
    crawler = DaytonaComputeCrawler()
    html_content = crawler.fetch_html()
    agenda_items = crawler.extract_agenda_items(html_content)

    db = DatabaseConnection("data/events.db")
    schema = SchemaManager(db)
    schema.initialize_schema()
    repository = SQLiteConferenceRepository(db)

    repository.upsert_watch_sources(crawler.get_default_watch_sources())
    repository.replace_agenda_items(crawler.conference_slug, agenda_items)

    output_path = Path("data/raw/daytona_compute_agenda_20260309.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(crawler.sessions_to_json(agenda_items))

    print(f"Stored {len(agenda_items)} agenda items in data/events.db")
    print(f"Wrote raw snapshot to {output_path}")
    print("Agenda:")
    for item in agenda_items:
        speakers = ", ".join(item.speaker_names) if item.speaker_names else "TBD"
        print(f"  {item.start_datetime.strftime('%I:%M %p')} - {item.title} [{speakers}]")


if __name__ == "__main__":
    main()
