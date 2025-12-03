---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "User Story 2 - Calculate Estimated Recipe Cost"
phase: "Phase 1 - Core Feature"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "82419"
review_status: "approved"
reviewed_by: "claude"
reviewer_shell_pid: "84323"
history:
  - timestamp: "2025-12-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – User Story 2 - Calculate Estimated Recipe Cost

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

**Objective**: Implement `calculate_estimated_cost()` in RecipeService that uses preferred variant pricing regardless of pantry state.

**Success Criteria** (from spec acceptance scenarios):
1. Ingredient with preferred variant → uses preferred variant's most recent purchase price
2. Ingredient with no preferred variant → falls back to any available variant's price
3. Multiple ingredients → returns total based on preferred variant pricing

**Use Case**: Planning/shopping - estimate costs before purchasing ingredients.

## Context & Constraints

**Prerequisite Documents**:
- Plan: `kitty-specs/005-recipe-fifo-cost/plan.md`
- Contract: `kitty-specs/005-recipe-fifo-cost/contracts/recipe_service_costing.py`
- Quickstart: `kitty-specs/005-recipe-fifo-cost/quickstart.md`

**Dependencies**:
- **WP01 should be complete** - shares service patterns
- Can proceed in parallel with WP02 after WP01

**Architectural Constraints**:
- Ignores pantry inventory entirely
- Uses preferred variant → any variant fallback
- Uses most recent purchase for pricing
- Same fail-fast error handling as WP02

**Key Files**:
- `src/services/recipe_service.py` (add method after `calculate_actual_cost`)
- `src/services/variant_service.py` (preferred variant lookup)
- `src/services/purchase_service.py` (latest purchase price)

## Subtasks & Detailed Guidance

### Subtask T013 – Implement method shell

**Purpose**: Create the `calculate_estimated_cost()` method structure.

**Steps**:
1. Add method to `RecipeService` after `calculate_actual_cost()`
2. Signature: `def calculate_estimated_cost(self, recipe_id: int) -> Decimal:`
3. Add docstring per contract specification
4. Initialize: `total_cost = Decimal("0.00")`

**Files**: `src/services/recipe_service.py`

**Notes**: Mirror structure of `calculate_actual_cost()`.

### Subtask T014 – Get preferred variant for each ingredient

**Purpose**: Look up the preferred variant, falling back to any variant if none preferred.

**Steps**:
1. For each `recipe_ingredient`, get its `ingredient`
2. Call `variant_service.get_preferred_variant(ingredient.id)`
3. If no preferred variant, call `variant_service.get_any_variant(ingredient.id)`
4. If no variant exists at all, raise `IngredientNotFound(f"No variants for {ingredient.name}")`

**Files**: `src/services/recipe_service.py`

**Notes**: Check if these methods exist in variant_service; implement if needed.

### Subtask T015 – Get most recent purchase price

**Purpose**: Get the latest purchase to determine current pricing.

**Steps**:
1. Call `purchase_service.get_latest_purchase(variant.id)`
2. If no purchase history, raise `ValidationError(f"No pricing data for {variant.name}")`
3. Extract `purchase.unit_cost` for pricing

**Files**: `src/services/recipe_service.py`

**Notes**: Check if this method exists in purchase_service; implement if needed.

### Subtask T016 – Convert units and calculate cost

**Purpose**: Convert recipe units to purchase units and calculate ingredient cost.

**Steps**:
1. Get purchase unit from variant or purchase record
2. Convert recipe quantity to purchase units using `convert_any_units()`
3. If conversion fails (missing density), raise `ValidationError`
4. Calculate: `ingredient_cost = converted_quantity * purchase.unit_cost`
5. Add to total: `total_cost += ingredient_cost`

**Files**: `src/services/recipe_service.py`

**Notes**: Use same unit conversion pattern as WP02.

### Subtask T017 – Write tests for estimated cost

**Purpose**: Verify preferred variant logic and fallback behavior.

**Steps**:
1. `test_calculate_estimated_cost_uses_preferred_variant`:
   - Setup: Ingredient with preferred variant (is_preferred=True)
   - Assert: Uses that variant's latest purchase price
2. `test_calculate_estimated_cost_falls_back_to_any_variant`:
   - Setup: Ingredient with no preferred variant set
   - Assert: Uses any available variant's price
3. `test_calculate_estimated_cost_handles_multiple_ingredients`:
   - Setup: Recipe with multiple ingredients
   - Assert: Total = sum of all ingredient costs
4. `test_calculate_estimated_cost_ignores_pantry`:
   - Setup: Recipe with pantry inventory at different prices
   - Assert: Uses variant pricing, not pantry pricing
5. `test_calculate_estimated_cost_raises_validation_error_no_purchase`:
   - Variant with no purchase history

**Files**: `src/tests/test_recipe_service.py`

**Notes**: Follow existing test patterns.

## Test Strategy

**Required Tests**:
- Preferred variant selection
- Fallback to any variant
- Multiple ingredients summation
- Pantry ignored (uses variant pricing)
- Error handling (no variant, no purchase)

**Commands**:
```bash
pytest src/tests/test_recipe_service.py -v -k "estimated_cost"
pytest src/tests/test_recipe_service.py -v --cov=src/services/recipe_service
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing variant_service methods | Implement get_preferred_variant/get_any_variant if needed |
| Missing purchase_service methods | Implement get_latest_purchase if needed |
| Unit conversion between recipe and purchase | Use existing convert_any_units with density |

## Definition of Done Checklist

- [x] T013: Method shell implemented
- [x] T014: Preferred variant lookup with fallback
- [x] T015: Latest purchase price retrieval
- [x] T016: Unit conversion and cost calculation
- [x] T017: All tests pass (8 tests in test_recipe_service.py)
- [x] Error handling matches WP02 patterns
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Acceptance Checkpoints**:
1. Preferred variant used when available
2. Fallback to any variant works
3. Pantry completely ignored
4. Decimal precision maintained

**Spec Verification**:
- Run acceptance scenario 1: Preferred variant pricing
- Run acceptance scenario 2: Fallback variant pricing
- Run acceptance scenario 3: Multiple ingredients total

## Activity Log

- 2025-12-02T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-03T17:40:58Z – claude – shell_pid=81940 – lane=doing – Started implementation
- 2025-12-03T18:38:58Z – claude – shell_pid=82419 – lane=for_review – Completed all subtasks T013-T017, all 8 tests passing
- 2025-12-03T20:50:00Z – claude – shell_pid=84323 – lane=done – APPROVED: All 9 estimated_cost tests pass, preferred variant selection verified, fallback to any variant works
- 2025-12-03T18:49:40Z – claude – shell_pid=82419 – lane=done – Approved: All 9 estimated_cost tests pass
