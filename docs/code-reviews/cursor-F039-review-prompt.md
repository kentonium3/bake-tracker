# Cursor Code Review Prompt - Feature 039: Planning Workspace (Service Layer)

## Role

You are a senior software engineer performing an independent code review of Feature 039 (planning-workspace). This is a **partial feature review** covering the completed **Service Layer (WP01-WP06)**. The UI work packages (WP07-WP09) are still pending and NOT included in this review.

## Important Instructions

1. **Run verification commands outside the sandbox** - venv activation will fail inside sandbox
2. **If any verification command fails, STOP and report the blocker** - do not attempt fixes
3. **Write the report to** `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F039-review.md` (NOT in the worktree)

## Feature Summary

**Core Purpose:** Provide automatic batch calculation to prevent underproduction during holiday baking events. The planning workspace helps users answer "How much do I need to bake?" and tracks progress through shopping, production, and assembly phases.

**Completed Service Layer (WP01-WP06):**

1. **WP01 - Model Foundation**: ProductionPlanSnapshot model, Event.output_mode (BUNDLED/BULK_COUNT)
2. **WP02 - Batch Calculation Service**: calculate_batches (always round UP), waste calculation, bundle explosion, recipe aggregation
3. **WP03 - Shopping List Service**: Shopping list generation, gap calculation, mark_shopping_complete
4. **WP04 - Feasibility Service**: Production/assembly feasibility checks, partial assembly calculation
5. **WP05 - Progress Service**: Production/assembly progress tracking with DTOs
6. **WP06 - Planning Service Facade**: Orchestration of all modules, calculate_plan, check_staleness, get_plan_summary

**Key Architecture:**
- BUNDLED mode: User specifies bundle quantities (EventAssemblyTarget), system explodes to recipe batches
- BULK_COUNT mode: User specifies recipe batches directly (EventProductionTarget)
- Staleness detection: Compares calculated_at timestamp against model modifications
- Session management: All functions accept optional `session` parameter per project patterns

## Files to Review

### Model Layer (WP01)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/models/production_plan_snapshot.py`
  - ProductionPlanSnapshot model with event_id, calculated_at, is_stale, shopping_complete
  - Timestamp fields for staleness: requirements_updated_at, recipes_updated_at, bundles_updated_at
  - calculation_results JSON blob (recipe_batches, aggregated_ingredients, shopping_list)
  - Helper methods: get_recipe_batches(), get_shopping_list(), mark_stale()

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/models/event.py`
  - OutputMode enum (BUNDLED, BULK_COUNT)
  - Event.output_mode field
  - production_plan_snapshots relationship

### Batch Calculation Service (WP02)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/services/planning/batch_calculation.py`
  - calculate_batches(units_needed, yield_per_batch) - ALWAYS rounds UP
  - calculate_waste(units_needed, batches, yield_per_batch) - returns (waste_units, waste_percent)
  - explode_bundle_requirements(finished_good_id, bundle_quantity, session) - recursive bundle explosion
  - aggregate_by_recipe(unit_quantities, session) - groups FinishedUnits by recipe
  - RecipeBatchResult dataclass

### Shopping List Service (WP03)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/services/planning/shopping_list.py`
  - ShoppingListItem dataclass (ingredient_id, needed, in_stock, to_buy, is_sufficient)
  - calculate_purchase_gap(needed, in_stock) - returns max(0, needed - in_stock)
  - get_shopping_list(event_id, session) - generates shopping list from event
  - mark_shopping_complete(event_id, session) - updates ProductionPlanSnapshot
  - Session management pattern throughout

### Feasibility Service (WP04)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/services/planning/feasibility.py`
  - FeasibilityStatus enum (CAN_ASSEMBLE, PARTIAL, CANNOT_ASSEMBLE, AWAITING_PRODUCTION)
  - FeasibilityResult dataclass
  - check_production_feasibility(event_id, session) - wraps batch_production_service
  - check_assembly_feasibility(event_id, session) - wraps assembly_service
  - Partial assembly calculation: minimum across all component inventories

### Progress Service (WP05)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/services/planning/progress.py`
  - ProductionProgress dataclass (recipe_id, target_batches, completed_batches, progress_percent)
  - AssemblyProgress dataclass (finished_good_id, target_quantity, assembled_quantity)
  - get_production_progress(event_id, session)
  - get_assembly_progress(event_id, session)
  - get_overall_progress(event_id, session) - returns dict with production_percent, assembly_percent

