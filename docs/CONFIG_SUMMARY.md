# Crawler Configuration Optimization Summary

## What Was Done

Optimized Apify crawler configurations using the same pattern as `memory_mbytes`:
- **Explicit defaults** in YAML config
- **Per-crawler overrides** for flexibility
- **Centralized management** via Python scripts
- **Validation** to prevent errors

## Files Created

### 1. `apify/crawler_schedules.yaml`
Apify platform-specific settings and schedules

```yaml
defaults:
  memory_mbytes: 1024    # ✅ Explicit default (1 GB)
  timeout_secs: 3600     # ✅ 1 hour max runtime
  notify_on_failure: true

schedules:
  garysguide:
    actor_id: "iliazlobin/events-garysguide-crawler"
    cron: "0 2 * * *"
    memory_mbytes: 1024  # ✅ Overrideable per crawler
    input:
      region: "sf"
      maxItems: 100
```

**Features**:
- Default memory allocation (1024 MB)
- Schedule definitions (cron, timezone)
- Input configurations
- Notification settings
- Cost optimization parameters

### 2. `scripts/sync_apify_schedules.py`
Sync script to push schedules to Apify platform

**Commands**:
```bash
# List all schedules
python3 scripts/sync_apify_schedules.py list

# Validate configs
python3 scripts/sync_apify_schedules.py validate

# Sync to Apify (dry run)
python3 scripts/sync_apify_schedules.py sync --dry-run

# Sync to Apify (live)
export APIFY_API_TOKEN="your_token"
python3 scripts/sync_apify_schedules.py sync
```

**Features**:
- Reads YAML config with defaults
- Merges per-crawler overrides
- Validates all settings (memory > 0, required fields)
- Generates Apify API payloads
- Syncs to Apify platform via REST API
- Supports dry-run mode

### 3. `docs/CRAWLER_CONFIG_OPTIMIZATION.md`
Comprehensive documentation (9KB)

**Contents**:
- Architecture overview
- Configuration structure
- Validation rules
- Usage examples
- Cost analysis
- Migration path

### 4. Updated `CLAUDE.md`
Added "Configuration Management" section

**Location**: Between "Integration with Python SQLite" and "Best Practices"

## Configuration Pattern

### Before (Hardcoded)
```typescript
// main.ts
const crawler = new PuppeteerCrawler({
  maxRequestsPerMinute: 15,  // ❌ Hardcoded
  requestHandlerTimeoutSecs: 180,
  // ...
})
```

### After (Centralized)
```yaml
# crawler_schedules.yaml
defaults:
  memory_mbytes: 1024      # ✅ Explicit default
  timeout_secs: 3600

schedules:
  garysguide:
    memory_mbytes: 2048    # ✅ Override if needed
```

### Benefits
1. **Explicit** - All settings visible in config
2. **Overrideable** - Per-crawler customization
3. **Validated** - Prevents invalid configurations
4. **Centralized** - Single source of truth
5. **Version Controlled** - Config changes tracked in Git

## Validation Rules

```python
# All enforced by sync_apify_schedules.py validate
memory_mbytes > 0           ✅
timeout_secs > 0            ✅
actor_id required           ✅
cron expression required    ✅
timezone required           ✅
```

## Configuration Hierarchy

```
defaults (crawler_schedules.yaml)
    ↓ merge
per-crawler overrides
    ↓ validate
final config
    ↓ sync
Apify platform (via API)
```

## Quick Start

### 1. Install Dependencies
```bash
pip install pyyaml requests
```

### 2. List Current Configs
```bash
python3 scripts/sync_apify_schedules.py list
```

Expected output:
```
=== Apify Crawler Schedules ===

📅 garysguide
   Actor: iliazlobin/events-garysguide-crawler
   Cron: 0 2 * * *
   Memory: 1024 MB
   Timeout: 3600s

📅 luma
   Actor: iliazlobin/events-luma-crawler
   Cron: 0 3 * * *
   Memory: 1024 MB
   ...
```

### 3. Validate All Configs
```bash
python3 scripts/sync_apify_schedules.py validate
```

Expected output:
```
Validating 3 schedules...

✅ garysguide
✅ luma
✅ meetup

✅ All schedule configurations are valid
```

### 4. Test Sync (Dry Run)
```bash
python3 scripts/sync_apify_schedules.py sync --dry-run
```

### 5. Apply to Apify
```bash
export APIFY_API_TOKEN="your_token"
python3 scripts/sync_apify_schedules.py sync
```

## Configuration Files Overview

### `apify/crawler_config.yaml`
**Purpose**: Crawler runtime settings
- Rate limits
- Session pools
- Autoscaling
- Managed by: `manage_crawler_config.py`

### `apify/crawler_schedules.yaml` ✨ NEW
**Purpose**: Apify platform settings
- Memory allocation
- Schedules
- Notifications
- Managed by: `sync_apify_schedules.py`

## Next Steps

1. **Test validation**:
   ```bash
   python3 scripts/sync_apify_schedules.py validate
   ```

2. **Review configs**:
   ```bash
   python3 scripts/sync_apify_schedules.py show --crawler garysguide
   ```

3. **Dry run sync**:
   ```bash
   python3 scripts/sync_apify_schedules.py sync --dry-run
   ```

4. **Apply to Apify** (when ready):
   ```bash
   export APIFY_API_TOKEN="..."
   python3 scripts/sync_apify_schedules.py sync
   ```

## Similar Optimizations Applied

✅ **Memory allocation**
  - Default: 1024 MB (1 GB)
  - Overrideable per crawler
  - Validated (must be > 0)
  - Sent to Apify as `options.memoryMbytes`

✅ **Timeout settings**
  - Default: 3600s (1 hour)
  - Overrideable per crawler
  - Validated (must be > 0)
  - Sent to Apify as `options.timeoutSecs`

✅ **Build selection**
  - Default: `latest`
  - Overrideable per crawler
  - Sent to Apify as `options.build`

✅ **Notifications**
  - Default: fail=true, success=false
  - Overrideable per crawler
  - Cost optimization (avoid spam)

✅ **Schedule settings**
  - Cron expressions
  - Timezone settings
  - Enabled/disabled flag
  - Per-crawler customization

## Dependencies

```bash
# Required for all commands
pip install pyyaml

# Required for sync command only
pip install requests
```

## References

- Full docs: `docs/CRAWLER_CONFIG_OPTIMIZATION.md`
- Project guide: `CLAUDE.md` (Configuration Management section)
- Apify API: https://docs.apify.com/api/v2
- Apify Schedules: https://docs.apify.com/platform/schedules
