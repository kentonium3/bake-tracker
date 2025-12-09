# Data Model: Nested Recipes (Sub-Recipe Components)

**Feature**: 012-nested-recipes
**Date**: 2025-12-09
**Status**: Complete

## Entity Overview

```
┌─────────────────┐         ┌─────────────────────┐
│     Recipe      │ 1    *  │   RecipeComponent   │
│─────────────────│─────────│─────────────────────│
│ id (PK)         │         │ id (PK)             │
│ name            │         │ recipe_id (FK)      │──┐
│ category        │         │ component_recipe_id │──┼─→ Recipe.id
│ yield_quantity  │         │   (FK)              │  │
│ yield_unit      │         │ quantity (Float)    │  │
│ ...             │         │ notes               │  │
└─────────────────┘         │ sort_order          │  │
        │                   └─────────────────────┘  │
        │                            ↑               │
        └────────────────────────────┴───────────────┘
              Recipe can be both parent and component
```

## New Entity: RecipeComponent

### Purpose

Junction table linking a parent recipe to a child (component) recipe. Enables hierarchical recipe structures where a recipe can contain other recipes as ingredients.

### Attributes

| Attribute | Type | Nullable | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | Integer | No | auto | Primary key (from BaseModel) |
| `uuid` | String(36) | No | auto | UUID identifier (from BaseModel) |
| `recipe_id` | Integer FK | No | - | Parent recipe that contains this component |
| `component_recipe_id` | Integer FK | No | - | Child recipe being used as component |
| `quantity` | Float | No | 1.0 | Batch multiplier (e.g., 2.0 = 2 batches) |
| `notes` | String(500) | Yes | null | Notes about this component usage |
| `sort_order` | Integer | No | 0 | Display order within parent recipe |
| `created_at` | DateTime | No | now | Creation timestamp (from BaseModel) |
| `updated_at` | DateTime | No | now | Last update timestamp (from BaseModel) |

### Foreign Keys

| Column | References | On Delete | Rationale |
|--------|------------|-----------|-----------|
| `recipe_id` | `recipes.id` | CASCADE | When parent deleted, remove component links |
| `component_recipe_id` | `recipes.id` | RESTRICT | Prevent deletion of recipe used as component |

### Constraints

| Constraint | Type | Expression | Purpose |
|------------|------|------------|---------|
| `ck_recipe_component_quantity_positive` | CHECK | `quantity > 0` | Batch multiplier must be positive |
| `ck_recipe_component_no_self_reference` | CHECK | `recipe_id != component_recipe_id` | Recipe cannot include itself |
| `uq_recipe_component_recipe_component` | UNIQUE | `(recipe_id, component_recipe_id)` | Same sub-recipe cannot be added twice to parent |

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_recipe_component_recipe` | `recipe_id` | Fast lookup of components for a recipe |
| `idx_recipe_component_component` | `component_recipe_id` | Fast lookup of recipes using a component |
| `idx_recipe_component_sort` | `recipe_id, sort_order` | Ordered component retrieval |

### Relationships

```python
# On RecipeComponent
recipe = relationship("Recipe", foreign_keys=[recipe_id], back_populates="recipe_components")
component_recipe = relationship("Recipe", foreign_keys=[component_recipe_id], back_populates="used_in_recipes")

