# Spec-Kitty Upgrade Issue Report

**Date:** 2026-01-08
**Upgrade Path:** v0.6.4 → v0.10.12
**Project:** bake-tracker
**Reporter:** Kent Gale (via Claude Code)

---

## Summary

The `spec-kitty upgrade` command failed during migration from v0.6.x to v0.10.12. Two migrations could not apply automatically due to missing template files in the installed package. Manual intervention was required to complete the upgrade.

---

## Issue 1: Migration `0.7.3_update_scripts` Fails

### Error Message
```
✗ Cannot apply 0.7.3_update_scripts: Template scripts not found in installed package
```

### Root Cause

The `0.7.3_update_scripts` migration attempts to copy updated bash scripts from the installed package to the project:

```python
# From m_0_7_3_update_scripts.py
def can_apply(self, project_path: Path) -> tuple[bool, str]:
    """Check if we have the template scripts to copy."""
    pkg_scripts = Path(__file__).parent.parent.parent / "scripts" / "bash"
    required = ["create-new-feature.sh"]
    for script in required:
        if not (pkg_scripts / script).exists():
            return False, "Template scripts not found in installed package"
    return True, ""
```

However, the bash scripts were **removed from the package in v0.10.0** (migration `0.10.0_python_only`). This creates a paradox: the upgrade path requires scripts that no longer exist in the target version.

### Workaround Applied

Manually deleted the project's bash scripts directory before running upgrade:

```bash
rm -rf .kittify/scripts/bash/
```

This caused the `0.7.3` migration's `detect()` method to return `False` (script doesn't exist = migration not needed), allowing the upgrade to proceed.

### Suggested Fix

The `0.7.3_update_scripts` migration should be updated to handle the case where:
1. The project has old bash scripts, AND
2. The installed package no longer ships bash scripts

Options:
- **Option A:** Have `can_apply()` return `True` with a note that scripts will be deleted (defer to `0.10.0_python_only`)
- **Option B:** Make `0.7.3` delete scripts if they can't be updated (merge with `0.10.0` behavior)
- **Option C:** Skip `0.7.3` entirely if target version >= 0.10.0 (scripts will be deleted anyway)

---

## Issue 2: Migration `0.10.6_workflow_simplification` Fails

### Error Message
```
✗ Cannot apply 0.10.6_workflow_simplification: Mission templates not updated with workflow commands
```

### Root Cause

The `0.10.6_workflow_simplification` migration requires the project's mission templates to already contain `spec-kitty agent workflow` commands:

```python
# From m_0_10_6_workflow_simplification.py
def can_apply(self, project_path: Path) -> tuple[bool, str]:
    """Check if we have mission templates to copy from."""
    software_dev_templates = missions_dir / "software-dev" / "command-templates"
    if software_dev_templates.exists():
        implement = software_dev_templates / "implement.md"
        if implement.exists():
            content = implement.read_text(encoding="utf-8")
            if "spec-kitty agent workflow implement" in content:
                return True, ""
    return False, "Mission templates not updated with workflow commands"
```

The migration expects to copy from `project/.kittify/missions/software-dev/command-templates/implement.md`, but this file still had the **old content** (with bash script references). The migration doesn't update these templates itself—it only copies them to agent directories.

### Workaround Applied

Manually copied the updated templates from the installed package to the project:

```bash
# Copy command-templates from package to project missions
cp -r /path/to/site-packages/specify_cli/missions/software-dev/command-templates/* \
      .kittify/missions/software-dev/command-templates/

cp -r /path/to/site-packages/specify_cli/missions/research/command-templates/* \
      .kittify/missions/research/command-templates/
```

After this, the `0.10.6` migration detected the project as "already in target state" and succeeded.

### Suggested Fix

The migration should **update** the mission templates from the package, not just check if they're already updated. Either:

- **Option A:** Add a prior migration (e.g., `0.10.5_update_mission_templates`) that copies updated command-templates from the package to `.kittify/missions/*/command-templates/`
- **Option B:** Have `0.10.6` itself copy the templates from the package before checking `can_apply()`
- **Option C:** Change `can_apply()` to check if the **package** has the templates, not the project

---

## Additional Cleanup Required

After the migrations completed, several artifacts still had stale bash script references:

### 1. Obsolete Python Scripts
The following were not removed by any migration:
- `.kittify/scripts/tasks/tasks_cli.py`
- `.kittify/scripts/tasks/task_helpers.py`
- `.kittify/scripts/tasks/acceptance_support.py`
- `.kittify/scripts/debug-dashboard-scan.py`

**Suggestion:** Add cleanup of `.kittify/scripts/tasks/` to `0.10.0_python_only` migration.

### 2. Old `.toml` Files in Agent Directories
`.gemini/commands/` had both `.md` and `.toml` versions of slash commands. The `.toml` files contained bash script references and were not removed.

**Suggestion:** Migration `0.10.2_update_slash_commands` should remove `.toml` files when updating to `.md` format.

### 3. `.kittify/templates/` Not Updated
The templates in `.kittify/templates/` (task-prompt-template.md, agent-file-template.md, etc.) still referenced bash scripts. These are the "master templates" that new features copy from.

**Suggestion:** Add a migration to update `.kittify/templates/` from package templates.

---

## Recommended Migration Improvements

### 1. Add Package-to-Project Template Sync
Create a migration that synchronizes templates from the installed package to the project. This ensures projects get updated templates without manual intervention.

### 2. Handle Removed Dependencies Gracefully
When a migration depends on files that were removed in a later version, the migration should either:
- Skip gracefully with a clear message
- Perform the equivalent cleanup action
- Chain to the migration that removes those files

### 3. Add Pre-flight Validation
Before starting migrations, validate that the entire upgrade path is possible. Currently, migrations fail one at a time, requiring multiple manual interventions.

### 4. Consolidate Overlapping Migrations
Migrations `0.7.3` (update scripts) and `0.10.0` (remove scripts) have overlapping concerns. Consider consolidating or adding skip logic.

---

## Environment Details

- **OS:** macOS Darwin 25.2.0
- **Python:** 3.14.2
- **spec-kitty-cli:** 0.10.12
- **Installation method:** `pip install spec-kitty-cli`

---

## Files Modified During Manual Fix

1. **Deleted:**
   - `.kittify/scripts/bash/` (entire directory, 14 scripts)
   - `.kittify/scripts/tasks/` (entire directory, 3 Python files)
   - `.kittify/scripts/debug-dashboard-scan.py`
   - `.gemini/commands/*.toml` (legacy format files)

2. **Updated from package:**
   - `.kittify/missions/software-dev/command-templates/*.md`
   - `.kittify/missions/research/command-templates/*.md`
   - `.kittify/templates/command-templates/*.md`
   - `.kittify/templates/task-prompt-template.md`
   - `.kittify/templates/agent-file-template.md`
   - `.kittify/templates/POWERSHELL_SYNTAX.md`
   - `.kittify/templates/AGENTS.md`

---

## Conclusion

The upgrade ultimately succeeded after manual intervention. The core issues stem from migrations that depend on files removed in later versions, and migrations that check project state without updating it from the package. Making migrations more self-contained (able to fetch what they need from the package) would significantly improve the upgrade experience.
