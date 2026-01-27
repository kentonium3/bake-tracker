---
work_package_id: WP02
title: Batch Calculation Service
lane: "doing"
dependencies:
- WP01
base_branch: 073-batch-calculation-user-decisions-WP01
base_commit: 7eedb5fedcdc079a25704e92d054b4d18c98bc46
created_at: '2026-01-27T19:30:59.193507+00:00'
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
phase: Phase 1 - Core Service
assignee: ''
agent: ''
shell_pid: "19203"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-27T18:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Batch Calculation Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

This WP depends on WP01. Start from the WP01 branch:

```bash
spec-kitty implement WP02
```

---

## Objectives & Success Criteria

**Primary Objective**: Implement batch calculation logic that uses F072's FU-level output to generate floor/ceil batch options for each FinishedUnit.

**Success Criteria**:
1. `calculate_batch_options_for_fu(fu, quantity)` returns correct floor/ceil options
2. `calculate_batch_options(event_id)` returns `List[BatchOptionsResult]` for all FUs in event
3. Shortfall flags correctly identify when floor option produces less than needed
4. Exact match detection works when quantity is exactly divisible by yield
5. Both YieldMode.DISCRETE_COUNT and YieldMode.BATCH_PORTION handled correctly
6. Edge cases handled: zero yield, zero quantity, floor=0

---

## Context & Constraints

**Why this is needed**: Users need to see their batch options with clear trade-offs. The core calculation determines how many batches are needed and flags shortfalls.

**Key Documents**:
- `kitty-specs/073-batch-calculation-user-decisions/plan.md` - Data flow diagram
- `kitty-specs/073-batch-calculation-user-decisions/quickstart.md` - Code examples
- `kitty-specs/073-batch-calculation-user-decisions/data-model.md` - Dataclass definitions

**Constraints**:
- Must use WP01's `decompose_event_to_fu_requirements()` output
- Follow session parameter pattern from CLAUDE.md
- 1x recipe scaling only (no half-batch or double-batch)

---

## Subtasks & Detailed Guidance

### Subtask T009 – Add BatchOption dataclass

**Purpose**: Define the output structure for a single batch option.

**Steps**:
1. Open `src/services/planning_service.py`
2. Add the dataclass after `FURequirement` (added in WP01):

```python
@dataclass
class BatchOption:
    """One batch option for user selection."""
    batches: int           # Number of batches to make
    total_yield: int       # batches × yield_per_batch
    quantity_needed: int   # From FURequirement.quantity_needed
    difference: int        # total_yield - quantity_needed
    is_shortfall: bool     # difference < 0
    is_exact_match: bool   # difference == 0
    yield_per_batch: int   # From FinishedUnit (for display)
```

**Files**: `src/services/planning_service.py`
**Parallel?**: Yes (with T010)

---

### Subtask T010 – Add BatchOptionsResult dataclass

**Purpose**: Define the container for all options for one FinishedUnit.

**Steps**:
1. In `src/services/planning_service.py`, add after `BatchOption`:

```python
@dataclass
class BatchOptionsResult:
    """Batch options for one FinishedUnit."""
    finished_unit_id: int
    finished_unit_name: str
    recipe_id: int
    recipe_name: str
    quantity_needed: int
    yield_per_batch: int
    yield_mode: str        # "discrete_count" or "batch_portion"
    item_unit: str         # "cookie", "cake", etc.
    options: List[BatchOption]
```

**Files**: `src/services/planning_service.py`
**Parallel?**: Yes (with T009)

---

### Subtask T011 – Implement calculate_batch_options_for_fu()

**Purpose**: Core calculation logic for a single FinishedUnit.

**Steps**:
1. Add import at top: `import math`
2. Add the function after the dataclasses:

```python
def calculate_batch_options_for_fu(
    finished_unit: FinishedUnit,
    quantity_needed: int,
) -> List[BatchOption]:
    """
    Calculate floor/ceil batch options for a single FinishedUnit.

    Args:
        finished_unit: The FU to calculate for
        quantity_needed: How many items/portions needed

    Returns:
        List of 0-2 BatchOptions:
        - Empty if quantity_needed <= 0 or invalid yield
        - One option if floor == ceil (exact division)
        - Two options otherwise (floor may shortfall, ceil meets/exceeds)
    """
    if quantity_needed <= 0:
        return []

    # Use existing method to get raw batch count
    raw_batches = finished_unit.calculate_batches_needed(quantity_needed)

    if raw_batches <= 0:
        return []

    # Determine yield per batch based on mode
    yield_per_batch = finished_unit.items_per_batch or 1
    if finished_unit.yield_mode == YieldMode.BATCH_PORTION:
        yield_per_batch = 1  # One batch = one portion

    options = []

    # Floor option (may shortfall)
    floor_batches = math.floor(raw_batches)
    if floor_batches > 0:
        floor_yield = floor_batches * yield_per_batch
        floor_diff = floor_yield - quantity_needed
        options.append(BatchOption(
            batches=floor_batches,
            total_yield=floor_yield,
            quantity_needed=quantity_needed,
            difference=floor_diff,
            is_shortfall=floor_diff < 0,
            is_exact_match=floor_diff == 0,
            yield_per_batch=yield_per_batch,
        ))

    # Ceil option (if different from floor)
    ceil_batches = math.ceil(raw_batches)
    if ceil_batches != floor_batches:
        ceil_yield = ceil_batches * yield_per_batch
        ceil_diff = ceil_yield - quantity_needed
        options.append(BatchOption(
            batches=ceil_batches,
            total_yield=ceil_yield,
            quantity_needed=quantity_needed,
            difference=ceil_diff,
            is_shortfall=False,  # Ceil never shortfalls
            is_exact_match=ceil_diff == 0,
            yield_per_batch=yield_per_batch,
        ))

    return options
```

