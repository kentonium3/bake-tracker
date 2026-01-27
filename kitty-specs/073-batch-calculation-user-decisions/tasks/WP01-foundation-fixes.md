---
work_package_id: WP01
title: Foundation Fixes
lane: "done"
dependencies: []
base_branch: main
base_commit: 1826555fcc5313254f73ce3d3eb79c1f2734b750
created_at: '2026-01-27T19:19:19.226699+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
phase: Phase 0 - Foundation
assignee: ''
agent: "claude"
shell_pid: "18855"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-27T18:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Foundation Fixes

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

Since this WP has no dependencies, start from main:

```bash
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

**Primary Objective**: Fix F072 API to return FinishedUnit-level data (instead of Recipe-level aggregation) and update BatchDecision schema to support multiple FUs from the same recipe per event.

**Success Criteria**:
1. `decompose_event_to_fu_requirements(event_id)` returns `List[FURequirement]` with FU identity preserved
2. All 22 existing F072 tests pass with updated assertions
3. BatchDecision table accepts: (event_id=1, recipe_id=1, finished_unit_id=1) AND (event_id=1, recipe_id=1, finished_unit_id=2)
4. Fresh database creation works with new constraint

---

## Context & Constraints

**Why this change is needed**: F072's current `calculate_recipe_requirements()` returns `Dict[Recipe, int]` which aggregates at recipe level. When a recipe has multiple FUs with different yields (e.g., Large Cake yield 1, Small Cake yield 4), aggregating "5 large + 10 small = 15" loses the yield context needed for batch calculation.

**Key Documents**:
- `.kittify/memory/constitution.md` - Schema change strategy (export/reset/import)
- `kitty-specs/073-batch-calculation-user-decisions/plan.md` - Full architecture
- `kitty-specs/073-batch-calculation-user-decisions/data-model.md` - API and schema changes

**Constraints**:
- F072 is not used by any production code yet (only tests) - breaking change is safe
- BatchDecision table is likely empty - no migration needed
- Follow session parameter pattern from CLAUDE.md

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add FURequirement dataclass

**Purpose**: Define the new return type for F072's decomposition function.

**Steps**:
1. Open `src/services/planning_service.py`
2. Add import: `from dataclasses import dataclass`
3. Add the dataclass after imports, before function definitions:

```python
@dataclass
class FURequirement:
    """Requirement for a single FinishedUnit from bundle decomposition."""
    finished_unit: FinishedUnit
    quantity_needed: int
    recipe: Recipe  # Convenience reference (same as finished_unit.recipe)
```

**Files**: `src/services/planning_service.py`
**Parallel?**: No - other tasks depend on this

---

### Subtask T002 – Rename calculate_recipe_requirements

**Purpose**: Rename the public function to reflect its new behavior (FU-level, not recipe-level).

**Steps**:
1. Rename `calculate_recipe_requirements` → `decompose_event_to_fu_requirements`
2. Rename `_calculate_recipe_requirements_impl` → `_decompose_event_to_fu_requirements_impl`
3. Update docstring to describe new return type:

```python
def decompose_event_to_fu_requirements(
    event_id: int,
    session: Session = None,
) -> List[FURequirement]:
    """
    Decompose event FG selections into FinishedUnit-level requirements.

    Traverses bundle hierarchies, multiplying quantities at each level.
    Returns FU-level data (not recipe-level aggregation) to preserve
    yield context for downstream batch calculation.

    Args:
        event_id: The Event to decompose
        session: Optional session for transaction sharing

    Returns:
        List of FURequirement objects, one per atomic FinishedUnit found

    Raises:
        ValidationError: If event not found or FU has no recipe
        CircularReferenceError: If bundle contains circular reference
        MaxDepthExceededError: If nesting exceeds MAX_FG_NESTING_DEPTH
    """
```

**Files**: `src/services/planning_service.py`
**Parallel?**: No - depends on T001

---

### Subtask T003 – Modify decomposition to return FU-level data

**Purpose**: Change the internal decomposition function to collect FU-level data instead of aggregating by recipe.

**Steps**:
1. Rename `_decompose_fg_to_recipes` → `_decompose_fg_to_fus`
2. Change return type from `Dict[Recipe, int]` to `List[FURequirement]`
3. Modify the atomic component handling (line ~149-162):

**Before** (aggregates by recipe):
```python
if comp.finished_unit_id is not None:
    fu = comp.finished_unit_component
    # ... validation ...
    recipe = fu.recipe
    result[recipe] = result.get(recipe, 0) + effective_qty
