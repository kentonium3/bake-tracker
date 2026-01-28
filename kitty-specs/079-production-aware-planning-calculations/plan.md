# Implementation Plan: Production-Aware Planning Calculations

**Branch**: `079-production-aware-planning-calculations` | **Date**: 2026-01-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/079-production-aware-planning-calculations/spec.md`

## Summary

Integrate production progress into planning calculations so that feasibility checks, shopping lists, and amendment validation use **remaining needs** (target - completed) rather than total planned needs. This prevents false warnings during production and protects completed work from amendments.

**Key Integration Points:**
- `planning/progress.py` - Already tracks completed vs target; add remaining calculation
- `planning/feasibility.py` - Modify to use remaining batches for production checks
- `planning/shopping_list.py` - Add production-aware variant for remaining needs
- `plan_amendment_service.py` - Add production validation hook to block changes to completed work

## Technical Context

**Language/Version**: Python 3.10+ (existing project standard)
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter (existing)
**Storage**: SQLite with WAL mode (existing)
**Testing**: pytest with >70% service coverage requirement
**Target Platform**: Desktop (Windows/Mac)
**Project Type**: Single desktop application
**Performance Goals**: Calculations complete within 1 second for typical event (10-20 recipes)
**Constraints**: Must not break existing progress.py/feasibility.py consumers
**Scale/Scope**: Single user, ~50 recipes, ~20 events per year

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Solves real problem: false warnings during production |
| II. Data Integrity & FIFO | ✅ PASS | Uses existing ProductionRun data; no FIFO changes |
| III. Future-Proof Schema | ✅ PASS | No schema changes; uses existing models |
| IV. Test-Driven Development | ✅ PASS | All service changes will have tests |
| V. Layered Architecture | ✅ PASS | Changes are service-layer only |
| VI. Schema Change Strategy | ✅ N/A | No schema changes required |
| VII. Pragmatic Aspiration | ✅ PASS | Clean service layer supports future web migration |

**Desktop Phase Checks:**
- Does this design block web deployment? → NO (service-layer changes only)
- Is the service layer UI-independent? → YES
- Does this support AI-assisted JSON import? → N/A (calculation feature)
- What's the web migration cost? → LOW (stateless functions)

## Project Structure

### Documentation (this feature)

```
kitty-specs/079-production-aware-planning-calculations/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal - no unknowns)
├── data-model.md        # Phase 1 output (RemainingNeeds DTO only)
├── quickstart.md        # Phase 1 output
└── tasks/               # Phase 2 output (WP files)
```

### Source Code (repository root)

```
src/
├── models/              # No changes (uses existing ProductionRun, EventProductionTarget)
├── services/
│   ├── planning/
│   │   ├── progress.py          # ADD: remaining_batches calculation
│   │   ├── feasibility.py       # MODIFY: use remaining for production checks
│   │   ├── shopping_list.py     # MODIFY: production-aware shopping list
│   │   └── planning_service.py  # MODIFY: expose remaining needs in plan summary
│   └── plan_amendment_service.py # MODIFY: add production validation
└── ui/
    └── planning_tab.py          # MODIFY: display remaining vs total

src/tests/
├── planning/
│   ├── test_progress.py         # ADD: remaining tests
│   ├── test_feasibility.py      # ADD: production-aware tests
│   └── test_shopping_list.py    # ADD: remaining needs tests
└── test_plan_amendment_service.py # ADD: production validation tests
```

**Structure Decision**: Single desktop application with layered architecture. All changes are in existing service modules with new tests.

## Complexity Tracking

*No violations - design follows all constitution principles.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | - | - |

---

## Phase 0: Research

**No significant unknowns** - the codebase exploration revealed clear integration points:

1. **Progress tracking** - `progress.py` already has `ProductionProgress` DTO with `completed_batches` and `target_batches`
2. **Feasibility checks** - `feasibility.py` line 254-256 uses `target.target_batches` directly
3. **Shopping list** - `shopping_list.py` wraps `event_service.get_shopping_list()` which uses total needs
4. **Amendment validation** - `plan_amendment_service.py` has `_validate_amendment_allowed()` that can be extended

### Research Findings

**Decision**: Add `remaining_batches` field to `ProductionProgress` DTO and create helper function `get_remaining_production_needs()`.

**Rationale**: Keeps calculation logic centralized; feasibility and shopping_list can import from progress.

**Alternatives Considered**:
- Duplicate remaining calculation in each module → Rejected (DRY violation)
- Add new `remaining_needs.py` module → Rejected (over-engineering for simple calculation)

---

## Phase 1: Design & Contracts

### Data Model

**New DTO Field** (no schema change):

```python
# In progress.py - extend existing ProductionProgress

