# Apify Deploy & Verify Skill

Deploy an Apify actor, run it on the cloud, debug issues, and verify results.

## When to Use

Invoke this skill when you need to:
- Deploy a new or updated Apify crawler to the cloud
- Verify a crawler works correctly on Apify's platform
- Debug deployment or runtime issues
- Get a complete verification report with metrics

## What This Skill Does

1. **Pre-Deploy Checks**
   - Verify crawler builds locally (`npm run build`)
   - Check for common issues (dist folder, Dockerfile, package.json)
   - Ensure required files exist

2. **Deploy to Apify**
   - Run `apify push` to deploy to cloud
   - Monitor build process
   - Capture build ID and version

3. **Run on Apify Cloud**
   - Execute the actor with test input
   - Wait for completion (with configurable timeout)
   - Handle timeouts and failures gracefully

4. **Debug Issues**
   - Analyze error logs for common problems:
     - `tsx not found` → Fix start script
     - `dist/main.js not found` → Fix .gitignore and Dockerfile
     - `Chrome not found` → Fix Docker base image
     - `tsc not found` → Fix build process
   - Automatically retry after fixes (up to 5 attempts)

5. **Verify Results**
   - Extract dataset URL
   - Count events collected vs expected
   - Calculate runtime and speed
   - Identify any warnings or issues
   - Compare with local test results

6. **Generate Report**
   - Summary of deployment
   - Performance metrics
   - Data quality assessment
   - Issues encountered and resolutions

## Usage

```
/apify-deploy-verify
```

Or with parameters:
```
/apify-deploy-verify --crawler garysguide-crawler --maxItems 10 --timeout 600
```

## Parameters

- `--crawler` (required): Name of crawler directory in `apify/`
- `--maxItems` (optional): Number of items to collect for test (default: 10)
- `--timeout` (optional): Timeout in seconds (default: 300)
- `--input` (optional): Custom JSON input for the actor
- `--skip-local-test` (optional): Skip local build verification
- `--max-retries` (optional): Max deployment retry attempts (default: 5)

## Example Output

```
🚀 Apify Deploy & Verify Report
================================

Crawler: garysguide-crawler
Build: 1.0.5 ✅ SUCCESS
Deployment Time: 45 seconds

Cloud Run Results:
------------------
Status: ✅ COMPLETED (with timeout)
Runtime: 306 seconds (5m 6s)
Dataset URL: https://console.apify.com/storage/datasets/VHaDY551ie5rzS9Bd

Events Collected:
-----------------
Expected: 10 events
Collected: 7 events (70%)
Speed: ~44 seconds per event

Issues Encountered:
-------------------
⚠️ Timeout after 300s (2 slow pages)
⚠️ 403 blocked: londonandpartners.com (anti-bot)
⚠️ Timeout: Amazon page (slow load)

Data Quality:
-------------
✅ Title: 7/7 (100%)
✅ URL: 7/7 (100%)
⚠️ Date: 2/7 (29%)
⚠️ Location: 3/7 (43%)
✅ Description: 7/7 (100%)

Recommendations:
----------------
1. ✅ Crawler is operational
2. 💡 Increase timeout to 600s for production
3. 💡 Consider filtering non-event pages
4. ✅ Ready for scheduled runs

Deployment: SUCCESS ✅
```

## Common Issues & Auto-Fixes

The skill automatically detects and fixes:

### Issue 1: `tsx not found`
**Detection**: Error contains "tsx: not found"
**Fix**: Update package.json start script to use `node dist/main.js`
**Retry**: Automatic

### Issue 2: `dist/main.js not found`
**Detection**: Error contains "Cannot find module '/usr/src/app/dist/main.js'"
**Fix**: Remove `dist/` from .gitignore, rebuild locally
**Retry**: Automatic

### Issue 3: Chrome/Browser Launch Failed
**Detection**: Error contains "Failed to launch browser" or "ENOENT chrome"
**Fix**: Create Dockerfile with `apify/actor-node-puppeteer-chrome:20` base image
**Retry**: Automatic

### Issue 4: Build Failures
**Detection**: "npm run build" fails, "tsc not found"
**Fix**: Update Dockerfile to pre-build locally instead of in Docker
**Retry**: Automatic

