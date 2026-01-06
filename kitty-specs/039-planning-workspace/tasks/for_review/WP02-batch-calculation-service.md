---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
title: "Batch Calculation Service"
phase: "Phase 2 - Services"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "57624"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T03:09:20Z"
    lane: "planned"
    agent: "claude"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Batch Calculation Service

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Implement batch count calculation that ALWAYS rounds up (never short)
- Calculate waste percentage for each recipe
- Explode bundle requirements to unit quantities
- Aggregate FinishedUnits by recipe

**Success Metrics (from spec):**
- SC-003: Batch calculations NEVER result in production shortfall - total yield always >= requirement (100% accuracy)
- SC-007: Waste percentage is calculated correctly

---

## Context & Constraints

### Reference Documents
- **Contract**: `kitty-specs/039-planning-workspace/contracts/planning_service.py` - RecipeBatchResult DTO
- **Quickstart**: `kitty-specs/039-planning-workspace/quickstart.md` - Batch calculation algorithm
- **Research**: `kitty-specs/039-planning-workspace/research.md` - No RecipeYieldOption; use single yield

### Key Constraints
- Use `math.ceil()` for batch calculation - NEVER round down
- Recipe has single `yield_quantity` (no yield options to optimize)
- Session management: all functions accept optional `session` parameter
- Parallelizable with WP03, WP04, WP05

### Architectural Notes
- Located in `src/services/planning/` module
- No business logic in models - all calculation here
- Follow existing service patterns

---

## Subtasks & Detailed Guidance

### Subtask T007 - Create planning/__init__.py

- **Purpose**: Initialize the planning services module
- **Steps**:
  1. Create directory: `src/services/planning/`
  2. Create `__init__.py` with exports:
     ```python
     from .batch_calculation import (
         calculate_batches,
         calculate_waste,
         explode_bundle_requirements,
         aggregate_by_recipe,
         RecipeBatchResult,
     )
     ```
  3. Add docstring describing module purpose
- **Files**: `src/services/planning/__init__.py`
- **Parallel?**: Yes - can be created while other modules start

### Subtask T008 - Create batch_calculation.py

- **Purpose**: Core batch calculation functions
- **Steps**:
  1. Create `src/services/planning/batch_calculation.py`
  2. Import `math`, dataclasses, typing
  3. Define `RecipeBatchResult` dataclass (per contract):
     ```python
     @dataclass
     class RecipeBatchResult:
         recipe_id: int
         recipe_name: str
         units_needed: int
         batches: int
         yield_per_batch: int
         total_yield: int
         waste_units: int
         waste_percent: float
     ```
  4. Implement `calculate_batches(units_needed: int, yield_per_batch: int) -> int`:
     ```python
     def calculate_batches(units_needed: int, yield_per_batch: int) -> int:
         """Calculate batches needed. Always rounds UP to prevent shortfall."""
         import math
         return math.ceil(units_needed / yield_per_batch)
     ```
- **Files**: `src/services/planning/batch_calculation.py`
- **Parallel?**: Yes

### Subtask T009 - Implement waste calculation

- **Purpose**: Calculate waste units and percentage (FR-014)
- **Steps**:
  1. Add `calculate_waste()` function:
     ```python
     def calculate_waste(units_needed: int, batches: int, yield_per_batch: int) -> tuple[int, float]:
         """Calculate waste units and percentage.

         Returns:
             (waste_units, waste_percent)
         """
         total_yield = batches * yield_per_batch
         waste_units = total_yield - units_needed
         waste_percent = (waste_units / total_yield) * 100 if total_yield > 0 else 0.0
         return waste_units, waste_percent
     ```
  2. Add helper `create_batch_result()` that combines calculation + waste
- **Files**: `src/services/planning/batch_calculation.py`
- **Parallel?**: Yes
- **Notes**: Waste percent should never exceed 100% (impossible if ceil is used correctly)

### Subtask T010 - Implement bundle explosion logic

