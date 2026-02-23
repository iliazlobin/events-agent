---
name: clean-refactor
description: Remove temporary files, unused code, and compact documentation while preserving all production functionality. Cleans up debug data, Python cache files, temporary logs, and consolidates documentation.
disable-model-invocation: true
allowed-tools: Bash(find *), Bash(rm *), Bash(ls *), Bash(du *), Bash(tar *)
---

# Project Cleanup

Remove temporary and debugging files while keeping all essential code, tests, and data.

## What to keep

**Production code**:
- `src/events_agent/` - All source code (crawlers, models, filters, storage, utils)
- `tests/` - All unit and integration tests
- `scripts/validate_crawl.py` - Data validation utility

**Data**:
- `data/raw/` - Crawled raw event data (valuable)
- `data/processed/` - Processed/filtered event data (valuable)

**Configuration**:
- `pyproject.toml`, `README.md`, `AGENTS.md`, `.gitignore`
- All configuration and documentation files

## What to remove

**Root directory**:
- `test_*.py` - Ad-hoc test scripts

**scripts/ directory**:
- `inspect_*.py` - Inspection scripts (investigation phase)
- `debug_*.py` - Debugging scripts
- `test_*.py` - Temporary test scripts
- `analyze_*.py`, `crawl_*.py` - Other temporary scripts
- **Keep**: `validate_crawl.py` only

**data/debug/**:
- All JSON, PNG, HTML files
- Remove entire directory

## Cleanup process

### Step 1: Review files to be removed

```bash
# Root test files
find . -maxdepth 1 -name "test_*.py" -type f

# Scripts (except validate_crawl.py)
find scripts/ -name "*.py" ! -name "validate_crawl.py" -type f

# Debug directory
ls -lh data/debug/ 2>/dev/null || echo "Already removed"
```

### Step 2: Create backup

```bash
mkdir -p .cleanup_backup
tar -czf .cleanup_backup/backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  test_*.py scripts/inspect_*.py scripts/debug_*.py scripts/test_*.py \
  scripts/analyze_*.py scripts/crawl_*.py data/debug/ 2>/dev/null
```

### Step 3: Remove files

```bash
# Remove root test files
rm -f test_*.py

# Remove scripts except validate_crawl.py
find scripts/ -name "*.py" ! -name "validate_crawl.py" -type f -delete

# Remove debug directory
rm -rf data/debug/

# Remove archived docs if they exist
rm -rf docs/archive/
```

### Step 4: Verify cleanup

```bash
# Check root (should have no test_*.py)
ls test_*.py 2>&1 || echo "✓ No test files in root"

# Check scripts (should only have validate_crawl.py)
ls scripts/

# Check debug removed
ls data/debug/ 2>&1 || echo "✓ Debug directory removed"

# Verify essential files remain
ls src/events_agent/
ls tests/
ls data/raw/
ls data/processed/
```

### Step 5: Update .gitignore

Ensure future clutter is prevented:

```gitignore
# Temporary test files
test_*.py
!tests/

# Debug data
data/debug/

# Inspection scripts
scripts/inspect_*.py
scripts/debug_*.py
scripts/test_*.py
scripts/analyze_*.py
scripts/crawl_*.py

# Cleanup backups
.cleanup_backup/
```

## Expected results

After cleanup:
- **Scripts**: 1 file (validate_crawl.py)
- **Root**: No test_*.py files
- **Debug**: Directory removed
- **Backup**: Created in .cleanup_backup/
- **Source/tests/data**: All preserved

## Safety notes

- Always review files before deletion
- Backup is created automatically
- Never deletes production code, tests, or crawled data
- Can restore from .cleanup_backup/ if needed

## Recovery

To restore files from backup:

```bash
cd .cleanup_backup/
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz
# Files restored to current directory
```
