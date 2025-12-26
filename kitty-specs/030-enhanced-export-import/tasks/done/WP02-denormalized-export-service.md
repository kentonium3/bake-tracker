---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
title: "Denormalized Export Service"
phase: "Phase 1 - Export Services"
lane: "done"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-25T14:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Denormalized Export Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Export AI-friendly denormalized views with context fields for external augmentation.

**Success Criteria**:
1. view_products.json includes ingredient name, category, supplier name, last purchase price, inventory quantity
2. view_inventory.json includes product details and purchase context
3. view_purchases.json includes product and supplier details
4. All views include _meta with editable_fields and readonly_fields arrays
5. Unit tests achieve >70% coverage

## Context & Constraints

**Owner**: Gemini (Track A - Export)

**References**:
- `kitty-specs/030-enhanced-export-import/spec.md`: FR-006 through FR-010, User Story 1
- `kitty-specs/030-enhanced-export-import/data-model.md`: Denormalized view schemas
- `src/services/import_export_service.py`: Existing export patterns with joinedload

**Constraints**:
- Views are read-only - no session modifications
- Use eager loading (joinedload) for performance
- Editable fields per spec: brand, product_name, package_size, package_unit, upc_code, notes

## Subtasks & Detailed Guidance

### Subtask T007 - Implement export_products_view()

**Purpose**: Export products with ingredient and supplier context for AI augmentation.

**Steps**:
1. Create `src/services/denormalized_export_service.py`
2. Implement `export_products_view(output_path: str, session: Session = None)`:
   ```python
   def export_products_view(output_path: str, session: Session = None) -> ExportResult:
       if session is not None:
           return _export_products_view_impl(output_path, session)
       with session_scope() as sess:
           return _export_products_view_impl(output_path, sess)
   ```
3. Query products with eager loading:
   ```python
   products = session.query(Product).options(
       joinedload(Product.ingredient),
   ).all()
   ```
4. For each product, aggregate:
   - All product fields
   - ingredient_slug, ingredient_name, ingredient_category
   - supplier_name (from most recent purchase)
   - last_purchase_price (from most recent purchase)
   - inventory_quantity (sum from inventory_items)

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: Yes (independent view)

### Subtask T008 - Implement export_inventory_view()

**Purpose**: Export inventory items with product and purchase context.

**Steps**:
1. Implement `export_inventory_view(output_path: str, session: Session = None)`
2. Query inventory items with eager loading:
   ```python
   items = session.query(InventoryItem).options(
       joinedload(InventoryItem.product).joinedload(Product.ingredient),
   ).all()
   ```
3. For each item, include:
   - All inventory fields
   - product_slug (brand + ingredient_slug)
   - product_name, brand, package_unit
   - ingredient_slug, ingredient_name
   - purchase_date, unit_cost (from associated purchase if available)

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: Yes (independent view)

### Subtask T009 - Implement export_purchases_view()

**Purpose**: Export purchases with product and supplier details.

**Steps**:
1. Implement `export_purchases_view(output_path: str, session: Session = None)`
2. Query purchases with eager loading:
   ```python
   purchases = session.query(Purchase).options(
       joinedload(Purchase.product).joinedload(Product.ingredient),
       joinedload(Purchase.supplier),
   ).all()
   ```
3. For each purchase, include:
   - All purchase fields
   - product_slug, product_name, brand
   - ingredient_slug, ingredient_name
   - supplier_name, supplier_city, supplier_state

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: Yes (independent view)

### Subtask T010 - Add editable/readonly field metadata

**Purpose**: Document which fields can be modified during import.

**Steps**:
1. Add _meta section to all view exports:
   ```python
   view_data = {
       "version": "1.0",
       "view_type": "products",
       "export_date": datetime.utcnow().isoformat() + "Z",
       "_meta": {
           "editable_fields": ["brand", "product_name", "package_size", "package_unit", "upc_code", "notes"],
           "readonly_fields": ["id", "ingredient_id", "ingredient_slug", "ingredient_name", "ingredient_category", "supplier_name", "last_purchase_price", "inventory_quantity"]
       },
       "records": [...]
   }
   ```
2. Define editable/readonly constants per view type
3. Inventory view editable: quantity, location, notes
4. Purchases view editable: notes (most fields are historical)

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: No (applies to all views)

### Subtask T011 - Write unit tests

**Purpose**: Verify denormalized export functionality.

**Steps**:
1. Create `src/tests/services/test_denormalized_export.py`
2. Test cases:
   - Export empty database (should create file with 0 records)
   - Export products view with sample data
   - Verify context fields present (ingredient_name, supplier_name)
   - Verify _meta.editable_fields and _meta.readonly_fields present
   - Verify all three view types export correctly
3. Use fixtures from existing test patterns

**Files**: `src/tests/services/test_denormalized_export.py`
**Parallel?**: No (after implementation)

## Test Strategy

- Unit tests for each view export function
- Verify context fields are populated correctly
- Verify _meta section format

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| N+1 queries | Use joinedload for all relationships |
| Missing relationships | Handle None gracefully in context fields |

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] view_products.json, view_inventory.json, view_purchases.json exports work
- [ ] All views include _meta with editable/readonly fields
- [ ] Context fields populated (ingredient_name, supplier_name, etc.)
- [ ] >70% test coverage on service
- [ ] tasks.md updated with status change

## Review Guidance

- Verify joinedload used for all relationships
- Verify _meta section present in all views
- Verify editable_fields matches spec requirements
- Verify None handling for missing relationships

## Activity Log

- 2025-12-25T14:00:00Z - system - lane=planned - Prompt created.
- 2025-12-26T03:48:04Z – system – shell_pid= – lane=done – Implementation complete by Gemini CLI, reviewed and tests pass
