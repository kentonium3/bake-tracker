# Cursor Code Review Prompt: Feature 045 - Cost Architecture Refactor

## Feature Overview

**Feature Number:** F045
**Title:** Cost Architecture Refactor
**High-Level Goal:** Remove cost fields (`unit_cost`, `total_cost`) from definition models (FinishedUnit, FinishedGood) and relocate cost tracking to instance models (ProductionRun, AssemblyRun). This follows the principle "Costs on Instances, Not Definitions" - definitions describe WHAT can be made, while instances capture WHEN it was made and at WHAT COST.

**Specification Files:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/kitty-specs/045-cost-architecture-refactor/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/kitty-specs/045-cost-architecture-refactor/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/kitty-specs/045-cost-architecture-refactor/research.md`

## Code Changes

The following files were modified as part of this feature. These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

**Models:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/models/finished_unit.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/models/finished_good.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/models/package.py`

**Services:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/services/__init__.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/services/finished_unit_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/services/finished_good_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/services/assembly_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/services/package_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/services/import_export_service.py`

**UI:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/ui/forms/finished_unit_detail.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/ui/forms/finished_good_detail.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/ui/forms/package_form.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/ui/packages_tab.py`

**Tests:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/tests/test_event_planning_workflow.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/tests/test_assembly_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/tests/test_batch_production_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/tests/services/test_production_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/tests/services/test_import_export_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/src/tests/integration/test_import_export_v4.py`

**Data Files:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/test_data/sample_data_min.json`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor/test_data/sample_data_all.json`

## Environment Setup

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to the worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor

# Verify Python environment (use main repo's venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.models import FinishedUnit, FinishedGood; print('Models import OK')"

# Verify tests run (quick sanity check)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/test_assembly_service.py -v --tb=short -q 2>&1 | tail -5
```

If ANY verification command fails, STOP immediately and report the failure as a blocker before attempting any fixes.

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP immediately and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use the format below and write to the specified location

## Report Output

Write your review report to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F045-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in the worktree.

## Report Format

Use the following structure for your report:

```markdown
# Code Review: F045 - Cost Architecture Refactor

**Reviewer:** Cursor
**Date:** [DATE]
**Commit Range:** main..045-cost-architecture-refactor

## Executive Summary
[1-2 sentence overview of findings]

## Blockers
[Issues that MUST be fixed before merge - empty if none]

## Critical Issues
[Serious bugs, data integrity risks, security concerns]

## Recommendations
[Suggested improvements, non-blocking concerns]

## Questions for Implementer
[Clarifications needed, design decisions to discuss]

## Verification Results
[Output of environment verification commands]

## Files Reviewed
[List of files examined with brief notes]
```
