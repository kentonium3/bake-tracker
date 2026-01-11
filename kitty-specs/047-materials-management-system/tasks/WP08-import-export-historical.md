---
work_package_id: "WP08"
subtasks:
  - "T055"
  - "T056"
  - "T057"
  - "T058"
  - "T059"
  - "T060"
  - "T061"
title: "Import/Export & Historical - User Stories 7 & 8"
phase: "Phase 3 - Polish"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - Import/Export & Historical - User Stories 7 & 8

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Extend import/export for materials; implement historical query support.

**User Stories:**
- US7: As a baker, I want to see what materials I used in past assemblies even if catalog data has changed
- US8: As a baker, I need to import and export my materials catalog for backup and data transfer

**Success Criteria:**
- Export includes all material hierarchy, products, units, and purchases
- Import recreates material catalog with relationships intact
- Historical queries return snapshot data (original names at assembly time)
- Import/export round-trip preserves all data without loss

## Context & Constraints

**Reference Documents:**
- `kitty-specs/047-materials-management-system/spec.md` - User Stories 7 & 8
- `src/services/catalog_import_service.py` - Existing import service
- `src/services/coordinated_export_service.py` - Existing export service
- Existing import/export format (v4.x)

**Import Order (dependency-based):**
1. material_categories
2. material_subcategories
3. materials
4. material_products
5. material_units
6. material_purchases (optional - view data only)

**Dependencies:**
- WP06 (MaterialConsumption must exist for history queries)

## Subtasks & Detailed Guidance

### Subtask T055 - Extend catalog_import_service for Materials
- **Purpose**: Import material catalog from JSON
- **File**: `src/services/catalog_import_service.py`
- **Parallel?**: No
- **Steps**:
  1. Add import functions:
     - `_import_material_categories(data, session)`
     - `_import_material_subcategories(data, session)`
     - `_import_materials(data, session)`
     - `_import_material_products(data, session)`
     - `_import_material_units(data, session)`
  2. Follow existing patterns for supplier resolution
  3. Handle foreign key resolution (category -> subcategory -> material -> product)
  4. Validate required fields, report clear errors for missing data
  5. Update main import function to call material importers

### Subtask T056 - Extend coordinated_export_service for Materials
- **Purpose**: Export material catalog to JSON
- **File**: `src/services/coordinated_export_service.py`
- **Parallel?**: No
- **Steps**:
  1. Add export functions:
     - `_export_material_categories(session)`
     - `_export_material_subcategories(session)`
     - `_export_materials(session)`
     - `_export_material_products(session)`
     - `_export_material_units(session)`
  2. Follow existing patterns for data formatting
  3. Include all fields needed for re-import
  4. Update main export function to include material sections

### Subtask T057 - Define Import/Export Format Extension
- **Purpose**: Document format for material data
- **File**: `docs/import_export_format.md` (or inline documentation)
- **Parallel?**: No
- **Steps**:
  1. Define JSON structure for each material entity:
     ```json
     {
       "material_categories": [
         {"name": "Ribbons", "slug": "ribbons", "description": null, "sort_order": 0}
       ],
       "material_subcategories": [
         {"category_slug": "ribbons", "name": "Satin", "slug": "satin", ...}
       ],
       "materials": [
         {"subcategory_slug": "satin", "name": "Red Satin", "base_unit_type": "linear_inches", ...}
       ],
       "material_products": [
         {"material_slug": "red-satin", "name": "Michaels 100ft Roll", "supplier_slug": "michaels", ...}
       ],
       "material_units": [
         {"material_slug": "red-satin", "name": "6-inch ribbon", "quantity_per_unit": 6, ...}
       ]
     }
     ```
  2. Use slugs for foreign key references (not IDs)
  3. Document required vs optional fields

