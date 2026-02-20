#!/bin/bash

# Apify Deploy & Verify Skill
# Deploys Apify actor, runs on cloud, debugs issues, verifies results

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default parameters
MAX_ITEMS=10
TIMEOUT=300
MAX_RETRIES=5
SKIP_LOCAL_TEST=false
CUSTOM_INPUT=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --maxItems)
      MAX_ITEMS="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    --input)
      CUSTOM_INPUT="$2"
      shift 2
      ;;
    --skip-local-test)
      SKIP_LOCAL_TEST=true
      shift
      ;;
    --max-retries)
      MAX_RETRIES="$2"
      shift 2
      ;;
    *)
      echo "Unknown parameter: $1"
      exit 1
      ;;
  esac
done

# Helper functions
print_header() {
  echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
  echo -e "${RED}❌ $1${NC}"
}

print_info() {
  echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check we're in a crawler directory
if [[ ! -f "package.json" ]] || [[ ! -d ".actor" ]]; then
  print_error "Not in an Apify crawler directory"
  print_info "Usage: cd apify/your-crawler && /apify-deploy-verify"
  exit 2
fi

CRAWLER_NAME=$(basename "$PWD")
print_header "🚀 Apify Deploy & Verify: $CRAWLER_NAME"

# Phase 1: Pre-Deploy Checks
print_header "Phase 1: Pre-Deploy Checks"

if [[ "$SKIP_LOCAL_TEST" == "false" ]]; then
  print_info "Building locally..."
  if npm run build > /tmp/build.log 2>&1; then
    print_success "Local build successful"
  else
    print_error "Local build failed"
    cat /tmp/build.log
    exit 2
  fi

  if [[ -d "dist" ]] && [[ -f "dist/main.js" ]]; then
    print_success "dist/main.js exists"
  else
    print_warning "dist/main.js not found after build"
  fi
else
  print_warning "Skipping local test (--skip-local-test)"
fi

# Phase 2: Deploy Loop with Auto-Fix
print_header "Phase 2: Deploy to Apify Cloud"

RETRY=0
DEPLOY_SUCCESS=false

while [[ $RETRY -lt $MAX_RETRIES ]]; do
  if [[ $RETRY -gt 0 ]]; then
    print_info "Retry attempt $RETRY of $MAX_RETRIES"
  fi

  print_info "Running apify push..."

  if apify push > /tmp/deploy.log 2>&1; then
    print_success "Deployment successful"
    DEPLOY_SUCCESS=true

    # Extract build ID and version
    BUILD_ID=$(grep -o 'Build: [0-9.]*' /tmp/deploy.log | head -1 | awk '{print $2}')
    print_info "Build version: $BUILD_ID"
    break
  else
    print_error "Deployment failed"

    # Analyze error and attempt fix
    ERROR_LOG=$(cat /tmp/deploy.log)

    if echo "$ERROR_LOG" | grep -q "tsx: not found"; then
      print_warning "Detected: tsx not found error"
      print_info "Auto-fix: Updating package.json start script"

      # Fix package.json
      sed -i.bak 's/"start": "npm run start:dev"/"start": "node dist\/main.js"/' package.json
      print_success "Fixed package.json"

    elif echo "$ERROR_LOG" | grep -q "Cannot find module.*dist/main.js"; then
      print_warning "Detected: dist/main.js not found in container"
      print_info "Auto-fix: Updating .gitignore and Dockerfile"

      # Fix .gitignore
      sed -i.bak '/^dist$/d' .gitignore 2>/dev/null || true
      print_success "Removed dist/ from .gitignore"

      # Rebuild
      npm run build

    elif echo "$ERROR_LOG" | grep -q "Failed to launch.*browser\|chrome ENOENT"; then
      print_warning "Detected: Chrome/browser not found"
      print_info "Auto-fix: Creating Dockerfile with Puppeteer-Chrome base"

      cat > Dockerfile << 'EOF'
FROM apify/actor-node-puppeteer-chrome:20

COPY package*.json ./
RUN npm install --quiet --only=prod --no-optional

COPY dist ./dist
COPY .actor ./.actor

CMD npm start
EOF
      print_success "Created Dockerfile"

      # Rebuild locally
      npm run build

    else
      print_error "Unknown deployment error"
      echo "$ERROR_LOG"
      break
    fi
  fi

  RETRY=$((RETRY + 1))
done

if [[ "$DEPLOY_SUCCESS" == "false" ]]; then
  print_error "Deployment failed after $MAX_RETRIES attempts"
  exit 1
fi

# Phase 3: Run on Apify Cloud
print_header "Phase 3: Run on Apify Cloud"

# Construct input
if [[ -n "$CUSTOM_INPUT" ]]; then
  INPUT="$CUSTOM_INPUT"
else
  INPUT="{\"maxItems\":$MAX_ITEMS,\"region\":\"sf\"}"
fi

print_info "Input: $INPUT"
print_info "Timeout: ${TIMEOUT}s"

# Run actor
ACTOR_ID=$(cat .actor/actor.json | grep -o '"name": "[^"]*"' | head -1 | cut -d'"' -f4)
print_info "Running actor: $ACTOR_ID"

START_TIME=$(date +%s)

if apify actors call "$ACTOR_ID" \
  --input "$INPUT" \
  --timeout "$TIMEOUT" \
  --output-dataset > /tmp/run.log 2>&1; then

  RUN_STATUS="SUCCESS"
  print_success "Actor run completed"
else
  EXIT_CODE=$?
  if grep -q "timeout" /tmp/run.log; then
    RUN_STATUS="TIMEOUT"
    print_warning "Actor hit timeout (events may still be collected)"
  else
    RUN_STATUS="FAILED"
    print_error "Actor run failed"
  fi
fi

END_TIME=$(date +%s)
RUNTIME=$((END_TIME - START_TIME))

# Phase 4: Verify Results
print_header "Phase 4: Verify Results"

# Extract dataset URL
DATASET_URL=$(grep -o 'https://console.apify.com/storage/datasets/[a-zA-Z0-9]*' /tmp/run.log | head -1)

if [[ -n "$DATASET_URL" ]]; then
  print_success "Dataset URL: $DATASET_URL"
else
  print_warning "Could not extract dataset URL"
fi

# Parse dataset from output
DATASET_JSON=$(sed -n '/^\[{/,/^\]$/p' /tmp/run.log)

if [[ -n "$DATASET_JSON" ]]; then
  # Count events
  EVENT_COUNT=$(echo "$DATASET_JSON" | grep -o '"url":' | wc -l | tr -d ' ')

  print_info "Events collected: $EVENT_COUNT / $MAX_ITEMS"

  if [[ $EVENT_COUNT -gt 0 ]]; then
    # Calculate speed
    SPEED=$((RUNTIME / EVENT_COUNT))
    print_info "Speed: ~${SPEED}s per event"

    # Check data quality
    TITLES=$(echo "$DATASET_JSON" | grep -o '"title": "[^"]*"' | grep -v '""' | wc -l | tr -d ' ')
    DATES=$(echo "$DATASET_JSON" | grep -o '"dateStr": "[^"]*"' | grep -v '""' | wc -l | tr -d ' ')
    LOCATIONS=$(echo "$DATASET_JSON" | grep -o '"location": "[^"]*"' | grep -v '""' | wc -l | tr -d ' ')

    print_info "Data Quality:"
    echo "  - Titles: $TITLES/$EVENT_COUNT"
    echo "  - Dates: $DATES/$EVENT_COUNT"
    echo "  - Locations: $LOCATIONS/$EVENT_COUNT"
  else
    print_error "No events collected!"
  fi
else
  print_error "Could not parse dataset"
  EVENT_COUNT=0
fi

# Check for warnings/errors
WARNINGS=$(grep -c "WARN\|⚠️" /tmp/run.log || true)
ERRORS=$(grep -c "ERROR\|❌" /tmp/run.log || true)

if [[ $WARNINGS -gt 0 ]]; then
  print_warning "$WARNINGS warnings in run logs"
fi

if [[ $ERRORS -gt 0 ]]; then
  print_error "$ERRORS errors in run logs"
fi

# Phase 5: Generate Report
print_header "📊 Deployment & Verification Report"

echo "Crawler: $CRAWLER_NAME"
echo "Build: $BUILD_ID"
echo "Status: $RUN_STATUS"
echo "Runtime: ${RUNTIME}s"
echo ""
echo "Events:"
echo "  Expected: $MAX_ITEMS"
echo "  Collected: $EVENT_COUNT ($(( EVENT_COUNT * 100 / MAX_ITEMS ))%)"
echo ""

if [[ -n "$DATASET_URL" ]]; then
  echo "Dataset: $DATASET_URL"
else
  echo "Dataset: Not available"
fi

echo ""
echo "Issues:"
if [[ $WARNINGS -gt 0 ]]; then
  echo "  ⚠️  $WARNINGS warnings"
fi
if [[ $ERRORS -gt 0 ]]; then
  echo "  ❌ $ERRORS errors"
fi
if [[ "$RUN_STATUS" == "TIMEOUT" ]]; then
  echo "  ⚠️  Timeout after ${TIMEOUT}s"
fi

echo ""
echo "Recommendations:"
if [[ "$RUN_STATUS" == "TIMEOUT" ]]; then
  echo "  💡 Increase timeout to $((TIMEOUT * 2))s for production"
fi
if [[ $EVENT_COUNT -ge $((MAX_ITEMS * 7 / 10)) ]]; then
  echo "  ✅ Crawler is operational ($(( EVENT_COUNT * 100 / MAX_ITEMS ))% success rate)"
fi
if [[ $EVENT_COUNT -lt $((MAX_ITEMS / 2)) ]]; then
  echo "  ⚠️  Low collection rate - check selectors and test locally"
fi

echo ""
if [[ $EVENT_COUNT -gt 0 ]]; then
  print_success "VERIFICATION COMPLETE ✅"
  exit 0
else
  print_error "VERIFICATION FAILED ❌"
  exit 4
fi
