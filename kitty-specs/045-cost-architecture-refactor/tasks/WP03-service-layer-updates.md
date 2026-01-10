---
work_package_id: "WP03"
subtasks:
  - "T014"
  - "T015"
  - "T016"
title: "Service Layer Cost Reference Updates"
phase: "Phase 2 - Service Layer"
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

# Work Package Prompt: WP03 - Service Layer Cost Reference Updates

## Objectives & Success Criteria

**Goal**: Update finished_unit_service.py and finished_good_service.py to remove all references to the now-deleted stored cost fields (`unit_cost`, `total_cost`).

**Success Criteria**:
- No service file references `FinishedUnit.unit_cost` or `FinishedGood.total_cost`
- No service methods attempt to set or get stored cost values
- Services compile and run without AttributeError
- UI tabs that consume these services still function (without cost data)

**Independent Test**:
```python
from src.services.finished_unit_service import FinishedUnitService
from src.services.finished_good_service import FinishedGoodService
# Services should import without error
```

## Context & Constraints

**Related Documents**:
- Feature Spec: `kitty-specs/045-cost-architecture-refactor/spec.md`
- Implementation Plan: `kitty-specs/045-cost-architecture-refactor/plan.md`
- Research: `kitty-specs/045-cost-architecture-refactor/research.md`

**Architecture Constraints**:
- This is a "removal only" refactor - do not add new functionality
- Remove cost calculation methods entirely (F046+ will reimplement on instances)
- Services must remain functional for non-cost operations

**Dependencies**:
- **MUST wait for WP01 and WP02 to complete** before starting this WP
- Model changes must be in place before service changes

## Subtasks & Detailed Guidance

### Subtask T014 - Update finished_unit_service.py

**Purpose**: Remove all references to `unit_cost` and cost calculation methods.

**Steps**:
1. Open `src/services/finished_unit_service.py`
2. Search for all occurrences of `unit_cost`
3. For each occurrence, determine the appropriate action:
   - If it's accessing `FinishedUnit.unit_cost`: Remove the access
   - If it's a method that calculates/updates cost: Remove the method
   - If it's a return value: Remove from return dict or set to None/omit

**Specific Lines to Address** (from research.md):
- **Line 587**: `fifo_cost = FinishedUnitService._calculate_fifo_unit_cost(unit)` - Remove this call and related logic
- **Line 743**: `purchase_cost = FinishedUnitService._get_inventory_item_unit_cost(...)` - Remove this call
- **Line 811**: `unit_cost = Decimal(str(purchase.unit_cost))` - This references Purchase.unit_cost which is DIFFERENT and should remain
- **Line 1037**: `return FinishedUnitService.calculate_unit_cost(finished_unit_id)` - Remove this method if it returns stored cost

**Methods to Potentially Remove**:
- `_calculate_fifo_unit_cost()` - Private FIFO cost calculator
- `_get_inventory_item_unit_cost()` - Gets cost from inventory
- `calculate_unit_cost()` - Public cost calculation method

**Important Distinction**:
- `Purchase.unit_cost` and `InventoryItem.unit_cost` are DIFFERENT entities - NOT in scope for removal
- Only remove references to `FinishedUnit.unit_cost`

**Strategy**:
```bash
grep -n "\.unit_cost" src/services/finished_unit_service.py
```
Review each match and determine if it's FinishedUnit.unit_cost (remove) or other entity (keep).

**Files**: `src/services/finished_unit_service.py`
**Parallel?**: Yes, with T015

### Subtask T015 - Update finished_good_service.py

**Purpose**: Remove all references to `total_cost` and cost calculation methods.

**Steps**:
1. Open `src/services/finished_good_service.py`
2. Search for all occurrences of `total_cost`
3. For each occurrence, determine the appropriate action:
   - If it's accessing `FinishedGood.total_cost`: Remove the access
   - If it's setting `finished_good.total_cost = ...`: Remove the assignment
   - If it's in return values: Remove from return dict or omit

