# Apify Deploy & Verify Skill

Automates the complete workflow of deploying an Apify crawler to the cloud, running it, debugging issues, and verifying results.

## Quick Start

```bash
cd apify/garysguide-crawler
/apify-deploy-verify
```

## What It Does

1. ✅ **Pre-Deploy**: Builds locally, checks for issues
2. 🚀 **Deploy**: Pushes to Apify cloud with auto-retry
3. 🔧 **Debug**: Auto-fixes common deployment issues
4. ▶️  **Run**: Executes crawler on Apify platform
5. ✅ **Verify**: Checks results, counts events, measures performance
6. 📊 **Report**: Comprehensive summary with recommendations

## Common Auto-Fixes

The skill automatically detects and fixes:

- ❌ `tsx not found` → Updates package.json start script
- ❌ `dist/main.js not found` → Fixes .gitignore, rebuilds
- ❌ `Chrome not found` → Creates Dockerfile with Puppeteer image
- ❌ Build failures → Adjusts build process

## Example Output

```
🚀 Apify Deploy & Verify: garysguide-crawler
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 1: Pre-Deploy Checks
✅ Local build successful
✅ dist/main.js exists

Phase 2: Deploy to Apify Cloud
✅ Deployment successful
ℹ️  Build version: 1.0.5

Phase 3: Run on Apify Cloud
ℹ️  Input: {"maxItems":10,"region":"sf"}
ℹ️  Timeout: 300s
✅ Actor run completed

Phase 4: Verify Results
✅ Dataset URL: https://console.apify.com/storage/datasets/ABC123
ℹ️  Events collected: 7 / 10
ℹ️  Speed: ~44s per event
ℹ️  Data Quality:
  - Titles: 7/7
  - Dates: 2/7
  - Locations: 3/7
⚠️  1 warnings in run logs

📊 Deployment & Verification Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Crawler: garysguide-crawler
Build: 1.0.5
Status: SUCCESS
Runtime: 306s

Events:
  Expected: 10
  Collected: 7 (70%)

Dataset: https://console.apify.com/storage/datasets/ABC123

Issues:
  ⚠️  1 warnings
  ⚠️  Timeout after 300s

Recommendations:
  💡 Increase timeout to 600s for production
  ✅ Crawler is operational (70% success rate)

✅ VERIFICATION COMPLETE ✅
```

## Usage Patterns

### Basic Verification
```bash
cd apify/my-crawler
/apify-deploy-verify
```

### Custom Test Size
```bash
/apify-deploy-verify --maxItems 50 --timeout 600
```

### Different Region
```bash
/apify-deploy-verify --input '{"region":"nyc","maxItems":10}'
```

### Skip Local Test
```bash
/apify-deploy-verify --skip-local-test
```

## When to Use

- ✅ After creating a new Apify crawler
- ✅ After making changes to existing crawler
- ✅ Before setting up scheduled runs
- ✅ To debug deployment issues
- ✅ To verify cloud performance

## Integration with Development Workflow

```bash
# 1. Develop crawler locally
npm run build
apify run --input-file=inputs/test.json

# 2. Deploy and verify
/apify-deploy-verify

# 3. If successful, commit
git add .
git commit -m "feat: Add new crawler"

# 4. Set up production schedule (via Apify console or API)
```

## Exit Codes

- `0` - Success
- `1` - Deployment failed
- `2` - Build failed locally
- `3` - Actor run failed
- `4` - No events collected

## Files

- `SKILL.md` - Full documentation
- `skill.sh` - Bash implementation
- `README.md` - This file

## Version

v1.0.0 - Created 2026-02-19
