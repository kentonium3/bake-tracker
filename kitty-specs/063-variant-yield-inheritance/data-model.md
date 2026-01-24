# Data Model: Variant Yield Inheritance

**Feature**: 063-variant-yield-inheritance
**Date**: 2025-01-24

## Overview

This feature adds service primitives to `recipe_service.py` for transparent yield access. No database schema changes are required.

## Existing Models (No Changes)

### Recipe

```python
# src/models/recipe.py - Existing fields used
class Recipe(BaseModel):
    base_recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True)
    # Variants have base_recipe_id set; base recipes have NULL
```

### FinishedUnit

```python
# src/models/finished_unit.py - Existing nullable fields
class FinishedUnit(BaseModel):
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    display_name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)

    # Yield fields - NULL for variant FinishedUnits
    items_per_batch = Column(Integer, nullable=True)
    item_unit = Column(String(50), nullable=True)
```

## Service Primitive Contracts

### `get_base_yield_structure(recipe_id, session=None)`

Returns yield specifications from the base recipe. For base recipes, returns own yields. For variants, returns base recipe's yields.

**Signature**:
```python
def get_base_yield_structure(
    recipe_id: int,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get yield structure for a recipe, resolving to base recipe if variant.

    Args:
        recipe_id: Recipe ID (base or variant)
        session: Optional SQLAlchemy session for transaction sharing

    Returns:
        List of yield dicts with keys:
        - slug: str
        - display_name: str (from base recipe's FinishedUnits)
        - items_per_batch: Optional[int]
        - item_unit: Optional[str]

    Raises:
        RecipeNotFound: If recipe_id does not exist
    """
```

**Behavior**:
1. Load recipe by ID
2. If `base_recipe_id` is not None, use that ID instead
3. Query FinishedUnits for the resolved recipe ID
4. Return list of yield dictionaries

**Example**:
```python
# Base recipe "Plain Thumbprint Cookies" has FinishedUnit:
#   items_per_batch=24, item_unit="cookie"

# Variant "Raspberry Thumbprint Cookies" has FinishedUnit:
#   items_per_batch=NULL, item_unit=NULL

# Both calls return the same yield structure:
get_base_yield_structure(base_id)    # [{"items_per_batch": 24, "item_unit": "cookie", ...}]
get_base_yield_structure(variant_id) # [{"items_per_batch": 24, "item_unit": "cookie", ...}]
```

---

### `get_finished_units(recipe_id, session=None)`

Returns a recipe's own FinishedUnits for display purposes.

**Signature**:
```python
def get_finished_units(
    recipe_id: int,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get a recipe's own FinishedUnits (not inherited).

    Args:
        recipe_id: Recipe ID
        session: Optional SQLAlchemy session for transaction sharing

    Returns:
        List of FinishedUnit dicts with keys:
        - id: int
        - slug: str
        - display_name: str
        - items_per_batch: Optional[int] (NULL for variants)
        - item_unit: Optional[str] (NULL for variants)
        - yield_mode: str

    Raises:
        RecipeNotFound: If recipe_id does not exist
    """
```

**Behavior**:
1. Load recipe by ID
2. Query FinishedUnits where `recipe_id` matches
3. Return list of FinishedUnit dictionaries

**Example**:
```python
# Base recipe "Plain Thumbprint Cookies":
get_finished_units(base_id)
# [{"display_name": "Plain Cookie", "items_per_batch": 24, "item_unit": "cookie", ...}]

# Variant "Raspberry Thumbprint Cookies":
get_finished_units(variant_id)
# [{"display_name": "Raspberry Cookie", "items_per_batch": None, "item_unit": None, ...}]
```

---

### `create_recipe_variant` (Extended)

Extend existing function to accept FinishedUnit display names.

**Extended Signature**:
```python
def create_recipe_variant(
    base_recipe_id: int,
    variant_name: str,
    name: str = None,
    copy_ingredients: bool = True,
    finished_unit_names: Optional[List[Dict]] = None,  # NEW
    session: Optional[Session] = None,
) -> dict:
    """
    Create a variant of an existing recipe with optional FinishedUnits.

    Args:
        base_recipe_id: The recipe to create a variant of
        variant_name: Name distinguishing this variant (e.g., "Raspberry")
        name: Full recipe name (defaults to "Base Name - Variant Name")
        copy_ingredients: If True, copy ingredients from base recipe
        finished_unit_names: List of dicts with variant FinishedUnit display names:
            [{"base_slug": "plain-cookie", "display_name": "Raspberry Cookie"}, ...]
        session: Optional session for transaction sharing

    Returns:
        Created variant recipe dict

    Raises:
        RecipeNotFound: If base recipe does not exist
        ValidationError: If display_name matches base FinishedUnit display_name
    """
```

**Behavior for `finished_unit_names`**:
1. If provided, for each entry:
   - Look up base FinishedUnit by `base_slug`
   - Create variant FinishedUnit with:
     - `recipe_id`: variant recipe ID
     - `display_name`: from input
     - `slug`: generated from variant recipe name + display_name
     - `items_per_batch`: NULL
     - `item_unit`: NULL
     - Other fields copied from base

2. Validate display_name differs from base FinishedUnit display_name

---

## Validation Rules

### FR-003: Variant FinishedUnits Must Not Store Yields

Enforced by:
- `create_recipe_variant` sets `items_per_batch=None`, `item_unit=None`
- No setter/update path allows populating these fields for variants

### FR-004: Variant Display Names Must Differ

Enforced by:
- `create_recipe_variant` validates `display_name` != base FinishedUnit `display_name`
- Raises `ValidationError` with inline message if duplicate detected

---

## Test Cases

### Service Primitive Tests

```python
# test_get_base_yield_structure_base_recipe
# Given a base recipe with FinishedUnit(items_per_batch=24, item_unit="cookie")
# When get_base_yield_structure(base_id) is called
# Then return [{"items_per_batch": 24, "item_unit": "cookie", ...}]

# test_get_base_yield_structure_variant_recipe
# Given a variant with base_recipe_id pointing to above base
# When get_base_yield_structure(variant_id) is called
# Then return [{"items_per_batch": 24, "item_unit": "cookie", ...}] (from base)

# test_get_finished_units_variant
# Given a variant with FinishedUnit(display_name="Raspberry Cookie", items_per_batch=NULL)
# When get_finished_units(variant_id) is called
# Then return [{"display_name": "Raspberry Cookie", "items_per_batch": None, ...}]

# test_create_variant_with_finished_units
# Given base recipe with FinishedUnit "Plain Cookie"
# When create_recipe_variant(..., finished_unit_names=[{"base_slug": "...", "display_name": "Raspberry Cookie"}])
# Then variant FinishedUnit is created with NULL yield fields

# test_create_variant_rejects_duplicate_display_name
# Given base recipe with FinishedUnit "Plain Cookie"
# When create_recipe_variant(..., finished_unit_names=[{"...", "display_name": "Plain Cookie"}])
# Then ValidationError is raised
```
