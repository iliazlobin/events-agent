# Distributed Crawler - High-Level Design

**Version:** 1.0
**Date:** February 13, 2026
**Project:** Events Agent - Distributed Architecture
**Status:** Draft

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [System Components](#system-components)
4. [Data Flow](#data-flow)
5. [Component Interactions](#component-interactions)
6. [Data Models](#data-models)
7. [API Specifications](#api-specifications)
8. [Deployment Architecture](#deployment-architecture)
9. [Failure Handling](#failure-handling)
10. [Scalability Considerations](#scalability-considerations)
11. [Migration Strategy](#migration-strategy)
12. [Monitoring and Observability](#monitoring-and-observability)

---

## Executive Summary

### Design Goals

1. **Scalability:** Support 50+ event sources with linear performance scaling
2. **Reliability:** 99.5% uptime with automatic failure recovery
3. **Simplicity:** Minimize operational complexity for small team
4. **Cost Efficiency:** Optimize infrastructure costs (<$200/month for Phase 2)
5. **Gradual Migration:** Phased approach from single-process to distributed

### Architecture Approach

**Phased Evolution:**
- **Phase 1:** Multi-process parallelization (0 infrastructure cost, 4x speedup)
- **Phase 2:** Queue-based distributed system with Redis (target architecture)
- **Phase 3:** Production-grade with Kafka + Kubernetes (future enhancement)

**Core Pattern:** Master-Worker with Message Queue
- Simple coordination model
- Proven scalability
- Easy to implement and debug
- Supports fault tolerance

### Key Technologies

- **Message Queue:** Redis 7.0+ (simple, fast, sufficient for medium scale)
- **Database:** PostgreSQL 15+ (better than SQLite for distributed writes)
- **Crawler Engine:** Playwright (existing, maintained)
- **Coordination:** Redis (Phase 2) or etcd (Phase 3)
- **Language:** Python 3.10+

---

## Architecture Overview

### Phase 2 Architecture (Target)

```
┌─────────────────┐
│   Scheduler     │  Seeds tasks to queue
│  (Main Process) │  Monitors overall health
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         Redis Message Queue             │
│  ┌──────────┐  ┌──────────┐            │
│  │  Tasks   │  │  DLQ     │            │
│  │  Queue   │  │  (Failed)│            │
│  └──────────┘  └──────────┘            │
│                                         │
│  Shared State:                          │
│  • URL deduplication (Bloom/Set)        │
│  • Politeness tracking (last access)   │
│  • Metrics (time series)                │
└─────────────────────────────────────────┘
         │
         ├────────┬────────┬────────┐
         ▼        ▼        ▼        ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ...
    │Worker 1│ │Worker 2│ │Worker 3│
    │        │ │        │ │        │
    │Playwright│Playwright│Playwright
    └────┬───┘ └────┬───┘ └────┬───┘
         │          │          │
         └──────────┼──────────┘
                    ▼
         ┌──────────────────────┐
         │   PostgreSQL DB      │
         │                      │
         │  • events table      │
         │  • crawl_sessions    │
         │  • schema_version    │
         └──────────────────────┘
```

### Information Flow

1. **Scheduler** seeds crawl tasks to Redis queue with source + location
2. **Workers** pull tasks from queue (blocking pop)
3. **Deduplication check** via Redis (Bloom filter or Set)
4. **Politeness check** via Redis (last access timestamps)
5. **Crawl execution** using Playwright
6. **Event extraction** and validation (Pydantic models)
7. **Batch insert** to PostgreSQL (100 events per batch)
8. **Metrics recording** to Redis time series
9. **Task acknowledgment** or retry on failure

---

## System Components

### 1. Scheduler (Main Process)

**Responsibilities:**
- Seed initial crawl tasks based on schedule
- Monitor worker health via heartbeats
- Track overall crawl progress
- Trigger periodic tasks (hourly, daily)

**Key Functions:**
```python
def schedule_crawls():
    """Seeds tasks for all sources based on schedule."""
    for source in get_active_sources():
        if should_crawl(source):
            enqueue_task(source, location='nyc', priority=source.priority)

def monitor_workers():
    """Checks worker heartbeats, triggers replacement if needed."""
    for worker_id in get_registered_workers():
        if not is_alive(worker_id):
            logger.warning(f"Worker {worker_id} failed, requeuing tasks")
            requeue_worker_tasks(worker_id)
            remove_worker(worker_id)
```

**Configuration:**
- Cron-like scheduling (hourly, daily, custom intervals)
- Source priority levels (high/medium/low)
- Max concurrent tasks per source

### 2. Message Queue (Redis)

**Components:**
- **Task Queue:** Main queue for crawl tasks (`crawl_tasks` list)
- **Dead Letter Queue:** Failed tasks after max retries (`crawl_dlq`)
- **Deduplication Store:** Bloom filter or Set (`seen_urls`)
- **Politeness Store:** Hash map (`last_access:{hostname}`)
- **Metrics Store:** Time series (`metrics:{source}:{metric}`)

**Queue Operations:**
```python
# Enqueue task
redis.lpush('crawl_tasks', json.dumps({
    'task_id': str(uuid4()),
    'source': 'luma',
    'location': 'nyc',
    'priority': 'high',
    'retry_count': 0,
    'created_at': datetime.utcnow().isoformat()
}))

# Dequeue task (blocking)
task = redis.brpop('crawl_tasks', timeout=5)

# Deduplication
if not redis.sismember('seen_urls', url):
    redis.sadd('seen_urls', url)
    # Proceed with crawl

# Politeness
last_access = redis.get(f'last_access:{hostname}')
if not last_access or (time.time() - float(last_access)) > 10:
    redis.setex(f'last_access:{hostname}', 60, str(time.time()))
    # Proceed with crawl
```

**Persistence:**
- Redis persistence: RDB snapshots every 15 minutes
- AOF (Append-Only File) for durability
- Daily backups to S3 or local storage

### 3. Worker Pool

**Responsibilities:**
- Pull tasks from queue
- Execute crawls using Playwright
- Extract and validate events
- Save events to database
- Record metrics
- Handle failures and retries

**Worker Lifecycle:**
```python
class CrawlWorker:
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.redis = redis.Redis()
        self.db = DatabaseConnection()
        self.repo = SQLiteEventRepository(self.db)
        self.browser = None

    def start(self):
        """Main worker loop."""
        self.browser = launch_browser()
        self.register_worker()

        while True:
            try:
                task = self.get_next_task()
                if task:
                    self.process_task(task)
                else:
                    self.send_heartbeat()
                    time.sleep(5)
            except Exception as e:
                logger.exception(f"Worker error: {e}")
                time.sleep(10)

    def process_task(self, task):
        """Process a single crawl task."""
        try:
            # Check politeness
            if not self.can_crawl(task['source']):
                self.requeue_with_delay(task, delay=30)
                return

            # Execute crawl
            crawler = get_crawler(task['source'])
            events = crawler.crawl(self.browser, task['location'])

            # Save events
            saved_count = self.repo.save_many(events)

            # Record metrics
            self.record_success(task, saved_count)

            # Acknowledge task
            self.ack_task(task)

        except RetryableError as e:
            self.retry_task(task)
        except PermanentError as e:
            self.move_to_dlq(task, error=str(e))

    def register_worker(self):
        """Register worker with coordinator."""
        self.redis.hset('workers', self.worker_id, json.dumps({
            'status': 'idle',
            'registered_at': time.time(),
            'pid': os.getpid()
        }))
        self.redis.expire(f'worker:{self.worker_id}:heartbeat', 60)

    def send_heartbeat(self):
        """Send heartbeat to coordinator."""
        self.redis.setex(
            f'worker:{self.worker_id}:heartbeat',
            60,
            json.dumps({
                'timestamp': time.time(),
                'status': 'alive',
                'tasks_processed': self.tasks_processed
            })
        )
```

**Worker Configuration:**
- Max concurrent tasks: 1 per worker (simple model)
- Memory limit: 2 GB per worker
- Timeout: 5 minutes per crawl task
- Heartbeat interval: 30 seconds

### 4. Database (PostgreSQL)

**Schema:**
```sql
-- Events table (same as SQLite)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP,
    location_name TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    is_online BOOLEAN DEFAULT FALSE,
    price_cents INTEGER,
    currency VARCHAR(10),
    is_free BOOLEAN DEFAULT FALSE,
    description TEXT,
    image_url TEXT,
    organizer_name VARCHAR(255),
    category VARCHAR(100),
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, source)
);

-- Indexes for performance
CREATE INDEX idx_events_source ON events(source);
CREATE INDEX idx_events_start_datetime ON events(start_datetime);
CREATE INDEX idx_events_city_state ON events(city, state);
CREATE INDEX idx_events_location ON events(city, state, start_datetime);
CREATE INDEX idx_events_created_at ON events(created_at);

-- Crawl sessions (tracking)
CREATE TABLE crawl_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL UNIQUE,
    source VARCHAR(50) NOT NULL,
    location VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    events_found INTEGER DEFAULT 0,
    events_saved INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    worker_id VARCHAR(50),
    error_message TEXT
);

CREATE INDEX idx_sessions_source ON crawl_sessions(source);
CREATE INDEX idx_sessions_started_at ON crawl_sessions(started_at);

-- Schema version (migrations)
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);
```

**Connection Pooling:**
```python
from psycopg2 import pool

# Connection pool (10 connections max)
connection_pool = pool.SimpleConnectionPool(
    minconn=2,
    maxconn=10,
    host='localhost',
    database='events_db',
    user='events_user',
    password=os.getenv('DB_PASSWORD')
)
```

### 5. Deduplication System

**Strategy:** Redis-based with two options

**Option A: Redis Set (Simple, Exact Matching)**
```python
class RedisSetDeduplicator:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.key = 'seen_urls'

    def is_seen(self, url: str) -> bool:
        normalized = normalize_url(url)
        return self.redis.sismember(self.key, normalized)

    def mark_seen(self, url: str):
        normalized = normalize_url(url)
        self.redis.sadd(self.key, normalized)
        # Set expiry for memory management
        if self.redis.scard(self.key) % 10000 == 0:
            self.redis.expire(self.key, 86400 * 7)  # 7 days

def normalize_url(url: str) -> str:
    """Normalize URL for consistent deduplication."""
    parsed = urlparse(url.lower())
    # Sort query parameters
    query_params = sorted(parse_qsl(parsed.query))
    # Remove fragment
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path.rstrip('/'),
        '',
        urlencode(query_params),
        ''
    ))
```

**Option B: Redis Bloom Filter (Memory Efficient)**
```python
from redisbloom.client import Client

class BloomFilterDeduplicator:
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.rb = Client(host=redis_host, port=redis_port)
        self.key = 'seen_urls_bloom'

        # Create filter: 1% error rate, 10M capacity
        try:
            self.rb.bfCreate(self.key, 0.01, 10000000)
        except:
            pass  # Already exists

    def is_seen(self, url: str) -> bool:
        normalized = normalize_url(url)
        return self.rb.bfExists(self.key, normalized)

    def mark_seen(self, url: str):
        normalized = normalize_url(url)
        self.rb.bfAdd(self.key, normalized)
```

**Recommendation:** Start with Redis Set (Option A) for simplicity. Migrate to Bloom Filter if memory becomes issue (>10M URLs).

### 6. Politeness Manager

**Shared State via Redis:**
```python
class DistributedPolitenessManager:
    def __init__(self, redis_client, min_delay=10):
        self.redis = redis_client
        self.min_delay = min_delay  # seconds

    def can_crawl(self, hostname: str) -> bool:
        """Check if enough time has passed since last crawl."""
        key = f'last_access:{hostname}'
        last_access = self.redis.get(key)

        if not last_access:
            return True

        elapsed = time.time() - float(last_access)
        return elapsed >= self.min_delay

    def wait_if_needed(self, hostname: str):
        """Block until politeness delay satisfied."""
        key = f'last_access:{hostname}'
        last_access = self.redis.get(key)

        if last_access:
            elapsed = time.time() - float(last_access)
            if elapsed < self.min_delay:
                wait_time = self.min_delay - elapsed
                logger.debug(f"Waiting {wait_time:.1f}s for {hostname}")
                time.sleep(wait_time)

    def record_access(self, hostname: str, fetch_time: float):
        """Record access time for hostname."""
        key = f'last_access:{hostname}'
        # Store with TTL (1 minute is sufficient)
        self.redis.setex(key, 60, str(time.time()))

        # Adaptive delay based on fetch time
        adaptive_delay = max(self.min_delay, fetch_time * 10)
        if adaptive_delay > self.min_delay:
            logger.info(f"Adaptive delay for {hostname}: {adaptive_delay:.1f}s")
```

**Distributed Lock for Critical Sections:**
```python
from redis.lock import Lock

def crawl_with_lock(hostname: str):
    """Ensure only one worker crawls hostname at a time."""
    lock_key = f'lock:crawl:{hostname}'
    lock = Lock(redis, lock_key, timeout=300)  # 5 min timeout

    if lock.acquire(blocking=False):
        try:
            # Perform crawl
            events = crawler.crawl(url)
            return events
        finally:
            lock.release()
    else:
        logger.info(f"Lock held by another worker for {hostname}")
        # Requeue task with delay
        return None
```

### 7. Metrics Collector

**Redis Time Series for Metrics:**
```python
class MetricsCollector:
    def __init__(self, redis_client):
        self.redis = redis_client

    def record_crawl(self, source: str, events_count: int, duration: float, success: bool):
        """Record crawl metrics."""
        timestamp = int(time.time())

        # Events count time series
        self.redis.zadd(f'metrics:{source}:events', {timestamp: events_count})

        # Duration time series
        self.redis.zadd(f'metrics:{source}:duration', {timestamp: duration})

        # Success/failure counter
        status = 'success' if success else 'failure'
        self.redis.incr(f'metrics:{source}:{status}')

        # Global counters
        self.redis.incr('metrics:global:crawls_total')
        self.redis.incrby('metrics:global:events_total', events_count)

        # Trim old data (keep 7 days for detailed metrics)
        cutoff = timestamp - (7 * 86400)
        self.redis.zremrangebyscore(f'metrics:{source}:events', 0, cutoff)
        self.redis.zremrangebyscore(f'metrics:{source}:duration', 0, cutoff)

    def get_stats(self, source: str, hours=24) -> dict:
        """Get metrics for source over time period."""
        cutoff = int(time.time()) - (hours * 3600)

        # Get events time series
        events = self.redis.zrangebyscore(
            f'metrics:{source}:events',
            cutoff,
            '+inf',
            withscores=True
        )

        total_events = sum(score for _, score in events)
        avg_events = total_events / len(events) if events else 0

        # Get success/failure counts
        success_count = int(self.redis.get(f'metrics:{source}:success') or 0)
        failure_count = int(self.redis.get(f'metrics:{source}:failure') or 0)
        total_crawls = success_count + failure_count
        success_rate = success_count / total_crawls if total_crawls > 0 else 0

        return {
            'total_events': total_events,
            'avg_events_per_crawl': avg_events,
            'crawl_count': len(events),
            'success_rate': success_rate,
            'period_hours': hours
        }
```

---

## Data Flow

### 1. Scheduled Crawl Flow

```
1. Scheduler
   ├─> Check crawl schedule for each source
   ├─> Determine if source should be crawled now
   └─> Enqueue task to Redis

2. Redis Queue
   ├─> Store task in crawl_tasks list
   └─> Return task ID

3. Worker (pulls from queue)
   ├─> BRPOP task from crawl_tasks (blocking)
   ├─> Parse task JSON
   └─> Begin processing

4. Deduplication Check
   ├─> Extract URLs from task
   ├─> Check Redis Set/Bloom filter
   └─> Filter out seen URLs

5. Politeness Check
   ├─> Extract hostname from URL
   ├─> Check last access time in Redis
   ├─> Wait if needed (10s delay)
   └─> Record new access time

6. Crawl Execution
   ├─> Launch Playwright browser (if needed)
   ├─> Navigate to source URL
   ├─> Extract events from page
   └─> Transform to Event objects

7. Event Validation
   ├─> Validate with Pydantic schema
   ├─> Filter invalid events
   └─> Log validation errors

8. Database Save
   ├─> Batch events (100 per batch)
   ├─> Upsert to PostgreSQL
   ├─> Handle duplicates (UNIQUE constraint)
   └─> Return saved count

9. Metrics Recording
   ├─> Record events count to Redis
   ├─> Record crawl duration
   ├─> Increment success counter
   └─> Trim old metrics

10. Task Completion
    ├─> Log crawl summary
    ├─> Acknowledge task (remove from queue)
    └─> Ready for next task
```

### 2. Failure Recovery Flow

```
1. Task Failure
   ├─> Exception during crawl
   └─> Classify error type

2. Error Classification
   ├─> Transient (network timeout, 503)
   │   └─> Retry with backoff
   ├─> Rate Limit (429, 403)
   │   └─> Retry with longer backoff
   ├─> Permanent (404, 410, invalid URL)
   │   └─> Move to DLQ
   └─> Unknown (5xx, connection refused)
       └─> Retry with caution

3. Retry Logic
   ├─> Increment retry_count in task
   ├─> Check if retry_count < max_retries (3)
   ├─> Calculate backoff delay (1m, 5m, 30m)
   ├─> LPUSH task back to queue with delay
   └─> Log retry attempt

4. Dead Letter Queue
   ├─> Check if max_retries exceeded
   ├─> Move task to crawl_dlq
   ├─> Record failure details
   └─> Alert if DLQ size > threshold

5. Worker Failure
   ├─> Worker misses heartbeat (3 consecutive)
   ├─> Scheduler detects failed worker
   ├─> Retrieve in-progress tasks for worker
   ├─> Requeue tasks to crawl_tasks
   └─> Remove worker from registry
```

---

## Component Interactions

### Sequence Diagram: Scheduled Crawl

```
Scheduler     Redis Queue     Worker     PostgreSQL     Metrics
   │              │             │            │             │
   ├─ Schedule ──>│             │            │             │
   │              │             │            │             │
   │              │<── Pull ────┤            │             │
   │              │             │            │             │
   │              │   Process   │            │             │
   │              │             ├─ Crawl    │             │
   │              │             │            │             │
   │              │             ├─ Save ───>│             │
   │              │             │<─ ACK ─────┤             │
   │              │             │            │             │
   │              │             ├─ Metrics ─────────────>│
   │              │             │            │             │
   │              │<─ ACK ──────┤            │             │
```

---

## API Specifications

### Task Queue API

**Enqueue Task:**
```python
def enqueue_task(source: str, location: str, priority: str = 'medium') -> str:
    """
    Enqueue a crawl task to Redis queue.

    Args:
        source: Event source name (e.g., 'luma', 'meetup')
        location: Location identifier (e.g., 'nyc', 'sf')
        priority: Task priority ('high', 'medium', 'low')

    Returns:
        task_id: UUID of enqueued task
    """
    task = {
        'task_id': str(uuid4()),
        'source': source,
        'location': location,
        'priority': priority,
        'retry_count': 0,
        'created_at': datetime.utcnow().isoformat()
    }

    redis.lpush('crawl_tasks', json.dumps(task))
    return task['task_id']
```

**Dequeue Task:**
```python
def dequeue_task(timeout: int = 5) -> Optional[dict]:
    """
    Dequeue next available task from Redis queue.

    Args:
        timeout: Blocking timeout in seconds

    Returns:
        task: Task dictionary or None if timeout
    """
    result = redis.brpop('crawl_tasks', timeout=timeout)
    if result:
        _, task_json = result
        return json.loads(task_json)
    return None
```

### Worker API

**Register Worker:**
```python
def register_worker(worker_id: str) -> bool:
    """Register worker with coordinator."""
    worker_info = {
        'worker_id': worker_id,
        'status': 'idle',
        'registered_at': time.time(),
        'pid': os.getpid(),
        'hostname': socket.gethostname()
    }

    redis.hset('workers', worker_id, json.dumps(worker_info))
    redis.setex(f'worker:{worker_id}:heartbeat', 60, str(time.time()))
    return True
```

**Send Heartbeat:**
```python
def send_heartbeat(worker_id: str, status: str, tasks_processed: int):
    """Send worker heartbeat to coordinator."""
    heartbeat = {
        'timestamp': time.time(),
        'status': status,
        'tasks_processed': tasks_processed
    }

    redis.setex(
        f'worker:{worker_id}:heartbeat',
        60,
        json.dumps(heartbeat)
    )
```

### Metrics API

**Record Crawl:**
```python
def record_crawl(source: str, events_count: int, duration: float, success: bool):
    """Record crawl metrics to Redis."""
    metrics = MetricsCollector(redis)
    metrics.record_crawl(source, events_count, duration, success)
```

**Get Statistics:**
```python
def get_stats(source: str, hours: int = 24) -> dict:
    """Get crawl statistics for source."""
    metrics = MetricsCollector(redis)
    return metrics.get_stats(source, hours)
```

---

## Deployment Architecture

### Phase 2 Deployment

**Infrastructure:**
- 1 Redis instance (standalone, persistence enabled)
- 1 PostgreSQL instance
- 2-4 worker VMs
- 1 scheduler (runs on same VM as PostgreSQL)

**Network Topology:**
```
Internet
   │
   └─> Load Balancer (optional, for API)
         │
         ├─> Redis (6379)
         │    └─ Persistence: RDB + AOF
         │
         ├─> PostgreSQL (5432)
         │    └─ Backups: Daily to S3
         │
         └─> Worker VMs (2-4 instances)
              ├─ Worker 1: 2 CPU, 4 GB RAM
              ├─ Worker 2: 2 CPU, 4 GB RAM
              └─ Worker 3: 2 CPU, 4 GB RAM
```

**Deployment Steps:**

1. **Provision Infrastructure**
   ```bash
   # Redis
   docker run -d --name redis \
     -p 6379:6379 \
     -v /data/redis:/data \
     redis:7-alpine redis-server --appendonly yes

   # PostgreSQL
   docker run -d --name postgres \
     -p 5432:5432 \
     -e POSTGRES_DB=events_db \
     -e POSTGRES_PASSWORD=$DB_PASSWORD \
     -v /data/postgres:/var/lib/postgresql/data \
     postgres:15-alpine

   # Apply schema
   psql -d events_db -f schema.sql
   ```

2. **Deploy Application**
   ```bash
   # Clone repository
   git clone https://github.com/yourorg/events-agent.git
   cd events-agent

   # Install dependencies
   python3 -m venv venv
   source venv/bin/activate
   pip install -e .

   # Install Playwright
   playwright install chromium

   # Configure environment
   cp .env.example .env
   # Edit .env with Redis/PostgreSQL credentials

   # Run migrations
   python scripts/migrate.py
   ```

3. **Start Workers**
   ```bash
   # Worker 1
   python -m events_agent.worker --worker-id worker-1

   # Worker 2
   python -m events_agent.worker --worker-id worker-2

   # Worker 3
   python -m events_agent.worker --worker-id worker-3
   ```

4. **Start Scheduler**
   ```bash
   python -m events_agent.scheduler
   ```

**Systemd Service Files:**

`/etc/systemd/system/events-worker@.service`
```ini
[Unit]
Description=Events Agent Worker %i
After=network.target redis.service postgres.service

[Service]
Type=simple
User=events
WorkingDirectory=/opt/events-agent
Environment="PATH=/opt/events-agent/venv/bin"
ExecStart=/opt/events-agent/venv/bin/python -m events_agent.worker --worker-id worker-%i
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Failure Handling

### Worker Failure Scenarios

**Scenario 1: Worker Crash During Crawl**

| Step | Action |
|------|--------|
| 1 | Worker fails mid-crawl (e.g., OOM, network issue) |
| 2 | Task not acknowledged (still in Redis queue or being processed) |
| 3 | Worker heartbeat stops |
| 4 | Scheduler detects missed heartbeats (3 consecutive, ~90s) |
| 5 | Scheduler retrieves worker's in-progress tasks |
| 6 | Tasks requeued to crawl_tasks with original retry_count |
| 7 | New worker picks up task |
| 8 | Crawl retried (idempotent due to deduplication) |

**Scenario 2: Persistent Crawl Failure**

| Step | Action |
|------|--------|
| 1 | Crawl fails (e.g., 404, 403, parsing error) |
| 2 | Worker classifies error type |
| 3 | If transient: retry with backoff |
| 4 | If permanent: move to DLQ |
| 5 | If retry_count >= 3: move to DLQ |
| 6 | DLQ inspected manually or via alert |

### Database Failure

**Scenario: PostgreSQL Unreachable**

| Step | Action |
|------|--------|
| 1 | Worker attempts database save |
| 2 | Connection fails (timeout, connection refused) |
| 3 | Worker logs error, retries with exponential backoff |
| 4 | If persistent: task marked as failed, moved to DLQ |
| 5 | Events stored in local buffer (optional fallback) |
| 6 | Alert triggered if DLQ depth > threshold |

**Mitigation:**
- Connection pooling with automatic retry
- Local buffering of events (fallback to JSON)
- Database HA (replication, failover) in Phase 3

### Redis Failure

**Scenario: Redis Unreachable**

| Step | Action |
|------|--------|
| 1 | Worker attempts queue operation |
| 2 | Connection fails |
| 3 | Worker logs error, sleeps 10s, retries |
| 4 | If Redis down >5 minutes: alert triggered |
| 5 | Workers wait in retry loop until Redis restored |
| 6 | On Redis restore: tasks resume automatically |

**Mitigation:**
- Redis persistence (RDB + AOF)
- Daily backups
- Phase 3: Redis Cluster for HA

---

## Scalability Considerations

### Horizontal Scaling

**Adding Workers:**
```bash
# Dynamically add worker
python -m events_agent.worker --worker-id worker-N

# Worker auto-registers with coordinator
# Immediately begins pulling tasks
# Linear speedup (2x workers ≈ 2x throughput)
```

**Scaling Limits (Phase 2):**
- Redis: ~10K ops/sec (sufficient for 10 workers)
- PostgreSQL: ~1000 writes/sec (batch inserts)
- Workers: 10 workers max (diminishing returns due to politeness)

**Bottleneck Analysis:**
| Component | Limit | Mitigation |
|-----------|-------|------------|
| Redis | 10K ops/sec | Redis Cluster (Phase 3) |
| PostgreSQL | 1K writes/sec | Batch inserts, connection pooling |
| Network | 100 Mbps | Upgrade to 1 Gbps |
| Worker CPU | 100% utilization | Add more workers |

### Vertical Scaling

**Redis Scaling:**
- Start: 2 GB RAM
- Growth: 4 GB → 8 GB as URL count grows
- Monitor: Memory usage, eviction rate

**PostgreSQL Scaling:**
- Start: 2 CPU, 4 GB RAM, 100 GB SSD
- Growth: 4 CPU, 8 GB RAM, 500 GB SSD
- Monitor: Query latency, connection count

**Worker Scaling:**
- Start: 2 CPU, 4 GB RAM per worker
- Growth: Reduce to 1 CPU, 2 GB RAM if memory-bound
- Monitor: CPU utilization, memory usage

---

## Migration Strategy

### Phase 1: Multi-Process (Immediate)

**Changes:**
```python
# main.py - Before
for source in sources:
    events = crawl_source(source)
    save_events(events)

# main.py - After
from multiprocessing import Pool

with Pool(processes=4) as pool:
    results = pool.map(crawl_source, sources)
```

**Impact:** 4x speedup, 0 infrastructure cost

### Phase 2: Redis Queue (2 weeks)

**Migration Steps:**

1. **Database Migration (SQLite → PostgreSQL)**
   ```bash
   # Export SQLite data
   python scripts/export_sqlite.py --output events.csv

   # Create PostgreSQL schema
   psql -d events_db -f schema/postgres.sql

   # Import data
   psql -d events_db -c "\COPY events FROM 'events.csv' CSV HEADER"
   ```

2. **Deploy Redis**
   ```bash
   docker run -d --name redis -p 6379:6379 \
     -v /data/redis:/data \
     redis:7-alpine redis-server --appendonly yes
   ```

3. **Update Application Code**
   - Add Redis client to workers
   - Implement queue operations
   - Add deduplication layer
   - Add politeness manager

4. **Deploy Workers**
   - Start 2-4 workers
   - Monitor queue depth and worker health

5. **Cutover**
   - Stop old single-process crawler
   - Start scheduler + workers
   - Monitor for 24 hours

**Rollback Plan:**
- Keep SQLite database as backup
- Can revert to single-process if issues

---

## Monitoring and Observability

### Key Metrics

**Queue Metrics:**
- Queue depth (crawl_tasks length)
- DLQ depth (crawl_dlq length)
- Enqueue rate (tasks/minute)
- Dequeue rate (tasks/minute)
- Average wait time

**Worker Metrics:**
- Active workers count
- Idle workers count
- Tasks processed per worker
- Worker uptime
- Heartbeat status

**Crawl Metrics:**
- Events crawled per source
- Crawl success rate
- Crawl duration (avg, p50, p95, p99)
- Error rate by error type
- Bandwidth usage

**Database Metrics:**
- Connection count
- Query latency (avg, p95, p99)
- Write throughput
- Database size
- Index hit rate

### Logging Strategy

**Log Levels:**
- **DEBUG:** Detailed crawl steps, queue operations
- **INFO:** Crawl start/end, events saved, metrics
- **WARNING:** Retries, temporary failures, long queues
- **ERROR:** Permanent failures, database errors, worker crashes
- **CRITICAL:** System-wide failures, data loss

**Structured Logging:**
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "crawl_completed",
    source="luma",
    events_count=42,
    duration=12.5,
    worker_id="worker-1"
)
```

**Log Aggregation:**
- Local files: `/var/log/events-agent/worker-*.log`
- Rotation: Daily, keep 30 days
- Phase 3: Centralized logging (ELK, Loki)

### Alerting

**Critical Alerts:**
- No workers active for >5 minutes
- Queue depth >10,000 tasks
- DLQ depth >100 tasks
- Database unreachable for >2 minutes
- Redis unreachable for >2 minutes

**Warning Alerts:**
- Worker count <2 for >5 minutes
- Crawl success rate <90% over 1 hour
- Average crawl duration >5 minutes
- Queue depth >1,000 tasks

**Alert Channels:**
- Email for critical alerts
- Slack/Discord for warnings
- PagerDuty for on-call (Phase 3)

---

## Security Considerations

### Authentication and Authorization

**Database:**
- Strong passwords (20+ characters, random)
- Least-privilege users (worker user can only INSERT/SELECT)
- SSL/TLS for connections (Phase 3)

**Redis:**
- Password protection (`requirepass` config)
- Bind to private network only (not 0.0.0.0)
- SSL/TLS for connections (Phase 3)

**API (Future):**
- JWT authentication
- Rate limiting (100 req/min per API key)
- API key rotation

### Data Privacy

**PII Handling:**
- No user accounts (no PII currently)
- Event data is public (from public sources)
- User-agent identifies as bot (transparent)

**Compliance:**
- Respect robots.txt
- Honor rate limits
- Provide crawler contact info in user-agent

### Network Security

**Phase 2:**
- Private network for Redis/PostgreSQL
- Firewall rules (allow only necessary ports)
- SSH key-based authentication

**Phase 3:**
- VPC with private subnets
- Bastion host for SSH access
- TLS for all internal communication

---

**Document Status:** Draft
**Last Updated:** February 13, 2026
**Next Review:** March 1, 2026
**Owner:** Events Agent Development Team
