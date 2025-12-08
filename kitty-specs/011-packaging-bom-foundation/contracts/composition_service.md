# Service Contract: Composition Service (Packaging Extensions)

**Service**: `src/services/composition_service.py`
**Feature**: 011-packaging-bom-foundation

## New Methods

### add_packaging_to_assembly

Adds a packaging product to a FinishedGood assembly.

```python
def add_packaging_to_assembly(
    assembly_id: int,
    packaging_product_id: int,
    quantity: float = 1.0,
    notes: Optional[str] = None,
    sort_order: int = 0
) -> Composition:
    """
    Add packaging product to a FinishedGood assembly.

    Args:
        assembly_id: ID of the parent FinishedGood
        packaging_product_id: ID of the packaging Product
        quantity: Quantity of packaging needed (supports decimals)
        notes: Optional notes for this packaging requirement
        sort_order: Display order (lower = earlier)

    Returns:
        Created Composition instance

    Raises:
        ValidationError: If assembly_id or packaging_product_id invalid
        ValidationError: If product is not a packaging product
        ValidationError: If quantity <= 0
        IntegrityError: If duplicate packaging for assembly
    """
```

### add_packaging_to_package

Adds a packaging product to a Package.

```python
def add_packaging_to_package(
    package_id: int,
    packaging_product_id: int,
    quantity: float = 1.0,
    notes: Optional[str] = None,
    sort_order: int = 0
) -> Composition:
    """
    Add packaging product to a Package.

    Args:
        package_id: ID of the parent Package
        packaging_product_id: ID of the packaging Product
        quantity: Quantity of packaging needed (supports decimals)
        notes: Optional notes for this packaging requirement
        sort_order: Display order (lower = earlier)

    Returns:
        Created Composition instance

    Raises:
        ValidationError: If package_id or packaging_product_id invalid
        ValidationError: If product is not a packaging product
        ValidationError: If quantity <= 0
        IntegrityError: If duplicate packaging for package
    """
```

### get_assembly_packaging

Retrieves all packaging compositions for a FinishedGood.

```python
def get_assembly_packaging(assembly_id: int) -> List[Composition]:
    """
    Get all packaging compositions for a FinishedGood assembly.

    Args:
        assembly_id: ID of the FinishedGood

    Returns:
        List of Composition instances where packaging_product_id is not null,
        sorted by sort_order
    """
```

### get_package_packaging

Retrieves all packaging compositions for a Package.

```python
def get_package_packaging(package_id: int) -> List[Composition]:
    """
    Get all packaging compositions for a Package.

    Args:
        package_id: ID of the Package

    Returns:
        List of Composition instances where packaging_product_id is not null,
        sorted by sort_order
    """
```

### update_packaging_quantity

Updates the quantity for a packaging composition.

```python
def update_packaging_quantity(
    composition_id: int,
    quantity: float
) -> Composition:
    """
    Update quantity for a packaging composition.

    Args:
        composition_id: ID of the Composition
        quantity: New quantity (must be > 0)

    Returns:
        Updated Composition instance

    Raises:
        ValidationError: If composition not found
        ValidationError: If composition is not a packaging composition
        ValidationError: If quantity <= 0
    """
```

### remove_packaging

Removes a packaging composition.

```python
def remove_packaging(composition_id: int) -> bool:
    """
    Remove a packaging composition.

    Args:
        composition_id: ID of the Composition to remove

    Returns:
        True if removed, False if not found

    Raises:
        ValidationError: If composition is not a packaging composition
    """
```

## Updated Methods

### create_composition (existing method update)

Add support for packaging_product_id parameter.

```python
def create_composition(
    assembly_id: Optional[int] = None,
    package_id: Optional[int] = None,  # NEW
    finished_unit_id: Optional[int] = None,
    finished_good_id: Optional[int] = None,
    packaging_product_id: Optional[int] = None,  # NEW
    quantity: float = 1.0,  # CHANGED: int -> float
    notes: Optional[str] = None,
    sort_order: int = 0
) -> Composition:
```

## Validation Rules

1. **Packaging product validation**: Before creating composition, verify the product's ingredient has `is_packaging=True`
2. **Parent XOR**: Exactly one of `assembly_id` or `package_id` must be provided
3. **Component XOR**: Exactly one of `finished_unit_id`, `finished_good_id`, or `packaging_product_id` must be provided
4. **Quantity positive**: `quantity > 0`
5. **Duplicate prevention**: No duplicate packaging products for same assembly/package

## Error Messages

| Error | Message |
|-------|---------|
| Invalid assembly | "FinishedGood with ID {id} not found" |
| Invalid package | "Package with ID {id} not found" |
| Invalid product | "Product with ID {id} not found" |
| Not packaging | "Product '{name}' is not a packaging product" |
| Invalid quantity | "Quantity must be greater than 0" |
| Duplicate | "Packaging product '{name}' already exists for this {assembly/package}" |
