# Data Model: Ingredient Auto-Slug & Deletion Protection

**Feature**: 035-ingredient-auto-slug
**Date**: 2026-01-02

## Schema Changes

### SnapshotIngredient - Add Denormalization Fields

**File**: `src/models/inventory_snapshot.py`

**Current Schema**:
```python
class SnapshotIngredient(BaseModel):
    __tablename__ = "snapshot_ingredients"

    snapshot_id = Column(Integer, ForeignKey("inventory_snapshots.id", ondelete="CASCADE"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"))
    quantity = Column(Float, nullable=False, default=0.0)
```

**New Schema**:
```python
class SnapshotIngredient(BaseModel):
    __tablename__ = "snapshot_ingredients"

    snapshot_id = Column(Integer, ForeignKey("inventory_snapshots.id", ondelete="CASCADE"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Float, nullable=False, default=0.0)

    # Denormalized fields for historical preservation (F035)
    ingredient_name_snapshot = Column(String(200), nullable=True)
    parent_l1_name_snapshot = Column(String(200), nullable=True)
    parent_l0_name_snapshot = Column(String(200), nullable=True)
```

**Changes**:
| Field | Change | Rationale |
|-------|--------|-----------|
| `ingredient_id` | `RESTRICT` → `SET NULL`, nullable=True | Allow nullification after denormalization |
| `ingredient_name_snapshot` | NEW | Preserve L2 ingredient name |
| `parent_l1_name_snapshot` | NEW | Preserve L1 parent name |
| `parent_l0_name_snapshot` | NEW | Preserve L0 root name |

### IngredientAlias - Verify Cascade Delete

**File**: `src/models/ingredient_alias.py`

**Required Configuration**:
```python
ingredient_id = Column(
    Integer,
    ForeignKey("ingredients.id", ondelete="CASCADE"),
    nullable=False
)
```

### IngredientCrosswalk - Verify Cascade Delete

**File**: `src/models/ingredient_crosswalk.py`

**Required Configuration**:
```python
ingredient_id = Column(
    Integer,
    ForeignKey("ingredients.id", ondelete="CASCADE"),
    nullable=False
)
```

## Entity Relationships

```
Ingredient (catalog entity - protected)
    │
    ├── Product.ingredient_id (FK) ── BLOCKS deletion
    │
    ├── RecipeIngredient.ingredient_id (FK) ── BLOCKS deletion
    │
    ├── SnapshotIngredient.ingredient_id (FK) ── DENORMALIZE then NULLIFY
    │
    ├── IngredientAlias.ingredient_id (FK) ── CASCADE delete
    │
    └── IngredientCrosswalk.ingredient_id (FK) ── CASCADE delete
```

## Deletion Flow State Machine

```
                    ┌─────────────────┐
                    │ Delete Request  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Check Products  │
                    └────────┬────────┘
                             │
               ┌─────────────┴─────────────┐
               │ count > 0                 │ count = 0
               ▼                           ▼
        ┌──────────────┐          ┌────────────────┐
        │ BLOCK        │          │ Check Recipes  │
        │ (show count) │          └───────┬────────┘
        └──────────────┘                  │
                             ┌────────────┴────────────┐
                             │ count > 0               │ count = 0
                             ▼                         ▼
                      ┌──────────────┐        ┌────────────────┐
                      │ BLOCK        │        │ Check Children │
                      │ (show count) │        └───────┬────────┘
                      └──────────────┘                │
                                         ┌────────────┴────────────┐
                                         │ count > 0               │ count = 0
                                         ▼                         ▼
                                  ┌──────────────┐        ┌─────────────────┐
                                  │ BLOCK        │        │ Denormalize     │
                                  │ (show count) │        │ Snapshots       │
                                  └──────────────┘        └────────┬────────┘
                                                                   │
                                                          ┌────────▼────────┐
                                                          │ Nullify Snapshot│
                                                          │ FKs             │
                                                          └────────┬────────┘
                                                                   │
                                                          ┌────────▼────────┐
                                                          │ CASCADE delete  │
                                                          │ Alias/Crosswalk │
                                                          └────────┬────────┘
                                                                   │
                                                          ┌────────▼────────┐
                                                          │ DELETE          │
                                                          │ Ingredient      │
                                                          └─────────────────┘
```

## Validation Rules

### Pre-Deletion Validation

| Check | Entity | Behavior |
|-------|--------|----------|
| Product references | Product | BLOCK if count > 0 |
| Recipe references | RecipeIngredient | BLOCK if count > 0 |
| Child ingredients | Ingredient | BLOCK if count > 0 |
| Snapshot references | SnapshotIngredient | DENORMALIZE + NULLIFY |
| Alias references | IngredientAlias | CASCADE (automatic) |
| Crosswalk references | IngredientCrosswalk | CASCADE (automatic) |

### Denormalization Logic

Before nullifying `SnapshotIngredient.ingredient_id`:

```python
def denormalize_snapshot_ingredient(snapshot_ing, ingredient, session):
    """Copy ingredient hierarchy names to snapshot before deletion."""
    snapshot_ing.ingredient_name_snapshot = ingredient.display_name

    ancestors = ingredient_hierarchy_service.get_ancestors(ingredient.id, session)

    if len(ancestors) >= 1:
        # First ancestor is immediate parent (L1 for L2 ingredient)
        snapshot_ing.parent_l1_name_snapshot = ancestors[0].display_name

    if len(ancestors) >= 2:
        # Second ancestor is grandparent (L0 for L2 ingredient)
        snapshot_ing.parent_l0_name_snapshot = ancestors[1].display_name
```

## Migration Strategy

Per constitution (Section VI: Schema Change Strategy), use export/reset/import cycle:

1. Export all data to JSON
2. Update model definitions
3. Delete database, recreate with new schema
4. Transform JSON if needed (add null values for new fields)
5. Import transformed data

**New Fields Default**: All three snapshot fields default to NULL for existing records.
