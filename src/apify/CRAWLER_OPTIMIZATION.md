# Crawler Configuration Optimization

All Apify crawlers have been optimized with consistent settings for better performance, reliability, and cost efficiency.

## Applied Optimizations

### 1. Memory Configuration
- **Default**: 1024 MB (1 GB) for all crawlers
- **Rationale**: Sufficient for Puppeteer + Chrome without over-provisioning
- **Override**: Can be adjusted per-crawler in `crawler_config.yaml`

### 2. Rate Limiting
**Before**: 3 requests/minute (too conservative)  
**After**: 10-15 requests/minute (optimized)

| Crawler | Old | New | Rationale |
|---------|-----|-----|-----------|
| Gary's Guide | 3 | 15 | Static pages, low blocking risk |
| Luma | 3 | 10 | Next.js app, moderate complexity |
| Meetup | 3 | 10 | GraphQL API, good reliability |

### 3. Request Timeouts
**Before**: Mixed (60s-300s)  
**After**: Optimized per crawler

| Crawler | Timeout | Rationale |
|---------|---------|-----------|
| Gary's Guide | 180s (3 min) | Scrolling + redirects |
| Luma | 300s (5 min) | Extensive scrolling |
| Meetup | 120s (2 min) | GraphQL is fast |

### 4. Session Pool
**Before**: 10 max sessions  
**After**: 5 max sessions

- Reduced from 10 → 5 for better resource usage
- Still sufficient for concurrent requests
- Lower memory overhead

### 5. Autoscaling
**Before**: minConcurrency=2, maxConcurrency=10  
**After**: minConcurrency=1, maxConcurrency=5

- Start with 1 to save resources during warmup
- Max 5 provides good parallelism without overwhelming targets
- Better stability and lower blocking risk

## Configuration Files

### `crawler_config.yaml`
Central configuration with defaults and per-crawler overrides:

```yaml
defaults:
  memory_mbytes: 1024
  max_requests_per_minute: 15
  max_request_retries: 3
  request_handler_timeout_secs: 180
  session_pool_size: 5
  min_concurrency: 1
  max_concurrency: 5

crawlers:
  garysguide:
    memory_mbytes: 1024
    max_requests_per_minute: 15
    # ... crawler-specific settings
```

### Per-Crawler `main.ts`
All crawlers now use consistent settings:

```typescript
const crawler = new PuppeteerCrawler({
  proxyConfiguration,
  requestHandler: router,
  maxRequestsPerCrawl: maxItems + 10,
  maxRequestsPerMinute: 15,          // Optimized
  maxRequestRetries: 3,
  requestHandlerTimeoutSecs: 180,    // Per-crawler
  useSessionPool: true,
  sessionPoolOptions: {
    maxPoolSize: 5,                  // Reduced from 10
    sessionOptions: {
      maxUsageCount: 10,
      maxErrorScore: 5,
    },
  },
  autoscaledPoolOptions: {
    minConcurrency: 1,                // Reduced from 2
    maxConcurrency: 5,                // Reduced from 10
  },
})
```

## Performance Impact

### Runtime Improvements
| Crawler | Before | After | Improvement |
|---------|--------|-------|-------------|
| Gary's Guide | ~50 min | ~15-20 min | 60% faster |
| Luma | ~30 min | ~10-15 min | 50% faster |
| Meetup | ~25 min | ~8-12 min | 60% faster |

*Estimates based on 100-150 events per run*

### Cost Impact
| Crawler | Before | After | Savings |
|---------|--------|-------|---------|
| Gary's Guide | $0.25 | $0.10-0.12 | 50% |
| Luma | $0.15 | $0.06-0.08 | 55% |
| Meetup | $0.12 | $0.05-0.06 | 58% |

*Based on Apify pricing: $0.25 per compute unit (1 GB RAM for 1 hour)*

## Deployment

### Local Testing
```bash
cd src/apify/<crawler-name>
npm install
npm run build
apify run --input-file=inputs/test.json
```

### Deploy to Apify
```bash
apify push
```

### Set Memory on Apify Platform
When creating schedules or running actors:

```bash
apify actor call <actor-name> \
  --input '{"region":"sf","maxItems":100}' \
  --memory-mbytes 1024
```

Or via API:
```json
{
  "actorId": "iliazlobin/events-luma",
  "input": { "urls": ["https://lu.ma/nyc"], "maxItems": 150 },
  "options": {
    "memoryMbytes": 1024
  }
}
```

## Monitoring

### Key Metrics to Track
1. **Runtime**: Should be 50-60% faster than before
2. **Success Rate**: Should remain >95%
3. **Memory Usage**: Should stay under 1 GB (current limit)
4. **Request Rate**: Actual rate vs configured limit
5. **Cost per Run**: Should decrease by ~50%

### Alerts
Set up alerts for:
- Runtime > 30 minutes (indicates blocking or issues)
- Success rate < 90%
- Memory usage > 900 MB (approaching limit)

## Rollback Plan

If optimizations cause issues:

1. **Reduce rate limit**: 15 → 10 → 5 requests/min
2. **Increase timeout**: Add 60s increments
3. **Increase memory**: 1024 → 2048 MB
4. **Reduce concurrency**: maxConcurrency 5 → 3 → 1

## Future Improvements

- [ ] Implement adaptive rate limiting based on response codes
- [ ] Add automatic retry with exponential backoff
- [ ] Monitor and tune memory based on actual usage
- [ ] Create dashboard for real-time monitoring
- [ ] Set up automated testing of configurations
