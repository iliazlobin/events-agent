"""Actor entrypoint for Fever."""

from events_agent.actor_runtime import LegacyActorConfig, run_legacy_source_actor
from events_agent.legacy_crawlers.fever_crawler import FeverCrawler


def build_crawler(actor_input: dict):
    return FeverCrawler(
        rate_limit_seconds=actor_input.get("rateLimitSeconds", 2.0),
        max_events=actor_input.get("maxItems", 100),
    )


def main() -> int:
    return run_legacy_source_actor(
        LegacyActorConfig(source_name="fever", default_location="nyc"),
        build_crawler,
    )


if __name__ == "__main__":
    raise SystemExit(main())
