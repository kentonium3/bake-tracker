# Data Model: Event Planning Restoration

**Feature**: 006-event-planning-restoration
**Date**: 2025-12-03
**Status**: Draft

## Entity Relationship Overview

```
Recipe ←──────── FinishedUnit ←──────── Composition ──────────→ FinishedGood
                      │                      │                       │
                      │                      └───────────────────────┘
                      │                              (self-referential)
                      │
                      └─────────────────────────────────────────────────┐
                                                                        │
Package ←──────── PackageFinishedGood ──────────→ FinishedGood ←───────┘
    │
    │
EventRecipientPackage
    │
    ├──────────→ Event
    └──────────→ Recipient
```

## Entities

### Existing Entities (No Changes)

#### Recipe
- **Table**: `recipes`
- **Purpose**: Defines ingredients and quantities for baking
- **Key Fields**: id, name, recipe_ingredients
- **Cost Method**: `calculate_cost()` → uses RecipeService.calculate_actual_cost()

#### FinishedUnit
- **Table**: `finished_units`
- **Purpose**: Individual baked item linked to a recipe
- **Key Fields**: id, slug, display_name, recipe_id, yield_mode, items_per_batch, unit_cost
- **Cost Method**: `calculate_recipe_cost_per_item()` → derived from recipe cost

#### FinishedGood
- **Table**: `finished_goods`
- **Purpose**: Assembly containing FinishedUnits and/or other FinishedGoods
- **Key Fields**: id, slug, display_name, assembly_type, total_cost
- **Cost Method**: `calculate_component_cost()` → sum of composition costs
- **Relationship**: `components` → Composition[]

#### Composition
- **Table**: `compositions`
- **Purpose**: Polymorphic junction linking FinishedGood to components
- **Key Fields**: assembly_id, finished_unit_id (nullable), finished_good_id (nullable), component_quantity
- **Constraint**: Exactly one of finished_unit_id or finished_good_id must be non-null

### Entities to Re-enable/Modify

#### Recipient (Re-enable)
- **Table**: `recipients`
- **Status**: Model exists, enabled in __init__.py
- **Purpose**: Person or household receiving gift packages
- **Key Fields**:
  - id (int, PK)
  - name (string, required)
  - household_name (string, optional)
  - address (text, optional)
  - notes (text, optional)
  - date_added (datetime)
  - last_modified (datetime)
- **Changes Required**: None - model is functional

#### Event (Re-enable)
- **Table**: `events`
- **Status**: Model exists, disabled in __init__.py
- **Purpose**: Gift-giving occasion (e.g., "Christmas 2024")
- **Key Fields**:
  - id (int, PK)
  - name (string, required, indexed)
  - event_date (date, required)
  - year (int, required, indexed)
  - notes (text, optional)
  - date_added (datetime)
  - last_modified (datetime)
- **Relationships**:
  - event_recipient_packages → EventRecipientPackage[]
- **Calculated Properties**:
  - get_total_cost() → sum of all assignment costs
  - get_recipient_count() → unique recipients
  - get_package_count() → total packages (sum of quantities)
- **Changes Required**: Re-enable import in __init__.py

#### Package (Modify)
- **Table**: `packages`
- **Status**: Model exists, disabled, references removed Bundle
- **Purpose**: Gift package containing FinishedGoods (assemblies)
- **Key Fields**:
  - id (int, PK)
  - name (string, required, indexed)
  - description (text, optional)
  - is_template (bool, default False)
  - notes (text, optional)
  - date_added (datetime)
  - last_modified (datetime)
- **Relationships**:
  - package_finished_goods → PackageFinishedGood[] (CHANGED from package_bundles)
- **Calculated Properties**:
  - calculate_cost() → sum of FinishedGood costs × quantities
  - get_item_count() → count of FinishedGoods (renamed from get_bundle_count)
- **Changes Required**:
  - Update relationship from `package_bundles` to `package_finished_goods`
  - Update calculate_cost() to use FinishedGood.total_cost

### New/Modified Junction Tables

