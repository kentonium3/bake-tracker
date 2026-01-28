# Data Model: Snapshot Export Coverage

**Feature**: F081 Snapshot Export Coverage
**Date**: 2026-01-28

## Overview

This document describes the 4 snapshot entity types that require export/import support. All snapshot models already exist (F037, F064) - this feature adds data portability.

## Entity Definitions

### RecipeSnapshot

**Source**: `src/models/recipe_snapshot.py` (Feature F037)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | Integer | No | Primary key |
| uuid | UUID | No | Unique identifier (BaseModel) |
| recipe_id | Integer FK | No | Reference to recipes.id |
| production_run_id | Integer FK | Yes | Reference to production_runs.id |
| scale_factor | Float | No | Batch size multiplier (default 1.0) |
| snapshot_date | DateTime | No | When snapshot was captured |
| recipe_data | Text (JSON) | No | Recipe metadata at snapshot time |
| ingredients_data | Text (JSON) | No | Ingredient list at snapshot time |
| is_backfilled | Boolean | No | True if created during migration |

**Export JSON Structure**:
```json
{
  "uuid": "string (UUID4)",
  "recipe_slug": "string",
  "snapshot_date": "ISO datetime",
  "scale_factor": 1.0,
  "recipe_data": "JSON string",
  "ingredients_data": "JSON string",
  "is_backfilled": false
}
```

### FinishedGoodSnapshot

**Source**: `src/models/finished_good_snapshot.py` (Feature F064)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | Integer | No | Primary key |
| uuid | UUID | No | Unique identifier (BaseModel) |
| finished_good_id | Integer FK | No | Reference to finished_goods.id |
| planning_snapshot_id | Integer FK | Yes | Reference to planning_snapshots.id |
| assembly_run_id | Integer FK | Yes | Reference to assembly_runs.id |
| snapshot_date | DateTime | No | When snapshot was captured |
| definition_data | Text (JSON) | No | FinishedGood definition with components |
| is_backfilled | Boolean | No | True if created during migration |

**Export JSON Structure**:
```json
{
  "uuid": "string (UUID4)",
  "finished_good_slug": "string",
  "snapshot_date": "ISO datetime",
  "definition_data": "JSON string",
  "is_backfilled": false
}
```

### MaterialUnitSnapshot

**Source**: `src/models/material_unit_snapshot.py` (Feature F064)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | Integer | No | Primary key |
| uuid | UUID | No | Unique identifier (BaseModel) |
| material_unit_id | Integer FK | No | Reference to material_units.id |
| planning_snapshot_id | Integer FK | Yes | Reference to planning_snapshots.id |
| assembly_run_id | Integer FK | Yes | Reference to assembly_runs.id |
| snapshot_date | DateTime | No | When snapshot was captured |
| definition_data | Text (JSON) | No | MaterialUnit definition |
| is_backfilled | Boolean | No | True if created during migration |

**Export JSON Structure**:
```json
{
  "uuid": "string (UUID4)",
  "material_unit_slug": "string",
  "snapshot_date": "ISO datetime",
  "definition_data": "JSON string",
  "is_backfilled": false
}
```

### FinishedUnitSnapshot

**Source**: `src/models/finished_unit_snapshot.py` (Feature F064)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| id | Integer | No | Primary key |
| uuid | UUID | No | Unique identifier (BaseModel) |
| finished_unit_id | Integer FK | No | Reference to finished_units.id |
| planning_snapshot_id | Integer FK | Yes | Reference to planning_snapshots.id |
| assembly_run_id | Integer FK | Yes | Reference to assembly_runs.id |
| snapshot_date | DateTime | No | When snapshot was captured |
| definition_data | Text (JSON) | No | FinishedUnit definition |
| is_backfilled | Boolean | No | True if created during migration |

**Export JSON Structure**:
```json
{
  "uuid": "string (UUID4)",
  "finished_unit_slug": "string",
  "snapshot_date": "ISO datetime",
  "definition_data": "JSON string",
  "is_backfilled": false
}
```

## FK Resolution Strategy

### Export

Each snapshot exports its parent reference as a **slug** field for portable identification:

| Snapshot Type | Parent FK | Export Field |
|--------------|-----------|--------------|
| RecipeSnapshot | recipe_id | recipe_slug |
| FinishedGoodSnapshot | finished_good_id | finished_good_slug |
| MaterialUnitSnapshot | material_unit_id | material_unit_slug |
| FinishedUnitSnapshot | finished_unit_id | finished_unit_slug |

### Import

Import resolves parent FK by slug lookup:

```python
# Example: RecipeSnapshot
recipe = session.query(Recipe).filter(Recipe.slug == recipe_slug).first()
if not recipe:
    logger.warning(f"RecipeSnapshot skipped: recipe '{recipe_slug}' not found")
    continue  # Skip this snapshot
recipe_id = recipe.id
```

## Dependency Order

Snapshots must be imported AFTER their parent entities:

| Entity Type | Import Order | Dependencies |
|-------------|--------------|--------------|
| recipes | 4 | [ingredients] |
| finished_goods | 15 | [] |
| material_units | 12 | [materials] |
| finished_units | 5 | [recipes] |
| **recipe_snapshots** | **19** | [recipes] |
| **finished_good_snapshots** | **20** | [finished_goods] |
| **material_unit_snapshots** | **21** | [material_units] |
| **finished_unit_snapshots** | **22** | [finished_units] |

## Export File Naming

| Entity Type | Filename |
|-------------|----------|
| RecipeSnapshot | recipe_snapshots.json |
| FinishedGoodSnapshot | finished_good_snapshots.json |
| MaterialUnitSnapshot | material_unit_snapshots.json |
| FinishedUnitSnapshot | finished_unit_snapshots.json |

## Data Preservation Rules

1. **UUID Preservation**: Import uses exact UUID from export (FR-010)
2. **Timestamp Preservation**: Import uses exact snapshot_date (FR-011)
3. **JSON Preservation**: recipe_data, ingredients_data, definition_data copied exactly (FR-012)
4. **Export Order**: Snapshots exported chronologically (oldest first) (FR-015)

## Relationship Diagram

```
Recipe ←─────────── RecipeSnapshot
  │                      │
  │ slug ◄───────────── recipe_slug
  │
FinishedGood ←────── FinishedGoodSnapshot
  │                      │
  │ slug ◄───────────── finished_good_slug
  │
MaterialUnit ←────── MaterialUnitSnapshot
  │                      │
  │ slug ◄───────────── material_unit_slug
  │
FinishedUnit ←────── FinishedUnitSnapshot
  │                      │
  │ slug ◄───────────── finished_unit_slug
```

## Notes

- Context FKs (planning_snapshot_id, assembly_run_id, production_run_id) are NOT exported/imported in this feature - those are out of scope (see spec.md Out of Scope section)
- Snapshot models already exist and are in use - this feature only adds data portability
