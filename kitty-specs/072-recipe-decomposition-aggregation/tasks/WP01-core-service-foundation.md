---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Core Service Foundation"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "98326"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: []
history:
  - timestamp: "2026-01-27T16:30:47Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Core Service Foundation

## Important: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - this is the starting work package.

---

## Objectives & Success Criteria

Create the `planning_service.py` module with the core recipe decomposition functionality:

1. **Module Creation**: New `src/services/planning_service.py` with proper imports and boilerplate
2. **Recursive Decomposition**: `_decompose_fg_to_recipes()` function with cycle detection
3. **Public API**: `calculate_recipe_requirements(event_id, session=None)` returning `Dict[Recipe, int]`
4. **Unit Tests**: Basic tests for atomic FGs, bundle decomposition, and recipe aggregation

**Success Metrics**:
- All 6 subtask tests pass
- Service follows session parameter pattern from CLAUDE.md
- No import cycles introduced

---

## Context & Constraints

### Reference Documents
- **Spec**: `kitty-specs/072-recipe-decomposition-aggregation/spec.md`
- **Plan**: `kitty-specs/072-recipe-decomposition-aggregation/plan.md`
- **Research**: `kitty-specs/072-recipe-decomposition-aggregation/research.md`
- **Constitution**: `.kittify/memory/constitution.md`
- **Session Pattern**: CLAUDE.md Session Management section

### Key Patterns to Follow

**Session Parameter Pattern** (from planning_snapshot_service.py):
```python
def calculate_recipe_requirements(
    event_id: int,
    session: Session = None,
) -> Dict[Recipe, int]:
    if session is not None:
        return _calculate_recipe_requirements_impl(event_id, session)
    with session_scope() as session:
        return _calculate_recipe_requirements_impl(event_id, session)
```

**Cycle Detection Pattern** (from event_service.py get_required_recipes):
```python
# Path-based detection (allows DAG, catches true cycles)
if fg_id in _path:
    raise CircularReferenceError(fg_id, list(_path))
_path.add(fg_id)
try:
    # ... work ...
finally:
    _path.discard(fg_id)
```

### Imports to Reuse
From `src/services/event_service.py`:
- `CircularReferenceError`
- `MaxDepthExceededError`
- `MAX_FG_NESTING_DEPTH`

From `src/services/database.py`:
- `session_scope`

### Models Used (Read-Only)
- `Event` - validate event exists
- `EventFinishedGood` - get FG selections with quantities
- `FinishedGood` - bundle with `components` relationship
- `Composition` - `component_quantity`, `finished_unit_id`, `finished_good_id`
- `FinishedUnit` - has `recipe` relationship
- `Recipe` - output keys

---

## Subtasks & Detailed Guidance

### Subtask T001 - Create planning_service.py module with imports and boilerplate

**Purpose**: Establish the service file structure following project conventions.

**Steps**:
1. Create `src/services/planning_service.py`
2. Add module docstring explaining F072 purpose
3. Add imports:
   ```python
   from typing import Dict, Optional, Set
   from sqlalchemy.orm import Session
   from src.services.database import session_scope
   from src.services.event_service import (
       CircularReferenceError,
       MaxDepthExceededError,
       MAX_FG_NESTING_DEPTH,
   )
   from src.models import (
       Event,
       EventFinishedGood,
       FinishedGood,
       FinishedUnit,
       Recipe,
   )
   ```
4. Add any F072-specific exception class if needed (e.g., `PlanningServiceError`)

**Files**:
- `src/services/planning_service.py` (new file, ~30 lines for boilerplate)

**Parallel?**: No - must complete before T002, T003

**Notes**:
- Import Recipe from models, not by ID
- Follow alphabetical import ordering per project convention

---

### Subtask T002 - Implement _decompose_fg_to_recipes() recursive function

**Purpose**: Core algorithm that recursively traverses bundle hierarchy with quantity tracking.

**Steps**:
1. Implement the internal recursive function:
   ```python
   def _decompose_fg_to_recipes(
       fg_id: int,
       multiplier: int,
       session: Session,
       _path: Set[int],
       _depth: int,
   ) -> Dict[Recipe, int]:
   ```

2. Add depth limit check:
   ```python
   if _depth > MAX_FG_NESTING_DEPTH:
       raise MaxDepthExceededError(_depth, MAX_FG_NESTING_DEPTH)
   ```

3. Add cycle detection (path-based):
   ```python
   if fg_id in _path:
       raise CircularReferenceError(fg_id, list(_path))
   _path.add(fg_id)
   ```

4. Query FinishedGood with components:
   ```python
   fg = session.query(FinishedGood).filter(FinishedGood.id == fg_id).first()
   if fg is None:
       raise ValidationError([f"FinishedGood {fg_id} not found"])
   ```