```

**After** (preserves FU identity):
```python
if comp.finished_unit_id is not None:
    fu = comp.finished_unit_component
    if fu is None:
        raise ValidationError([f"FinishedUnit {comp.finished_unit_id} not found"])
    if fu.recipe is None:
        raise ValidationError([f"FinishedUnit '{fu.display_name}' (id={fu.id}) has no recipe"])

    result.append(FURequirement(
        finished_unit=fu,
        quantity_needed=effective_qty,
        recipe=fu.recipe,
    ))
```

4. Change recursive merge from dict merge to list extend:

**Before**:
```python
for recipe, qty in child_result.items():
    result[recipe] = result.get(recipe, 0) + qty
```

**After**:
```python
result.extend(child_result)
```

**Files**: `src/services/planning_service.py`
**Parallel?**: No - core logic change

---

### Subtask T004 – Remove recipe-level aggregation from main function

**Purpose**: The main function should return the FU-level list directly without aggregating.

**Steps**:
1. In `_decompose_event_to_fu_requirements_impl`, change result initialization:

**Before**:
```python
result: Dict[Recipe, int] = {}
for efg in efgs:
    fg_result = _decompose_fg_to_recipes(...)
    for recipe, qty in fg_result.items():
        result[recipe] = result.get(recipe, 0) + qty
return result
```

**After**:
```python
result: List[FURequirement] = []
for efg in efgs:
    fu_requirements = _decompose_fg_to_fus(...)
    result.extend(fu_requirements)
