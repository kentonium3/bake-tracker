# Cursor Code Review Prompt: F076 Assembly Feasibility & Single-Screen Planning

## Feature Overview

**Feature Number:** F076
**Title:** Assembly Feasibility & Single-Screen Planning
**User Goal:** Integrate Phase 2 planning calculations (F068-F075) into a cohesive single-screen planning experience. Add assembly feasibility validation to check if batch production meets finished goods requirements. Display all planning sections (event, recipes, FGs, batches, shopping, assembly) on one screen with real-time update propagation.

## Specification

Read the feature specification first to understand intended behavior:
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/076-assembly-feasibility-single-screen-planning/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/076-assembly-feasibility-single-screen-planning/plan.md`

## Code Changes

The following files were modified or created for this feature. Review should extend to any related code, dependencies, or callers as needed.

**Service Layer:**
- `src/services/assembly_feasibility_service.py` - New service implementing:
  - `ComponentStatus` dataclass (finished_unit_id, name, quantity_needed, quantity_available, is_sufficient)
  - `FGFeasibilityStatus` dataclass (finished_good_id, name, quantity_needed, can_assemble, shortfall, components)
  - `AssemblyFeasibilityResult` dataclass (overall_feasible, finished_goods list, decided_count, total_fu_count)
  - `calculate_assembly_feasibility(event_id, session=None)` - Main public function
  - Integration with F072 decomposition and batch decision data

**UI Components:**
- `src/ui/components/shopping_summary_frame.py` - New widget showing:
  - "X items to purchase" count
  - "Y items sufficient" count
  - Integration with F075 inventory gap analysis

- `src/ui/components/assembly_status_frame.py` - New widget showing:
  - Overall status indicator with color coding (Ready/Shortfalls/Cannot Assemble/Awaiting)
  - "X of Y finished goods ready" summary
  - Per-FG details with shortfall amounts

- `src/ui/planning_tab.py` - Modified to:
  - Add shopping summary panel
  - Add assembly status panel
  - Wire update callbacks for real-time propagation

**Tests:**
- `src/tests/test_assembly_feasibility_service.py` - Unit tests for feasibility calculations

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Verify environment is functional
cd /Users/kentgale/Vaults-repos/bake-tracker

# Run assembly feasibility tests to confirm environment works
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/test_assembly_feasibility_service.py -v --tb=short

# If the above command fails, STOP and report blocker before proceeding
```

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP immediately and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use template format and write to specified location

## Report Template

Use the template at:
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_code_review_report.md`

## Report Output

Write your review report to:
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F076-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in any worktree.