5. Initialize result dict and traverse components:
   ```python
   result: Dict[Recipe, int] = {}
   for comp in fg.components:
       effective_qty = int(comp.component_quantity * multiplier)

       if effective_qty <= 0:
           continue  # Skip zero-quantity components

       if comp.finished_unit_id is not None:
           # Atomic: get recipe from FinishedUnit
           fu = comp.finished_unit_component
           if fu and fu.recipe:
               recipe = fu.recipe
               result[recipe] = result.get(recipe, 0) + effective_qty
           else:
               raise ValidationError([f"FinishedUnit {fu.id} has no recipe"])

       elif comp.finished_good_id is not None:
           # Nested bundle: recurse
           child_result = _decompose_fg_to_recipes(
               comp.finished_good_id,
               effective_qty,
               session,
               _path,
               _depth + 1,
           )
           for recipe, qty in child_result.items():
               result[recipe] = result.get(recipe, 0) + qty
   ```

6. Clean up path and return:
   ```python
   _path.discard(fg_id)
   return result
   ```

**Files**:
- `src/services/planning_service.py` (~60 lines for this function)

**Parallel?**: No - must complete before T003

**Notes**:
- Use `int()` for component_quantity since it's stored as float but we need integer units
- The `finished_unit_component` relationship is eager-loaded per model definition
- Use `try/finally` for reliable path cleanup

---

### Subtask T003 - Implement calculate_recipe_requirements() public API

**Purpose**: Public entry point that queries EventFinishedGoods and aggregates results.

**Steps**:
1. Implement public function with session pattern:
   ```python
   def calculate_recipe_requirements(
       event_id: int,
       session: Session = None,
   ) -> Dict[Recipe, int]:
       """
       Calculate aggregated recipe requirements for an event.

       Args:
           event_id: The Event to calculate requirements for
           session: Optional session for transaction sharing

       Returns:
           Dictionary mapping Recipe objects to total quantities needed

       Raises:
           ValidationError: If event not found or FG has no recipe
           CircularReferenceError: If bundle contains circular reference
           MaxDepthExceededError: If nesting exceeds limit
       """
       if session is not None:
           return _calculate_recipe_requirements_impl(event_id, session)
       with session_scope() as session:
           return _calculate_recipe_requirements_impl(event_id, session)
   ```

2. Implement the internal implementation:
   ```python
   def _calculate_recipe_requirements_impl(
       event_id: int,
       session: Session,
   ) -> Dict[Recipe, int]:
       # Validate event exists
       event = session.query(Event).filter(Event.id == event_id).first()
       if event is None:
           raise ValidationError([f"Event {event_id} not found"])

       # Query EventFinishedGoods for this event
       efgs = session.query(EventFinishedGood).filter(
           EventFinishedGood.event_id == event_id
       ).all()

       # Handle empty event
       if not efgs:
           return {}

       # Aggregate across all FG selections
       result: Dict[Recipe, int] = {}
       for efg in efgs:
           fg_result = _decompose_fg_to_recipes(
               efg.finished_good_id,
               efg.quantity,
               session,
               set(),  # Fresh path for each top-level FG
               0,      # Start at depth 0
           )
           for recipe, qty in fg_result.items():
               result[recipe] = result.get(recipe, 0) + qty

       return result
   ```

**Files**:
- `src/services/planning_service.py` (~40 lines for public API + impl)

**Parallel?**: No - depends on T002

**Notes**:
- Import ValidationError from wherever it's defined in the codebase
- Each top-level FG starts with a fresh `_path` set (DAG support)

---

### Subtask T004 - Write unit tests for single atomic FG

**Purpose**: Verify basic functionality with the simplest case.

**Steps**:
1. Create test file `src/tests/test_planning_service.py`
2. Set up test fixtures:
   - Create a Recipe
   - Create a FinishedUnit linked to that Recipe
   - Create a FinishedGood with one FinishedUnit component
   - Create an Event
   - Create an EventFinishedGood linking them with quantity

3. Write test:
   ```python
   def test_single_atomic_fg_returns_correct_recipe_quantity(session):
       """
       Given an event with a single atomic FG (quantity 24)
       When recipe requirements are calculated
       Then the result contains one recipe with quantity 24
       """
       # Setup fixtures...

       result = calculate_recipe_requirements(event.id, session=session)

       assert len(result) == 1
       assert recipe in result
       assert result[recipe] == 24
   ```

**Files**:
- `src/tests/test_planning_service.py` (new file, ~50 lines for this test + fixtures)

**Parallel?**: Yes - after T001-T003 complete

