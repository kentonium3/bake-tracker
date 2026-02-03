"""
Finished Goods Inventory Service.

This module provides session-aware primitives for managing finished goods
inventory (FinishedUnit and FinishedGood models). All inventory changes
are tracked with audit records via the FinishedGoodsAdjustment model.

Key Functions:
- Query Functions: get_inventory_status, get_low_stock_items, get_total_inventory_value
- Validation Functions: check_availability, validate_consumption
- Mutation Function: adjust_inventory (creates audit trail)

Session Pattern:
All functions accept an optional `session` parameter. If provided, the function
uses the caller's session (for transaction atomicity). If None, the function
creates its own session via session_scope().

Feature: F061 - Finished Goods Inventory Service
"""

from typing import Optional
from decimal import Decimal

from sqlalchemy.orm import joinedload

from src.services.database import session_scope
from src.models.finished_unit import FinishedUnit
from src.models.finished_good import FinishedGood
from src.models.finished_goods_adjustment import FinishedGoodsAdjustment
from src.utils.constants import (
    DEFAULT_LOW_STOCK_THRESHOLD,
    FINISHED_GOODS_ADJUSTMENT_REASONS,
)


# =============================================================================
# Query Functions
# =============================================================================


def get_inventory_status(
    item_type: Optional[str] = None,
    item_id: Optional[int] = None,
    exclude_zero: bool = False,
    session=None,
) -> list[dict]:
    """
    Get inventory status for finished goods.

    Transaction boundary: Read-only operation.
    Creates own session if none provided; uses caller's session if passed.

    Returns inventory information including current counts, costs, and values
    for FinishedUnits and/or FinishedGoods.

    Args:
        item_type: Filter by type - "finished_unit" or "finished_good".
                   If None, returns both types.
        item_id: Filter to specific item ID. Requires item_type to be set.
        exclude_zero: If True, exclude items with inventory_count == 0.
        session: Optional SQLAlchemy session for transactional composition.

    Returns:
        List of dicts with keys:
        - item_type: "finished_unit" or "finished_good"
        - id: Item ID
        - slug: URL-safe identifier
        - display_name: Human-readable name
        - inventory_count: Current quantity
        - current_cost: Decimal cost per unit
        - total_value: Decimal (inventory_count * current_cost)

    Raises:
        ValueError: If item_type is invalid or item_id provided without item_type.
    """
    if session is not None:
        return _get_inventory_status_impl(item_type, item_id, exclude_zero, session)
    with session_scope() as session:
        return _get_inventory_status_impl(item_type, item_id, exclude_zero, session)


def _get_inventory_status_impl(
    item_type: Optional[str],
    item_id: Optional[int],
    exclude_zero: bool,
    session,
) -> list[dict]:
    """Implementation for get_inventory_status.

    Transaction boundary: Inherits session from caller.
    Read-only operation.
    """
    # Validate item_type
    valid_types = ("finished_unit", "finished_good")
    if item_type is not None and item_type not in valid_types:
        raise ValueError(f"Invalid item_type: {item_type}. Must be one of: {valid_types}")

    # item_id requires item_type
    if item_id is not None and item_type is None:
        raise ValueError("item_id requires item_type to be specified")

    results = []

    # Query FinishedUnits
    if item_type is None or item_type == "finished_unit":
        query = session.query(FinishedUnit)
        if item_id is not None:
            query = query.filter(FinishedUnit.id == item_id)
        if exclude_zero:
            query = query.filter(FinishedUnit.inventory_count > 0)

        for unit in query.all():
            current_cost = unit.calculate_current_cost()
            results.append({
                "item_type": "finished_unit",
                "id": unit.id,
                "slug": unit.slug,
                "display_name": unit.display_name,
                "inventory_count": unit.inventory_count,
                "current_cost": current_cost,
                "total_value": unit.inventory_count * current_cost,
            })

    # Query FinishedGoods
    if item_type is None or item_type == "finished_good":
        query = session.query(FinishedGood)
        if item_id is not None:
            query = query.filter(FinishedGood.id == item_id)
        if exclude_zero:
            query = query.filter(FinishedGood.inventory_count > 0)

        for good in query.all():
            current_cost = good.calculate_current_cost()
            results.append({
                "item_type": "finished_good",
                "id": good.id,
                "slug": good.slug,
                "display_name": good.display_name,
                "inventory_count": good.inventory_count,
                "current_cost": current_cost,
                "total_value": good.inventory_count * current_cost,
            })

    return results


