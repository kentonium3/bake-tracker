---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "FinishedUnit Model + UI Cost Removal"
phase: "Phase 1 - Model Layer"
lane: "done"
assignee: ""
agent: "claude"
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

# Work Package Prompt: WP01 - FinishedUnit Model + UI Cost Removal

## Objectives & Success Criteria

**Goal**: Remove `unit_cost` column and all related methods from the FinishedUnit model; remove cost display from the FinishedUnit detail UI.

**Success Criteria**:
- FinishedUnit model has no `unit_cost` column definition
- No `calculate_recipe_cost_per_item()` method exists
- No `update_unit_cost_from_recipe()` method exists
- `to_dict()` returns no cost-related fields
- UI detail view displays without cost section
- No import errors when loading the model

**Independent Test**:
```python
from src.models.finished_unit import FinishedUnit
fu = FinishedUnit(slug="test", display_name="Test", recipe_id=1, yield_mode=YieldMode.DISCRETE_COUNT)
assert not hasattr(fu, 'unit_cost') or 'unit_cost' not in FinishedUnit.__table__.columns
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

**Parallelization Note**: This WP can run in parallel with WP02 (FinishedGood). Different model files with no dependencies.

## Subtasks & Detailed Guidance

### Subtask T001 - Remove `unit_cost` Column

**Purpose**: Eliminate the stored cost field that causes staleness issues.

**Steps**:
1. Open `src/models/finished_unit.py`
2. Locate line 98: `unit_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))`
3. Delete this entire line
4. Remove the `Decimal` import if no longer needed (check other usages first)

**Files**: `src/models/finished_unit.py`
**Parallel?**: Yes, with other T00x subtasks in this WP

### Subtask T002 - Remove CheckConstraint

**Purpose**: Remove the database constraint that validates the now-deleted field.

**Steps**:
1. In `src/models/finished_unit.py`, locate the `__table_args__` tuple
2. Find line 133: `CheckConstraint("unit_cost >= 0", name="ck_finished_unit_unit_cost_non_negative")`
3. Delete this CheckConstraint entry
4. Ensure the tuple syntax remains valid (check trailing commas)

**Files**: `src/models/finished_unit.py`
**Parallel?**: Yes

### Subtask T003 - Remove `calculate_recipe_cost_per_item()` Method

**Purpose**: Remove method that calculates cost from recipe - no longer needed as costs move to instances.

**Steps**:
1. In `src/models/finished_unit.py`, locate lines 171-196
2. Delete the entire `calculate_recipe_cost_per_item()` method
3. Verify no other model methods call this (should be safe to remove)

**Files**: `src/models/finished_unit.py`
**Parallel?**: Yes

**Code to remove**:
```python
def calculate_recipe_cost_per_item(self) -> Decimal:
    """
    Calculate cost per finished unit item based on current recipe cost.
    ...
    """
    # Full method body from lines 171-196
```

### Subtask T004 - Remove `update_unit_cost_from_recipe()` Method

**Purpose**: Remove method that updates the stored cost field.

**Steps**:
1. In `src/models/finished_unit.py`, locate lines 198-205
2. Delete the entire `update_unit_cost_from_recipe()` method

**Files**: `src/models/finished_unit.py`
**Parallel?**: Yes

**Code to remove**:
```python
def update_unit_cost_from_recipe(self) -> None:
    """
    Update the stored unit_cost field based on current recipe cost.
    ...
    """
    self.unit_cost = self.calculate_recipe_cost_per_item()
```

### Subtask T005 - Update `to_dict()` Method

**Purpose**: Remove cost fields from dictionary representation.

**Steps**:
1. In `src/models/finished_unit.py`, locate the `to_dict()` method (starts around line 237)
2. Remove lines 253-254: `result["unit_cost"] = float(self.unit_cost) if self.unit_cost else 0.0`
3. Remove line 257: `result["recipe_cost_per_item"] = float(self.calculate_recipe_cost_per_item())`

**Files**: `src/models/finished_unit.py`
**Parallel?**: Yes

**Before**:
```python
result["unit_cost"] = float(self.unit_cost) if self.unit_cost else 0.0
result["batch_percentage"] = float(self.batch_percentage) if self.batch_percentage else None
result["recipe_cost_per_item"] = float(self.calculate_recipe_cost_per_item())
```

**After**:
```python
result["batch_percentage"] = float(self.batch_percentage) if self.batch_percentage else None
```

### Subtask T006 - Remove Cost Display from UI

**Purpose**: Remove cost display from the FinishedUnit detail view.

**Steps**:
1. Open `src/ui/forms/finished_unit_detail.py`
2. Locate line 167: `cost = self.finished_unit.unit_cost or 0`
3. Remove this line and any related display code (the label showing cost)
4. Locate line 324: Another reference to `unit_cost`
5. Remove this line and related display code
6. Search the file for any other `unit_cost` references and remove them

**Files**: `src/ui/forms/finished_unit_detail.py`
**Parallel?**: Yes

**Notes**:
- Look for associated Label widgets that display the cost
- The detail view should still function, just without cost information
- May need to adjust layout if cost section leaves a gap

## Test Strategy

**No explicit tests required for this WP** (per spec, testing is in WP04).

However, verify:
1. Model file imports without error: `python -c "from src.models.finished_unit import FinishedUnit"`
2. UI file imports without error: `python -c "from src.ui.forms.finished_unit_detail import *"`

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Service files reference removed methods | Medium | Defer to WP03; methods will be removed there |
| UI crashes without cost data | Low | Remove display code, don't leave references to missing attributes |
| Import errors from circular dependencies | Low | Test imports after changes |

## Definition of Done Checklist

- [ ] T001: `unit_cost` column removed from model
- [ ] T002: CheckConstraint removed
- [ ] T003: `calculate_recipe_cost_per_item()` method removed
- [ ] T004: `update_unit_cost_from_recipe()` method removed
- [ ] T005: `to_dict()` no longer returns cost fields
- [ ] T006: UI detail view has no cost display
- [ ] Model file imports successfully
- [ ] UI file imports successfully
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Verification Points**:
1. Grep for `unit_cost` in `src/models/finished_unit.py` - should return 0 matches
2. Grep for `calculate_recipe_cost_per_item` - should return 0 matches
3. Grep for `update_unit_cost_from_recipe` - should return 0 matches
4. Verify `to_dict()` method does not reference cost
5. UI file has no references to `unit_cost`

**Note**: Service layer updates are handled in WP03. Expect some service files to still reference these model attributes until WP03 is complete.

## Activity Log

- 2026-01-09T18:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-09T23:11:42Z – claude – lane=doing – Started implementation
- 2026-01-09T23:28:30Z – claude – lane=for_review – Implementation complete - all subtasks done
- 2026-01-10T01:27:40Z – claude – lane=done – Code review approved: All verification points pass - no unit_cost references in model, UI imports clean
