---
work_package_id: "WP08"
subtasks:
  - "T033"
  - "T034"
  - "T035"
title: "Import/Export Schema Handling"
phase: "Phase 4 - Polish"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP02"]
history:
  - timestamp: "2026-01-18T18:06:18Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 – Import/Export Schema Handling

## Implementation Command

```bash
spec-kitty implement WP08 --base WP02
```

## Objectives & Success Criteria

Update import/export service to handle deprecated MaterialProduct fields gracefully.

**Success Criteria**:
- Export excludes current_inventory and weighted_avg_cost
- Import ignores these fields if present in old files
- Backward compatibility maintained with old export files
- Roundtrip test passes

## Context & Constraints

**Reference Documents**:
- `kitty-specs/058-materials-fifo-foundation/research.md` - Pattern 6: Import/Export
- `kitty-specs/058-materials-fifo-foundation/spec.md` - User Story 5
- `src/services/import_export_service.py` - Current implementation

**Key Constraints**:
- Must maintain backward compatibility with old export files
- Must not fail on unknown fields during import
- Export should produce clean files without deprecated fields

## Subtasks & Detailed Guidance

### Subtask T033 – Update MaterialProduct export to exclude deprecated fields

**Purpose**: Ensure exports don't include fields that no longer exist in the model.

**Steps**:
1. Open `src/services/import_export_service.py`
2. Find the function that exports MaterialProduct data (likely in an export section)
3. Add exclusion filter:

```python
# Define excluded fields for MaterialProduct
MATERIAL_PRODUCT_EXCLUDED_FIELDS = {"current_inventory", "weighted_avg_cost", "inventory_value"}

# In the export function for material products
def _export_material_products(session) -> List[Dict]:
    """Export material products, excluding deprecated fields."""
    products = session.query(MaterialProduct).all()
    result = []
    for product in products:
        product_data = product.to_dict()
        # Remove deprecated fields
        for field in MATERIAL_PRODUCT_EXCLUDED_FIELDS:
            product_data.pop(field, None)
        result.append(product_data)
    return result
```

4. Alternatively, if using a centralized export pattern, add to the exclusion logic:
```python
def _filter_deprecated_fields(entity_type: str, data: dict) -> dict:
    """Remove deprecated fields based on entity type."""
    if entity_type == "material_products":
        excluded = {"current_inventory", "weighted_avg_cost", "inventory_value"}
        return {k: v for k, v in data.items() if k not in excluded}
    return data
```

**Files**:
- Edit: `src/services/import_export_service.py`

**Parallel?**: Yes (can be done alongside T034)

