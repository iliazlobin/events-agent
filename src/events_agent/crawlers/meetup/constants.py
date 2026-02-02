"""Constants for Meetup crawler."""

# Scrolling configuration
DEFAULT_SCROLL_WAIT_MS = 2500
MAX_SCROLL_ATTEMPTS = 30
PAGE_LOAD_WAIT_MS = 3000

# Rate limiting
DEFAULT_RATE_LIMIT_SECONDS = 2.0

# Event limits
DEFAULT_MAX_EVENTS_TOTAL = 100
DEFAULT_MAX_EVENTS_PER_DAY = 50

# Distance options
DEFAULT_DISTANCE_MILES = 10

# Event types
EVENT_TYPE_IN_PERSON = "inPerson"
EVENT_TYPE_ONLINE = "online"
EVENT_TYPE_ALL = "all"
