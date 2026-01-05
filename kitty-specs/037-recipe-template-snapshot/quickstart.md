# Quickstart: F037 Recipe Template & Snapshot System

## Overview

This feature implements a Template/Snapshot architecture for recipes:
- **Recipe (Template)**: Mutable definition that can be edited over time
- **RecipeSnapshot (Instance)**: Immutable capture of recipe state at production time

## Key Concepts

### Template vs Snapshot
```
Recipe Template (editable)         RecipeSnapshot (immutable)
├── name: "Thumbprint Cookies"     ├── recipe_data: { name, yield, ... }
├── yield_quantity: 36             ├── ingredients_data: [ {...}, {...} ]
├── recipe_ingredients: [...]  --> ├── scale_factor: 1.0
└── is_production_ready: true      └── snapshot_date: 2026-01-03
                                          │
                                          ▼
                                   ProductionRun
                                   ├── num_batches: 2
                                   └── actual_yield: 72
```

### Scaling Formula
- **Expected Yield** = `base_yield × scale_factor × num_batches`
- **Ingredient Quantity** = `base_quantity × scale_factor × num_batches`

Example: Recipe yields 36 cookies, producing 2 batches at 2x scale:
- Expected: 36 × 2 × 2 = 144 cookies
- Flour (2 cups base): 2 × 2 × 2 = 8 cups needed

## New Database Entities

### RecipeSnapshot (NEW)
```python
class RecipeSnapshot(BaseModel):
    __tablename__ = "recipe_snapshots"

    recipe_id = Column(Integer, FK("recipes.id", ondelete="RESTRICT"))
    production_run_id = Column(Integer, FK("production_runs.id"), unique=True)
    scale_factor = Column(Float, default=1.0)
    snapshot_date = Column(DateTime, default=utc_now)
    recipe_data = Column(Text)  # JSON
    ingredients_data = Column(Text)  # JSON
    is_backfilled = Column(Boolean, default=False)
```

### Recipe Additions
```python
# In Recipe model
base_recipe_id = Column(Integer, FK("recipes.id", ondelete="SET NULL"))
variant_name = Column(String(100), nullable=True)
is_production_ready = Column(Boolean, default=False)
```

## Key Service Functions

### Create Snapshot (NEW)
```python
def create_recipe_snapshot(
    recipe_id: int,
    scale_factor: float,
    production_run_id: int,
    session=None
) -> dict:
    """Create immutable snapshot of recipe at production time."""
```

### Modified Production Flow
```python
def record_batch_production(..., scale_factor: float = 1.0, ...):
    # 1. Create snapshot FIRST (captures recipe state)
    snapshot = create_recipe_snapshot(recipe_id, scale_factor, production_run_id, session)

    # 2. Calculate quantities using snapshot
    for ingredient in snapshot.ingredients_data:
        quantity_needed = ingredient.quantity * scale_factor * num_batches
        consume_fifo(...)

    # 3. Create production run linked to snapshot
    production_run = ProductionRun(recipe_snapshot_id=snapshot.id, ...)
```

## UI Changes

### Recipe Form
- Add: `is_production_ready` checkbox (default unchecked)
- Add: `base_recipe_id` dropdown (optional, for variants)
- Add: `variant_name` text field (optional)

### Recipe List
- Variants indented under base recipe
- Filter: "Production Ready Only" checkbox
- Display variant count badge

### Production Dialog
- Add: `scale_factor` input (default 1.0)
- Show: Calculated expected yield with scaling
- Show: Ingredient requirements scaled

### Recipe History View
- List of snapshots with dates
- View snapshot details
- "Create Recipe from Snapshot" button

## Migration Strategy

1. Add new columns/tables (nullable where needed)
2. For existing ProductionRuns:
   - Create snapshots from current recipe state
   - Set `is_backfilled = True`
   - Update FK to recipe_snapshot_id
3. Make recipe_snapshot_id required
4. Deprecate direct recipe_id on ProductionRun

## Testing Checklist

- [ ] Create recipe, run production, modify recipe, verify historical cost unchanged
- [ ] Create variant, verify linked to base
- [ ] Production with scale_factor > 1 calculates correctly
- [ ] is_production_ready filter works
- [ ] Snapshot is immutable (no update path)
- [ ] Delete recipe blocked if snapshots exist
- [ ] Migration creates backfilled snapshots correctly