def get_low_stock_items(
    threshold: Optional[int] = None,
    item_type: Optional[str] = None,
    session=None,
) -> list[dict]:
    """
    Get items with inventory below a threshold.

    Transaction boundary: Read-only operation.
    Creates own session if none provided; uses caller's session if passed.

    Args:
        threshold: Inventory count threshold. Defaults to DEFAULT_LOW_STOCK_THRESHOLD.
        item_type: Filter by type - "finished_unit" or "finished_good".
                   If None, returns both types.
        session: Optional SQLAlchemy session for transactional composition.

    Returns:
        List of dicts (same structure as get_inventory_status) ordered by
        inventory_count ascending (lowest first).

    Raises:
        ValueError: If item_type is invalid.
    """
    if session is not None:
        return _get_low_stock_items_impl(threshold, item_type, session)
    with session_scope() as session:
        return _get_low_stock_items_impl(threshold, item_type, session)


def _get_low_stock_items_impl(
    threshold: Optional[int],
    item_type: Optional[str],
    session,
) -> list[dict]:
    """Implementation for get_low_stock_items.

    Transaction boundary: Inherits session from caller.
    Read-only operation.
    """
    # Default threshold
    if threshold is None:
        threshold = DEFAULT_LOW_STOCK_THRESHOLD

    # Validate item_type
    valid_types = ("finished_unit", "finished_good")
    if item_type is not None and item_type not in valid_types:
        raise ValueError(f"Invalid item_type: {item_type}. Must be one of: {valid_types}")

    results = []

    # Query FinishedUnits with low stock
    if item_type is None or item_type == "finished_unit":
        units = (
            session.query(FinishedUnit)
            .filter(FinishedUnit.inventory_count < threshold)
            .order_by(FinishedUnit.inventory_count.asc())
            .all()
        )
        for unit in units:
            current_cost = unit.calculate_current_cost()
            results.append({
                "item_type": "finished_unit",
                "id": unit.id,
                "slug": unit.slug,
                "display_name": unit.display_name,
                "inventory_count": unit.inventory_count,
                "current_cost": current_cost,
                "total_value": unit.inventory_count * current_cost,
            })

    # Query FinishedGoods with low stock
    if item_type is None or item_type == "finished_good":
        goods = (
            session.query(FinishedGood)
            .filter(FinishedGood.inventory_count < threshold)
            .order_by(FinishedGood.inventory_count.asc())
            .all()
        )
        for good in goods:
            current_cost = good.calculate_current_cost()
            results.append({
                "item_type": "finished_good",
                "id": good.id,
                "slug": good.slug,
                "display_name": good.display_name,
                "inventory_count": good.inventory_count,
                "current_cost": current_cost,
                "total_value": good.inventory_count * current_cost,
            })

    # Sort combined results by inventory_count ascending
    results.sort(key=lambda x: x["inventory_count"])

    return results


def get_total_inventory_value(session=None) -> dict:
    """
    Calculate the total value of all finished goods inventory.

    Transaction boundary: Read-only operation.
    Creates own session if none provided; uses caller's session if passed.

    Args:
        session: Optional SQLAlchemy session for transactional composition.

    Returns:
        Dict with keys:
        - finished_units_value: Decimal total value of FinishedUnits
        - finished_goods_value: Decimal total value of FinishedGoods
        - total_value: Decimal sum of both
        - finished_units_count: int number of distinct FinishedUnit items
        - finished_goods_count: int number of distinct FinishedGood items
        - total_items_count: int total distinct items
    """
    if session is not None:
        return _get_total_inventory_value_impl(session)
    with session_scope() as session:
        return _get_total_inventory_value_impl(session)


def _get_total_inventory_value_impl(session) -> dict:
    """Implementation for get_total_inventory_value.

    Transaction boundary: Inherits session from caller.
    Read-only operation.
    """
    # Initialize accumulators
    finished_units_value = Decimal("0.0000")
    finished_goods_value = Decimal("0.0000")
    finished_units_count = 0
    finished_goods_count = 0

    # Query all FinishedUnits
    units = session.query(FinishedUnit).all()
    for unit in units:
        finished_units_count += 1
        current_cost = unit.calculate_current_cost()
        finished_units_value += unit.inventory_count * current_cost

    # Query all FinishedGoods
    goods = session.query(FinishedGood).all()
    for good in goods:
        finished_goods_count += 1
        current_cost = good.calculate_current_cost()
        finished_goods_value += good.inventory_count * current_cost

    return {
        "finished_units_value": finished_units_value,
        "finished_goods_value": finished_goods_value,
        "total_value": finished_units_value + finished_goods_value,
        "finished_units_count": finished_units_count,
        "finished_goods_count": finished_goods_count,
        "total_items_count": finished_units_count + finished_goods_count,
    }