# On Recipe (additions)
recipe_components = relationship(
    "RecipeComponent",
    foreign_keys="RecipeComponent.recipe_id",
    back_populates="recipe",
    cascade="all, delete-orphan",
)
used_in_recipes = relationship(
    "RecipeComponent",
    foreign_keys="RecipeComponent.component_recipe_id",
    back_populates="component_recipe",
)
```

## Modified Entity: Recipe

### New Relationships

| Relationship | Type | Purpose |
|--------------|------|---------|
| `recipe_components` | One-to-Many | Sub-recipes contained in this recipe |
| `used_in_recipes` | One-to-Many | Parent recipes that use this as component |

### Modified Methods

| Method | Change | Description |
|--------|--------|-------------|
| `calculate_cost()` | Extend | Include component recipe costs: `sum(component.quantity * component.component_recipe.calculate_cost())` |
| `to_dict()` | Extend | Include `recipe_components` and `total_cost_with_components` |

## Validation Rules (Service Layer)

### Circular Reference Detection

**Algorithm**: Before adding component, traverse the component tree to ensure no cycle:

```python
def _would_create_cycle(parent_id: int, component_id: int, session) -> bool:
    """Check if adding component would create circular reference."""
    visited = set()
    to_visit = [component_id]

    while to_visit:
        current = to_visit.pop()
        if current == parent_id:
            return True  # Cycle detected
        if current in visited:
            continue
        visited.add(current)

        # Get components of current recipe
        components = session.query(RecipeComponent).filter_by(recipe_id=current).all()
        for comp in components:
            to_visit.append(comp.component_recipe_id)

    return False
```

### Depth Limit Enforcement

**Algorithm**: Calculate depth of component recipe; reject if adding would exceed 3 levels:

```python
def _get_recipe_depth(recipe_id: int, session) -> int:
    """Get the maximum depth of recipe hierarchy."""
    components = session.query(RecipeComponent).filter_by(recipe_id=recipe_id).all()
    if not components:
        return 1  # Leaf recipe

    max_child_depth = 0
    for comp in components:
        child_depth = _get_recipe_depth(comp.component_recipe_id, session)
        max_child_depth = max(max_child_depth, child_depth)

    return 1 + max_child_depth

def _would_exceed_depth(parent_id: int, component_id: int, session) -> bool:
    """Check if adding component would exceed 3-level limit."""
    parent_depth = _get_recipe_depth(parent_id, session)
    component_depth = _get_recipe_depth(component_id, session)
    # Parent is at level N, component subtree adds component_depth levels
    # Total would be: (where parent is in hierarchy) + 1 + component_depth - 1
    # Simplified: need to ensure resulting max depth <= 3
    return parent_depth + component_depth > 3
```

### Deletion Protection

**Rule**: Recipe cannot be deleted if `used_in_recipes` is non-empty.

**Implementation**: RESTRICT foreign key on `component_recipe_id` enforces this at database level.

## Import/Export Schema

### Export Format (JSON)

```json
{
  "recipes": [
    {
      "name": "Frosted Layer Cake",
      "category": "Cakes",
      "yield_quantity": 1,
      "yield_unit": "cake",
      "ingredients": [...],
      "components": [
        {
          "recipe_name": "Chocolate Cake Layers",
          "quantity": 1.0,
          "notes": "Bake day before"
        },
        {
          "recipe_name": "Buttercream Frosting",
          "quantity": 2.0,
          "notes": null
        }
      ]
    }
  ]
}
```

### Import Rules

1. Import sub-recipes before parent recipes (topological sort or multi-pass)
2. If component recipe not found, log warning and skip component (don't fail entire import)
3. Match component by `recipe_name` (case-sensitive exact match)

## Migration Plan

### Forward Migration

```sql
CREATE TABLE recipe_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    recipe_id INTEGER NOT NULL,
    component_recipe_id INTEGER NOT NULL,
    quantity REAL NOT NULL DEFAULT 1.0,
    notes VARCHAR(500),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (component_recipe_id) REFERENCES recipes(id) ON DELETE RESTRICT,
    CONSTRAINT ck_recipe_component_quantity_positive CHECK (quantity > 0),
    CONSTRAINT ck_recipe_component_no_self_reference CHECK (recipe_id != component_recipe_id),
    CONSTRAINT uq_recipe_component_recipe_component UNIQUE (recipe_id, component_recipe_id)
);

CREATE INDEX idx_recipe_component_recipe ON recipe_components(recipe_id);
CREATE INDEX idx_recipe_component_component ON recipe_components(component_recipe_id);
CREATE INDEX idx_recipe_component_sort ON recipe_components(recipe_id, sort_order);
```

### Rollback Migration

```sql
DROP TABLE IF EXISTS recipe_components;
```

### Data Impact

- **No existing data modified** - New table only
- **Backward compatible** - Recipes without components continue to work identically
