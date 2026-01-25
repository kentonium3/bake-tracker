---
work_package_id: "WP02"
subtasks:
  - "T003"
  - "T004"
  - "T005"
title: "Decouple Planning Service"
phase: "Phase 2 - Service Decoupling"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-25T03:23:15Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Decouple Planning Service

## Objectives & Success Criteria

**Goal**: Replace direct `recipe.finished_units` access with `recipe_service.get_finished_units()` primitive in planning_service.py.

**Success Criteria**:
- [ ] No direct `recipe.finished_units` access in planning_service.py
- [ ] Planning service imports and uses `recipe_service.get_finished_units()`
- [ ] All existing tests pass
- [ ] Planning calculations work identically for base and variant recipes

**Implementation Command**:
```bash
spec-kitty implement WP02 --base WP01
```

## Context & Constraints

**Background**:
The planning service currently accesses `recipe.finished_units` directly, creating tight coupling to the Recipe model. This WP replaces that with the `get_finished_units()` primitive, which provides a clean abstraction that works identically for base and variant recipes.

**Key Pattern Change**:
```python
# BEFORE (tightly coupled):
if recipe.finished_units:
    primary_unit = recipe.finished_units[0]
    items_per_batch = primary_unit.items_per_batch

# AFTER (decoupled):
finished_units = recipe_service.get_finished_units(recipe_id, session=session)
if finished_units:
    primary_unit = finished_units[0]
    items_per_batch = primary_unit["items_per_batch"]  # NOTE: dict access, not attribute!
```

**Critical Note**: The primitive returns a list of dicts, NOT ORM objects. Use `["key"]` notation, not `.attribute` notation.

**Key Documents**:
- Spec: `kitty-specs/066-recipe-variant-yield-remediation/spec.md`
- Plan: `kitty-specs/066-recipe-variant-yield-remediation/plan.md`
- Research: `kitty-specs/066-recipe-variant-yield-remediation/research.md`

**File to Update**: `src/services/planning/planning_service.py`

## Subtasks & Detailed Guidance

### Subtask T005 – Add Import for recipe_service

**Purpose**: Import recipe_service to access the primitive.

**Location**: Top of `src/services/planning/planning_service.py`

**Steps**:
1. Find the imports section at the top of the file
2. Add import for recipe_service

**Code to Add**:
```python
from src.services import recipe_service
```

**Files**: `src/services/planning/planning_service.py` (imports section)

---

### Subtask T003 – Replace Direct Access at Lines 505-506

**Purpose**: Decouple the `_calculate_bulk_count_requirements` function from direct model access.

**Current Code** (approx. lines 500-516):
```python
for target in event.production_targets:
    recipe = session.get(Recipe, target.recipe_id)
    if recipe:
        # F056: Use FinishedUnit.items_per_batch instead of deprecated yield_quantity
        items_per_batch = 1
        if recipe.finished_units:
            primary_unit = recipe.finished_units[0]
            if primary_unit.items_per_batch and primary_unit.items_per_batch > 0:
                items_per_batch = primary_unit.items_per_batch
```

**Updated Code**:
```python
for target in event.production_targets:
    recipe = session.get(Recipe, target.recipe_id)
    if recipe:
        # F066: Use get_finished_units() primitive for decoupled yield access
        items_per_batch = 1
        finished_units = recipe_service.get_finished_units(target.recipe_id, session=session)
        if finished_units:
            primary_unit = finished_units[0]
            if primary_unit["items_per_batch"] and primary_unit["items_per_batch"] > 0:
                items_per_batch = primary_unit["items_per_batch"]
```

**Key Changes**:
1. Replace `recipe.finished_units` with `recipe_service.get_finished_units(target.recipe_id, session=session)`
2. Change attribute access (`.items_per_batch`) to dict access (`["items_per_batch"]`)
3. Update comment to reference F066

**Files**: `src/services/planning/planning_service.py` (lines ~500-516)

**Parallel**: Yes - can be done alongside T004

---

### Subtask T004 – Replace Direct Access at Lines 686-687

**Purpose**: Decouple the yield access in the legacy/fallback path.

**Current Code** (approx. lines 680-695):
```python
else:
    # Fallback: use live recipe (legacy compatibility)
    recipe = session.get(Recipe, target.recipe_id)
    if recipe:
        recipe_name = recipe.name
        # F056: Use FinishedUnit.items_per_batch if available
        yield_per_batch = 1
        if recipe.finished_units:
            primary_unit = recipe.finished_units[0]
            if primary_unit.items_per_batch and primary_unit.items_per_batch > 0:
                yield_per_batch = primary_unit.items_per_batch
```

**Updated Code**:
```python
else:
    # Fallback: use live recipe (legacy compatibility)
    recipe = session.get(Recipe, target.recipe_id)
    if recipe:
        recipe_name = recipe.name
        # F066: Use get_finished_units() primitive for decoupled yield access
        yield_per_batch = 1
        finished_units = recipe_service.get_finished_units(target.recipe_id, session=session)
        if finished_units:
            primary_unit = finished_units[0]
            if primary_unit["items_per_batch"] and primary_unit["items_per_batch"] > 0:
                yield_per_batch = primary_unit["items_per_batch"]
```

**Key Changes**:
1. Replace `recipe.finished_units` with `recipe_service.get_finished_units(target.recipe_id, session=session)`
2. Change attribute access to dict access
3. Update comment to reference F066

**Files**: `src/services/planning/planning_service.py` (lines ~680-695)

**Parallel**: Yes - can be done alongside T003

## Test Strategy

**Run Existing Tests**:
```bash
./run-tests.sh src/tests/ -v -k "planning"
```

**Verification Points**:
1. All planning-related tests pass
2. Batch calculations produce same results as before
3. No direct `recipe.finished_units` access remains in file

**Search for Remaining Direct Access**:
```bash
grep -n "\.finished_units" src/services/planning/planning_service.py
```
Should return no matches after this WP.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Dict vs attribute access confusion | Use IDE autocomplete; review carefully |
| Session not passed correctly | Always pass `session=session` to primitive |
| Performance regression | Primitive uses same query pattern; no regression expected |

## Definition of Done Checklist

- [ ] T005: Import added for recipe_service
- [ ] T003: First direct access location replaced
- [ ] T004: Second direct access location replaced
- [ ] No `recipe.finished_units` access in planning_service.py
- [ ] All existing tests pass
- [ ] Changes committed with clear message

## Review Guidance

- Verify all `recipe.finished_units` replaced with primitive call
- Verify dict access `["key"]` used, not attribute access `.key`
- Verify session is passed to primitive calls
- Verify import added at top of file
- Run tests to confirm no regressions

## Activity Log

- 2026-01-25T03:23:15Z – system – lane=planned – Prompt created.
