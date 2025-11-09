# Service Contract: PantryService

**Module**: `src/services/pantry_service.py`
**Pattern**: Functional (module-level functions)
**Dependencies**: `src/models.PantryItem`, `src/services.database.session_scope`, `src/services.exceptions`, `src/services.variant_service`, `src/services.ingredient_service`, `decimal.Decimal`

## Function Signatures

### add_to_pantry

```python
def add_to_pantry(
    variant_id: int,
    quantity: Decimal,
    unit: str,
    purchase_date: date,
    expiration_date: Optional[date] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None
) -> PantryItem:
    """
    Add a new pantry item (lot) to inventory.

    Args:
        variant_id: ID of variant being added to pantry
        quantity: Amount being added
        unit: Unit of quantity (e.g., "lb", "oz", "cup")
        purchase_date: When this lot was purchased (for FIFO ordering)
        expiration_date: Optional expiration date
        location: Optional storage location (e.g., "Main Pantry", "Basement")
        notes: Optional user notes

    Returns:
        PantryItem: Created pantry item object

    Raises:
        VariantNotFound: If variant_id doesn't exist
        ValidationError: If quantity <= 0, invalid unit, or invalid dates
        DatabaseError: If database operation fails

    Example:
        >>> from decimal import Decimal
        >>> from datetime import date
        >>> item = add_to_pantry(
        ...     variant_id=123,
        ...     quantity=Decimal("25.0"),
        ...     unit="lb",
        ...     purchase_date=date(2025, 11, 1),
        ...     expiration_date=date(2026, 11, 1),
        ...     location="Main Pantry"
        ... )
        >>> item.quantity
        Decimal('25.0')
    """
```

---

### get_pantry_items

```python
def get_pantry_items(
    ingredient_slug: Optional[str] = None,
    variant_id: Optional[int] = None,
    location: Optional[str] = None,
    min_quantity: Optional[Decimal] = None
) -> List[PantryItem]:
    """
    Retrieve pantry items with optional filtering.

    Args:
        ingredient_slug: Filter by ingredient (all variants)
        variant_id: Filter by specific variant
        location: Filter by storage location
        min_quantity: Filter items with quantity >= min_quantity (useful to exclude depleted lots)

    Returns:
        List[PantryItem]: Matching pantry items, ordered by purchase_date ASC (oldest first)

    Example:
        >>> items = get_pantry_items(ingredient_slug="all_purpose_flour", min_quantity=Decimal("0.1"))
        >>> [f"{item.quantity} {item.unit}" for item in items]
        ['10.5 lb', '15.0 lb', '8.25 lb']
    """
```

---

### get_total_quantity

```python
def get_total_quantity(ingredient_slug: str) -> Decimal:
    """
    Calculate total quantity for an ingredient across all variants and locations.

    Args:
        ingredient_slug: Ingredient identifier

    Returns:
        Decimal: Total quantity in ingredient's recipe_unit (after unit conversion)

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist

    Note:
        This function converts all pantry item quantities to the ingredient's recipe_unit
        using unit conversion logic from unit_converter.py.

    Example:
        >>> total = get_total_quantity("all_purpose_flour")
        >>> total
        Decimal('33.75')  # Total cups across all variants/locations
    """
```

---

### consume_fifo

```python
def consume_fifo(
    ingredient_slug: str,
    quantity_needed: Decimal
) -> Dict[str, Any]:
    """
    Consume pantry inventory using FIFO (First In, First Out) logic.

    Args:
        ingredient_slug: Ingredient to consume
        quantity_needed: Amount to consume in ingredient's recipe_unit

    Returns:
        Dict containing:
            - "consumed" (Decimal): Actual amount consumed
            - "breakdown" (List[Dict]): Per-lot consumption details
                Each entry: {
                    "pantry_item_id": int,
                    "variant_id": int,
                    "lot_date": date,
                    "quantity_consumed": Decimal,
                    "unit": str,
                    "remaining_in_lot": Decimal
                }
            - "shortfall" (Decimal): Amount still needed (0 if fully satisfied)
            - "satisfied" (bool): True if quantity_needed fully consumed

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist
        DatabaseError: If database operation fails

    Note:
        - Consumes oldest lots first (by purchase_date)
        - Updates pantry_item quantities transactionally
        - If insufficient inventory, consumes all available and returns shortfall
        - Partial lot consumption is supported (lot quantity updated, not deleted)

    Example:
        >>> result = consume_fifo("all_purpose_flour", Decimal("12.0"))
        >>> result["consumed"]
        Decimal('12.0')
        >>> result["satisfied"]
        True
        >>> result["breakdown"]
        [
            {"pantry_item_id": 45, "variant_id": 123, "lot_date": date(2025, 11, 1),
             "quantity_consumed": Decimal("10.0"), "unit": "lb", "remaining_in_lot": Decimal("0.0")},
            {"pantry_item_id": 46, "variant_id": 123, "lot_date": date(2025, 11, 15),
             "quantity_consumed": Decimal("2.0"), "unit": "lb", "remaining_in_lot": Decimal("13.0")}
        ]
    """
```

---

### get_expiring_soon

