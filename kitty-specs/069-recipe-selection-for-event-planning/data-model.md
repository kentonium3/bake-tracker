# Data Model: Recipe Selection for Event Planning

**Feature**: 069-recipe-selection-for-event-planning
**Date**: 2026-01-26
**Status**: Complete

## Overview

This feature uses **existing data models** from F068 and the Recipe module. No schema changes are required.

## Existing Entities (Read-Only)

### Recipe

**Location**: `src/models/recipe.py`

**Relevant Fields for Selection**:

| Field | Type | Purpose |
|-------|------|---------|
| `id` | Integer (PK) | Recipe identifier |
| `name` | String(200) | Display name |
| `base_recipe_id` | FK to Recipe.id | NULL = base recipe, NOT NULL = variant |
| `variant_name` | String(100) | Variant label (e.g., "Raspberry") |
| `is_archived` | Boolean | Soft-delete flag (exclude from selection) |
| `is_production_ready` | Boolean | Production readiness status |

**Key Relationships**:
```
Recipe (base)
├── base_recipe_id = NULL
└── variants → [Recipe where base_recipe_id = this.id]

Recipe (variant)
├── base_recipe_id = parent.id
└── base_recipe → Recipe (self-referential)
```

**Identification Logic**:
```python
def is_variant(recipe: Recipe) -> bool:
    return recipe.base_recipe_id is not None

def is_base(recipe: Recipe) -> bool:
    return recipe.base_recipe_id is None
```

### Event

**Location**: `src/models/event.py`

**Relevant Fields**:

| Field | Type | Purpose |
|-------|------|---------|
| `id` | Integer (PK) | Event identifier |
| `name` | String(200) | Event display name |
| `event_recipes` | Relationship | Collection of EventRecipe associations |

**Relationship to EventRecipe**:
```python
event_recipes = relationship(
    "EventRecipe",
    back_populates="event",
    cascade="all, delete-orphan",
    lazy="selectin",
)
```

### EventRecipe (Junction Table)

**Location**: `src/models/event_recipe.py`

**Full Structure**:

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| `id` | Integer (PK) | Auto-increment | Record identifier |
| `event_id` | FK to events.id | NOT NULL, CASCADE | Parent event |
| `recipe_id` | FK to recipes.id | NOT NULL, RESTRICT | Selected recipe |
| `created_at` | DateTime | Default=utc_now | Selection timestamp |

**Constraints**:
```sql
UNIQUE(event_id, recipe_id)  -- Prevent duplicate selections
```

**Cascade Behavior**:
- Delete Event → Deletes all EventRecipe for that event
- Delete Recipe → BLOCKED if EventRecipe references it

## Service Method Signatures

### New Methods for event_service.py

```python
def set_event_recipes(
    session: Session,
    event_id: int,
    recipe_ids: List[int],
) -> int:
    """
    Replace all recipe selections for an event.

    Args:
        session: Database session
        event_id: Target event ID
        recipe_ids: List of recipe IDs to select (empty list clears all)

    Returns:
        Number of recipes now selected

    Raises:
        ValidationError: If event not found or recipe ID invalid
    """

def get_event_recipe_ids(
    session: Session,
    event_id: int,
) -> List[int]:
    """
    Get IDs of all recipes selected for an event.

    Args:
        session: Database session
        event_id: Target event ID

    Returns:
        List of selected recipe IDs (empty if none)

    Raises:
        ValidationError: If event not found
    """
```

## Data Flow

### Selection Flow

```
User checks recipes in UI
        ↓
RecipeSelectionFrame tracks selections (BooleanVar per recipe)
        ↓
User clicks "Save"
        ↓
Collect selected recipe IDs from UI state
        ↓
event_service.set_event_recipes(session, event_id, recipe_ids)
        ↓
Delete existing EventRecipe for event_id
        ↓
Insert new EventRecipe for each recipe_id
        ↓
Commit transaction
```

### Load Flow

```
User selects event in PlanningTab
        ↓
event_service.get_event_recipe_ids(session, event_id)
        ↓
Query EventRecipe WHERE event_id = X
        ↓
Return list of recipe_ids
        ↓
RecipeSelectionFrame.set_selected(recipe_ids)
        ↓
Update checkbox states (checked for selected, unchecked for others)
```

## Queries

### Get All Recipes for Selection

```python
session.query(Recipe).filter(
    Recipe.is_archived == False
).order_by(Recipe.name).all()
```

### Get Selected Recipe IDs

```python
session.query(EventRecipe.recipe_id).filter(
    EventRecipe.event_id == event_id
).all()
```

### Replace Selections

```python
# Delete existing
session.query(EventRecipe).filter(
    EventRecipe.event_id == event_id
).delete()

# Insert new
for recipe_id in recipe_ids:
    session.add(EventRecipe(event_id=event_id, recipe_id=recipe_id))
```

## Validation Rules

| Rule | Location | Error |
|------|----------|-------|
| Event must exist | set_event_recipes | ValidationError("Event not found") |
| Recipe must exist | set_event_recipes | ValidationError("Recipe {id} not found") |
| No duplicates | DB constraint | IntegrityError (handled) |

## Import/Export Impact

**Already Supported** (from F068):
- EventRecipe records included in export
- EventRecipe records imported with FK resolution
- Round-trip tested in `test_import_export_planning.py`

**No Changes Needed**: This feature uses existing import/export support.
