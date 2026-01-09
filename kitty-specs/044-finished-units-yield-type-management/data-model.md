# Data Model: Finished Units Yield Type Management

**Feature**: 044-finished-units-yield-type-management
**Date**: 2026-01-09

## Entity Overview

This feature uses existing models with one modification. No new tables required.

## Entity: FinishedUnit (Existing - Modify)

**Location**: `src/models/finished_unit.py`

**Purpose**: Represents yield types (finished products) that a recipe produces.

### Core Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto | Primary key |
| slug | String(100) | Unique, Not Null, Index | URL-safe identifier |
| display_name | String(200) | Not Null, Index | User-visible name |
| recipe_id | Integer | FK(recipes.id), Not Null | Parent recipe |
| items_per_batch | Integer | Nullable, >0 | Units per batch (discrete mode) |
| yield_mode | Enum | Not Null, Default DISCRETE_COUNT | DISCRETE_COUNT or BATCH_PORTION |
| item_unit | String(50) | Nullable | Unit name (cookie, truffle) |

### Fields Used by This Feature

- **display_name**: Name shown in UI (e.g., "Large Cookie")
- **items_per_batch**: How many per batch (e.g., 30)
- **recipe_id**: Links to parent Recipe

### Required Modification

```python
# BEFORE (line 84):
recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)

# AFTER:
recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
```

**Reason**: Per clarification session 2026-01-09, when a Recipe is deleted, its FinishedUnits should cascade delete.

## Entity: Recipe (Existing - No Changes)

**Location**: `src/models/recipe.py`

**Purpose**: Parent entity for FinishedUnits.

### Relevant Relationship

```python
# Line 99 - already exists
finished_units = relationship("FinishedUnit", back_populates="recipe")
```

**Note**: No cascade delete on relationship side - it's handled by the FK constraint.

## Entity Relationship Diagram

```
┌─────────────────────────────────────┐
│              Recipe                  │
├─────────────────────────────────────┤
│ id (PK)                             │
│ name                                │
│ category                            │
│ yield_quantity                      │
│ yield_unit                          │
│ ...                                 │
├─────────────────────────────────────┤
│ finished_units → [FinishedUnit]     │ (one-to-many)
└─────────────────────────────────────┘
                │
                │ FK: recipe_id (CASCADE)
                ▼
┌─────────────────────────────────────┐
│           FinishedUnit              │
├─────────────────────────────────────┤
│ id (PK)                             │
│ slug (Unique)                       │
│ display_name                        │
│ recipe_id (FK → recipes.id)         │
│ items_per_batch                     │
│ yield_mode                          │
│ ...                                 │
└─────────────────────────────────────┘
```

## Validation Rules

### FinishedUnit Validation

| Rule | Field(s) | Implementation |
|------|----------|----------------|
| Required name | display_name | Service validates not empty |
| Positive batch size | items_per_batch | DB constraint + service validation |
| Unique name per recipe | display_name + recipe_id | **NEW**: Service validation needed |
| Max name length | display_name | DB constraint (200 chars) |

### New Validation: Name Uniqueness Per Recipe

```python
# Add to FinishedUnitService.create_finished_unit():
def _validate_name_unique_in_recipe(
    self, display_name: str, recipe_id: int, session, exclude_id: int = None
) -> bool:
    """Check if display_name is unique within the recipe."""
    query = session.query(FinishedUnit).filter(
        FinishedUnit.recipe_id == recipe_id,
        FinishedUnit.display_name == display_name
    )
    if exclude_id:
        query = query.filter(FinishedUnit.id != exclude_id)
    return query.first() is None
```

## State Transitions

FinishedUnits have no explicit state machine. They follow the recipe's save lifecycle:

```
[Recipe Edit Form]
       │
       ▼
┌──────────────────┐
│ Pending Changes  │  (in-memory, not saved)
│ - Added units    │
│ - Modified units │
│ - Deleted units  │
└──────────────────┘
       │
       │ User clicks "Save Recipe"
       ▼
┌──────────────────┐
│   Persisted      │  (committed to database)
└──────────────────┘
```

## Data Volume Assumptions

| Metric | Expected Range | Notes |
|--------|----------------|-------|
| Recipes | 50-200 | Typical home baker |
| FinishedUnits per Recipe | 1-5 | Most recipes have 1-3 yield types |
| Total FinishedUnits | 100-500 | Manageable for local SQLite |

## Migration Considerations

### Existing Data Check

Before changing FK from RESTRICT to CASCADE, verify no orphaned records:

```sql
-- Should return 0 rows if data is clean
SELECT fu.* FROM finished_units fu
LEFT JOIN recipes r ON fu.recipe_id = r.id
WHERE r.id IS NULL;
```

### Migration Approach

The FK constraint change can be handled by:
1. SQLite doesn't enforce FK constraints unless PRAGMA foreign_keys=ON
2. Recreation of table may be needed for strict FK change
3. For this project, dropping and recreating the constraint is acceptable since it's a single-user desktop app

**Recommended**: Handle in model definition only (SQLAlchemy will use correct FK on new DB creation). For existing DBs, the behavioral change is handled at application level by the cascade delete in service layer.