```python
def get_expiring_soon(days: int = 14) -> List[PantryItem]:
    """
    Get pantry items expiring within specified days.

    Args:
        days: Number of days from today to check (default 14)

    Returns:
        List[PantryItem]: Items expiring within timeframe, sorted by expiration_date ASC

    Note:
        Only returns items with expiration_date set.
        Items with no expiration_date are excluded.

    Example:
        >>> expiring = get_expiring_soon(days=7)
        >>> for item in expiring:
        ...     print(f"{item.variant.display_name} expires {item.expiration_date}")
        King Arthur - 25 lb bag expires 2025-11-15
    """
```

---

### update_pantry_item

```python
def update_pantry_item(
    pantry_item_id: int,
    updates: Dict[str, Any]
) -> PantryItem:
    """
    Update pantry item attributes.

    Args:
        pantry_item_id: PantryItem identifier
        updates: Dictionary with fields to update
            - quantity (Decimal, optional): New quantity
            - expiration_date (date, optional): New expiration date
            - location (str, optional): New location
            - notes (str, optional): New notes

    Returns:
        PantryItem: Updated pantry item object

    Raises:
        PantryItemNotFound: If pantry_item_id doesn't exist
        ValidationError: If updates invalid (e.g., negative quantity)
        DatabaseError: If database operation fails

    Note:
        variant_id and purchase_date cannot be changed (immutable for FIFO integrity).

    Example:
        >>> updated = update_pantry_item(45, {
        ...     "quantity": Decimal("15.5"),
        ...     "location": "Basement Storage"
        ... })
    """
```

---

### delete_pantry_item

```python
def delete_pantry_item(pantry_item_id: int) -> bool:
    """
    Delete pantry item (remove lot from inventory).

    Args:
        pantry_item_id: PantryItem identifier

    Returns:
        bool: True if deletion successful

    Raises:
        PantryItemNotFound: If pantry_item_id doesn't exist
        DatabaseError: If database operation fails

    Note:
        Typically used to remove depleted lots (quantity=0) or correct data entry errors.
        For consuming inventory, use consume_fifo() instead.

    Example:
        >>> delete_pantry_item(45)
        True
    """
```

---

### get_pantry_value

```python
def get_pantry_value() -> Decimal:
    """
    Calculate total value of all pantry inventory.

    Returns:
        Decimal: Total cost of all pantry items (sum of quantity * unit_cost for each item)

    Note:
        Requires purchase cost data to be tracked in PantryItem model.
        If cost data not available, returns Decimal("0.0").

    Example:
        >>> total_value = get_pantry_value()
        >>> total_value
        Decimal('245.67')
    """
```

---

## Exception Mapping

| Exception | HTTP Status (future) | User Message |
|-----------|---------------------|--------------|
| `PantryItemNotFound` | 404 Not Found | "Pantry item with ID {id} not found" |
| `VariantNotFound` | 404 Not Found | "Variant with ID {id} not found" |
| `IngredientNotFoundBySlug` | 404 Not Found | "Ingredient '{slug}' not found" |
| `ValidationError` | 400 Bad Request | "Validation failed: {error_details}" |
| `DatabaseError` | 500 Internal Server Error | "Database operation failed" |

---

## FIFO Algorithm Implementation Details

### Query Pattern
```python
# Get all pantry items for ingredient, ordered by purchase_date ASC
pantry_items = session.query(PantryItem)\
    .join(Variant)\
    .join(Ingredient)\
    .filter(Ingredient.slug == ingredient_slug, PantryItem.quantity > 0)\
    .order_by(PantryItem.purchase_date.asc())\
    .all()
```

### Consumption Loop
```python
for pantry_item in pantry_items:
    if remaining_needed <= 0:
        break

    to_consume = min(pantry_item.quantity, remaining_needed)
    pantry_item.quantity -= to_consume
    consumed += to_consume
    remaining_needed -= to_consume

    breakdown.append({...})
    session.flush()  # Persist change within transaction
```

### Transaction Safety
- All quantity updates happen within single `session_scope()` transaction
- If error occurs, all changes rolled back automatically
- Use `session.flush()` after each lot update to persist incrementally
- Final `session.commit()` happens when exiting `session_scope()` context

---

## Validation Rules

### add_to_pantry
- `variant_id`: Must reference existing Variant
- `quantity`: Must be > 0 (positive)
- `unit`: Must be valid unit from unit_converter.py
- `purchase_date`: Cannot be future date
- `expiration_date`: If provided, must be >= purchase_date

### update_pantry_item
- `quantity`: If updated, must be >= 0 (can be zero for depleted lot)
- `expiration_date`: If updated, must be >= purchase_date
- `variant_id`, `purchase_date`: Immutable (cannot be changed)

### consume_fifo
- `ingredient_slug`: Must reference existing Ingredient
- `quantity_needed`: Must be > 0 (positive)
- Quantity units converted to ingredient's recipe_unit before consumption

---

## Performance Considerations

- **Index on purchase_date**: Critical for FIFO query performance (ORDER BY purchase_date ASC)
- **Index on variant_id**: Foreign key provides this automatically
- **Index on ingredient_slug**: Via Variant FK to Ingredient
- **Eager loading**: Load Variant and Ingredient relationships to avoid N+1 queries
- **Query optimization**: Use single query to get all lots, iterate in Python (faster than multiple queries)
- **Batch updates**: Use session.flush() for incremental persistence, session.commit() at end

---

**Contract Status**: ✅ Defined - 8 functions with complete type signatures, FIFO algorithm documented
