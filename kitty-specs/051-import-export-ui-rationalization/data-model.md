# Data Model: Import/Export UI Rationalization

**Feature**: 051-import-export-ui-rationalization
**Date**: 2026-01-13
**Status**: Complete

## Overview

This feature makes minimal data model changes. The primary storage change is using the existing `app_config` table for directory preferences. No new database tables or schema migrations required.

## Entities

### Existing Entity: app_config

**Location**: `src/models/app_config.py`

The `app_config` table already exists and follows a key-value pattern suitable for storing directory preferences.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| key | String | Configuration key (unique) |
| value | String | Configuration value |
| created_at | DateTime | Record creation timestamp |
| updated_at | DateTime | Record update timestamp |

**New Keys for This Feature**:

| Key | Default Value | Description |
|-----|--------------|-------------|
| `import_directory` | `~/Documents` | Default directory for file open dialogs |
| `export_directory` | `~/Documents` | Default directory for file save dialogs |
| `logs_directory` | `<project>/docs/user_testing` | Directory for import log files |

## Service Data Structures

### ValidationResult (NEW)

**Location**: `src/services/schema_validation_service.py` (new file)

```python
@dataclass
class ValidationError:
    """A validation error with context for actionable error messages."""
    field: str              # Field path (e.g., "ingredients[0].display_name")
    message: str            # Human-readable error message
    record_number: int      # 1-indexed record number (0 if top-level)
    expected: Optional[str] # Expected type or format
    actual: Optional[str]   # Actual value or type found

@dataclass
class ValidationWarning:
    """A validation warning (non-fatal issue)."""
    field: str              # Field path
    message: str            # Human-readable warning message
    record_number: int      # 1-indexed record number

@dataclass
class ValidationResult:
    """Result of schema validation."""
    valid: bool                        # True if no errors (warnings OK)
    errors: List[ValidationError]      # List of validation errors
    warnings: List[ValidationWarning]  # List of validation warnings

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)
```

### Import Log Structure

**Location**: Enhanced `_write_import_log()` in `src/ui/import_export_dialog.py`

Plain text format with sections:

```
================================================================================
IMPORT LOG
================================================================================

SOURCE
------
File: /path/to/file.json
Size: 12,345 bytes
Format: Catalog (Normalized v4.0)

OPERATION
---------
Purpose: Catalog
Mode: Add Only
Timestamp: 2026-01-13T10:30:00Z

PREPROCESSING (if Context-Rich)
-------------------------------
Entity Type: ingredients
Records Extracted: 25
FK Validations: 25 passed, 0 failed
Context Fields Ignored: supplier_name, category_path

SCHEMA VALIDATION
-----------------
Status: PASSED
Errors: 0
Warnings: 2
  - ingredients[5].notes: Field exceeds recommended length (500 chars)
  - ingredients[12].package_type: Unknown package type 'bulk'

IMPORT RESULTS
--------------
ingredients: 20 imported, 3 skipped, 2 updated
products: 15 imported, 0 skipped, 0 updated

ERRORS
------
(none)

WARNINGS
--------
- ingredients[3] 'Sugar, Granulated': Skipped (already exists)
- ingredients[7] 'Vanilla Extract': Updated (augmented empty fields)

SUMMARY
-------
Total Records: 35
Successful: 35
Skipped: 3
Failed: 0

METADATA
--------
Application: Bake Tracker v0.7.0
Log Version: 2.0
Duration: 1.23 seconds
================================================================================
```

## Relationships

### Supplier Import Order

Suppliers must be imported BEFORE products due to FK relationship:

```
Supplier (1) <-- (N) Product
```

**Import dependency order** (existing + suppliers):
1. suppliers (NEW in catalog)
2. ingredients
3. products
4. materials
5. material_products
6. recipes (depends on ingredients)

### Context-Rich Data Flow

```
aug_ingredients.json
    ├── _meta.editable_fields
    └── ingredients[]
        ├── display_name (editable)
        ├── category (editable)
        ├── ...
        ├── supplier_name (readonly - ignored)
        ├── category_path (readonly - ignored)
        └── inventory_total (readonly - ignored)
           │
           ▼ Preprocessing
     normalized_ingredients.json
        └── ingredients[]
            ├── display_name
            ├── category
            └── ... (only editable fields)
               │
               ▼ Schema Validation (Catalog schemas)
               │
               ▼ Import (catalog_import_service)
```

## Schema Validation Rules

### Catalog Entity Schemas

| Entity | Required Fields | Optional Fields | FK References |
|--------|-----------------|-----------------|---------------|
| suppliers | `name` | `slug`, `contact_info`, `notes` | - |
| ingredients | `display_name` | `category`, `package_unit`, `package_unit_quantity`, `notes` | - |
| products | `display_name`, `ingredient_slug` | `supplier_slug`, `brand`, `package_unit`, `unit_cost` | ingredient, supplier |
| materials | `name` | `category`, `hierarchy_path` | - |
| material_products | `material_name`, `product_name` | - | material, product |
| recipes | `name` | `category`, `yield_quantity`, `yield_unit`, `ingredients[]`, `components[]` | ingredients (via slug) |

### Field Type Validation

| Type | Validation Rule |
|------|-----------------|
| string | Non-empty unless optional |
| number | Parseable as int/float |
| decimal | Parseable as Decimal, non-negative for costs |
| array | Must be list type |
| boolean | Must be true/false |
| slug | Lowercase, alphanumeric with hyphens |
| unit | Must be in valid units list |

## Migration Notes

**No migration required.** This feature:
- Uses existing `app_config` table
- Adds no new database columns
- Creates no new tables

Directory preferences are created on first access with sensible defaults.
