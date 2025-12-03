---
work_package_id: "WP04"
subtasks:
  - "T018"
  - "T019"
  - "T020"
title: "User Story 3 - Handle Partial Pantry Inventory"
phase: "Phase 2 - Enhancement"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "82543"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – User Story 3 - Handle Partial Pantry Inventory

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

**Objective**: Ensure `calculate_actual_cost()` correctly blends FIFO costs with fallback pricing when pantry inventory is insufficient.

**Success Criteria** (from spec acceptance scenarios):
1. Recipe needs 3 cups flour, pantry has 2 cups at $0.10/cup, preferred variant at $0.15/cup → cost = (2 × $0.10) + (1 × $0.15) = $0.35
2. Multiple ingredients with varying coverage → each costed appropriately
3. Zero pantry inventory → falls back entirely to preferred variant

**Note**: This WP validates and extends the WP02 implementation.

## Context & Constraints

**Prerequisite Documents**:
- Plan: `kitty-specs/005-recipe-fifo-cost/plan.md`
- Spec: `kitty-specs/005-recipe-fifo-cost/spec.md` (User Story 3)

**Dependencies**:
- **WP02 must be complete** - this extends `calculate_actual_cost()`

**Key Insight**:
The shortfall handling was already specified in WP02 (T009). This WP focuses on:
1. Verifying the implementation handles partial scenarios correctly
2. Adding comprehensive tests for blended costing
3. Ensuring the math is precise

**Key Files**:
- `src/services/recipe_service.py` (verify implementation)
- `src/tests/test_recipe_service.py` (add partial inventory tests)

## Subtasks & Detailed Guidance

### Subtask T018 – Verify shortfall handling in calculate_actual_cost

**Purpose**: Confirm the implementation correctly detects and handles pantry shortfalls.

**Steps**:
1. Review `calculate_actual_cost()` implementation from WP02
2. Verify: When `consume_fifo()` returns `shortfall > 0`, fallback pricing is applied
3. Verify: The `shortfall` value is correctly used (not `quantity_needed`)
4. If issues found, fix the implementation

**Files**: `src/services/recipe_service.py`

**Notes**: This is primarily a verification task. The logic should already exist from WP02.

### Subtask T019 – Ensure FIFO + fallback costs blend correctly

**Purpose**: Verify the cost calculation formula is mathematically correct.

**Steps**:
1. Confirm formula: `ingredient_cost = fifo_result.total_cost + (shortfall * fallback_unit_price)`
2. Verify unit conversion is applied to shortfall before pricing
3. Ensure Decimal arithmetic (no float precision loss)
4. Trace through with a manual calculation to verify

**Files**: `src/services/recipe_service.py`

**Example Trace**:
```
Recipe: 3 cups flour
Pantry: 2 cups at $0.10/cup
Preferred variant: $0.15/cup

consume_fifo(dry_run=True):
  - consumed: 2.0
  - total_cost: $0.20
  - shortfall: 1.0

fallback_cost = 1.0 * $0.15 = $0.15
ingredient_cost = $0.20 + $0.15 = $0.35 ✓
```

### Subtask T020 – Write tests for partial inventory scenarios

**Purpose**: Comprehensive test coverage for blended costing scenarios.

**Steps**:
1. `test_calculate_actual_cost_partial_inventory_blends_costs`:
   - Setup: 3 cups needed, 2 cups in pantry at $0.10, variant at $0.15
   - Assert: Total = $0.35
2. `test_calculate_actual_cost_zero_inventory_uses_fallback`:
   - Setup: Recipe needs flour, pantry empty
   - Assert: Uses entirely preferred variant pricing
3. `test_calculate_actual_cost_full_inventory_no_fallback`:
   - Setup: Recipe needs 2 cups, pantry has 3 cups
   - Assert: Uses only FIFO costs (no fallback)
4. `test_calculate_actual_cost_multiple_ingredients_mixed_coverage`:
   - Setup: Flour (partial), sugar (full), butter (empty)
   - Assert: Each ingredient costed per its coverage level
5. `test_calculate_actual_cost_shortfall_unit_conversion`:
   - Setup: Recipe in cups, pantry in grams, partial coverage
   - Assert: Shortfall correctly converted before fallback pricing

**Files**: `src/tests/test_recipe_service.py`

**Notes**: Use precise Decimal values in assertions.

## Test Strategy

**Required Tests**:
- Partial inventory (pantry < needed)
- Zero inventory (pantry empty)
- Full inventory (pantry >= needed)
- Multiple ingredients with varying coverage
- Unit conversion with shortfall

**Commands**:
```bash
pytest src/tests/test_recipe_service.py -v -k "partial"
pytest src/tests/test_recipe_service.py -v -k "actual_cost"
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Rounding errors in blended costs | Use Decimal throughout; test with exact values |
| Unit conversion applied incorrectly to shortfall | Verify shortfall is in correct units before pricing |
| Edge case: exactly enough inventory | Test boundary condition |

## Definition of Done Checklist

- [ ] T018: Shortfall handling verified correct
- [ ] T019: Blended cost formula verified
- [ ] T020: All partial inventory tests pass
- [ ] Acceptance scenario from spec verified: 3 cups, 2 in pantry = $0.35
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Acceptance Checkpoints**:
1. Spec acceptance scenario: (2 × $0.10) + (1 × $0.15) = $0.35
2. Zero inventory → 100% fallback pricing
3. Full inventory → 0% fallback pricing
4. Decimal precision maintained

**Manual Verification**:
Run the exact scenario from the spec and verify the result matches $0.35.

## Activity Log

- 2025-12-02T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-03T18:39:23Z – claude – shell_pid=82543 – lane=doing – Started verification and testing
