# Database Schema

## Overview

The Seasonal Baking Tracker uses SQLite with SQLAlchemy ORM. This document describes all database tables, fields, relationships, and constraints.

## Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  Ingredient  │───┐   │   Recipe     │       │FinishedGood  │
│              │   │   │              │───┬──▶│              │
└──────────────┘   │   └──────────────┘   │   └──────────────┘
                   │                       │            │
                   │   ┌──────────────┐   │            │
                   └──▶│ RecipeIng.   │───┘            │
                       │ (junction)   │                │
                       └──────────────┘                │
                                                        │
┌──────────────┐       ┌──────────────┐               │
│InventorySnap │       │   Bundle     │◀──────────────┘
│              │       │              │
└──────────────┘       └──────────────┘
       │                      │
       │                      │
       │               ┌──────────────┐
       │               │ BundleItem   │
       │               │ (junction)   │
       │               └──────────────┘
       │                      │
       │               ┌──────────────┐       ┌──────────────┐
       │               │   Package    │       │  Recipient   │
       │               │              │       │              │
       │               └──────────────┘       └──────────────┘
       │                      │                       │
       │                      │                       │
       │               ┌──────────────┐               │
       │               │PackageBundle │               │
       │               │ (junction)   │               │
       │               └──────────────┘               │
       │                                               │
       │               ┌──────────────┐               │
       └──────────────▶│    Event     │◀──────────────┘
                       │              │
                       └──────────────┘
                              │
                       ┌──────────────┐
                       │EventAssign.  │
                       │ (junction)   │
                       └──────────────┘
