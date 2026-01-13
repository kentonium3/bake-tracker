---
work_package_id: "WP06"
subtasks:
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
  - "T042"
title: "Supplier Import"
phase: "Phase 1 - Dependent Services"
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

# Work Package Prompt: WP06 - Supplier Import

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Add supplier import capability to the Import Data dialog Catalog purpose.

**Success Criteria**:
- Suppliers recognized as valid entity in catalog_import_service
- `import_suppliers()` function processes supplier records
- Auto-detection recognizes files with suppliers array
- Suppliers import before products (dependency ordering)
- Slug uniqueness validated during import

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/051-import-export-ui-rationalization/spec.md` (US2 - Supplier Import/Export)
- Plan: `kitty-specs/051-import-export-ui-rationalization/plan.md`

**Dependencies**:
- WP05 (supplier export) for round-trip testing

**Existing Patterns**:
- `src/services/catalog_import_service.py` - VALID_ENTITIES, import_ingredients(), import_products()
- `src/services/enhanced_import_service.py` - detect_format(), FormatDetectionResult
- `src/services/supplier_service.py` - generate_supplier_slug()

## Subtasks & Detailed Guidance

### Subtask T037 - Add suppliers to VALID_ENTITIES
- **Purpose**: Enable suppliers in catalog import
- **Steps**:
  1. Open `src/services/catalog_import_service.py`
  2. Find `VALID_ENTITIES` list or equivalent
  3. Add `"suppliers"` to the list
  4. Position before "products" (dependency order matters)
- **Files**: `src/services/catalog_import_service.py`
- **Parallel?**: No (foundation)
- **Notes**: Order should be: suppliers, ingredients, products, materials, ...

### Subtask T038 - Add import_suppliers() function
- **Purpose**: Process supplier records from JSON
- **Steps**:
  1. Add `import_suppliers(suppliers_data, mode, result)` function
  2. Follow existing import_ingredients() pattern:
     - Iterate over supplier records
     - For each: lookup by slug or name
     - If exists: skip (add mode) or augment (augment mode)
     - If new: create supplier record
     - Track counts in result
  3. Handle both "merge" and "skip_existing" modes
  4. Generate slug if not provided using `generate_supplier_slug(name)`
- **Files**: `src/services/catalog_import_service.py`
- **Parallel?**: No (after T037)
- **Notes**: Supplier fields: name (required), slug, contact_info, notes

### Subtask T039 - Update import dependency order
- **Purpose**: Ensure suppliers import before products (FK requirement)
- **Steps**:
  1. Find entity processing loop in catalog import
  2. Ensure order is: suppliers → ingredients → products → materials → material_products → recipes
  3. This matters because products may reference suppliers via supplier_slug FK
  4. Test multi-entity import with suppliers and products
- **Files**: `src/services/catalog_import_service.py`
- **Parallel?**: No (after T038)
- **Notes**: Products have `supplier_slug` FK; must import suppliers first

### Subtask T040 - Update detect_format() in enhanced_import_service
- **Purpose**: Recognize supplier files during auto-detection
- **Steps**:
  1. Open `src/services/enhanced_import_service.py`
  2. Find `_detect_format_from_data()` function
  3. Add detection for suppliers array:
     - If `"suppliers"` key exists in data
     - Set appropriate format_type
     - Count records in suppliers array
  4. Handle single-entity supplier file and multi-entity file
- **Files**: `src/services/enhanced_import_service.py`
- **Parallel?**: Yes (independent of T037-T039)
- **Notes**: Return FormatDetectionResult with supplier count

### Subtask T041 - Update detection display for suppliers
- **Purpose**: Show supplier count in ImportDialog detection message
- **Steps**:
  1. Verify `FormatDetectionResult.summary` includes supplier info
  2. If multi-entity, detection should show: "Multiple entities: Suppliers (6), Ingredients (45), ..."
  3. Update display logic in ImportDialog._detect_format() if needed
- **Files**: `src/ui/import_export_dialog.py`, `src/services/enhanced_import_service.py`
- **Parallel?**: Yes (after T040)
- **Notes**: Detection label shows record counts per entity

### Subtask T042 - Validate supplier slug uniqueness
- **Purpose**: Prevent duplicate slug conflicts
- **Steps**:
  1. Before creating supplier, check if slug already exists
  2. If slug collision with different name: add error with suggestion
  3. If same name already exists: skip (add mode) or update (augment)
  4. Generate unique slug if needed: append suffix
  5. Include clear error message for conflicts
- **Files**: `src/services/catalog_import_service.py`
- **Parallel?**: No (part of T038 implementation)
- **Notes**: Slug must be unique; name can potentially duplicate but slug cannot

## Expected Import Behavior

| Scenario | Mode: Add Only | Mode: Augment |
|----------|----------------|---------------|
| New supplier | Create | Create |
| Existing (same slug) | Skip | Update empty fields |
| Slug collision | Error | Error |
| Missing slug in JSON | Generate from name | Generate from name |

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Slug collision with existing | Generate unique slug or error with suggestion |
| Import order breaks FKs | Ensure suppliers first in processing order |
| Missing supplier breaks product import | Clear error message pointing to missing supplier |

## Definition of Done Checklist

- [ ] `suppliers` in VALID_ENTITIES
- [ ] `import_suppliers()` function handles add and augment modes
- [ ] Import order: suppliers before products
- [ ] detect_format() recognizes supplier files
- [ ] Detection display shows supplier record count
- [ ] Slug uniqueness validated with clear errors
- [ ] Round-trip test: export from WP05, import here, verify data matches

## Review Guidance

**Key checkpoints**:
1. Import suppliers.json file, verify all records created
2. Re-import same file with "Add Only" mode, verify skip message
3. Import multi-entity file (suppliers + products), verify order
4. Test slug collision scenario, verify clear error
5. Round-trip: export suppliers, import to fresh DB, compare

## Activity Log

- 2026-01-13T12:55:00Z - system - lane=planned - Prompt created.
- 2026-01-13T19:17:38Z – claude – lane=doing – Starting implementation of Supplier Import
- 2026-01-13T19:21:51Z – claude – lane=for_review – Implemented supplier import with ADD_ONLY and AUGMENT modes, slug uniqueness validation, and proper dependency ordering
- 2026-01-13T20:57:14Z – claude – lane=done – Code review APPROVED by claude - Supplier import with ADD_ONLY/AUGMENT modes, slug uniqueness validation, proper dependency ordering
