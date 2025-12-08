# Service Contract: Ingredient Service (Packaging Extensions)

**Service**: `src/services/ingredient_service.py`
**Feature**: 011-packaging-bom-foundation

## Constants

### PACKAGING_CATEGORIES

```python
PACKAGING_CATEGORIES = [
    "Bags",
    "Boxes",
    "Ribbon",
    "Labels",
    "Tissue Paper",
    "Wrapping",
    "Other Packaging"
]
```

## Updated Methods

### create_ingredient

Add `is_packaging` parameter.

```python
def create_ingredient(
    display_name: str,
    category: str,
    recipe_unit: Optional[str] = None,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    notes: Optional[str] = None,
    is_packaging: bool = False,  # NEW
    # ... density fields ...
) -> Ingredient:
    """
    Create a new ingredient.

    Args:
        display_name: Ingredient name
        category: Category name (use PACKAGING_CATEGORIES for packaging)
        is_packaging: True if this is a packaging material (default: False)
        ...

    Returns:
        Created Ingredient instance

    Raises:
        ValidationError: If display_name empty or duplicate
    """
```

### update_ingredient

Add ability to update `is_packaging` flag.

```python
def update_ingredient(
    ingredient_id: int,
    display_name: Optional[str] = None,
    category: Optional[str] = None,
    is_packaging: Optional[bool] = None,  # NEW
    # ... other fields ...
) -> Ingredient:
    """
    Update an existing ingredient.

    Args:
        ingredient_id: ID of ingredient to update
        is_packaging: New packaging flag value (optional)
        ...

    Returns:
        Updated Ingredient instance

    Raises:
        ValidationError: If ingredient not found
        ValidationError: If changing is_packaging on ingredient with products in compositions
    """
```

## New Methods

### get_packaging_ingredients

```python
def get_packaging_ingredients() -> List[Ingredient]:
    """
    Get all ingredients marked as packaging.

    Returns:
        List of Ingredient instances where is_packaging=True,
        sorted by category then display_name
    """
```

### get_food_ingredients

```python
def get_food_ingredients() -> List[Ingredient]:
    """
    Get all ingredients that are NOT packaging.

    Returns:
        List of Ingredient instances where is_packaging=False,
        sorted by category then display_name
    """
```

### get_ingredients_by_category

```python
def get_ingredients_by_category(
    category: str,
    is_packaging: Optional[bool] = None
) -> List[Ingredient]:
    """
    Get ingredients filtered by category and optionally packaging flag.

    Args:
        category: Category name to filter by
        is_packaging: If specified, filter by packaging flag

    Returns:
        List of matching Ingredient instances
    """
```

### is_packaging_ingredient

```python
def is_packaging_ingredient(ingredient_id: int) -> bool:
    """
    Check if an ingredient is marked as packaging.

    Args:
        ingredient_id: ID of ingredient to check

    Returns:
        True if ingredient exists and is_packaging=True, False otherwise
    """
```

### validate_packaging_category

```python
def validate_packaging_category(category: str) -> bool:
    """
    Check if category is a valid packaging category.

    Args:
        category: Category name to validate

    Returns:
        True if category is in PACKAGING_CATEGORIES
    """
```

## Validation Rules

1. **Category warning**: If `is_packaging=True` and category not in PACKAGING_CATEGORIES, log warning (don't reject)
2. **Flag change protection**: Cannot change `is_packaging` from True to False if ingredient has products used in packaging compositions

## Error Messages

| Error | Message |
|-------|---------|
| Flag change blocked | "Cannot unmark packaging: ingredient has products used in {count} composition(s)" |
