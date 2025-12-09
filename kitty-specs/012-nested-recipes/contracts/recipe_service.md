# Service Contract: Recipe Service Extensions

**Feature**: 012-nested-recipes
**Module**: `src/services/recipe_service.py`
**Date**: 2025-12-09

## Overview

Extensions to the existing `recipe_service.py` for managing recipe components (sub-recipes).

---

## New Functions

### `add_recipe_component`

Add an existing recipe as a component of another recipe.

```python
def add_recipe_component(
    recipe_id: int,
    component_recipe_id: int,
    quantity: float = 1.0,
    notes: str = None,
    sort_order: int = None
) -> RecipeComponent:
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `recipe_id` | int | Yes | Parent recipe ID |
| `component_recipe_id` | int | Yes | Child recipe ID to add as component |
| `quantity` | float | No | Batch multiplier (default: 1.0) |
| `notes` | str | No | Notes for this component |
| `sort_order` | int | No | Display order (default: append to end) |

**Returns**: `RecipeComponent` instance

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `RecipeNotFound` | Parent or component recipe doesn't exist |
| `ValidationError` | Quantity <= 0, circular reference detected, or depth limit exceeded |

**Validation**:
1. Both recipes must exist
2. Quantity must be > 0
3. Cannot add recipe to itself (`recipe_id != component_recipe_id`)
4. Cannot create circular reference (direct or indirect)
5. Resulting hierarchy must not exceed 3 levels
6. Component cannot already be in parent recipe

---

### `remove_recipe_component`

Remove a component recipe from a parent recipe.

```python
def remove_recipe_component(
    recipe_id: int,
    component_recipe_id: int
) -> bool:
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `recipe_id` | int | Yes | Parent recipe ID |
| `component_recipe_id` | int | Yes | Component recipe ID to remove |

**Returns**: `True` if removed, `False` if not found

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `RecipeNotFound` | Parent recipe doesn't exist |

---

### `update_recipe_component`

Update quantity or notes for an existing component.

```python
def update_recipe_component(
    recipe_id: int,
    component_recipe_id: int,
    quantity: float = None,
    notes: str = None,
    sort_order: int = None
) -> RecipeComponent:
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `recipe_id` | int | Yes | Parent recipe ID |
| `component_recipe_id` | int | Yes | Component recipe ID |
| `quantity` | float | No | New batch multiplier (if provided) |
| `notes` | str | No | New notes (if provided) |
| `sort_order` | int | No | New display order (if provided) |

**Returns**: Updated `RecipeComponent` instance

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `RecipeNotFound` | Parent recipe doesn't exist |
| `ValidationError` | Component not found in recipe, or quantity <= 0 |

---

### `get_recipe_components`

Get all component recipes for a recipe.

```python
def get_recipe_components(recipe_id: int) -> List[RecipeComponent]:
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `recipe_id` | int | Yes | Recipe ID |

**Returns**: List of `RecipeComponent` instances, ordered by `sort_order`

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `RecipeNotFound` | Recipe doesn't exist |

---

### `get_recipes_using_component`

Get all recipes that use a given recipe as a component.

```python
def get_recipes_using_component(component_recipe_id: int) -> List[Recipe]:
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `component_recipe_id` | int | Yes | Recipe ID to check |

**Returns**: List of `Recipe` instances that use this as a component

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `RecipeNotFound` | Recipe doesn't exist |

---

### `get_aggregated_ingredients`

Get all ingredients from a recipe and all its sub-recipes, with quantities aggregated.

```python
def get_aggregated_ingredients(
    recipe_id: int,
    multiplier: float = 1.0
) -> List[Dict]:
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `recipe_id` | int | Yes | Recipe ID |
| `multiplier` | float | No | Scale factor for all quantities (default: 1.0) |

**Returns**: List of aggregated ingredients:
```python
[
    {
        "ingredient": Ingredient,  # Ingredient instance
        "ingredient_id": int,
        "ingredient_name": str,
        "total_quantity": float,  # Aggregated across all recipe levels
        "unit": str,
        "sources": [  # Where this ingredient comes from
            {"recipe_name": str, "quantity": float}
        ]
    },
    ...
]
```

**Behavior**:
- Recursively collects ingredients from all sub-recipes
- Multiplies quantities by component batch multipliers
- Aggregates same ingredients (by ingredient_id + unit)
- Tracks source recipes for each ingredient

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `RecipeNotFound` | Recipe doesn't exist |

---

### `calculate_total_cost_with_components`

Calculate total recipe cost including all sub-recipe costs.

```python
def calculate_total_cost_with_components(recipe_id: int) -> Dict:
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `recipe_id` | int | Yes | Recipe ID |

**Returns**: Cost breakdown:
```python
{
    "recipe_id": int,
    "recipe_name": str,
    "direct_ingredient_cost": float,  # Cost of direct ingredients only
    "component_costs": [  # Cost breakdown by component
        {
            "component_recipe_id": int,
            "component_recipe_name": str,
            "quantity": float,
            "unit_cost": float,  # Cost for 1 batch
            "total_cost": float  # unit_cost * quantity
        },
        ...
    ],
    "total_component_cost": float,  # Sum of all component costs
    "total_cost": float,  # direct_ingredient_cost + total_component_cost
    "cost_per_unit": float,  # total_cost / yield_quantity
}
```

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `RecipeNotFound` | Recipe doesn't exist |

---

## Internal Helper Functions

### `_would_create_cycle`

Check if adding a component would create a circular reference.

```python
def _would_create_cycle(
    parent_id: int,
    component_id: int,
    session
) -> bool:
```

**Returns**: `True` if cycle would be created

---

### `_get_recipe_depth`

Get the maximum depth of a recipe's component hierarchy.

```python
def _get_recipe_depth(recipe_id: int, session) -> int:
```

**Returns**: Depth (1 = no components, 2 = has direct components, 3 = has nested components)

---

### `_would_exceed_depth`

Check if adding a component would exceed the 3-level depth limit.

```python
def _would_exceed_depth(
    parent_id: int,
    component_id: int,
    session
) -> bool:
```

**Returns**: `True` if depth limit would be exceeded

---

## Modified Functions

### `delete_recipe`

**Change**: Add check for recipes using this as component.

**New Behavior**:
- If recipe is used as component in other recipes, raise `ValidationError` with list of parent recipe names
- Database RESTRICT constraint provides backup enforcement

---

### `get_recipe_with_costs`

**Change**: Include component costs in response.

**New Response Fields**:
```python
{
    # ... existing fields ...
    "components": [
        {
            "component_recipe": Recipe,
            "quantity": float,
            "notes": str,
            "unit_cost": float,
            "total_cost": float
        },
        ...
    ],
    "total_component_cost": float,
    "total_cost": float  # Now includes component costs
}
```

---

## Error Messages

| Code | Message Template |
|------|------------------|
| `CIRCULAR_REF` | "Cannot add '{component_name}' as component: would create circular reference" |
| `DEPTH_EXCEEDED` | "Cannot add '{component_name}': would exceed maximum nesting depth of 3 levels" |
| `SELF_REFERENCE` | "Recipe cannot include itself as a component" |
| `ALREADY_COMPONENT` | "'{component_name}' is already a component of this recipe" |
| `IN_USE_AS_COMPONENT` | "Cannot delete '{recipe_name}': used as component in: {parent_names}" |
| `COMPONENT_NOT_FOUND` | "Component recipe not found in this recipe" |
