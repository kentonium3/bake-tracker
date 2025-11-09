# Service Contract: VariantService

**Module**: `src/services/variant_service.py`
**Pattern**: Functional (module-level functions)
**Dependencies**: `src/models.Variant`, `src/services.database.session_scope`, `src/services.exceptions`, `src/services.ingredient_service`, `src/utils.validators`

## Function Signatures

### create_variant

```python
def create_variant(ingredient_slug: str, variant_data: Dict[str, Any]) -> Variant:
    """
    Create a new variant for an ingredient.

    Args:
        ingredient_slug: Slug of parent ingredient
        variant_data: Dictionary containing:
            - brand (str, required): Brand name
            - package_size (str, optional): Human-readable size
            - purchase_unit (str, required): Unit purchased in
            - purchase_quantity (Decimal, required): Quantity in package
            - upc (str, optional): Universal Product Code
            - gtin (str, optional): Global Trade Item Number
            - supplier (str, optional): Where to buy
            - preferred (bool, optional): Mark as preferred variant (default False)
            - net_content_value (Decimal, optional): Industry standard field
            - net_content_uom (str, optional): Industry standard field

    Returns:
        Variant: Created variant object with auto-calculated display_name

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist
        ValidationError: If required fields missing or invalid
        DatabaseError: If database operation fails

    Note:
        If preferred=True, all other variants for this ingredient will be set to preferred=False.

    Example:
        >>> data = {
        ...     "brand": "King Arthur",
        ...     "package_size": "25 lb bag",
        ...     "purchase_unit": "lb",
        ...     "purchase_quantity": Decimal("25.0"),
        ...     "preferred": True
        ... }
        >>> variant = create_variant("all_purpose_flour", data)
        >>> variant.display_name
        'King Arthur - 25 lb bag'
    """
```

---

### get_variant

```python
def get_variant(variant_id: int) -> Variant:
    """
    Retrieve variant by ID.

    Args:
        variant_id: Variant identifier

    Returns:
        Variant: Variant object with ingredient relationship eager-loaded

    Raises:
        VariantNotFound: If variant_id doesn't exist

    Example:
        >>> variant = get_variant(123)
        >>> variant.brand
        'King Arthur'
        >>> variant.ingredient.name
        'All-Purpose Flour'
    """
```

---

### get_variants_for_ingredient

```python
def get_variants_for_ingredient(ingredient_slug: str) -> List[Variant]:
    """
    Retrieve all variants for an ingredient, sorted with preferred first.

    Args:
        ingredient_slug: Ingredient identifier

    Returns:
        List[Variant]: All variants for ingredient, preferred variant first, then by brand

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist

    Example:
        >>> variants = get_variants_for_ingredient("all_purpose_flour")
        >>> variants[0].preferred
        True
        >>> [v.brand for v in variants]
        ['King Arthur', 'Bob's Red Mill', 'Store Brand']
    """
```

---

### set_preferred_variant

```python
def set_preferred_variant(variant_id: int) -> Variant:
    """
    Mark variant as preferred, clearing preferred flag on all other variants for same ingredient.

    Args:
        variant_id: ID of variant to mark as preferred

    Returns:
        Variant: Updated variant with preferred=True

    Raises:
        VariantNotFound: If variant_id doesn't exist
        DatabaseError: If database operation fails

    Note:
        This function ensures only one variant per ingredient is marked preferred.
        All other variants for the same ingredient will have preferred=False.

    Example:
        >>> variant = set_preferred_variant(456)
        >>> variant.preferred
        True
        >>> # All other variants for this ingredient now have preferred=False
    """
```

---

### update_variant

```python
def update_variant(variant_id: int, variant_data: Dict[str, Any]) -> Variant:
    """
    Update variant attributes.

    Args:
        variant_id: Variant identifier
        variant_data: Dictionary with fields to update (partial update supported)
            - brand (str, optional): New brand
            - package_size (str, optional): New package size
            - purchase_unit (str, optional): New purchase unit
            - purchase_quantity (Decimal, optional): New purchase quantity
            - upc, gtin, supplier (optional): Update identification/sourcing
            - preferred (bool, optional): Change preferred status
            - net_content_value, net_content_uom (optional): Industry fields

    Returns:
        Variant: Updated variant object

    Raises:
        VariantNotFound: If variant_id doesn't exist
        ValidationError: If update data invalid
        DatabaseError: If database operation fails

    Note:
        ingredient_slug (FK) cannot be changed after creation.
        If updating preferred to True, use set_preferred_variant() instead for proper toggling.

    Example:
        >>> updated = update_variant(123, {
        ...     "package_size": "50 lb bag",
        ...     "purchase_quantity": Decimal("50.0")
        ... })
    """
```

