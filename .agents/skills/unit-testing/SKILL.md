---
name: unit-testing
description: Write unit tests for main classes added to the events-agent project. Use when adding tests for new crawlers, repositories, data modules, or any main class. Follows pytest conventions and project test patterns.
---

# Unit Testing for Events Agent

## When to Use

Apply this skill when:
- Adding unit tests for new crawlers (Jazz Near You, Songkick, TimeOut, DoNYC, etc.)
- Adding unit tests for new data modules (jazz_venues, seasonal_events)
- Adding unit tests for new repositories, filters, or utilities
- User asks to "add tests", "write unit tests", or "ensure test coverage"

## Test Structure

```
tests/
├── unit/           # Fast, isolated tests (mock external deps)
│   ├── test_models.py
│   ├── test_date_utils.py
│   ├── test_jazz_venues.py
│   ├── test_seasonal_events.py
│   └── ...
└── integration/    # Tests with mocked pages or real requests
    ├── test_crawlers.py
    ├── test_new_crawlers.py
    ├── test_jazz_and_timeout_crawlers.py
    └── ...
```

- **Unit tests**: Logic, parsing, pure functions. No browser, no network.
- **Integration tests**: Crawler extraction with mocked pages; real requests marked `@pytest.mark.integration`.

## Crawler Test Pattern

For each new crawler, add tests for:

1. **URL construction**: `test_*_crawler_get_events_url()`
2. **ID generation**: `test_*_crawler_generate_event_id*()` (if applicable)
3. **Parse methods**: `test_*_crawler_parse_*()` with BeautifulSoup HTML fixtures
4. **Extraction**: `test_*_crawler_extract_events_from_page()` with mocked page

### Crawler Test Template

```python
def test_mycrawler_get_events_url():
    """Test MyCrawler URL construction."""
    crawler = MyCrawler()
    url = crawler.get_events_url("nyc")
    assert url == "https://expected-url.com/nyc"

def test_mycrawler_parse_event():
    """Test MyCrawler event parsing from HTML."""
    crawler = MyCrawler()
    html = '''
    <div class="event-item">
        <h3 class="title">Event Title</h3>
        <a href="/events/123">Link</a>
        <span class="venue">Venue Name</span>
        <time class="date">2026-02-15T19:00:00</time>
    </div>
    '''
    soup = BeautifulSoup(html, "html.parser")
    item = soup.find("div", class_="event-item")
    event = crawler._parse_event_item(item, "https://base-url.com")
    assert event is not None
    assert event.title == "Event Title"
    assert event.source == EventSource.MYSOURCE

def test_mycrawler_extract_events_from_page():
    """Test MyCrawler extraction with mocked page."""
    crawler = MyCrawler()
    mock_page = Mock()
    mock_page.url = "https://base-url.com"
    mock_page.content.return_value = "<html>...</html>"
    mock_page.wait_for_selector = Mock()
    events = crawler.extract_events_from_page(mock_page)
    assert len(events) >= 1
```

## Data Module Test Pattern

For reference data (jazz_venues, seasonal_events):

1. **Data presence**: List/dict is not empty
2. **Lookup functions**: `get_*` return correct values
3. **Edge cases**: Empty input, not found, case insensitivity
4. **Validation**: Returned objects have expected fields

## Mocking

- **Playwright Page**: `Mock()` with `content.return_value`, `wait_for_selector`, `evaluate`, `wait_for_timeout`
- **HTML fixtures**: Use BeautifulSoup to build elements for parse method tests
- **No real network**: Unit tests must not call `crawl()` with real browser unless marked `@pytest.mark.integration`

## Assertions

- Use `assert event.source == EventSource.X` for event source
- Use `assert event.title`, `assert event.url` for required fields
- Use `assert event.genre == "jazz"` for domain-specific fields
- Use `assert event is None` for parse failures

## Integration Tests

Real-browser tests go in integration/ and use:

```python
@pytest.mark.integration
def test_mycrawler_real_request():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        crawler = MyCrawler()
        try:
            events = crawler.crawl(browser, "nyc")
            if events:
                assert all(e.source == EventSource.MYSOURCE for e in events)
        finally:
            browser.close()
```

Run with: `pytest -m integration` (excludes by default)

## Existing Examples

- **Crawlers**: `tests/integration/test_new_crawlers.py` (Fever, Cozymeal, Eventbrite)
- **Crawlers**: `tests/integration/test_jazz_and_timeout_crawlers.py` (Jazz Near You, Songkick, TimeOut, DoNYC)
- **Data modules**: `tests/unit/test_jazz_venues.py`, `tests/unit/test_seasonal_events.py`
- **Utils**: `tests/unit/test_date_utils.py`

## Checklist for New Class Tests

- [ ] URL/getter methods tested
- [ ] Parse/transform methods tested with fixtures
- [ ] Extraction tested with mocked page
- [ ] Edge cases: None, empty, invalid input
- [ ] EventSource and key fields asserted
- [ ] Integration test stub if crawler does network I/O
