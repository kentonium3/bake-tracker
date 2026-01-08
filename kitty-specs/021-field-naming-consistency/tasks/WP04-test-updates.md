---
work_package_id: WP04
title: Test Updates
lane: done
history:
- timestamp: '2025-12-15T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: automated
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 3 - Validation
review_status: approved without changes
reviewed_by: claude-reviewer
shell_pid: '83880'
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
- T025
- T026
- T027
- T028
- T029
- T030
- T031
- T032
- T033
- T034
- T035
- T036
- T053
- T054
- T055
- T056
---

# Work Package Prompt: WP04 - Test Updates

## Objectives & Success Criteria

**Part A - Field Rename:**
- Update all test files to use new field names `package_unit` and `package_unit_quantity`

**Part B - Terminology Rename:**
- Rename `pantry` references to `inventory` in test function names, variables, and docstrings

**Success Criteria:**
- `grep -rn "purchase_unit\|purchase_quantity" src/tests/` returns zero matches
- `grep -rni "pantry" src/tests/` returns only acceptable matches (skip reasons with historical context, if preserved)
- `pytest src/tests -v` passes 100%

## Context & Constraints

### Prerequisites
- WP01 (Model), WP02 (Services), WP03 (UI) should be completed first.

### Related Documents
- Spec: `kitty-specs/021-field-naming-consistency/spec.md` (FR-005, User Story 5)
- Research: `kitty-specs/021-field-naming-consistency/research.md` (~18 test files affected)

### Constraints
- Tests should validate the same behavior, just with new field names.
- Do not change test logic or assertions beyond the field name updates.

## Subtasks & Detailed Guidance

### Subtask T019 - Update conftest.py

**Purpose**: Update test fixtures and sample data generators.

**Steps**:
1. Open `src/tests/conftest.py`
2. Find all fixture functions that create Product objects
3. Replace `purchase_unit=...` with `package_unit=...`
4. Replace `purchase_quantity=...` with `package_unit_quantity=...`
5. Update any sample data dictionaries

**Files**: `src/tests/conftest.py`

**Parallel?**: Yes - but foundational, recommend doing first.

### Subtask T020 - Update test_models.py

**Purpose**: Update model tests.

**Steps**:
1. Open `src/tests/test_models.py`
2. Search and replace `purchase_unit` -> `package_unit`
3. Search and replace `purchase_quantity` -> `package_unit_quantity`

**Files**: `src/tests/test_models.py`

**Parallel?**: Yes.

### Subtask T021 - Update test_validators.py

**Purpose**: Update validator tests.

**Steps**:
1. Open `src/tests/test_validators.py`
2. Search and replace field name references

**Files**: `src/tests/test_validators.py`

**Parallel?**: Yes.

### Subtask T022 - Update test_catalog_import_service.py

**Purpose**: Update catalog import tests.

**Steps**:
1. Open `src/tests/test_catalog_import_service.py`
2. Search and replace field name references
3. Update any inline JSON test data

**Files**: `src/tests/test_catalog_import_service.py`

**Parallel?**: Yes.

### Subtask T023 - Update test_batch_production_service.py

**Steps**:
1. Open `src/tests/test_batch_production_service.py`
2. Search and replace field name references

**Files**: `src/tests/test_batch_production_service.py`

**Parallel?**: Yes.

### Subtask T024 - Update test_assembly_service.py

**Steps**:
1. Open `src/tests/test_assembly_service.py`
2. Search and replace field name references

**Files**: `src/tests/test_assembly_service.py`

**Parallel?**: Yes.

### Subtask T025 - Update services/test_recipe_service.py

**Steps**:
1. Open `src/tests/services/test_recipe_service.py`
2. Search and replace field name references

**Files**: `src/tests/services/test_recipe_service.py`

**Parallel?**: Yes.

### Subtask T026 - Update services/test_production_service.py

**Steps**:
1. Open `src/tests/services/test_production_service.py`
2. Search and replace field name references

**Files**: `src/tests/services/test_production_service.py`

**Parallel?**: Yes.

### Subtask T027 - Update services/test_product_recommendation_service.py

**Steps**:
1. Open `src/tests/services/test_product_recommendation_service.py`
2. Search and replace field name references

**Files**: `src/tests/services/test_product_recommendation_service.py`

**Parallel?**: Yes.

### Subtask T028 - Update services/test_inventory_item_service.py

**Steps**:
1. Open `src/tests/services/test_inventory_item_service.py`
2. Search and replace field name references

**Files**: `src/tests/services/test_inventory_item_service.py`

**Parallel?**: Yes.

### Subtask T029 - Update services/test_ingredient_service.py

**Steps**:
1. Open `src/tests/services/test_ingredient_service.py`
2. Search and replace field name references

**Files**: `src/tests/services/test_ingredient_service.py`

**Parallel?**: Yes.

### Subtask T030 - Update services/test_event_service_products.py

**Steps**:
1. Open `src/tests/services/test_event_service_products.py`
2. Search and replace field name references

**Files**: `src/tests/services/test_event_service_products.py`

**Parallel?**: Yes.

### Subtask T031 - Update services/test_event_service_packaging.py

**Steps**:
1. Open `src/tests/services/test_event_service_packaging.py`
2. Search and replace field name references

**Files**: `src/tests/services/test_event_service_packaging.py`

**Parallel?**: Yes.

### Subtask T032 - Update services/test_composition_service.py

**Steps**:
1. Open `src/tests/services/test_composition_service.py`
2. Search and replace field name references

**Files**: `src/tests/services/test_composition_service.py`

**Parallel?**: Yes.

### Subtask T033 - Update integration/test_purchase_flow.py

