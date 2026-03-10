"""Actor entrypoint for Eventbrite."""

from events_agent.actor_runtime import LegacyActorConfig, run_legacy_source_actor
from events_agent.legacy_crawlers.eventbrite_crawler import EventbriteCrawler


def build_crawler(actor_input: dict):
    return EventbriteCrawler(
        rate_limit_seconds=actor_input.get("rateLimitSeconds", 1.0),
        max_events=actor_input.get("maxItems", 150),
        max_pages=actor_input.get("maxPages", 6),
    )


def main() -> int:
    return run_legacy_source_actor(
        LegacyActorConfig(source_name="eventbrite", default_location="nyc"),
        build_crawler,
    )


if __name__ == "__main__":
    raise SystemExit(main())
