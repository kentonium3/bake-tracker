# Service Contract: MaterialUnitService

**Module**: `src/services/material_unit_service.py`
**Purpose**: Manage MaterialUnits and calculate availability/cost aggregations

## Interface

### Unit CRUD

```python
def create_unit(
    material_id: int,
    name: str,
    quantity_per_unit: float,
    slug: str | None = None,
    description: str | None = None,
    session: Session | None = None
) -> MaterialUnit:
    """
    Create a MaterialUnit for a material.

    quantity_per_unit is in the material's base_unit_type:
    - 'each': 1 = one item
    - 'linear_inches': 6 = 6 inches
    - 'square_inches': 12 = 12 square inches
    """

def get_unit(
    unit_id: int | None = None,
    slug: str | None = None,
    session: Session | None = None
) -> MaterialUnit | None:
    """Get unit by ID or slug."""

def list_units(
    material_id: int | None = None,
    session: Session | None = None
) -> list[MaterialUnit]:
    """List units, optionally filtered by material."""

def update_unit(
    unit_id: int,
    name: str | None = None,
    description: str | None = None,
    session: Session | None = None
) -> MaterialUnit:
    """Update unit fields. Cannot change quantity_per_unit after creation."""

def delete_unit(
    unit_id: int,
    session: Session | None = None
) -> bool:
    """Delete unit. Raises if used in any Composition."""
```

### Availability Calculations

```python
def get_available_inventory(
    unit_id: int,
    session: Session | None = None
) -> int:
    """
    Calculate available inventory for a MaterialUnit.

    Formula:
    available = floor(sum(product.current_inventory) / unit.quantity_per_unit)

    Returns:
        Number of complete units available (integer, rounded down)
    """

def get_current_cost(
    unit_id: int,
    session: Session | None = None
) -> Decimal:
    """
    Calculate current cost for one MaterialUnit.

    Formula:
    cost = weighted_avg_cost_across_products * quantity_per_unit

    The weighted_avg_cost is calculated across all products for the material,
    weighted by their current_inventory.

    Returns:
        Cost per unit in dollars
    """

def get_unit_summary(
    unit_id: int,
    session: Session | None = None
) -> dict:
    """
    Get comprehensive summary for a MaterialUnit.

    Returns:
        {
            'unit_id': int,
            'name': str,
            'material_id': int,
            'material_name': str,
            'quantity_per_unit': float,
            'base_unit_type': str,
            'available_inventory': int,
            'current_cost': Decimal,
            'products': [
                {
                    'product_id': int,
                    'name': str,
                    'current_inventory': float,
                    'weighted_avg_cost': Decimal,
                    'units_available': int  # This product's contribution
                },
                ...
            ]
        }
    """
```

### Consumption Preview

```python
def preview_consumption(
    unit_id: int,
    quantity_needed: int,
    session: Session | None = None
) -> dict:
    """
    Preview what products would be consumed for a given quantity.

    Uses proportional allocation across products based on current inventory.

    Returns:
        {
            'can_fulfill': bool,
            'quantity_needed': int,
            'available': int,
            'shortage': int,  # 0 if can_fulfill
            'allocations': [
                {
                    'product_id': int,
                    'product_name': str,
                    'base_units_consumed': float,
                    'unit_cost': Decimal,
                    'total_cost': Decimal
                },
                ...
            ],
            'total_cost': Decimal
        }
    """
```

## Validation Rules

- quantity_per_unit must be > 0
- Cannot delete units used in compositions

## Error Handling

- `ValueError`: Invalid input (non-positive quantity)
- `NotFoundError`: Material or unit not found