**Notes**:
- Use pytest fixtures following existing test patterns
- Match acceptance scenario 1 from spec.md

---

### Subtask T005 - Write unit tests for single bundle decomposition

**Purpose**: Verify bundle decomposition with quantity multiplication.

**Steps**:
1. Add test fixtures for bundle:
   - Create 2 Recipes
   - Create 2 FinishedUnits (one per recipe)
   - Create a FinishedGood (bundle) containing 2 units of each FinishedUnit
   - Create Event and EventFinishedGood with quantity 10

2. Write test:
   ```python
   def test_bundle_decomposes_with_multiplied_quantities(session):
       """
       Given an event with a bundle FG (quantity 10) containing 2 atomic items each
       When recipe requirements are calculated
       Then the result shows 20 units needed for each component's recipe
       """
       # Setup: bundle with 2 of each FinishedUnit, event quantity 10
       # Expected: each recipe needs 10 * 2 = 20 units

       result = calculate_recipe_requirements(event.id, session=session)

       assert len(result) == 2
       assert result[recipe1] == 20
       assert result[recipe2] == 20
   ```

**Files**:
- `src/tests/test_planning_service.py` (~50 lines for this test)

**Parallel?**: Yes - after T001-T003 complete

**Notes**:
- Match acceptance scenario 2 from spec.md

---

### Subtask T006 - Write unit tests for recipe aggregation (multiple FGs same recipe)

**Purpose**: Verify that quantities are summed when multiple FGs use the same recipe.

**Steps**:
1. Add test fixtures:
   - Create 1 Recipe
   - Create 2 FinishedUnits both linked to the same Recipe
   - Create 2 FinishedGoods (bundles), each containing different FinishedUnits but same recipe
   - Create Event with both FGs selected

2. Write test:
   ```python
   def test_recipe_quantities_aggregated_across_multiple_fgs(session):
       """
       Given an event with multiple FGs that share the same recipe
       When recipe requirements are calculated
       Then the quantities are summed for that recipe
       """
       # Setup: 2 FGs both requiring same recipe
       # FG1: 10 units, FG2: 15 units
       # Expected: recipe needs 25 units total

       result = calculate_recipe_requirements(event.id, session=session)

       assert len(result) == 1
       assert result[shared_recipe] == 25
   ```

**Files**:
- `src/tests/test_planning_service.py` (~50 lines for this test)

**Parallel?**: Yes - after T001-T003 complete

**Notes**:
- Match acceptance scenario 3 from spec.md

---

## Test Strategy

**Test File**: `src/tests/test_planning_service.py`

**Run Tests**:
```bash
./run-tests.sh src/tests/test_planning_service.py -v
```

**Fixture Strategy**:
- Use pytest fixtures with `session` scope where possible
- Create factory functions for complex fixtures (bundles, nested structures)
- Each test should be independent (no shared state)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Import cycles with models | Use late imports if needed |
| ValidationError location unclear | Search codebase: `grep -r "class ValidationError" src/` |
| component_quantity is float | Cast to int explicitly |
| Session detachment | Follow CLAUDE.md session patterns strictly |

---

## Definition of Done Checklist

- [ ] `src/services/planning_service.py` created with proper structure
- [ ] `_decompose_fg_to_recipes()` implements recursive decomposition
- [ ] `calculate_recipe_requirements()` follows session parameter pattern
- [ ] Test for single atomic FG passes
- [ ] Test for bundle decomposition passes
- [ ] Test for recipe aggregation passes
- [ ] All imports resolve without cycles
- [ ] Code follows project conventions (formatting, docstrings)

---

## Review Guidance

**Reviewers should verify**:
1. Session parameter pattern matches CLAUDE.md exactly
2. Cycle detection uses path-based approach (not global visited set)
3. Depth limiting uses MAX_FG_NESTING_DEPTH constant
4. All three acceptance scenarios from spec.md are covered
5. No database writes (read-only operation)

---

## Activity Log

- 2026-01-27T16:30:47Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
- 2026-01-27T16:34:25Z – claude – shell_pid=96187 – lane=doing – Started implementation via workflow command
- 2026-01-27T16:44:47Z – claude – shell_pid=96187 – lane=for_review – Ready for review: Implemented planning_service.py with calculate_recipe_requirements(), 7 tests passing (atomic FG, bundle decomposition, recipe aggregation)
- 2026-01-27T16:46:05Z – claude – shell_pid=98326 – lane=doing – Started review via workflow command
- 2026-01-27T16:47:38Z – claude – shell_pid=98326 – lane=done – Review passed: Session pattern correct, path-based cycle detection, all 7 tests pass covering atomic FG, bundle decomposition, and recipe aggregation scenarios
