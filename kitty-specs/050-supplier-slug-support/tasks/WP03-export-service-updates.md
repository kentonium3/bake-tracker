---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "Export Service Updates"
phase: "Phase 1 - Core Functionality"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "59105"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2026-01-12T23:45:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Export Service Updates

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: When addressing feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Update export to include supplier slugs and product supplier references.

**Success Criteria**:
- Supplier export JSON includes `slug` field
- Product export JSON includes `preferred_supplier_slug` and `preferred_supplier_name`
- Handle products with no preferred supplier (null/empty fields)
- All export tests pass

## Context & Constraints

**Dependencies**: WP01 must be complete (slug field exists in model)

**Can Parallelize With**: WP02 (different files, no conflicts)

**Key Files**:
- `src/services/import_export_service.py` - Main export logic
- Research finding: Look for `_export_suppliers()` or similar method

---

## Subtasks & Detailed Guidance

### Subtask T013 - Update supplier export with slug field

**Purpose**: Include slug in supplier JSON export.

**Steps**:
1. Open `src/services/import_export_service.py`
2. Locate supplier export logic (likely `_export_suppliers()` or `export_data()`)
3. Ensure slug is included in the export dict:
   ```python
   def _export_supplier(supplier: Supplier) -> dict:
       return {
           "id": supplier.id,
           "slug": supplier.slug,  # Add slug field
           "name": supplier.name,
           "supplier_type": supplier.supplier_type,
           "website_url": supplier.website_url,
           "city": supplier.city,
           "state": supplier.state,
           "zip_code": supplier.zip_code,
           "street_address": supplier.street_address,
           "notes": supplier.notes,
           "is_active": supplier.is_active,
       }
   ```
4. If using `to_dict()`, verify slug is included (should be automatic after WP01)

**Files**: `src/services/import_export_service.py`
**Notes**: Slug should be early in the dict for readability

### Subtask T014 - Add preferred_supplier_slug to product export

**Purpose**: Enable slug-based supplier resolution on import.

**Steps**:
1. Locate product export logic
2. Add supplier slug lookup:
   ```python
   def _export_product(product: Product, session: Session) -> dict:
       result = {
           "id": product.id,
           "sku": product.sku,
           "display_name": product.display_name,
           # ... other fields
           "preferred_supplier_id": product.preferred_supplier_id,
       }

       # Add slug-based reference
       if product.preferred_supplier_id:
           supplier = session.query(Supplier).get(product.preferred_supplier_id)
           if supplier:
               result["preferred_supplier_slug"] = supplier.slug
           else:
               result["preferred_supplier_slug"] = None
       else:
           result["preferred_supplier_slug"] = None

       return result
   ```

**Files**: `src/services/import_export_service.py`
**Notes**: Handle case where supplier_id exists but supplier was deleted

### Subtask T015 - Add preferred_supplier_name to product export

**Purpose**: Provide human-readable supplier reference.

**Steps**:
1. Extend product export to include supplier name:
   ```python
   if supplier:
       result["preferred_supplier_slug"] = supplier.slug
       result["preferred_supplier_name"] = supplier.display_name  # Use display_name property
   else:
       result["preferred_supplier_slug"] = None
       result["preferred_supplier_name"] = None
   ```

**Files**: `src/services/import_export_service.py`
**Notes**: Use `display_name` property which includes location for physical suppliers

### Subtask T016 - Write tests for supplier export

**Purpose**: Verify slug is included in export.

**Steps**:
1. Add/update export tests:
   ```python
   def test_export_supplier_includes_slug(self, session):
       """Supplier export includes slug field."""
       supplier = create_supplier({
           "name": "Test Store",
           "supplier_type": "physical",
           "city": "Boston",
           "state": "MA"
       }, session=session)

       export_data = export_suppliers(session)

       supplier_export = next(s for s in export_data if s["id"] == supplier.id)
       assert supplier_export["slug"] == "test_store_boston_ma"
   ```

**Files**: `src/tests/test_import_export.py`
**Parallel?**: Yes

### Subtask T017 - Write tests for product export with supplier slug

**Purpose**: Verify product export includes supplier references.

**Steps**:
1. Add product export tests:
   ```python
   def test_export_product_includes_supplier_slug(self, session):
       """Product export includes preferred_supplier_slug."""
       supplier = create_supplier({...}, session=session)
       product = create_product({
           "display_name": "Test Product",
           "preferred_supplier_id": supplier.id
       }, session=session)

       export_data = export_products(session)

       product_export = next(p for p in export_data if p["id"] == product.id)
       assert product_export["preferred_supplier_slug"] == supplier.slug
       assert product_export["preferred_supplier_name"] == supplier.display_name

   def test_export_product_no_supplier(self, session):
       """Product without supplier has null slug fields."""
       product = create_product({
           "display_name": "Test Product"
       }, session=session)

       export_data = export_products(session)

       product_export = next(p for p in export_data if p["id"] == product.id)
       assert product_export["preferred_supplier_slug"] is None
       assert product_export["preferred_supplier_name"] is None
   ```

**Files**: `src/tests/test_import_export.py`
**Parallel?**: Yes

---

## Test Strategy

**Required Tests**:
1. Supplier export includes slug
2. Product export includes preferred_supplier_slug
3. Product export includes preferred_supplier_name
4. Product with no supplier has null fields
5. Product with deleted supplier handles gracefully

**Run Tests**:
```bash
./run-tests.sh src/tests/test_import_export.py -v -k "export"
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Product references deleted supplier | Export fails | Check if supplier exists, set null if not |
| Session management in nested queries | Detached objects | Use eager loading or pass session |

---

## Definition of Done Checklist

- [ ] Supplier export includes slug field
- [ ] Product export includes preferred_supplier_slug
- [ ] Product export includes preferred_supplier_name
- [ ] Null handling for products without suppliers
- [ ] Tests pass for all export scenarios
- [ ] `tasks.md` updated

---

## Review Guidance

**Key Checkpoints**:
1. Verify export JSON structure matches data-model.md
2. Confirm null handling for edge cases
3. Check that existing export tests still pass
4. Run: `./run-tests.sh src/tests/test_import_export.py -v`

---

## Activity Log

- 2026-01-12T23:45:00Z - system - lane=planned - Prompt created.
- 2026-01-13T05:06:52Z – claude – lane=doing – Starting export service updates
- 2026-01-13T05:11:11Z – claude – lane=for_review – All subtasks complete: supplier export includes slug/type/website_url, product export includes preferred_supplier_slug/name, null handling for deleted suppliers. 5/5 new tests passing.
- 2026-01-13T06:22:00Z – claude – shell_pid=59105 – lane=done – APPROVED. All 5 export tests pass. Supplier slug export, product supplier_slug export, null handling verified.
