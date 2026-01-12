# Research: Import/Export System Phase 1

**Feature**: 049-import-export-phase1
**Date**: 2026-01-12
**Status**: Complete

## 1. Existing Service Architecture

### Current Services

| Service | Purpose | Lines | Key Functions |
|---------|---------|-------|---------------|
| `import_export_service.py` | Main import/export with ImportResult | ~800 | `import_all_from_json_v4()`, `export_all_to_json_v4()` |
| `coordinated_export_service.py` | Multi-file export with manifest | ~400 | `export_complete()`, per-entity exporters |
| `catalog_import_service.py` | Catalog import (ADD_ONLY/AUGMENT) | ~300 | `import_catalog()` |
| `denormalized_export_service.py` | Context-rich view exports | ~500 | `export_products_view()`, `export_inventory_view()` |
| `enhanced_import_service.py` | Enhanced import with FK resolution | ~400 | `import_view()` |

### Decision: Extend vs New Services

**Decision**: Extend existing services
**Rationale**:
- Maintains consistency with established patterns
- Reduces duplicate code and maintenance burden
- Leverages existing ImportResult/ExportResult infrastructure
- Follows constitution principle V (layered architecture)

**Alternative Rejected**: Creating parallel import_export_v4_service.py
- Would duplicate infrastructure (result classes, error handling)
- Would create confusion about which service to use
- Would require coordinating two services for related operations

## 2. Full Backup Entity Coverage

### Current State (12 entities)

The coordinated_export_service currently exports:
1. suppliers
2. ingredients
3. products
4. recipes (with recipe_ingredients, recipe_components)
5. purchases
6. inventory_items
7. material_categories
8. material_subcategories
9. materials
10. material_products
11. material_units
12. material_purchases

### Missing Entities (4 to add)

| Entity | Dependencies | Import Order |
|--------|--------------|--------------|
| finished_goods | None | 13 |
| events | None | 14 |
| production_runs | recipes, events (optional) | 15 |
| inventory_depletions | recipes, inventory_items | 16 |

### Decision: Manifest Format

**Decision**: Extend existing manifest format with new entities
**Rationale**:
- Manifest version stays at 1.0 (backward compatible addition)
- New entities added to `DEPENDENCY_ORDER` constant
- Existing import logic handles new entities automatically

## 3. Materials Catalog Import

### Current Ingredient Import Pattern

```python
# catalog_import_service.py pattern:
1. Read JSON with ingredients array
2. For each ingredient:
   a. Check if slug exists
   b. If ADD_ONLY: skip if exists
   c. If AUGMENT: update null fields if exists
   d. Create if not exists
3. Return ImportResult with counts
```

### Decision: Replicate Pattern for Materials

**Decision**: Exact pattern replication for materials
**Rationale**:
- Success criterion SC-013 requires pattern match
- Reduces learning curve for future maintainers
- Ensures consistent behavior for users

**Implementation Details**:
- Add `import_materials()` function following `import_ingredients()` structure
- Add `import_material_products()` with slug resolution
- Support same modes: ADD_ONLY, AUGMENT
- Same error handling and result reporting

## 4. Context-Rich Export Design

### Existing view_products.json Structure

```json
{
  "view_type": "products",
  "export_date": "2025-12-24T12:00:00Z",
  "record_count": 152,
  "_meta": {
    "editable_fields": ["brand", "product_name", ...],
    "readonly_fields": ["id", "ingredient_slug", "inventory_quantity", ...]
  },
  "records": [...]
}
```

### Decision: Consistent View Structure

**Decision**: All context-rich exports follow same structure with `_meta` section
**Rationale**:
- Enables auto-detection based on `_meta` presence
- Self-documenting for AI augmentation workflows
- Consistent processing for import

### New Views to Add

**export_ingredients_view()**:
- Editable: description, notes, density fields
- Readonly: slug, category_hierarchy_path, product_count, total_inventory

**export_materials_view()**:
- Editable: description, notes
- Readonly: slug, category_hierarchy_path, product_count

**export_recipes_view()**:
- Editable: instructions, notes, prep_time, cook_time
- Readonly: slug, ingredient_list (embedded), computed_cost, yield_info

## 5. Transaction Import Design

### Purchase Import

