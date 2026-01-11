# Service Contract: MaterialPurchaseService

**Module**: `src/services/material_purchase_service.py`
**Purpose**: Record purchases, update inventory, manage weighted average costing

## Interface

### Purchase Recording

```python
def record_purchase(
    product_id: int,
    supplier_id: int,
    purchase_date: date,
    packages_purchased: int,
    package_price: Decimal,
    notes: str | None = None,
    session: Session | None = None
) -> MaterialPurchase:
    """
    Record a material purchase.

    Side effects:
    - Creates immutable MaterialPurchase record
    - Updates MaterialProduct.current_inventory (adds units)
    - Recalculates MaterialProduct.weighted_avg_cost

    Returns:
        The created MaterialPurchase record
    """

def get_purchase(
    purchase_id: int,
    session: Session | None = None
) -> MaterialPurchase | None:
    """Get purchase by ID."""

def list_purchases(
    product_id: int | None = None,
    supplier_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    session: Session | None = None
) -> list[MaterialPurchase]:
    """List purchases with optional filtering."""
```

### Inventory Adjustment

```python
def adjust_inventory(
    product_id: int,
    new_quantity: float | None = None,
    percentage: float | None = None,
    notes: str | None = None,
    session: Session | None = None
) -> MaterialProduct:
    """
    Adjust product inventory.

    Exactly one of new_quantity or percentage must be provided.
    - new_quantity: Set inventory to this exact value (in base units)
    - percentage: Multiply current inventory by this percentage (0.0 to 1.0)

    Note: weighted_avg_cost is NOT changed by adjustments.

    Returns:
        Updated MaterialProduct
    """

def get_inventory_summary(
    material_id: int,
    session: Session | None = None
) -> dict:
    """
    Get aggregated inventory across all products for a material.

    Returns:
        {
            'material_id': int,
            'material_name': str,
            'base_unit_type': str,
            'total_inventory': float,  # Sum across all products
            'weighted_avg_cost': Decimal,  # Weighted across products
            'products': [
                {
                    'product_id': int,
                    'name': str,
                    'current_inventory': float,
                    'weighted_avg_cost': Decimal
                },
                ...
            ]
        }
    """
```

### Weighted Average Calculation

```python
def calculate_weighted_average(
    current_quantity: float,
    current_avg_cost: Decimal,
    added_quantity: float,
    added_unit_cost: Decimal
) -> Decimal:
    """
    Calculate new weighted average cost after adding inventory.

    Formula:
    new_avg = (current_qty * current_avg + added_qty * added_cost) / (current_qty + added_qty)

    Special cases:
    - If current_quantity == 0: return added_unit_cost
    - If added_quantity == 0: return current_avg_cost
    """
```

## Validation Rules

- packages_purchased must be > 0
- package_price must be >= 0
- percentage must be between 0.0 and 1.0 (inclusive)
- new_quantity must be >= 0
- Cannot set inventory negative

## Error Handling

- `ValueError`: Invalid input (negative packages, percentage out of range)
- `NotFoundError`: Product or supplier not found
