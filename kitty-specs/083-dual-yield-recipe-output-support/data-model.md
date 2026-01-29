# Data Model: Dual-Yield Recipe Output Support

**Feature**: 083-dual-yield-recipe-output-support
**Date**: 2026-01-29
**Status**: Complete

## Schema Changes

### FinishedUnit Table

**Current Schema** (`src/models/finished_unit.py`):

```sql
CREATE TABLE finished_units (
    id INTEGER PRIMARY KEY,
    uuid TEXT,
    slug VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id),
    yield_mode VARCHAR(20) NOT NULL DEFAULT 'discrete_count',
    items_per_batch INTEGER,
    item_unit VARCHAR(50),
    batch_percentage NUMERIC(5,2),
    portion_description VARCHAR(200),
    inventory_count INTEGER NOT NULL DEFAULT 0,
    category VARCHAR(100),
    description TEXT,
    production_notes TEXT,
    notes TEXT,
    created_at DATETIME,
    updated_at DATETIME,

    CONSTRAINT ck_finished_unit_inventory_non_negative CHECK (inventory_count >= 0),
    CONSTRAINT ck_finished_unit_items_per_batch_positive CHECK (items_per_batch IS NULL OR items_per_batch > 0),
    CONSTRAINT ck_finished_unit_batch_percentage_valid CHECK (batch_percentage IS NULL OR (batch_percentage > 0 AND batch_percentage <= 100))
);
```

**New Schema** (changes highlighted):

```sql
CREATE TABLE finished_units (
    id INTEGER PRIMARY KEY,
    uuid TEXT,
    slug VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id),
    yield_mode VARCHAR(20) NOT NULL DEFAULT 'discrete_count',
    yield_type VARCHAR(10) NOT NULL DEFAULT 'SERVING',  -- NEW FIELD
    items_per_batch INTEGER,
    item_unit VARCHAR(50),
    batch_percentage NUMERIC(5,2),
    portion_description VARCHAR(200),
    inventory_count INTEGER NOT NULL DEFAULT 0,
    category VARCHAR(100),
    description TEXT,
    production_notes TEXT,
    notes TEXT,
    created_at DATETIME,
    updated_at DATETIME,

    -- Existing constraints
    CONSTRAINT ck_finished_unit_inventory_non_negative CHECK (inventory_count >= 0),
    CONSTRAINT ck_finished_unit_items_per_batch_positive CHECK (items_per_batch IS NULL OR items_per_batch > 0),
    CONSTRAINT ck_finished_unit_batch_percentage_valid CHECK (batch_percentage IS NULL OR (batch_percentage > 0 AND batch_percentage <= 100)),

    -- NEW CONSTRAINTS
    CONSTRAINT ck_finished_unit_yield_type_valid CHECK (yield_type IN ('EA', 'SERVING')),
    CONSTRAINT uq_finished_unit_recipe_item_unit_yield_type UNIQUE (recipe_id, item_unit, yield_type)
);
```

---

## SQLAlchemy Model Changes

**File**: `src/models/finished_unit.py`

### Add yield_type Column

```python
# After yield_mode column (around line 90)
yield_type = Column(
    String(10),
    nullable=False,
    default="SERVING",
    index=True,
    doc="Yield classification: 'EA' (whole unit) or 'SERVING' (consumption unit)"
)
```

### Add Constraints to __table_args__

```python
__table_args__ = (
    # Existing indexes...
    Index("idx_finished_unit_slug", "slug"),
    Index("idx_finished_unit_display_name", "display_name"),
    Index("idx_finished_unit_recipe", "recipe_id"),
    Index("idx_finished_unit_category", "category"),
    Index("idx_finished_unit_inventory", "inventory_count"),
    Index("idx_finished_unit_created_at", "created_at"),
    Index("idx_finished_unit_recipe_inventory", "recipe_id", "inventory_count"),
    Index("idx_finished_unit_yield_type", "yield_type"),  # NEW INDEX

    # Existing constraints...
    UniqueConstraint("slug", name="uq_finished_unit_slug"),
    CheckConstraint("inventory_count >= 0", name="ck_finished_unit_inventory_non_negative"),
    CheckConstraint(
        "items_per_batch IS NULL OR items_per_batch > 0",
        name="ck_finished_unit_items_per_batch_positive",
    ),
    CheckConstraint(
        "batch_percentage IS NULL OR (batch_percentage > 0 AND batch_percentage <= 100)",
        name="ck_finished_unit_batch_percentage_valid",
    ),

    # NEW CONSTRAINTS
    CheckConstraint(
        "yield_type IN ('EA', 'SERVING')",
        name="ck_finished_unit_yield_type_valid",
    ),
    UniqueConstraint(
        "recipe_id", "item_unit", "yield_type",
        name="uq_finished_unit_recipe_item_unit_yield_type",
    ),
)
```