### Issue 5: Timeout
**Detection**: "timeout of X seconds"
**Fix**: Not auto-fixed (report only)
**Recommendation**: Increase timeout or reduce maxItems

## Implementation Details

The skill follows this workflow:

```
1. Pre-Deploy Phase
   ├── Check working directory
   ├── Verify package.json exists
   ├── Run npm run build
   ├── Check dist/ folder exists
   └── Verify .actor/actor.json exists

2. Deploy Phase
   ├── Run apify push
   ├── Monitor build logs
   ├── Capture build ID
   └── Check for build errors

3. Debug Phase (if errors)
   ├── Analyze error logs
   ├── Apply automatic fixes
   ├── Increment retry counter
   └── Return to Deploy Phase

4. Run Phase
   ├── Construct input JSON
   ├── Run apify actors call
   ├── Wait for completion (--timeout)
   └── Capture output and logs

5. Verify Phase
   ├── Parse dataset JSON
   ├── Count events collected
   ├── Extract dataset URL
   ├── Calculate metrics
   └── Identify issues

6. Report Phase
   ├── Generate summary
   ├── Compare with expectations
   ├── Provide recommendations
   └── Output to user
```

## Files Modified

The skill may automatically modify these files if issues are detected:

- `package.json` - Fix start script
- `.gitignore` - Remove dist/ exclusion
- `Dockerfile` - Create with proper base image
- (Rebuilds dist/ folder as needed)

All changes are logged in the report.

## Exit Codes

- `0` - Success (crawler deployed and verified)
- `1` - Deployment failed after max retries
- `2` - Build failed locally
- `3` - Actor run failed (non-timeout error)
- `4` - No events collected (data issue)

Note: Timeout is NOT considered a failure if events were collected.

## Dependencies

- `apify` CLI tool installed and authenticated
- `npm` and `node` available
- `jq` for JSON parsing (optional, falls back to grep/sed)
- Working directory must be crawler root (e.g., `apify/garysguide-crawler/`)

## Examples

### Example 1: Basic Deploy & Verify
```bash
cd apify/garysguide-crawler
/apify-deploy-verify
```

### Example 2: Custom Test Parameters
```bash
cd apify/luma-crawler
/apify-deploy-verify --maxItems 50 --timeout 600
```

### Example 3: NYC Region Test
```bash
cd apify/garysguide-crawler
/apify-deploy-verify --input '{"region":"nyc","maxItems":10}'
```

### Example 4: Skip Local Verification
```bash
cd apify/meetup-crawler
/apify-deploy-verify --skip-local-test --maxItems 20
```

## Best Practices

1. **Run Local Tests First**: Don't skip local testing unless necessary
2. **Use Appropriate Timeout**: 300s for 10 items, 600s for 50+ items
3. **Test with Small Batches**: Start with maxItems=10 for initial verification
4. **Monitor First Run**: Watch logs carefully on first deployment
5. **Iterate on Issues**: Let the skill auto-fix common problems
6. **Document Custom Fixes**: If manual fixes needed, document them

## Troubleshooting

### Skill Can't Find Crawler
**Error**: "Not in crawler directory"
**Solution**: `cd` into the crawler directory first (e.g., `cd apify/garysguide-crawler`)

### Build Keeps Failing
**Error**: Repeated build failures after auto-fixes
**Solution**: Check `npm run build` locally for compilation errors

### Actor Not Found
**Error**: "Actor ID not found"
**Solution**: Ensure you've run `apify push` at least once manually

### Dataset Empty
**Error**: "0 events collected"
**Solution**: Check crawler selectors, test URL validity, verify local run works

## Related Skills

- `/unit-testing` - Add tests for crawler logic
- `/commit` - Commit successful deployment changes
- Standard git workflow for version control

## Version History

- v1.0.0 (2026-02-19) - Initial skill creation
  - Auto-fixes for common Apify deployment issues
  - Comprehensive verification and reporting
  - Tested with Gary's Guide crawler

## Notes

- This skill assumes TypeScript/JavaScript crawlers using Crawlee/Puppeteer
- Python-based actors may require different fixes
- Skill saves deployment history in `.apify-verify-history.json`
- Each run appends to the history for tracking over time
