# Skills Setup Summary

**Date**: 2026-02-10
**Status**: ✅ Completed - Reformatted to official Claude Code standard

## Skills Structure

All skills now follow the [official Claude Code skills format](https://code.claude.com/docs/en/skills):

```
.agents/skills/              # Primary location (canonical)
├── cleanup/
│   └── SKILL.md            # Project cleanup skill
└── init/
    └── SKILL.md            # Project initialization skill

.claude/skills/             # Symlink → ../.agents/skills/
```

## Available Skills

### 1. `/cleanup` - Project Cleanup

**Purpose**: Remove temporary, debugging, and non-essential files

**Frontmatter**:
```yaml
name: cleanup
description: Remove temporary, debugging, and non-essential files from the project while preserving production code, tests, and crawled data. Use when the project has accumulated inspection scripts, debug files, or temporary test files.
disable-model-invocation: true
allowed-tools: Bash(find *), Bash(rm *), Bash(ls *), Bash(du *), Bash(tar *)
```

**Features**:
- Manual invocation only (`disable-model-invocation: true`)
- Restricted to specific bash commands for safety
- Automatic backup creation
- Preserves all production code, tests, and data
- Updates .gitignore to prevent future clutter

**Usage**:
```bash
/cleanup
```

**What it does**:
1. Lists files to be removed
2. Creates backup in .cleanup_backup/
3. Removes temporary files:
   - Root test_*.py files
   - Inspection/debug scripts (except validate_crawl.py)
   - data/debug/ directory
4. Verifies essential files remain
5. Updates .gitignore

### 2. `/init` - Project Initialization

**Purpose**: Initialize the project and set up local development environment

**Frontmatter**:
```yaml
name: init
description: Initialize this project
```

**Features**:
- Creates virtual environment
- Activates venv
- Keeps setup minimal and concise

**Usage**:
```bash
/init
```

## Skills Format Compliance

Both skills follow the official standard:

✅ **Directory structure**: `<skill-name>/SKILL.md`
✅ **YAML frontmatter**: name, description, and optional fields
✅ **Markdown content**: Clear instructions and examples
✅ **Location**: `.agents/skills/` with `.claude/skills/` symlink
✅ **Agent Skills standard**: Compatible with [agentskills.io](https://agentskills.io)

## Key Features

### Invocation Control

- **cleanup**: Manual only (`disable-model-invocation: true`)
  - You invoke with `/cleanup`
  - Claude cannot trigger automatically
  - Use for actions with side effects

- **init**: Both manual and automatic
  - You can invoke with `/init`
  - Claude can load when relevant
  - Use for reference or safe operations

### Tool Permissions

**cleanup** specifies `allowed-tools`:
```yaml
allowed-tools: Bash(find *), Bash(rm *), Bash(ls *), Bash(du *), Bash(tar *)
```

This grants Claude permission to use these specific bash commands without asking when the skill is active, providing a smoother experience while maintaining safety.

## Directory Benefits

Using `.agents/skills/` with symlink:
- **Organized**: Separate from Claude Code internals
- **Compatible**: `.claude/skills/` symlink maintains compatibility
- **Discoverable**: Both paths work for skill invocation
- **Standard**: Follows Agent Skills open standard

## Testing Skills

### Test cleanup skill:
```bash
/cleanup
```

Should show:
1. List of files to remove
2. Backup creation
3. Removal confirmation
4. Verification of essential files

### Test init skill:
```bash
/init
```

Should:
1. Create/verify venv
2. Activate virtual environment

## Migration from Old Format

**Before**:
```
.claude/skills/
└── cleanup.md              # Flat file, non-standard format
```

**After**:
```
.agents/skills/
├── cleanup/
│   └── SKILL.md           # Official format with frontmatter
└── init/
    └── SKILL.md

.claude/skills/ → symlink to .agents/skills/
```

**Changes made**:
1. Created skill directories
2. Renamed files to `SKILL.md`
3. Added YAML frontmatter
4. Restructured content for clarity
5. Added `allowed-tools` for safety
6. Set `disable-model-invocation` for cleanup

## Additional Resources

- **Official docs**: https://code.claude.com/docs/en/skills
- **Agent Skills standard**: https://agentskills.io
- **Skill file**: `.agents/skills/<skill-name>/SKILL.md`
- **Invocation**: `/skill-name` or let Claude load automatically

## Next Steps

You can now:
1. ✅ Use `/cleanup` to maintain a clean project
2. ✅ Use `/init` to set up the environment
3. Add more skills to `.agents/skills/` as needed
4. Share skills by committing to version control
5. Create plugins with bundled skills

All skills are production-ready and follow official standards! 🎯
