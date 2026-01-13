# Data Model: Supplier Slug Support

**Feature**: 050-supplier-slug-support
**Date**: 2026-01-12

## Schema Changes

### Supplier Model (`src/models/supplier.py`)

#### New Field

```python
slug = Column(String(100), nullable=False, unique=True, index=True)
```

| Attribute | Value | Rationale |
|-----------|-------|-----------|
| Type | `String(100)` | Sufficient for `name_city_state` + conflict suffix |
| Nullable | `False` | All suppliers must have slugs for portability |
| Unique | `True` | Slugs serve as portable identifiers |
| Index | `True` | Fast lookups during import/export |

#### Updated Table Constraints

Add unique index for slug:
```python
Index("idx_supplier_slug", "slug", unique=True)
```

### Current Supplier Schema (Before)

```
suppliers
├── id              INTEGER PRIMARY KEY
├── uuid            VARCHAR(36) UNIQUE
├── name            VARCHAR(200) NOT NULL
├── supplier_type   VARCHAR(20) NOT NULL DEFAULT 'physical'
├── website_url     VARCHAR(500)
├── street_address  VARCHAR(200)
├── city            VARCHAR(100)
├── state           VARCHAR(2)
├── zip_code        VARCHAR(10)
├── notes           TEXT
├── is_active       BOOLEAN NOT NULL DEFAULT TRUE
├── created_at      DATETIME
├── updated_at      DATETIME
└── [Indexes]
    ├── idx_supplier_name_city (name, city)
    ├── idx_supplier_active (is_active)
    └── idx_supplier_type (supplier_type)
```

### Updated Supplier Schema (After)

```
suppliers
├── id              INTEGER PRIMARY KEY
├── uuid            VARCHAR(36) UNIQUE
├── slug            VARCHAR(100) NOT NULL UNIQUE  ← NEW
├── name            VARCHAR(200) NOT NULL
├── supplier_type   VARCHAR(20) NOT NULL DEFAULT 'physical'
├── website_url     VARCHAR(500)
├── street_address  VARCHAR(200)
├── city            VARCHAR(100)
├── state           VARCHAR(2)
├── zip_code        VARCHAR(10)
├── notes           TEXT
├── is_active       BOOLEAN NOT NULL DEFAULT TRUE
├── created_at      DATETIME
├── updated_at      DATETIME
└── [Indexes]
    ├── idx_supplier_slug (slug) UNIQUE           ← NEW
    ├── idx_supplier_name_city (name, city)
    ├── idx_supplier_active (is_active)
    └── idx_supplier_type (supplier_type)
```

## Slug Generation Pattern

### Physical Suppliers

```
Input:  name="Wegmans", city="Burlington", state="MA"
Output: slug="wegmans_burlington_ma"
```

### Online Suppliers

```
Input:  name="King Arthur Baking", supplier_type="online"
Output: slug="king_arthur_baking"
```

### Algorithm

1. Build input string based on supplier type
2. Apply Unicode normalization (NFD)
3. Encode to ASCII (removes accents)
4. Convert to lowercase
5. Replace spaces/hyphens with underscores
6. Remove non-alphanumeric chars (except `_`)
7. Collapse consecutive underscores
8. Strip leading/trailing underscores
9. Check uniqueness, append `_1`, `_2`, etc. if needed

## Migration Strategy

Per Constitution VI (Schema Change Strategy), use export/reset/import cycle:

1. Export all data to JSON (includes suppliers without slugs)
2. Delete database, update Supplier model with slug field
3. Recreate empty database with new schema
4. Transform exported JSON to add slug field to suppliers
5. Import transformed data

### Migration Script (Conceptual)

```python
def add_slugs_to_export(export_data: dict) -> dict:
    """Add slug field to all suppliers in export."""
    slugs_used = set()

    for supplier in export_data.get("suppliers", []):
        base_slug = generate_base_slug(supplier)
        slug = ensure_unique_slug(base_slug, slugs_used)
        supplier["slug"] = slug
        slugs_used.add(slug)

    return export_data
```

## Product Export/Import Changes

### Export Format (Updated)

```json
{
  "products": [
    {
      "sku": "FL-001",
      "display_name": "King Arthur All-Purpose Flour",
      "preferred_supplier_slug": "king_arthur_baking",
      "preferred_supplier_name": "King Arthur Baking",
      "preferred_supplier_id": 5
    }
  ]
}
```

New fields:
- `preferred_supplier_slug` - Primary key for import matching
- `preferred_supplier_name` - Human-readable fallback display

### Import Resolution Order

1. Match by `preferred_supplier_slug` (primary)
2. Fallback to `preferred_supplier_id` (legacy files)
3. Log warning if unresolved, import product without supplier

## Comparison with Existing Models

| Model | Slug Field | Generation |
|-------|------------|------------|
| Ingredient | `slug VARCHAR(200)` nullable | `create_slug(name, session)` |
| Material | `slug VARCHAR(200)` NOT NULL | `slugify(name)` inline |
| **Supplier** | `slug VARCHAR(100)` NOT NULL | `create_slug(name_city_state, session)` |

## Test Data Updates

### `test_data/suppliers.json` (Updated)

```json
{
  "suppliers": [
    {
      "name": "Costco",
      "slug": "costco_waltham_ma",
      "supplier_type": "physical",
      "city": "Waltham",
      "state": "MA",
      "zip_code": "02451"
    },
    {
      "name": "King Arthur Baking",
      "slug": "king_arthur_baking",
      "supplier_type": "online",
      "website_url": "https://shop.kingarthurbaking.com"
    }
  ]
}
```
