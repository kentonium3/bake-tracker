"""Material Inventory Service - FIFO inventory management for materials.

This module provides business logic for managing material inventory including
lot tracking, FIFO (First In, First Out) consumption, and availability checks.

Parallels inventory_item_service.py for food ingredients.
Part of Feature 058: Materials FIFO Foundation.

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
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime

from sqlalchemy.orm import Session, joinedload

from ..models import MaterialInventoryItem, MaterialProduct, Material
from .database import session_scope
from .exceptions import (
    ValidationError as ServiceValidationError,
    DatabaseError,
    MaterialInventoryItemNotFoundError,
)
from .material_unit_converter import (
    convert_to_base_units,
    convert_from_base_units,
    validate_unit_compatibility,
)


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
            .options(joinedload(MaterialInventoryItem.product).joinedload(MaterialProduct.material))
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
        return sum(Decimal(str(lot.quantity_remaining)) for lot in lots)

    if session is not None:
        return _do_sum(session)
    else:
        with session_scope() as sess:
            return _do_sum(sess)


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
        product = (
            sess.query(MaterialProduct)
            .options(joinedload(MaterialProduct.material))
            .filter(MaterialProduct.id == material_product_id)
            .first()
        )

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
            lot_cost_per_unit = (
                Decimal(str(lot.cost_per_unit)) if lot.cost_per_unit else Decimal("0.0")
            )

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

            breakdown.append(
                {
                    "inventory_item_id": lot.id,
                    "quantity_consumed": to_consume,
                    "unit": "base_units",  # Always in base units internally
                    "remaining_in_lot": remaining_in_lot,
                    "unit_cost": lot_cost_per_unit,
                    "purchase_date": lot.purchase_date,
                }
            )

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
                shortfalls.append(
                    {
                        "material_product_id": product_id,
                        "quantity_needed": qty_needed,
                        "quantity_available": result["consumed"],
                        "shortfall": result["shortfall"],
                        "unit": unit,
                    }
                )

        return {
            "can_fulfill": len(shortfalls) == 0,
            "shortfalls": shortfalls,
        }

    if session is not None:
        return _do_validate(session)
    else:
        with session_scope() as sess:
            return _do_validate(sess)


def get_inventory_by_material(
    material_id: int,
    session: Optional[Session] = None,
) -> List[MaterialInventoryItem]:
    """
    Get all inventory items for a material (across all products).

    Args:
        material_id: ID of the Material
        session: Optional database session

    Returns:
        List[MaterialInventoryItem]: Inventory items ordered by purchase_date ASC
    """

    def _do_query(sess: Session) -> List[MaterialInventoryItem]:
        return (
            sess.query(MaterialInventoryItem)
            .options(joinedload(MaterialInventoryItem.product).joinedload(MaterialProduct.material))
            .join(MaterialProduct)
            .filter(
                MaterialProduct.material_id == material_id,
                MaterialInventoryItem.quantity_remaining >= 0.001,
            )
            .order_by(MaterialInventoryItem.purchase_date.asc())
            .all()
        )

    if session is not None:
        return _do_query(session)
    else:
        with session_scope() as sess:
            return _do_query(sess)


def get_total_inventory_value(
    material_product_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> Decimal:
    """
    Calculate total value of material inventory.

    If material_product_id is provided, calculates for that product only.
    Otherwise calculates for all material inventory.

    Args:
        material_product_id: Optional product filter
        session: Optional database session

    Returns:
        Decimal: Total inventory value (sum of quantity_remaining * cost_per_unit)
    """

    def _do_calculate(sess: Session) -> Decimal:
        query = sess.query(MaterialInventoryItem).filter(
            MaterialInventoryItem.quantity_remaining >= 0.001,
        )

        if material_product_id is not None:
            query = query.filter(MaterialInventoryItem.material_product_id == material_product_id)

        items = query.all()

        total_value = Decimal("0.0")
        for item in items:
            qty = Decimal(str(item.quantity_remaining))
            cost = Decimal(str(item.cost_per_unit)) if item.cost_per_unit else Decimal("0.0")
            total_value += qty * cost

        return total_value

    if session is not None:
        return _do_calculate(session)
    else:
        with session_scope() as sess:
            return _do_calculate(sess)


def _inventory_item_to_dict(item: MaterialInventoryItem) -> Dict[str, Any]:
    """Convert a MaterialInventoryItem to a dictionary."""
    return item.to_dict()


def adjust_inventory(
    inventory_item_id: int,
    adjustment_type: str,  # "add", "subtract", "set", "percentage"
    value: Decimal,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Adjust inventory quantity for a MaterialInventoryItem.

    Args:
        inventory_item_id: The MaterialInventoryItem ID to adjust
        adjustment_type: One of "add", "subtract", "set", "percentage"
            - "add": Add value to current quantity
            - "subtract": Subtract value from current quantity
            - "set": Set quantity to exact value
            - "percentage": Set to percentage of CURRENT quantity (0-100)
        value: The adjustment value (units for add/subtract/set, percent for percentage)
        notes: Optional adjustment reason for audit trail
        session: Optional database session

    Returns:
        Dict with updated inventory item data

    Raises:
        MaterialInventoryItemNotFoundError: If item doesn't exist
        ValidationError: If adjustment would result in negative quantity
    """
    if session is not None:
        return _adjust_inventory_impl(inventory_item_id, adjustment_type, value, notes, session)
    with session_scope() as sess:
        return _adjust_inventory_impl(inventory_item_id, adjustment_type, value, notes, sess)


def _adjust_inventory_impl(
    inventory_item_id: int,
    adjustment_type: str,
    value: Decimal,
    notes: Optional[str],
    session: Session,
) -> Dict[str, Any]:
    # Fetch the inventory item
    item = session.query(MaterialInventoryItem).filter_by(id=inventory_item_id).first()
    if not item:
        raise MaterialInventoryItemNotFoundError(inventory_item_id)

    current_qty = Decimal(str(item.quantity_remaining))

    # Calculate new quantity based on adjustment type
    if adjustment_type == "add":
        new_qty = current_qty + value
    elif adjustment_type == "subtract":
        new_qty = current_qty - value
    elif adjustment_type == "set":
        new_qty = value
    elif adjustment_type == "percentage":
        # Percentage is 0-100, representing percentage of CURRENT remaining
        if value < 0 or value > 100:
            raise ServiceValidationError([f"Percentage must be 0-100, got: {value}"])
        new_qty = (current_qty * value) / Decimal("100")
        # Round to reasonable precision (2 decimal places for materials)
        new_qty = new_qty.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        raise ServiceValidationError([f"Invalid adjustment_type: {adjustment_type}"])

    # Validate non-negative
    if new_qty < 0:
        raise ServiceValidationError(
            [
                f"Adjustment would result in negative quantity: {new_qty}. "
                f"Current: {current_qty}, Adjustment: {adjustment_type} {value}"
            ]
        )

    # Update the item
    item.quantity_remaining = float(new_qty)
    if notes:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        adjustment_note = f"[{timestamp}] Adjustment ({adjustment_type}): {notes}"
        if item.notes:
            item.notes = f"{item.notes}\n{adjustment_note}"
        else:
            item.notes = adjustment_note

    session.commit()

    return _inventory_item_to_dict(item)
