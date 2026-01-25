# spec-kitty Bug Report: Acceptance Checker History Validation Mismatch

**Date:** 2026-01-25
**Version:** spec-kitty-cli 0.12.1
**Severity:** Medium - Acceptance fails due to metadata mismatch, workaround available (`--lenient`)
**Reporter:** Claude Opus (via Kent Gale)
**Status:** OPEN - Workaround available

## Summary

The `spec-kitty accept` command fails validation because it expects lane transition history entries in the YAML frontmatter `history` array, but the `spec-kitty agent tasks move-task` command only adds entries to the markdown Activity Log section (not the YAML frontmatter).

This creates a mismatch where:
1. Work packages correctly transition through lanes (planned → doing → for_review → done)
2. The `lane:` field in YAML frontmatter is correctly updated
3. The Activity Log section in markdown body correctly records transitions
4. **BUT** the YAML `history` array in frontmatter is NOT updated
5. Acceptance checker validates the YAML `history` array and fails

## Root Cause

The acceptance checker (`spec-kitty accept`) looks for lane entries in two places:

1. **YAML frontmatter `history` array** - expects structured entries like:
   ```yaml
   history:
   - timestamp: '2026-01-25T18:28:06Z'
     lane: done
     agent: claude-opus
     shell_pid: '51754'
     action: Review passed
   ```

2. **Markdown Activity Log section** - formatted text entries like:
   ```markdown
   ## Activity Log
   - 2026-01-25T18:28:06Z – claude-opus – shell_pid=51754 – lane=done – Review passed
   ```

The `move-task` command only writes to format #2 (Activity Log), but the acceptance validation expects format #1 (YAML history).

## Evidence

### Acceptance Check Output (JSON)

```json
{
  "work_packages": [
    {
      "id": "WP01",
      "lane": "done",
      "latest_lane": "planned",       // ← From YAML history array
      "has_lane_entry": false,         // ← Expecting lane=done in YAML history
      "metadata": {
        "lane": "done",                // ← Correctly updated by move-task
        "agent": "claude-opus"
      }
    }
  ],
  "activity_issues": [
    "WP01: Activity Log missing entry for lane=done",
    "WP01: latest Activity Log entry not lane=done"
  ]
}
```

Note: `lane: "done"` is correctly set in frontmatter, but `latest_lane` shows "planned" because that's the last entry in the YAML `history` array.

### WP Frontmatter (After move-task)

```yaml
---
work_package_id: WP01
lane: "done"                          # ← Correctly updated
history:
- timestamp: '2026-01-25T18:09:19Z'
  lane: planned                       # ← Only entry in YAML history
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---
```

### Activity Log Section (Correctly Updated)

```markdown
## Activity Log

- 2026-01-25T18:09:19Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-25T18:18:06Z – claude-opus – shell_pid=47605 – lane=for_review – Implemented...
- 2026-01-25T18:27:33Z – claude-opus – shell_pid=51754 – lane=doing – Started review...
- 2026-01-25T18:28:06Z – claude-opus – shell_pid=51754 – lane=done – Review passed...
```

The Activity Log shows the complete lane progression, but the YAML `history` array only has the initial entry.

## Commands That Fail

```bash
spec-kitty accept --actor "claude-opus" --feature "067-recipe-ui-polish-yield-variants" --mode local

# Output: "Outstanding acceptance issues detected"
# activity_issues: "Activity Log missing entry for lane=done"
```

## Commands That Work (But Don't Fix Root Cause)

```bash
# This adds to Activity Log section, not YAML history
spec-kitty agent tasks add-history WP01 --note "lane=done – Review passed" --agent claude-opus
```

## Impact

**Feature merges are blocked** without using `--lenient` flag:
- All implemented and reviewed work packages fail acceptance
- Manual workaround required for every feature completion
- Metadata tracking becomes inconsistent between YAML and markdown

**Data integrity concern:**
- Two sources of truth for lane history (YAML vs markdown)
- They can become out of sync
- Unclear which is authoritative

## Expected Behavior

When `spec-kitty agent tasks move-task WP01 --to done` is run:

1. ✅ Update `lane: "done"` in YAML frontmatter (currently works)
2. ❌ Add entry to YAML `history` array with `lane: done` (NOT WORKING)
3. ✅ Add entry to markdown Activity Log section (currently works)

The acceptance checker should then pass because the YAML history array contains a `lane: done` entry.

## Suggested Fixes

### Option 1: Update move-task to Write YAML History

Modify `move-task` command to also append to the YAML `history` array:

```python
# In move-task implementation
history_entry = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "lane": new_lane,
    "agent": agent_name,
    "shell_pid": shell_pid,
    "action": note or f"Moved to {new_lane}"
}
wp_frontmatter["history"].append(history_entry)
```

### Option 2: Update Acceptance Checker to Parse Activity Log

Modify acceptance validation to parse the markdown Activity Log section instead of (or in addition to) the YAML history array.

### Option 3: Consolidate to Single Source

Decide whether YAML history or Activity Log is authoritative, and:
- Remove the redundant format
- Update all commands to use the chosen format
- Update validators to check the chosen format

## Reproduction Steps

1. Create a new feature with `spec-kitty specify`
2. Generate tasks with `spec-kitty tasks`
3. Implement a WP and move through lanes:
   ```bash
   spec-kitty agent workflow implement WP01 --agent claude
   # ... implement ...
   spec-kitty agent tasks move-task WP01 --to for_review
   spec-kitty agent workflow review WP01 --agent claude
   spec-kitty agent tasks move-task WP01 --to done
   ```
4. Run acceptance:
   ```bash
   spec-kitty accept --mode local
   ```
5. Observe failure with "Activity Log missing entry for lane=done"

## Current Workaround

Use `--lenient` flag to skip strict metadata validation:

```bash
spec-kitty accept --actor "claude-opus" --mode local --lenient
```

This allows acceptance to proceed while the bug is fixed, but does not resolve the underlying data inconsistency.

## Environment

- OS: macOS Darwin 25.2.0
- spec-kitty-cli: 0.12.1
- Feature attempted: 067-recipe-ui-polish-yield-variants
- Agent: Claude Opus 4.5
- All 4 WPs correctly at `lane: "done"` in frontmatter
- All 4 WPs have complete Activity Log entries in markdown

## Related Issues

- The `add-history` command has the same limitation - writes to Activity Log, not YAML history
- There may be similar discrepancies between frontmatter fields and markdown sections
