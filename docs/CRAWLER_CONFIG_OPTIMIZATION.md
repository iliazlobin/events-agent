# Crawler Configuration Optimization

## Overview

Optimized Apify crawler configurations by introducing a centralized, explicit, and overrideable configuration system with proper defaults and per-crawler customization.

## Changes Made

### 1. Created `apify/crawler_schedules.yaml`

**Purpose**: Apify-specific run settings and schedule configurations

**Structure**:
```yaml
defaults:
  memory_mbytes: 1024          # Explicit default: 1 GB RAM
  timeout_secs: 3600           # 1 hour max runtime
  build: latest                # Use latest Actor build
  notify_on_failure: true      # Alert on failures
  notify_on_success: false     # No alerts on success

schedules:
  garysguide:
    actor_id: "iliazlobin/events-garysguide-crawler"
    cron: "0 2 * * *"          # 2 AM daily
    timezone: "America/New_York"
    memory_mbytes: 1024        # Override if needed
    input:                     # Schedule-specific input
      region: "sf"
      maxItems: 100
```

**Key Features**:
- ✅ Explicit defaults for all Apify platform settings
- ✅ Per-crawler overrides (memory, timeout, notifications)
- ✅ Schedule definitions (cron, timezone, enabled flag)
- ✅ Input configurations for scheduled runs
- ✅ Cost optimization settings (retention, run limits)

### 2. Created `scripts/sync_apify_schedules.py`

**Purpose**: Sync schedule configurations to Apify platform via API

**Features**:
- Read and parse `crawler_schedules.yaml`
- Merge defaults with per-crawler overrides
- Validate required fields and constraints
- Generate Apify API payloads
- Create/update schedules via Apify API
- Dry-run mode for safe testing

**Commands**:
```bash
# List all schedule configs
python3 scripts/sync_apify_schedules.py list

# Show detailed config for one crawler
python3 scripts/sync_apify_schedules.py show --crawler garysguide

# Validate all schedules
python3 scripts/sync_apify_schedules.py validate

# Sync all schedules (dry run)
python3 scripts/sync_apify_schedules.py sync --dry-run

# Sync specific crawler
python3 scripts/sync_apify_schedules.py sync --crawler garysguide

# Sync all schedules (requires APIFY_API_TOKEN)
export APIFY_API_TOKEN="your_token"
python3 scripts/sync_apify_schedules.py sync
```

**Validation**:
- ✅ `memory_mbytes > 0`
- ✅ `timeout_secs > 0`
- ✅ `actor_id` is required
- ✅ `cron` expression is present
- ✅ `timezone` is specified

### 3. Existing `apify/crawler_config.yaml`

**Purpose**: Crawler runtime settings and performance tuning

**Structure**:
```yaml
defaults:
  memory_mbytes: 1024                    # Platform memory
  max_requests_per_minute: 15            # Rate limiting
  max_request_retries: 3                 # Retry logic
  request_handler_timeout_secs: 180      # Handler timeout
  session_pool_size: 5                   # Session management
  min_concurrency: 1                     # Autoscaling
  max_concurrency: 5

crawlers:
  garysguide:
    name: "events-crawler-garysguide"
    memory_mbytes: 1024                  # Override defaults
    max_requests_per_minute: 15
    default_input:
      region: "sf"
      maxItems: 100
```

**Usage**: Managed via `scripts/manage_crawler_config.py`

## Architecture

### Separation of Concerns

**crawler_config.yaml** (Runtime Settings):
- Crawler performance parameters
- Rate limits, retries, timeouts
- Session pool configuration
- Autoscaling settings
- **Used by**: TypeScript crawler code (future integration)

**crawler_schedules.yaml** (Apify Platform Settings):
- Apify-specific run options
- Memory allocation (platform level)
- Schedule definitions (cron, timezone)
- Input configurations
- Notification settings
- **Used by**: `sync_apify_schedules.py` → Apify API

### Configuration Inheritance

```
defaults                 (Global defaults)
    ↓
crawler config          (Merge overrides)
    ↓
final config           (Used by scripts/API)
```

**Example**:
```yaml
# defaults.memory_mbytes = 1024
# garysguide.memory_mbytes = 2048
# → Final: 2048 MB
```

## Benefits

### 1. **Explicit Configuration**
- All settings visible in one place
- No hidden defaults in code
- Easy to understand and audit

### 2. **Overrideable Per Crawler**
- Shared defaults reduce duplication
- Per-crawler overrides for special cases
- Flexible and maintainable

### 3. **Validation**
- Type checking (memory > 0, timeout > 0)
- Required field validation
- Cron expression validation
- Prevents invalid configurations

### 4. **Centralized Management**
- Single source of truth
- Easy to update multiple crawlers
- Version controlled configurations

### 5. **Cost Optimization**
- Explicit memory settings (avoid over-provisioning)
- Timeout limits prevent runaway costs
- Retention policies reduce storage costs

### 6. **Consistency**
- All crawlers follow same pattern
- Predictable behavior
- Easier to debug and troubleshoot

## Migration Path

