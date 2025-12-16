# Data Model: Unit Reference Table & UI Dropdowns

**Feature**: 022-unit-reference-table
**Date**: 2025-12-16
**Status**: Complete

## Entity Overview

This feature introduces one new entity (Unit) with no changes to existing entities. The Unit table is a reference table - other entities continue to store unit values as strings (not foreign keys).

## New Entities

### Unit

Reference table storing all valid measurement units.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto | Primary key (from BaseModel) |
| uuid | String(36) | Unique, Not Null | UUID identifier (from BaseModel) |
| code | String(20) | Unique, Not Null, Index | Unit code stored in other tables (e.g., "oz", "cup") |
| display_name | String(50) | Not Null | Human-readable name (e.g., "ounce", "cup") |
| symbol | String(20) | Not Null | Display symbol in UI (e.g., "oz", "cup") |
| category | String(20) | Not Null, Index | Unit category: "weight", "volume", "count", "package" |
| un_cefact_code | String(10) | Nullable | UN/CEFACT standard code (future use) |
| sort_order | Integer | Not Null, Default 0 | Display order within category |
| created_at | DateTime | Not Null | From BaseModel |
| updated_at | DateTime | Not Null | From BaseModel |

**Table Name**: `units`

**Indexes**:
- `idx_unit_code` on `code` (unique)
- `idx_unit_category` on `category`

**Relationships**: None (reference table only)

## Seed Data

The following 27 units will be seeded from `src/utils/constants.py`:

### Weight Units (4)
| code | display_name | symbol | un_cefact_code |
|------|--------------|--------|----------------|
| oz | ounce | oz | ONZ |
| lb | pound | lb | LBR |
| g | gram | g | GRM |
| kg | kilogram | kg | KGM |

### Volume Units (9)
| code | display_name | symbol | un_cefact_code |
|------|--------------|--------|----------------|
| tsp | teaspoon | tsp | - |
| tbsp | tablespoon | tbsp | - |
| cup | cup | cup | - |
| ml | milliliter | ml | MLT |
| l | liter | l | LTR |
| fl oz | fluid ounce | fl oz | OZA |
| pt | pint | pt | PTI |
| qt | quart | qt | QTI |
| gal | gallon | gal | GLL |

### Count Units (4)
| code | display_name | symbol | un_cefact_code |
|------|--------------|--------|----------------|
| each | each | ea | EA |
| count | count | ct | - |
| piece | piece | pc | PCE |
| dozen | dozen | dz | DZN |

### Package Units (10)
| code | display_name | symbol | un_cefact_code |
|------|--------------|--------|----------------|
| bag | bag | bag | BG |
| box | box | box | BX |
| bar | bar | bar | - |
| bottle | bottle | bottle | BO |
| can | can | can | CA |
| jar | jar | jar | JR |
| packet | packet | packet | PA |
| container | container | container | - |
| package | package | pkg | PK |
| case | case | case | CS |

## Existing Entity Impacts

### No Schema Changes Required

The following entities store unit values as strings and will **not** change:

| Entity | Field | Impact |
|--------|-------|--------|
| Product | package_unit | UI changes only - dropdown instead of text |
| Ingredient | density_volume_unit | UI changes only - dropdown instead of text |
| Ingredient | density_weight_unit | UI changes only - dropdown instead of text |
| RecipeIngredient | unit | UI changes only - dropdown instead of text |
| Recipe | yield_unit | **NO CHANGE** - stays free-form text |

**Rationale**: Using string references (not FKs) maintains backward compatibility with existing data and import/export functionality. The Unit table serves as a reference for UI dropdowns, not as a constraint enforced by foreign keys.

## Validation Rules

1. **Unit.code**: Must be unique, lowercase, max 20 characters
2. **Unit.category**: Must be one of: "weight", "volume", "count", "package"
3. **Unit.sort_order**: Used for display ordering within dropdown categories

## State Transitions

Not applicable - Unit is a static reference table with no state changes.

## Data Flow

```
Application Startup
       │
       ▼
init_database()
       │
       ▼
seed_units() ◄─── constants.py (WEIGHT_UNITS, VOLUME_UNITS, COUNT_UNITS, PACKAGE_UNITS)
       │
       ▼
units table populated
       │
       ▼
UI Forms query units by category for dropdowns
```

## Migration Notes

Per Constitution VI (Schema Change Strategy for Desktop Phase):
- No migration script needed
- New table created automatically by SQLAlchemy on startup
- Seeding is idempotent (check if empty before inserting)
- Existing data in other tables is unchanged