3. Add import for YieldMode if not present: `from src.models.finished_unit import YieldMode`

**Files**: `src/services/planning_service.py`
**Parallel?**: No - core logic

---

### Subtask T012 – Implement calculate_batch_options()

**Purpose**: Event-level function that uses F072 output to calculate options for all FUs.

**Steps**:
1. Add the function (follows session pattern):

```python
def calculate_batch_options(
    event_id: int,
    session: Session = None,
) -> List[BatchOptionsResult]:
    """
    Calculate batch options for all FUs in an event.

    Uses decompose_event_to_fu_requirements() to get FU-level data,
    then calculates floor/ceil options for each.

    Args:
        event_id: The Event to calculate for
        session: Optional session for transaction sharing

    Returns:
        List of BatchOptionsResult, one per FURequirement from F072

    Raises:
        ValidationError: If event not found
    """
    if session is not None:
        return _calculate_batch_options_impl(event_id, session)
    with session_scope() as session:
        return _calculate_batch_options_impl(event_id, session)


def _calculate_batch_options_impl(
    event_id: int,
    session: Session,
) -> List[BatchOptionsResult]:
    """Implementation of calculate_batch_options."""
    # Get FU-level requirements from F072
    fu_requirements = decompose_event_to_fu_requirements(event_id, session=session)

    results = []
    for fu_req in fu_requirements:
        fu = fu_req.finished_unit
        recipe = fu_req.recipe

        # Calculate options for this FU
        options = calculate_batch_options_for_fu(fu, fu_req.quantity_needed)

        # Determine yield per batch for display
        yield_per_batch = fu.items_per_batch or 1
        if fu.yield_mode == YieldMode.BATCH_PORTION:
            yield_per_batch = 1

        results.append(BatchOptionsResult(
            finished_unit_id=fu.id,
            finished_unit_name=fu.display_name,
            recipe_id=recipe.id,
            recipe_name=recipe.name,
            quantity_needed=fu_req.quantity_needed,
            yield_per_batch=yield_per_batch,
            yield_mode=fu.yield_mode.value if fu.yield_mode else "discrete_count",
            item_unit=fu.item_unit or "item",
            options=options,
        ))

    return results
```

**Files**: `src/services/planning_service.py`
**Parallel?**: No - depends on T011

---

### Subtask T013 – Handle edge cases

**Purpose**: Ensure robust handling of unusual inputs.

**Edge cases to handle**:

1. **Zero quantity needed**: Return empty options list
2. **Zero or missing yield**: Handle `items_per_batch = None` or `= 0`
3. **Floor = 0**: When floor_batches rounds to 0, only return ceil option
4. **BATCH_PORTION mode**: yield_per_batch = 1 (one batch = one portion)
5. **Exact division**: Only one option returned when quantity exactly divisible

**Steps**:
1. Review `calculate_batch_options_for_fu()` for edge case handling
2. Add guards for zero/None yield:

```python
# In calculate_batch_options_for_fu, after getting yield_per_batch:
if yield_per_batch <= 0:
    # Invalid yield configuration - return empty
    return []
```

3. Verify floor=0 case is handled (already skipped in implementation)

**Files**: `src/services/planning_service.py`
**Parallel?**: No - refinement of T011

---

### Subtask T014 – Write tests

**Purpose**: Comprehensive test coverage for batch calculation.

**Steps**:
1. Create `src/tests/test_batch_calculation.py`
2. Write tests covering:

```python
"""Tests for batch calculation service (F073)."""
import pytest
from src.services.planning_service import (
    calculate_batch_options_for_fu,
    calculate_batch_options,
    BatchOption,
    BatchOptionsResult,
)
from src.models.finished_unit import FinishedUnit, YieldMode


class TestCalculateBatchOptionsForFU:
    """Tests for calculate_batch_options_for_fu()."""

    def test_exact_division_returns_one_option(self, test_db):
        """When quantity exactly divisible, only one option returned."""
        # FU with yield 24/batch, need 48 → exactly 2 batches
        fu = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
        )
        options = calculate_batch_options_for_fu(fu, 48)
        assert len(options) == 1
        assert options[0].batches == 2
        assert options[0].is_exact_match is True
        assert options[0].is_shortfall is False

    def test_floor_ceil_options(self, test_db):
        """Non-exact division returns floor and ceil options."""
        # FU with yield 24/batch, need 50 → floor=2 (48), ceil=3 (72)
        fu = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
        )
        options = calculate_batch_options_for_fu(fu, 50)
        assert len(options) == 2

        floor_opt = options[0]
        assert floor_opt.batches == 2
        assert floor_opt.total_yield == 48
        assert floor_opt.difference == -2
        assert floor_opt.is_shortfall is True
        assert floor_opt.is_exact_match is False

        ceil_opt = options[1]
        assert ceil_opt.batches == 3
        assert ceil_opt.total_yield == 72
        assert ceil_opt.difference == 22
        assert ceil_opt.is_shortfall is False
        assert ceil_opt.is_exact_match is False

    def test_zero_quantity_returns_empty(self, test_db):
        """Zero quantity needed returns empty list."""
        fu = FinishedUnit(...)
        options = calculate_batch_options_for_fu(fu, 0)
        assert options == []

    def test_batch_portion_mode(self, test_db):
        """BATCH_PORTION mode treats each batch as one portion."""
        fu = FinishedUnit(
            slug="cake",
            display_name="Cake",
            yield_mode=YieldMode.BATCH_PORTION,
            items_per_batch=None,  # Not used for BATCH_PORTION
            item_unit="cake",
        )
        options = calculate_batch_options_for_fu(fu, 3)
        assert len(options) == 1  # Exact: 3 batches = 3 cakes
        assert options[0].batches == 3
        assert options[0].yield_per_batch == 1

    def test_floor_zero_only_returns_ceil(self, test_db):
        """When floor rounds to 0, only ceil option returned."""
        fu = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
        )
        # Need 5 cookies, floor=0, ceil=1
        options = calculate_batch_options_for_fu(fu, 5)
        assert len(options) == 1
        assert options[0].batches == 1
        assert options[0].is_shortfall is False


class TestCalculateBatchOptions:
    """Tests for calculate_batch_options() event-level function."""

    def test_returns_results_for_all_fus(self, test_db):
        """Returns BatchOptionsResult for each FU in event."""
        # Setup: Event with 2 different FUs
        # ... test implementation
        pass

    def test_uses_f072_decomposition(self, test_db):
        """Verifies F072 decomposition is used for bundle expansion."""
        # Setup: Event with bundle containing atomic FUs
        # ... test implementation
        pass
```

3. Run tests: `./run-tests.sh src/tests/test_batch_calculation.py -v`

**Files**: `src/tests/test_batch_calculation.py` (NEW)
**Parallel?**: Yes (write alongside T011-T013)

---

## Test Strategy

**Required Tests** (in `src/tests/test_batch_calculation.py`):
- Exact division (one option, is_exact_match=True)
- Non-exact division (floor shortfall, ceil surplus)
- Zero quantity (empty result)
- BATCH_PORTION mode (yield=1)
- Floor=0 case (only ceil returned)
- Event-level function returns all FUs
- Integration with F072 decomposition

**Run Command**:
```bash
./run-tests.sh src/tests/test_batch_calculation.py -v
```

**Expected Outcome**: All tests pass, >70% coverage for new functions

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| BATCH_PORTION calculation differs from DISCRETE_COUNT | Medium | Test both modes explicitly |
| Rounding edge cases (quantity exactly divisible) | Medium | Include exact match tests |
| F072 returns detached objects | Low | Pass session through |
| Zero yield configuration | Low | Add guard clause |

---

## Definition of Done Checklist

- [ ] BatchOption dataclass added
- [ ] BatchOptionsResult dataclass added
- [ ] calculate_batch_options_for_fu() implemented
- [ ] calculate_batch_options() implemented
- [ ] Edge cases handled (zero yield, zero quantity, floor=0)
- [ ] BATCH_PORTION mode tested
- [ ] DISCRETE_COUNT mode tested
- [ ] All new tests passing
- [ ] >70% coverage for new code

---

## Review Guidance

**Key Checkpoints**:
1. **Calculation correctness**: Verify floor/ceil math is correct
2. **Edge cases**: Zero quantity, zero yield, floor=0
3. **Yield modes**: Both DISCRETE_COUNT and BATCH_PORTION work
4. **Session management**: Session passed through to F072

**Questions for Review**:
- Does the calculation match user expectations for batch options?
- Are shortfall flags intuitive (floor may shortfall, ceil never does)?

---

## Activity Log

- 2026-01-27T18:00:00Z – system – lane=planned – Prompt created.
