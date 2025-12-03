---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
title: "User Story 1 - Calculate Actual Recipe Cost"
phase: "Phase 1 - Core Feature"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "76189"
review_status: "approved"
reviewed_by: "claude"
reviewer_shell_pid: "80943"
history:
  - timestamp: "2025-12-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – User Story 1 - Calculate Actual Recipe Cost

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Implement `calculate_actual_cost()` in RecipeService that uses FIFO pantry inventory to determine accurate recipe costs.

**Success Criteria** (from spec acceptance scenarios):
1. Recipe requiring 2 cups flour with pantry at $0.10/cup (older) and $0.12/cup (newer) → uses $0.10/cup rate (FIFO)
2. Multiple ingredients → sums FIFO-based costs for all ingredients
3. Pantry quantities NOT modified (read-only operation)
4. Unit conversion works (recipe uses cups, pantry tracked in grams)

**This is the MVP** - delivers core FIFO costing capability.

## Context & Constraints

**Prerequisite Documents**:
- Constitution: `.kittify/memory/constitution.md` (FIFO Accuracy NON-NEGOTIABLE)
- Plan: `kitty-specs/005-recipe-fifo-cost/plan.md`
- Contract: `kitty-specs/005-recipe-fifo-cost/contracts/recipe_service_costing.py`
- Quickstart: `kitty-specs/005-recipe-fifo-cost/quickstart.md`

**Dependencies**:
- **WP01 must be complete** - requires `consume_fifo(dry_run=True)` capability

**Architectural Constraints**:
- RecipeService calls PantryService (downward dependency flow)
- Use existing `convert_any_units()` from unit_converter
- Use `INGREDIENT_DENSITIES` constants for density lookup
- Fail fast on uncostable ingredients (no partial results)

**Key Files**:
- `src/services/recipe_service.py` (add method after line ~412)
- `src/services/unit_converter.py` (use existing `convert_any_units()`)
- `src/utils/constants.py` (use `get_ingredient_density()`)

## Subtasks & Detailed Guidance

### Subtask T006 – Implement method shell

**Purpose**: Create the `calculate_actual_cost()` method structure.

**Steps**:
1. Add method to `RecipeService` class in `src/services/recipe_service.py`
2. Signature: `def calculate_actual_cost(self, recipe_id: int) -> Decimal:`
3. Add comprehensive docstring per contract specification
4. Initialize: `total_cost = Decimal("0.00")`

**Files**: `src/services/recipe_service.py`

**Notes**: Follow existing method patterns - use `with session_scope() as session:`.

### Subtask T007 – Load and iterate RecipeIngredients

**Purpose**: Load the recipe and iterate through its ingredients.

**Steps**:
1. Query recipe by ID with eager-loading: `joinedload(Recipe.recipe_ingredients).joinedload(RecipeIngredient.ingredient)`
2. If recipe not found, raise `RecipeNotFound`
3. Handle empty recipe: return `Decimal("0.00")` (per FR-008)
4. For each `recipe_ingredient`: extract `quantity`, `unit`, and `ingredient`

**Files**: `src/services/recipe_service.py`

**Notes**: Eager-load relationships before leaving session scope.

### Subtask T008 – Convert units and call consume_fifo

**Purpose**: For each ingredient, convert to pantry units and simulate FIFO consumption.

**Steps**:
1. Get ingredient density: `density = get_ingredient_density(ingredient.name)`
2. If density required but missing, raise `ValidationError` with descriptive message
3. Convert recipe quantity to pantry units using `convert_any_units()`
4. Call `pantry_service.consume_fifo(ingredient.slug, converted_quantity, dry_run=True)`
5. Extract `fifo_result.total_cost` and `fifo_result.shortfall`

**Files**: `src/services/recipe_service.py`

**Notes**:
- Import: `from src.services.unit_converter import convert_any_units`
- Import: `from src.utils.constants import get_ingredient_density`

### Subtask T009 – Implement fallback for shortfall

**Purpose**: When pantry is insufficient, use preferred variant pricing for the shortfall.

**Steps**:
1. If `fifo_result.shortfall > 0`:
   - Get preferred variant: `variant_service.get_preferred_variant(ingredient_id)`
   - If no variant exists, raise `IngredientNotFound`
   - Get latest purchase: `purchase_service.get_latest_purchase(variant_id)`
   - If no purchase exists, raise `ValidationError("No pricing data...")`
   - Calculate fallback cost: `shortfall * purchase.unit_cost`
2. If no shortfall, fallback cost is 0

**Files**: `src/services/recipe_service.py`

**Notes**: Import variant_service and purchase_service as needed.

### Subtask T010 – Sum costs and return Decimal

