# Work Packages: Recipe FIFO Cost Integration

**Inputs**: Design documents from `/kitty-specs/005-recipe-fifo-cost/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required per constitution - service layer must maintain >70% test coverage.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `kitty-specs/005-recipe-fifo-cost/tasks/planned/`.

---

## Work Package WP01: PantryService dry_run Extension (Priority: P0)

**Goal**: Add `dry_run=True` parameter to `consume_fifo()` enabling read-only FIFO cost simulation.
**Independent Test**: Call `consume_fifo(ingredient_slug, quantity, dry_run=True)` and verify pantry quantities unchanged, cost returned.
**Prompt**: `tasks/planned/WP01-pantry-dry-run.md`

### Included Subtasks
- [ ] T001 Add `dry_run: bool = False` parameter to `consume_fifo()` signature
- [ ] T002 Implement dry-run branch logic (skip session flush/commit when `dry_run=True`)
- [ ] T003 Add `total_cost` field to `ConsumeFifoResult` dict
- [ ] T004 Add `unit_cost` field to each `ConsumptionBreakdownItem`
- [ ] T005 Write tests for `consume_fifo(dry_run=True)` behavior

### Implementation Notes
1. Modify `src/services/pantry_service.py` lines ~229-349
2. When `dry_run=True`: calculate costs, build breakdown, but do NOT call `session.flush()` or update quantities
3. Ensure existing `dry_run=False` behavior unchanged (backward compatibility)
4. Add cost tracking: `total_cost = sum(item.unit_cost * item.quantity_consumed for item in breakdown)`

### Parallel Opportunities
- None - sequential implementation required (T001 → T002 → T003 → T004 → T005)

### Dependencies
- None (foundational work package)

### Risks & Mitigations
- Breaking existing consumption logic → Test existing behavior before and after changes
- Session state leakage in dry_run mode → Use explicit session rollback or detached queries

---

## Work Package WP02: User Story 1 – Calculate Actual Recipe Cost (Priority: P1) 🎯 MVP

**Goal**: Implement `calculate_actual_cost()` in RecipeService using FIFO pantry inventory.
**Independent Test**: Create recipe with known ingredient quantities, pantry with known costs at different dates, verify FIFO ordering in returned cost.
**Prompt**: `tasks/planned/WP02-actual-cost.md`

### Included Subtasks
- [ ] T006 Implement `calculate_actual_cost(recipe_id: int) -> Decimal` method shell
- [ ] T007 Load Recipe with RecipeIngredients, iterate each ingredient
- [ ] T008 For each ingredient: convert units and call `consume_fifo(dry_run=True)`
- [ ] T009 Implement fallback to preferred variant pricing for any shortfall
- [ ] T010 Sum all ingredient costs and return Decimal total
- [ ] T011 Implement fail-fast error handling (RecipeNotFound, IngredientNotFound, ValidationError)
- [ ] T012 Write tests for `calculate_actual_cost()` covering FIFO ordering and read-only behavior

### Implementation Notes
1. Add method to `src/services/recipe_service.py` after existing cost methods (~line 412+)
2. Follow existing service patterns: `with session_scope() as session:`, eager-load relationships
3. Use `convert_any_units()` from unit_converter for recipe→pantry unit conversion
4. Get ingredient density via `get_ingredient_density(ingredient.name)` from constants
5. Call `pantry_service.consume_fifo(ingredient.slug, converted_quantity, dry_run=True)`
6. For shortfall: call `variant_service.get_preferred_variant()` then `purchase_service.get_latest_price()`

### Parallel Opportunities
- T006-T010 sequential; T011 and T012 can overlap with final implementation polish

### Dependencies
- Depends on WP01 (consume_fifo dry_run capability)

### Risks & Mitigations
- Unit conversion failures → Use existing `convert_any_units()` with density lookup
- Missing density data → Fail fast with descriptive ValidationError

---

## Work Package WP03: User Story 2 – Calculate Estimated Recipe Cost (Priority: P2)

**Goal**: Implement `calculate_estimated_cost()` using preferred variant pricing (ignores pantry).
**Independent Test**: Calculate cost for recipe with empty pantry, verify uses preferred variant's most recent purchase price.
**Prompt**: `tasks/planned/WP03-estimated-cost.md`

### Included Subtasks
- [ ] T013 Implement `calculate_estimated_cost(recipe_id: int) -> Decimal` method shell
- [ ] T014 For each ingredient: get preferred variant (or fallback to any variant)
- [ ] T015 Get most recent purchase price for the variant
- [ ] T016 Convert units between recipe and purchase units, calculate ingredient cost
- [ ] T017 Write tests for `calculate_estimated_cost()` with preferred/fallback variant scenarios

### Implementation Notes
1. Add method to `src/services/recipe_service.py` after `calculate_actual_cost()`
2. Use `variant_service.get_preferred_variant(ingredient_id)` → fallback to `get_any_variant(ingredient_id)`
3. Use `purchase_service.get_latest_purchase(variant_id)` for pricing
4. Convert recipe units to purchase units using `convert_any_units()`
5. Follow same error handling pattern as `calculate_actual_cost()`

### Parallel Opportunities
- T013-T16 sequential; T017 can overlap with late implementation

### Dependencies
- Depends on WP01 (shares service patterns)
- Can proceed in parallel with WP02 after WP01 complete

### Risks & Mitigations
- Missing purchase history → Fail fast with ValidationError
- No preferred variant set → Graceful fallback to any variant

---

## Work Package WP04: User Story 3 – Handle Partial Pantry Inventory (Priority: P3)

**Goal**: Ensure `calculate_actual_cost()` correctly blends FIFO costs with fallback pricing for partial inventory.
**Independent Test**: Recipe needs 3 cups, pantry has 2 cups at $0.10/cup, verify cost = (2 × $0.10) + (1 × fallback price).
**Prompt**: `tasks/planned/WP04-partial-inventory.md`

### Included Subtasks
- [ ] T018 Verify `calculate_actual_cost()` handles shortfall from `consume_fifo()` result
- [ ] T019 Ensure FIFO portion + fallback portion are correctly summed per ingredient
- [ ] T020 Write tests for partial inventory scenarios (2 cups available of 3 needed, etc.)

### Implementation Notes
1. This WP validates/extends WP02 implementation
2. Key check: `consume_fifo()` returns `shortfall > 0` → calculate fallback cost for shortfall amount
3. Formula: `ingredient_cost = fifo_result.total_cost + (shortfall * fallback_unit_price)`
4. Test with multiple ingredients having different coverage levels

### Parallel Opportunities
- T018-T19 sequential; T020 can start after basic implementation verified

### Dependencies
- Depends on WP02 (calculate_actual_cost implementation)

### Risks & Mitigations
- Rounding errors in blended costs → Use Decimal throughout, test with known values

---

## Work Package WP05: Edge Cases & Validation (Priority: P4)

**Goal**: Handle all edge cases and verify test coverage meets >70% threshold.
**Independent Test**: All edge case tests pass; `pytest --cov` shows >70% on new methods.
**Prompt**: `tasks/planned/WP05-edge-cases-validation.md`

### Included Subtasks
- [ ] T021 Handle edge cases: zero quantity ingredients, missing density, empty recipe
- [ ] T022 Validate error messages are descriptive and user-friendly
- [ ] T023 Run coverage check and verify >70% threshold met for new code
- [ ] T024 Validate quickstart.md scenarios execute correctly

### Implementation Notes
1. Edge cases from spec:
   - Recipe with zero ingredients → return Decimal("0.00")
   - Ingredient quantity = 0 → skip (contributes $0)
   - No variants → raise IngredientNotFound
   - No purchase history → raise ValidationError
   - Missing density → raise ValidationError
2. Run: `pytest src/tests -v --cov=src/services/recipe_service --cov=src/services/pantry_service`
3. Test quickstart examples manually or with integration test

### Parallel Opportunities
- T021-T22 can proceed in parallel with T23-T24

### Dependencies
- Depends on WP02, WP03, WP04

### Risks & Mitigations
- Coverage gap → Add targeted tests for uncovered branches
- Edge case discovery → Review spec edge cases section thoroughly

---

## Dependency & Execution Summary

```
WP01 (PantryService dry_run)
  │
  ├──> WP02 (User Story 1 - Actual Cost) 🎯 MVP
  │      │
  │      └──> WP04 (User Story 3 - Partial Inventory)
  │
  └──> WP03 (User Story 2 - Estimated Cost)
              │
              └──> WP05 (Edge Cases & Validation)
                         ↑
                    (also depends on WP02, WP04)
