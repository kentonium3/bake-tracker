---
work_package_id: WP03
title: Decouple Batch Calculation
lane: "doing"
dependencies: [WP01]
base_branch: 066-recipe-variant-yield-remediation-WP02
base_commit: 28cd0870a1811b7da946a57f976a8cd47feaf102
created_at: '2026-01-25T03:53:12.631064+00:00'
subtasks:
- T006
- T007
phase: Phase 2 - Service Decoupling
assignee: ''
agent: ''
shell_pid: "26101"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-25T03:23:15Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Decouple Batch Calculation

## Objectives & Success Criteria

**Goal**: Replace direct `recipe.finished_units` access with `recipe_service.get_finished_units()` primitive in batch_calculation.py.

**Success Criteria**:
- [ ] No direct `recipe.finished_units` access in batch_calculation.py
- [ ] Batch calculation imports and uses `recipe_service.get_finished_units()`
- [ ] All existing tests pass
- [ ] Batch calculations work identically for base and variant recipes

**Implementation Command**:
```bash
# Step 1: Create worktree based on WP01 branch
spec-kitty implement WP03 --base WP01

# Step 2: Change to worktree directory
cd .worktrees/066-recipe-variant-yield-remediation-WP03
```

**Note**: The `--base WP01` flag creates the worktree from WP01's branch, not from main. This is required because WP01 changes are not yet merged to main.

## Context & Constraints

**Background**:
The batch calculation module currently accesses `recipe.finished_units` directly. This WP replaces that with the `get_finished_units()` primitive for consistency with the planning service decoupling.

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
    items_per_batch = primary_unit["items_per_batch"]  # NOTE: dict access!
```

**Critical Note**: The primitive returns a list of dicts, NOT ORM objects.

**Key Documents**:
- Spec: `kitty-specs/066-recipe-variant-yield-remediation/spec.md`
- Plan: `kitty-specs/066-recipe-variant-yield-remediation/plan.md`

**File to Update**: `src/services/planning/batch_calculation.py`

## Subtasks & Detailed Guidance

### Subtask T007 – Add Import for recipe_service

**Purpose**: Import recipe_service to access the primitive.

**Location**: Top of `src/services/planning/batch_calculation.py`

**Steps**:
1. Find the imports section at the top of the file
2. Add import for recipe_service

**Code to Add**:
```python
from src.services import recipe_service
```

**Files**: `src/services/planning/batch_calculation.py` (imports section)

---

### Subtask T006 – Replace Direct Access at Lines 296-297

**Purpose**: Decouple the batch calculation from direct model access.

**Current Code** (approx. lines 290-305):
```python
# Cache recipe info on first encounter
recipe = session.get(Recipe, recipe_id)
if recipe:
    # F056: Use FinishedUnit.items_per_batch instead of deprecated yield_quantity
    items_per_batch = 1
    if recipe.finished_units:
        primary_unit = recipe.finished_units[0]
        if primary_unit.items_per_batch and primary_unit.items_per_batch > 0:
            items_per_batch = primary_unit.items_per_batch
    recipe_info[recipe_id] = (
        recipe.name,
        items_per_batch,
    )
```

**Updated Code**:
```python
# Cache recipe info on first encounter
recipe = session.get(Recipe, recipe_id)
if recipe:
    # F066: Use get_finished_units() primitive for decoupled yield access
    items_per_batch = 1
    finished_units = recipe_service.get_finished_units(recipe_id, session=session)
    if finished_units:
        primary_unit = finished_units[0]
        if primary_unit["items_per_batch"] and primary_unit["items_per_batch"] > 0:
            items_per_batch = primary_unit["items_per_batch"]
    recipe_info[recipe_id] = (
        recipe.name,
        items_per_batch,
    )
```

**Key Changes**:
1. Replace `recipe.finished_units` with `recipe_service.get_finished_units(recipe_id, session=session)`
2. Change attribute access (`.items_per_batch`) to dict access (`["items_per_batch"]`)
3. Update comment to reference F066

**Files**: `src/services/planning/batch_calculation.py` (lines ~290-305)

## Test Strategy

**Run Existing Tests**:
```bash
./run-tests.sh src/tests/ -v -k "batch"
```

**Verification Points**:
1. All batch calculation tests pass
2. Calculations produce same results as before
3. No direct `recipe.finished_units` access remains

**Search for Remaining Direct Access**:
```bash
grep -n "\.finished_units" src/services/planning/batch_calculation.py
```
Should return no matches after this WP.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Dict vs attribute access confusion | Use IDE autocomplete; review carefully |
| Session not passed correctly | Always pass `session=session` to primitive |

## Definition of Done Checklist

- [ ] T007: Import added for recipe_service
- [ ] T006: Direct access location replaced with primitive call
- [ ] No `recipe.finished_units` access in batch_calculation.py
- [ ] All existing tests pass
- [ ] Changes committed with clear message

## Review Guidance

- Verify all `recipe.finished_units` replaced with primitive call
- Verify dict access `["key"]` used, not attribute access `.key`
- Verify session is passed to primitive call
- Verify import added at top of file
- Run tests to confirm no regressions

## Activity Log

- 2026-01-25T03:23:15Z – system – lane=planned – Prompt created.