```

---

## Tables

### Ingredient

Stores raw materials and supplies.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key, Auto Increment | Unique identifier |
| `name` | String(200) | NOT NULL | Ingredient name |
| `brand` | String(200) | | Brand or supplier |
| `category` | String(100) | NOT NULL | Category (Flour, Sugar, etc.) |
| `purchase_unit` | String(50) | NOT NULL | Unit purchased in (bag, box, lb) |
| `purchase_unit_size` | String(100) | | Size description (50 lb, 5 kg) |
| `recipe_unit` | String(50) | NOT NULL | Unit used in recipes (cup, oz, g) |
| `conversion_factor` | Float | NOT NULL, > 0 | Purchase to recipe unit conversion |
| `quantity` | Float | NOT NULL, >= 0 | Current quantity in purchase units |
| `unit_cost` | Float | NOT NULL, >= 0 | Cost per purchase unit |
| `last_updated` | DateTime | NOT NULL | Last modification timestamp |
| `notes` | Text | | Additional notes |

**Indexes:**
- `idx_ingredient_name` on `name`
- `idx_ingredient_category` on `category`

**Example:**
```python
{
  "name": "All-Purpose Flour",
  "brand": "King Arthur",
  "category": "Flour/Grains",
  "purchase_unit": "bag",
  "purchase_unit_size": "50 lb",
  "recipe_unit": "cup",
  "conversion_factor": 200.0,  # 1 bag = 200 cups
  "quantity": 3.5,  # 3.5 bags on hand
  "unit_cost": 15.99,
  "last_updated": "2025-11-01 10:30:00"
}
```

---

### InventorySnapshot

Point-in-time captures of ingredient quantities.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key, Auto Increment | Unique identifier |
| `name` | String(200) | NOT NULL | Snapshot name |
| `snapshot_date` | DateTime | NOT NULL | When snapshot was created |
| `description` | Text | | Optional description |
| `created_at` | DateTime | NOT NULL | Record creation timestamp |

**Related Table:** `SnapshotIngredient` (junction table)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key | Unique identifier |
| `snapshot_id` | Integer | Foreign Key → Snapshot | Reference to snapshot |
| `ingredient_id` | Integer | Foreign Key → Ingredient | Reference to ingredient |
| `quantity` | Float | NOT NULL, >= 0 | Quantity at snapshot time |

**Indexes:**
- `idx_snapshot_date` on `snapshot_date`

---

### Recipe

Instructions for making baked goods.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key, Auto Increment | Unique identifier |
| `name` | String(200) | NOT NULL | Recipe name |
| `category` | String(100) | NOT NULL | Category (Cookies, Cakes, etc.) |
| `source` | String(500) | | Where recipe came from |
| `yield_quantity` | Float | NOT NULL, > 0 | Number of items produced |
| `yield_unit` | String(50) | NOT NULL | Unit of yield (cookies, servings) |
| `yield_description` | String(200) | | Description (e.g., "2-inch cookies") |
| `estimated_time_minutes` | Integer | >= 0 | Prep + bake time |
| `notes` | Text | | Additional notes |
| `date_added` | DateTime | NOT NULL | When added to database |
| `last_modified` | DateTime | NOT NULL | Last update timestamp |

**Related Table:** `RecipeIngredient` (junction table)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key | Unique identifier |
| `recipe_id` | Integer | Foreign Key → Recipe | Reference to recipe |
| `ingredient_id` | Integer | Foreign Key → Ingredient | Reference to ingredient |
| `quantity` | Float | NOT NULL, > 0 | Amount needed |
| `unit` | String(50) | NOT NULL | Unit (must match ingredient's recipe_unit) |
| `notes` | String(500) | | Optional notes (e.g., "sifted") |

**Indexes:**
- `idx_recipe_name` on `name`
- `idx_recipe_category` on `category`

---

### FinishedGood

Baked items produced from recipes with flexible yield modes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key, Auto Increment | Unique identifier |
| `name` | String(200) | NOT NULL, Indexed | Finished good name |
| `recipe_id` | Integer | Foreign Key → Recipe (RESTRICT) | Source recipe |
| `yield_mode` | Enum(YieldMode) | NOT NULL | "discrete_count" or "batch_portion" |
| `items_per_batch` | Integer | | Items per batch (discrete_count mode) |
| `item_unit` | String(50) | | Unit name (e.g., "cookie", "truffle") |
| `batch_percentage` | Float | | % of batch used (batch_portion mode) |
| `portion_description` | String(200) | | Description (e.g., "9-inch round") |
| `category` | String(100) | Indexed | Category (Cookies, Cakes, etc.) |
| `notes` | Text | | Additional notes |
| `date_added` | DateTime | NOT NULL | When created |
| `last_modified` | DateTime | NOT NULL | Last update timestamp |

**Calculated Methods:**
- `calculate_batches_needed(quantity)` - Returns batches needed for given quantity
- `get_cost_per_item()` - Returns cost per item based on recipe cost and yield mode

**Indexes:**
- `idx_finished_good_name` on `name`
- `idx_finished_good_recipe` on `recipe_id`
- `idx_finished_good_category` on `category`

**Note:** ProductionRecord not yet implemented (planned for Phase 4)

---

### Bundle

Grouped quantities of a single finished good (e.g., "Bag of 4 Sugar Cookies").

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key, Auto Increment | Unique identifier |
| `name` | String(200) | NOT NULL, Indexed | Bundle name |
| `finished_good_id` | Integer | Foreign Key → FinishedGood (RESTRICT) | The finished good |
| `quantity` | Integer | NOT NULL, > 0 | Number of items per bundle |
| `packaging_notes` | Text | | Packaging instructions |
| `date_added` | DateTime | NOT NULL | When created |
| `last_modified` | DateTime | NOT NULL | Last update timestamp |

**Calculated Methods:**
- `calculate_cost()` - Returns finished_good.cost_per_item × quantity
- `calculate_batches_needed(bundle_count)` - Returns batches needed for given number of bundles

**Indexes:**
- `idx_bundle_name` on `name`
- `idx_bundle_finished_good` on `finished_good_id`

**Note:** Simplified from original multi-item bundle design. Each bundle contains a quantity of one finished good type.

---

### Package

Gift packages containing bundles.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key, Auto Increment | Unique identifier |
| `name` | String(200) | NOT NULL, Indexed | Package name |
| `category` | String(100) | Indexed | Package category (optional) |
| `notes` | Text | | Additional notes |
| `date_added` | DateTime | NOT NULL | When package was created |
| `last_modified` | DateTime | NOT NULL | Last update timestamp |

**Calculated Fields:**
- `calculate_cost()` - Sum of (bundle.cost × quantity) for all bundles in package

**Related Table:** `PackageBundle` (junction table)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key | Unique identifier |
| `package_id` | Integer | Foreign Key → Package (CASCADE) | Reference to package |
| `bundle_id` | Integer | Foreign Key → Bundle (RESTRICT) | Bundle in package |
| `quantity` | Integer | NOT NULL, > 0 | Quantity per package |

**Indexes:**
- `idx_package_name` on `name`
- `idx_package_category` on `category`
- `idx_pb_package` on `package_id`
- `idx_pb_bundle` on `bundle_id`

---

### Recipient

People receiving gift packages.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key, Auto Increment | Unique identifier |
| `name` | String(200) | NOT NULL, Indexed | Recipient name |
| `household_name` | String(200) | Indexed | Household identifier (optional) |
| `address` | Text | | Delivery address (optional) |
| `preferences` | Text | | Gift preferences and dietary restrictions |
| `notes` | Text | | Additional notes |
| `date_added` | DateTime | NOT NULL | When recipient was created |
| `last_modified` | DateTime | NOT NULL | Last update timestamp |

**Indexes:**
- `idx_recipient_name` on `name`
- `idx_recipient_household` on `household_name`

---

### Event

Holiday seasons or baking events.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key, Auto Increment | Unique identifier |
| `name` | String(200) | NOT NULL, Indexed | Event name (Christmas 2025) |
| `event_date` | Date | NOT NULL, Indexed | Event date |
| `year` | Integer | NOT NULL, Indexed | Year (for filtering) |
| `notes` | Text | | Additional notes |
| `date_added` | DateTime | NOT NULL | When event was created |
| `last_modified` | DateTime | NOT NULL | Last update timestamp |

**Calculated Fields:**
- `total_cost` - Sum of all package costs × quantities for all assignments
- `recipient_count` - Number of unique recipients in this event
- `package_count` - Total packages (sum of quantities across all assignments)

**Related Table:** `EventRecipientPackage` (junction table)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key | Unique identifier |
| `event_id` | Integer | Foreign Key → Event (CASCADE) | Reference to event |
| `recipient_id` | Integer | Foreign Key → Recipient (RESTRICT) | Who receives |
| `package_id` | Integer | Foreign Key → Package (RESTRICT) | What they receive |
| `quantity` | Integer | NOT NULL, Default: 1 | Number of packages |
| `notes` | Text | | Optional assignment notes |

**Indexes:**
- `idx_event_name` on `name`
- `idx_event_year` on `year`
- `idx_event_date` on `event_date`
- `idx_erp_event` on `event_id`
- `idx_erp_recipient` on `recipient_id`
- `idx_erp_package` on `package_id`

**Note:** Inventory snapshot feature was simplified - shopping lists use live inventory instead of snapshots.

---

### EditHistory

Tracks changes for undo functionality.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key, Auto Increment | Unique identifier |
| `table_name` | String(100) | NOT NULL | Which table was modified |
| `record_id` | Integer | NOT NULL | ID of modified record |
| `field_name` | String(100) | NOT NULL | Which field changed |
| `old_value` | Text | | Previous value (JSON) |
| `new_value` | Text | | New value (JSON) |
| `timestamp` | DateTime | NOT NULL | When change occurred |
| `user_action` | String(200) | | Description of action |

**Indexes:**
- `idx_edit_history_timestamp` on `timestamp`
- `idx_edit_history_table_record` on `(table_name, record_id)`

**Note:** Only last 8 edits per entity kept in memory for undo.

---

## Calculated Fields

These are not stored in database but calculated on-demand:

### Recipe Cost
```python
recipe_cost = sum(
    (ingredient.unit_cost / ingredient.conversion_factor) * recipe_ingredient.quantity
    for each ingredient in recipe
)
```

### Finished Good Cost
```python
finished_good_cost = recipe.cost / recipe.yield_quantity
```

### Bundle Cost
```python
bundle_cost = sum(
    finished_good.cost * bundle_item.quantity
    for each finished_good in bundle
)
```

### Package Cost
```python
package_cost = sum(
    bundle.cost * package_bundle.quantity
    for each bundle in package
)
```

---

## Database Configuration

### SQLite Settings
```python
SQLALCHEMY_DATABASE_URI = 'sqlite:///data/bake_tracker.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Connection arguments
connect_args = {
    'check_same_thread': False,
    'timeout': 30
}

# Enable foreign keys
PRAGMA foreign_keys = ON;

# Enable WAL mode for better concurrency
PRAGMA journal_mode = WAL;
```

### Indexes
Indexes are created on:
- All foreign keys
- Frequently queried fields (name, category, date)
- Fields used in sorting and filtering

---

## Migration Strategy

For schema changes:
1. Use Alembic for migrations (future enhancement)
2. Backup database before applying changes
3. Test migrations on copy before production
4. Document all schema changes in CHANGELOG.md

---

## Data Integrity

### Foreign Key Constraints
All relationships enforce referential integrity. Deletions cascade or prevent based on relationship:

- **Ingredient deletion**: Blocked if used in recipes
- **Recipe deletion**: Cascades to finished goods (with confirmation)
- **Event deletion**: Cascades to event assignments
- **Snapshot deletion**: Blocked if referenced by events

### Validation
- Quantities and costs must be non-negative
- Conversion factors must be positive
- Units must match predefined types
- Dates must be valid
- Required fields enforced at database and application level

---

**Document Status:** Living document, updated with schema changes
**Last Updated:** 2025-11-04 (Phase 3b completion - Events, Recipients, Packages fully implemented)