- **Purpose**: Explode FinishedGood requirements to FinishedUnit quantities (FR-009)
- **Steps**:
  1. Add function:
     ```python
     def explode_bundle_requirements(
         finished_good_id: int,
         bundle_quantity: int,
         session: Session
     ) -> Dict[int, int]:
         """Explode bundle to component FinishedUnit quantities.

         Args:
             finished_good_id: The bundle (FinishedGood) ID
             bundle_quantity: How many bundles needed
             session: Database session

         Returns:
             Dict mapping finished_unit_id -> total quantity needed
         """
     ```
  2. Query FinishedGood.components (Composition records)
  3. For each Composition with finished_unit_id:
     - quantity = composition.component_quantity * bundle_quantity
  4. For nested FinishedGoods (composition.finished_good_id), recursively explode
  5. Aggregate same finished_unit_id values
- **Files**: `src/services/planning/batch_calculation.py`
- **Parallel?**: Yes
- **Notes**: Watch for circular references in nested bundles

### Subtask T011 - Implement recipe aggregation

- **Purpose**: Group FinishedUnits by their linked recipe (FR-010)
- **Steps**:
  1. Add function:
     ```python
     def aggregate_by_recipe(
         unit_quantities: Dict[int, int],
         session: Session
     ) -> List[RecipeBatchResult]:
         """Aggregate FinishedUnit quantities by recipe.

         Args:
             unit_quantities: Dict of finished_unit_id -> quantity needed
             session: Database session

         Returns:
             List of RecipeBatchResult for each recipe
         """
     ```
  2. For each finished_unit_id, get FinishedUnit.recipe_id
  3. Group quantities by recipe_id (sum if multiple units use same recipe)
  4. For each recipe: calculate_batches(), calculate_waste()
  5. Return list of RecipeBatchResult
- **Files**: `src/services/planning/batch_calculation.py`
- **Parallel?**: Yes
- **Notes**: Handle case where FinishedUnit has no recipe (error)

### Subtask T012 - Write unit tests

- **Purpose**: Verify all batch calculation functions
- **Steps**:
  1. Create `src/tests/services/planning/test_batch_calculation.py`
  2. Test cases for `calculate_batches()`:
     - Exact fit: 48 needed, 48 yield = 1 batch
     - Round up: 49 needed, 48 yield = 2 batches
     - Large: 300 needed, 48 yield = 7 batches (ceil(300/48)=7)
     - Edge: 1 needed, 48 yield = 1 batch
  3. Test cases for `calculate_waste()`:
     - Zero waste: 48 needed, 1 batch, 48 yield = (0, 0.0%)
     - Some waste: 49 needed, 2 batches, 48 yield = (47, 49.0%)
  4. Test cases for `explode_bundle_requirements()`:
     - Simple bundle with 2 components
     - Nested bundle (bundle containing bundle)
  5. Test cases for `aggregate_by_recipe()`:
     - Multiple units, same recipe
     - Multiple units, different recipes
- **Files**: `src/tests/services/planning/test_batch_calculation.py`
- **Parallel?**: Yes

---

## Test Strategy

**Unit Tests Required:**
- `src/tests/services/planning/test_batch_calculation.py`

**Run with:**
```bash
pytest src/tests/services/planning/test_batch_calculation.py -v
```

**Critical Test Cases:**
- NEVER produce shortfall (total_yield >= units_needed always)
- Waste calculation is accurate
- Bundle explosion handles nesting

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Rounding errors cause shortfall | Use math.ceil exclusively; test edge cases |
| Circular bundle references | Add recursion depth limit or cycle detection |
| Division by zero | Guard against zero yield_per_batch |

---

## Definition of Done Checklist

- [ ] planning/__init__.py created with exports
- [ ] batch_calculation.py implements all functions
- [ ] RecipeBatchResult dataclass matches contract
- [ ] calculate_batches ALWAYS rounds up
- [ ] Waste calculation is accurate
- [ ] Bundle explosion handles nesting
- [ ] Recipe aggregation works correctly
- [ ] All unit tests pass
- [ ] >70% test coverage on module
- [ ] `tasks.md` updated with status change

---

## Review Guidance

- Verify math.ceil is used (never floor/round)
- Check total_yield >= units_needed in all test cases
- Validate nested bundle handling
- Ensure session parameter pattern is followed

---

## Activity Log

- 2026-01-06T03:09:20Z - claude - lane=planned - Prompt created.
- 2026-01-06T12:58:15Z – claude – shell_pid=57624 – lane=doing – Started implementation
- 2026-01-06T13:04:15Z – claude – shell_pid=57624 – lane=for_review – Moved to for_review
