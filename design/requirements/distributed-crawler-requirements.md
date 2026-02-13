# Distributed Crawler Requirements

**Version:** 1.0
**Date:** February 13, 2026
**Project:** Events Agent - Distributed Architecture
**Status:** Draft

---

## Table of Contents

1. [Overview](#overview)
2. [Business Requirements](#business-requirements)
3. [Functional Requirements](#functional-requirements)
4. [Non-Functional Requirements](#non-functional-requirements)
5. [Technical Requirements](#technical-requirements)
6. [Constraints](#constraints)
7. [Success Criteria](#success-criteria)

---

## Overview

### Purpose
Transform the Events Agent from a single-process crawler into a distributed system capable of scaling to 50+ event sources across multiple cities while maintaining reliability and data quality.

### Current State
- **Architecture:** Single-process Python crawler
- **Sources:** 9 event sources (Luma, Meetup, Eventbrite, Fever, Cozymeal, Jazz Near You, Songkick, TimeOut, DoNYC)
- **Database:** SQLite with WAL mode
- **Crawl Time:** 2-3 hours for all sources
- **Region:** NYC only
- **Refresh Rate:** Daily/weekly

### Target State
- **Architecture:** Distributed queue-based system with multiple workers
- **Sources:** 20-50+ event sources
- **Database:** PostgreSQL with distributed write capability
- **Crawl Time:** <30 minutes for all sources
- **Regions:** Multiple cities (NYC, SF, LA, Boston, etc.)
- **Refresh Rate:** Hourly to near real-time

---

## Business Requirements

### BR-1: Scalability
**Priority:** High
**Description:** System must scale to handle 50+ event sources without significant architecture changes.

**Acceptance Criteria:**
- Support 50+ concurrent crawlers
- Crawl completion time <1 hour for all sources
- Linear scaling with worker additions (2x workers = ~2x throughput)
- Handle 100K+ events per crawl cycle

### BR-2: Multi-Region Support
**Priority:** Medium
**Description:** Enable event aggregation across multiple cities/regions.

**Acceptance Criteria:**
- Support 5+ cities simultaneously
- Region-specific crawling (NYC, SF, LA, Boston, Chicago)
- Configurable source priority per region
- Region-aware event storage and querying

### BR-3: Improved Refresh Rate
**Priority:** High
**Description:** Reduce time between crawls to improve event freshness.

**Acceptance Criteria:**
- Hourly crawls for high-priority sources (Luma, Meetup)
- Daily crawls for low-priority sources
- Configurable refresh schedules per source
- Near real-time updates for critical events

### BR-4: Cost Efficiency
**Priority:** High
**Description:** Optimize infrastructure costs while meeting performance goals.

**Acceptance Criteria:**
- Phase 1 (Multi-process): $0/month additional cost
- Phase 2 (Redis Queue): $100-200/month maximum
- Auto-scaling to reduce idle worker costs
- Optimize bandwidth and compute usage

### BR-5: Reliability
**Priority:** High
**Description:** Ensure system continues operating despite component failures.

**Acceptance Criteria:**
- 99.5% uptime for crawling operations
- Automatic recovery from worker failures
- No data loss on worker crashes
- Failed crawls retry automatically with exponential backoff

---

## Functional Requirements

### FR-1: Distributed Task Queue
**Priority:** High
**Description:** Implement message queue for task distribution across workers.

**Acceptance Criteria:**
- Tasks queued with source, location, and priority metadata
- Workers pull tasks from queue dynamically
- Support for task priorities (high/medium/low)
- Dead letter queue for failed tasks after 3 retries
- Queue depth monitoring and metrics

**Technical Details:**
- Message broker: Redis (Phase 2) or Kafka (Phase 3)
- Queue format: JSON with schema validation
- TTL: 24 hours for tasks
- Persistence: Disk-backed for durability

### FR-2: Worker Pool Management
**Priority:** High
**Description:** Dynamic worker pool that scales based on workload.

**Acceptance Criteria:**
- Minimum 2 workers, maximum 10 workers
- Workers register/deregister with coordinator
- Heartbeat monitoring (30-second interval)
- Automatic worker replacement on failure
- Graceful shutdown with task completion

### FR-3: URL Deduplication
**Priority:** High
**Description:** Prevent crawling duplicate URLs across distributed workers.

**Acceptance Criteria:**
- Shared deduplication state across workers
- Sub-second lookup performance
- 1-2% false positive rate acceptable
- Support for 10M+ unique URLs
- Memory efficient (Bloom filter or Redis Set)

**Technical Details:**
- Primary: Redis Set for exact matching
- Alternative: Redis Bloom Filter for memory efficiency
- URL normalization before deduplication
- TTL: 7 days for seen URLs

### FR-4: Politeness Enforcement
**Priority:** High
**Description:** Ensure distributed politeness across workers to respect target servers.

**Acceptance Criteria:**
- 10-15 second delay between requests to same host
- Shared "last access time" state across workers
- Per-source rate limiting (configurable)
- Robots.txt compliance with caching
- Adaptive throttling based on server response

**Technical Details:**
- Redis for shared state (hostname → last_access_timestamp)
- Distributed locks for critical sections
- Robots.txt cache: 24-hour TTL

### FR-5: Event Storage
**Priority:** High
**Description:** Distributed-safe event storage with deduplication.

**Acceptance Criteria:**
- Support concurrent writes from multiple workers
- Automatic event deduplication (UNIQUE constraint on event_id + source)
- Transaction support for batch inserts
- Query performance <100ms for filtered queries
- Database migrations managed programmatically

**Technical Details:**
- Migrate SQLite → PostgreSQL
- Connection pooling (max 10 connections per worker)
- Schema versioning and migrations
- Indexes on: source, start_datetime, city, state

### FR-6: Crawl Session Tracking
**Priority:** Medium
**Description:** Track crawl sessions for monitoring and debugging.

**Acceptance Criteria:**
- Record start/end time, source, events count, errors
- Session status: pending, in_progress, completed, failed
- Link events to crawl sessions via foreign key
- Historical session analytics
- Retention: 90 days

### FR-7: Configuration Management
**Priority:** Medium
**Description:** Centralized configuration for distributed system.

**Acceptance Criteria:**
- Source definitions (name, URL, priority, refresh interval)
- Worker configuration (max concurrency, timeout, memory limits)
- Region definitions (city, state, timezone)
- Runtime configuration updates without restarts
- Version-controlled configuration files

**Technical Details:**
- YAML/JSON configuration files
- Environment variables for secrets
- Optional: etcd for dynamic configuration (Phase 3)

### FR-8: Monitoring and Metrics
**Priority:** High
**Description:** Real-time visibility into crawler performance and health.

**Acceptance Criteria:**
- Queue depth tracking
- Worker health status (alive/dead/idle)
- Events crawled per source per time period
- Error rates and failure types
- Crawl duration metrics
- Resource usage (CPU, memory, bandwidth)

**Technical Details:**
- Metrics stored in Redis time series
- 7-day retention for detailed metrics
- 90-day retention for aggregated metrics
- Dashboard/API for visualization

### FR-9: Error Handling and Retry Logic
**Priority:** High
**Description:** Robust error handling with intelligent retries.

**Acceptance Criteria:**
- Classify errors: transient (retry), permanent (skip), rate-limit (backoff)
- Exponential backoff: 1 min → 5 min → 30 min
- Max 3 retry attempts per task
- Dead letter queue for manual review
- Error logging with full context

**Error Categories:**
- **Transient:** Network timeout, 503, DNS failure → Retry
- **Permanent:** 404, 410, invalid URL → Skip
- **Rate Limit:** 429, 403 with retry-after → Backoff
- **Unknown:** 5xx, connection refused → Retry with caution

### FR-10: Data Export and API
**Priority:** Low
**Description:** Programmatic access to crawled events.

**Acceptance Criteria:**
- REST API for event queries
- Filters: date range, source, city, category
- Pagination support (limit/offset)
- JSON and CSV export formats
- Rate limiting: 100 requests/minute

**Deferred to Future:** Phase 3 enhancement

---

## Non-Functional Requirements

### NFR-1: Performance
**Priority:** High

| Metric | Requirement |
|--------|-------------|
| **Crawl Throughput** | 500+ events/minute (across all workers) |
| **Queue Latency** | <100ms from task enqueue to worker pickup |
| **Database Write Latency** | <50ms per batch insert (100 events) |
| **Query Performance** | <100ms for filtered queries (date + location) |
| **Worker Startup Time** | <30 seconds from launch to first task |

### NFR-2: Scalability
**Priority:** High

| Dimension | Requirement |
|-----------|-------------|
| **Concurrent Workers** | 2-10 workers (Phase 2), 50+ workers (Phase 3) |
| **Event Sources** | 50+ sources without architecture changes |
| **Events per Crawl** | 100K+ events |
| **Unique URLs Tracked** | 10M+ URLs in deduplication system |
| **Regions** | 5+ cities/regions |

### NFR-3: Reliability
**Priority:** High

| Metric | Requirement |
|--------|-------------|
| **Uptime** | 99.5% availability (43 hours downtime/year) |
| **Worker Failure Recovery** | <2 minutes to detect and replace failed worker |
| **Data Durability** | Zero data loss on worker failures |
| **Message Queue Durability** | Disk-backed persistence, no message loss |
| **Database Backup** | Daily automated backups, 7-day retention |

### NFR-4: Maintainability
**Priority:** Medium

**Requirements:**
- Clear separation of concerns (repository pattern, modular crawlers)
- Comprehensive logging with structured format (JSON)
- Code coverage >80% for critical components
- Documentation for all public APIs
- Type hints for all functions (mypy compliance)

### NFR-5: Observability
**Priority:** High

**Requirements:**
- Real-time metrics dashboard
- Alerting for critical failures (worker down, queue backlog, high error rate)
- Centralized logging with search capability
- Trace crawl sessions end-to-end
- Performance profiling for bottlenecks

### NFR-6: Security
**Priority:** Medium

**Requirements:**
- API authentication (JWT or API keys)
- Database credentials in environment variables
- HTTPS for all external API calls
- Input validation for all user-provided data
- Rate limiting to prevent abuse

### NFR-7: Testability
**Priority:** High

**Requirements:**
- Unit tests for all business logic
- Integration tests for crawler + database
- Load tests simulating 10 concurrent workers
- Chaos testing for failure scenarios
- CI/CD pipeline with automated testing

---

## Technical Requirements

### TR-1: Technology Stack

**Required:**
- **Language:** Python 3.10+
- **Message Queue:** Redis 7.0+ with RedisBloom
- **Database:** PostgreSQL 15+ with TimescaleDB extension (optional)
- **Crawler:** Playwright 1.40+
- **Testing:** pytest, pytest-asyncio, pytest-cov

**Optional (Phase 3):**
- **Message Broker:** Apache Kafka 3.0+
- **Coordination:** etcd 3.5+
- **Orchestration:** Kubernetes 1.28+
- **Monitoring:** Prometheus + Grafana

### TR-2: Infrastructure Requirements

**Phase 1 (Multi-Process):**
- 1 server: 4 CPU cores, 8 GB RAM, 50 GB SSD
- Cost: $0/month (existing infrastructure)

**Phase 2 (Redis Queue):**
- 1 Redis instance: 2 GB RAM, persistence enabled (~$20/month)
- 1 PostgreSQL instance: 2 CPU, 4 GB RAM, 100 GB SSD (~$20/month)
- 2-4 worker VMs: 2 CPU, 4 GB RAM each (~$40-80/month)
- **Total:** $80-120/month

**Phase 3 (Production):**
- 3-node Kafka cluster (~$150/month)
- 3-node etcd cluster (~$60/month)
- PostgreSQL HA (~$100/month)
- 5-10 worker nodes (~$200-400/month)
- Monitoring stack (~$50/month)
- **Total:** $560-760/month

### TR-3: Data Retention

| Data Type | Retention Period | Compression |
|-----------|-----------------|-------------|
| **Events** | 1 year | None (queried frequently) |
| **Crawl Sessions** | 90 days | None |
| **Metrics (detailed)** | 7 days | None |
| **Metrics (aggregated)** | 1 year | Yes |
| **Logs** | 30 days | gzip after 7 days |
| **Deduplication State** | 7 days | N/A (Bloom filter) |

### TR-4: API Contracts

**Task Queue Message Format:**
```json
{
  "task_id": "uuid-v4",
  "source": "luma",
  "location": "nyc",
  "priority": "high",
  "retry_count": 0,
  "created_at": "2026-02-13T10:30:00Z",
  "metadata": {
    "region": "northeast",
    "timezone": "America/New_York"
  }
}
```

**Worker Heartbeat Format:**
```json
{
  "worker_id": "worker-01",
  "status": "busy",
  "current_task_id": "uuid-v4",
  "events_processed": 1234,
  "uptime_seconds": 86400,
  "memory_mb": 512,
  "timestamp": "2026-02-13T10:30:00Z"
}
```

---

## Constraints

### C-1: Budget Constraints
- Phase 2 infrastructure budget: Maximum $200/month
- Must justify ROI for Phase 3 before approval

### C-2: Team Constraints
- 1-2 developers for implementation
- Limited DevOps expertise (favor simple solutions)
- Part-time maintenance (6-8 hours/week)

### C-3: Technology Constraints
- Must use Python (existing codebase)
- Must maintain compatibility with existing Playwright crawlers
- Cannot use proprietary/paid crawler services

### C-4: Timeline Constraints
- Phase 1: 1 day (immediate performance boost)
- Phase 2: 2 weeks (including testing)
- Phase 3: 8-10 weeks (if approved)

### C-5: Compatibility Constraints
- Maintain backward compatibility with existing SQLite data
- Migration scripts for SQLite → PostgreSQL
- Existing tests must pass without modification

---

## Success Criteria

### Phase 1 Success Criteria
- ✅ Crawl time reduced from 2-3 hours to <45 minutes
- ✅ Zero infrastructure cost increase
- ✅ All existing tests pass
- ✅ No data loss or corruption

### Phase 2 Success Criteria
- ✅ Crawl time reduced to <15 minutes
- ✅ Support 10+ concurrent sources
- ✅ Worker failure recovery <2 minutes
- ✅ 99.5% uptime over 30-day period
- ✅ Infrastructure cost <$150/month
- ✅ Documentation complete (architecture, deployment, operations)

### Phase 3 Success Criteria (Future)
- ✅ Support 50+ event sources
- ✅ Multi-region support (5+ cities)
- ✅ Crawl time <30 minutes for all sources
- ✅ 99.9% uptime
- ✅ Auto-scaling operational
- ✅ Full monitoring and alerting
- ✅ API for event access

---

## Out of Scope (Deferred)

The following are explicitly **out of scope** for Phase 1 and Phase 2:

1. **Advanced Analytics**
   - Machine learning for event categorization
   - Recommendation engine
   - Trend analysis and predictions

2. **User-Facing Features**
   - Web UI for event browsing
   - Email notifications
   - Calendar integrations

3. **Advanced Search**
   - Full-text search (FTS5 or Elasticsearch)
   - Fuzzy matching
   - Natural language queries

4. **Social Features**
   - User accounts and authentication
   - Event ratings and reviews
   - Social sharing

5. **Advanced Crawling**
   - JavaScript rendering for all sources
   - CAPTCHA solving
   - Proxy rotation
   - Browser fingerprinting avoidance

---

## Risk Assessment

### High Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Redis single point of failure** | High | Redis persistence, automated backups, failover to Redis Cluster in Phase 3 |
| **PostgreSQL write bottleneck** | Medium | Connection pooling, batch inserts, read replicas if needed |
| **Worker resource exhaustion** | Medium | Memory limits, max concurrent tasks per worker, monitoring |
| **Crawl target blocking** | High | Politeness policies, user-agent rotation, respect robots.txt |

### Medium Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Configuration drift** | Medium | Version-controlled config, automated deployment |
| **Queue depth explosion** | Medium | Queue depth limits, auto-scaling, backpressure |
| **Data quality degradation** | Medium | Validation tests, schema enforcement, monitoring |
| **Cost overruns** | Low | Auto-scaling limits, cost alerts, resource quotas |

---

## Appendices

### Appendix A: Glossary

- **Bloom Filter:** Probabilistic data structure for set membership testing
- **DHT:** Distributed Hash Table for decentralized key-value storage
- **URL Frontier:** Queue of URLs waiting to be crawled
- **Politeness:** Rate limiting to avoid overwhelming target servers
- **Dead Letter Queue:** Queue for failed tasks after max retry attempts
- **Heartbeat:** Periodic health check signal from workers
- **WAL Mode:** Write-Ahead Logging for SQLite concurrency

### Appendix B: References

See `design/research/distributed-crawler-research.md` for comprehensive references and research findings.

---

**Document Status:** Draft
**Last Updated:** February 13, 2026
**Next Review:** March 1, 2026
**Owner:** Events Agent Development Team
