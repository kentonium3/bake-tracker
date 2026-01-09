---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "FinishedGood Model + UI Cost Removal"
phase: "Phase 1 - Model Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-09T18:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - FinishedGood Model + UI Cost Removal

## Objectives & Success Criteria

**Goal**: Remove `total_cost` column and all related methods from the FinishedGood model; remove cost display from the FinishedGood detail UI.

**Success Criteria**:
- FinishedGood model has no `total_cost` column definition
- No `calculate_component_cost()` method exists
- No `update_total_cost_from_components()` method exists
- `get_component_breakdown()` returns no cost-related fields
- `to_dict()` returns no cost-related fields
- UI detail view displays without cost section
- No import errors when loading the model

**Independent Test**:
```python
from src.models.finished_good import FinishedGood
fg = FinishedGood(slug="test", display_name="Test")
assert not hasattr(fg, 'total_cost') or 'total_cost' not in FinishedGood.__table__.columns
```

## Context & Constraints

**Related Documents**:
- Feature Spec: `kitty-specs/045-cost-architecture-refactor/spec.md`
- Implementation Plan: `kitty-specs/045-cost-architecture-refactor/plan.md`
- Research: `kitty-specs/045-cost-architecture-refactor/research.md`

**Architecture Constraints**:
- This is a "removal only" refactor - do not add new functionality
- Follow layered architecture: Model changes should not affect Services directly (WP03 handles services)
- No backward compatibility needed for cost fields

**Parallelization Note**: This WP can run in parallel with WP01 (FinishedUnit). Different model files with no dependencies.

## Subtasks & Detailed Guidance

### Subtask T007 - Remove `total_cost` Column

**Purpose**: Eliminate the stored cost field that causes staleness issues.

**Steps**:
1. Open `src/models/finished_good.py`
2. Locate line 76: `total_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))`
3. Delete this entire line
4. Remove the `Decimal` import if no longer needed (check other usages first)

**Files**: `src/models/finished_good.py`
**Parallel?**: Yes, with other T00x subtasks in this WP

### Subtask T008 - Remove CheckConstraint

**Purpose**: Remove the database constraint that validates the now-deleted field.

**Steps**:
1. In `src/models/finished_good.py`, locate the `__table_args__` tuple
2. Find line 106: `CheckConstraint("total_cost >= 0", name="ck_finished_good_total_cost_non_negative")`
3. Delete this CheckConstraint entry
4. Ensure the tuple syntax remains valid (check trailing commas)

**Files**: `src/models/finished_good.py`
**Parallel?**: Yes

### Subtask T009 - Remove `calculate_component_cost()` Method

**Purpose**: Remove method that calculates total cost from components - no longer needed as costs move to instances.

**Steps**:
1. In `src/models/finished_good.py`, locate lines 114-142
2. Delete the entire `calculate_component_cost()` method

**Files**: `src/models/finished_good.py`
**Parallel?**: Yes

**Code to remove**:
```python
def calculate_component_cost(self) -> Decimal:
    """
    Calculate total cost from all components in the assembly.
    ...
    """
    # Full method body from lines 114-142
```

### Subtask T010 - Remove `update_total_cost_from_components()` Method

**Purpose**: Remove method that updates the stored cost field.

**Steps**:
1. In `src/models/finished_good.py`, locate lines 144-151
2. Delete the entire `update_total_cost_from_components()` method

**Files**: `src/models/finished_good.py`
**Parallel?**: Yes

**Code to remove**:
```python
def update_total_cost_from_components(self) -> None:
    """
    Update the stored total_cost field based on current component costs.
    ...
    """
    self.total_cost = self.calculate_component_cost()
```

### Subtask T011 - Update `get_component_breakdown()` Method

**Purpose**: Remove cost fields from the component breakdown output.

**Steps**:
1. In `src/models/finished_good.py`, locate the `get_component_breakdown()` method (starts around line 153)
2. In the `component_info` dictionary initialization (around line 166-175), remove:
   - `"unit_cost": Decimal("0.0000")`
   - `"total_cost": Decimal("0.0000")`
