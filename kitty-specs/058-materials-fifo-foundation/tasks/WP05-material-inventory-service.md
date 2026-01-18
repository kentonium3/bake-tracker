---
work_package_id: "WP05"
subtasks:
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "MaterialInventoryService Core"
phase: "Phase 2 - Services"
lane: "doing"
assignee: "claude-opus"
agent: "claude-opus"
shell_pid: "28309"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: ["WP01", "WP04"]
history:
  - timestamp: "2026-01-18T18:06:18Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2026-01-18T21:30:00Z"
    lane: "done"
    agent: "claude-opus"
    shell_pid: ""
    action: "Review passed: MaterialInventoryService with FIFO consumption operations"
---

# Work Package Prompt: WP05 – MaterialInventoryService Core

## Implementation Command

```bash
spec-kitty implement WP05 --base WP01
```

**Note**: Also requires WP04 (unit converter) to be complete.

## Objectives & Success Criteria

Create the service layer for material inventory FIFO operations, paralleling `inventory_item_service.py`.

**Success Criteria**:
- `get_fifo_inventory()` returns lots ordered by purchase_date ASC (oldest first)
- `consume_material_fifo()` correctly consumes from oldest lots first
- `calculate_available_inventory()` sums quantity_remaining across all lots
- `validate_inventory_availability()` checks if requirements can be met
- All functions follow session management pattern per CLAUDE.md

## Context & Constraints

**Reference Documents**:
- `src/services/inventory_item_service.py` - **PRIMARY PATTERN TO COPY**
- `kitty-specs/058-materials-fifo-foundation/research.md` - Pattern 2: FIFO Algorithm
- `kitty-specs/058-materials-fifo-foundation/plan.md` - Service layer requirements
- `CLAUDE.md` - Session management rules

**Key Constraints**:
- Follow session management pattern: accept optional `session=None` parameter
- Return structure must match spec: `{consumed, breakdown, shortfall, satisfied, total_cost}`
- Filter quantity_remaining > 0.001 to avoid floating-point dust
- All quantities in base units (cm)

## Subtasks & Detailed Guidance

### Subtask T017 – Create material_inventory_service.py structure

**Purpose**: Set up the service file with imports and docstring.

**Steps**:
1. Create `src/services/material_inventory_service.py`:

```python
"""Material Inventory Service - FIFO inventory management for materials.

This module provides business logic for managing material inventory including
lot tracking, FIFO (First In, First Out) consumption, and availability checks.

All functions are stateless and follow the session pattern:
- If session provided: caller owns transaction, don't commit
- If session is None: create own transaction via session_scope()

Key Features:
- Lot-based inventory tracking (purchase date, cost per unit)
- FIFO consumption algorithm - oldest lots consumed first
- Unit conversion during consumption
- Availability validation

Example Usage:
    >>> from src.services.material_inventory_service import consume_material_fifo
    >>> result = consume_material_fifo(
    ...     material_product_id=123,
    ...     quantity_needed=Decimal("100"),
    ...     target_unit="cm",
    ... )
    >>> result["satisfied"]  # True if enough inventory
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import date

from sqlalchemy.orm import Session, joinedload

from ..models import MaterialInventoryItem, MaterialProduct, Material
from .database import session_scope
from .exceptions import (
    ValidationError as ServiceValidationError,
    DatabaseError,
)
from .material_unit_converter import (
    convert_to_base_units,
    convert_from_base_units,
    validate_unit_compatibility,
)
```

**Files**:
- Create: `src/services/material_inventory_service.py`

**Parallel?**: No (foundation for other subtasks)

### Subtask T018 – Implement get_fifo_inventory()

**Purpose**: Query inventory items ordered by purchase date for FIFO consumption.

**Steps**:
1. Add function to `material_inventory_service.py`:

```python
def get_fifo_inventory(
    material_product_id: int,
    session: Optional[Session] = None,
) -> List[MaterialInventoryItem]:
    """
    Get inventory items for a material product ordered by purchase date (FIFO).

    Returns lots with quantity_remaining > 0.001, ordered oldest first.

    Args:
        material_product_id: ID of the MaterialProduct
        session: Optional database session for transaction composability

    Returns:
        List[MaterialInventoryItem]: Inventory items ordered by purchase_date ASC

    Example:
        >>> lots = get_fifo_inventory(material_product_id=123)
        >>> lots[0].purchase_date < lots[1].purchase_date  # Oldest first
        True
    """
    def _do_query(sess: Session) -> List[MaterialInventoryItem]:
        return (
            sess.query(MaterialInventoryItem)
            .options(
                joinedload(MaterialInventoryItem.product)
                .joinedload(MaterialProduct.material)
            )
            .filter(
                MaterialInventoryItem.material_product_id == material_product_id,
                MaterialInventoryItem.quantity_remaining >= 0.001,  # Avoid float dust
            )
            .order_by(MaterialInventoryItem.purchase_date.asc())
            .all()
        )

    if session is not None:
        return _do_query(session)
    else:
        with session_scope() as sess:
            return _do_query(sess)
```

**Files**:
- Edit: `src/services/material_inventory_service.py`

