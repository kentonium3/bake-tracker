# Service Contract: MaterialConsumptionService

**Module**: `src/services/material_consumption_service.py`
**Purpose**: Handle material consumption during assembly, create snapshots, decrement inventory

## Interface

### Assembly Material Validation

```python
def get_pending_materials(
    finished_good_id: int,
    session: Session | None = None
) -> list[dict]:
    """
    Get materials requiring resolution for a FinishedGood.

    Finds Composition entries where:
    - material_id is set (generic placeholder)
    - is_generic = True

    Returns:
        [
            {
                'composition_id': int,
                'material_id': int,
                'material_name': str,
                'quantity_needed': float,
                'available_products': [
                    {
                        'product_id': int,
                        'name': str,
                        'available_units': int,
                        'unit_cost': Decimal
                    },
                    ...
                ]
            },
            ...
        ]
    """

def validate_material_availability(
    finished_good_id: int,
    assembly_quantity: int,
    material_assignments: dict[int, list[dict]] | None = None,
    session: Session | None = None
) -> dict:
    """
    Validate that all materials are available for assembly.

    Args:
        finished_good_id: The FinishedGood being assembled
        assembly_quantity: How many units being assembled
        material_assignments: For generic materials, specifies which products to use:
            {
                composition_id: [
                    {'product_id': int, 'quantity': int},
                    ...
                ]
            }

    Returns:
        {
            'valid': bool,
            'errors': [str, ...],  # Empty if valid
            'material_requirements': [
                {
                    'composition_id': int,
                    'is_generic': bool,
                    'material_name': str,
                    'base_units_needed': float,
                    'available': float,
                    'sufficient': bool,
                    'assignments': [...]  # Only for generic materials
                },
                ...
            ]
        }
    """
```

### Consumption Recording

```python
def record_material_consumption(
    assembly_run_id: int,
    finished_good_id: int,
    assembly_quantity: int,
    material_assignments: dict[int, list[dict]] | None = None,
    session: Session | None = None
) -> list[MaterialConsumption]:
    """
    Record all material consumption for an assembly run.

    This function:
    1. Resolves generic materials using material_assignments
    2. Creates MaterialConsumption records with full snapshots
    3. Decrements MaterialProduct.current_inventory
    4. Validates sufficient inventory (raises if insufficient)

    Args:
        assembly_run_id: The AssemblyRun being recorded
        finished_good_id: The FinishedGood being assembled
        assembly_quantity: How many units assembled
        material_assignments: Product selections for generic materials

    Returns:
        List of created MaterialConsumption records

    Raises:
        ValidationError: If any material has insufficient inventory
        ValueError: If generic material missing from assignments
    """

def get_consumption_by_assembly(
    assembly_run_id: int,
    session: Session | None = None
) -> list[MaterialConsumption]:
    """Get all material consumption records for an assembly run."""

def get_material_cost_for_assembly(
    assembly_run_id: int,
    session: Session | None = None
) -> Decimal:
    """Calculate total material cost for an assembly run."""
```

### Historical Queries

```python
def get_consumption_history(
    material_id: int | None = None,
    product_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    session: Session | None = None
) -> list[dict]:
    """
    Query historical consumption with snapshot data.

    Returns consumption records with their point-in-time snapshot data,
    not current catalog values.

    Returns:
        [
            {
                'consumption_id': int,
                'assembly_run_id': int,
                'assembly_date': datetime,
                'quantity_consumed': float,
                'unit_cost': Decimal,
                'total_cost': Decimal,
                # Snapshot fields (values at time of consumption)
                'product_name': str,
                'material_name': str,
                'subcategory_name': str,
                'category_name': str,
                'supplier_name': str | None
            },
            ...
        ]
    """
```

## Internal Functions

```python
def _create_consumption_snapshot(
    product: MaterialProduct,
    quantity_consumed: float,
    unit_cost: Decimal,
    session: Session
) -> dict:
    """
    Create snapshot data for consumption record.

    Captures current names from product -> material -> subcategory -> category chain.
    """

def _allocate_consumption_across_products(
    material_id: int,
    base_units_needed: float,
    session: Session
) -> list[dict]:
    """
    Allocate consumption proportionally across available products.

    Uses proportional allocation weighted by current_inventory.
    """
```

## Validation Rules

- All generic materials must have assignments before recording
- Total assigned quantity must equal required quantity per generic material
- Inventory must be sufficient for all consumption (no negative inventory)
- Consumption records are immutable (no update/delete)

## Error Handling

- `ValidationError`: Insufficient inventory, missing assignments
- `ValueError`: Invalid quantity, missing required parameters
- `NotFoundError`: Assembly run, finished good, or product not found
