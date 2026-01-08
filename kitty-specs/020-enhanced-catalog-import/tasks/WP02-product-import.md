---
work_package_id: WP02
title: Product Import
lane: done
history:
- timestamp: '2025-12-14T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 1 - Foundation
review_status: ''
reviewed_by: ''
shell_pid: '63528'
subtasks:
- T008
- T009
- T010
- T011
- T012
---

# Work Package Prompt: WP02 - Product Import

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Implement `import_products()` with FK validation for ingredient references.

**Success Criteria**:
- `import_products()` function creates products with valid ingredient references
- FK validation fails with actionable error when ingredient_slug not found
- Composite unique key (ingredient_id, brand) correctly handles duplicates
- Unit tests verify both success and failure paths

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/020-enhanced-catalog-import/spec.md` - FR-001, FR-022
- `kitty-specs/020-enhanced-catalog-import/data-model.md` - Product field mapping
- `src/models/product.py` - Product model definition

**Prerequisites**:
- WP01 complete (CatalogImportResult class exists)

**Architectural Constraints**:
1. Product unique key: `(ingredient_id, brand)` - note: brand can be null
2. Must lookup ingredient by slug to get ingredient_id
3. FK error format: "Product 'X' for ingredient 'Y' failed: Ingredient 'Y' not found."

---

## Subtasks & Detailed Guidance

### T008 - Implement import_products() with ADD_ONLY mode

**Purpose**: Create product import function matching ingredient pattern.

**Steps**:
1. Add Product model import: `from src.models.product import Product`
2. Define function signature:
   ```python
   def import_products(
       data: List[Dict],
       mode: str = "add",
       dry_run: bool = False,
       session: Optional[Session] = None
   ) -> CatalogImportResult:
   ```
3. Implement session handling pattern (same as ingredients)
4. In `_import_products_impl`:
   - Build slug->id lookup: `slug_to_id = {i.slug: i.id for i in session.query(Ingredient.slug, Ingredient.id).all()}`
   - For each product, lookup ingredient_id
   - Check for existing (ingredient_id, brand) combo
   - Create or skip as appropriate

**Files**: `src/services/catalog_import_service.py`

---

### T009 - Implement ingredient_slug FK validation

**Purpose**: Validate that referenced ingredient exists before creating product.

**Steps**:
1. Extract `ingredient_slug` from product data
2. Look up in `slug_to_id` dict
3. If not found:
   ```python
   result.add_error(
       "products",
       f"{brand or 'Generic'} ({ingredient_slug})",
       "fk_missing",
       f"Ingredient '{ingredient_slug}' not found",
       "Import the ingredient first or check the slug spelling"
   )
   continue  # Skip this product, continue with others
   ```

**Files**: `src/services/catalog_import_service.py`

---

### T010 - Handle composite unique key (ingredient_id, brand)

**Purpose**: Correctly identify duplicate products.

**Steps**:
1. Build existing products lookup:
   ```python
   existing_products = set()
   for p in session.query(Product.ingredient_id, Product.brand).all():
       existing_products.add((p.ingredient_id, p.brand))
   ```
2. Before creating product, check:
   ```python
   if (ingredient_id, brand) in existing_products:
       result.add_skip("products", f"{brand} ({ingredient_slug})", "Already exists")
       continue
   ```
3. Handle null brand: `brand` can be None, which is valid and should still be unique per ingredient

**Note**: Brand is nullable. `(ingredient_id, None)` is a valid unique combination.

**Files**: `src/services/catalog_import_service.py`

---

### T011 - Test: test_import_products_add_mode [P]

**Purpose**: Verify new products are created correctly with valid FK.

**Steps**:
1. Pre-create ingredient with slug "test_flour"
2. Create product data referencing "test_flour"
3. Call `import_products(data)`
4. Assert added == 1
5. Query database to verify product exists with correct ingredient_id

**Files**: `src/tests/test_catalog_import_service.py`

**Parallel**: Yes

---

### T012 - Test: test_import_products_fk_validation [P]

**Purpose**: Verify FK validation fails with actionable error.

**Steps**:
1. Create product data referencing non-existent "missing_ingredient"
2. Call `import_products(data)`
3. Assert failed == 1, added == 0
4. Assert error message contains "missing_ingredient"
5. Assert error includes suggestion to import ingredient first

**Files**: `src/tests/test_catalog_import_service.py`

**Parallel**: Yes

---

## Test Strategy

**Required Tests**:
- `test_import_products_add_mode` - Happy path with valid FK
- `test_import_products_fk_validation` - FK error with actionable message

**Commands**:
```bash
pytest src/tests/test_catalog_import_service.py::test_import_products_add_mode -v
pytest src/tests/test_catalog_import_service.py::test_import_products_fk_validation -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Null brand handling | Explicitly test with brand=None in test data |
| FK lookup cache stale | Build lookup at start of import, not per-record |
| Wrong ingredient_id type | Verify lookup returns int, not string |

---

## Definition of Done Checklist

- [ ] T008: `import_products()` function implemented
- [ ] T009: FK validation with actionable error message
- [ ] T010: Composite unique key handles null brand
- [ ] T011: `test_import_products_add_mode` passes
- [ ] T012: `test_import_products_fk_validation` passes
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

**Reviewer Checkpoints**:
1. FK error message format matches spec (entity, identifier, error, suggestion)
2. Null brand handled correctly in uniqueness check
3. Session pattern matches WP01 implementation
4. Partial success: valid products created even if some fail

---

## Activity Log

- 2025-12-14T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-15T02:48:40Z – claude – shell_pid=56445 – lane=doing – Started implementation
- 2025-12-15T02:51:01Z – claude – shell_pid=56445 – lane=for_review – Ready for review
- 2025-12-15T03:23:37Z – claude-reviewer – shell_pid=63528 – lane=done – Code review: APPROVED - Product import with FK validation, skip logic, and AUGMENT mode verified