**Decision**: Create dedicated transaction_import_service.py
**Rationale**:
- Transaction imports are fundamentally different from catalog imports
- Catalog imports are idempotent; transaction imports are not
- Separate service provides clear separation of concerns

**Key Validations**:
1. Positive quantity (FR-016)
2. Product slug exists
3. Duplicate detection: (product_slug, date, cost) combination

**Side Effects**:
1. Create Purchase record
2. Create InventoryItem record
3. Recalculate weighted average cost

### Adjustment Import

**Decision**: Same service as purchase import (transaction_import_service.py)
**Rationale**:
- Both are transaction imports (non-catalog)
- Share validation infrastructure
- Logically grouped

**Key Validations**:
1. Negative quantity only (FR-020)
2. Reason code required from allowed list (FR-021)
3. Cannot create negative inventory (FR-022)

**Allowed Reason Codes**:
- spoilage
- waste
- correction
- other

## 6. Format Auto-Detection

### Detection Algorithm

**Decision**: Detect based on `_meta` field presence
**Rationale**:
- Simple, reliable detection
- Context-rich always has `_meta` with editable_fields
- Normalized never has `_meta`

```python
def detect_format(data: dict) -> str:
    if "_meta" in data and "editable_fields" in data.get("_meta", {}):
        return "context_rich"
    if "version" in data and "application" in data:
        return "normalized"
    return "unknown"
```

### Import Type Detection

For transaction imports, detect based on `import_type` field:
- `import_type: "purchases"` → Purchase import
- `import_type: "inventory_updates"` or `"adjustments"` → Adjustment import
- No `import_type` + catalog entities → Catalog import
- No `import_type` + full entities → Full backup restore

## 7. UI Redesign

### Export Dialog Structure

**Decision**: Tabbed interface with 3 export types
**Rationale**:
- Clear visual separation
- Purpose explanation for each type
- Matches user mental model

```
┌─ Export ───────────────────────────────────────────┐
│                                                     │
│  [Full Backup] [Catalog] [Context-Rich]            │
│                                                     │
│  ═══════════════════════════════════════════       │
│                                                     │
│  Purpose: Create complete system backup             │
│           for disaster recovery or migration.       │
│                                                     │
│  Includes: All 16 entity types                     │
│                                                     │
│  [Export Full Backup...]                           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Import Dialog Structure

**Decision**: Step-based wizard with format confirmation
**Rationale**:
- User selects file first
- System auto-detects format
- User confirms before proceeding

Steps:
1. Select file
2. Show detected format with confirmation
3. Select import mode (if applicable)
4. Import with progress
5. Show results

## 8. Error Handling Strategy

### Decision: Fail-Fast with Rollback

**Decision**: Atomic transactions with clear error messages
**Rationale**:
- Constitution principle II: Data Integrity
- User needs actionable feedback
- Partial imports create inconsistent state

**Error Message Format**:
```
Import failed: [Entity] '[name]' - [reason]
Suggestion: [actionable fix]

Example:
Import failed: material_product 'kraft_box_large' - material 'kraft_boxes' not found
Suggestion: Ensure 'kraft_boxes' exists in materials import or database before importing material_products
```

## 9. Testing Strategy

### Unit Test Coverage

Each work package includes its own unit tests:
- Happy path
- Edge cases (empty arrays, zero counts)
- Error cases (missing references, invalid values)

### Integration Test Scenarios

1. **Round-trip**: Export all → Reset DB → Import → Verify counts match
2. **Context-rich round-trip**: Export view → Modify editable → Import → Verify changes
3. **Transaction import**: Import purchases → Verify inventory increased
4. **Error recovery**: Import with errors → Verify rollback complete

## 10. Parallel Work Safety

### File Boundaries

Strict file ownership prevents merge conflicts:

| Agent | Owns | Must Not Touch |
|-------|------|----------------|
| Claude | enhanced_import_service.py | catalog_import_service.py (Gemini) |
| Gemini-WP2 | catalog_import_service.py | import_export_service.py |
| Gemini-WP3 | denormalized_export_service.py | coordinated_export_service.py |
| Gemini-WP4/5 | transaction_import_service.py (NEW) | Other services |
| Gemini-WP7 | ui/dialogs/import_export_dialog.py | Service layer |

### Shared Dependencies

ImportResult and ExportResult classes are NOT modified - all WPs use existing interfaces.
