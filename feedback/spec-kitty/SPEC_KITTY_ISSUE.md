# Issue: Subtask Completion and Assignee Tracking Not Enforced During Implementation

## Summary

Agents consistently reach `/spec-kitty.accept` with unchecked subtasks in `tasks.md` and missing `assignee` fields in work package frontmatter. This happens because:

1. The `implement.md` prompt doesn't instruct agents to mark subtasks complete after each one
2. The `move-task` command doesn't include `--assignee` in the documented example
3. There's no validation gate preventing moves to `for_review`/`done` when subtasks are incomplete
4. The `review.md` prompt doesn't pre-check subtask completion before proceeding

This results in manual cleanup at acceptance time on every feature.

## Observed Behavior

Every feature implementation follows this pattern:

1. Agent runs `/spec-kitty.implement` for WP01, WP02, etc.
2. Agent moves work packages through lanes correctly (frontmatter `lane:` field updates)
3. Agent does NOT run `mark-status` for individual subtasks (T001, T002, etc.)
4. Agent does NOT set `assignee` when claiming work
5. At `/spec-kitty.accept`, the check fails with:
   - `unchecked_tasks`: 18 items still showing `[ ]` in tasks.md
   - `metadata_issues`: "WP01: missing assignee in frontmatter" (repeated for all WPs)
6. User/agent must manually fix these before acceptance passes

## Root Cause

The spec-kitty workflow has **two-tier tracking** that agents don't understand:

| Tier | File | Marker | Updated By |
|------|------|--------|------------|
| Work Package | `tasks/WP##-*.md` | `lane:` frontmatter | `move-task` command |
| Subtask | `tasks.md` | `- [ ]` / `- [x]` checkbox | `mark-status` command |

**The current prompts only document the work package tier.** Agents don't know `mark-status` exists or when to call it.

## Proposed Solution

### 1. Update `implement.md` Template

Add explicit instructions to:
- Include `--assignee` when moving to `doing`
- Run `mark-status` after completing each subtask
- Verify subtask completion before moving to `for_review`

See attached: `implement.md.proposed`

### 2. Update `review.md` Template

Add pre-check step to:
- Verify all subtasks for the WP are marked `[x]` before proceeding
- Reject reviews where subtasks are incomplete

See attached: `review.md.proposed`

### 3. CLI Enhancement: Validate Subtasks on Lane Transitions

When `spec-kitty agent move-task` is called with target lane `for_review` or `done`:

1. Parse `tasks.md` to find subtasks belonging to this WP
2. Check if all are marked `[x]`
3. If any are `[ ]`:
   - **Default:** Fail with error listing unchecked subtasks and remediation commands
   - **With `--force`:** Warn but allow (for exceptional cases)

Example error output:
```
ERROR: Cannot move WP01 to for_review - unchecked subtasks:
  - [ ] T001 Change FK ondelete RESTRICT → CASCADE
  - [ ] T003 Integrate uniqueness check into create_finished_unit()

Mark these complete first:
  spec-kitty agent mark-status --task-id T001 --status done
  spec-kitty agent mark-status --task-id T003 --status done

Or use --force to override (not recommended)
```

### 4. CLI Enhancement: Separate `--lenient` from Subtask Validation

Current behavior: `--lenient` bypasses all validation including unchecked tasks.

Proposed behavior:
- `--lenient` skips metadata warnings (missing assignee, shell_pid)
- `--lenient` does NOT skip unchecked subtasks (this indicates incomplete work)
- New flag `--skip-task-check` for truly exceptional cases

## Impact

Without this fix:
- Every feature requires manual cleanup at acceptance
- Agents don't learn the correct workflow (prompts don't teach it)
- The two-tier tracking system is effectively broken for AI agents

With this fix:
- Agents are taught the full workflow in `implement.md`
- Validation gates catch issues early (at `move-task` time, not `accept` time)
- `review.md` enforces completeness before review proceeds
- Acceptance becomes a true validation step, not a cleanup step

## Environment

- spec-kitty version: 0.10.12
- Observed across multiple features (F042, F043, F044)
- Agents affected: Claude Code, Gemini CLI

## Attachments

- `implement.md.proposed` - Proposed template with subtask tracking instructions
- `review.md.proposed` - Proposed template with pre-check validation