```

- **Sequence**: WP01 → (WP02 || WP03) → WP04 → WP05
- **Parallelization**: After WP01, WP02 and WP03 can proceed in parallel
- **MVP Scope**: WP01 + WP02 delivers core FIFO costing capability

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Add `dry_run` parameter to `consume_fifo()` | WP01 | P0 | No |
| T002 | Implement dry-run branch logic | WP01 | P0 | No |
| T003 | Add `total_cost` to result dict | WP01 | P0 | No |
| T004 | Add `unit_cost` to breakdown items | WP01 | P0 | No |
| T005 | Write tests for dry_run behavior | WP01 | P0 | No |
| T006 | Implement `calculate_actual_cost()` shell | WP02 | P1 | No |
| T007 | Iterate RecipeIngredients with unit conversion | WP02 | P1 | No |
| T008 | Call `consume_fifo(dry_run=True)` | WP02 | P1 | No |
| T009 | Implement fallback to preferred variant | WP02 | P1 | No |
| T010 | Sum ingredient costs, return Decimal | WP02 | P1 | No |
| T011 | Implement fail-fast error handling | WP02 | P1 | No |
| T012 | Write tests for actual cost calculation | WP02 | P1 | No |
| T013 | Implement `calculate_estimated_cost()` shell | WP03 | P2 | No |
| T014 | Get preferred variant for each ingredient | WP03 | P2 | No |
| T015 | Get most recent purchase price | WP03 | P2 | No |
| T016 | Convert units and calculate cost | WP03 | P2 | No |
| T017 | Write tests for estimated cost | WP03 | P2 | No |
| T018 | Verify shortfall handling in actual cost | WP04 | P3 | No |
| T019 | Blend FIFO + fallback costs correctly | WP04 | P3 | No |
| T020 | Write tests for partial inventory | WP04 | P3 | No |
| T021 | Handle edge cases (zero qty, missing density) | WP05 | P4 | No |
| T022 | Validate error messages | WP05 | P4 | No |
| T023 | Verify >70% test coverage | WP05 | P4 | No |
| T024 | Validate quickstart.md scenarios | WP05 | P4 | No |