3. In the finished_unit_component block, remove:
   - `"unit_cost": composition.finished_unit_component.unit_cost`
   - `"total_cost": composition.finished_unit_component.unit_cost * composition.component_quantity`
4. In the finished_good_component block, remove:
   - `"unit_cost": composition.finished_good_component.total_cost`
   - `"total_cost": composition.finished_good_component.total_cost * composition.component_quantity`

**Files**: `src/models/finished_good.py`
**Parallel?**: Yes

**Before** (component_info dict):
```python
component_info = {
    "composition_id": composition.id,
    "quantity": composition.component_quantity,
    "notes": composition.component_notes,
    "sort_order": composition.sort_order,
    "type": None,
    "name": None,
    "unit_cost": Decimal("0.0000"),
    "total_cost": Decimal("0.0000"),
}
```

**After**:
```python
component_info = {
    "composition_id": composition.id,
    "quantity": composition.component_quantity,
    "notes": composition.component_notes,
    "sort_order": composition.sort_order,
    "type": None,
    "name": None,
}
```

### Subtask T012 - Update `to_dict()` Method

**Purpose**: Remove cost fields from dictionary representation.

**Steps**:
1. In `src/models/finished_good.py`, locate the `to_dict()` method (starts around line 296)
2. Remove line 312: `result["total_cost"] = float(self.total_cost) if self.total_cost else 0.0`
3. Remove line 315: `result["component_cost"] = float(self.calculate_component_cost())`

**Files**: `src/models/finished_good.py`
**Parallel?**: Yes

**Before**:
```python
result["total_cost"] = float(self.total_cost) if self.total_cost else 0.0
result["component_cost"] = float(self.calculate_component_cost())
result["is_in_stock"] = self.inventory_count > 0
```

**After**:
```python
result["is_in_stock"] = self.inventory_count > 0
```

### Subtask T013 - Remove Cost Display from UI

**Purpose**: Remove cost display from the FinishedGood detail view.

**Steps**:
1. Open `src/ui/forms/finished_good_detail.py`
2. Locate line 143: `cost = self.finished_good.total_cost or 0`
3. Remove this line and any related display code (the label showing cost)
4. Locate line 426: Another reference to `total_cost`
5. Remove this line and related display code
6. Search the file for any other `total_cost` references and remove them

**Files**: `src/ui/forms/finished_good_detail.py`
**Parallel?**: Yes

**Notes**:
- Look for associated Label widgets that display the cost
- The detail view should still function, just without cost information
- May need to adjust layout if cost section leaves a gap

## Test Strategy

**No explicit tests required for this WP** (per spec, testing is in WP04).

However, verify:
1. Model file imports without error: `python -c "from src.models.finished_good import FinishedGood"`
2. UI file imports without error: `python -c "from src.ui.forms.finished_good_detail import *"`

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Service files reference removed methods | Medium | Defer to WP03; methods will be removed there |
| UI crashes without cost data | Low | Remove display code, don't leave references to missing attributes |
| Import errors from circular dependencies | Low | Test imports after changes |
| `get_component_breakdown()` consumers expect cost fields | Medium | Service updates in WP03 will handle downstream consumers |

## Definition of Done Checklist

- [ ] T007: `total_cost` column removed from model
- [ ] T008: CheckConstraint removed
- [ ] T009: `calculate_component_cost()` method removed
- [ ] T010: `update_total_cost_from_components()` method removed
- [ ] T011: `get_component_breakdown()` returns no cost fields
- [ ] T012: `to_dict()` no longer returns cost fields
- [ ] T013: UI detail view has no cost display
- [ ] Model file imports successfully
- [ ] UI file imports successfully
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Verification Points**:
1. Grep for `total_cost` in `src/models/finished_good.py` - should return 0 matches
2. Grep for `calculate_component_cost` - should return 0 matches
3. Grep for `update_total_cost_from_components` - should return 0 matches
4. Verify `to_dict()` method does not reference cost
5. Verify `get_component_breakdown()` returns no cost keys
6. UI file has no references to `total_cost`

**Note**: Service layer updates are handled in WP03. Expect some service files to still reference these model attributes until WP03 is complete.

## Activity Log

- 2026-01-09T18:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
