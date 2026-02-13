# Distributed Crawler Design Documentation

This directory contains comprehensive design documentation for transforming the Events Agent into a distributed crawler system.

## Document Structure

```
design/
├── README.md (this file)
├── high-level-design.md
├── requirements/
│   └── distributed-crawler-requirements.md
├── research/
│   └── distributed-crawler-research.md
└── diagrams/
    ├── README.md
    ├── 01-system-architecture.puml
    ├── 02-component-diagram.puml
    ├── 03-sequence-crawl-flow.puml
    ├── 04-deployment-diagram.puml
    ├── 05-task-state-machine.puml
    ├── 06-data-flow.puml
    └── 07-class-diagram.puml
```

## Quick Start

### For Product Managers
Start with:
1. `requirements/distributed-crawler-requirements.md` - Business requirements, success criteria, phased approach

### For Architects
Start with:
1. `high-level-design.md` - Architecture overview, component design, data flow
2. `diagrams/01-system-architecture.puml` - Visual system overview

### For Engineers
Start with:
1. `high-level-design.md` - API specs, component interactions, implementation details
2. `diagrams/07-class-diagram.puml` - Class structure and relationships
3. `diagrams/03-sequence-crawl-flow.puml` - Step-by-step execution flow

### For Researchers
Start with:
1. `research/distributed-crawler-research.md` - Comprehensive industry research, patterns, technologies

## Document Summaries

### 1. Requirements Document
**File:** `requirements/distributed-crawler-requirements.md`
**Length:** ~5,000 words
**Sections:**
- Business requirements (scalability, multi-region, cost efficiency)
- Functional requirements (queue, workers, deduplication, politeness)
- Non-functional requirements (performance, reliability, scalability)
- Technical requirements (tech stack, infrastructure, APIs)
- Success criteria for each phase

**Key Highlights:**
- **Phase 1:** Multi-process (0 cost, 4x speedup)
- **Phase 2:** Redis queue ($100-200/month, 12x speedup)
- **Phase 3:** Production-grade ($600/month, 40x+ speedup)

### 2. High-Level Design Document
**File:** `high-level-design.md`
**Length:** ~8,000 words
**Sections:**
- Architecture overview with diagrams (ASCII art)
- System components (scheduler, queue, workers, database)
- Data flow and component interactions
- API specifications (queue, worker, metrics)
- Deployment architecture
- Failure handling strategies
- Migration strategy from current system

**Key Highlights:**
- Master-Worker pattern with Redis message queue
- PostgreSQL for distributed writes
- Bloom filter deduplication
- Distributed politeness management
- Phased migration path

### 3. Research Document
**File:** `research/distributed-crawler-research.md`
**Length:** ~15,000 words
**Sections:**
- Common distributed crawler architectures
- Key components (URL frontier, Bloom filters, politeness)
- Technologies (RabbitMQ vs Kafka vs Redis)
- Scalability challenges (deduplication, DNS, robots.txt)
- Real-world examples (Google, Common Crawl)
- Recommendations for Events Agent

**Key Highlights:**
- 43 authoritative references
- Comparison of 3 message queues
- Comparison of 3 coordination systems (ZooKeeper, etcd, Consul)
- Comparison of 3 crawler frameworks (Scrapy, Nutch, StormCrawler)
- Cost-benefit analysis for each phase

### 4. PlantUML Diagrams
**Directory:** `diagrams/`
**Count:** 7 diagrams

| Diagram | Purpose | Key Elements |
|---------|---------|--------------|
| **01-system-architecture** | High-level system view | Scheduler, Redis, Workers, PostgreSQL |
| **02-component-diagram** | Software components | Packages, interfaces, dependencies |
| **03-sequence-crawl-flow** | Crawl execution flow | Task lifecycle from schedule to save |
| **04-deployment-diagram** | Infrastructure layout | VMs, networks, services |
| **05-task-state-machine** | Task state transitions | Created → Queued → InProgress → Completed |
| **06-data-flow** | Data movement | Processes, data stores, external entities |
| **07-class-diagram** | Object-oriented design | Classes, interfaces, relationships |

**Rendering:** See `diagrams/README.md` for instructions on rendering PlantUML diagrams to PNG/SVG.

## Design Principles

### 1. Gradual Migration
- **Phase 1:** Multi-process (minimal changes, immediate value)
- **Phase 2:** Distributed queue (target architecture)
- **Phase 3:** Production-grade (future enhancement)

**Rationale:** Incremental approach reduces risk, allows learning, and provides early wins.

### 2. Simplicity Over Perfection
- Redis over Kafka (simpler, sufficient)
- PostgreSQL over distributed databases (proven, reliable)
- No coordination service initially (Redis sufficient)

**Rationale:** Small team, limited DevOps expertise, medium scale.

### 3. Proven Patterns
- Master-Worker architecture (battle-tested)
- Repository pattern (clean separation)
- Queue-based task distribution (scalable, fault-tolerant)

**Rationale:** Use industry-proven patterns rather than novel approaches.

### 4. Cost Consciousness
- Phase 1: $0/month (free performance boost)
- Phase 2: <$200/month (affordable for MVP)
- Phase 3: Only if business justifies ROI

**Rationale:** Budget-constrained startup, must justify infrastructure costs.

## Key Decisions

### Technology Choices

