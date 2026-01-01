# Service Contract: ingredient_hierarchy_service

**Module**: `src/services/ingredient_hierarchy_service.py`
**Date**: 2025-12-30
**Status**: Design

---

## Purpose

Provides tree traversal and hierarchy management operations for the ingredient taxonomy. All hierarchy-related business logic is encapsulated here, keeping the UI layer thin.

---

## Dependencies

- `src/models/ingredient.py` - Ingredient model with hierarchy fields
- `src/services/database.py` - session_scope for transactions
- `src/services/exceptions.py` - Custom exceptions

---

## Public API

### Tree Navigation

#### `get_root_ingredients(session=None) -> List[Dict]`

Get all root-level (hierarchy_level=0) ingredients.

**Parameters**:
- `session`: Optional SQLAlchemy session

**Returns**: List of ingredient dictionaries, sorted by display_name

**Example**:
```python
roots = get_root_ingredients()
# [{"id": 1, "display_name": "Chocolate", "hierarchy_level": 0, ...}, ...]
```

---

#### `get_children(parent_id: int, session=None) -> List[Dict]`

Get direct children of an ingredient.

**Parameters**:
- `parent_id`: ID of parent ingredient
- `session`: Optional SQLAlchemy session

**Returns**: List of child ingredient dictionaries, sorted by display_name

**Raises**: `IngredientNotFoundError` if parent_id doesn't exist

---

#### `get_all_descendants(ancestor_id: int, session=None) -> List[Dict]`

Get all descendants (recursive) of an ingredient.

**Parameters**:
- `ancestor_id`: ID of ancestor ingredient
- `session`: Optional SQLAlchemy session

**Returns**: List of all descendant ingredients (all levels below ancestor)

**Raises**: `IngredientNotFoundError` if ancestor_id doesn't exist

---

#### `get_ancestors(ingredient_id: int, session=None) -> List[Dict]`

Get path from ingredient to root (for breadcrumb display).

**Parameters**:
- `ingredient_id`: ID of ingredient
- `session`: Optional SQLAlchemy session

**Returns**: List of ancestors ordered from immediate parent to root

**Example**:
```python
ancestors = get_ancestors(semi_sweet_chips_id)
# [{"display_name": "Dark Chocolate", ...}, {"display_name": "Chocolate", ...}]
```

---

#### `get_leaf_ingredients(parent_id: Optional[int] = None, session=None) -> List[Dict]`

Get all leaf-level (hierarchy_level=2) ingredients.

**Parameters**:
- `parent_id`: Optional - filter to descendants of this parent
- `session`: Optional SQLAlchemy session

**Returns**: List of leaf ingredients, sorted by display_name

---

### Validation

#### `validate_hierarchy_level(ingredient_id: int, allowed_levels: List[int], session=None) -> bool`

Check if ingredient is at an allowed hierarchy level.

**Parameters**:
- `ingredient_id`: ID of ingredient to check
- `allowed_levels`: List of allowed levels (e.g., [2] for recipes)
- `session`: Optional SQLAlchemy session

**Returns**: True if valid

**Raises**: `ValidationError` with helpful message if invalid

---

#### `is_leaf(ingredient_id: int, session=None) -> bool`

Check if ingredient is a leaf (hierarchy_level=2).

**Parameters**:
- `ingredient_id`: ID of ingredient
- `session`: Optional SQLAlchemy session

**Returns**: True if leaf, False otherwise

---

### Hierarchy Management

#### `move_ingredient(ingredient_id: int, new_parent_id: Optional[int], session=None) -> Dict`

Move ingredient to a new parent.

**Parameters**:
- `ingredient_id`: ID of ingredient to move
- `new_parent_id`: ID of new parent (None = make root)
- `session`: Optional SQLAlchemy session

**Returns**: Updated ingredient dictionary

**Raises**:
- `IngredientNotFoundError` if ingredient or parent not found
- `ValidationError` if move would create cycle
- `ValidationError` if move would exceed max depth (3 levels)

---

#### `would_create_cycle(ingredient_id: int, new_parent_id: int, session=None) -> bool`

Check if setting new_parent_id would create a circular reference.

**Parameters**:
- `ingredient_id`: ID of ingredient being moved
- `new_parent_id`: Proposed new parent ID
- `session`: Optional SQLAlchemy session

**Returns**: True if cycle would be created, False if safe

---

### Search

#### `search_ingredients(query: str, session=None) -> List[Dict]`

Search ingredients by display_name, returning matches with ancestry info.

**Parameters**:
- `query`: Search string (case-insensitive partial match)
- `session`: Optional SQLAlchemy session

**Returns**: List of matching ingredients with `ancestors` field populated

**Example**:
```python
results = search_ingredients("chocolate chips")
# [{"id": 3, "display_name": "Semi-Sweet Chocolate Chips",
#   "ancestors": [{"display_name": "Dark Chocolate"}, {"display_name": "Chocolate"}]}, ...]
```

---

## Internal Helpers

#### `_calculate_hierarchy_level(parent_id: Optional[int], session) -> int`

Calculate hierarchy_level based on parent.

**Returns**: 0 if no parent, parent.hierarchy_level + 1 otherwise

**Raises**: `ValidationError` if result would exceed 2

---

#### `_validate_parent_depth(parent: Ingredient) -> None`

Ensure parent can accept children (hierarchy_level < 2).

**Raises**: `ValidationError` if parent is already at max depth

---

## Exceptions

```python
class IngredientNotFoundError(Exception):
    """Raised when ingredient ID doesn't exist."""
    pass

class HierarchyValidationError(ValidationError):
    """Raised for hierarchy-specific validation failures."""
    pass

class CircularReferenceError(HierarchyValidationError):
    """Raised when operation would create circular reference."""
    pass
```

---

## Usage Patterns

### Recipe Ingredient Selection

```python
# UI calls service to validate before adding to recipe
from src.services.ingredient_hierarchy_service import is_leaf, get_leaf_ingredients

if not is_leaf(selected_ingredient_id):
    # Get suggestions for user
    suggestions = get_leaf_ingredients(parent_id=selected_ingredient_id)
    raise ValidationError(f"Select a specific ingredient: {suggestions[:3]}")
```

### Breadcrumb Display

```python
from src.services.ingredient_hierarchy_service import get_ancestors

ancestors = get_ancestors(ingredient_id)
breadcrumb = " → ".join([a["display_name"] for a in reversed(ancestors)])
# "Chocolate → Dark Chocolate → Semi-Sweet Chocolate Chips"
```

### Tree Widget Population

```python
from src.services.ingredient_hierarchy_service import get_root_ingredients, get_children

# Initial load
roots = get_root_ingredients()

# On expand
def on_node_expand(parent_id):
    return get_children(parent_id)
```

---

## Test Coverage Requirements

| Function | Test Cases Required |
|----------|---------------------|
| get_root_ingredients | Empty tree, populated tree |
| get_children | Valid parent, invalid parent, no children |
| get_all_descendants | Single level, multi-level, empty |
| get_ancestors | Leaf, mid-tier, root |
| get_leaf_ingredients | All leaves, filtered by parent |
| validate_hierarchy_level | Valid, invalid, edge cases |
| move_ingredient | Valid move, cycle detection, depth exceeded |
| would_create_cycle | Direct cycle, indirect cycle, safe move |
| search_ingredients | Match found, no match, partial match |
