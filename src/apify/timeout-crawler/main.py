"""Actor entrypoint for TimeOut."""

from events_agent.actor_runtime import LegacyActorConfig, run_legacy_source_actor
from events_agent.legacy_crawlers.timeout_crawler import TimeOutNYCCrawler


def build_crawler(actor_input: dict):
    return TimeOutNYCCrawler(
        category=actor_input.get("category", "events-calendar"),
        rate_limit_seconds=actor_input.get("rateLimitSeconds", 2.0),
    )


def main() -> int:
    return run_legacy_source_actor(
        LegacyActorConfig(source_name="timeout", default_location="newyork"),
        build_crawler,
    )


if __name__ == "__main__":
    raise SystemExit(main())