### Planning Service Facade (WP06)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/services/planning/planning_service.py`
  - calculate_plan(event_id, force_recalculate, session) - main orchestration
  - check_staleness(event_id, session) - timestamp-based detection
  - get_plan_summary(event_id, session) - returns PlanSummary with phase statuses
  - get_assembly_checklist(event_id, session)
  - Exceptions: PlanningError, StalePlanError, EventNotConfiguredError, EventNotFoundError
  - DTOs: PlanSummary, PlanPhase, PhaseStatus

### Module Init

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/services/planning/__init__.py`
  - Exports all public functions and classes from submodules

### Tests

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/tests/services/planning/test_batch_calculation.py` (28 tests)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/tests/services/planning/test_shopping_list.py` (25 tests)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/tests/services/planning/test_feasibility.py` (18 tests)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/tests/services/planning/test_progress.py` (29 tests)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/src/tests/services/planning/test_planning_service.py` (27 tests)

### Specification Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/kitty-specs/039-planning-workspace/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/kitty-specs/039-planning-workspace/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/kitty-specs/039-planning-workspace/tasks.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/kitty-specs/039-planning-workspace/data-model.md`

### Work Package Prompts (for context)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/kitty-specs/039-planning-workspace/tasks/for_review/WP01-model-foundation.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/kitty-specs/039-planning-workspace/tasks/for_review/WP02-batch-calculation-service.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/kitty-specs/039-planning-workspace/tasks/for_review/WP03-shopping-list-service.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/kitty-specs/039-planning-workspace/tasks/for_review/WP04-feasibility-service.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/kitty-specs/039-planning-workspace/tasks/for_review/WP05-progress-service.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace/kitty-specs/039-planning-workspace/tasks/for_review/WP06-planning-service-facade.md`

## Review Checklist

### 1. Model Layer (WP01)

- [ ] ProductionPlanSnapshot model exists with required fields
- [ ] calculation_results JSON stores recipe_batches, shopping_list
- [ ] Staleness timestamp fields: requirements_updated_at, recipes_updated_at, bundles_updated_at
- [ ] shopping_complete and shopping_completed_at fields exist
- [ ] Helper methods: get_recipe_batches(), get_shopping_list(), mark_stale()
- [ ] OutputMode enum (BUNDLED, BULK_COUNT) in event.py
- [ ] Event.output_mode field with proper enum type
- [ ] Event.production_plan_snapshots relationship

### 2. Batch Calculation Service (WP02)

- [ ] calculate_batches() ALWAYS rounds UP (uses math.ceil)
- [ ] calculate_batches() raises ValueError for yield_per_batch <= 0
- [ ] calculate_waste() returns (waste_units, waste_percent)
- [ ] explode_bundle_requirements() handles nested FinishedGoods recursively
- [ ] explode_bundle_requirements() detects circular references
- [ ] aggregate_by_recipe() groups FinishedUnits by recipe_id
- [ ] RecipeBatchResult dataclass has all required fields
- [ ] Session passed through all nested calls

### 3. Shopping List Service (WP03)

- [ ] calculate_purchase_gap() returns max(0, needed - in_stock) - never negative
- [ ] ShoppingListItem has is_sufficient field (in_stock >= needed)
- [ ] get_shopping_list() wraps event_service correctly
- [ ] mark_shopping_complete() updates ProductionPlanSnapshot
- [ ] Session management pattern followed (session=None with fallback)
- [ ] Decimal used for quantity calculations

### 4. Feasibility Service (WP04)

- [ ] FeasibilityStatus has CAN_ASSEMBLE, PARTIAL, CANNOT_ASSEMBLE, AWAITING_PRODUCTION
- [ ] FeasibilityResult has can_assemble count for partial assembly
- [ ] check_production_feasibility() wraps batch_production_service
- [ ] check_assembly_feasibility() wraps assembly_service
- [ ] Partial assembly calculates minimum across all component inventories
- [ ] Status determination: AWAITING_PRODUCTION when FinishedUnits have zero inventory

### 5. Progress Service (WP05)

- [ ] ProductionProgress dataclass with progress_percent
- [ ] AssemblyProgress dataclass with progress_percent
- [ ] get_overall_progress() returns dict with production_percent, assembly_percent
- [ ] Progress percentages can exceed 100% (over-production)
- [ ] Session management pattern followed

### 6. Planning Service Facade (WP06)

- [ ] calculate_plan() supports both BUNDLED and BULK_COUNT modes
- [ ] calculate_plan() raises EventNotConfiguredError when output_mode is None
- [ ] calculate_plan() raises EventNotFoundError for nonexistent events
- [ ] calculate_plan() persists to ProductionPlanSnapshot
- [ ] check_staleness() compares timestamps correctly (handles timezone-aware/naive)
- [ ] get_plan_summary() returns PlanSummary with phase_statuses dict
- [ ] Exceptions properly defined: PlanningError, StalePlanError, etc.
- [ ] Session passed through all delegated calls