**Parallel?**: Yes (independent function)

### Subtask T019 – Implement calculate_available_inventory()

**Purpose**: Sum total available inventory across all lots.

**Steps**:
1. Add function to `material_inventory_service.py`:

```python
def calculate_available_inventory(
    material_product_id: int,
    session: Optional[Session] = None,
) -> Decimal:
    """
    Calculate total available inventory for a material product.

    Sums quantity_remaining across all lots (base units).

    Args:
        material_product_id: ID of the MaterialProduct
        session: Optional database session

    Returns:
        Decimal: Total quantity available in base units (cm or count)

    Example:
        >>> available = calculate_available_inventory(material_product_id=123)
        >>> available
        Decimal('5000.0')  # 5000 cm available
    """
    def _do_sum(sess: Session) -> Decimal:
        lots = get_fifo_inventory(material_product_id, session=sess)
        return sum(
            Decimal(str(lot.quantity_remaining)) for lot in lots
        )

    if session is not None:
        return _do_sum(session)
    else:
        with session_scope() as sess:
            return _do_sum(sess)
```

**Files**:
- Edit: `src/services/material_inventory_service.py`

**Parallel?**: Yes (depends on T018 being done)

### Subtask T020 – Implement consume_material_fifo() algorithm

**Purpose**: Core FIFO consumption algorithm - consumes from oldest lots first.

**Steps**:
1. Add function to `material_inventory_service.py`:

```python
def consume_material_fifo(
    material_product_id: int,
    quantity_needed: Decimal,
    target_unit: str,
    context_id: Optional[int] = None,  # e.g., assembly_run_id
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Consume material inventory using FIFO (First In, First Out) logic.

    **CRITICAL FUNCTION**: Implements core inventory consumption algorithm.

    Algorithm:
        1. Query all lots for product ordered by purchase_date ASC (oldest first)
        2. Iterate through lots, consuming from each until quantity satisfied
        3. Convert between target_unit and base units as needed
        4. Update lot quantities atomically (unless dry_run)
        5. Track consumption breakdown for audit trail
        6. Calculate total FIFO cost

    Args:
        material_product_id: Product to consume from
        quantity_needed: Amount to consume in target_unit
        target_unit: Unit that quantity_needed is expressed in
        context_id: Optional reference (e.g., assembly_run_id)
        dry_run: If True, simulate without modifying database
        session: Optional database session (caller owns transaction if provided)

    Returns:
        Dict with keys:
            - "consumed" (Decimal): Amount consumed in target_unit
            - "breakdown" (List[Dict]): Per-lot details with unit_cost
            - "shortfall" (Decimal): Amount not available (0.0 if satisfied)
            - "satisfied" (bool): True if quantity_needed fully consumed
            - "total_cost" (Decimal): Total FIFO cost of consumed portion

    Example:
        >>> result = consume_material_fifo(123, Decimal("100"), "cm")
        >>> result["satisfied"]
        True
        >>> result["total_cost"]
        Decimal("15.00")
    """
    def _do_consume(sess: Session) -> Dict[str, Any]:
        # Get product to determine base_unit_type
        product = sess.query(MaterialProduct).options(
            joinedload(MaterialProduct.material)
        ).filter(MaterialProduct.id == material_product_id).first()

        if not product:
            raise ServiceValidationError([f"Material product {material_product_id} not found"])

        base_unit_type = product.material.base_unit_type

        # Convert quantity_needed to base units
        success, qty_in_base, error = convert_to_base_units(
            quantity_needed, target_unit, base_unit_type
        )
        if not success:
            raise ServiceValidationError([error])

        # Get all lots ordered by purchase_date ASC (oldest first)
        lots = get_fifo_inventory(material_product_id, session=sess)

        consumed_base = Decimal("0.0")
        total_cost = Decimal("0.0")
        breakdown = []
        remaining_needed = qty_in_base

        for lot in lots:
            if remaining_needed <= Decimal("0.0"):
                break

            lot_remaining = Decimal(str(lot.quantity_remaining))
            lot_cost_per_unit = Decimal(str(lot.cost_per_unit)) if lot.cost_per_unit else Decimal("0.0")

            # Consume up to available amount
            to_consume = min(lot_remaining, remaining_needed)

            # Calculate cost for this lot
            lot_cost = to_consume * lot_cost_per_unit
            total_cost += lot_cost

            # Update lot quantity (unless dry_run)
            if not dry_run:
                lot.quantity_remaining = float(lot_remaining - to_consume)

            consumed_base += to_consume
            remaining_needed -= to_consume

            # Calculate remaining_in_lot for breakdown
            if dry_run:
                remaining_in_lot = lot_remaining - to_consume
            else:
                remaining_in_lot = Decimal(str(lot.quantity_remaining))

            breakdown.append({
                "inventory_item_id": lot.id,
                "quantity_consumed": to_consume,
                "unit": "base_units",  # Always in base units internally
                "remaining_in_lot": remaining_in_lot,
                "unit_cost": lot_cost_per_unit,
                "purchase_date": lot.purchase_date,
            })

            if not dry_run:
                sess.flush()

        # Convert consumed back to target_unit for return
        success, consumed_target, _ = convert_from_base_units(
            consumed_base, target_unit, base_unit_type
        )
        if not success:
            consumed_target = consumed_base  # Fallback

        # Calculate shortfall in target units
        shortfall_base = max(Decimal("0.0"), remaining_needed)
        success, shortfall_target, _ = convert_from_base_units(
            shortfall_base, target_unit, base_unit_type
        )
        if not success:
            shortfall_target = shortfall_base

        return {
            "consumed": consumed_target,
            "breakdown": breakdown,
            "shortfall": shortfall_target,
            "satisfied": shortfall_base == Decimal("0.0"),
            "total_cost": total_cost,
        }

    try:
        if session is not None:
            return _do_consume(session)
        else:
            with session_scope() as sess:
                return _do_consume(sess)
    except ServiceValidationError:
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to consume FIFO for material product {material_product_id}",
            original_error=e,
        )
```

