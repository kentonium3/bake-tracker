# Data Model: Recipe Template & Snapshot System

**Feature**: F037-recipe-template-snapshot
**Created**: 2026-01-03
**Status**: Draft

## Entity Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│     Recipe      │────<│  RecipeSnapshot  │>────│  ProductionRun  │
│   (Template)    │     │   (Immutable)    │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │
        │ base_recipe_id (self-ref)
        ▼
┌─────────────────┐
│  Recipe Variant │
└─────────────────┘
```

## Entities

### Recipe (Modified)

**Purpose**: Mutable template that can be edited over time. Used for planning, browsing, and editing.

**New Fields**:
| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| base_recipe_id | Integer FK | Yes | NULL | Self-referential FK for variant relationship |
| variant_name | String(100) | Yes | NULL | Distinguishes variants (e.g., "Raspberry", "Strawberry") |
| is_production_ready | Boolean | No | False | Filters experimental vs proven recipes |

**Constraints**:
- `CHECK(base_recipe_id != id)` - Prevents self-referential variants
- `ON DELETE SET NULL` for base_recipe_id - Orphaned variants become standalone

**Relationships**:
- `variants` - One-to-many self-referential (recipes where base_recipe_id = this.id)
- `base_recipe` - Many-to-one self-referential (the parent recipe)
- `snapshots` - One-to-many to RecipeSnapshot

---

### RecipeSnapshot (New)

**Purpose**: Immutable capture of recipe state at production time. Used for historical costing and reporting.

**Fields**:
| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| id | Integer PK | No | Auto | Primary key |
| recipe_id | Integer FK | No | - | Source recipe (for history queries) |
| production_run_id | Integer FK | No | - | 1:1 link to production run |
| scale_factor | Float | No | 1.0 | Size multiplier per batch |
| snapshot_date | DateTime | No | utc_now | When snapshot was created |
| recipe_data | JSON/Text | No | - | Denormalized recipe metadata |
| ingredients_data | JSON/Text | No | - | Denormalized ingredient list |
| is_backfilled | Boolean | No | False | True for migrated historical data |

**JSON Schema for recipe_data**:
```json
{
  "name": "Thumbprint Cookies",
  "category": "Cookies",
  "source": "Grandma's cookbook",
  "yield_quantity": 36,
  "yield_unit": "cookies",
  "yield_description": "2-inch cookies",
  "estimated_time_minutes": 45,
  "notes": "Chill dough 30 min",
  "variant_name": "Raspberry"
}
```

**JSON Schema for ingredients_data**:
```json
[
  {
    "ingredient_id": 5,
    "ingredient_name": "All-Purpose Flour",
    "ingredient_slug": "all-purpose-flour",
    "quantity": 2.0,
    "unit": "cups",
    "notes": "sifted",
    "unit_cost_at_snapshot": 0.25,
    "total_cost": 0.50
  }
]
```

**Constraints**:
- `ON DELETE RESTRICT` for recipe_id - Cannot delete recipe with snapshots
- `UNIQUE(production_run_id)` - 1:1 relationship
- Immutability enforced at service layer (no update methods)

**Indexes**:
- `idx_snapshot_recipe` on recipe_id
- `idx_snapshot_date` on snapshot_date
- `idx_snapshot_production_run` on production_run_id

---

### ProductionRun (Modified)

**Purpose**: Records batch production events. Now links to snapshot instead of recipe.

**Modified Fields**:
| Field | Change | Description |
|-------|--------|-------------|
| recipe_id | DEPRECATED | Keep nullable for migration, remove in future |
| recipe_snapshot_id | NEW FK | Link to RecipeSnapshot (required for new runs) |
| scale_factor | REMOVED | Stored in snapshot instead |

**Note**: `num_batches` remains on ProductionRun as it's a production-time decision, while `scale_factor` moves to snapshot as it affects ingredient quantities.

**Migration Strategy**:
1. Add recipe_snapshot_id as nullable
2. Backfill snapshots for existing production runs (is_backfilled=True)
3. Set recipe_snapshot_id for all existing runs
4. Make recipe_snapshot_id non-nullable
5. Drop recipe_id FK (keep column for reference or remove)

---

### RecipeIngredient (Unchanged)

**Validation Addition**: `ingredient_id` must reference an Ingredient with `hierarchy_level = 2` (leaf only).

This validation is enforced at service layer, not schema level, to allow for migration flexibility.

---

## State Transitions

### Recipe Lifecycle
```
Created (is_production_ready=False)
    │
    ▼
Tested/Refined (editing allowed)
    │
    ▼
Marked Production Ready (is_production_ready=True)
    │
    ▼
Production Run → Snapshot Created
    │
    ▼
Recipe Modified → Historical snapshots preserved
```

### Snapshot Lifecycle
```
Production Started
    │
    ▼
Snapshot Created (immutable from this point)
    │
    ▼
Production Completed → Costs calculated from snapshot
    │
    ▼
Historical Reference (permanent)
```

---

## Relationships Summary

| From | To | Cardinality | FK Location | On Delete |
|------|-----|-------------|-------------|-----------|
| Recipe | Recipe (variant) | 1:N | Recipe.base_recipe_id | SET NULL |
| Recipe | RecipeSnapshot | 1:N | RecipeSnapshot.recipe_id | RESTRICT |
| RecipeSnapshot | ProductionRun | 1:1 | RecipeSnapshot.production_run_id | RESTRICT |
| ProductionRun | RecipeSnapshot | 1:1 | (via RecipeSnapshot) | - |

---

## Open Questions

1. **RecipeComponent in snapshots**: Spec says "direct ingredients only" - confirmed. Nested recipe snapshots deferred to Phase 3.

2. **Scale factor storage**: Should scale_factor be on ProductionRun or RecipeSnapshot?
   - **Decision**: RecipeSnapshot, because it affects ingredient quantity calculations which are snapshot-specific.

3. **Cost snapshot timing**: Capture costs at snapshot creation or calculate on-demand?
   - **Decision**: Capture at snapshot creation for true historical accuracy (ingredient costs may change).