**Purpose**: Combine FIFO and fallback costs for final total.

**Steps**:
1. For each ingredient: `ingredient_cost = fifo_result.total_cost + fallback_cost`
2. Add to running total: `total_cost += ingredient_cost`
3. Return `total_cost` (Decimal)

**Files**: `src/services/recipe_service.py`

**Notes**: Maintain Decimal precision throughout.

### Subtask T011 – Implement fail-fast error handling

**Purpose**: Ensure descriptive errors for all failure cases.

**Steps**:
1. Wrap main logic in try/except
2. Re-raise specific exceptions: `RecipeNotFound`, `IngredientNotFound`
3. Wrap SQLAlchemy errors: `raise DatabaseError(...)`
4. ValidationError for: missing density, no pricing data, unit conversion failure

**Files**: `src/services/recipe_service.py`

**Notes**: Follow existing error handling patterns in the file.

### Subtask T012 – Write comprehensive tests

**Purpose**: Verify FIFO ordering, read-only behavior, and error handling.

**Steps**:
1. `test_calculate_actual_cost_uses_fifo_ordering`:
   - Setup: Recipe with 2 cups flour, pantry with 1 cup at $0.10 (older), 1 cup at $0.12 (newer)
   - Assert: Total cost = 2 * $0.10 = $0.20 (oldest consumed first)
2. `test_calculate_actual_cost_does_not_modify_pantry`:
   - Capture pantry state before, call method, compare after
3. `test_calculate_actual_cost_handles_multiple_ingredients`:
   - Setup: Recipe with flour and sugar, each with pantry
   - Assert: Total = flour_cost + sugar_cost
4. `test_calculate_actual_cost_converts_units`:
   - Setup: Recipe in cups, pantry in grams
   - Assert: Correct conversion applied
5. `test_calculate_actual_cost_raises_recipe_not_found`:
   - Call with invalid recipe_id
6. `test_calculate_actual_cost_raises_validation_error_no_variant`:
   - Ingredient with no variants

**Files**: `src/tests/test_recipe_service.py`

**Notes**: Use existing fixtures, follow existing test patterns.

## Test Strategy

**Required Tests**:
- FIFO ordering verification
- Read-only behavior (pantry unchanged)
- Multiple ingredients summation
- Unit conversion (volume ↔ weight)
- Error handling (RecipeNotFound, IngredientNotFound, ValidationError)

**Commands**:
```bash
pytest src/tests/test_recipe_service.py -v -k "actual_cost"
pytest src/tests/test_recipe_service.py -v --cov=src/services/recipe_service
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Unit conversion failures | Use existing convert_any_units with density lookup |
| Missing density data | Fail fast with descriptive ValidationError |
| FIFO logic drift | Rely on WP01's consume_fifo(dry_run=True) |
| Session management | Follow existing service patterns |

## Definition of Done Checklist

- [x] T006: Method shell implemented with signature and docstring
- [x] T007: Recipe loading with eager-loaded relationships
- [x] T008: Unit conversion and consume_fifo integration
- [x] T009: Fallback pricing for shortfall implemented
- [x] T010: Cost summation returns Decimal
- [x] T011: Fail-fast error handling complete
- [x] T012: All tests pass (10 tests in test_recipe_service.py)
- [x] Pantry quantities verified unchanged after cost calculation (test_does_not_modify_pantry)
- [x] `tasks.md` updated with completion status

## Review Guidance

**Key Acceptance Checkpoints**:
1. FIFO ordering: Oldest inventory costs used first
2. Read-only: Pantry quantities unchanged
3. Error messages: Descriptive and user-friendly
4. Decimal precision: No float rounding issues

**Spec Verification**:
- Run acceptance scenario 1: 2 cups flour, FIFO pricing
- Run acceptance scenario 2: Multiple ingredients
- Run acceptance scenario 3: Verify read-only
- Run acceptance scenario 4: Unit conversion

## Activity Log

- 2025-12-02T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-03T15:20:04Z – claude – shell_pid=75289 – lane=doing – Started implementation of calculate_actual_cost()
- 2025-12-03T15:45:00Z – claude – lane=doing – Completed implementation and all 10 tests passing
- 2025-12-03T15:26:55Z – claude – shell_pid=76189 – lane=for_review – Completed all subtasks T006-T012, all 10 tests passing
- 2025-12-03T20:35:00Z – claude – shell_pid=80943 – lane=done – APPROVED: All 10 tests pass, FIFO ordering verified, read-only behavior confirmed, shortfall fallback working, contract compliance complete
- 2025-12-03T17:37:23Z – claude – shell_pid=76189 – lane=done – Approved: All 10 tests pass, FIFO ordering verified, read-only behavior confirmed