---

## Entity Relationships

```
Recipe (1) ──────< (N) FinishedUnit
                        │
                        ├── slug (unique identifier)
                        ├── display_name (user-facing name)
                        ├── item_unit (output unit: "cookie", "cake")
                        ├── yield_type (NEW: "EA" or "SERVING")
                        ├── items_per_batch (quantity)
                        └── ... other fields
```

**Relationship constraints**:
- One Recipe can have many FinishedUnits
- Each (recipe_id, item_unit, yield_type) combination must be unique
- This allows: "small cake/EA" and "small cake/SERVING" on same recipe
- This prevents: two "small cake/EA" on same recipe

---

## Validation Rules

### Service Layer Validation

**File**: `src/services/recipe_service.py` (or `finished_unit_service.py`)

```python
VALID_YIELD_TYPES = {"EA", "SERVING"}

def validate_yield_type(yield_type: str) -> List[str]:
    """Validate yield_type value.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    if not yield_type:
        errors.append("yield_type is required")
    elif yield_type not in VALID_YIELD_TYPES:
        errors.append(f"yield_type must be 'EA' or 'SERVING', got '{yield_type}'")
    return errors
```

### Import Validation

**File**: `src/services/coordinated_export_service.py`

```python
# In import_finished_units section
yield_type = record.get("yield_type", "SERVING")  # Default for backward compat
if yield_type not in ("EA", "SERVING"):
    logger.warning(f"Invalid yield_type '{yield_type}', defaulting to 'SERVING'")
    yield_type = "SERVING"
```

---

## Export Format

### Current Format

```json
{
  "slug": "wedding-cake-whole",
  "display_name": "Wedding Cake (Whole)",
  "recipe_slug": "wedding-cake",
  "yield_mode": "discrete_count",
  "items_per_batch": 1,
  "item_unit": "cake",
  "inventory_count": 2
}
```

### New Format

```json
{
  "slug": "wedding-cake-whole",
  "display_name": "Wedding Cake (Whole)",
  "recipe_slug": "wedding-cake",
  "yield_mode": "discrete_count",
  "yield_type": "EA",
  "items_per_batch": 1,
  "item_unit": "cake",
  "inventory_count": 2
}
```

### Example: Dual-Yield Recipe

```json
[
  {
    "slug": "wedding-cake-whole",
    "display_name": "Wedding Cake (Whole)",
    "recipe_slug": "wedding-cake",
    "yield_mode": "discrete_count",
    "yield_type": "EA",
    "items_per_batch": 1,
    "item_unit": "cake",
    "inventory_count": 2
  },
  {
    "slug": "wedding-cake-servings",
    "display_name": "Wedding Cake (Servings)",
    "recipe_slug": "wedding-cake",
    "yield_mode": "discrete_count",
    "yield_type": "SERVING",
    "items_per_batch": 100,
    "item_unit": "slice",
    "inventory_count": 0
  }
]
```

---

## Migration Data Transformation

### Pre-Migration Export Sample

```json
{
  "slug": "sugar-cookies",
  "display_name": "Sugar Cookies",
  "recipe_slug": "sugar-cookies-recipe",
  "yield_mode": "discrete_count",
  "items_per_batch": 24,
  "item_unit": "cookie"
}
```

### Post-Migration Import

```json
{
  "slug": "sugar-cookies",
  "display_name": "Sugar Cookies",
  "recipe_slug": "sugar-cookies-recipe",
  "yield_mode": "discrete_count",
  "yield_type": "SERVING",
  "items_per_batch": 24,
  "item_unit": "cookie"
}
```

**Transformation rule**: Add `"yield_type": "SERVING"` to all existing records (conservative default - most baked goods are counted as servings).