@dataclass
class ProductionProgress:
    recipe_id: int
    recipe_name: str
    target_batches: int
    completed_batches: int
    remaining_batches: int      # NEW: max(0, target - completed)
    overage_batches: int        # NEW: max(0, completed - target)
    progress_percent: float
    is_complete: bool
```

**New Helper Function**:

```python
def get_remaining_production_needs(
    event_id: int,
    *,
    session: Optional[Session] = None
) -> Dict[int, int]:
    """Get remaining batches needed per recipe.

    Returns:
        Dict mapping recipe_id -> remaining_batches
    """
```

### Service Contracts

**1. Progress Service** (`planning/progress.py`):

```python
# Existing - enhanced
def get_production_progress(event_id, session=None) -> List[ProductionProgress]:
    """Now includes remaining_batches and overage_batches fields."""

# New
def get_remaining_production_needs(event_id, session=None) -> Dict[int, int]:
    """Returns {recipe_id: remaining_batches} for use by other services."""
```

**2. Feasibility Service** (`planning/feasibility.py`):

```python
# Modified signature - add production_aware flag
def check_production_feasibility(
    event_id: int,
    *,
    production_aware: bool = True,  # NEW: default True for remaining-based check
    session: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """Check production feasibility.

    Args:
        production_aware: If True, check remaining batches. If False, check total.
    """
```

**3. Shopping List Service** (`planning/shopping_list.py`):

```python
# Modified signature - add production_aware flag
def get_shopping_list(
    event_id: int,
    *,
    include_sufficient: bool = True,
    production_aware: bool = True,  # NEW: default True for remaining needs
    session: Optional[Session] = None
) -> List[ShoppingListItem]:
```

**4. Amendment Service** (`plan_amendment_service.py`):

```python
# New validation function
def _validate_no_production_for_recipe(
    event_id: int,
    recipe_id: int,
    session: Session
) -> None:
    """Validate no production has been recorded for this recipe.

    Raises:
        ValidationError: If recipe has completed production
    """

def _validate_no_production_for_finished_good(
    event_id: int,
    fg_id: int,
    session: Session
) -> None:
    """Validate no production recorded for FG's recipes.

    Raises:
        ValidationError: If any recipe contributing to this FG has production
    """
```

### UI Updates

**Planning Tab** (`ui/planning_tab.py`):

- Progress bars show "X of Y (Z remaining)" instead of just "X of Y"
- Overage indicator when completed > target: "5 of 3 (+2 overage)"
- Recipe rows with completed production show lock icon (amendment blocked)

---

## Implementation Approach

### Work Package Structure

**WP01: Remaining Needs Calculation** (P1 - Foundation)
- Extend `ProductionProgress` DTO with `remaining_batches`, `overage_batches`
- Add `get_remaining_production_needs()` helper function
- Tests for edge cases (overage, zero, exact completion)

**WP02: Production-Aware Feasibility** (P2 - Core)
- Modify `check_production_feasibility()` to use remaining batches
- Add `production_aware` parameter (default True)
- Tests for remaining-based feasibility

**WP03: Production-Aware Shopping List** (P3 - Core)
- Modify shopping list to calculate needs from remaining batches
- Add `production_aware` parameter (default True)
- Tests for remaining-based shopping

**WP04: Amendment Production Validation** (P3 - Protection)
- Add validation to `modify_batch_decision()` and `drop_finished_good()`
- Clear error messages explaining why amendment blocked
- Tests for validation logic

**WP05: UI Progress Display** (P4 - Polish)
- Update planning_tab to show remaining vs total
- Add overage indicator
- Add lock icon for recipes with production

### Dependencies

```
WP01 (remaining calc) → WP02 (feasibility)
                      → WP03 (shopping)
                      → WP04 (amendment validation)
WP01-04 → WP05 (UI)
```

WP02, WP03, WP04 can be parallelized after WP01 completes.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing feasibility consumers | Low | High | Add flag with True default; test backwards compat |
| Shopping list calculation complexity | Low | Medium | Reuse existing aggregation; add remaining filter |
| Amendment validation false positives | Low | Medium | Clear error messages; allow FGs without production |

---

## Quickstart

After `/spec-kitty.tasks` generates work packages:

```bash
# Create worktree for implementation
spec-kitty implement WP01

# Run tests for remaining calculation
./run-tests.sh src/tests/planning/test_progress.py -v

# Implementation order
WP01 → WP02/WP03/WP04 (parallel) → WP05
```

---

## Post-Phase 1 Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Clearer progress display, accurate feasibility |
| II. Data Integrity | ✅ PASS | No data changes; calculation only |
| III. Future-Proof Schema | ✅ PASS | No schema changes |
| IV. TDD | ✅ PASS | Tests defined for each WP |
| V. Layered Architecture | ✅ PASS | Service-only changes |
| VII. Pragmatic Aspiration | ✅ PASS | Clean APIs for future web |

**Design approved for task generation.**
