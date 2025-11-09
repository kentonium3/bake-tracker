---
work_package_id: "WP04"
subtasks: ["T038", "T039", "T040", "T041", "T042", "T043", "T044", "T045", "T046", "T047", "T048", "T049", "T050", "T051", "T052", "T053"]
title: "PantryService Implementation"
phase: "Phase 2 - Service Implementation"
lane: "done"
assignee: "Claude Code"
agent: "Claude Code"
shell_pid: "4504"
history:
  - timestamp: "2025-11-09T03:08:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: "4504"
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-11-09T07:58:47Z"
    lane: "done"
    agent: "Claude Code"
    shell_pid: "4504"
    action: "Work package completed - all tasks implemented and integration tests passing"
---

# Work Package Prompt: WP04 – PantryService Implementation

## Objectives & Success Criteria

Implement complete PantryService with 8 functions including **critical FIFO (First In, First Out) consumption algorithm**.

**Success Criteria**:
- FIFO consumption orders lots by purchase_date correctly in 100% of test cases (per spec SC-004)
- Shortfall calculations accurate to 0.001 (3 decimal places) (per spec SC-010)
- Unit conversion integration works correctly
- All pantry operations are transactionally atomic
- Expiring items query works efficiently

## Context & Constraints

**Contract**: `kitty-specs/002-service-layer-for/contracts/pantry_service.md`
**Data Model**: `kitty-specs/002-service-layer-for/data-model.md` - FIFO algorithm pseudocode
**Research**: `kitty-specs/002-service-layer-for/research.md` - FIFO decision (Python iteration, not SQL)

**Dependencies**: WP01 (infrastructure), WP02 (IngredientService), WP03 (VariantService)

**⚠️ CRITICAL FIFO Algorithm**:
- Query: ORDER BY purchase_date ASC (oldest first)
- Iteration: Python loop (not SQL window functions)
- Transaction: All updates in single session_scope()
- Edge cases: Insufficient inventory, partial lot consumption, unit conversion

## Subtasks

### T038-T039: add_to_pantry()

**Tests**:
- Successful addition with all fields
- ValidationError for quantity <= 0
- ValidationError for expiration_date < purchase_date
- VariantNotFound for invalid variant_id

**Implementation**:
```python
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any
from src.models import PantryItem
from src.services import session_scope, ValidationError, VariantNotFound
from src.services.variant_service import get_variant

def add_to_pantry(
    variant_id: int,
    quantity: Decimal,
    unit: str,
    purchase_date: date,
    expiration_date: Optional[date] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None
) -> PantryItem:
    """Add a new pantry item (lot) to inventory."""
    # Validate variant exists
    variant = get_variant(variant_id)

    # Validate quantity > 0
    if quantity <= 0:
        raise ValidationError("Quantity must be positive")

    # Validate dates
    if expiration_date and expiration_date < purchase_date:
        raise ValidationError("Expiration date cannot be before purchase date")

    with session_scope() as session:
        item = PantryItem(
            variant_id=variant_id,
            quantity=quantity,
            unit=unit,
            purchase_date=purchase_date,
            expiration_date=expiration_date,
            location=location,
            notes=notes
        )
        session.add(item)
        session.flush()
        return item
```

### T040-T041: get_pantry_items()

**Tests**: Filtering by ingredient_slug, variant_id, location, min_quantity

**Implementation**:
```python
from typing import List

def get_pantry_items(
    ingredient_slug: Optional[str] = None,
    variant_id: Optional[int] = None,
    location: Optional[str] = None,
    min_quantity: Optional[Decimal] = None
) -> List[PantryItem]:
    """Retrieve pantry items with optional filtering."""
    from src.models import Variant

    with session_scope() as session:
        q = session.query(PantryItem)

        if ingredient_slug:
            q = q.join(Variant).filter(Variant.ingredient_slug == ingredient_slug)
        if variant_id:
            q = q.filter(PantryItem.variant_id == variant_id)
        if location:
            q = q.filter(PantryItem.location == location)
        if min_quantity:
            q = q.filter(PantryItem.quantity >= min_quantity)

        return q.order_by(PantryItem.purchase_date.asc()).all()
```

### T042-T043: get_total_quantity()

**Tests**: Sum across multiple lots, unit conversion, empty inventory

**Implementation**:
```python
def get_total_quantity(ingredient_slug: str) -> Decimal:
    """Calculate total quantity for ingredient across all variants and locations."""
    from src.services.ingredient_service import get_ingredient
    from src.utils.unit_converter import convert_unit

    ingredient = get_ingredient(ingredient_slug)  # Validate exists
    target_unit = ingredient.recipe_unit

    items = get_pantry_items(ingredient_slug=ingredient_slug, min_quantity=Decimal("0.001"))

    total = Decimal("0.0")
    for item in items:
        converted = convert_unit(item.quantity, item.unit, target_unit, ingredient_slug)
        total += converted

    return total
```

### T044-T045: consume_fifo() ⚠️ **MOST CRITICAL FUNCTION**

**Tests (extensive)**:
- Single lot full consumption
- Multiple lots partial consumption
- Insufficient inventory (shortfall calculation)
- Exact quantity match
- Unit conversion during consumption
- Breakdown details accuracy
- Transaction rollback on error

