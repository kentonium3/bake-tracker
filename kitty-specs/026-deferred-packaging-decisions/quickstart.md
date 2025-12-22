# Quickstart: Deferred Packaging Decisions

**Feature**: 026-deferred-packaging-decisions

## Overview

This feature enables planning with generic packaging requirements (e.g., "Cellophane Bags 6x10") instead of committing to specific designs upfront. Specific materials are assigned from inventory when ready to assemble.

## Key Concepts

### Generic Product
A packaging type without design specificity. Identified by `product_name` field on Product (e.g., "Cellophane Bags 6x10"). Multiple specific products share this name but have different brands (designs).

### Specific Material
An actual packaging product in inventory with a specific design/brand (e.g., "Snowflake design" cellophane bag).

### Assignment
The process of allocating specific inventory items to fulfill a generic packaging requirement.

## Database Changes

### New Column: compositions.is_generic
```sql
ALTER TABLE compositions ADD COLUMN is_generic BOOLEAN NOT NULL DEFAULT 0;
```

### New Table: composition_assignments
```sql
CREATE TABLE composition_assignments (
    id INTEGER PRIMARY KEY,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    composition_id INTEGER NOT NULL REFERENCES compositions(id) ON DELETE CASCADE,
    inventory_item_id INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE RESTRICT,
    quantity_assigned REAL NOT NULL CHECK (quantity_assigned > 0),
    assigned_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

## Service API

### packaging_service.py

```python
def get_generic_products() -> list[str]:
    """Get distinct product_name values for packaging products."""

def get_generic_inventory_summary(product_name: str) -> dict:
    """
    Returns: {
        'total': int,
        'breakdown': [{'brand': str, 'product_id': int, 'available': int}]
    }
    """

def get_estimated_cost(product_name: str, quantity: float) -> float:
    """Average price across all products with this product_name."""

def assign_materials(composition_id: int, assignments: list[dict]) -> bool:
    """
    Create assignment records.
    assignments: [{'inventory_item_id': int, 'quantity': float}]
    """

def get_pending_requirements(event_id: int = None) -> list[Composition]:
    """Find compositions where is_generic=True and no assignments exist."""
```

## UI Workflow

### Planning
1. User creates finished good with packaging
2. Selects "Generic product" radio button
3. Chooses product type from dropdown
4. Sees inventory summary and estimated cost
5. Saves with `is_generic=True`

### Assignment
1. User opens assembly definition
2. Sees pending generic requirements
3. Clicks "Assign Materials"
4. Selects specific products and quantities
5. Saves when total matches required

### Assembly
1. User completes assembly
2. If unassigned packaging, sees prompt
3. Can assign now, view details, or bypass

## Testing

```bash
# Run packaging service tests
pytest src/tests/services/test_packaging_service.py -v

# Run integration tests
pytest src/tests/integration/test_deferred_packaging.py -v
```

## Migration

Per Constitution VI (Schema Change Strategy):
1. Export: `python -c "from src.services.import_export_service import export_all_to_json; export_all_to_json('backup.json')"`
2. Delete database
3. Run app (creates new schema)
4. Import: Use File > Import Data menu
