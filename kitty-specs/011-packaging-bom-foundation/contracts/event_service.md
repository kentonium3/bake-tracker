# Service Contract: Event Service (Shopping List Extensions)

**Service**: `src/services/event_service.py`
**Feature**: 011-packaging-bom-foundation

## New Data Classes

### PackagingNeed

```python
@dataclass
class PackagingNeed:
    """Represents packaging requirement for shopping list."""
    product_id: int
    product: Product  # Reference to Product instance
    ingredient_name: str  # e.g., "Cellophane Cookie Bags"
    product_display_name: str  # e.g., "Amazon Basics 100 count"
    total_needed: float  # Total quantity needed for event
    on_hand: float  # Current inventory quantity
    to_buy: float  # max(0, total_needed - on_hand)
    unit: str  # Purchase unit (e.g., "pack", "roll")
```

### PackagingSource

```python
@dataclass
class PackagingSource:
    """Tracks where packaging need originated."""
    source_type: str  # "finished_good" or "package"
    source_id: int
    source_name: str  # e.g., "Cookie Dozen Bag" or "Holiday Gift Box"
    quantity_per: float  # Quantity needed per source
    source_count: int  # How many of this source in event
    total_for_source: float  # quantity_per * source_count
```

## New Methods

### get_event_packaging_needs

Calculates all packaging needs for an event.

```python
def get_event_packaging_needs(event_id: int) -> Dict[int, PackagingNeed]:
    """
    Calculate packaging material needs for an event.

    Aggregates packaging from:
    1. Package-level packaging (Package.packaging_compositions)
    2. FinishedGood-level packaging (FinishedGood.components where packaging_product_id is set)

    Args:
        event_id: ID of the event

    Returns:
        Dict mapping product_id -> PackagingNeed

    Raises:
        EventNotFoundError: If event doesn't exist

    Example:
        needs = get_event_packaging_needs(1)
        for product_id, need in needs.items():
            print(f"{need.ingredient_name}: need {need.total_needed}, buy {need.to_buy}")
    """
```

### get_event_packaging_breakdown

Provides detailed breakdown of packaging needs by source.

```python
def get_event_packaging_breakdown(event_id: int) -> Dict[int, List[PackagingSource]]:
    """
    Get detailed breakdown of where packaging needs come from.

    Args:
        event_id: ID of the event

    Returns:
        Dict mapping product_id -> List[PackagingSource]
        Shows which FinishedGoods/Packages contribute to each packaging need

    Example:
        breakdown = get_event_packaging_breakdown(1)
        for product_id, sources in breakdown.items():
            for src in sources:
                print(f"  From {src.source_type} '{src.source_name}': {src.total_for_source}")
    """
```

### get_event_shopping_list

Updated to include packaging section.

```python
def get_event_shopping_list(
    event_id: int,
    include_packaging: bool = True  # NEW parameter
) -> Dict[str, Any]:
    """
    Get complete shopping list for an event.

    Args:
        event_id: ID of the event
        include_packaging: If True, include packaging section (default: True)

    Returns:
        Dict with structure:
        {
            "event": {...},
            "ingredients": [
                {
                    "ingredient_name": str,
                    "total_needed": float,
                    "on_hand": float,
                    "to_buy": float,
                    "unit": str
                },
                ...
            ],
            "packaging": [  # NEW section
                {
                    "ingredient_name": str,
                    "product_name": str,
                    "total_needed": float,
                    "on_hand": float,
                    "to_buy": float,
                    "unit": str
                },
                ...
            ]
        }
    """
```

## Implementation Notes

### Aggregation Logic

```python
def _aggregate_packaging(event_id: int) -> Dict[int, float]:
    """
    Internal method to aggregate packaging quantities.

    For each EventRecipientPackage (erp) in event:
        package_qty = erp.quantity

        # Package-level packaging
        for comp in erp.package.packaging_compositions:
            needs[comp.packaging_product_id] += comp.component_quantity * package_qty

        # FinishedGood-level packaging
        for pfg in erp.package.package_finished_goods:
            fg_qty = pfg.quantity * package_qty
            for comp in pfg.finished_good.components:
                if comp.packaging_product_id:
                    needs[comp.packaging_product_id] += comp.component_quantity * fg_qty

    return needs
```

### Inventory Lookup

```python
def _get_packaging_on_hand(product_id: int) -> float:
    """
    Get current inventory quantity for a packaging product.

    Uses inventory_item_service.get_total_quantity_for_product(product_id)
    """
```

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Event has no packages | Return empty dicts for packaging |
| Package has no packaging | Skip, don't add to needs |
| FinishedGood has no packaging | Skip, don't add to needs |
| Same packaging in multiple places | Aggregate correctly |
| No inventory for packaging | to_buy = total_needed |
| Inventory exceeds need | to_buy = 0 |

## Error Messages

| Error | Message |
|-------|---------|
| Event not found | "Event with ID {id} not found" |
