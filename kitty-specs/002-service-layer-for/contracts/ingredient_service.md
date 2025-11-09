# Service Contract: IngredientService

**Module**: `src/services/ingredient_service.py`
**Pattern**: Functional (module-level functions)
**Dependencies**: `src/models.Ingredient`, `src/services.database.session_scope`, `src/services.exceptions`, `src/utils.validators`, `src/utils.slug_utils`

## Function Signatures

### create_ingredient

```python
def create_ingredient(ingredient_data: Dict[str, Any]) -> Ingredient:
    """
    Create a new ingredient with auto-generated slug.

    Args:
        ingredient_data: Dictionary containing:
            - name (str, required): Ingredient name
            - category (str, required): Category classification
            - recipe_unit (str, required): Default unit for recipes
            - density_g_per_ml (float, optional): For volume-weight conversions
            - foodon_id (str, optional): FoodOn taxonomy ID
            - fdc_id (str, optional): USDA FoodData Central ID
            - gtin (str, optional): Global Trade Item Number
            - allergens (List[str], optional): Allergen codes

    Returns:
        Ingredient: Created ingredient object with generated slug and ID

    Raises:
        ValidationError: If required fields missing or invalid
        SlugAlreadyExists: If generated slug conflicts (shouldn't happen with auto-increment)
        DatabaseError: If database operation fails

    Example:
        >>> data = {
        ...     "name": "All-Purpose Flour",
        ...     "category": "Flour",
        ...     "recipe_unit": "cup",
        ...     "density_g_per_ml": 0.507
        ... }
        >>> ingredient = create_ingredient(data)
        >>> ingredient.slug
        'all_purpose_flour'
    """
```

---

### get_ingredient

```python
def get_ingredient(slug: str) -> Ingredient:
    """
    Retrieve ingredient by slug.

    Args:
        slug: Unique ingredient identifier (e.g., "all_purpose_flour")

    Returns:
        Ingredient: Ingredient object with relationships eager-loaded

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist

    Example:
        >>> ingredient = get_ingredient("all_purpose_flour")
        >>> ingredient.name
        'All-Purpose Flour'
    """
```

---

### search_ingredients

```python
def search_ingredients(
    query: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
) -> List[Ingredient]:
    """
    Search ingredients by partial name match and/or category filter.

    Args:
        query: Optional partial name to search (case-insensitive)
        category: Optional category to filter by (exact match)
        limit: Maximum number of results (default 100)

    Returns:
        List[Ingredient]: Matching ingredients, sorted by name

    Example:
        >>> results = search_ingredients(query="flour", category="Flour")
        >>> [i.name for i in results]
        ['All-Purpose Flour', 'Bread Flour', 'Cake Flour']
    """
```

---

### update_ingredient

```python
def update_ingredient(slug: str, ingredient_data: Dict[str, Any]) -> Ingredient:
    """
    Update ingredient attributes (slug cannot be changed).

    Args:
        slug: Ingredient identifier
        ingredient_data: Dictionary with fields to update (partial update supported)
            - name (str, optional): New name
            - category (str, optional): New category
            - recipe_unit (str, optional): New recipe unit
            - density_g_per_ml (float, optional): New density
            - foodon_id, fdc_id, gtin, allergens (optional): Industry standard fields

    Returns:
        Ingredient: Updated ingredient object

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist
        ValidationError: If update data invalid
        DatabaseError: If database operation fails

    Note:
        Slug cannot be changed to maintain foreign key integrity.
        Attempting to change slug will raise ValidationError.

    Example:
        >>> updated = update_ingredient("all_purpose_flour", {
        ...     "category": "Baking Essentials",
        ...     "density_g_per_ml": 0.510
        ... })
    """
```

---

### delete_ingredient

```python
def delete_ingredient(slug: str) -> bool:
    """
    Delete ingredient if not referenced by other entities.

    Args:
        slug: Ingredient identifier

    Returns:
        bool: True if deletion successful

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist
        IngredientInUse: If ingredient has dependencies (recipes, variants, pantry items)
        DatabaseError: If database operation fails

    Example:
        >>> delete_ingredient("unused_ingredient")
        True

        >>> delete_ingredient("all_purpose_flour")
        IngredientInUse: Cannot delete all_purpose_flour: used in 5 recipes, 3 variants
    """
```

---

### check_ingredient_dependencies

```python
def check_ingredient_dependencies(slug: str) -> Dict[str, int]:
    """
    Check if ingredient is referenced by other entities.

    Args:
        slug: Ingredient identifier

    Returns:
        Dict[str, int]: Dependency counts
            - "recipes": Number of recipes using this ingredient
            - "variants": Number of variants for this ingredient
            - "pantry_items": Number of pantry items (via variants)
            - "unit_conversions": Number of custom unit conversions

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist

    Example:
        >>> deps = check_ingredient_dependencies("all_purpose_flour")
        >>> deps
        {'recipes': 5, 'variants': 3, 'pantry_items': 12, 'unit_conversions': 2}
    """
```

---

### list_ingredients

```python
def list_ingredients(
    category: Optional[str] = None,
    sort_by: str = "name",
    limit: Optional[int] = None,
    offset: int = 0
) -> List[Ingredient]:
    """
    List all ingredients with optional filtering and pagination.

    Args:
        category: Optional category filter (exact match)
        sort_by: Field to sort by ("name", "category", "created_at")
        limit: Maximum number of results (None = all)
        offset: Number of results to skip (for pagination)

    Returns:
        List[Ingredient]: Ingredients matching criteria

    Example:
        >>> ingredients = list_ingredients(category="Flour", sort_by="name", limit=10)
        >>> len(ingredients)
        10
    """
```

---

## Exception Mapping

| Exception | HTTP Status (future) | User Message |
|-----------|---------------------|--------------|
| `IngredientNotFoundBySlug` | 404 Not Found | "Ingredient '{slug}' not found" |
| `SlugAlreadyExists` | 409 Conflict | "Ingredient with slug '{slug}' already exists" |
| `IngredientInUse` | 409 Conflict | "Cannot delete ingredient: {dependency_details}" |
| `ValidationError` | 400 Bad Request | "Validation failed: {error_details}" |
| `DatabaseError` | 500 Internal Server Error | "Database operation failed" |

---

## Implementation Notes

### Slug Generation
- Automatically called in `create_ingredient()` using `slug_utils.create_slug(name, session)`
- Uniqueness enforced by database UNIQUE constraint + auto-increment suffix
- Slug cannot be changed after creation (immutable for FK stability)

### Validation
- Use `validators.validate_ingredient_data(data)` before database operations
- Check required fields: name, category, recipe_unit
- Validate recipe_unit is known unit from unit_converter.py
- Validate optional fields if provided (density > 0, proper format for IDs)

### Transaction Management
- All functions use `with session_scope() as session:` for automatic commit/rollback
- Eager load relationships when appropriate (avoid N+1 queries)
- Use `session.flush()` to get generated IDs before commit

### Performance Considerations
- Index on `slug` column (UNIQUE constraint provides this)
- Search operations use LIKE with leading % (slower, but necessary for partial match)
- List operations should default to reasonable limits (e.g., 100) to prevent memory issues
- Dependency checking uses COUNT queries (fast with proper indexes)

---

**Contract Status**: ✅ Defined - 7 functions with complete type signatures and exception specifications