#### PackageFinishedGood (New - replaces PackageBundle)
- **Table**: `package_finished_goods`
- **Purpose**: Links Package to FinishedGood with quantity
- **Key Fields**:
  - id (int, PK)
  - package_id (int, FK → packages.id, CASCADE)
  - finished_good_id (int, FK → finished_goods.id, RESTRICT)
  - quantity (int, required, default 1)
- **Relationships**:
  - package → Package
  - finished_good → FinishedGood
- **Indexes**:
  - idx_package_fg_package (package_id)
  - idx_package_fg_finished_good (finished_good_id)
- **Notes**: Replaces PackageBundle which referenced removed Bundle model

#### EventRecipientPackage (Re-enable)
- **Table**: `event_recipient_packages`
- **Status**: Model exists, disabled
- **Purpose**: Assigns packages to recipients for events
- **Key Fields**:
  - id (int, PK)
  - event_id (int, FK → events.id, CASCADE)
  - recipient_id (int, FK → recipients.id, RESTRICT)
  - package_id (int, FK → packages.id, RESTRICT)
  - quantity (int, default 1)
  - notes (text, optional)
- **Relationships**:
  - event → Event
  - recipient → Recipient
  - package → Package
- **Calculated Properties**:
  - calculate_cost() → package.calculate_cost() × quantity
- **Changes Required**: Re-enable import, verify Package relationship works

## Cost Calculation Flow

```
1. Recipe cost (via RecipeService.calculate_actual_cost())
   │
   ▼
2. FinishedUnit.unit_cost = Recipe.cost / items_per_batch
   │
   ▼
3. Composition.total_cost = FinishedUnit.unit_cost × quantity
   │
   ▼
4. FinishedGood.total_cost = Σ(Composition.total_cost)
   │
   ▼
5. PackageFinishedGood cost = FinishedGood.total_cost × quantity
   │
   ▼
6. Package.cost = Σ(PackageFinishedGood costs)
   │
   ▼
7. EventRecipientPackage.cost = Package.cost × quantity
   │
   ▼
8. Event.total_cost = Σ(EventRecipientPackage.cost)
```

## Migration Notes

### Database Changes

1. **New Table**: `package_finished_goods`
   - Create table with package_id, finished_good_id, quantity
   - Add indexes and foreign key constraints

2. **Drop Table**: `package_bundles` (if exists)
   - Data migration not needed (clean slate confirmed)

3. **No Changes**: `events`, `event_recipient_packages`, `recipients`, `packages`
   - Tables should already exist from Phase 3b
   - Re-enable in __init__.py only

### Code Changes

1. **src/models/__init__.py**:
   - Re-enable: Event, EventRecipientPackage, Package
   - Add: PackageFinishedGood
   - Remove references to: Bundle, PackageBundle

2. **src/models/package.py**:
   - Replace PackageBundle with PackageFinishedGood
   - Update relationship name and foreign key
   - Update calculate_cost() to use FinishedGood

3. **Services**:
   - Rewrite event_service.py (remove Bundle references)
   - Rewrite package_service.py (use FinishedGood)
   - Keep recipient_service.py (functional)

## Validation Rules

| Entity | Field | Rule |
|--------|-------|------|
| Package | name | Required, max 200 chars |
| Event | name | Required, max 200 chars |
| Event | year | Required, positive integer |
| Event | event_date | Required, valid date |
| Recipient | name | Required, max 200 chars |
| PackageFinishedGood | quantity | Required, positive integer |
| EventRecipientPackage | quantity | Required, positive integer |

## Indexes

| Table | Index | Columns | Purpose |
|-------|-------|---------|---------|
| packages | idx_package_name | name | Name search |
| packages | idx_package_is_template | is_template | Template filtering |
| events | idx_event_name | name | Name search |
| events | idx_event_year | year | Year filtering |
| events | idx_event_date | event_date | Date queries |
| recipients | idx_recipient_name | name | Name search |
| package_finished_goods | idx_package_fg_package | package_id | Package lookup |
| package_finished_goods | idx_package_fg_finished_good | finished_good_id | FinishedGood lookup |
| event_recipient_packages | idx_erp_event | event_id | Event lookup |
| event_recipient_packages | idx_erp_recipient | recipient_id | Recipient lookup |
| event_recipient_packages | idx_erp_package | package_id | Package lookup |
