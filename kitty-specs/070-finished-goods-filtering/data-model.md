# Data Model: F070 Finished Goods Filtering

**Date**: 2026-01-26
**Feature**: 070-finished-goods-filtering

## Overview

This feature uses existing models with no schema changes. Key relationships:

```
Event
├── event_recipes: List[EventRecipe] (F069)
│   └── recipe_id → Recipe
└── event_finished_goods: List[EventFinishedGood]
    └── finished_good_id → FinishedGood

FinishedGood (bundle)
└── components: List[Composition]
    ├── finished_unit_id → FinishedUnit → recipe_id → Recipe
    └── finished_good_id → FinishedGood (nested, recurse)
```

## Existing Models (Read Only)

### FinishedGood

**File**: `src/models/finished_good.py`

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| slug | String | Unique identifier |
| display_name | String | User-visible name |
| components | Relationship | → Composition (lazy="joined") |

**Note**: NO `recipe_id` field. Recipes are determined by traversing `components`.

### FinishedUnit

**File**: `src/models/finished_unit.py`

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| recipe_id | Integer | FK → Recipe (CASCADE) |
| recipe | Relationship | → Recipe (lazy="joined") |

**Note**: This is the atomic item that links to a Recipe.

### Composition

**File**: `src/models/composition.py`

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| assembly_id | Integer | FK → FinishedGood (parent bundle) |
| finished_unit_id | Integer | FK → FinishedUnit (nullable) |
| finished_good_id | Integer | FK → FinishedGood (nullable, nested bundle) |
| component_quantity | Float | Quantity of component |

**Constraint**: Exactly one of `finished_unit_id`, `finished_good_id`, or other component types must be non-null.

### EventRecipe (F069)

**File**: `src/models/event_recipe.py`

| Field | Type | Description |
|-------|------|-------------|
| event_id | Integer | FK → Event (CASCADE) |
| recipe_id | Integer | FK → Recipe (RESTRICT) |

### EventFinishedGood

**File**: `src/models/event_finished_good.py`

| Field | Type | Description |
|-------|------|-------------|
| event_id | Integer | FK → Event (CASCADE) |
| finished_good_id | Integer | FK → FinishedGood (RESTRICT) |
| quantity | Integer | Quantity to produce (>0) |

## Service Layer DTOs

### AvailabilityResult (New)

```python
@dataclass
class AvailabilityResult:
    """Result of checking FG availability."""
    is_available: bool
    required_recipe_ids: Set[int]
    missing_recipe_ids: Set[int]
    fg_id: int
    fg_name: str
```

### RemovedFGInfo (New)

```python
@dataclass
class RemovedFGInfo:
    """Info about an FG that was auto-removed."""
    fg_id: int
    fg_name: str
    missing_recipes: List[str]  # Recipe names for notification
```

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                          Event                               │
│  (Planning event selected by user)                          │
└─────────────────────────────────────────────────────────────┘
         │                              │
         │ event_recipes                │ event_finished_goods
         ▼                              ▼
┌─────────────────┐            ┌─────────────────────┐
│   EventRecipe   │            │  EventFinishedGood  │
│  (junction)     │            │     (junction)      │
└─────────────────┘            └─────────────────────┘
         │                              │
         │ recipe_id                    │ finished_good_id
         ▼                              ▼
┌─────────────────┐            ┌─────────────────────┐
│     Recipe      │◄───────────│    FinishedGood     │
│ (what to make)  │            │ (bundle/assembly)   │
└─────────────────┘            └─────────────────────┘
         ▲                              │
         │                              │ components
         │ recipe_id                    ▼
┌─────────────────┐            ┌─────────────────────┐
│  FinishedUnit   │◄───────────│    Composition      │
│ (atomic item)   │            │ (junction to parts) │
└─────────────────┘            └─────────────────────┘
                                        │
                                        │ finished_good_id
                                        ▼
                               ┌─────────────────────┐
                               │    FinishedGood     │
                               │   (nested bundle)   │
                               └─────────────────────┘
```

## Decomposition Algorithm

**Input**: `finished_good_id`
**Output**: `Set[int]` (recipe IDs required)

```
function get_required_recipes(fg_id, visited={}, depth=0):
    if depth > 10: raise MaxDepthExceededError
    if fg_id in visited: raise CircularReferenceError
    visited.add(fg_id)

    fg = query(FinishedGood, fg_id)
    recipes = set()

    for comp in fg.components:
        if comp.finished_unit_id:
            # Atomic: get recipe directly
            recipes.add(comp.finished_unit_component.recipe_id)
        elif comp.finished_good_id:
            # Nested bundle: recurse
            child = get_required_recipes(comp.finished_good_id, visited, depth+1)
            recipes.update(child)
        # else: packaging/material component - no recipe needed

    return recipes
```

## Availability Check Flow

```
1. User selects event
2. Load event's selected recipe IDs (F069)
3. For each FinishedGood in catalog:
   a. Decompose to required recipe IDs
   b. Check if required ⊆ selected
   c. If yes → available
   d. If no → unavailable (hidden)
4. Display only available FGs
```

## Cascade Removal Flow

```
1. User deselects a recipe
2. set_event_recipes() called with new list
3. After updating EventRecipe:
   a. Get current EventFinishedGood selections
   b. For each selected FG:
      - Decompose to required recipes
      - Check if all required are still selected
      - If not → mark for removal
   c. Delete marked EventFinishedGood records
   d. Return list of removed FGs for notification
4. UI shows notification with removed FG names
```