### 7. Code Quality

- [ ] All functions follow session management pattern (session=None with fallback)
- [ ] Docstrings present for public functions
- [ ] No unused imports
- [ ] No debug print statements
- [ ] No business logic in model layer
- [ ] Datetime comparisons handle timezone-aware vs naive correctly

## Verification Commands

**IMPORTANT: Run these commands outside the sandbox to ensure venv activation works. If any command fails, STOP and report the blocker.**

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace

# Activate virtual environment (use main repo venv)
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify all planning modules import correctly
PYTHONPATH=. python3 -c "
from src.models.production_plan_snapshot import ProductionPlanSnapshot
from src.models.event import OutputMode
from src.services.planning import (
    calculate_batches,
    calculate_waste,
    explode_bundle_requirements,
    aggregate_by_recipe,
    RecipeBatchResult,
    calculate_purchase_gap,
    get_shopping_list,
    ShoppingListItem,
    check_production_feasibility,
    check_assembly_feasibility,
    FeasibilityStatus,
    FeasibilityResult,
    get_production_progress,
    get_assembly_progress,
    get_overall_progress,
    ProductionProgress,
    AssemblyProgress,
    calculate_plan,
    check_staleness,
    get_plan_summary,
    PlanningError,
    StalePlanError,
    EventNotConfiguredError,
    PlanSummary,
    PlanPhase,
    PhaseStatus,
)
print('All imports successful')
"

# Verify ProductionPlanSnapshot model structure
grep -n "class ProductionPlanSnapshot" src/models/production_plan_snapshot.py
grep -n "calculated_at\|is_stale\|shopping_complete\|calculation_results" src/models/production_plan_snapshot.py

# Verify OutputMode enum
grep -n "class OutputMode\|BUNDLED\|BULK_COUNT" src/models/event.py

# Verify batch calculation functions
grep -n "def calculate_batches\|def calculate_waste\|def explode_bundle_requirements\|def aggregate_by_recipe" src/services/planning/batch_calculation.py

# Verify shopping list functions
grep -n "def calculate_purchase_gap\|def get_shopping_list\|def mark_shopping_complete" src/services/planning/shopping_list.py

# Verify feasibility functions
grep -n "def check_production_feasibility\|def check_assembly_feasibility\|class FeasibilityStatus" src/services/planning/feasibility.py

# Verify progress functions
grep -n "def get_production_progress\|def get_assembly_progress\|def get_overall_progress" src/services/planning/progress.py

# Verify planning service facade
grep -n "def calculate_plan\|def check_staleness\|def get_plan_summary\|class PlanningError" src/services/planning/planning_service.py

# Verify round-up behavior in batch calculation
grep -n "math.ceil" src/services/planning/batch_calculation.py

# Run all planning tests
PYTHONPATH=. python3 -m pytest src/tests/services/planning/ -v --tb=short 2>&1 | tail -50

# Run full test suite to verify no regressions (just summary)
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -30

# Check git log for F039 commits
git log --oneline -15
```

## Key Implementation Patterns

### Batch Calculation (Always Round UP)
```python
def calculate_batches(units_needed: int, yield_per_batch: int) -> int:
    """Calculate batches needed. Always rounds UP to prevent shortfall."""
    if yield_per_batch <= 0:
        raise ValueError("yield_per_batch must be greater than 0")
    if units_needed <= 0:
        return 0
    return math.ceil(units_needed / yield_per_batch)