### Subtask T058 - Implement get_consumption_history() Query
- **Purpose**: Query historical material consumption with snapshot data
- **File**: `src/services/material_consumption_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `get_consumption_history(material_id=None, product_id=None, from_date=None, to_date=None, session=None)`
  2. Query MaterialConsumption records
  3. Return snapshot fields (NOT current catalog data):
     ```python
     {
         'consumption_id': int,
         'assembly_run_id': int,
         'assembly_date': datetime,
         'quantity_consumed': float,
         'unit_cost': Decimal,
         'total_cost': Decimal,
         # Snapshot fields - values at time of consumption
         'product_name': str,
         'material_name': str,
         'subcategory_name': str,
         'category_name': str,
         'supplier_name': str | None
     }
     ```
  4. Filter by material_id, product_id, date range as provided

### Subtask T059 - Update Assembly Detail Views for Material Snapshots
- **Purpose**: Show historical material data in assembly details
- **File**: UI integration (existing assembly detail views)
- **Parallel?**: No
- **Steps**:
  1. Find existing assembly detail view
  2. Add "Materials Used" section
  3. Query MaterialConsumption for the assembly_run_id
  4. Display snapshot fields (product_name, material_name, etc.)
  5. Show total material cost for the assembly

### Subtask T060 - Add Import/Export Tests for Materials
- **Purpose**: Verify round-trip data integrity
- **File**: `src/tests/test_import_export_materials.py`
- **Parallel?**: Yes
- **Steps**:
  1. Create test material catalog (hierarchy with products and units)
  2. Export to JSON
  3. Clear database (or use separate test DB)
  4. Import from JSON
  5. Verify all relationships intact
  6. Verify no data loss (counts match, values match)
  7. Test error handling for missing supplier references

### Subtask T061 - Add Historical Query Tests
- **Purpose**: Verify snapshot data preserved
- **File**: `src/tests/test_material_consumption_history.py`
- **Parallel?**: Yes
- **Steps**:
  1. Create product with specific name
  2. Record assembly with material consumption
  3. Rename product in catalog
  4. Query consumption history
  5. Verify snapshot shows ORIGINAL name, not current name
  6. Test date range filtering

## Test Strategy

```python
import pytest
from src.services.coordinated_export_service import export_catalog
from src.services.catalog_import_service import import_catalog
from src.services.material_consumption_service import get_consumption_history

def test_import_export_roundtrip(db_session, full_material_catalog):
    """Export and re-import preserves all material data."""
    # Export
    export_data = export_catalog(session=db_session)
    assert 'material_categories' in export_data
    assert len(export_data['material_categories']) > 0

    # Clear and re-import
    # ... (use separate test session or clear tables)
    import_catalog(export_data, session=db_session)

    # Verify counts match
    assert count_material_categories(session=db_session) == len(export_data['material_categories'])

def test_historical_snapshot_preserved(db_session, assembly_with_materials):
    """Snapshot names preserved after catalog rename."""
    # Get original product name from consumption
    history = get_consumption_history(
        assembly_run_id=assembly_with_materials.id,
        session=db_session
    )
    original_name = history[0]['product_name']

    # Rename the product
    rename_product(history[0]['product_id'], "New Product Name", session=db_session)

    # Query history again
    history_after = get_consumption_history(
        assembly_run_id=assembly_with_materials.id,
        session=db_session
    )

    # Snapshot should show ORIGINAL name
    assert history_after[0]['product_name'] == original_name
    assert history_after[0]['product_name'] != "New Product Name"
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Foreign key resolution during import | Use slugs, validate in dependency order |
| Missing supplier during import | Clear error message, fail import for that item |
| Large export files | Test with realistic data volumes |
| Snapshot vs current data confusion | Clear documentation, consistent naming |

## Definition of Done Checklist

- [ ] Export includes all material entities
- [ ] Import recreates catalog with relationships
- [ ] Slug-based foreign key resolution works
- [ ] Historical queries return snapshot data
- [ ] Assembly details show material consumption history
- [ ] Round-trip test passes with no data loss
- [ ] Snapshot preserved after catalog rename
- [ ] Error handling for invalid import data

## Review Guidance

**Reviewer should verify:**
1. Import order respects foreign key dependencies
2. Export uses slugs (not IDs) for references
3. Historical queries use snapshot fields, NOT joins to current catalog
4. Error messages for import failures are actionable

## Activity Log

- 2026-01-10T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-10T22:38:13Z – claude – lane=doing – Starting Import/Export Historical implementation
- 2026-01-10T22:57:06Z – claude – lane=for_review – WP08 Import/Export Historical complete - all tests passing
- 2026-01-11T01:06:59Z – claude – lane=done – Review passed: Import/export extended for materials, MaterialPurchase export added, historical snapshot queries working.
