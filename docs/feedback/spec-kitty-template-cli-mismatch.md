# GitHub Issue Report: review.md Template References Non-Existent CLI Parameters

**Repository:** Priivacy-ai/spec-kitty
**Issue Filed:** #74
**Status:** Reclassified as upgrade path issue
**Prepared:** 2026-01-10
**Reporter:** bake-tracker project

---

## Update: This Was an Upgrade Path Issue

After investigation, we discovered this is **NOT an upstream bug**. Fresh spec-kitty v0.10.12 installations use simplified templates that delegate to `spec-kitty agent workflow`:

**Fresh v0.10.12 template:**
```markdown
Run this command to get the work package prompt and review instructions:
spec-kitty agent workflow review $ARGUMENTS
```

**Our project's old template (109 lines):**
Contained verbose inline instructions with outdated CLI syntax referencing non-existent parameters like `--review-status` and `--target-lane`.

## Root Cause

The `spec-kitty upgrade` command reported "Project is already up to date" but did NOT update the command templates from the old verbose format to the new simplified wrapper format.

This is likely because:
1. Template migration was marked as "skipped" or "not applicable" during upgrade
2. The upgrade path doesn't detect content differences in existing templates
3. Templates may have been considered "user customizations" and preserved

## Resolution Applied

We manually updated the local templates to match the current spec-kitty format:
- `.kittify/missions/software-dev/command-templates/implement.md`
- `.kittify/missions/software-dev/command-templates/review.md`
- `.kittify/templates/command-templates/implement.md`
- `.kittify/templates/command-templates/review.md`

## Recommendation for spec-kitty

The upgrade path should either:
1. Detect and offer to replace old verbose templates with new simplified ones
2. Document that template format changes require manual intervention
3. Add a `spec-kitty upgrade --refresh-templates` option for opt-in template replacement

---

## Original Issue Content (for reference)

The original issue documented these problems in the OLD templates:

### Issue 1: Non-existent parameters (Line 92)
```markdown
* **Alternative:** For custom review statuses, use `--review-status "approved with minor notes"` or `--target-lane "planned"` for rejected tasks.
```
Neither `--review-status` nor `--target-lane` exist in the CLI.

### Issue 2: Incorrect mark-status syntax (Line 96)
```markdown
Run `spec-kitty agent mark-status --task-id <TASK_ID> --status done`
```
Should be: `spec-kitty agent tasks mark-status <TASK_ID> --status done`

These issues only affected projects with old templates that weren't refreshed during upgrade.
