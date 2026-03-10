"""Shared runtime for Python-based source actors under src/apify."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from playwright.sync_api import sync_playwright

from events_agent.models.event import Event, EventSource


@dataclass(frozen=True)
class LegacyActorConfig:
    """Configuration for a Python source actor backed by a legacy crawler."""

    source_name: str
    location_key: str = "location"
    default_location: str = "nyc"


def load_actor_input() -> dict[str, Any]:
    """Load actor input from Apify-style env vars or local storage fallback."""
    if raw_input := os.getenv("ACTOR_INPUT"):
        return json.loads(raw_input)

    input_path = os.getenv("ACTOR_INPUT_PATH")
    if input_path and Path(input_path).exists():
        return json.loads(Path(input_path).read_text())

    local_input = Path("storage/key_value_stores/default/INPUT.json")
    if local_input.exists():
        return json.loads(local_input.read_text())

    return {}


def actor_output_dir() -> Path:
    """Return the dataset output directory used by local actor runs."""
    root = Path(os.getenv("APIFY_LOCAL_STORAGE_DIR", "storage"))
    dataset_dir = root / "datasets" / "default"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    return dataset_dir


def event_to_actor_item(event: Event) -> dict[str, Any]:
    """Map normalized Event rows to the actor output contract."""
    return {
        "eventId": event.event_id,
        "source": event.source.value,
        "url": str(event.url),
        "title": event.title,
        "description": event.description,
        "startDatetime": event.start_datetime.isoformat(),
        "endDatetime": event.end_datetime.isoformat() if event.end_datetime else None,
        "locationName": event.location_name,
        "locationAddress": event.location_address,
        "city": event.city,
        "state": event.state,
        "isOnline": event.is_online,
        "attendeeCount": event.attendee_count,
        "capacity": event.capacity,
        "spotsRemaining": event.spots_remaining,
        "waitlist": event.waitlist,
        "registrationClosed": event.registration_closed,
        "priceCents": event.price_cents,
        "minPriceCents": event.min_price_cents,
        "maxPriceCents": event.max_price_cents,
        "currency": event.currency,
        "isFree": event.is_free,
        "organizerName": event.organizer_name,
        "organizerUrl": str(event.organizer_url) if event.organizer_url else None,
        "groupName": event.group_name,
        "imageUrl": event.image_url,
        "topics": event.topics,
        "experienceType": event.experience_type,
        "category": event.category,
        "tags": event.tags,
        "registrationUrl": event.registration_url,
        "sourceExtensions": event.source_extensions,
        "originalProvider": event.original_provider,
        "aggregatedFrom": event.aggregated_from,
        "shortUrl": event.short_url,
        "aggregatorDetailUrl": event.aggregator_detail_url,
        "crawledAt": event.crawled_at.isoformat(),
        "detailCrawled": event.detail_crawled,
    }


def actor_item_to_event(item: dict[str, Any]) -> Event:
    """Map an actor dataset item or normalized JSON payload back to an Event."""
    field_map = {
        "eventId": "event_id",
        "startDatetime": "start_datetime",
        "endDatetime": "end_datetime",
        "locationName": "location_name",
        "locationAddress": "location_address",
        "isOnline": "is_online",
        "attendeeCount": "attendee_count",
        "spotsRemaining": "spots_remaining",
        "registrationClosed": "registration_closed",
        "priceCents": "price_cents",
        "minPriceCents": "min_price_cents",
        "maxPriceCents": "max_price_cents",
        "isFree": "is_free",
        "organizerName": "organizer_name",
        "organizerUrl": "organizer_url",
        "hostName": "host_name",
        "hostBio": "host_bio",
        "groupName": "group_name",
        "groupRating": "group_rating",
        "groupReviewCount": "group_review_count",
        "aiSummary": "ai_summary",
        "imageUrl": "image_url",
        "experienceType": "experience_type",
        "chefName": "chef_name",
        "chefRating": "chef_rating",
        "chefBio": "chef_bio",
        "skillLevel": "skill_level",
        "cuisineType": "cuisine_type",
        "performerNames": "performer_names",
        "durationMinutes": "duration_minutes",
        "reviewCount": "review_count",
        "feeAmount": "fee_amount",
        "feeRequired": "fee_required",
        "paymentMethods": "payment_methods",
        "registrationUrl": "registration_url",
        "sourceExtensions": "source_extensions",
        "originalProvider": "original_provider",
        "aggregatedFrom": "aggregated_from",
        "shortUrl": "short_url",
        "aggregatorDetailUrl": "aggregator_detail_url",
        "crawledAt": "crawled_at",
        "detailCrawled": "detail_crawled",
    }
    event_payload = {
        field_map.get(key, key): value
        for key, value in item.items()
    }

    source = event_payload.get("source")
    if isinstance(source, str):
        event_payload["source"] = EventSource(source)

    return Event(**event_payload)


def actor_items_to_events(items: Iterable[dict[str, Any]]) -> list[Event]:
    """Convert actor dataset items into normalized Event rows."""
    return [actor_item_to_event(item) for item in items]


def load_events_from_json_data(data: Any) -> list[Event]:
    """Load normalized Events from actor dataset JSON or raw event JSON."""
    if isinstance(data, dict):
        items = data.get("events", data.get("items"))
        if items is None:
            raise ValueError("Expected top-level 'events' or 'items' key in JSON object")
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("Expected JSON array or object containing event items")

    return actor_items_to_events(items)


def write_dataset_items(items: list[dict[str, Any]]) -> Path:
    """Persist actor dataset items in Apify local storage format."""
    dataset_dir = actor_output_dir()
    for index, item in enumerate(items, start=1):
        (dataset_dir / f"{index:09d}.json").write_text(json.dumps(item, indent=2, default=str))
    return dataset_dir


def run_legacy_source_actor(
    config: LegacyActorConfig,
    crawler_factory: Callable[[dict[str, Any]], Any],
) -> int:
    """Shared main routine for actor entrypoints backed by legacy crawlers."""
    actor_input = load_actor_input()
    location = actor_input.get(config.location_key, config.default_location)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            crawler = crawler_factory(actor_input)
            events = crawler.crawl(browser, location)
        finally:
            browser.close()

    items = [event_to_actor_item(event) for event in events]
    dataset_dir = write_dataset_items(items)
    print(f"{config.source_name}: wrote {len(items)} items to {dataset_dir}")
    return 0
