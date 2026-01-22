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

    Returns inventory information including current counts, costs, and values
    for FinishedUnits and/or FinishedGoods.

    Args:
        item_type: Filter by type - "finished_unit" or "finished_good".
                   If None, returns both types.
        item_id: Filter to specific item ID. Requires item_type to be set.
        exclude_zero: If True, exclude items with inventory_count == 0.
        session: Optional SQLAlchemy session. If None, creates own session.

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
    """Implementation for get_inventory_status."""
    # TODO: Implement in WP02
    raise NotImplementedError("get_inventory_status will be implemented in WP02")


def get_low_stock_items(
    threshold: Optional[int] = None,
    item_type: Optional[str] = None,
    session=None,
) -> list[dict]:
    """
    Get items with inventory below a threshold.

    Args:
        threshold: Inventory count threshold. Defaults to DEFAULT_LOW_STOCK_THRESHOLD.
        item_type: Filter by type - "finished_unit" or "finished_good".
                   If None, returns both types.
        session: Optional SQLAlchemy session.

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
    """Implementation for get_low_stock_items."""
    # TODO: Implement in WP02
    raise NotImplementedError("get_low_stock_items will be implemented in WP02")


def get_total_inventory_value(session=None) -> dict:
    """
    Calculate the total value of all finished goods inventory.

    Args:
        session: Optional SQLAlchemy session.

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
    """Implementation for get_total_inventory_value."""
    # TODO: Implement in WP02
    raise NotImplementedError("get_total_inventory_value will be implemented in WP02")


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

    Does not modify any data - use for availability checks before operations.

    Args:
        item_type: "finished_unit" or "finished_good"
        item_id: ID of the item to check
        quantity: Quantity to check availability for (must be positive)
        session: Optional SQLAlchemy session.

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
    """Implementation for check_availability."""
    # TODO: Implement in WP03
    raise NotImplementedError("check_availability will be implemented in WP03")


def validate_consumption(
    item_type: str,
    item_id: int,
    quantity: int,
    session=None,
) -> dict:
    """
    Validate a consumption request without modifying inventory.

    Use for pre-flight validation in UI before actual consumption.

    Args:
        item_type: "finished_unit" or "finished_good"
        item_id: ID of the item
        quantity: Quantity to consume (must be positive)
        session: Optional SQLAlchemy session.

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
    """Implementation for validate_consumption."""
    # TODO: Implement in WP03
    raise NotImplementedError("validate_consumption will be implemented in WP03")


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

    This is the core mutation function - all inventory changes should flow
    through this function to maintain the audit trail.

    Args:
        item_type: "finished_unit" or "finished_good"
        item_id: ID of the item to adjust
        quantity: Change amount (positive to add, negative to consume)
        reason: Reason for adjustment (must be in FINISHED_GOODS_ADJUSTMENT_REASONS)
        notes: Optional context for the adjustment. Required when reason is "adjustment".
        session: Optional SQLAlchemy session.

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
    """Implementation for adjust_inventory."""
    # TODO: Implement in WP03
    raise NotImplementedError("adjust_inventory will be implemented in WP03")