**Files**:
- Edit: `src/services/material_inventory_service.py`

**Parallel?**: Yes (core function)

**Notes**:
- This is the most critical function - copy pattern from `inventory_item_service.py:consume_fifo()`
- Ensure atomicity: all updates in same transaction
- Filter `>= 0.001` to avoid floating-point dust issues

### Subtask T021 – Implement validate_inventory_availability()

**Purpose**: Check if sufficient inventory exists to meet requirements.

**Steps**:
1. Add function to `material_inventory_service.py`:

```python
def validate_inventory_availability(
    requirements: List[Dict[str, Any]],
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Validate if sufficient inventory exists for given requirements.

    Args:
        requirements: List of dicts with keys:
            - "material_product_id" (int): Product to check
            - "quantity_needed" (Decimal): Amount needed
            - "unit" (str): Unit for quantity
        session: Optional database session

    Returns:
        Dict with keys:
            - "can_fulfill" (bool): True if all requirements met
            - "shortfalls" (List[Dict]): Details of any shortfalls

    Example:
        >>> result = validate_inventory_availability([
        ...     {"material_product_id": 123, "quantity_needed": Decimal("100"), "unit": "cm"},
        ... ])
        >>> result["can_fulfill"]
        True
    """
    def _do_validate(sess: Session) -> Dict[str, Any]:
        shortfalls = []

        for req in requirements:
            product_id = req["material_product_id"]
            qty_needed = req["quantity_needed"]
            unit = req["unit"]

            # Use dry_run to check without consuming
            result = consume_material_fifo(
                material_product_id=product_id,
                quantity_needed=qty_needed,
                target_unit=unit,
                dry_run=True,
                session=sess,
            )

            if not result["satisfied"]:
                shortfalls.append({
                    "material_product_id": product_id,
                    "quantity_needed": qty_needed,
                    "quantity_available": result["consumed"],
                    "shortfall": result["shortfall"],
                    "unit": unit,
                })

        return {
            "can_fulfill": len(shortfalls) == 0,
            "shortfalls": shortfalls,
        }

    if session is not None:
        return _do_validate(session)
    else:
        with session_scope() as sess:
            return _do_validate(sess)
```

**Files**:
- Edit: `src/services/material_inventory_service.py`

**Parallel?**: Yes (uses consume_material_fifo with dry_run)

## Test Strategy

Unit tests will be in WP06. For this WP, verify functions work via manual testing:

```python
# Quick smoke test
from src.services.material_inventory_service import get_fifo_inventory
lots = get_fifo_inventory(1)  # Should return empty list or lots
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FIFO algorithm correctness | Copy pattern from inventory_item_service.py exactly |
| Session management bugs | Follow CLAUDE.md pattern strictly |
| Unit conversion errors | Use material_unit_converter with error handling |
| Floating-point precision | Use Decimal for calculations, filter >= 0.001 |

## Definition of Done Checklist

- [ ] `material_inventory_service.py` created with proper imports
- [ ] `get_fifo_inventory()` returns lots ordered by purchase_date ASC
- [ ] `calculate_available_inventory()` correctly sums quantities
- [ ] `consume_material_fifo()` implements FIFO algorithm
- [ ] `validate_inventory_availability()` checks requirements
- [ ] All functions accept optional `session` parameter
- [ ] Functions can be imported without errors
- [ ] Basic smoke test passes

## Review Guidance

**Key acceptance checkpoints**:
1. Verify FIFO ordering: oldest purchase_date first
2. Verify session pattern: `if session is not None: ... else: with session_scope()`
3. Verify return structure matches spec exactly
4. Verify unit conversion is used correctly
5. Verify dry_run mode doesn't modify database

## Activity Log

- 2026-01-18T18:06:18Z – system – lane=planned – Prompt created.
- 2026-01-18T19:09:59Z – claude – lane=doing – Starting MaterialInventoryService implementation
- 2026-01-18T19:20:30Z – claude – lane=for_review – T017-T021 complete: MaterialInventoryService with FIFO operations
- 2026-01-18T20:07:07Z – claude-opus – lane=done – Review passed: MaterialInventoryService with FIFO consumption operations
- 2026-01-18T21:33:45Z – claude-opus – shell_pid=28309 – lane=doing – Started review via workflow command
