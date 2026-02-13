# Distributed Web Crawler Architecture Research

**Date:** February 13, 2026
**Purpose:** Research distributed crawler architectures for scaling the Events Agent system
**Current System:** Single-process Python crawler with 9 event sources, SQLite storage

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Common Distributed Crawler Architectures](#common-distributed-crawler-architectures)
3. [Key Components and Patterns](#key-components-and-patterns)
4. [Technologies and Tools](#technologies-and-tools)
5. [Scalability Challenges](#scalability-challenges)
6. [Real-World Examples](#real-world-examples)
7. [Recommendations for Events Agent](#recommendations-for-events-agent)
8. [References](#references)

---

## Executive Summary

Distributed web crawling enables concurrent fetching at scale, high throughput, and improved fault tolerance by spreading work across multiple nodes. If one worker crashes, others continue running, thereby improving reliability. The trade-off is that distributed systems require message queues, synchronization of a URL frontier, and careful design to avoid duplication or overwhelming target sites.

### Key Findings

- **Master-Worker Pattern** is the most common architecture, with a master node managing task scheduling and worker nodes executing crawls
- **URL Frontier** serves as the "brain" of the crawler, deciding what to crawl next, in what order, and at what rate
- **Bloom Filters** provide efficient URL deduplication with minimal memory overhead (1-2% false positive rate acceptable)
- **Message Queues** (Kafka, RabbitMQ, Redis) enable reliable task distribution and fault recovery
- **Politeness Policies** are critical - most crawlers wait 10-15 seconds between requests to the same host
- **DNS Caching** is essential as DNS resolution is a well-known bottleneck in web crawling

---

## Common Distributed Crawler Architectures

### 1. Master-Worker Pattern

**Overview:** The most widely adopted architecture where a master node coordinates work distribution and worker nodes execute crawling tasks.

**Master Node Responsibilities:**
- Task scheduling and URL distribution
- Monitoring worker health via heartbeat signals
- Detecting node failures and reassigning work
- Maintaining global crawl state and metadata
- Coordinating politeness policies across workers

**Worker Node Responsibilities:**
- Fetching and analyzing web pages simultaneously
- Storing results and logs
- Communicating with master via gRPC or HTTP
- Checkpointing progress for recovery

**Advantages:**
- Simple coordination model
- Centralized control and monitoring
- Easy to implement and debug
- Clear separation of concerns

**Disadvantages:**
- Master node is a single point of failure
- Limited scalability as master becomes bottleneck
- Requires master node redundancy for production

**Implementation Example (Crawlab):**
```
Master Node → Manages scheduling, health monitoring
Worker Nodes → Execute tasks, store to MongoDB
Storage → SeaweedFS (distributed file system)
Communication → gRPC
```

### 2. Queue-Based Systems

**Overview:** Uses message queues as the primary coordination mechanism, decoupling URL producers from crawler consumers.

**Architecture Flow:**
```
URL Frontier → Message Queue → Worker Pool → Storage
     ↑              |              |            |
     └──────────────┴──────────────┴────────────┘
              (Feedback loop for discovered URLs)
```

**Key Components:**
- **URL Frontier:** Manages which pages to visit next through queue systems
- **Message Broker:** Distributes tasks (RabbitMQ, Kafka, Redis, SQS)
- **Worker Pool:** Scales horizontally based on queue depth
- **Storage:** Persistent storage for crawled data

**Advantages:**
- Excellent horizontal scalability
- Natural load balancing via queue depth
- Built-in retry mechanisms
- Decoupled components enable independent scaling

**Disadvantages:**
- More complex architecture
- Requires message queue infrastructure
- Potential message queue as bottleneck
- Network overhead for message passing

**Best Practices:**
- Use dead letter queues for failed URLs after 3 retry attempts
- Implement exponential backoff (1 min → 5 min → 30 min)
- Partition queues by domain for politeness enforcement
- Monitor queue depth for auto-scaling decisions

### 3. Distributed Hash Table (DHT) / Peer-to-Peer

**Overview:** Fully decentralized architecture where crawlers are treated as peers and URLs are distributed via DHT lookup.

**How It Works:**
- URLs are hashed (hostname or full URL) to determine which peer handles them
- DHT provides lookup service similar to hash table: (key, value) pairs
- Each peer maintains portion of crawl frontier
- No central coordinator - work distributed via DHT protocol

**DHT Distribution Mechanism:**
```
URL: https://example.com/page
Hash(example.com) → Node ID
DHT Lookup → Peer responsible for example.com
Peer crawls all example.com URLs
```

**Advantages:**
- No single point of failure
- Excellent load balancing via consistent hashing
- Graceful handling of node joins/leaves (churn tolerance)
- Natural politeness - each domain handled by single peer
- Leverages excess bandwidth/computing from distributed nodes

**Disadvantages:**
- Complex implementation and debugging
- Higher communication overhead
- Difficult to maintain global crawl state
- Harder to enforce global policies
- DHT maintenance overhead

**Use Cases:**
- Large-scale academic/research crawls
- P2P systems with commodity hardware
- When fault tolerance more important than control
- Crawls where central coordination impractical

### 4. Hybrid Architectures

**Overview:** Combines multiple patterns to balance trade-offs.

**Common Combinations:**

1. **Master-Worker + Message Queue:**
   - Master manages high-level coordination
   - Message queue handles task distribution
   - Workers pull from queue and report to master
   - Best of both worlds: control + scalability

2. **DHT + Central Coordinator:**
   - DHT for URL distribution and load balancing
   - Lightweight coordinator for global policies
   - Reduces coordinator bottleneck while maintaining control

3. **Multi-Tier Queues:**
   - Front queues: Prioritization based on page importance
   - Back queues: Politeness enforcement (group by host)
   - Recommended ratio: 3x back queues vs crawler threads

---

## Key Components and Patterns

### URL Frontier / Queue Management

**Definition:** The URL frontier manages which pages a web crawler visits next, balancing speed with politeness, prioritizing important pages while preventing server overload.

#### Dual-Queue Architecture

**Front Queues (Prioritization):**
- Assign URLs importance scores based on:
  - Page quality/authority (PageRank-like)
  - Update frequency (freshness)
  - Domain importance
  - User-defined priorities
- Multiple priority levels (high, medium, low)
- FIFO within each priority level

**Back Queues (Politeness):**
- Group URLs from same host together
- One queue per host or domain
- Space requests appropriately (10-15 second gaps)
- Prevents bombarding single server
- Number of back queues = 3x crawler threads (recommended)

**Flow:**
```
New URLs → Front Queues (prioritize) → Back Queues (politeness) → Workers
```

#### Memory Management

**Challenge:** On web-scale crawls, URL frontier can exceed available memory.

**Solution:**
- Keep portion of each queue in memory
- Store majority on disk (SSD preferred)
- Bring more URLs from disk as memory queues drain
- Use memory-mapped files for efficient disk access
- Typical ratio: 10-20% in memory, 80-90% on disk

#### Distributed Frontier Partitioning

**By Host/Domain (Recommended):**
```python
# Consistent hashing approach
node_id = hash(hostname) % num_nodes
# Each node handles specific set of hosts
```

**Advantages:**
- Natural politeness - one host per node
- No cross-node coordination for rate limiting
- Efficient DNS caching per node

**By URL Hash (Alternative):**
```python
node_id = hash(full_url) % num_nodes
# Better load distribution but breaks politeness
```

**Distributed Frontera Approach:**
- Kafka topic partitioning
- Each host downloaded by only one spider process
- Polite by design
- Scales via Kafka partition count

### Duplicate URL Detection

#### Bloom Filter-Based Deduplication

**What is a Bloom Filter:**
- Probabilistic data structure using bit array + hash functions
- Space and time efficient for membership testing
- Can produce false positives (says "yes" when should be "no")
- Never produces false negatives (if says "no", definitely not in set)

**How It Works:**
```
1. URL arrives → Apply K hash functions → Set K bits to 1
2. Check URL → Apply same K hash functions → Check if all K bits are 1
3. All bits = 1 → Probably seen before (99% certain)
4. Any bit = 0 → Definitely not seen (100% certain)
```

**Performance Characteristics:**
- False positive rate: 1-2% (acceptable for web crawling)
- Memory efficiency: 10x-100x better than hash sets
- Example: 1 billion URLs ≈ 1.2 GB memory (vs 12+ GB for hash set)
- Check speed: O(K) where K = number of hash functions (typically 3-7)

**Distributed Implementation:**

**Single Bloom Filter (Shared State):**
```python
# Redis-based shared Bloom Filter
import redis
from redisbloom.client import Client

rb = Client(host='redis-server', port=6379)
rb.bfCreate('seen_urls', 0.01, 1000000000)  # 1% error, 1B capacity

# Each worker checks/adds URLs
if not rb.bfExists('seen_urls', url):
    rb.bfAdd('seen_urls', url)
    crawl(url)
```

**Multi-Dimensional Bloom Filter:**
- Use MD5 hash preprocessing before Bloom Filter
- Reduces false positive rate
- Better distribution across bit array
- Recommended for large-scale crawls (billions of URLs)

**Trade-offs:**
- Memory vs Accuracy: Larger filter = lower false positive rate
- Centralized vs Distributed: Redis adds latency but ensures consistency
- Local filters faster but may duplicate work across nodes

#### Content-Based Deduplication

**Beyond URL Deduplication:**
- Hash page content (SHA-256 or SimHash)
- Detect pages that changed URLs but kept same content
- Identify near-duplicates (90%+ similar)

**Implementation:**
```python
import hashlib

def content_hash(html):
    # Normalize: remove whitespace, lowercase, strip HTML
    normalized = normalize_html(html)
    return hashlib.sha256(normalized.encode()).hexdigest()

# Store in distributed cache
if content_hash not in seen_content:
    seen_content.add(content_hash)
    process_page(html)
```

### Politeness Policies and Rate Limiting

#### Core Principles

**Definition:** Politeness policies involve rate-limiting that web crawlers provide to crawled web servers, ensuring respectful access that avoids overwhelming servers or consuming excessive resources.

**Common Heuristics:**
- **Standard wait time:** 10-15 seconds between requests to same host
- **Adaptive timing:** Wait time = 10x the most recent fetch time from that host
- **Server response monitoring:** Slow down or pause if server shows stress
- **Respect crawl-delay:** Honor explicit directives in robots.txt

#### Implementation Strategies

**Per-Host Queue with Timing:**
```python
class PolitenessManager:
    def __init__(self):
        self.last_access = {}  # hostname -> timestamp
        self.min_delay = 10  # seconds

    def can_crawl(self, hostname):
        if hostname not in self.last_access:
            return True
        elapsed = time.time() - self.last_access[hostname]
        return elapsed >= self.min_delay

    def record_access(self, hostname, fetch_time):
        self.last_access[hostname] = time.time()
        # Adaptive delay: 10x fetch time
        self.min_delay = max(10, fetch_time * 10)
```

**Distributed Politeness Coordination:**
- **Domain-specific queues:** Ensure one site isn't hit by all workers
- **Hash-based assignment:** Each host assigned to specific worker node
- **Shared state:** Redis/etcd to track last access times globally
- **Message queue partitioning:** Kafka partitions by hostname

#### Robots.txt Compliance

**Critical Requirements:**
- Parse robots.txt BEFORE queuing URLs
- Honor user-agent specific rules
- Respect crawl-delay directives
- Check disallow patterns
- Follow RFC 9309 specification

**Caching Strategy:**
```
Layer 1 (In-Memory): Top 1,000 domains, 12-hour TTL
Layer 2 (Redis): 100,000 domains, 24-hour TTL
Layer 3 (Database): All domains, 7-day TTL
```

**Best Practice:** Build robots.txt checking into URL frontier, not worker nodes.

**Longest Match Rule (RFC 9309):**
```
# If both Allow and Disallow match URL:
Allow: /path/to/
Disallow: /path/
# The longest (most specific) rule takes precedence → Allowed
```

**Failure Handling:**
- 403/401 on robots.txt → Assume full disallow
- Network timeout → Use cached version or retry
- Invalid syntax → Log warning, allow crawl

### Load Balancing and Task Distribution

#### Strategies

**Round-Robin:**
- Simplest approach
- Distributes URLs evenly across workers
- Doesn't account for task complexity or worker load

**Queue Depth-Based:**
- Assign tasks to worker with shortest queue
- Accounts for processing speed variations
- Requires worker load monitoring

**Consistent Hashing:**
- Hash hostname to determine worker assignment
- Same host always goes to same worker
- Excellent for DNS caching and politeness
- Handles worker joins/leaves gracefully

**Priority-Based:**
- High-priority URLs (homepage, sitemaps) go to dedicated workers
- Low-priority URLs fill in gaps
- Maximizes important content discovery rate

#### Auto-Scaling

**Scale-Up Triggers:**
- Queue depth > threshold (e.g., 10,000 URLs)
- Average wait time > target (e.g., 60 seconds)
- Worker CPU < 50% (underutilized)

**Scale-Down Triggers:**
- Queue depth < threshold (e.g., 1,000 URLs)
- Average wait time < target (e.g., 5 seconds)
- Worker CPU > 80% (consolidate work)

### Failure Handling and Fault Tolerance

#### Worker Node Failures

**Detection:**
- Master sends heartbeat to all workers regularly (every 30-60 seconds)
- Workers respond with status and progress checkpoint
- Missed heartbeats (3+ consecutive) → Mark worker as failed

**Recovery:**
1. Detect failed worker via missed heartbeats
2. Retrieve last checkpoint from worker's progress log
3. Re-queue incomplete tasks to message queue
4. Assign work to healthy workers
5. Update metadata to prevent duplicate work

**Self-Healing:**
- Redundancy ensures other workers continue without interruption
- No human intervention required for worker failures
- New workers can join pool dynamically

#### Master Node Failures

**Problem:** Master is single point of failure in master-worker architecture.

**Solutions:**

**Master Replication (Recommended):**
- Primary + standby masters
- Standby monitors primary health
- Automatic failover on primary failure
- Shared state via distributed database

**No Master (Alternative):**
- Fully decentralized via DHT or queue-based
- No single point of failure
- More complex coordination

#### Message Queue Failures

**Problem:** Queue broker failure stops entire crawl.

**Solutions:**

**Queue Clustering:**
- RabbitMQ cluster with 3+ nodes
- Redis Cluster for high availability
- Kafka multi-broker setup

**Message Persistence:**
- Persist messages to disk
- Replicate across brokers
- Ensures no message loss

**Worker Resilience:**
```python
while True:
    try:
        task = queue.get(timeout=30)
        process(task)
        queue.ack(task)
    except QueueConnectionError:
        logger.warning("Queue connection lost, retrying...")
        time.sleep(10)
        reconnect_to_queue()
```

#### URL Retry Logic

**Anti-Pattern: Immediate Retry Loop**
```python
# BAD: Creates infinite loop
try:
    fetch(url)
except:
    queue.put(url)  # Goes right back to main queue
```

**Best Practice: Exponential Backoff with Dead Letter Queue**
```python
class RetryManager:
    def __init__(self):
        self.retry_delays = [60, 300, 1800]  # 1min, 5min, 30min
        self.dead_letter_queue = []

    def handle_failure(self, url, attempt):
        if attempt >= len(self.retry_delays):
            # Move to dead letter queue for manual review
            self.dead_letter_queue.append(url)
            return

        delay = self.retry_delays[attempt]
        schedule_retry(url, delay, attempt + 1)
```

**Failure Categories:**
- **Transient (Retry):** Network timeout, 503 Service Unavailable, DNS temporary failure
- **Permanent (Skip):** 404 Not Found, 410 Gone, invalid URL
- **Rate Limit (Backoff):** 429 Too Many Requests, 403 Forbidden with retry-after
- **Unknown (Retry with caution):** 5xx errors, connection refused

---

## Technologies and Tools

### Message Queues

#### RabbitMQ

**Overview:** Message broker following AMQP (Advanced Message Queuing Protocol) standard, routing messages to exchanges and queues based on rules.

**Key Features:**
- Guaranteed message delivery
- Complex routing (topic, fanout, direct exchanges)
- Message acknowledgment and persistence
- Dead letter exchanges for failed messages
- Management UI and monitoring

**Performance:**
- Throughput: ~50,000 messages/second
- Latency: Low (single-digit milliseconds)
- Best for: Task queues with guaranteed delivery

**Use Case for Crawling:**
- Task distribution with delivery guarantees
- Complex routing (by domain, priority, content type)
- Worker acknowledgment ensures task completion

**Example:**
```python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='crawl_tasks', durable=True)

# Publish URL
channel.basic_publish(
    exchange='',
    routing_key='crawl_tasks',
    body='https://example.com',
    properties=pika.BasicProperties(delivery_mode=2)  # Persistent
)

# Consume URL
def callback(ch, method, properties, body):
    url = body.decode()
    crawl(url)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue='crawl_tasks', on_message_callback=callback)
```

**Pros:**
- Mature and stable
- Excellent documentation
- Built-in HA via clustering
- Flexible routing

**Cons:**
- Lower throughput than Kafka
- Doesn't store message history (once consumed, gone)
- Memory-based (not designed for long-term storage)

#### Apache Kafka

**Overview:** Distributed streaming platform designed for high throughput and long-term storage, treating messages as immutable log.

**Key Features:**
- Very high throughput (100K-1M+ messages/second)
- Persistent log with configurable retention
- Event replay capability (reprocess old messages)
- Partition-based parallelism
- Consumer groups for load balancing

**Performance:**
- Throughput: 100K-1M+ messages/second
- Latency: Moderate (10-100 milliseconds)
- Storage: Persistent, configurable retention (days to forever)
- Best for: High-volume event streaming, analytics pipelines

**Use Case for Crawling:**
- High-throughput URL distribution
- Crawl history and replay
- Real-time analytics on crawl progress
- Partition by hostname for politeness

**Example:**
```python
from kafka import KafkaProducer, KafkaConsumer

# Producer
producer = KafkaProducer(bootstrap_servers=['localhost:9092'])
producer.send('crawl_urls', b'https://example.com')

# Consumer with offset tracking
consumer = KafkaConsumer(
    'crawl_urls',
    bootstrap_servers=['localhost:9092'],
    group_id='crawler_group',
    auto_offset_reset='earliest'
)

for message in consumer:
    url = message.value.decode()
    crawl(url)
    # Offset committed automatically
```

**Pros:**
- Extremely high throughput
- Persistent storage enables replay
- Built for scale (billions of messages)
- Natural partitioning for distributed crawling

**Cons:**
- More complex setup and operations
- Higher latency than RabbitMQ/Redis
- Overkill for small-scale crawls
- Requires ZooKeeper (or KRaft mode)

#### Redis (Streams)

**Overview:** In-memory data structure store that can function as database, cache, and message broker.

**Key Features:**
- Extremely low latency (sub-millisecond)
- Multiple data structures (lists, sets, sorted sets, streams)
- Pub/Sub and Streams for messaging
- Persistence options (RDB, AOF)
- Simple setup and operation

**Performance:**
- Throughput: Up to 1 million messages/second
- Latency: Sub-millisecond
- Storage: In-memory (with disk persistence)
- Best for: Low latency, small workloads, already using Redis for caching

**Use Case for Crawling:**
- Lightweight task queues
- URL deduplication (Bloom filter, sets)
- Rate limiting state (last access times)
- Cache for robots.txt, DNS results
- Distributed locks

**Example:**
```python
import redis

r = redis.Redis(host='localhost', port=6379)

# Simple queue with list
r.lpush('crawl_queue', 'https://example.com')
url = r.brpop('crawl_queue', timeout=5)  # Blocking pop

# Redis Streams (more sophisticated)
r.xadd('crawl_stream', {'url': 'https://example.com'})
messages = r.xread({'crawl_stream': '0'}, count=10, block=5000)

# URL deduplication with set
if not r.sismember('seen_urls', url):
    r.sadd('seen_urls', url)
    crawl(url)

# Rate limiting
key = f'last_access:{hostname}'
if not r.exists(key) or (time.time() - float(r.get(key))) > 10:
    r.set(key, time.time())
    crawl(url)
```

**Pros:**
- Simplest to set up and use
- Extremely fast
- Versatile (queuing + caching + deduplication)
- Low operational overhead

**Cons:**
- In-memory limits scalability
- No complex routing like RabbitMQ
- Persistence guarantees weaker than Kafka
- Not designed for billions of messages

#### Comparison Summary

| Feature | RabbitMQ | Kafka | Redis |
|---------|----------|-------|-------|
| **Throughput** | 50K msg/s | 1M+ msg/s | 1M msg/s |
| **Latency** | Low (ms) | Medium (10-100ms) | Very Low (<1ms) |
| **Persistence** | Optional | Always | Optional |
| **Message Ordering** | Per queue | Per partition | Per stream |
| **Replay Capability** | No | Yes | Limited |
| **Complexity** | Medium | High | Low |
| **Best For** | Task queues | Event streaming | Caching + queuing |

**Recommendation for Event Crawling:**
- **Small scale (<10 workers, <100K URLs/day):** Redis
- **Medium scale (10-50 workers, complex routing):** RabbitMQ
- **Large scale (50+ workers, millions of events):** Kafka

### Distributed Coordination

#### Apache ZooKeeper

**Overview:** Distributed coordination service providing key-value store, leader election, distributed locks, and barriers. Originated in Hadoop ecosystem.

**Key Features:**
- Hierarchical namespace (like file system)
- Strong consistency guarantees (linearizable writes)
- Watch mechanism for change notifications
- Leader election and distributed locks
- Proven at massive scale (Hadoop, Kafka)

**Architecture:**
- Ensemble of 3-7 nodes (odd number for quorum)
- Leader handles all writes
- Followers serve reads and participate in consensus
- ZAB protocol for atomic broadcast

**Use Cases in Distributed Crawling:**
- Master election (high availability)
- Worker registration and discovery
- Configuration management
- Distributed locks for coordinated crawling
- Metadata storage (crawl statistics)

**Example:**
```python
from kazoo.client import KazooClient

zk = KazooClient(hosts='127.0.0.1:2181')
zk.start()

# Leader election
election = zk.Election("/master_election", "worker-1")
election.run(master_main_loop)  # Blocks until elected

# Worker registration
zk.create("/workers/worker-1", b"192.168.1.100", ephemeral=True)

# Distributed lock
lock = zk.Lock("/locks/domain/example.com")
with lock:
    crawl("example.com")  # Exclusive access
```

**Pros:**
- Battle-tested (10+ years in production)
- Strong consistency
- Rich feature set
- Large ecosystem and community

**Cons:**
- Complex operations and configuration
- Write scalability limited (single leader)
- Steep learning curve
- Heavy dependency (requires JVM)

#### etcd

**Overview:** Open-source distributed key-value store developed by CoreOS (now Red Hat), designed for distributed coordination with focus on simplicity, consistency, and reliability.

**Key Features:**
- HTTP/gRPC API (no client library required)
- Strong consistency (Raft consensus)
- Watch API for real-time notifications
- Lease mechanism for TTL
- Built-in leader election and locking
- Simpler than ZooKeeper

**Architecture:**
- Cluster of 3-5 nodes
- Raft protocol for consensus
- Leader handles reads and writes
- Automatic leader failover

**Use Cases in Distributed Crawling:**
- Service discovery (worker registration)
- Configuration storage
- Distributed locks
- Leader election
- Metadata coordination

**Example:**
```python
import etcd3

etcd = etcd3.client(host='localhost', port=2379)

# Service registration with lease
lease = etcd.lease(300)  # 300 seconds TTL
etcd.put('/workers/worker-1', '192.168.1.100', lease=lease)

# Distributed lock
lock = etcd.lock('domain:example.com')
lock.acquire()
try:
    crawl('example.com')
finally:
    lock.release()

# Watch for configuration changes
watch_id = etcd.add_watch_callback('/config/crawl_rate', callback)
```

**Pros:**
- Simpler than ZooKeeper
- HTTP/gRPC API (language agnostic)
- Modern design and implementation
- Lower operational complexity
- Used by Kubernetes (proven at scale)

**Cons:**
- Smaller ecosystem than ZooKeeper
- Write throughput limited
- Newer (less battle-tested than ZooKeeper)

#### Consul

**Overview:** Service discovery, configuration management, and service mesh solution developed by HashiCorp with built-in health checking and key-value store.

**Key Features:**
- Service discovery and health checking
- Multi-datacenter support
- Key-value store with watches
- Built-in DNS and HTTP interface
- Gossip protocol for cluster coordination
- More features than etcd/ZooKeeper

**Architecture:**
- Server agents (3-5 nodes)
- Client agents (on every worker)
- Gossip protocol (Serf) for membership
- Raft consensus for consistency

**Use Cases in Distributed Crawling:**
- Service discovery with health checks
- Dynamic worker pool management
- Configuration management
- DNS-based load balancing
- Coordination across data centers

**Example:**
```python
import consul

c = consul.Consul()

# Service registration with health check
c.agent.service.register(
    'crawler-worker',
    service_id='worker-1',
    address='192.168.1.100',
    port=8080,
    check=consul.Check.http('http://192.168.1.100:8080/health', interval='10s')
)

# Service discovery
index, services = c.health.service('crawler-worker', passing=True)
for service in services:
    print(f"Healthy worker: {service['Service']['Address']}")

# KV store
c.kv.put('config/crawl_rate', '10')
index, data = c.kv.get('config/crawl_rate')
```

**Pros:**
- Most feature-rich (service discovery + KV + health)
- Multi-datacenter support
- Built-in health checking
- Good UI and monitoring
- HashiCorp ecosystem integration

**Cons:**
- More complex than needed for simple coordination
- Heavier resource usage
- Gossip overhead in large clusters

#### Comparison Summary

| Feature | ZooKeeper | etcd | Consul |
|---------|-----------|------|--------|
| **API** | Java client | HTTP/gRPC | HTTP/DNS |
| **Consensus** | ZAB | Raft | Raft |
| **Maturity** | Very mature | Mature | Mature |
| **Simplicity** | Complex | Simple | Medium |
| **Service Discovery** | No | No | Yes (built-in) |
| **Health Checks** | No | No | Yes (built-in) |
| **Multi-DC** | No | No | Yes |
| **Best For** | Hadoop ecosystem | Kubernetes, modern apps | Service mesh, discovery |

**Recommendation for Event Crawling:**
- **Simple coordination, already using K8s:** etcd
- **Need service discovery + health checks:** Consul
- **Large Hadoop ecosystem:** ZooKeeper
- **Minimal setup for small project:** Redis (simpler alternative)

### Crawler Frameworks

#### Scrapy with Distributed Extensions

**Overview:** Scrapy is a popular Python web scraping framework with modular architecture. For distributed crawling, combine with:

**Scrapy + Frontera:**
- Distributed crawl frontier
- Pluggable backends (HBase, SQLite)
- URL prioritization and filtering
- Works with Scrapy spiders

**Scrapy + Scrapy-Redis:**
- Redis-based shared queue
- Duplicate filtering with Redis sets
- Distributed spiders across multiple servers
- Simple setup for small-medium scale

**Architecture:**
```
Scrapy Spider → Scrapy-Redis → Redis Queue
                    ↓
              Multiple Spiders (Workers)
                    ↓
              MongoDB/PostgreSQL
```

**Example:**
```python
# settings.py
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
REDIS_URL = 'redis://localhost:6379'

# spider.py
from scrapy_redis.spiders import RedisSpider

class EventSpider(RedisSpider):
    name = 'event_spider'
    redis_key = 'event_spider:start_urls'

    def parse(self, response):
        # Extract events
        for event in response.css('.event'):
            yield {
                'title': event.css('.title::text').get(),
                'date': event.css('.date::text').get(),
            }
```

**Pros:**
- Mature Python framework
- Rich middleware ecosystem
- Good documentation
- Easy to extend

**Cons:**
- Python GIL limits parallelism within process
- Not designed for massive scale (billions of pages)
- Requires additional tools for true distribution

#### Apache Nutch

**Overview:** Java-based crawler developed by Apache Software Foundation for enterprise and research-scale crawling, leveraging Hadoop MapReduce for distributed processing.

**Key Features:**
- Batch-driven architecture (fetch → parse → index as separate jobs)
- Hadoop/HDFS for distributed storage and processing
- Plugin architecture for extensibility
- Built-in duplicate detection and URL normalization
- Designed for web search engine scale

**Architecture:**
```
Injector → Generator → Fetcher → Parser → Indexer
   ↓          ↓           ↓         ↓        ↓
             Hadoop MapReduce Jobs
   ↓          ↓           ↓         ↓        ↓
                    HDFS Storage
```

**Processing Stages:**
1. **Inject:** Seed URLs into CrawlDB
2. **Generate:** Select URLs to fetch (batch)
3. **Fetch:** Download pages (MapReduce)
4. **Parse:** Extract links and content (MapReduce)
5. **Index:** Send to Solr/Elasticsearch
6. **Repeat**

**Batch Nature Trade-offs:**
- **CPU/Network usage spikes:** High network during fetch, high CPU during parse
- **Latency:** Hours between discovering URL and crawling it
- **Complexity:** Many moving parts (Hadoop, HDFS, JobTracker)

**Pros:**
- Proven at massive scale (billions of pages)
- Excellent distributed storage via HDFS
- Fault tolerant (Hadoop handles failures)
- Rich plugin ecosystem

**Cons:**
- Batch processing causes latency
- Complex setup (requires Hadoop cluster)
- Java-based (barrier for Python developers)
- Resource-intensive

#### StormCrawler

**Overview:** SDK for building distributed web crawlers using Apache Storm stream processing framework, designed as modern alternative to Nutch.

**Key Features:**
- Stream processing (real-time, continuous)
- DAG-based topology (vs batch jobs)
- All operations happen simultaneously
- Native integration with Elasticsearch, Kafka
- XPath extraction, sitemap processing
- Live monitoring via Kibana

**Architecture:**
```
Spouts (URL sources) → Bolts (processing) → Sinks (storage)
        ↓                      ↓                  ↓
    Kafka Queue     Fetch → Parse → Index    Elasticsearch
```

**Storm Topology Example:**
```
URLSpout → FetcherBolt → ParserBolt → IndexerBolt
             ↓              ↓             ↓
        DNS Cache      Extract Links   Elasticsearch
```

**Comparison with Nutch:**

| Aspect | Nutch (Batch) | StormCrawler (Stream) |
|--------|---------------|----------------------|
| **Processing** | Sequential jobs | Continuous pipeline |
| **Latency** | Hours | Seconds-minutes |
| **Resource Usage** | Spiky | Consistent |
| **Complexity** | Higher | Lower |
| **Scale** | Billions of pages | Millions-billions |

**Pros:**
- Real-time processing (low latency)
- Smoother resource utilization
- Modern architecture
- Better integration with big data tools

**Cons:**
- Requires Storm infrastructure
- Smaller community than Nutch/Scrapy
- Java-based
- Less mature than Nutch

**Verdict:** "StormCrawler is a combination of Nutch's scalability and Scrapy's user-friendliness."

#### Comparison Summary

| Framework | Language | Scale | Processing | Best For |
|-----------|----------|-------|------------|----------|
| **Scrapy + Redis** | Python | Small-Medium | Real-time | Python devs, moderate scale |
| **Apache Nutch** | Java | Massive | Batch | Search engines, archives |
| **StormCrawler** | Java | Large | Stream | Real-time crawling, analytics |
| **Custom (Queue-based)** | Any | Variable | Real-time | Full control, specific needs |

**Recommendation for Events Agent:**
- **Current (Single-process):** Keep it simple
- **First distributed step:** Scrapy + Redis (Python ecosystem)
- **Need real-time:** StormCrawler or custom queue-based
- **Archive-scale (billions):** Apache Nutch

---

## Scalability Challenges

### URL Deduplication at Scale

**Challenge:** With billions of URLs, even 1 byte per URL = gigabytes of memory.

**Problem Dimensions:**
- **Memory:** 1 billion URLs × 100 bytes = 100 GB
- **Speed:** Must check millions of URLs per second
- **Distribution:** Multiple workers need shared state
- **False positives:** Some duplication acceptable (1-2%)

**Solutions:**

**1. Bloom Filter (Primary Approach)**
- Memory: 1 billion URLs ≈ 1.2 GB (vs 100+ GB for hash set)
- Speed: O(K) hash operations (K=3-7)
- Accuracy: 1-2% false positive rate
- Distribution: Shared Redis Bloom Filter

**2. Multi-Dimensional Bloom Filter**
- MD5 hash preprocessing
- Reduces false positives
- Better bit distribution
- Recommended for 10B+ URLs

**3. URL Normalization**
```python
def normalize_url(url):
    # Remove fragments, sort query params, lowercase
    parsed = urlparse(url.lower())
    query = sorted(parse_qsl(parsed.query))
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path.rstrip('/'),
        '',
        urlencode(query),
        ''  # No fragment
    ))
```

**4. Content-Based Deduplication**
- Hash normalized page content
- Detect URL changes with same content
- Use SimHash for near-duplicate detection

**5. Distributed Hash Table**
- Partition URL space across nodes
- Each node handles subset
- No shared state needed
- Natural for P2P architectures

**Trade-off Matrix:**

| Method | Memory | Accuracy | Distribution Complexity |
|--------|--------|----------|------------------------|
| Hash Set | Very High | 100% | High (sync required) |
| Bloom Filter | Low | 98-99% | Medium (shared Redis) |
| DHT | Medium | 100% | Low (partitioned) |
| Content Hash | Medium | 95% | Medium |

### Distributed DNS Resolution

**Challenge:** DNS resolution is a well-known bottleneck in web crawling, requiring multiple requests and round-trips across the internet, taking seconds or longer.

**Impact:**
- DNS lookup: 50-500ms per domain
- At 1000 URLs/sec, 50% new domains = 250-2500ms average latency
- Politeness limits cache hit rate (only 1 URL per domain every 10s)

**Solutions:**

**1. Multi-Layer DNS Caching**
```
Layer 1: In-memory LRU (10K domains, 5-min TTL)
Layer 2: Redis cache (100K domains, 1-hour TTL)
Layer 3: Local DNS resolver (OS cache)
Layer 4: Public DNS (8.8.8.8, 1.1.1.1)
```

**2. Prefetching Strategy**
```python
class DNSPrefetcher:
    def prefetch(self, urls):
        # Extract unique domains
        domains = set(urlparse(url).netloc for url in urls)

        # Async DNS resolution
        loop = asyncio.get_event_loop()
        tasks = [loop.getaddrinfo(domain, 80) for domain in domains]
        loop.run_until_complete(asyncio.gather(*tasks))
```

**3. Domain Grouping**
- Crawl all URLs from same domain in sequence
- Single DNS lookup serves multiple URLs
- Natural with per-domain politeness queues

**4. Shared DNS Cache (Redis)**
```python
def resolve_hostname(hostname):
    # Check cache
    cached = redis.get(f'dns:{hostname}')
    if cached:
        return cached

    # Resolve and cache
    ip = socket.gethostbyname(hostname)
    redis.setex(f'dns:{hostname}', 3600, ip)
    return ip
```

**Best Practices:**
- Cache for at least 1 hour (DNS TTL typically 300-3600s)
- Use async DNS resolution libraries (aiodns)
- Pre-warm cache for known domains
- Monitor cache hit rate (target >80%)

### Robots.txt Caching

**Challenge:** Must fetch and parse robots.txt before crawling any domain, but millions of domains = millions of requests.

**Complexity:**
- Must fetch BEFORE queuing URLs
- One robots.txt per domain
- Can change over time (need refresh)
- Parsing is CPU-intensive
- Distributed workers need shared state

**Solutions:**

**1. Multi-Tier Cache (Recommended)**
```
Tier 1: In-memory (top 1K domains, 12-hour TTL)
Tier 2: Redis (100K domains, 24-hour TTL)
Tier 3: PostgreSQL (all domains, 7-day TTL)
```

**2. Lazy Loading + Proactive Refresh**
```python
class RobotsTxtManager:
    def can_fetch(self, url):
        domain = urlparse(url).netloc

        # Check cache
        robots = cache.get(f'robots:{domain}')
        if not robots:
            # Fetch and cache
            robots = fetch_robots_txt(domain)
            cache.setex(f'robots:{domain}', 86400, robots)

        return robots.can_fetch('*', url)

    def refresh_popular_domains(self):
        # Proactively refresh top 1000 domains
        for domain in get_top_domains(1000):
            robots = fetch_robots_txt(domain)
            cache.setex(f'robots:{domain}', 86400, robots)
```

**3. Integration with URL Frontier**
```python
# Check robots.txt when adding to frontier, not when crawling
def add_to_frontier(url):
    if robots_manager.can_fetch(url):
        frontier.add(url)
    else:
        logger.info(f"Blocked by robots.txt: {url}")
```

**4. Handling Failures**
```python
def fetch_robots_txt(domain):
    try:
        response = requests.get(f'https://{domain}/robots.txt', timeout=10)
        if response.status_code == 403 or response.status_code == 401:
            return RobotFileParser()  # Empty = disallow all
        elif response.status_code == 404:
            return AllowAllParser()  # No robots.txt = allow all
        else:
            return parse_robots_txt(response.text)
    except Timeout:
        return cached_version or AllowAllParser()
```

**Caching Controversy:**
- **Long cache (24h+):** Reduces load, but delays detecting changes
- **Short cache (1h):** More up-to-date, but higher overhead
- **Recommendation:** 24h for regular domains, 1h for frequently changing domains

**Monitoring:**
- Cache hit rate (target >95%)
- 403/401 rate (indicate blocking)
- Parse errors (log for investigation)

### Bandwidth Management

**Challenge:** Bandwidth for conducting crawls is neither infinite nor free. With billions of fetches, careful throttling is essential.

**Issues:**
- Network bandwidth costs
- Crawler traps (endless dynamic pages designed to exhaust bandwidth)
- Target server bandwidth consumption
- ISP rate limits

**Solutions:**

**1. Global Bandwidth Throttling**
```python
class BandwidthThrottler:
    def __init__(self, max_mbps=100):
        self.max_bytes_per_sec = max_mbps * 1024 * 1024 / 8
        self.current_usage = 0
        self.window_start = time.time()

    def can_fetch(self, expected_size):
        elapsed = time.time() - self.window_start
        if elapsed >= 1.0:
            # Reset window
            self.current_usage = 0
            self.window_start = time.time()
            return True

        if self.current_usage + expected_size > self.max_bytes_per_sec:
            return False

        self.current_usage += expected_size
        return True
```

**2. Per-Worker Bandwidth Limits**
- Distribute total bandwidth across workers
- Each worker tracks local usage
- Prevents single worker consuming all bandwidth

**3. Response Size Limits**
```python
# Streaming download with size limit
def fetch_with_limit(url, max_size=10*1024*1024):  # 10 MB
    response = requests.get(url, stream=True)
    content = b''
    for chunk in response.iter_content(chunk_size=8192):
        content += chunk
        if len(content) > max_size:
            raise ContentTooLarge(f"Exceeded {max_size} bytes")
    return content
```

**4. Crawler Trap Detection**
```python
class TrapDetector:
    def __init__(self):
        self.url_counts = {}  # domain -> count

    def is_trap(self, url):
        domain = urlparse(url).netloc
        self.url_counts[domain] = self.url_counts.get(domain, 0) + 1

        # More than 1000 URLs from same domain = likely trap
        if self.url_counts[domain] > 1000:
            return True

        # Detect patterns: /page/1, /page/2, ... /page/999999
        if re.match(r'.*/\d{5,}$', url):
            return True

        return False
```

**5. Content-Type Filtering**
```python
# Only crawl HTML pages
def should_crawl(url, headers):
    content_type = headers.get('Content-Type', '')
    return 'text/html' in content_type
```

**Monitoring:**
- Total bandwidth per day/hour
- Average page size
- Top bandwidth consumers (domains)
- Trap detection triggers

### Crawl Frontier Partitioning

**Challenge:** Distribute URL frontier across multiple nodes while maintaining politeness and avoiding duplication.

**Partitioning Strategies:**

**1. By Hostname (Recommended)**
```python
# Consistent hashing
def get_worker_for_url(url, num_workers):
    hostname = urlparse(url).netloc
    worker_id = hash(hostname) % num_workers
    return worker_id
```

**Advantages:**
- Natural politeness (each domain handled by one worker)
- Excellent DNS caching (all URLs from domain on same worker)
- No cross-worker coordination for rate limiting

**Disadvantages:**
- Uneven load if URL distribution skewed
- Hot domains create bottlenecks

**2. By URL Hash**
```python
def get_worker_for_url(url, num_workers):
    worker_id = hash(url) % num_workers
    return worker_id
```

**Advantages:**
- Better load distribution
- Uniform work across workers

**Disadvantages:**
- Breaks politeness (same domain across multiple workers)
- Requires coordination for rate limiting
- Poor DNS cache hit rate

**3. Hybrid Approach**
```python
def get_worker_for_url(url, num_workers):
    hostname = urlparse(url).netloc

    # Popular domains get dedicated workers
    if hostname in POPULAR_DOMAINS:
        return POPULAR_DOMAINS[hostname]

    # Others distributed by hash
    return hash(hostname) % (num_workers - len(POPULAR_WORKERS))
```

**4. Dynamic Rebalancing**
```python
class DynamicPartitioner:
    def rebalance(self):
        # Monitor queue depths
        queue_depths = get_worker_queue_depths()

        # If imbalanced, redistribute some domains
        overloaded = [w for w in workers if queue_depths[w] > THRESHOLD]
        underloaded = [w for w in workers if queue_depths[w] < THRESHOLD]

        for worker in overloaded:
            domains = get_worker_domains(worker)
            # Move least active domains to underloaded workers
            for domain in domains[-10:]:
                reassign_domain(domain, underloaded[0])
```

**Kafka-Based Partitioning (Distributed Frontera):**
- URLs published to Kafka topic
- Topic partitioned by hostname hash
- Each consumer (worker) reads from assigned partitions
- Kafka guarantees same hostname always to same consumer
- Built-in politeness and load balancing

**Trade-offs:**

| Strategy | Politeness | Load Balance | DNS Cache | Complexity |
|----------|-----------|--------------|-----------|------------|
| By Hostname | Excellent | Poor | Excellent | Low |
| By URL Hash | Poor | Excellent | Poor | High |
| Hybrid | Good | Good | Good | Medium |
| Kafka-based | Excellent | Good | Excellent | Medium |

---

## Real-World Examples

### Google's Crawler Architecture (Caffeine)

**Overview:** Complete rebuild of Google's indexing system announced in 2010, designed to address exponential growth of web content.

**Historical Context:**
- **1998 (Original):** 2.4 million websites, 188 million internet users
- **2009 (Pre-Caffeine):** 238 million websites (100x), 1.8 billion users (10x)
- **Need:** System couldn't keep pace with growth

**Old Architecture:**
- Multiple index layers refreshed at different rates
- Main layer updated every couple of weeks
- Batch processing model
- Stale results between updates

**Caffeine Architecture:**

**1. Continuous Indexing**
- Analyzes web in small portions (not massive batches)
- Updates index on continuous basis globally
- New pages/information added straight to index
- No waiting for batch completion

**2. Real-Time Processing**
- Processes hundreds of thousands of pages in parallel every second
- Analyzes crawled pages in real-time
- Extracts text, images, structured data
- Stores in different index tiers (Base, Zeppelins, Landfills)

**3. Massive Scale**
- Nearly 100 million gigabytes of storage
- Hundreds of thousands of gigabytes added daily
- Distributed across thousands of machines
- Global infrastructure

**4. Incremental Updates**
- Incremental and continuous crawling
- Find and index web content much faster
- 50% fresher results than old index
- Largest collection of web content offered

**Key Innovations:**
- Real-time processing pipeline (no batch delays)
- Tiered storage system (hot/warm/cold data)
- Massively parallel architecture
- Continuous improvement (always learning)

**Lessons for Distributed Crawlers:**
- Batch processing doesn't scale to internet growth
- Real-time/continuous better than periodic updates
- Tiered storage optimizes cost/performance
- Parallelism is essential at scale

### Common Crawl

**Overview:** Open repository of web crawl data that can be accessed and analyzed by anyone, serving as major resource for researchers and developers.

**Mission:**
- Build and maintain open web crawl data
- Democratize access to web-scale data
- Enable research and analysis

**Architecture:**

**1. Crawling Infrastructure**
- Uses Apache Nutch for crawling
- Deployed on Amazon EC2
- Runs monthly crawls
- Covers billions of web pages

**2. Storage**
- WARC (Web ARChive) format
- Stored on Amazon S3 (public dataset)
- Petabytes of data
- Compressed and indexed

**3. Data Format**
```
WARC Files: Raw HTML, headers, metadata
WET Files: Extracted plaintext
WAT Files: Computed metadata (links, language, etc.)
```

**4. Access Methods**
- Direct S3 access (free egress for AWS users)
- Athena SQL queries
- EMR for big data processing
- Download individual files

**Scale:**
- **Monthly crawl:** 3-5 billion web pages
- **Total archive:** 250+ billion pages (as of 2024)
- **Storage:** 400+ TB per monthly crawl
- **Free and open:** No cost for data access on AWS

**Architecture Insights:**
- Leverage cloud infrastructure (EC2, S3)
- Standard formats (WARC) enable interoperability
- Monthly batch crawls (not real-time)
- Open data model encourages usage

**Use Cases:**
- NLP and machine learning training data
- Web research and analysis
- Search engine development
- Historical web analysis

**Lessons for Distributed Crawlers:**
- Cloud infrastructure reduces operational burden
- Standard formats important for data sharing
- Batch crawls still viable for archival use cases
- Open data creates ecosystem value

### Open Source Examples

**1. UbiCrawler (Academic)**
- Fully distributed web crawler from University of Milan
- Peer-to-peer architecture (no central coordinator)
- Fault-tolerant design
- Scalable to hundreds of nodes
- Used for web graph analysis

**Key Features:**
- Consistent hashing for URL assignment
- Asynchronous communication
- Self-organizing coordinator ring
- Handles node failures gracefully

**2. Crawlab (Production)**
- Open-source distributed crawler management platform
- Supports any language/framework
- Web UI for spider management
- Built on Go, Vue.js

**Architecture:**
```
Master Node → Scheduling, monitoring
Worker Nodes → Execute spiders, store results
MongoDB → Metadata and configuration
SeaweedFS → Distributed file storage
gRPC → Communication protocol
```

**Use Cases:**
- Managing multiple Scrapy projects
- Distributed task scheduling
- Monitoring and analytics
- Team collaboration

**3. StormCrawler Examples**
- DigitalPebble maintains reference implementations
- Used by web archiving organizations
- Powers commercial web monitoring services
- Integrated with Elasticsearch for search

**4. Nutch Deployments**
- Yahoo! (historically, for search indexing)
- Various national libraries (web archiving)
- Academic research (web graph analysis)
- Enterprise search solutions

---

## Recommendations for Events Agent

### Current State Analysis

**System:**
- Single-process Python crawler
- 9 event sources (Luma, Meetup, Eventbrite, Fever, Cozymeal, Jazz Near You, Songkick, TimeOut, DoNYC)
- SQLite database with deduplication
- ~104 tests (good coverage)
- Playwright-based crawling

**Scale:**
- NYC-focused event aggregation
- Thousands of events per crawl
- Daily or weekly crawl cadence
- Manageable with single process currently

**Strengths:**
- Simple architecture (easy to maintain)
- Good test coverage
- Solid database design
- Effective deduplication

**Limitations:**
- Single point of failure
- Limited throughput (sequential crawling)
- No fault recovery
- Difficult to scale beyond single machine

### When to Distribute

**Don't Distribute Yet If:**
- Current crawl completes in <1 hour
- Single machine has sufficient resources
- Simplicity valued over performance
- Team size small (1-2 developers)

**Distribute When:**
- Crawl time exceeds acceptable window (e.g., >2 hours)
- Adding more sources (e.g., 20+ sources)
- Need faster refresh rate (hourly vs daily)
- Reliability requirements increase (SLA needed)
- Scaling beyond single region (e.g., multiple cities)

### Recommended Architecture (Phased Approach)

#### Phase 1: Multi-Process (Low Complexity)

**Goal:** Parallelize crawling without distributed infrastructure.

**Changes:**
```python
# main.py
from multiprocessing import Pool

def crawl_source(source_name):
    crawler = get_crawler(source_name)
    events = crawler.crawl(browser, "nyc")
    repo.save_many(events)
    return len(events)

if __name__ == '__main__':
    sources = ['luma', 'meetup', 'eventbrite', ...]

    with Pool(processes=4) as pool:
        results = pool.map(crawl_source, sources)

    print(f"Total events: {sum(results)}")
```

**Advantages:**
- Minimal code changes
- 3-4x speedup (9 sources / 3-4 processes)
- No new infrastructure
- Same database (SQLite handles concurrent writes with WAL mode)

**Limitations:**
- Still single machine
- Limited to CPU cores
- Shared database may bottleneck

**Cost:** ~1 day implementation

#### Phase 2: Queue-Based with Redis (Medium Complexity)

**Goal:** Enable distributed workers with minimal infrastructure.

**Architecture:**
```
Main Process → Redis Queue → Worker Pool → PostgreSQL
     ↓              ↑            ↓              ↑
  Seed URLs    New URLs      Crawl        Save Events
```

**Components:**

**1. Redis Queue:**
```python
# producer.py
import redis
r = redis.Redis()

# Seed crawl tasks
sources = ['luma', 'meetup', 'eventbrite', ...]
for source in sources:
    r.lpush('crawl_tasks', json.dumps({'source': source, 'location': 'nyc'}))
```

**2. Worker:**
```python
# worker.py
import redis
r = redis.Redis()

while True:
    task = r.brpop('crawl_tasks', timeout=5)
    if not task:
        continue

    data = json.loads(task[1])
    crawler = get_crawler(data['source'])
    events = crawler.crawl(browser, data['location'])

    # Save to PostgreSQL (better for distributed writes)
    repo.save_many(events)

    # URL deduplication
    for url in discovered_urls:
        if not r.sismember('seen_urls', url):
            r.sadd('seen_urls', url)
            r.lpush('crawl_tasks', url)
```

**3. Monitoring:**
```python
# monitor.py
while True:
    queue_depth = r.llen('crawl_tasks')
    seen_count = r.scard('seen_urls')
    print(f"Queue: {queue_depth}, Seen: {seen_count}")
    time.sleep(10)
```

**Migration:**
- Migrate SQLite → PostgreSQL (better for distributed writes)
- Use `psycopg2` or `asyncpg`
- Keep schema identical (minimal code changes)

**Advantages:**
- Easy horizontal scaling (add more workers)
- Fault tolerance (task persists if worker dies)
- Simple retry logic
- Low operational complexity

**Limitations:**
- Redis single point of failure (mitigate with Redis Cluster)
- Limited message queue features
- No built-in politeness coordination

**Cost:** ~1 week implementation + 1 day testing

**Infrastructure:**
- 1 Redis instance (~$20/month on cloud)
- 1 PostgreSQL instance (~$20/month)
- 2-4 worker VMs (~$40-80/month)
- Total: ~$80-120/month

#### Phase 3: Production-Grade (High Complexity)

**Goal:** Enterprise-ready system with full fault tolerance and monitoring.

**Architecture:**
```
Scheduler → Kafka → Worker Pool → PostgreSQL
    ↓         ↓         ↓              ↑
  etcd    Partitions  Metrics     Analytics DB
```

**Components:**

**1. Kafka for Task Distribution:**
- Partition by hostname for politeness
- Persistent log enables replay
- High throughput (100K+ URLs/sec)

**2. etcd for Coordination:**
- Service discovery (worker registration)
- Configuration management
- Distributed locks for critical sections

**3. Worker Pool (Kubernetes):**
- Auto-scaling based on queue depth
- Health checks and automatic recovery
- Rolling updates for zero downtime

**4. Monitoring (Prometheus + Grafana):**
- Crawl rate metrics
- Error rates by source
- Queue depth over time
- Worker health and resource usage

**5. Politeness Manager:**
```python
class DistributedPolitenessManager:
    def __init__(self):
        self.redis = redis.Redis()

    def can_crawl(self, hostname):
        key = f'last_access:{hostname}'
        last_access = self.redis.get(key)

        if not last_access:
            return True

        elapsed = time.time() - float(last_access)
        return elapsed >= 10  # 10 second delay

    def record_access(self, hostname):
        key = f'last_access:{hostname}'
        self.redis.setex(key, 60, str(time.time()))
```

**Advantages:**
- True enterprise scale (millions of events)
- High availability (no single point of failure)
- Comprehensive monitoring and alerting
- Automated scaling and recovery

**Limitations:**
- High complexity (requires DevOps expertise)
- Significant operational overhead
- Higher costs

**Cost:** ~4-6 weeks implementation + 2 weeks testing

**Infrastructure:**
- 3-node Kafka cluster (~$150/month)
- 3-node etcd cluster (~$60/month)
- PostgreSQL HA (~$100/month)
- 5-10 worker nodes (~$200-400/month)
- Monitoring stack (~$50/month)
- Total: ~$560-760/month

### Decision Framework

**Choose Phase 1 (Multi-Process) If:**
- Crawl time 1-3 hours (acceptable but could be better)
- Budget constrained
- Small team (1-2 developers)
- Prototype or MVP stage

**Choose Phase 2 (Redis Queue) If:**
- Crawl time >3 hours (need significant speedup)
- Adding 10+ new sources
- Need fault tolerance
- Team comfortable with basic distributed systems
- Budget allows $100-200/month for infrastructure

**Choose Phase 3 (Production) If:**
- Mission-critical application (SLA required)
- 50+ sources or multiple regions
- Need sub-hour refresh rates
- Large team (3+ developers)
- Budget allows $500-1000/month for infrastructure

### Technology Stack Recommendations

**For Events Agent Specifically:**

**Recommended (Phase 2):**
- **Message Queue:** Redis (simplest, sufficient for medium scale)
- **Database:** PostgreSQL (better than SQLite for distributed writes)
- **Coordination:** None initially (Redis sufficient), add etcd if needed later
- **Deduplication:** Redis Sets (simple) or Bloom Filter (if millions of URLs)
- **Monitoring:** Simple logging initially, add Prometheus later

**Why Not Others:**
- **RabbitMQ:** More complex than needed, Redis sufficient
- **Kafka:** Overkill for event crawling (not real-time streaming)
- **ZooKeeper:** Too complex, etcd simpler if needed
- **Consul:** Service discovery not needed for small worker pool

**Migration Path:**
```
Current (Single-process)
    ↓ [1 day]
Phase 1 (Multi-process)
    ↓ [1 week]
Phase 2 (Redis + PostgreSQL)
    ↓ [if needed, 4-6 weeks]
Phase 3 (Kafka + K8s)
```

### Specific Implementation Recommendations

**1. Database Migration (SQLite → PostgreSQL):**

```sql
-- PostgreSQL schema (same as SQLite)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    start_datetime TIMESTAMP NOT NULL,
    -- ... other fields ...
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(event_id, source)
);

-- Indexes (same as SQLite)
CREATE INDEX idx_events_source ON events(source);
CREATE INDEX idx_events_start_datetime ON events(start_datetime);
-- ... other indexes ...
```

**Migration Script:**
```bash
# Export from SQLite
sqlite3 data/events.db ".mode csv" ".output events.csv" "SELECT * FROM events;"

# Import to PostgreSQL
psql -d events_db -c "\COPY events FROM 'events.csv' CSV HEADER;"
```

**2. URL Deduplication:**

```python
# Option A: Redis Set (simple, exact matching)
class RedisDeduplicator:
    def __init__(self):
        self.redis = redis.Redis()

    def is_seen(self, url):
        return self.redis.sismember('seen_urls', url)

    def mark_seen(self, url):
        self.redis.sadd('seen_urls', url)

# Option B: Redis Bloom Filter (memory efficient)
from redisbloom.client import Client

class BloomDeduplicator:
    def __init__(self):
        self.rb = Client(host='localhost', port=6379)
        # 1% error rate, 10 million capacity
        self.rb.bfCreate('seen_urls', 0.01, 10000000)

    def is_seen(self, url):
        return self.rb.bfExists('seen_urls', url)

    def mark_seen(self, url):
        self.rb.bfAdd('seen_urls', url)
```

**3. Politeness Management:**

```python
class EventCrawlerPoliteness:
    def __init__(self):
        self.redis = redis.Redis()
        self.min_delay = 10  # seconds

    def wait_if_needed(self, source):
        """Wait if we crawled this source recently."""
        key = f'last_crawl:{source}'
        last_crawl = self.redis.get(key)

        if last_crawl:
            elapsed = time.time() - float(last_crawl)
            if elapsed < self.min_delay:
                sleep_time = self.min_delay - elapsed
                logger.info(f"Waiting {sleep_time:.1f}s for {source}")
                time.sleep(sleep_time)

        # Record this crawl
        self.redis.setex(key, 60, str(time.time()))
```

**4. Monitoring and Alerting:**

```python
# Simple metrics collection
class CrawlMetrics:
    def __init__(self):
        self.redis = redis.Redis()

    def record_crawl(self, source, event_count, duration):
        timestamp = int(time.time())

        # Time series in Redis
        self.redis.zadd(f'metrics:{source}:events', {timestamp: event_count})
        self.redis.zadd(f'metrics:{source}:duration', {timestamp: duration})

        # Trim old data (keep 7 days)
        cutoff = timestamp - (7 * 24 * 3600)
        self.redis.zremrangebyscore(f'metrics:{source}:events', 0, cutoff)

    def get_stats(self, source):
        # Get last 24 hours
        cutoff = int(time.time()) - (24 * 3600)
        events = self.redis.zrangebyscore(f'metrics:{source}:events', cutoff, '+inf', withscores=True)

        total_events = sum(score for _, score in events)
        avg_events = total_events / len(events) if events else 0

        return {
            'total_events_24h': total_events,
            'avg_events_per_crawl': avg_events,
            'crawls_24h': len(events)
        }
```

### Testing Strategy for Distributed System

**1. Unit Tests (Existing):**
- Keep all existing tests
- Add tests for new components (queue, deduplication)

**2. Integration Tests:**
```python
def test_distributed_crawl():
    # Start Redis
    redis_client = redis.Redis()
    redis_client.flushall()

    # Seed tasks
    redis_client.lpush('crawl_tasks', json.dumps({'source': 'luma', 'location': 'nyc'}))

    # Run worker
    worker = CrawlWorker(redis_client)
    worker.process_one_task()

    # Verify results
    events = repo.find_by_source('luma')
    assert len(events) > 0
```

**3. Load Tests:**
```python
def test_concurrent_workers():
    # Simulate 4 workers processing same queue
    with Pool(processes=4) as pool:
        results = pool.map(worker.process_tasks, range(4))

    # Verify no duplicate events (test deduplication)
    all_events = repo.find_all()
    event_ids = [e.event_id for e in all_events]
    assert len(event_ids) == len(set(event_ids))  # No duplicates
```

**4. Failure Tests:**
```python
def test_worker_failure_recovery():
    # Start task
    redis_client.lpush('crawl_tasks', json.dumps({'source': 'luma'}))

    # Worker crashes mid-processing
    worker = CrawlWorker(redis_client)
    with pytest.raises(SimulatedCrash):
        worker.process_with_crash()

    # Task should still be in queue (not acknowledged)
    queue_depth = redis_client.llen('crawl_tasks')
    assert queue_depth == 1

    # New worker picks up task
    worker2 = CrawlWorker(redis_client)
    worker2.process_one_task()

    # Verify completion
    assert redis_client.llen('crawl_tasks') == 0
```

### Cost-Benefit Analysis

**Current System (Single-Process):**
- **Cost:** $0/month infrastructure (local machine)
- **Throughput:** ~9 sources in 2-3 hours
- **Reliability:** Low (single point of failure)
- **Maintenance:** Low (simple system)

**Phase 1 (Multi-Process):**
- **Cost:** $0/month (same machine)
- **Throughput:** ~9 sources in 30-45 minutes (4x speedup)
- **Reliability:** Low (still single machine)
- **Maintenance:** Low (minimal code changes)
- **ROI:** High (significant speedup for minimal effort)

**Phase 2 (Redis Queue):**
- **Cost:** ~$100/month
- **Throughput:** ~9 sources in 10-15 minutes (12x speedup)
- **Reliability:** Medium (fault tolerance, but Redis SPOF)
- **Maintenance:** Medium (distributed debugging)
- **ROI:** Medium (good for growing needs)

**Phase 3 (Production):**
- **Cost:** ~$600/month
- **Throughput:** ~50+ sources in <30 minutes (40x+ speedup)
- **Reliability:** High (full HA, auto-recovery)
- **Maintenance:** High (complex infrastructure)
- **ROI:** Low for current scale, high if scaling significantly

**Recommendation:** Start with Phase 1 (free speedup), move to Phase 2 only if crawl time becomes bottleneck or adding many more sources.

---

## References

### Architecture and Design

1. [Design a distributed web crawler - Medium](https://medium.com/@morefree7/design-a-distributed-web-crawler-f67a8ebb8336) - Master-worker pattern and architecture overview
2. [The Architecture of a Web Crawler - Medium](https://medium.com/@tonywangcn/the-architecture-of-a-web-crawler-building-a-google-inspired-distributed-web-crawler-part-1-7f4281f9f539) - Google-inspired distributed crawler design
3. [Distributed Web Crawling Made Easy - ZenRows](https://www.zenrows.com/blog/distributed-web-crawling) - Comprehensive guide to distributed crawling
4. [System Design Primer - Web Crawler](https://github.com/donnemartin/system-design-primer/blob/master/solutions/system_design/web_crawler/README.md) - System design interview resource
5. [Guide to Distributed Web Crawling - Bright Data](https://brightdata.com/blog/web-data/distributed-web-crawling) - Practical distributed crawling guide

### URL Frontier and Queue Management

6. [The URL frontier - Stanford NLP](https://nlp.stanford.edu/IR-book/html/htmledition/the-url-frontier-1.html) - Academic resource on URL frontier design
7. [What is a URL frontier - Firecrawl](https://www.firecrawl.dev/glossary/web-crawling-apis/what-is-url-frontier-web-crawling) - URL frontier explanation
8. [Web Crawler System Design - Grokking](https://grokkingthesystemdesign.com/guides/web-crawler-system-design/) - Step-by-step design guide

### Bloom Filters and Deduplication

9. [How to avoid crawling duplicate URLs at Google scale - ByteByteGo](https://blog.bytebytego.com/p/how-to-avoid-crawling-duplicate-urls) - Google-scale deduplication strategies
10. [Bloom Filter for Web Scraping Deduplication - Dataget](https://dataget.ai/blogs/bloom-filter-web-scraping-deduplication/) - Bloom filter implementation guide
11. [An Improved Bloom Filter in Distributed Crawler - IEEE](https://ieeexplore.ieee.org/document/8560281/) - Academic paper on improved Bloom filters
12. [Web Crawling at Scale - Medium](https://medium.com/@tonywangcn/web-crawling-at-scale-navigating-billions-of-urls-with-efficiency-7a9b9a1e3829) - Efficiency techniques for billions of URLs

### Crawler Frameworks

13. [The Battle of the Crawlers: Apache Nutch vs. StormCrawler - DZone](https://dzone.com/articles/the-battle-of-the-crawlers-apache-nutch-vs-stormcr) - Framework comparison
14. [StormCrawler - InfoQ](https://www.infoq.com/news/2016/12/nioche-stormcrawler-web-crawler/) - StormCrawler architecture overview
15. [Comparison of Open Source Web Crawlers - OutsourceIT](https://outsourceit.today/comparison-open-source-web-crawlers/) - Comprehensive framework comparison
16. [Scrapy vs Nutch - Medium](https://medium.com/@amit25173/scrapy-vs-nutch-3b50ff3bf163) - Detailed comparison
17. [GitHub - Crawlab](https://github.com/crawlab-team/crawlab) - Open-source distributed crawler platform

### Message Queues

18. [Understanding Message Brokers - Medium](https://medium.com/mindful-engineering/understanding-message-brokers-and-message-backends-redis-rabbitmq-and-kafka-with-fastapi-part-bb0818ed26f5) - RabbitMQ, Kafka, Redis comparison
19. [RabbitMQ vs Kafka vs Redis - Logit](https://logit.io/blog/post/rabbitmq-vs-kafka-vs-redis/) - Message queue comparison
20. [Choosing the Right Message Queue - Medium](https://medium.com/@unclejiyo/choosing-the-right-message-queue-rabbitmq-apache-kafka-and-redis-compared-eb5ad4b83449) - Selection guide
21. [I Benchmarked Kafka, RabbitMQ, and Redis Streams - Medium](https://medium.com/@ThreadSafeDiaries/i-benchmarked-kafka-rabbitmq-and-redis-streams-the-winner-surprised-me-cf3f484eb7b2) - Performance benchmarks

### Distributed Coordination

22. [In-Depth Comparison of Distributed Coordination Tools - Medium](https://medium.com/@karim.albakry/in-depth-comparison-of-distributed-coordination-tools-consul-etcd-zookeeper-and-nacos-a6f8e5d612a6) - Consul, etcd, ZooKeeper comparison
23. [Consul vs Zookeeper vs etcd - StackShare](https://stackshare.io/stackups/consul-vs-etcd-vs-zookeeper) - Feature comparison
24. [How To Choose Between Etcd, ZooKeeper, and Consul - DevOps.dev](https://blog.devops.dev/how-to-choose-between-etcd-zookeeper-and-consul-2c0e6a3c48da) - Selection criteria
25. [Apache ZooKeeper vs. etcd3 - DZone](https://dzone.com/articles/apache-zookeeper-vs-etcd3) - Technical comparison

### Distributed Hash Tables

26. [DHT-Based Distributed Crawler - UC Berkeley](https://people.eecs.berkeley.edu/~kubitron/courses/cs294-4-F03/papers/DHTcrawler.pdf) - Academic paper on DHT crawlers
27. [Distributed Web Crawling over DHTs - UC Berkeley](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2004/5370.html) - Research publication
28. [Distributed hash table - Wikipedia](https://en.wikipedia.org/wiki/Distributed_hash_table) - DHT overview

### Politeness and Rate Limiting

29. [Web crawling and indexes - Stanford](https://nlp.stanford.edu/IR-book/pdf/20crawl.pdf) - Academic resource on crawling rules
30. [What is polite crawling - Firecrawl](https://www.firecrawl.dev/glossary/web-crawling-apis/what-is-polite-crawling) - Politeness definition and best practices
31. [High-Performance Web Crawling - Mercator](https://www.cs.cornell.edu/courses/cs685/2002fa/mercator.pdf) - Politeness implementation details

### Robots.txt

32. [Respecting Robots.txt at Scale - Medium](https://medium.com/gumgum-tech/respecting-robots-exclusion-protocol-or-robots-txt-at-scale-60ee57dc1295) - Large-scale robots.txt handling
33. [How Google Interprets robots.txt - Google Developers](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec) - Official specification
34. [Robots.txt for SEO - Conductor](https://www.conductor.com/academy/robotstxt/) - Best practices guide

### Scalability and Performance

35. [Design and Implementation of a High-Performance Distributed Web Crawler - NYU](https://cse.engineering.nyu.edu/tr/tr-cis-2001-03.pdf) - Academic research on scalability
36. [Distributed Frontera - Zyte](https://www.zyte.com/blog/distributed-frontera-web-crawling-at-large-scale/) - Production-scale crawling
37. [Web Crawling Contents - Stanford](http://i.stanford.edu/~olston/publications/crawling_survey.pdf) - Comprehensive survey

### Fault Tolerance

38. [How to create a distributed, fault tolerant crawler - ScrapeBot](https://scrapebot.com/how-to-create-a-distributed-fault-tolerant-crawler/) - Practical guide
39. [UbiCrawler: Scalability and fault-tolerance issues - ResearchGate](https://www.researchgate.net/publication/243767349_Ubicrawler_Scalability_and_fault-tolerance_issues) - Academic research

### Real-World Examples

40. [Google's Caffeine Update - Search Engine Land](https://searchengineland.com/googles-new-indexing-infrastructure-caffeine-now-live-43891) - Google's indexing system
41. [Our new search index: Caffeine - Google Developers](https://developers.google.com/search/blog/2010/06/our-new-search-index-caffeine) - Official announcement
42. [Common Crawl](https://commoncrawl.org) - Open web crawl repository
43. [Crawlab GitHub](https://github.com/crawlab-team/crawlab) - Open-source distributed crawler platform

---

**End of Research Document**

*Last Updated: February 13, 2026*
*Total References: 43*
*Document Length: ~15,000 words*
