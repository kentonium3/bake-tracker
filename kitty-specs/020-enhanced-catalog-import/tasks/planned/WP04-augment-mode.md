---
work_package_id: "WP04"
subtasks:
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
title: "AUGMENT Mode"
phase: "Phase 2 - Features"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-14T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - AUGMENT Mode

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: Update `review_status: acknowledged` when addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Add AUGMENT mode to ingredients and products; reject AUGMENT for recipes.

**Success Criteria**:
- AUGMENT mode updates only NULL fields on existing records
- Non-null fields are never overwritten
- New records created when slug/key doesn't exist (same as ADD_ONLY)
- AUGMENT for recipes returns clear error message
- Tests verify null-only updates and protection of existing values

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/020-enhanced-catalog-import/spec.md` - FR-004, FR-005, FR-030-033
- `kitty-specs/020-enhanced-catalog-import/data-model.md` - Protected vs augmentable fields

**Prerequisites**:
- WP01, WP02, WP03 complete (entity import functions exist)

**Field Classifications**:

| Entity | Protected Fields | Augmentable Fields |
|--------|-----------------|-------------------|
| Ingredient | slug, display_name | density_*, foodon_id, fdc_ids, foodex2_code, langual_terms, allergens, description |
| Product | ingredient_slug, brand | upc_code, package_size, package_type, purchase_unit (if null), purchase_quantity (if null), is_preferred (if null) |
| Recipe | ALL | NONE (AUGMENT not supported) |

---

## Subtasks & Detailed Guidance

### T022 - Add mode parameter to import_ingredients()

**Purpose**: Extend ingredient import to handle AUGMENT mode.

**Steps**:
1. Mode is already a parameter; add logic branch:
   ```python
   if mode == "augment":
       return _augment_ingredients(data, dry_run, session, result)
   else:
       return _add_ingredients(data, dry_run, session, result)
   ```
2. In `_augment_ingredients`:
   - For each ingredient:
     - If exists: update only null fields, call `result.add_augment()`
     - If not exists: create new (same as add mode)

**Files**: `src/services/catalog_import_service.py`

---

### T023 - Implement protected vs augmentable field handling for ingredients

**Purpose**: Ensure only augmentable fields are updated, and only when null.

**Steps**:
1. Define constants:
   ```python
   INGREDIENT_PROTECTED_FIELDS = {"slug", "display_name", "id", "date_added"}
   INGREDIENT_AUGMENTABLE_FIELDS = {
       "density_volume_value", "density_volume_unit",
       "density_weight_value", "density_weight_unit",
       "foodon_id", "fdc_ids", "foodex2_code", "langual_terms",
       "allergens", "description", "is_packaging", "notes"
   }
   ```
2. Augment logic:
   ```python
   updated_fields = []
   for field in INGREDIENT_AUGMENTABLE_FIELDS:
       if field in import_data and import_data[field] is not None:
           current_value = getattr(existing_ingredient, field)
           if current_value is None:
               setattr(existing_ingredient, field, import_data[field])
               updated_fields.append(field)
   if updated_fields:
       result.add_augment("ingredients", slug, updated_fields)
   else:
       result.add_skip("ingredients", slug, "No null fields to update")
   ```

**Files**: `src/services/catalog_import_service.py`

---

### T024 - Add mode parameter to import_products()

**Purpose**: Extend product import to handle AUGMENT mode.

**Steps**:
1. Add same mode branching as ingredients
2. For existing products: update only null augmentable fields

**Files**: `src/services/catalog_import_service.py`

---

### T025 - Implement protected vs augmentable field handling for products

**Purpose**: Define and enforce product field classifications.

**Steps**:
1. Define constants:
   ```python
   PRODUCT_PROTECTED_FIELDS = {"ingredient_id", "brand", "id", "date_added"}
   PRODUCT_AUGMENTABLE_FIELDS = {
       "upc_code", "package_size", "package_type",
       "purchase_unit", "purchase_quantity", "preferred",
       "supplier", "supplier_sku", "notes"
   }
   ```
2. Same augment logic pattern as ingredients

**Files**: `src/services/catalog_import_service.py`

---

### T026 - Add AUGMENT rejection to import_recipes()

**Purpose**: Return clear error when AUGMENT mode requested for recipes.

**Steps**:
1. At start of `import_recipes()`:
   ```python
   if mode == "augment":
       result = CatalogImportResult()
       result.add_error(
           "recipes",
           "all",
           "mode_not_supported",
           "AUGMENT mode is not supported for recipes",
           "Use ADD_ONLY mode (--mode=add) for recipe import"
       )
       return result
   ```
2. This is a fail-fast at function entry, before any processing

**Files**: `src/services/catalog_import_service.py`

---

### T027 - Test: test_import_ingredients_augment_mode [P]

**Purpose**: Verify null fields updated in AUGMENT mode.

**Steps**:
1. Create ingredient with slug="test", density_volume_value=None
2. Import with mode="augment", density_volume_value=0.55
3. Assert density_volume_value updated to 0.55
4. Assert result.entity_counts["ingredients"]["augmented"] == 1

**Files**: `src/tests/test_catalog_import_service.py`

---

### T028 - Test: test_import_ingredients_augment_preserves_existing [P]

**Purpose**: Verify non-null fields NOT overwritten.

**Steps**:
1. Create ingredient with density_volume_value=0.50 (not null)
2. Import with mode="augment", density_volume_value=0.99
3. Query database, assert density_volume_value still 0.50
4. Verify in result that field was NOT in updated_fields list

**Files**: `src/tests/test_catalog_import_service.py`

---

### T029 - Test: test_import_products_augment_mode [P]

**Purpose**: Verify product AUGMENT works correctly.

**Steps**:
1. Create product with upc_code=None
2. Import with mode="augment", upc_code="123456789012"
3. Assert upc_code updated
4. Assert brand unchanged (protected)

**Files**: `src/tests/test_catalog_import_service.py`

---

### T030 - Test: test_import_recipes_augment_rejected

**Purpose**: Verify AUGMENT mode rejected for recipes.

**Steps**:
1. Create any recipe import data
2. Call `import_recipes(data, mode="augment")`
3. Assert error message contains "AUGMENT mode is not supported"
4. Assert no recipes modified or created

**Files**: `src/tests/test_catalog_import_service.py`

---

## Test Strategy

**Required Tests**:
- `test_import_ingredients_augment_mode` - Null fields updated
- `test_import_ingredients_augment_preserves_existing` - Non-null protected
- `test_import_products_augment_mode` - Product AUGMENT works
- `test_import_recipes_augment_rejected` - Recipe AUGMENT fails

**Commands**:
```bash
pytest src/tests/test_catalog_import_service.py -k "augment" -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Accidental overwrite of user data | Test explicitly verifies non-null preservation |
| Field list incomplete | Reference data-model.md for complete list |
| AUGMENT on non-existent record | Should create new (document this behavior) |

---

## Definition of Done Checklist

- [ ] T022: Mode parameter functional for ingredients
- [ ] T023: Ingredient field classification implemented
- [ ] T024: Mode parameter functional for products
- [ ] T025: Product field classification implemented
- [ ] T026: Recipe AUGMENT rejection with clear error
- [ ] T027: `test_import_ingredients_augment_mode` passes
- [ ] T028: `test_import_ingredients_augment_preserves_existing` passes
- [ ] T029: `test_import_products_augment_mode` passes
- [ ] T030: `test_import_recipes_augment_rejected` passes
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

**Reviewer Checkpoints**:
1. Protected fields NEVER modified in AUGMENT mode
2. Only NULL fields updated (not empty string, not zero)
3. New records created when key doesn't exist
4. Recipe AUGMENT fails immediately with helpful message
5. Result tracking distinguishes "added" vs "augmented" vs "skipped"

---

## Activity Log

- 2025-12-14T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