| Component | Choice | Alternatives Considered | Rationale |
|-----------|--------|------------------------|-----------|
| **Message Queue** | Redis | RabbitMQ, Kafka, SQS | Simplest, fast, multi-purpose |
| **Database** | PostgreSQL | MySQL, MongoDB, Cassandra | Excellent for distributed writes |
| **Coordination** | Redis (Phase 2) | ZooKeeper, etcd, Consul | Redis sufficient for medium scale |
| **Deduplication** | Redis Set → Bloom Filter | DHT, Local cache | Shared state, memory efficient |
| **Crawler Engine** | Playwright (existing) | Selenium, Scrapy | Already implemented, works well |

### Architectural Patterns

| Pattern | Application | Benefit |
|---------|-------------|---------|
| **Master-Worker** | Scheduler + Worker pool | Simple coordination, proven scalability |
| **Repository** | Data access layer | Clean separation, testable |
| **Strategy** | Deduplication, crawlers | Pluggable implementations |
| **Queue-based** | Task distribution | Decoupling, fault tolerance |

## Implementation Roadmap

### Phase 1: Multi-Process (Week 1)
**Effort:** 1 day
**Cost:** $0/month

**Tasks:**
- [ ] Refactor `main.py` to use `multiprocessing.Pool`
- [ ] Test with 4 parallel crawlers
- [ ] Verify SQLite WAL mode handles concurrent writes
- [ ] Measure performance improvement

**Deliverables:**
- 4x speedup (2-3 hours → 30-45 minutes)
- Zero infrastructure cost
- All existing tests pass

### Phase 2: Redis Queue (Weeks 2-3)
**Effort:** 2 weeks
**Cost:** $100-200/month

**Tasks:**
- [ ] Design queue message format
- [ ] Implement `QueueClient` class
- [ ] Migrate SQLite → PostgreSQL
- [ ] Implement `WorkerService` class
- [ ] Implement `SchedulerService` class
- [ ] Add deduplication layer (Redis Set)
- [ ] Add politeness manager
- [ ] Add metrics collector
- [ ] Write integration tests
- [ ] Deploy infrastructure (Redis, PostgreSQL, workers)
- [ ] Cutover and monitor

**Deliverables:**
- 12x speedup (2-3 hours → 10-15 minutes)
- Fault tolerance (worker failures auto-recover)
- Metrics dashboard
- Documentation (deployment, operations)

### Phase 3: Production-Grade (Weeks 4-11)
**Effort:** 8 weeks (if approved)
**Cost:** $600/month

**Tasks:**
- [ ] Deploy Kafka cluster
- [ ] Deploy etcd cluster
- [ ] Implement auto-scaling
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Set up alerting (PagerDuty)
- [ ] Implement API layer
- [ ] Add multi-region support
- [ ] Database HA (replication, failover)
- [ ] Load testing (10+ workers)
- [ ] Chaos testing (failure scenarios)

**Deliverables:**
- 40x+ speedup (support 50+ sources in <30 minutes)
- 99.9% uptime
- Auto-scaling operational
- Full observability
- REST API for event access

## Success Metrics

### Phase 1 Metrics
- ✅ Crawl time: <45 minutes (target: 30-45 min)
- ✅ Cost: $0/month
- ✅ All tests pass
- ✅ No data loss

### Phase 2 Metrics
- ✅ Crawl time: <15 minutes (target: 10-15 min)
- ✅ Infrastructure cost: <$150/month
- ✅ Uptime: >99.5% (43 hours downtime/year)
- ✅ Worker failure recovery: <2 minutes
- ✅ Documentation: Complete and tested

### Phase 3 Metrics
- ✅ Support: 50+ event sources
- ✅ Crawl time: <30 minutes for all sources
- ✅ Multi-region: 5+ cities
- ✅ Uptime: >99.9% (8 hours downtime/year)
- ✅ Auto-scaling: Operational and tested

## References

### Internal Documents
- `../CLAUDE.md` - Project overview and instructions
- `../README.md` - User-facing documentation
- `../SQLITE_MIGRATION.md` - Database migration guide
- `../queries/quick_analysis.sql` - SQL query examples

### External Resources
See `research/distributed-crawler-research.md` for 43 authoritative references on:
- Distributed crawler architectures
- URL frontier design
- Bloom filters and deduplication
- Message queue comparisons
- Crawler frameworks
- Real-world examples (Google, Common Crawl)

## Contributing to Design Docs

### When to Update
- Architecture changes (add component, change pattern)
- New requirements (business or technical)
- Technology decisions (switch from Redis to Kafka)
- Lessons learned from implementation

### How to Update
1. Update relevant `.md` files
2. Update PlantUML diagrams (`.puml` files)
3. Re-render diagrams to PNG/SVG
4. Update this README if structure changes
5. Commit all changes together

### Document Owners
- **Requirements:** Product Manager + Tech Lead
- **High-Level Design:** Architect + Tech Lead
- **Research:** Tech Lead
- **Diagrams:** Architect

## Questions & Feedback

For questions about the design:
1. Check existing documentation first
2. Review diagrams for visual understanding
3. Consult research document for background
4. Open GitHub issue if unresolved

For design feedback:
1. Suggest specific improvements (not just "this is bad")
2. Provide rationale (why is your approach better?)
3. Consider constraints (budget, team size, timeline)
4. Propose alternatives with trade-offs

---

**Design Status:** Draft
**Last Updated:** February 13, 2026
**Next Review:** March 1, 2026
**Maintained By:** Events Agent Development Team