**Implementation**:
```python
def consume_fifo(ingredient_slug: str, quantity_needed: Decimal) -> Dict[str, Any]:
    """Consume pantry inventory using FIFO logic."""
    from src.services.ingredient_service import get_ingredient
    from src.utils.unit_converter import convert_unit

    ingredient = get_ingredient(ingredient_slug)  # Validate exists

    with session_scope() as session:
        # Get all lots ordered by purchase_date ASC (oldest first)
        pantry_items = session.query(PantryItem).join(Variant).filter(
            Variant.ingredient_slug == ingredient_slug,
            PantryItem.quantity > 0
        ).order_by(PantryItem.purchase_date.asc()).all()

        consumed = Decimal("0.0")
        breakdown = []
        remaining_needed = quantity_needed

        for item in pantry_items:
            if remaining_needed <= Decimal("0.0"):
                break

            # Convert lot quantity to ingredient recipe_unit
            available = convert_unit(item.quantity, item.unit, ingredient.recipe_unit, ingredient_slug)

            # Consume up to available amount
            to_consume_in_recipe_unit = min(available, remaining_needed)

            # Convert back to lot's unit for deduction
            to_consume_in_lot_unit = convert_unit(to_consume_in_recipe_unit, ingredient.recipe_unit, item.unit, ingredient_slug)

            # Update lot quantity
            item.quantity -= to_consume_in_lot_unit
            consumed += to_consume_in_recipe_unit
            remaining_needed -= to_consume_in_recipe_unit

            breakdown.append({
                "pantry_item_id": item.id,
                "variant_id": item.variant_id,
                "lot_date": item.purchase_date,
                "quantity_consumed": to_consume_in_lot_unit,
                "unit": item.unit,
                "remaining_in_lot": item.quantity
            })

            session.flush()  # Persist update within transaction

        shortfall = max(Decimal("0.0"), remaining_needed)
        satisfied = shortfall == Decimal("0.0")

        return {
            "consumed": consumed,
            "breakdown": breakdown,
            "shortfall": shortfall,
            "satisfied": satisfied
        }
```

### T046-T047: get_expiring_soon()

**Tests**: Expiration date filtering, sorting, items without expiration_date excluded

**Implementation**:
```python
from datetime import timedelta

def get_expiring_soon(days: int = 14) -> List[PantryItem]:
    """Get pantry items expiring within specified days."""
    from datetime import date as date_type

    cutoff_date = date_type.today() + timedelta(days=days)

    with session_scope() as session:
        return session.query(PantryItem).filter(
            PantryItem.expiration_date.isnot(None),
            PantryItem.expiration_date <= cutoff_date,
            PantryItem.quantity > 0
        ).order_by(PantryItem.expiration_date.asc()).all()
```

### T048-T049: update_pantry_item()

**Tests**: Partial update, immutable fields (variant_id, purchase_date), validation

**Implementation**: Similar pattern to update_ingredient, prevent changing variant_id/purchase_date

### T050-T051: delete_pantry_item()

**Tests**: Successful deletion, PantryItemNotFound

**Implementation**: Standard delete with get-first pattern

### T052-T053: get_pantry_value()

**Tests**: Value calculation, zero for no cost data

**Implementation**:
```python
def get_pantry_value() -> Decimal:
    """Calculate total value of all pantry inventory."""
    # NOTE: This requires cost tracking in PantryItem model
    # If not implemented, return Decimal("0.0")
    # Future: Join with Purchase to get unit_cost, multiply by quantity
    return Decimal("0.0")  # TODO: Implement when cost tracking ready
```

## Test Strategy

**Test file**: `src/tests/test_pantry_service.py`

**FIFO Test Scenarios** (comprehensive):
```python
def test_consume_fifo_single_lot():
    """Test consuming from single lot."""
    # Add 10.0 lb lot on 2025-01-01
    # Consume 5.0 lb
    # Assert: consumed=5.0, lot quantity=5.0, satisfied=True, shortfall=0

def test_consume_fifo_multiple_lots():
    """Test consuming across multiple lots in order."""
    # Add lot1: 10.0 lb on 2025-01-01
    # Add lot2: 15.0 lb on 2025-01-15
    # Consume 12.0 lb
    # Assert: lot1 depleted (0.0), lot2 has 13.0 remaining

def test_consume_fifo_insufficient_inventory():
    """Test shortfall calculation when inventory insufficient."""
    # Add lot: 10.0 lb
    # Consume 15.0 lb
    # Assert: consumed=10.0, shortfall=5.0, satisfied=False

def test_consume_fifo_unit_conversion():
    """Test unit conversion during FIFO consumption."""
    # Add lot: 25.0 lb (=100 cups @ 4 cups/lb)
    # Consume 50.0 cups
    # Assert: lot has 12.5 lb remaining
```

**Run tests**: `pytest src/tests/test_pantry_service.py -v --cov=src/services/pantry_service`

**Performance test**: FIFO with 100+ lots (should complete <1 second per research decision)

## Risks & Mitigations

**Risk**: Unit conversion errors in FIFO → Use unit_converter.py consistently, test all conversion paths
**Risk**: Decimal rounding errors → Never use float, maintain 3 decimal precision
**Risk**: Transaction rollback failure → Test exception handling, verify rollback
**Risk**: FIFO ordering incorrect → Index on purchase_date, extensive ordering tests

## Definition of Done Checklist

- [x] All 16 subtasks completed
- [x] `src/services/pantry_service.py` created with 8 functions
- [x] FIFO algorithm works correctly (100% pass rate on ordering tests)
- [x] Shortfall calculations accurate to 0.001
- [x] Unit conversion integrated correctly
- [x] All tests pass with >70% coverage
- [x] Performance test passes (100 lots FIFO <1s)

## Activity Log

- 2025-11-09T03:08:51Z – system – lane=planned – Prompt created.
- 2025-11-09T08:02:39Z – Claude Code – lane=done – Work package completed. All tasks implemented and integration tests passing.

