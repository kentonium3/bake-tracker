# Cursor Code Review Prompt: F078 Plan Snapshots & Amendments

## Your Role

You are a senior software engineer performing an independent code review. You are discovering this feature for the first time. Your fresh perspective is valuable for finding issues that might be missed by the implementer.

## Feature Overview

**Feature Number**: F078
**Title**: Plan Snapshots & Amendments
**User Goal**: Enable bakery planners to capture a complete snapshot of their production plan when starting production, record amendments (drop FG, add FG, modify batch) during production with required reasons, view amendment history, and compare the original plan against the current state.

## Specification

Read the full spec before examining any code:
`/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/078-plan-snapshots-amendments/spec.md`

## Code Changes

The following files were modified or created for this feature:

**Models:**
- `/Users/kentgale/Vaults-repos/bake-tracker/src/models/plan_snapshot.py` (new)
- `/Users/kentgale/Vaults-repos/bake-tracker/src/models/__init__.py` (modified)
- `/Users/kentgale/Vaults-repos/bake-tracker/src/models/event.py` (modified)

**Services:**
- `/Users/kentgale/Vaults-repos/bake-tracker/src/services/plan_snapshot_service.py` (new)
- `/Users/kentgale/Vaults-repos/bake-tracker/src/services/plan_amendment_service.py` (new)
- `/Users/kentgale/Vaults-repos/bake-tracker/src/services/plan_state_service.py` (modified)

**UI:**
- `/Users/kentgale/Vaults-repos/bake-tracker/src/ui/planning_tab.py` (modified)

**Tests:**
- `/Users/kentgale/Vaults-repos/bake-tracker/src/tests/test_plan_snapshot_model.py` (new)
- `/Users/kentgale/Vaults-repos/bake-tracker/src/tests/test_plan_snapshot_service.py` (new)
- `/Users/kentgale/Vaults-repos/bake-tracker/src/tests/test_plan_amendment_service.py` (new)

**Note**: These are the primary changes, but your review should extend to any related code, dependencies, or callers as needed.

## Environment Setup Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.**

Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker

# Activate virtual environment
source venv/bin/activate

# Verify imports work
python -c "from src.models import PlanSnapshot; from src.services import plan_snapshot_service, plan_amendment_service; print('Imports OK')"

# Run F078 tests to verify environment
pytest src/tests/test_plan_snapshot_service.py src/tests/test_plan_amendment_service.py -v --tb=short
```

If ANY of these commands fail, STOP immediately and report the blocker before attempting any fixes.

## Review Approach

1. **Read the spec first** - Understand the intended behavior BEFORE examining the implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on the spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If any fail, STOP and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write your report** - Use the format below

## Report Output

Write your review report to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F078-review.md`

**Important**: Write to the `docs/code-reviews/` directory, NOT in any worktree.

## Report Format

Structure your report with these sections:

```markdown
# Code Review Report: F078 Plan Snapshots & Amendments

**Reviewer**: Cursor
**Date**: [date]
**Commit**: [commit hash reviewed]

## Summary
[Brief overall assessment - 2-3 sentences]

## Blockers
[Issues that MUST be fixed before merge - if none, state "None"]

## Critical Issues
[Serious problems that should be addressed - bugs, data integrity risks, security concerns]

## Recommendations
[Suggested improvements - code quality, patterns, edge cases]

## Observations
[Notable findings - good patterns observed, questions, areas for future consideration]

## Verification Results
[Output/results of running the verification commands]
```
