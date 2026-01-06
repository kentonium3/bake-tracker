# Quickstart: Planning Workspace (F039)

**Feature Branch**: `039-planning-workspace`
**Date**: 2026-01-05

## Overview

This quickstart guides implementation of the Planning Workspace feature, which provides automatic batch calculation to prevent underproduction during holiday baking.

---

## Prerequisites

Ensure these are in place before starting:

1. **F037 (Recipe Redesign) merged** - Recipes have yield information
2. **F038 (UI Mode Restructure) merged** - PLAN mode exists in navigation
3. **Virtual environment active** with all dependencies
4. **Tests passing** - Run `pytest src/tests -v` to confirm baseline

---

## Implementation Order

### Phase 1: Model Changes (Foundation)

**Files to modify/create:**
1. `src/models/event.py` - Add `OutputMode` enum and `output_mode` field
2. `src/models/production_plan_snapshot.py` - New model (create file)
3. `src/models/__init__.py` - Export new model

**Verification:**
```bash
# After model changes, verify migrations work
python -c "from src.models import ProductionPlanSnapshot, Event; print('Models OK')"
```

### Phase 2: Service Layer (Core Logic)

**Directory to create:** `src/services/planning/`

**Files to create:**
1. `__init__.py` - Export facade
2. `planning_service.py` - Facade with public API
3. `batch_calculation.py` - Batch count calculations
4. `shopping_list.py` - Shopping list generation
5. `feasibility.py` - Production/assembly feasibility
6. `progress.py` - Progress tracking

**Test files to create:** `src/tests/services/planning/`
- `test_batch_calculation.py`
- `test_shopping_list.py`
- `test_feasibility.py`
- `test_progress.py`

**Verification:**
```bash
pytest src/tests/services/planning/ -v
```

### Phase 3: UI Layer (User Interface)

**Directory to create:** `src/ui/planning/`

**Files to create:**
1. `__init__.py`
2. `planning_workspace.py` - Main container with wizard layout
3. `phase_sidebar.py` - Navigation sidebar with status indicators
4. `calculate_view.py` - Calculate phase UI
5. `shop_view.py` - Shopping phase UI
6. `produce_view.py` - Production phase UI
7. `assemble_view.py` - Assembly phase UI

**Integration:**
- Wire up in main navigation (PLAN mode from F038)
- Connect to PlanningService facade

---

## Key Patterns to Follow

### Session Management

```python
# Every service function MUST follow this pattern
def my_function(..., session=None):
    if session is not None:
        return _my_function_impl(..., session)
    with session_scope() as session:
        return _my_function_impl(..., session)
```

### Batch Calculation Algorithm

```python
def calculate_batches(units_needed: int, yield_per_batch: int) -> int:
    """Calculate batches needed. Always rounds UP to prevent shortfall."""
    import math
    return math.ceil(units_needed / yield_per_batch)
```

### Staleness Check

```python
def is_stale(plan, session) -> bool:
    """Check if any input is newer than plan calculation."""
    calculated_at = plan.calculated_at

    # Check event
    if plan.event.last_modified > calculated_at:
        return True

    # Check targets
    for target in plan.event.assembly_targets:
        if target.updated_at > calculated_at:
            return True

    # Check recipes (use last_modified, not updated_at)
    # ... etc

    return False
```

---

## Testing Strategy

### Unit Tests (Required)

Each service module needs tests covering:
1. **Happy path** - Normal operation
2. **Edge cases** - Zero quantities, single item, large numbers
3. **Error cases** - Missing data, invalid inputs

Example test structure:
```python
class TestBatchCalculation:
    def test_calculate_batches_exact_fit(self):
        """48 cookies needed, 48 per batch = 1 batch."""
        assert calculate_batches(48, 48) == 1

    def test_calculate_batches_rounds_up(self):
        """49 cookies needed, 48 per batch = 2 batches (never short)."""
        assert calculate_batches(49, 48) == 2

    def test_calculate_batches_large_quantity(self):
        """300 cookies needed, 48 per batch = 7 batches."""
        assert calculate_batches(300, 48) == 7  # ceil(300/48) = 7
```

### Integration Tests (Recommended)

Test full workflow:
1. Create event with bundle requirements
2. Calculate plan
3. Verify batch counts correct
4. Verify shopping list accurate
5. Simulate production progress
6. Check assembly feasibility updates

---

## UI Guidelines

### Wizard Layout

```
+------------------+----------------------------------+
|   SIDEBAR        |         MAIN CONTENT             |
+------------------+----------------------------------+
| [*] Calculate    |                                  |
| [ ] Shop         |   << Phase-specific content >>   |
| [ ] Produce      |                                  |
| [ ] Assemble     |                                  |
+------------------+----------------------------------+
```

### Status Indicators

- Green checkmark: Phase complete
- Yellow circle: In progress / partial
- Gray circle: Not started
- Red warning: Issue detected

### Warning Display

When prerequisites incomplete:
```
+------------------------------------------+
| ! Production incomplete                   |
|   3/7 brownie batches done               |
|   [Continue anyway] [Go to Produce]      |
+------------------------------------------+
```

---

## Common Pitfalls

### 1. Session Detachment

**Wrong:**
```python
with session_scope() as session:
    event = get_event(event_id)
another_function()  # Creates new session
event.name = "New"  # DETACHED! Changes lost
```

**Right:**
```python
with session_scope() as session:
    event = get_event(event_id, session=session)
    another_function(session=session)
    event.name = "New"  # Still attached, changes persist
```

### 2. Timestamp Field Names

Some models use non-standard names:
- Event: `last_modified` (not `updated_at`)
- Recipe: `last_modified` (not `updated_at`)
- Others: `updated_at` (standard)

### 3. Rounding Direction

**Always round UP** for batch calculations:
```python
import math
batches = math.ceil(needed / yield)  # Never short
```

### 4. Waste Calculation

```python
waste_units = (batches * yield_per_batch) - units_needed
waste_percent = (waste_units / (batches * yield_per_batch)) * 100
```

---

## Parallelization Opportunities

These tasks can be developed in parallel after models are defined:

| Task | Dependencies | Can Parallelize With |
|------|--------------|---------------------|
| batch_calculation.py | Models only | shopping_list.py, feasibility.py |
| shopping_list.py | Models only | batch_calculation.py, progress.py |
| feasibility.py | Models only | batch_calculation.py, progress.py |
| progress.py | Models only | All other service modules |
| calculate_view.py | Services complete | shop_view.py, produce_view.py |
| shop_view.py | Services complete | calculate_view.py, assemble_view.py |
| produce_view.py | Services complete | shop_view.py, assemble_view.py |
| assemble_view.py | Services complete | All other view modules |

---

## Verification Checklist

Before marking implementation complete:

- [ ] All service tests pass with >70% coverage
- [ ] UI displays correctly in all phases
- [ ] Batch calculation never produces shortfall
- [ ] Shopping list aggregates correctly
- [ ] Staleness detection works
- [ ] Progress bars update dynamically
- [ ] Warnings display for incomplete prerequisites
- [ ] Plan persists across sessions
- [ ] Export/import cycle preserves plan data