```

### Session Management Pattern
```python
def some_function(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> SomeResult:
    """Function accepting optional session."""
    if session is not None:
        return _some_function_impl(event_id, session)
    with session_scope() as session:
        return _some_function_impl(event_id, session)
```

### Staleness Detection Pattern
```python
def _check_staleness_impl(event_id: int, session: Session) -> Tuple[bool, Optional[str]]:
    # Normalize datetimes to handle timezone-aware vs naive
    calculated_at = _normalize_datetime(plan.calculated_at)

    # Compare against all relevant timestamps
    if event.last_modified > calculated_at:
        return True, "Event modified since plan calculation"

    for target in event.assembly_targets:
        if target.updated_at > calculated_at:
            return True, f"Assembly target modified"
    # ... etc
```

## Output Format

Write your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F039-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 039 - Planning Workspace (Service Layer)

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 039-planning-workspace
**Branch/Worktree:** `.worktrees/039-planning-workspace`
**Scope:** Service Layer Only (WP01-WP06) - UI work packages (WP07-WP09) pending

## Summary

[Brief overview - is the service layer architecture sound? Are there blocking issues?]

## Verification Results

### Module Import Validation
- production_plan_snapshot.py: [PASS/FAIL]
- batch_calculation.py: [PASS/FAIL]
- shopping_list.py: [PASS/FAIL]
- feasibility.py: [PASS/FAIL]
- progress.py: [PASS/FAIL]
- planning_service.py: [PASS/FAIL]

### Test Results
- Batch calculation tests: [X passed, Y failed]
- Shopping list tests: [X passed, Y failed]
- Feasibility tests: [X passed, Y failed]
- Progress tests: [X passed, Y failed]
- Planning service tests: [X passed, Y failed]
- Full test suite: [X passed, Y skipped, Z failed]

### Code Pattern Validation
- Model layer (WP01): [correct/issues found]
- Batch calculation (WP02): [correct/issues found]
- Shopping list (WP03): [correct/issues found]
- Feasibility (WP04): [correct/issues found]
- Progress (WP05): [correct/issues found]
- Planning facade (WP06): [correct/issues found]

## Findings

### Critical Issues
[Any blocking issues that must be fixed before continuing to UI work]

### Warnings
[Non-blocking concerns that should be addressed]

### Observations
[General observations about code quality, patterns, potential improvements]

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/models/production_plan_snapshot.py | [status] | [notes] |
| src/models/event.py | [status] | [notes] |
| src/services/planning/batch_calculation.py | [status] | [notes] |
| src/services/planning/shopping_list.py | [status] | [notes] |
| src/services/planning/feasibility.py | [status] | [notes] |
| src/services/planning/progress.py | [status] | [notes] |
| src/services/planning/planning_service.py | [status] | [notes] |
| src/services/planning/__init__.py | [status] | [notes] |
| src/tests/services/planning/*.py | [status] | [notes] |

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: Batch calculation always rounds UP | [PASS/FAIL] | [evidence] |
| FR-002: Waste percentage calculated correctly | [PASS/FAIL] | [evidence] |
| FR-003: Bundle explosion handles nesting | [PASS/FAIL] | [evidence] |
| FR-004: Circular reference detection | [PASS/FAIL] | [evidence] |
| FR-005: Shopping gap never negative | [PASS/FAIL] | [evidence] |
| FR-006: Feasibility status accurate | [PASS/FAIL] | [evidence] |
| FR-007: Partial assembly calculation correct | [PASS/FAIL] | [evidence] |
| FR-008: Progress tracking accurate | [PASS/FAIL] | [evidence] |
| FR-009: Staleness detection works | [PASS/FAIL] | [evidence] |
| FR-010: Plan persists to snapshot | [PASS/FAIL] | [evidence] |
| Session management pattern followed | [PASS/FAIL] | [evidence] |
| All existing tests pass (no regressions) | [PASS/FAIL] | [evidence] |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Model Foundation | [PASS/FAIL] | [notes] |
| WP02: Batch Calculation Service | [PASS/FAIL] | [notes] |
| WP03: Shopping List Service | [PASS/FAIL] | [notes] |
| WP04: Feasibility Service | [PASS/FAIL] | [notes] |
| WP05: Progress Service | [PASS/FAIL] | [notes] |
| WP06: Planning Service Facade | [PASS/FAIL] | [notes] |

## Code Quality Assessment

### Session Management
[Any concerns about session handling - are sessions passed through correctly?]

### Edge Cases
[Any edge cases that may not be handled properly]

### Data Types
[Proper use of Decimal vs float, datetime handling, etc.]

### Test Coverage
[Are the tests comprehensive? Any gaps?]

## Potential Issues

### Datetime Handling
[Any concerns about timezone-aware vs naive datetime comparisons]

### Decimal Precision
[Any concerns about Decimal vs float usage]

### Error Handling
[Are exceptions properly defined and raised?]

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

**Next Steps:**
- [Any recommended actions before proceeding to UI work (WP07-WP09)]
```

## Additional Context

- This is a **partial feature review** - UI work packages (WP07-WP09) are NOT included
- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI (not yet implemented for F039)
- pytest for testing
- The worktree is at `.worktrees/039-planning-workspace`
- Layered architecture: UI -> Services -> Models -> Database
- Session management is CRITICAL: functions must accept optional `session` parameter
- All existing tests must pass (no regressions)
- There may be FK cycle warnings during test teardown (non-blocking, known issue)
- Datetime comparisons must handle both timezone-aware and naive datetimes (SQLite returns naive)
