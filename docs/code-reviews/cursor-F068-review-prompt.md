# Cursor Code Review Prompt: F068 - Event Management & Planning Data Model

## Your Role

You are a senior software engineer performing an independent code review. You are discovering this feature for the first time. Your fresh perspective is valuable for finding issues that the implementer may have missed.

## Feature Overview

**Feature Number**: F068
**Title**: Event Management & Planning Data Model
**User Goal**: Enable users to create, view, edit, and delete planning events with a database schema that supports all Phase 2 planning features (F069-F079) without requiring future schema changes.

## Specification

Read the full requirements here before examining any code:
- **Spec file**: `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/068-event-management-planning-data-model/spec.md`
- **Func spec**: `/Users/kentgale/Vaults-repos/bake-tracker/docs/func-spec/F068_event_management_planning_data_model.md`
- **Data model**: `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/068-event-management-planning-data-model/data-model.md`

## Files Modified

These are the primary changes. Your review should extend to any related code, dependencies, or callers as needed.

**Models (new/modified)**:
- `src/models/__init__.py`
- `src/models/batch_decision.py` (new)
- `src/models/event.py` (modified - added planning fields)
- `src/models/event_finished_good.py` (new)
- `src/models/event_recipe.py` (new)
- `src/models/plan_amendment.py` (new)
- `src/models/planning_snapshot.py` (new)

**Services**:
- `src/services/event_service.py` (modified)
- `src/services/import_export_service.py` (modified - added planning tables)

**UI**:
- `src/ui/forms/event_planning_form.py` (new)
- `src/ui/main_window.py` (modified)
- `src/ui/modes/plan_mode.py` (modified)
- `src/ui/planning_tab.py` (new)

**Tests**:
- `src/tests/integration/test_import_export_planning.py` (new)
- `src/tests/test_event_planning.py` (new)

**Other**:
- `.gitignore`

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to project root
cd /Users/kentgale/Vaults-repos/bake-tracker

# Verify imports work (tests that models load)
./run-tests.sh -v -k "test_event_exports_expected_attendees" 2>&1 | tail -20

# Verify test suite runs
./run-tests.sh src/tests/integration/test_import_export_planning.py -v 2>&1 | tail -30
```

If ANY verification command fails, STOP immediately and report as a blocker before attempting any fixes.

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use the format below and write to specified location

## Report Output

Write your review report to:
**`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F068-review.md`**

Important: Write to the `docs/code-reviews/` directory in the main repo, NOT in any worktree.

## Report Format

Use this structure for your report:

```markdown
# Code Review Report: F068 - Event Management & Planning Data Model

**Reviewer**: Cursor
**Date**: [date]
**Verdict**: [APPROVE / APPROVE WITH SUGGESTIONS / REQUEST CHANGES / BLOCKER]

## Executive Summary

[2-3 sentences summarizing your overall assessment]

## Verification Results

[Results of running the verification commands - did they pass?]

## Findings

### Critical Issues (must fix)

[List any issues that would block approval]

### Suggestions (should consider)

[List improvements that would strengthen the implementation]

### Observations (informational)

[Any other notes, questions, or observations]

## Areas Reviewed

[List the areas you examined and your confidence level in each]

## Recommendation

[Your final recommendation with rationale]
```

## Begin Review

Start by reading the spec file, then form your own expectations before examining the implementation.