return result
```

2. Update type hints throughout the function

**Files**: `src/services/planning_service.py`
**Parallel?**: No - depends on T003

---

### Subtask T005 – Update all 22 F072 tests

**Purpose**: Update test assertions to work with new `List[FURequirement]` return type.

**Steps**:
1. Open `src/tests/test_planning_service.py`
2. Update import statement to include `FURequirement`
3. For each test, change assertions from dict-based to list-based:

**Before (dict assertion)**:
```python
result = calculate_recipe_requirements(event.id, session=test_db)
assert recipe_a in result
assert result[recipe_a] == 24
```

**After (list assertion)**:
```python
result = decompose_event_to_fu_requirements(event.id, session=test_db)
# Find the FURequirement for our expected FU
fu_req = next((r for r in result if r.finished_unit.id == fu_a.id), None)
assert fu_req is not None
assert fu_req.quantity_needed == 24
assert fu_req.recipe.id == recipe_a.id
```

**Key test categories to update**:
- T004: Single atomic FG → verify single FURequirement returned
- T005: Bundle decomposition → verify FURequirements for each component
- T006: Recipe aggregation → **BEHAVIOR CHANGE**: now returns separate FURequirements
- T007-T008: Nested bundles → verify quantities multiply correctly
- T009: DAG → same FU appears multiple times with correct quantities
- T010: Mixed atomic/bundle → list contains all
- T011-T014: Edge cases → adapt error assertions

**Important**: T006 "recipe aggregation" test changes behavior:
- **Before**: Multiple FGs with same recipe → aggregated into single dict entry
- **After**: Multiple FGs with same recipe → separate FURequirement per FG

4. Run tests after each batch of changes: `pytest src/tests/test_planning_service.py -v`

**Files**: `src/tests/test_planning_service.py`
**Parallel?**: Yes (can proceed after T004 completes)

---

### Subtask T006 – Modify BatchDecision finished_unit_id to NOT NULL

**Purpose**: Make `finished_unit_id` required since batch decisions are now per-FU.

**Steps**:
1. Open `src/models/batch_decision.py`
2. Change the `finished_unit_id` column:

**Before**:
```python
finished_unit_id = Column(
    Integer,
    ForeignKey("finished_units.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)
```

**After**:
```python
finished_unit_id = Column(
    Integer,
    ForeignKey("finished_units.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
)
```

**Notes**:
- Change `nullable=True` → `nullable=False`
- Change `ondelete="SET NULL"` → `ondelete="CASCADE"` (can't SET NULL if NOT NULL)

**Files**: `src/models/batch_decision.py`
**Parallel?**: Yes (independent of T001-T005)

---

### Subtask T007 – Update UniqueConstraint

**Purpose**: Allow multiple batch decisions from the same recipe per event (different FUs).

**Steps**:
1. In `src/models/batch_decision.py`, find the `__table_args__` section
2. Update the UniqueConstraint:

**Before**:
```python
__table_args__ = (
    UniqueConstraint("event_id", "recipe_id", name="uq_batch_decision_event_recipe"),
    CheckConstraint("batches > 0", name="ck_batch_decision_batches_positive"),
    Index("idx_batch_decision_event", "event_id"),
    Index("idx_batch_decision_recipe", "recipe_id"),
    Index("idx_batch_decision_finished_unit", "finished_unit_id"),
)
```

**After**:
```python
__table_args__ = (
    UniqueConstraint("event_id", "finished_unit_id", name="uq_batch_decision_event_fu"),
    CheckConstraint("batches > 0", name="ck_batch_decision_batches_positive"),
    Index("idx_batch_decision_event", "event_id"),
    Index("idx_batch_decision_recipe", "recipe_id"),
    Index("idx_batch_decision_finished_unit", "finished_unit_id"),
)
```

**Files**: `src/models/batch_decision.py`
**Parallel?**: Yes (do with T006)

---

### Subtask T008 – Verify constraint changes with fresh database

**Purpose**: Ensure the schema changes work correctly.

**Steps**:
1. Check if batch_decisions table has data:
```python
# In Python shell or test
from src.services.database import session_scope
from src.models import BatchDecision
with session_scope() as session:
    count = session.query(BatchDecision).count()
    print(f"Existing batch_decisions: {count}")
```

2. If count > 0: Follow Constitution VI (export/reset/import)
3. If count == 0 (expected): Delete database and recreate

```bash
# From project root
rm bake_tracker.db  # or wherever the DB lives
python -c "from src.services.database import init_db; init_db()"
```

4. Test the new constraint allows multiple FUs from same recipe:
```python
# Quick validation
from src.services.database import session_scope
from src.models import BatchDecision, Event, Recipe, FinishedUnit

with session_scope() as session:
    # Get existing test data or create minimal
    event = session.query(Event).first()
    recipe = session.query(Recipe).first()
    fus = session.query(FinishedUnit).filter(FinishedUnit.recipe_id == recipe.id).limit(2).all()

    if event and recipe and len(fus) >= 2:
        # This should now work (same recipe, different FUs)
        bd1 = BatchDecision(event_id=event.id, recipe_id=recipe.id, finished_unit_id=fus[0].id, batches=3)
        bd2 = BatchDecision(event_id=event.id, recipe_id=recipe.id, finished_unit_id=fus[1].id, batches=5)
        session.add_all([bd1, bd2])
        session.commit()
        print("SUCCESS: Multiple FUs from same recipe allowed")
```

**Files**: Database file, `src/services/database.py` (init)
**Parallel?**: No - final validation step

---

## Test Strategy

**Required Tests** (all in `src/tests/test_planning_service.py`):
- All 22 existing F072 tests must pass with updated assertions
- No new tests required for WP01 (tests are being updated, not added)

**Run Command**:
```bash
./run-tests.sh src/tests/test_planning_service.py -v
```

**Expected Outcome**: 22 tests pass

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing batch_decisions data | Low | Check count before schema change; table is likely empty |
| Test assertion changes miss edge cases | Medium | Carefully review each test's original intent |
| Import cycles from new dataclass | Low | FURequirement only references existing models |
| Session detachment issues | Low | FURequirement holds references to ORM objects - test with detached objects |

---

## Definition of Done Checklist

- [ ] FURequirement dataclass added to planning_service.py
- [ ] Function renamed to decompose_event_to_fu_requirements
- [ ] Decomposition returns List[FURequirement] (not Dict[Recipe, int])
- [ ] All 22 F072 tests updated and passing
- [ ] BatchDecision.finished_unit_id is NOT NULL
- [ ] UniqueConstraint changed to (event_id, finished_unit_id)
- [ ] Fresh database creation works
- [ ] Manual verification: multiple FUs from same recipe per event allowed

---

## Review Guidance

**Key Checkpoints**:
1. **API Change**: Verify new function signature and return type in planning_service.py
2. **Test Coverage**: All 22 tests must pass - run full test suite
3. **Schema Change**: Verify BatchDecision model has correct constraints
4. **No Regressions**: Ensure bundle decomposition logic (cycle detection, depth limit) still works

**Questions for Review**:
- Does T006 test (recipe aggregation) correctly reflect the new behavior?
- Are there any tests that should now have multiple FURequirements where before they had one dict entry?

---

## Activity Log

- 2026-01-27T18:00:00Z – system – lane=planned – Prompt created.
- 2026-01-27T19:29:41Z – claude – shell_pid=16747 – lane=for_review – All 8 tasks (T001-T008) complete. 22 tests passing.
- 2026-01-27T19:29:50Z – claude – shell_pid=18855 – lane=doing – Started review via workflow command
- 2026-01-27T19:30:26Z – claude – shell_pid=18855 – lane=done – Review passed: All 8 subtasks complete, 22 tests passing, API correctly returns List[FURequirement], BatchDecision schema updated with (event_id, finished_unit_id) constraint
