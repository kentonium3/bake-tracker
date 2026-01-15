---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
title: "Service Layer New Exports"
phase: "Phase 1 - Service Layer"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-15T13:35:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Service Layer New Exports

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Add/expose `export_products_context_rich()` with proper field definitions
- Create `export_material_products_context_rich()` method
- Create `export_finished_units_context_rich()` method
- Create `export_finished_goods_context_rich()` method
- Each new export produces valid JSON with `_meta` section defining editable vs readonly fields
- Each new export includes relevant context from relationships

**Success**: After this WP, all 7 entity types have working context-rich export methods in the service layer.

## Context & Constraints

**File to modify**: `src/services/denormalized_export_service.py`

**Reference**:
- `kitty-specs/053-context-rich-export-fixes/plan.md` - Implementation approach
- `kitty-specs/053-context-rich-export-fixes/research.md` - Current implementation details
- `test_data/old_view_products.json` - Example Products export structure

**Pattern to follow**: Existing `export_ingredients_context_rich()` method structure

**Models**:
- `src/models/product.py` - Product model
- `src/models/material_product.py` - MaterialProduct model
- `src/models/finished_unit.py` - FinishedUnit model (yields from recipes)
- `src/models/finished_good.py` - FinishedGood model (assembled bundles)

## Subtasks & Detailed Guidance

### Subtask T005 - Expose Products Export

**Purpose**: Make Products export available with proper field definitions.

**Steps**:
1. Check if `export_products_context_rich()` already exists (it may from WP01 rename)
2. Ensure `PRODUCTS_CONTEXT_RICH_EDITABLE` constant defines:
   - brand, product_name, package_size, package_type, package_unit, package_unit_quantity
   - upc_code, gtin, notes, preferred, is_hidden
3. Ensure `PRODUCTS_CONTEXT_RICH_READONLY` constant defines:
   - id, uuid, ingredient_id, ingredient_slug, ingredient_name, ingredient_category
   - preferred_supplier_id, preferred_supplier_name
   - last_purchase_price, last_purchase_date, inventory_quantity
   - date_added, last_modified
4. Verify method produces JSON matching `test_data/old_view_products.json` structure

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: Yes

**Reference structure**:
```json
{
  "version": "1.0",
  "export_type": "products",
  "export_date": "ISO timestamp",
  "_meta": {
    "editable_fields": [...],
    "readonly_fields": [...]
  },
  "records": [...]
}
```

### Subtask T006 - Create Material Products Export

**Purpose**: Enable context-rich export for Material Products (materials with brand/supplier info).

**Steps**:
1. Define `MATERIAL_PRODUCTS_CONTEXT_RICH_EDITABLE` constant:
   - brand, product_name, package_info fields, notes, preferred
2. Define `MATERIAL_PRODUCTS_CONTEXT_RICH_READONLY` constant:
   - id, uuid, material_id, material_slug, material_name
   - material_category, material_subcategory (if hierarchy exists)
   - supplier context, inventory context, purchase context
3. Create `export_material_products_context_rich()` method:
   - Query MaterialProduct with eager loading
   - Build denormalized records with context
   - Follow Products pattern exactly

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: Yes

**Notes**: Study the Material Products model relationships to determine available context fields.

### Subtask T007 - Create Finished Units Export

**Purpose**: Enable context-rich export for Finished Units (yields from recipe production).

**Steps**:
1. Define `FINISHED_UNITS_CONTEXT_RICH_EDITABLE` constant:
   - name, description, yield-related fields, notes
2. Define `FINISHED_UNITS_CONTEXT_RICH_READONLY` constant:
   - id, uuid, recipe_id, recipe_slug, recipe_name
   - yield_quantity, yield_unit
   - production context if available
3. Create `export_finished_units_context_rich()` method:
   - Query FinishedUnit with eager loading of recipe relationship
   - Include recipe context (name, category, etc.)
   - Follow established pattern

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: Yes

**Notes**: Review FinishedUnit model to understand its relationship to Recipe.

### Subtask T008 - Create Finished Goods Export

**Purpose**: Enable context-rich export for Finished Goods (assembled bundles/packages).

**Steps**:
1. Define `FINISHED_GOODS_CONTEXT_RICH_EDITABLE` constant:
   - name, description, package-related fields, notes
2. Define `FINISHED_GOODS_CONTEXT_RICH_READONLY` constant:
   - id, uuid, component references
   - assembly context, recipe references
   - production/assembly run context if available
3. Create `export_finished_goods_context_rich()` method:
   - Query FinishedGood with eager loading
   - Include component/assembly context
   - Follow established pattern

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: Yes

**Notes**: Review FinishedGood model to understand its composition and relationships.

## Standard Export Method Pattern

Each new export method should follow this pattern:

```python
def export_<entity>_context_rich(self, output_dir: Path = None) -> ExportResult:
    """Export <entity> with context for AI augmentation."""
    with session_scope() as session:
        items = session.query(<Model>).options(
            # eager load relationships
        ).all()

        records = []
        for item in items:
            record = {
                # entity fields
                # context fields from relationships
            }
            records.append(record)

        output = {
            "version": "1.0",
            "export_type": "<entity>",
            "export_date": datetime.utcnow().isoformat() + "Z",
            "_meta": {
                "editable_fields": <ENTITY>_CONTEXT_RICH_EDITABLE,
                "readonly_fields": <ENTITY>_CONTEXT_RICH_READONLY
            },
            "records": records
        }

        # Write to file
        filename = f"aug_<entity>.json"
        # ... file writing logic

        return ExportResult(count=len(records), path=output_path)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing model relationships | Read model files first to understand available relationships |
| Inconsistent JSON structure | Follow existing patterns exactly, compare output structure |
| Missing context fields | Review what context is useful for AI augmentation |

## Definition of Done Checklist

- [ ] `export_products_context_rich()` produces valid JSON with proper fields
- [ ] `export_material_products_context_rich()` created and produces valid JSON
- [ ] `export_finished_units_context_rich()` created and produces valid JSON
- [ ] `export_finished_goods_context_rich()` created and produces valid JSON
- [ ] All exports use `aug_` file prefix
- [ ] All exports include `_meta` section with editable/readonly field definitions
- [ ] All exports follow consistent JSON structure

## Review Guidance

- Verify each new export method follows the established pattern
- Check that `_meta` fields accurately reflect what should be editable vs readonly
- Test each export produces valid JSON
- Verify relationships are eager-loaded to avoid N+1 queries

## Activity Log

- 2026-01-15T13:35:00Z - system - lane=planned - Prompt created.
- 2026-01-15T19:11:33Z – unknown – lane=doing – Starting WP02 implementation
- 2026-01-15T19:16:20Z – claude – lane=for_review – Implemented T005-T008: Products export verified, Material Products/Finished Units/Finished Goods exports created with proper field definitions and export_all updated
- 2026-01-15T21:10:40Z – claude – lane=doing – Started review via workflow command
- 2026-01-15T21:11:33Z – claude – lane=done – Review passed: All 4 new export methods created with proper field definitions, _meta sections, and aug_ prefix
