# TD-009: Add Slug Field to Supplier Model for Portable Identification

**Created**: 2026-01-12
**Status**: Open
**Priority**: Medium
**Related Features**: F049 (Import/Export), F027 (Suppliers)
**Impact**: Data model, import/export, FK resolution

---

## Problem Statement

The Supplier model currently lacks a portable identifier (slug) for cross-system identification. This creates fragility in import/export workflows:

**Problem 1: ID-Based References are Not Portable**
- `Product.preferred_supplier_id` references suppliers by auto-increment ID
- IDs differ between databases (dev, test, production)
- Importing products with `preferred_supplier_id=3` fails if supplier IDs differ

**Problem 2: Current Workaround is Fragile**
- Import service builds `old_id -> new_id` mapping during supplier import
- Mapping relies on matching suppliers by `(name, city, state)` tuple
- Breaks if supplier name/address changes between export and import
- Requires suppliers to be in same import file as products

**Problem 3: Inconsistent with Other Entities**
- Ingredients use `slug` for portable identification
- Products reference ingredients via `ingredient_slug`
- Materials use `slug` for portable identification
- Suppliers are the outlier without slug support

---

## Current Behavior

```python
# Product references supplier by ID (not portable)
class Product(BaseModel):
    preferred_supplier_id = Column(Integer, ForeignKey("suppliers.id"))

# Import must map IDs at runtime
supplier_id_map = {}  # old_id -> new_id
for supplier_data in data["suppliers"]:
    # Match by name/city/state (fragile)
    existing = session.query(Supplier).filter_by(
        name=name, city=city, state=state
    ).first()
    if existing:
        supplier_id_map[old_id] = existing.id
```

---

## Proposed Solution

Add `slug` field to Supplier model for portable, stable identification:

```python
class Supplier(BaseModel):
    slug = Column(String(100), unique=True, nullable=False, index=True)  # NEW
    name = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    # ... other fields
```

### Export Format (Updated)

```json
{
  "suppliers": [
    {
      "slug": "wegmans_bedford_ma",
      "name": "Wegmans",
      "city": "Bedford",
      "state": "MA"
    }
  ],
  "products": [
    {
      "ingredient_slug": "bread_flour",
      "brand": "Wegman's",
      "preferred_supplier_slug": "wegmans_bedford_ma"
    }
  ]
}
```

### Import Behavior (Updated)

```python
# Match suppliers by slug (stable)
existing = session.query(Supplier).filter_by(slug=slug).first()

# Products reference suppliers by slug
supplier = session.query(Supplier).filter_by(
    slug=prod_data.get("preferred_supplier_slug")
).first()
if supplier:
    product.preferred_supplier_id = supplier.id
```

---

## Implementation Plan

### Phase 1: Add Slug Field (Non-Breaking)

1. Add `Supplier.slug` column (nullable initially for migration)
2. Generate slugs for existing suppliers: `{name}_{city}_{state}`.lower().replace(" ", "_")
3. Make slug non-nullable after population
4. Add unique constraint

### Phase 2: Update Export

1. Export `slug` in supplier data
2. Add `preferred_supplier_slug` to product export (alongside ID for backward compat)

### Phase 3: Update Import

1. Match suppliers by `slug` instead of name/city/state
2. Resolve `preferred_supplier_slug` in product import
3. Fall back to ID mapping for legacy files without slugs

### Phase 4: Deprecate ID References

1. Warn on import if `preferred_supplier_id` is used without slug
2. Update sample data files to use slug references
3. Document slug as preferred method

---

## Impact Analysis

### Models Affected

- `Supplier`: Add `slug` field
- `Product`: Add `preferred_supplier_slug` to export (model unchanged)

### Services Affected

- `import_export_service.py`: Update supplier/product import logic
- `catalog_import_service.py`: Add supplier slug handling if needed

### Files to Update

- `src/models/supplier.py`
- `src/services/import_export_service.py`
- `test_data/sample_data_all.json`
- `test_data/material_products_catalog.json` (if applicable)

---

## Migration Strategy

### Slug Generation for Existing Data

```python
def generate_supplier_slug(name: str, city: str, state: str) -> str:
    """Generate slug from supplier identity fields."""
    raw = f"{name}_{city}_{state}"
    slug = raw.lower().replace(" ", "_").replace("-", "_")
    return "".join(c for c in slug if c.isalnum() or c == "_")

# Migration
for supplier in session.query(Supplier):
    if not supplier.slug:
        supplier.slug = generate_supplier_slug(
            supplier.name, supplier.city, supplier.state
        )
```

### Handling Conflicts

- If generated slug already exists, append numeric suffix: `wegmans_bedford_ma_2`
- Log warnings for manual review

---

## Effort Estimate

| Phase | Effort |
|-------|--------|
| Phase 1: Add slug field | 2-3 hours |
| Phase 2: Update export | 1-2 hours |
| Phase 3: Update import | 2-3 hours |
| Phase 4: Deprecation | 1 hour |
| Testing | 2-3 hours |
| **Total** | **8-12 hours** |

---

## Recommendation

**Priority: Medium** - Address when import/export reliability becomes critical or during next import service enhancement.

**Rationale:**
- Current ID mapping workaround functions but is fragile
- Aligns with existing slug patterns (ingredients, materials)
- Enables reliable cross-environment data portability
- Non-breaking migration path available

---

**END OF TECHNICAL DEBT DOCUMENT**
