# spec-kitty agent setup-plan does not find mission-based templates

**Date**: 2026-01-12
**Version**: 0.10.12
**Reporter**: Kent Gale (via Claude Code)
**Related Issue**: https://github.com/Priivacy-ai/spec-kitty/issues/70

## Summary

The `spec-kitty agent feature setup-plan` command fails with "Plan template not found in repository" because it searches for templates in legacy locations (`.kittify/templates/`) rather than the mission-based structure (`.kittify/missions/<mission>/templates/`) introduced in v0.10.x.

## Error Message

```
$ spec-kitty agent feature setup-plan --json
{"error": "Plan template not found in repository"}
```

## Root Cause

In `specify_cli/cli/commands/agent/feature.py` (lines 246-259), the `setup-plan` command uses hardcoded paths that don't account for the mission-based directory structure:

```python
# Find plan template
plan_template_candidates = [
    repo_root / ".kittify" / "templates" / "plan-template.md",
    repo_root / "templates" / "plan-template.md",
]

plan_template = None
for candidate in plan_template_candidates:
    if candidate.exists():
        plan_template = candidate
        break

if plan_template is None:
    raise FileNotFoundError("Plan template not found in repository")
```

However, in v0.10.12's mission-based structure, templates are located at:
```
.kittify/missions/software-dev/templates/plan-template.md
.kittify/missions/research/templates/plan-template.md
```

The `spec-kitty mission current` command correctly identifies the active mission and its path, but the agent commands don't use this information.

## Workaround Applied

Created a symlink from the legacy location to the mission templates.

**Important**: The symlink must be created in BOTH the main repo AND each worktree, since worktrees have their own `.kittify/` directory structure:

```bash
# In main repo
cd /path/to/project
ln -s missions/software-dev/templates .kittify/templates

# In each worktree
cd /path/to/project/.worktrees/NNN-feature-name
ln -s missions/software-dev/templates .kittify/templates
```

This allows `setup-plan` to find the templates via the legacy path. However, the workaround is fragile - each new worktree created by `spec-kitty agent feature create-feature` will need the symlink added manually.

## Suggested Fixes

### Option 1: Use Mission Context (Recommended)

Update `setup-plan` to detect the current mission and look for templates in the mission directory:

```python
from specify_cli.core.missions import get_current_mission

def setup_plan(...):
    # ... existing code ...

    # Get current mission
    mission = get_current_mission(repo_root)

    # Build template candidates including mission path
    plan_template_candidates = [
        repo_root / ".kittify" / "missions" / mission.key / "templates" / "plan-template.md",
        repo_root / ".kittify" / "templates" / "plan-template.md",  # Legacy fallback
        repo_root / "templates" / "plan-template.md",  # Legacy fallback
    ]
```

### Option 2: Init Creates Compatibility Symlink

Have `spec-kitty init` create `.kittify/templates -> missions/<selected-mission>/templates` symlink automatically for backward compatibility with agent commands.

### Option 3: Centralize Template Discovery

Create a shared utility function for template discovery that all commands use:

```python
# In specify_cli/core/templates.py
def find_template(repo_root: Path, template_name: str) -> Optional[Path]:
    """Find template file, checking mission directory first."""
    mission = get_current_mission(repo_root)

    candidates = [
        repo_root / ".kittify" / "missions" / mission.key / "templates" / template_name,
        repo_root / ".kittify" / "templates" / template_name,
        repo_root / "templates" / template_name,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None
```

## Additional Context

This issue was discovered after a clean `spec-kitty init` with v0.10.12. The previous feature cycle (F049) completed successfully, but its `plan.md` may have been created through the workflow prompts rather than the agent command directly.

The `spec-kitty mission current` command correctly shows:
```
Path: /path/to/project/.kittify/missions/software-dev
```

This confirms spec-kitty knows where the mission templates are - the agent commands just don't use this information.

## Environment

- **OS**: macOS 26.2 (Darwin)
- **Python**: 3.13.11
- **spec-kitty-cli**: 0.10.12
- **Installation**: pip (user site-packages)

## Files Affected

The following agent commands likely have the same issue (hardcoded template paths):
- `spec-kitty agent feature setup-plan` - Confirmed affected
- Any other agent commands that copy templates

## Recommendation

Given that v0.10.x introduced the mission-based structure, all template lookups should be updated to check the mission directory first. A centralized template discovery utility (Option 3) would prevent similar issues in the future and make the codebase more maintainable.
