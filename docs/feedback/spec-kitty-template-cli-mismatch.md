# GitHub Issue Report: review.md Template References Non-Existent CLI Parameters

**Repository:** Priivacy-ai/spec-kitty
**Related Issue:** #72 (Subtask Completion and Assignee Tracking)
**Prepared:** 2026-01-10
**Reporter:** bake-tracker project

---

## Summary

The `review.md` command template references CLI parameters that do not exist in spec-kitty v0.10.12, causing confusion for AI agents attempting to follow the workflow.

## Affected Files

In the bundled templates (and consequently in initialized projects):
- `.kittify/missions/software-dev/command-templates/review.md`
- `.kittify/templates/command-templates/review.md`

## Problem Details

### Issue 1: Non-existent `--review-status` and `--target-lane` parameters

**Location:** Line 92

**Current text:**
```markdown
* **Alternative:** For custom review statuses, use `--review-status "approved with minor notes"` or `--target-lane "planned"` for rejected tasks.
```

**Actual CLI (`spec-kitty agent tasks move-task --help`):**
```
Options:
  --to               TEXT  Target lane (planned/doing/for_review/done) [required]
  --feature          TEXT  Feature slug (auto-detected if omitted)
  --agent            TEXT  Agent name
  --shell-pid        TEXT  Shell PID
  --note             TEXT  History note
  --json                   Output JSON format
  --help                   Show this message and exit.
```

Neither `--review-status` nor `--target-lane` exist. The lane is specified via `--to`.

### Issue 2: Incorrect `mark-status` command syntax

**Location:** Line 96

**Current text:**
```markdown
Run `spec-kitty agent mark-status --task-id <TASK_ID> --status done` (POSIX) or `spec-kitty agent -TaskId <TASK_ID> -Status done` (PowerShell) from repo root.
```

**Actual CLI (`spec-kitty agent tasks mark-status --help`):**
```
Usage: spec-kitty agent tasks mark-status [OPTIONS] TASK_ID

Arguments:
  *    task_id      TEXT  Task ID (e.g., T001) [required]

Options:
  *  --status         TEXT  Status: done/pending [required]
     --feature        TEXT  Feature slug (auto-detected if omitted)
     --json                 Output JSON format
```

**Issues:**
1. Missing `tasks` in command path (`agent mark-status` vs `agent tasks mark-status`)
2. `--task-id` should be a positional argument, not a named option
3. PowerShell syntax is incorrect

**Correct syntax:**
```bash
spec-kitty agent tasks mark-status <TASK_ID> --status done
```

## Impact

AI agents following the review.md template:
1. Attempt to use non-existent parameters, causing command failures
2. May invent workarounds or bypass validation rather than using correct syntax
3. Reach acceptance stage with incomplete metadata (as documented in #72)

## Suggested Fix

Replace line 92:
```markdown
* **Note:** Use `--note "your review summary"` to document the review outcome in the activity log.
```

Replace line 96:
```markdown
Run `spec-kitty agent tasks mark-status <TASK_ID> --status done` from repo root.
```

## Relationship to Issue #72

This template bug contributes to the problems described in #72:
- Agents can't properly track work completion because the documented commands fail
- The workaround behavior (bypassing validation) masks the underlying tracking issues

Fixing these template references would help agents successfully execute the two-tier tracking system.

## Verification

Commands to verify the issue:
```bash
# These parameters don't exist:
spec-kitty agent tasks move-task --help | grep -E "review-status|target-lane"
# Returns nothing

# Correct parameters:
spec-kitty agent tasks move-task --help | grep -E "\-\-to|\-\-note"
# Returns: --to, --note
```

## Local Fix Applied

We've applied this fix locally to our project templates pending an upstream fix. The changes are minimal and preserve the intent while using correct CLI syntax.

---

**Note:** This issue may be addressed as part of the template updates proposed in #72. Consider consolidating if appropriate.