---

### delete_variant

```python
def delete_variant(variant_id: int) -> bool:
    """
    Delete variant if not referenced by pantry items or purchases.

    Args:
        variant_id: Variant identifier

    Returns:
        bool: True if deletion successful

    Raises:
        VariantNotFound: If variant_id doesn't exist
        VariantInUse: If variant has dependencies (pantry items, purchases)
        DatabaseError: If database operation fails

    Example:
        >>> delete_variant(789)
        True

        >>> delete_variant(123)
        VariantInUse: Cannot delete variant: used in 12 pantry items, 25 purchases
    """
```

---

### check_variant_dependencies

```python
def check_variant_dependencies(variant_id: int) -> Dict[str, int]:
    """
    Check if variant is referenced by other entities.

    Args:
        variant_id: Variant identifier

    Returns:
        Dict[str, int]: Dependency counts
            - "pantry_items": Number of pantry items using this variant
            - "purchases": Number of purchase records for this variant

    Raises:
        VariantNotFound: If variant_id doesn't exist

    Example:
        >>> deps = check_variant_dependencies(123)
        >>> deps
        {'pantry_items': 5, 'purchases': 12}
    """
```

---

### search_variants_by_upc

```python
def search_variants_by_upc(upc: str) -> List[Variant]:
    """
    Search variants by UPC code (exact match).

    Args:
        upc: Universal Product Code (12-14 digits)

    Returns:
        List[Variant]: Matching variants (may be multiple if same UPC across suppliers)

    Example:
        >>> variants = search_variants_by_upc("012345678901")
        >>> len(variants)
        2  # Same product from different suppliers
    """
```

---

### get_preferred_variant

```python
def get_preferred_variant(ingredient_slug: str) -> Optional[Variant]:
    """
    Get the preferred variant for an ingredient.

    Args:
        ingredient_slug: Ingredient identifier

    Returns:
        Optional[Variant]: Preferred variant, or None if no variant marked preferred

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist

    Example:
        >>> preferred = get_preferred_variant("all_purpose_flour")
        >>> preferred.brand if preferred else "No preferred variant set"
        'King Arthur'
    """
```

---

## Exception Mapping

| Exception | HTTP Status (future) | User Message |
|-----------|---------------------|--------------|
| `VariantNotFound` | 404 Not Found | "Variant with ID {id} not found" |
| `VariantInUse` | 409 Conflict | "Cannot delete variant: {dependency_details}" |
| `IngredientNotFoundBySlug` | 404 Not Found | "Ingredient '{slug}' not found" |
| `ValidationError` | 400 Bad Request | "Validation failed: {error_details}" |
| `DatabaseError` | 500 Internal Server Error | "Database operation failed" |

---

## Implementation Notes

### Display Name Calculation
```python
@property
def display_name(self) -> str:
    """Auto-calculated display name: '{brand} - {package_size}'."""
    if self.package_size:
        return f"{self.brand} - {self.package_size}"
    return self.brand
```

### Preferred Variant Toggle Logic
- When creating variant with `preferred=True`, clear all other variants for that ingredient
- When updating variant to `preferred=True`, use `set_preferred_variant()` for atomic toggle
- Query optimization: Use single UPDATE statement to clear all others, then SET on selected
- Transaction safety: Both operations in single `session_scope()` transaction

### Validation
- Use `validators.validate_variant_data(data, ingredient_slug)` before database operations
- Check required fields: brand, purchase_unit, purchase_quantity
- Validate purchase_quantity > 0 (must be positive)
- Validate purchase_unit is known unit from unit_converter.py
- Validate UPC format if provided (12-14 digit string)
- Verify ingredient exists using `ingredient_service.get_ingredient(slug)`

### Transaction Management
- All functions use `with session_scope() as session:` for automatic commit/rollback
- Eager load ingredient relationship when retrieving variants
- Use `session.flush()` to get generated IDs before commit
- Preferred variant toggle uses UPDATE + SET in single transaction

### Performance Considerations
- Index on `ingredient_slug` (FK provides this)
- Index on `preferred` for quick lookups (partial index WHERE preferred=true)
- Index on `upc` for barcode scanning (future feature)
- Sorting: Preferred first (ORDER BY preferred DESC), then by brand (ORDER BY brand ASC)

---

**Contract Status**: ✅ Defined - 9 functions with complete type signatures and exception specifications
