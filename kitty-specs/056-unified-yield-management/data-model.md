# Data Model: Unified Yield Management

**Feature**: 056-unified-yield-management
**Date**: 2026-01-16

## Entity Changes

### Recipe (Deprecation)

**File**: `src/models/recipe.py`

**Current State**:
```python
yield_quantity = Column(Float, nullable=False)
yield_unit = Column(String(50), nullable=False)
yield_description = Column(String(200), nullable=True)
```

**Target State**:
```python
# DEPRECATED: Use FinishedUnit.items_per_batch instead
# Kept nullable for backward compatibility during transition
yield_quantity = Column(Float, nullable=True)

# DEPRECATED: Use FinishedUnit.item_unit instead
yield_unit = Column(String(50), nullable=True)

# DEPRECATED: Use FinishedUnit.display_name instead
yield_description = Column(String(200), nullable=True)
```

**Migration Path**:
1. Change nullable=True (this feature)
2. Remove columns entirely (future feature, after all data migrated)

---

### FinishedUnit (Enhanced Validation)

**File**: `src/models/finished_unit.py`

**Current Fields** (no schema change):
```python
# Identity
id = Column(Integer, primary_key=True)
uuid = Column(UUID, nullable=True)
slug = Column(String(100), nullable=False, unique=True)
display_name = Column(String(200), nullable=False)

# Recipe relationship
recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)

# Yield mode
yield_mode = Column(Enum(YieldMode), nullable=False, default=YieldMode.DISCRETE_COUNT)

# DISCRETE_COUNT mode fields
items_per_batch = Column(Integer, nullable=True)
item_unit = Column(String(50), nullable=True)  # "cookie", "truffle", "piece"

# BATCH_PORTION mode fields
batch_percentage = Column(Numeric(5, 2), nullable=True)
portion_description = Column(String(200), nullable=True)
```

**New Validation Rules** (service layer, not schema):
1. For DISCRETE_COUNT mode:
   - `items_per_batch` MUST be > 0
   - `item_unit` MUST be non-empty
2. For BATCH_PORTION mode:
   - `batch_percentage` MUST be > 0 and <= 100
   - `portion_description` SHOULD be provided (warning if missing)

---

## Relationship Changes

### Recipe → FinishedUnit (Existing)

```
Recipe (1) ←→ (many) FinishedUnit
```

**Existing relationship** (`src/models/recipe.py`):
```python
finished_units = relationship("FinishedUnit", back_populates="recipe")
```

**New Constraint** (service layer):
- Recipe MUST have at least one FinishedUnit with complete yield data
- Enforced on: recipe create, recipe update

---

## Validation Summary

### Service Layer Validation

**Location**: `src/services/recipe_service.py`

**New Function**: `validate_recipe_finished_units(recipe_id: int) -> List[str]`

**Validation Rules**:

| Rule | Check | Error Message |
|------|-------|---------------|
| At least one FinishedUnit | `len(recipe.finished_units) >= 1` | "Recipe must have at least one yield type" |
| Complete yield data | All required fields present | "Yield type '{name}' is incomplete" |
| Valid items_per_batch | `items_per_batch > 0` | "Items per batch must be greater than 0" |
| Valid item_unit | `item_unit` not empty | "Unit is required for yield type" |
| Valid display_name | `display_name` not empty | "Name is required for yield type" |

---

## Data Transformation

### Legacy → New Format

**Transformation Script**: `scripts/transform_yield_data.py`

**Input** (legacy recipe in JSON):
```json
{
  "name": "Chocolate Chip Cookies",
  "yield_quantity": 36,
  "yield_unit": "cookie",
  "yield_description": "2-inch cookies"
}
```

**Output** (transformed):
```json
{
  "name": "Chocolate Chip Cookies",
  "yield_quantity": null,
  "yield_unit": null,
  "yield_description": null,
  "finished_units": [
    {
      "slug": "chocolate_chip_cookies_2inch_cookies",
      "display_name": "2-inch cookies",
      "recipe_name": "Chocolate Chip Cookies",
      "yield_mode": "discrete_count",
      "items_per_batch": 36,
      "item_unit": "cookie"
    }
  ]
}
```

### Default Generation

When `yield_description` is missing:

**Input**:
```json
{
  "name": "Sugar Cookies",
  "yield_quantity": 24,
  "yield_unit": "each"
}
```

**Output**:
```json
{
  "name": "Sugar Cookies",
  "finished_units": [
    {
      "slug": "sugar_cookies_standard",
      "display_name": "Standard Sugar Cookies",
      "items_per_batch": 24,
      "item_unit": "each"
    }
  ]
}
```

---

## Import/Export Schema

### Export Format (finished_units.json)

```json
[
  {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "slug": "chocolate_chip_cookies_standard",
    "display_name": "Standard Chocolate Chip Cookies",
    "recipe_name": "Chocolate Chip Cookies",
    "category": "cookie",
    "yield_mode": "discrete_count",
    "items_per_batch": 36,
    "item_unit": "cookie",
    "batch_percentage": null,
    "portion_description": null,
    "inventory_count": 0,
    "is_archived": false
  }
]
```

### Import Dependency Order

```
1. suppliers
2. ingredients
3. products
4. recipes           # Must exist before finished_units
5. finished_units    # NEW: Added to dependency order
6. material_categories
7. material_subcategories
8. materials
9. material_products
```

---

## Entity Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          RECIPE                                  │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)                                                         │
│ name                                                            │
│ category                                                        │
│ yield_quantity    ← DEPRECATED (nullable)                       │
│ yield_unit        ← DEPRECATED (nullable)                       │
│ yield_description ← DEPRECATED (nullable)                       │
│ ...                                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ 1
                             │
                             │ *
┌────────────────────────────▼────────────────────────────────────┐
│                       FINISHED_UNIT                              │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)                                                         │
│ recipe_id (FK)     → Recipe.id                                  │
│ slug (UNIQUE)      ← Generated: {recipe}_{suffix}               │
│ display_name       ← From yield_description OR "Standard {name}"│
│ yield_mode         ← DISCRETE_COUNT or BATCH_PORTION            │
│ items_per_batch    ← From yield_quantity (for DISCRETE_COUNT)   │
│ item_unit          ← From yield_unit (for DISCRETE_COUNT)       │
│ batch_percentage   ← For BATCH_PORTION mode                     │
│ portion_description← For BATCH_PORTION mode                     │
└─────────────────────────────────────────────────────────────────┘
```
