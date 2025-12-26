# Data Model: Enhanced Export/Import System

**Feature**: 030-enhanced-export-import
**Date**: 2025-12-25

## Overview

No new database entities required. This feature operates on existing entities with new file formats for export/import operations.

## Existing Entities (Reference)

### Core Entities

| Entity | Unique Key | FK Dependencies |
|--------|-----------|-----------------|
| Supplier | name | None |
| Ingredient | slug | None |
| Product | (composite)* | ingredient_id |
| Purchase | id | product_id, supplier_id |
| InventoryItem | id | product_id |
| Recipe | name | None |
| RecipeIngredient | (recipe_id, ingredient_id) | recipe_id, ingredient_id |

*Product composite key: (ingredient_id, brand, package_unit_quantity, package_unit)

### Import Dependency Order

Must import in this order to satisfy FK constraints:
1. Suppliers (no dependencies)
2. Ingredients (no dependencies)
3. Products (depends on Ingredients)
4. Recipes (depends on Ingredients)
5. Purchases (depends on Products, Suppliers)
6. InventoryItems (depends on Products)

## New File Formats

### Manifest Schema (`manifest.json`)

```json
{
  "version": "1.0",
  "export_date": "2025-12-25T10:30:00Z",
  "source": "Seasonal Baking Tracker v0.8.0",
  "files": [
    {
      "filename": "suppliers.json",
      "entity_type": "suppliers",
      "record_count": 5,
      "sha256": "abc123...",
      "dependencies": [],
      "import_order": 1
    },
    {
      "filename": "ingredients.json",
      "entity_type": "ingredients",
      "record_count": 50,
      "sha256": "def456...",
      "dependencies": [],
      "import_order": 2
    },
    {
      "filename": "products.json",
      "entity_type": "products",
      "record_count": 100,
      "sha256": "ghi789...",
      "dependencies": ["ingredients"],
      "import_order": 3
    }
  ]
}
```

### Entity File Schema (Normalized)

Each entity file includes both ID and slug/name for FK resolution:

**suppliers.json**:
```json
{
  "version": "1.0",
  "entity_type": "suppliers",
  "records": [
    {
      "id": 1,
      "name": "Costco",
      "city": "Rochester",
      "state": "NY",
      "zip": "14623"
    }
  ]
}
```

**products.json** (with FK resolution fields):
```json
{
  "version": "1.0",
  "entity_type": "products",
  "records": [
    {
      "id": 15,
      "ingredient_id": 3,
      "ingredient_slug": "all_purpose_flour",
      "brand": "King Arthur",
      "product_name": "All-Purpose Flour",
      "package_size": "5 lb",
      "package_unit": "lb",
      "package_unit_quantity": 5.0,
      "upc_code": null
    }
  ]
}
```

### Denormalized View Schema

**view_products.json**:
```json
{
  "version": "1.0",
  "view_type": "products",
  "export_date": "2025-12-25T10:30:00Z",
  "_meta": {
    "editable_fields": ["brand", "product_name", "package_size", "package_unit", "upc_code", "notes"],
    "readonly_fields": ["id", "ingredient_id", "ingredient_slug", "ingredient_name", "ingredient_category", "supplier_name", "last_purchase_price", "inventory_quantity"]
  },
  "records": [
    {
      "id": 15,
      "ingredient_id": 3,
      "ingredient_slug": "all_purpose_flour",
      "ingredient_name": "All-Purpose Flour",
      "ingredient_category": "Flour",
      "brand": "King Arthur",
      "product_name": "All-Purpose Flour",
      "package_size": "5 lb",
      "package_unit": "lb",
      "package_unit_quantity": 5.0,
      "upc_code": null,
      "supplier_name": "Costco",
      "last_purchase_price": 12.99,
      "inventory_quantity": 2
    }
  ]
}
```

### Import Skipped Records Log

**import_skipped_2025-12-25_103000.json**:
```json
{
  "import_file": "purchases.json",
  "import_date": "2025-12-25T10:30:00Z",
  "mode": "merge",
  "skipped_records": [
    {
      "record_index": 42,
      "skip_reason": "fk_missing",
      "fk_entity": "supplier",
      "fk_value": "Wilson's Farm",
      "original_record": { ... }
    }
  ]
}
```

## Service Interfaces

### FKResolver Protocol

```python
from typing import Protocol, List
from enum import Enum

class ResolutionChoice(Enum):
    CREATE = "create"
    MAP = "map"
    SKIP = "skip"

@dataclass
class MissingFK:
    entity_type: str  # "supplier", "ingredient", "product"
    missing_value: str  # The slug/name that wasn't found
    affected_record_count: int
    sample_records: List[Dict]  # First 3 affected records for context

@dataclass
class Resolution:
    choice: ResolutionChoice
    entity_type: str
    missing_value: str
    mapped_id: Optional[int] = None  # For MAP choice
    created_entity: Optional[Dict] = None  # For CREATE choice

class FKResolverCallback(Protocol):
    def resolve(self, missing: MissingFK) -> Resolution:
        """Called for each missing FK. Returns user's resolution choice."""
        ...
```

### Import Result Extensions

```python
@dataclass
class EnhancedImportResult:
    """Extended result with resolution tracking."""

    # From existing ImportResult
    total_records: int
    successful: int
    skipped: int
    failed: int
    errors: List[Dict]
    warnings: List[Dict]

    # New fields
    resolutions: List[Resolution]  # FK resolutions made
    created_entities: Dict[str, int]  # Count by entity type
    mapped_entities: Dict[str, int]  # Count by entity type
    skipped_due_to_fk: int  # Records skipped due to unresolved FK
```

## Validation Rules

### Checksum Validation
- SHA256 hash of file content
- Validation before import
- Warning (not error) on mismatch with user choice to proceed

### FK Resolution Validation
- Slugs must be non-empty strings
- Mapped IDs must exist in database
- Created entities must pass entity-specific validation

### Duplicate Handling
- Entity files: First occurrence wins, skip duplicates with warning
- Transaction records: Duplicates allowed (FK references)

### Unknown Field Handling
- Warn about unknown fields
- Import known fields only
- Log unknown fields for debugging