### Current State
- Settings hardcoded in `main.ts` files
- Memory set manually per run
- Schedules created via web console

### Future State (Phase 2)
- Read `crawler_config.yaml` in TypeScript crawlers
- Use environment variables for runtime config
- Fully automated schedule management

**Example Future Integration** (`main.ts`):
```typescript
import { loadCrawlerConfig } from './config.js'

const config = loadCrawlerConfig('garysguide')

const crawler = new PuppeteerCrawler({
  maxRequestsPerMinute: config.max_requests_per_minute,
  maxRequestRetries: config.max_request_retries,
  requestHandlerTimeoutSecs: config.request_handler_timeout_secs,
  sessionPoolOptions: {
    maxPoolSize: config.session_pool_size,
    sessionOptions: {
      maxUsageCount: config.session_max_usage_count,
      maxErrorScore: config.session_max_error_score,
    },
  },
  autoscaledPoolOptions: {
    minConcurrency: config.min_concurrency,
    maxConcurrency: config.max_concurrency,
  },
})
```

## Cost Analysis

### Memory Allocation (1 GB = 1024 MB)

| Crawler | Memory | Runtime | Cost/Run |
|---------|--------|---------|----------|
| garysguide | 1024 MB | ~50 min | $0.20-0.25 |
| luma | 1024 MB | ~30 min | $0.12-0.15 |
| meetup | 1024 MB | ~25 min | $0.10-0.12 |

**Apify Pricing**: ~$0.25 per compute unit (1 GB RAM for 1 hour)

### Monthly Cost (Daily Runs)
- garysguide: $6-7.50/month
- luma: $3.60-4.50/month
- meetup: $3-3.60/month
- **Total**: ~$12.60-15.60/month

### Free Tier
- $5/month credit (625 compute units)
- 7-day dataset retention
- **Recommendation**: Export datasets daily to SQLite

## Dependencies

```bash
# Python dependencies
pip install pyyaml          # YAML parsing
pip install requests        # API calls (sync command only)
```

## Usage Examples

### List All Schedules
```bash
$ python3 scripts/sync_apify_schedules.py list

=== Apify Crawler Schedules ===

📅 garysguide
   Actor: iliazlobin/events-garysguide-crawler
   Cron: 0 2 * * *
   Timezone: America/New_York
   Memory: 1024 MB
   Timeout: 3600s
   Enabled: True
   Input: {"region": "sf", "maxItems": 100, ...

📅 luma
   Actor: iliazlobin/events-luma-crawler
   ...
```

### Show Detailed Config
```bash
$ python3 scripts/sync_apify_schedules.py show --crawler garysguide

=== garysguide Schedule Configuration ===

actor_id: iliazlobin/events-garysguide-crawler
cron: 0 2 * * *
timezone: America/New_York
enabled: true
memory_mbytes: 1024
timeout_secs: 3600
...
```

### Validate Configs
```bash
$ python3 scripts/sync_apify_schedules.py validate

Validating 3 schedules...

✅ garysguide
✅ luma
✅ meetup

✅ All schedule configurations are valid
```

### Sync to Apify (Dry Run)
```bash
$ python3 scripts/sync_apify_schedules.py sync --dry-run

🔍 DRY RUN: Would create/update schedule for garysguide
{
  "name": "garysguide - Daily Crawl",
  "isEnabled": true,
  "cronExpression": "0 2 * * *",
  "timezone": "America/New_York",
  "actorId": "iliazlobin/events-garysguide-crawler",
  "input": { "region": "sf", ... },
  "options": {
    "memoryMbytes": 1024,
    "timeoutSecs": 3600
  }
}
```

### Sync to Apify (Live)
```bash
$ export APIFY_API_TOKEN="apify_api_XXX..."
$ python3 scripts/sync_apify_schedules.py sync

Creating schedule for garysguide...
✅ Schedule created/updated: 12abc345def...

Creating schedule for luma...
✅ Schedule created/updated: 67ghi890jkl...

Creating schedule for meetup...
✅ Schedule created/updated: 34mno567pqr...

Synced 3/3 schedules
```

## Next Steps

1. **Test Schedule Sync**:
   ```bash
   # Install dependencies
   pip install pyyaml requests

   # Validate configs
   python3 scripts/sync_apify_schedules.py validate

   # Dry run
   python3 scripts/sync_apify_schedules.py sync --dry-run
   ```

2. **Apply to Apify**:
   ```bash
   # Set API token
   export APIFY_API_TOKEN="your_token"

   # Sync all schedules
   python3 scripts/sync_apify_schedules.py sync
   ```

3. **Monitor Runs**:
   - Check Apify Console: https://console.apify.com/schedules
   - Verify schedules are enabled
   - Monitor first runs for errors

4. **Phase 2 Integration**:
   - Create TypeScript config loader
   - Update crawler `main.ts` files
   - Use config values instead of hardcoded settings

## References

- Apify API Docs: https://docs.apify.com/api/v2
- Apify Schedules: https://docs.apify.com/platform/schedules
- Apify Pricing: https://apify.com/pricing
