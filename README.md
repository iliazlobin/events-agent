# Events Agent

Web crawler for collecting event data from Luma.com and Meetup.com, with filtering for NYC events in the current and next week.

## Features

- Crawls events from Luma.com and Meetup.com using Playwright
- Filters events by location (NYC area)
- Filters events by date range (current + next week)
- Structured data output with Pydantic validation
- Comprehensive test suite with unit and integration tests

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -e .

# Install Playwright browsers
playwright install chromium
```

## Usage

```bash
# Run the crawler
events-crawler

# Or with Python module
python -m events_agent.main
```

Output is saved to `events_output.json`.

## Testing

```bash
# Run unit tests only
pytest tests/unit/

# Run all tests including integration tests
pytest

# Run with coverage
pytest --cov=events_agent
```

## Architecture

- **Models**: Pydantic models for data validation (`models/event.py`)
- **Crawlers**: Abstract base class + Luma/Meetup implementations (`crawlers/`)
- **Filters**: Date and location filtering logic (`filters/`)
- **Utils**: Helper functions for dates, rate limiting (`utils/`)

## Project Structure

```
events-agent/
├── src/events_agent/
│   ├── models/          # Data models
│   ├── crawlers/        # Web crawlers
│   ├── filters/         # Filtering logic
│   ├── utils/           # Utilities
│   └── main.py          # CLI entry point
├── tests/
│   ├── fixtures/        # HTML samples
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
└── pyproject.toml       # Dependencies
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with verbose output
pytest -v
```