# =============================================================================
# Validation Functions
# =============================================================================


def check_availability(
    item_type: str,
    item_id: int,
    quantity: int,
    session=None,
) -> dict:
    """
    Check if a quantity is available for consumption.

    Transaction boundary: Read-only operation.
    Creates own session if none provided; uses caller's session if passed.

    Does not modify any data - use for availability checks before operations.

    Args:
        item_type: "finished_unit" or "finished_good"
        item_id: ID of the item to check
        quantity: Quantity to check availability for (must be positive)
        session: Optional SQLAlchemy session for transactional composition.

    Returns:
        Dict with keys:
        - available: bool - True if quantity is available
        - item_type: str
        - item_id: int
        - requested: int - the quantity requested
        - current_count: int - current inventory count
        - shortage: int - (only if available=False) amount short

    Raises:
        ValueError: If item_type is invalid, item not found, or quantity <= 0.
    """
    if session is not None:
        return _check_availability_impl(item_type, item_id, quantity, session)
    with session_scope() as session:
        return _check_availability_impl(item_type, item_id, quantity, session)


def _check_availability_impl(
    item_type: str,
    item_id: int,
    quantity: int,
    session,
) -> dict:
    """Implementation for check_availability.

    Transaction boundary: Inherits session from caller.
    Read-only operation.
    """
    # Validate item_type
    valid_types = ("finished_unit", "finished_good")
    if item_type not in valid_types:
        raise ValueError(f"Invalid item_type: {item_type}. Must be one of: {valid_types}")

    # Validate quantity
    if quantity <= 0:
        raise ValueError("Quantity must be positive")

    # Get the item
    if item_type == "finished_unit":
        item = session.query(FinishedUnit).filter_by(id=item_id).first()
    else:  # finished_good
        item = session.query(FinishedGood).filter_by(id=item_id).first()

    if not item:
        raise ValueError(f"Item not found: {item_type}/{item_id}")

    current_count = item.inventory_count

    # Check availability
    if current_count >= quantity:
        return {
            "available": True,
            "item_type": item_type,
            "item_id": item_id,
            "requested": quantity,
            "current_count": current_count,
        }
    else:
        return {
            "available": False,
            "item_type": item_type,
            "item_id": item_id,
            "requested": quantity,
            "current_count": current_count,
            "shortage": quantity - current_count,
        }


def validate_consumption(
    item_type: str,
    item_id: int,
    quantity: int,
    session=None,
) -> dict:
    """
    Validate a consumption request without modifying inventory.

    Transaction boundary: Read-only operation.
    Creates own session if none provided; uses caller's session if passed.

    Use for pre-flight validation in UI before actual consumption.

    Args:
        item_type: "finished_unit" or "finished_good"
        item_id: ID of the item
        quantity: Quantity to consume (must be positive)
        session: Optional SQLAlchemy session for transactional composition.

    Returns:
        Dict with keys:
        - valid: bool - True if consumption would succeed
        - item_type: str
        - item_id: int
        - quantity: int
        - current_count: int
        - remaining_after: int (only if valid=True)
        - error: str (only if valid=False)
        - shortage: int (only if valid=False)

    Raises:
        ValueError: If item_type is invalid or item not found.
    """
    if session is not None:
        return _validate_consumption_impl(item_type, item_id, quantity, session)
    with session_scope() as session:
        return _validate_consumption_impl(item_type, item_id, quantity, session)


def _validate_consumption_impl(
    item_type: str,
    item_id: int,
    quantity: int,
    session,
) -> dict:
    """Implementation for validate_consumption.

    Transaction boundary: Inherits session from caller.
    Read-only operation.
    """
    # Validate item_type
    valid_types = ("finished_unit", "finished_good")
    if item_type not in valid_types:
        raise ValueError(f"Invalid item_type: {item_type}. Must be one of: {valid_types}")

    # Get the item
    if item_type == "finished_unit":
        item = session.query(FinishedUnit).filter_by(id=item_id).first()
    else:  # finished_good
        item = session.query(FinishedGood).filter_by(id=item_id).first()

    if not item:
        raise ValueError(f"Item not found: {item_type}/{item_id}")

    current_count = item.inventory_count

    # Validate quantity is positive
    if quantity <= 0:
        return {
            "valid": False,
            "item_type": item_type,
            "item_id": item_id,
            "quantity": quantity,
            "current_count": current_count,
            "error": "Quantity must be positive",
            "shortage": 0,
        }

    # Check if sufficient inventory
    if current_count >= quantity:
        return {
            "valid": True,
            "item_type": item_type,
            "item_id": item_id,
            "quantity": quantity,
            "current_count": current_count,
            "remaining_after": current_count - quantity,
        }
    else:
        return {
            "valid": False,
            "item_type": item_type,
            "item_id": item_id,
            "quantity": quantity,
            "current_count": current_count,
            "error": f"Insufficient inventory: need {quantity}, have {current_count}",
            "shortage": quantity - current_count,
        }


