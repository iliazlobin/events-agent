"""Actor entrypoint for DoNYC."""

from events_agent.actor_runtime import LegacyActorConfig, run_legacy_source_actor
from events_agent.legacy_crawlers.timeout_crawler import DoNYCCrawler


def build_crawler(actor_input: dict):
    return DoNYCCrawler(
        rate_limit_seconds=actor_input.get("rateLimitSeconds", 2.0),
    )


def main() -> int:
    return run_legacy_source_actor(
        LegacyActorConfig(source_name="donyc", default_location="events"),
        build_crawler,
    )


if __name__ == "__main__":
    raise SystemExit(main())
