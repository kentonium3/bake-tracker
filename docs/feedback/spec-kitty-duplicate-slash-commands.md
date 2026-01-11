# Feedback Report: Duplicate Slash Commands in Worktrees

**Repository:** Priivacy-ai/spec-kitty
**Status:** Active bug - should be filed upstream
**Discovered:** 2026-01-10
**Reporter:** bake-tracker project

---

## Summary

Slash commands appeared twice in the command palette when using spec-kitty in a worktree. Initially appeared to be an upgrade gap, but investigation revealed **active bug in v0.10.12**: migration `m_0_10_1_populate_slash_commands.py` re-creates `.claude/commands/` in worktrees, undoing the fix from `m_0_7_2_worktree_commands_dedup.py`.

## Root Cause

Both the main repo AND the worktree had their own `.claude/commands/` directories with full copies of all 13 command files:

- **Main repo**: `/Users/kentgale/Vaults-repos/bake-tracker/.claude/commands/` (13 files, dated Jan 9)
- **Worktree**: `.worktrees/047-materials-management-system/.claude/commands/` (13 files, dated Jan 10)

**Critical observation:** This worktree was created TODAY with v0.10.12 already installed. This is NOT an upgrade gap from old worktrees - this is an active bug.

Claude Code discovers commands via upward directory traversal. Since worktrees are nested inside the main repo directory structure (`.worktrees/<feature>/`), Claude Code found BOTH:
1. The worktree's own commands
2. The main repo's commands (via parent traversal)

Result: Every `/spec-kitty.*` command appeared twice.

## Bug Analysis: Conflicting Migrations

The bug is in the migration system. Two migrations conflict:

### Migration 1: `m_0_7_2_worktree_commands_dedup.py`
- **Purpose:** Remove `.claude/commands/` from worktrees (they inherit from main repo)
- **Logic:** Correctly removes worktree commands since Claude Code traverses up to find them

### Migration 2: `m_0_10_1_populate_slash_commands.py`
- **Purpose:** Populate missing slash commands from mission templates
- **Problem:** Lines 128-129 have a special case that ALWAYS creates `.claude/commands/`:

```python
# Always create .claude/commands/, only create others if parent exists
if agent_dir.parent.exists() or agent_root == ".claude":
```

This means even in worktrees, the populate migration will create `.claude/commands/` because of the `or agent_root == ".claude"` clause.

### Conflict Result

When `spec-kitty upgrade` runs:
1. Migration 0.7.2 removes `.claude/commands/` from worktrees
2. Migration 0.10.1 re-creates `.claude/commands/` in worktrees

The migrations run in version order, so 0.10.1 runs AFTER 0.7.2 and undoes its work.

## When 0.7.2 Fix Was Intended

According to the [spec-kitty changelog](https://github.com/Priivacy-ai/spec-kitty):

**v0.7.0 - v0.7.2** (three-release correction cycle):
- v0.7.0: Initial attempt at fixing duplicate commands
- v0.7.1: Incorrectly removed commands from main repo (broke commands there)
- v0.7.2: Correct fix - removed duplicates from **worktrees only** since "worktrees find main repo's `.claude/commands/` through upward traversal"

## Why This Persists in v0.10.12

The `m_0_10_1_populate_slash_commands.py` migration:
1. Was added in v0.10.1 to fix projects with missing commands
2. Has special-case logic for `.claude/` that always creates commands
3. This special case doesn't check if it's in a worktree context
4. Runs on worktrees during `spec-kitty upgrade --recursive` or when processing existing worktrees

## Local Fix Applied

Removed the duplicate commands directory from the worktree:

```bash
rm -rf .worktrees/047-materials-management-system/.claude/commands/
```

Commands now appear once, discovered via upward traversal to the main repo's `.claude/commands/`.

## Workaround for Other Projects

If experiencing duplicate slash commands in worktrees:

1. Check if worktrees have their own `.claude/commands/` directory
2. If yes, remove it: `rm -rf .worktrees/<feature>/.claude/commands/`
3. Commands will be inherited from the main repo via parent directory traversal

Note: This fix may need to be reapplied after running `spec-kitty upgrade` until the upstream bug is fixed.

## Recommended Fix for spec-kitty

### Option A: Fix `m_0_10_1_populate_slash_commands.py`

The populate migration should skip worktrees. Modify lines 128-129:

```python
# Current (buggy):
if agent_dir.parent.exists() or agent_root == ".claude":

# Fixed:
from specify_cli.core.paths import is_worktree_context
if not is_worktree_context(project_path):
    if agent_dir.parent.exists() or agent_root == ".claude":
```

Or simpler - check if this is a worktree and skip entirely:

```python
def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
    # Skip worktrees - they inherit commands from main repo
    from specify_cli.core.paths import is_worktree_context
    if is_worktree_context(project_path):
        return MigrationResult(
            success=True,
            changes_made=["Skipped: worktrees inherit commands from main repo"],
            errors=[],
            warnings=[],
        )
    # ... rest of apply logic
```

### Option B: Re-run dedup after populate

Ensure `m_0_7_2_worktree_commands_dedup.py` runs AFTER `m_0_10_1_populate_slash_commands.py` by creating a new migration (e.g., `m_0_10_13_worktree_commands_dedup_v2.py`) that removes worktree commands.

### Recommendation

Option A is cleaner - fix the populate migration to respect the worktree context from the start.