# =============================================================================
# Mutation Function
# =============================================================================


def adjust_inventory(
    item_type: str,
    item_id: int,
    quantity: int,
    reason: str,
    notes: Optional[str] = None,
    session=None,
) -> dict:
    """
    Adjust inventory and create an audit trail record.

    Transaction boundary: Multi-step operation (atomic).
    Creates own session if none provided; uses caller's session if passed.
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
        1. Validate item_type and reason
        2. Fetch the item (FinishedUnit or FinishedGood)
        3. Validate new_count would be non-negative
        4. Update item.inventory_count
        5. Create FinishedGoodsAdjustment audit record
        6. Flush to database

    This is the core mutation function - all inventory changes should flow
    through this function to maintain the audit trail.

    Args:
        item_type: "finished_unit" or "finished_good"
        item_id: ID of the item to adjust
        quantity: Change amount (positive to add, negative to consume)
        reason: Reason for adjustment (must be in FINISHED_GOODS_ADJUSTMENT_REASONS)
        notes: Optional context for the adjustment. Required when reason is "adjustment".
        session: Optional SQLAlchemy session for transactional composition.

    Returns:
        Dict with keys:
        - success: bool (always True if no exception)
        - item_type: str
        - item_id: int
        - previous_count: int
        - new_count: int
        - quantity_change: int
        - reason: str
        - adjustment_id: int (ID of the created FinishedGoodsAdjustment record)

    Raises:
        ValueError: If:
            - item_type is invalid
            - item not found
            - reason not in FINISHED_GOODS_ADJUSTMENT_REASONS
            - reason is "adjustment" but notes not provided
            - adjustment would result in negative inventory
    """
    if session is not None:
        return _adjust_inventory_impl(item_type, item_id, quantity, reason, notes, session)
    with session_scope() as session:
        return _adjust_inventory_impl(item_type, item_id, quantity, reason, notes, session)


def _adjust_inventory_impl(
    item_type: str,
    item_id: int,
    quantity: int,
    reason: str,
    notes: Optional[str],
    session,
) -> dict:
    """Implementation for adjust_inventory.

    Transaction boundary: Inherits session from caller.
    Multi-step operation within caller's transaction:
        1. Validate inputs
        2. Fetch item
        3. Update inventory_count
        4. Create audit record
        5. Flush
    """
    # Validate item_type
    valid_types = ("finished_unit", "finished_good")
    if item_type not in valid_types:
        raise ValueError(f"Invalid item_type: {item_type}. Must be one of: {valid_types}")

    # Validate reason
    if reason not in FINISHED_GOODS_ADJUSTMENT_REASONS:
        raise ValueError(
            f"Invalid reason: {reason}. Must be one of: {FINISHED_GOODS_ADJUSTMENT_REASONS}"
        )

    # Validate notes for "adjustment" reason
    if reason == "adjustment" and not notes:
        raise ValueError("Notes are required when reason is 'adjustment'")

    # Get the item
    if item_type == "finished_unit":
        item = session.query(FinishedUnit).filter_by(id=item_id).first()
    else:  # finished_good
        item = session.query(FinishedGood).filter_by(id=item_id).first()

    if not item:
        raise ValueError(f"Item not found: {item_type}/{item_id}")

    # Calculate and validate new count BEFORE modification
    previous_count = item.inventory_count
    new_count = previous_count + quantity

    if new_count < 0:
        raise ValueError(
            f"Adjustment would result in negative inventory: "
            f"{previous_count} + {quantity} = {new_count}"
        )

    # Update inventory
    item.inventory_count = new_count

    # Create audit record in SAME session
    adjustment = FinishedGoodsAdjustment(
        finished_unit_id=item_id if item_type == "finished_unit" else None,
        finished_good_id=item_id if item_type == "finished_good" else None,
        quantity_change=quantity,
        previous_count=previous_count,
        new_count=new_count,
        reason=reason,
        notes=notes,
    )
    session.add(adjustment)
    session.flush()  # Get the ID

    return {
        "success": True,
        "item_type": item_type,
        "item_id": item_id,
        "previous_count": previous_count,
        "new_count": new_count,
        "quantity_change": quantity,
        "reason": reason,
        "adjustment_id": adjustment.id,
    }