**Specific Lines to Address** (from research.md):
- **Line 277**: `finished_good.total_cost = total_cost_with_packaging` - Remove this assignment
- **Line 1131**: `return component.unit_cost if component else Decimal("0.0000")` - This may reference FinishedUnit.unit_cost - review context
- **Line 1134**: `return component.total_cost if component else Decimal("0.0000")` - Remove if referencing FinishedGood.total_cost
- **Lines 1200, 1218**: Cost references in breakdown methods - Remove cost fields from output
- **Lines 1275-1276**: `"unit_cost"` and `"total_cost"` in output dicts - Remove these keys
- **Lines 1294-1295**: More cost fields in output - Remove
- **Lines 1339, 1389, 1396**: Assembly cost calculations - Remove
- **Lines 1405, 1408, 1410**: Pricing/margin calculations based on cost - Remove or refactor
- **Lines 1479, 1502**: Additional cost references - Remove

**High-Impact Areas**:
1. Assembly cost calculations - Remove entire calculation blocks
2. Pricing suggestions - May need to remove or return placeholder values
3. Component breakdowns - Remove cost fields from output dicts

**Strategy**:
```bash
grep -n "total_cost\|\.unit_cost" src/services/finished_good_service.py
```

**Files**: `src/services/finished_good_service.py`
**Parallel?**: Yes, with T014

### Subtask T016 - Verify UI Tabs Don't Reference Removed Methods

**Purpose**: Ensure UI components that call service methods still function.

**Steps**:
1. Check `src/ui/finished_units_tab.py` - Verify no calls to removed service methods
2. Check `src/ui/finished_goods_tab.py` - Verify no calls to removed service methods
3. Check `src/ui/recipes_tab.py` - Confirm it uses dynamic recipe cost (not stored cost)

**Expected Outcome**:
- Per research.md, `finished_units_tab.py` only has a comment about costs (line 88) - no actual cost column
- `recipes_tab.py` shows calculated costs from recipe_service (dynamic) - this is fine
- Main risk is if any tab calls a removed service method

**Verification**:
```bash
grep -n "calculate_unit_cost\|calculate_fifo\|calculate_component_cost" src/ui/*.py
```

If any matches found, either:
- Remove the call entirely, or
- Replace with a placeholder/null return

**Files**: `src/ui/finished_units_tab.py`, `src/ui/finished_goods_tab.py`, `src/ui/recipes_tab.py`
**Parallel?**: No, depends on T014 and T015

## Test Strategy

**No explicit tests required for this WP** (per spec, testing is in WP04).

However, verify services import without error:
```bash
python -c "from src.services.finished_unit_service import FinishedUnitService"
python -c "from src.services.finished_good_service import FinishedGoodService"
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Removing methods that are called elsewhere | High | Grep for method names across entire codebase before removing |
| Breaking service contracts (return values changed) | High | Document which return values change; update consumers |
| Confusing FinishedUnit.unit_cost with Purchase.unit_cost | Medium | Carefully review each occurrence; Purchase costs stay |
| Pricing calculations that depend on cost | Medium | May need to remove pricing suggestion features entirely |

## Definition of Done Checklist

- [ ] T014: finished_unit_service.py has no FinishedUnit.unit_cost references
- [ ] T015: finished_good_service.py has no FinishedGood.total_cost references
- [ ] T016: UI tabs function without calling removed methods
- [ ] Services import without error
- [ ] Grep for removed method names returns 0 matches in services
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Verification Points**:
1. `grep -r "\.unit_cost" src/services/finished_unit_service.py` - Should only match Purchase/InventoryItem, not FinishedUnit
2. `grep -r "\.total_cost" src/services/finished_good_service.py` - Should return 0 matches
3. Verify no AttributeError when services access model attributes
4. Check that service methods that previously returned cost data now omit it cleanly

**Service Method Changes to Verify**:
- Any method returning a dict should not include `unit_cost` or `total_cost` keys for FinishedUnit/FinishedGood
- Removed private methods should have no callers remaining

## Activity Log

- 2026-01-09T18:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-09T23:33:16Z – claude – lane=doing – Started implementation
- 2026-01-09T23:39:49Z – claude – lane=for_review – Implementation complete - all subtasks done
- 2026-01-10T01:27:45Z – claude – lane=done – Code review approved: No FinishedUnit.unit_cost or FinishedGood.total_cost in services, imports clean