**Steps**:
1. Open `src/tests/integration/test_purchase_flow.py`
2. Search and replace field name references

**Files**: `src/tests/integration/test_purchase_flow.py`

**Parallel?**: Yes.

### Subtask T034 - Update integration/test_packaging_flow.py

**Steps**:
1. Open `src/tests/integration/test_packaging_flow.py`
2. Search and replace field name references

**Files**: `src/tests/integration/test_packaging_flow.py`

**Parallel?**: Yes.

### Subtask T035 - Update integration/test_inventory_flow.py

**Steps**:
1. Open `src/tests/integration/test_inventory_flow.py`
2. Search and replace field name references

**Files**: `src/tests/integration/test_inventory_flow.py`

**Parallel?**: Yes.

### Subtask T036 - Update integration/test_fifo_scenarios.py

**Steps**:
1. Open `src/tests/integration/test_fifo_scenarios.py`
2. Search and replace field name references

**Files**: `src/tests/integration/test_fifo_scenarios.py`

**Parallel?**: Yes.

---

## Part B: pantry -> inventory Terminology

### Subtask T053 - Rename pantry->inventory in test_recipe_service.py

**Purpose**: Align test terminology with internal model naming.

**Steps**:
1. Open `src/tests/services/test_recipe_service.py`
2. Rename function names containing `pantry`:
   - `test_calculate_actual_cost_does_not_modify_pantry` -> `test_calculate_actual_cost_does_not_modify_inventory`
   - `test_calculate_actual_cost_no_pantry_uses_all_fallback` -> `test_calculate_actual_cost_no_inventory_uses_all_fallback`
   - `test_calculate_estimated_cost_ignores_pantry` -> `test_calculate_estimated_cost_ignores_inventory`
   - Similar for other function names
3. Update docstrings: "Pantry quantities" -> "Inventory quantities", "pantry insufficient" -> "inventory insufficient"
4. Update variable names in comments: "pantry state" -> "inventory state", "Add pantry items" -> "Add inventory items"
5. Update inline comments referencing pantry

**Files**: `src/tests/services/test_recipe_service.py`

**Occurrences**: ~30

**Parallel?**: Yes.

### Subtask T054 - Rename pantry->inventory in test_production_service.py

**Purpose**: Align test terminology with internal model naming.

**Steps**:
1. Open `src/tests/services/test_production_service.py`
2. Update docstring: "Insufficient pantry raises" -> "Insufficient inventory raises"

**Files**: `src/tests/services/test_production_service.py`

**Occurrences**: ~1

**Parallel?**: Yes.

### Subtask T055 - Rename pantry->inventory in test_validators.py

**Purpose**: Update skip reason to use current terminology.

**Steps**:
1. Open `src/tests/test_validators.py`
2. Find skip reason: `"TD-001: quantity moved to PantryItem, not Ingredient"`
3. Update to: `"TD-001: quantity moved to InventoryItem (formerly PantryItem), not Ingredient"`

**Files**: `src/tests/test_validators.py`

**Occurrences**: ~1

**Parallel?**: Yes.

**Note**: This preserves historical context while using current terminology.

### Subtask T056 - Rename pantry->inventory in test_services.py

**Purpose**: Update skip reasons to use current terminology.

**Steps**:
1. Open `src/tests/test_services.py`
2. Find all skip reasons referencing `PantryItem`:
   - `"TD-001: quantity moved to PantryItem, not Ingredient"`
   - `"TD-001: Stock management moved to PantryItem, not Ingredient"`
   - `"TD-001: Inventory value calculation moved to PantryItem"`
   - `"TD-001: Cost calculation requires Product/PantryItem with price data"`
3. Update each to reference `InventoryItem (formerly PantryItem)` or just `InventoryItem`

**Files**: `src/tests/test_services.py`

**Occurrences**: ~6

**Parallel?**: Yes.

**Note**: These skip reasons document historical schema changes. Either preserve with annotation or update to current terminology.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missed references cause test failures | Run full test suite after updates |
| Test logic inadvertently changed | Only change field/variable names, not test assertions or logic |
| Overzealous pantry renaming breaks historical context | Review skip reasons carefully; use "(formerly PantryItem)" annotation if helpful |

## Definition of Done Checklist

**Part A (purchase_* -> package_*):**
- [ ] All 18 test files updated for field name changes
- [ ] `grep -rn "purchase_unit\|purchase_quantity" src/tests/` returns zero matches

**Part B (pantry -> inventory):**
- [ ] T053: test_recipe_service.py updated (~30 occurrences)
- [ ] T054: test_production_service.py updated (~1 occurrence)
- [ ] T055: test_validators.py updated (~1 occurrence)
- [ ] T056: test_services.py updated (~6 occurrences)
- [ ] `grep -rni "pantry" src/tests/` returns only acceptable matches (if any preserved)

**Final Verification:**
- [ ] No syntax errors in any test file
- [ ] `pytest src/tests -v` passes 100%
- [ ] `tasks.md` updated with status change

## Review Guidance

- Run grep to confirm zero matches for `purchase_unit`/`purchase_quantity`
- Run grep for `pantry` and verify only acceptable matches remain
- Run pytest to confirm all tests pass
- Spot-check conftest.py fixtures for correct field names
- Verify function names like `test_*_pantry_*` have been renamed to `test_*_inventory_*`

## Activity Log

- 2025-12-15T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-15T17:20:47Z – claude – shell_pid=83880 – lane=doing – Started implementation
- 2025-12-15T17:41:12Z – claude – shell_pid=83880 – lane=for_review – Moved to for_review
- 2025-12-15T21:52:06Z – claude – shell_pid=83880 – lane=done – Code review approved: Tests correctly updated, 689 pass