**Notes**:
- Check if to_dict() in MaterialProduct still includes these (it shouldn't after WP02)
- This is a safety filter in case any code path still produces these fields

### Subtask T034 – Update MaterialProduct import to ignore deprecated fields

**Purpose**: Allow old export files to import without errors.

**Steps**:
1. In `src/services/import_export_service.py`, find the MaterialProduct import function
2. Add filter to ignore deprecated fields before validation/creation:

```python
# Define ignored fields for MaterialProduct import
MATERIAL_PRODUCT_IGNORED_IMPORT_FIELDS = {"current_inventory", "weighted_avg_cost", "inventory_value"}

# In the import function for material products
def _import_material_product(data: dict, session) -> ImportResult:
    """Import a material product, ignoring deprecated fields."""
    # Clean deprecated fields from input
    clean_data = {
        k: v for k, v in data.items()
        if k not in MATERIAL_PRODUCT_IGNORED_IMPORT_FIELDS
    }

    # Proceed with import using clean_data
    # ... rest of import logic
```

3. Add logging/warning when deprecated fields are encountered:
```python
import logging
logger = logging.getLogger(__name__)

# In import function
deprecated_found = set(data.keys()) & MATERIAL_PRODUCT_IGNORED_IMPORT_FIELDS
if deprecated_found:
    logger.info(f"Ignoring deprecated fields in MaterialProduct import: {deprecated_found}")
```

**Files**:
- Edit: `src/services/import_export_service.py`

**Parallel?**: Yes (can be done alongside T033)

**Notes**:
- Don't fail on deprecated fields - just ignore them
- Log a message for debugging/audit purposes

### Subtask T035 – Add import/export roundtrip tests

**Purpose**: Verify export→import cycle works correctly with new schema.

**Steps**:
1. Create or update test file:

```python
"""Tests for material product import/export with FIFO schema changes."""

import pytest
import json
from decimal import Decimal

from src.services.database import session_scope
from src.services.import_export_service import (
    export_data,
    import_data,
    # Or specific functions if named differently
)
from src.models import MaterialProduct


class TestMaterialProductExport:
    """Tests for MaterialProduct export without deprecated fields."""

    def test_export_excludes_current_inventory(self, setup_material_data):
        """Verify export doesn't include current_inventory."""
        export_result = export_data(include_materials=True)

        # Find material products in export
        material_products = export_result.get("material_products", [])

        for product in material_products:
            assert "current_inventory" not in product
            assert "weighted_avg_cost" not in product
            assert "inventory_value" not in product

    def test_export_includes_required_fields(self, setup_material_data):
        """Verify export includes all required catalog fields."""
        export_result = export_data(include_materials=True)

        material_products = export_result.get("material_products", [])
        if material_products:
            product = material_products[0]
            # Required fields for catalog
            assert "name" in product
            assert "material_id" in product or "material_slug" in product
            assert "package_quantity" in product
            assert "package_unit" in product


class TestMaterialProductImport:
    """Tests for MaterialProduct import with backward compatibility."""

    def test_import_ignores_deprecated_fields(self, setup_material_hierarchy):
        """Verify import succeeds when old fields present."""
        # Create import data with deprecated fields
        import_data_dict = {
            "material_products": [{
                "name": "Test Import Product",
                "material_slug": "test-material",
                "package_quantity": 100,
                "package_unit": "feet",
                "quantity_in_base_units": 3048,
                # Deprecated fields that should be ignored
                "current_inventory": 500.0,
                "weighted_avg_cost": "0.15",
                "inventory_value": "75.00",
            }]
        }

        result = import_data(import_data_dict)

        # Import should succeed
        assert result.failed == 0

        # Verify product was created without deprecated fields
        with session_scope() as session:
            product = session.query(MaterialProduct).filter_by(
                name="Test Import Product"
            ).first()
            assert product is not None
            # These attributes should not exist on the model
            assert not hasattr(product, 'current_inventory') or product.current_inventory is None

    def test_import_works_without_deprecated_fields(self, setup_material_hierarchy):
        """Verify import works with clean new-format data."""
        import_data_dict = {
            "material_products": [{
                "name": "Clean Import Product",
                "material_slug": "test-material",
                "package_quantity": 50,
                "package_unit": "yards",
                "quantity_in_base_units": 4572,
            }]
        }

        result = import_data(import_data_dict)

        assert result.failed == 0


class TestMaterialProductRoundtrip:
    """Tests for export→import roundtrip."""

    def test_roundtrip_preserves_data(self, setup_material_data):
        """Verify export→import cycle preserves product data."""
        # Export
        export_result = export_data(include_materials=True)

        # Clear products (simulate fresh import)
        with session_scope() as session:
            session.query(MaterialProduct).delete()

        # Import
        import_result = import_data(export_result)

        # Verify
        with session_scope() as session:
            products = session.query(MaterialProduct).all()
            assert len(products) > 0

            for product in products:
                assert product.name is not None
                assert product.package_quantity > 0
```

**Files**:
- Create or edit: `src/tests/test_material_import_export.py`

**Parallel?**: No (follows T033 and T034)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking old exports | Filter deprecated fields on both export and import |
| Missing required fields | Validate required fields separately from deprecated |
| Silent data loss | Log when deprecated fields are encountered |

## Definition of Done Checklist

- [ ] Export function filters out deprecated fields
- [ ] Import function ignores deprecated fields without error
- [ ] Logging added for deprecated field encounters
- [ ] Export test verifies no deprecated fields
- [ ] Import test verifies backward compatibility
- [ ] Roundtrip test passes
- [ ] No import errors with old export files

## Review Guidance

**Key acceptance checkpoints**:
1. Export output - verify no current_inventory, weighted_avg_cost, inventory_value
2. Import with old file - verify no errors when these fields present
3. Import with new file - verify works without these fields
4. Roundtrip - export, import, verify data preserved

## Activity Log

- 2026-01-18T18:06:18Z – system – lane=planned – Prompt created.
