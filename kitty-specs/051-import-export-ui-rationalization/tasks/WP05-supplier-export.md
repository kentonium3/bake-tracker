---
work_package_id: "WP05"
subtasks:
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
title: "Supplier Export"
phase: "Phase 0 - Foundational"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-13T12:55:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Supplier Export

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Add supplier export capability to the Export Data dialog Catalog tab.

**Success Criteria**:
- `export_suppliers()` function exists in import_export_service
- Suppliers checkbox appears in ExportDialog Catalog tab
- Export produces JSON with supplier data including slug field (F050 format)
- Suppliers can be included in multi-entity exports

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/051-import-export-ui-rationalization/spec.md` (US2 - Supplier Import/Export)
- Plan: `kitty-specs/051-import-export-ui-rationalization/plan.md`

**Dependencies**:
- None (independent work package)

**Existing Patterns**:
- `src/services/import_export_service.py` - export_ingredients_to_json(), export_recipes_to_json()
- `src/ui/import_export_dialog.py:849-896` - ExportDialog._setup_catalog_tab()

**Feature 050 Context**:
- Supplier model now has `slug` field
- `generate_supplier_slug()` in `src/services/supplier_service.py`

## Subtasks & Detailed Guidance

### Subtask T032 - Add export_suppliers() function
- **Purpose**: Export suppliers to JSON format
- **Steps**:
  1. Add `export_suppliers_to_json(file_path, ...)` to `src/services/import_export_service.py`
  2. Query all suppliers from database
  3. Build export data with version, export_date, source headers
  4. Map each supplier to dict with fields: `name`, `slug`, `contact_info`, `notes`
  5. Return ExportResult with file_path and record_count
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: No (establishes pattern)
- **Notes**: Follow existing export_ingredients_to_json() pattern exactly

### Subtask T033 - Include slug field in export
- **Purpose**: Ensure F050 slug field is exported for portability
- **Steps**:
  1. Verify Supplier model has `slug` attribute
  2. Include `supplier.slug` in export dict
  3. Generate slug if somehow missing: `generate_supplier_slug(supplier.name)`
  4. Test that exported JSON contains slug for each supplier
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: No (part of T032)
- **Notes**: Slug is required for import to another instance

### Subtask T034 - Update export_all_to_json() to include suppliers
- **Purpose**: Enable suppliers in multi-entity exports
- **Steps**:
  1. Find `export_all_to_json()` or equivalent batch export function
  2. Add `suppliers` to the list of exportable entities
  3. If `suppliers` in selected entities, call export_suppliers_to_json()
  4. Update entity_counts in result
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: No (after T032)
- **Notes**: Check existing implementation for entity list handling

### Subtask T035 - Add Suppliers checkbox to ExportDialog Catalog tab
- **Purpose**: UI for selecting suppliers in export
- **Steps**:
  1. Open `src/ui/import_export_dialog.py`, find `_setup_catalog_tab()`
  2. Current entities: Ingredients, Products, Recipes, Materials, Material Products
  3. Add `("suppliers", "Suppliers")` to entities list
  4. Position alphabetically: ..., Materials, Material Products, Products, Recipes, Suppliers
  5. Actually: Ingredients, Materials, Material Products, Products, Recipes, Suppliers (verify order)
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (after service work)
- **Notes**: Checkbox variable: `self.entity_vars["suppliers"]`

### Subtask T036 - Wire checkbox to export logic
- **Purpose**: Connect UI to service layer
- **Steps**:
  1. Verify `_export_catalog()` method reads from `self.entity_vars`
  2. Ensure `suppliers` key is passed to export function when checked
  3. Test export with only Suppliers selected
  4. Test export with Suppliers + other entities selected
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (final integration)
- **Notes**: May need no changes if entity_vars pattern is generic

## Expected JSON Format

```json
{
  "version": "4.0",
  "export_date": "2026-01-13T10:00:00Z",
  "source": "Bake Tracker v0.7.0",
  "suppliers": [
    {
      "name": "Costco",
      "slug": "costco",
      "contact_info": "membership required",
      "notes": "Bulk purchases"
    },
    {
      "name": "Local Farm",
      "slug": "local-farm",
      "contact_info": "Farmers market Saturdays",
      "notes": ""
    }
  ]
}
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Supplier model missing slug | Feature 050 added it; verify in model file |
| Export function doesn't exist | May need to create or find equivalent |
| Alphabetical ordering changes | Document expected order; verify visually |

## Definition of Done Checklist

- [ ] `export_suppliers_to_json()` function exists
- [ ] Exported JSON includes all supplier fields including `slug`
- [ ] `export_all_to_json()` supports suppliers entity
- [ ] Suppliers checkbox appears in ExportDialog Catalog tab
- [ ] Checkbox is alphabetically positioned
- [ ] Export with Suppliers checkbox produces valid JSON
- [ ] Manual test: export suppliers, verify file contains expected data

## Review Guidance

**Key checkpoints**:
1. Open Export Data dialog, Catalog tab
2. Verify "Suppliers" checkbox exists and is alphabetically positioned
3. Export with only Suppliers selected
4. Verify JSON file has correct format with slug field
5. Export with Suppliers + Ingredients, verify both in output

## Activity Log

- 2026-01-13T12:55:00Z - system - lane=planned - Prompt created.
- 2026-01-13T18:55:55Z – claude – lane=doing – Starting implementation of Supplier Export
- 2026-01-13T18:58:55Z – claude – lane=for_review – Implemented selective entity export with suppliers support (export already existed, added entities filter)
- 2026-01-13T20:57:06Z – claude – lane=done – Code review APPROVED by claude - Suppliers checkbox in export dialog, alphabetically positioned, slug field included in export
