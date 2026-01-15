# GitHub Issue Report: Template/CLI Mismatch Issues

**Repository:** Priivacy-ai/spec-kitty
**Issue Filed:** #74
**Status:** Multiple issues identified - some upstream bugs, some upgrade path issues
**Prepared:** 2026-01-10
**Updated:** 2026-01-15
**Reporter:** bake-tracker project

---

## Issue 2: Package Templates Have Wrong CLI Syntax (NEW - 2026-01-15)

### Summary

The spec-kitty package (v0.10.13) bundles templates with **incorrect CLI syntax** in their YAML frontmatter. This causes Claude Code skill invocations to fail because the `scripts:` frontmatter references commands that don't exist.

### Symptoms Observed

When running `/spec-kitty.specify`, Claude Code received a template with this command:
```bash
spec-kitty agent create-feature --json "{ARGS}"
```

But the actual CLI requires:
```bash
spec-kitty agent feature create-feature "<slug>" --json
```

The command failed with: `No such command 'create-feature'. Did you mean 'feature'?`

### Root Cause Investigation

**Package template location:**
`/Users/kentgale/Library/Python/3.13/lib/python/site-packages/specify_cli/templates/command-templates/specify.md`

**Package template frontmatter (WRONG):**
```yaml
---
description: Create or update the feature specification from a natural language feature description.
scripts:
  sh: spec-kitty agent create-feature --json "{ARGS}"
  ps: spec-kitty agent create-feature --json "{ARGS}"
---
```

**Local project template location:**
`.kittify/missions/software-dev/command-templates/specify.md`

**Local template frontmatter (CORRECT):**
```yaml
---
description: Create or update the feature specification from a natural language feature description.
---
```

The local template correctly removed the `scripts:` frontmatter and has the correct command in the template body:
```bash
spec-kitty agent feature create-feature "<slug>" --json
```

### Why Package Templates Are Being Used

1. **Broken AGENTS.md symlink**: The project's `.kittify/AGENTS.md` is a broken symlink:
   ```
   .kittify/AGENTS.md -> ../../../.kittify/AGENTS.md
   ```
   This resolves to `/Users/kentgale/.kittify/AGENTS.md` which doesn't exist.

2. **Skill discovery fallback**: When local template discovery fails (possibly due to the broken symlink), Claude Code's skill system falls back to package-bundled templates.

3. **Path structure mismatch**: The package template claims to be at `.kittify/templates/commands/specify.md` but:
   - Package actual path: `specify_cli/templates/command-templates/`
   - Local actual path: `.kittify/missions/software-dev/command-templates/`
   - Neither matches the claimed path

### Evidence

**Diff between package and local templates (key sections):**

Package has outdated `scripts:` block:
```diff
< scripts:
<   sh: spec-kitty agent create-feature --json "{ARGS}"
<   ps: spec-kitty agent create-feature --json "{ARGS}"
```

Package has placeholder-based instructions:
```diff
< 2. When discovery is complete... run the script `{SCRIPT}` from repo root
---
> 2. When discovery is complete... run the feature creation command from repo root:
>    ```bash
>    spec-kitty agent feature create-feature "<slug>" --json
>    ```
```

### This IS an Upstream Bug

Unlike Issue 1 (which was an upgrade path issue), this is a **genuine package bug**:

1. The package ships with templates whose `scripts:` frontmatter doesn't match the CLI
2. A fresh install of spec-kitty v0.10.13 would have this problem
3. The package's internal consistency is broken - templates reference commands that don't exist

### Recommended Fixes for spec-kitty

**Priority 1 - Fix package templates:**
1. Update all templates in `src/specify_cli/templates/command-templates/` to use correct CLI syntax
2. Either remove obsolete `scripts:` frontmatter or update to correct commands
3. The `scripts:` frontmatter in specify.md should be:
   ```yaml
   scripts:
     sh: spec-kitty agent feature create-feature "{SLUG}" --json
     ps: spec-kitty agent feature create-feature "{SLUG}" --json
   ```
   (Note: The template format may need to change since the command takes a slug, not the raw ARGS)

**Priority 2 - Add consistency tests:**
1. Add automated tests that verify template `scripts:` commands match actual CLI
2. Parse each template's frontmatter and validate the command exists

**Priority 3 - Fix AGENTS.md symlink creation:**
1. The `spec-kitty init` creates broken symlinks pointing to non-existent global `.kittify/`
2. Either create the global directory or don't create symlinks to it

### Local Workaround Applied

See "Local Fix" section below for how we resolved this in the bake-tracker project.

---

## Issue 1: review.md Template References Non-Existent CLI Parameters (Original Issue)

### Update: This Was an Upgrade Path Issue

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

---

## Local Fix Applied (2026-01-15)

To resolve Issue 2 (package template CLI mismatch) in the bake-tracker project, we need to:

### Step 1: Fix Broken AGENTS.md Symlink

The symlink `.kittify/AGENTS.md` points to non-existent `/Users/kentgale/.kittify/AGENTS.md`.

**Option A - Remove symlink, copy actual file:**
```bash
rm .kittify/AGENTS.md
cp /path/to/specify_cli/templates/AGENTS.md .kittify/AGENTS.md
```

**Option B - Create missing global directory:**
```bash
mkdir -p ~/.kittify
cp /path/to/specify_cli/templates/AGENTS.md ~/.kittify/AGENTS.md
```

### Step 2: Ensure Skill Loader Uses Local Templates

The skill loader needs to find local templates at `.kittify/missions/software-dev/command-templates/` instead of falling back to package templates. This may require:

1. Verifying the local template directory structure matches what the skill loader expects
2. Checking if there's a skill registration mechanism that needs updating
3. Testing that `/spec-kitty.specify` loads the local template after fixing AGENTS.md

### Step 3: Verify Fix

After applying the fix, run `/spec-kitty.specify` and verify:
1. The prompt shows correct CLI syntax: `spec-kitty agent feature create-feature "<slug>" --json`
2. The path reference shows local path, not package path
3. The command executes successfully

### Status

- [ ] AGENTS.md symlink fixed
- [ ] Skill loader verified to use local templates
- [ ] `/spec-kitty.specify` tested and working
