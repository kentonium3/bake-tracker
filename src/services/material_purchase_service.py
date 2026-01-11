"""Material Purchase Service - Purchase recording and inventory management.

This module provides business logic for recording material purchases and managing
inventory with weighted average costing. Part of Feature 047: Materials Management System.

Key Features:
- Purchase recording with automatic inventory updates
- Weighted average cost recalculation
- Inventory adjustments (by count or percentage)
- Unit conversion from package units to base units

All functions accept optional session parameter per CLAUDE.md session management rules.
"""

from typing import Optional
from decimal import Decimal
from datetime import date

from sqlalchemy.orm import Session

from ..models import MaterialProduct, MaterialPurchase, Supplier
from .database import session_scope
from .exceptions import ValidationError


# =============================================================================
# Custom Exceptions
# =============================================================================


class MaterialProductNotFoundError(Exception):
    """Raised when a material product is not found."""

    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Material product not found: {product_id}")


class SupplierNotFoundError(Exception):
    """Raised when a supplier is not found."""

    def __init__(self, supplier_id: int):
        self.supplier_id = supplier_id
        super().__init__(f"Supplier not found: {supplier_id}")


# =============================================================================
# Unit Conversion
# =============================================================================

# Linear unit conversions to inches
LINEAR_UNIT_TO_INCHES = {
    "inches": 1.0,
    "inch": 1.0,
    "in": 1.0,
    "feet": 12.0,
    "foot": 12.0,
    "ft": 12.0,
    "yards": 36.0,
    "yard": 36.0,
    "yd": 36.0,
}

# Area unit conversions to square inches
AREA_UNIT_TO_SQUARE_INCHES = {
    "square_inches": 1.0,
    "sq_in": 1.0,
    "square_feet": 144.0,
    "sq_ft": 144.0,
}


def convert_to_base_units(
    quantity: float,
    from_unit: str,
    base_unit_type: str,
) -> float:
    """Convert quantity from package unit to base units.

    Args:
        quantity: Quantity in package units
        from_unit: Package unit (e.g., 'feet', 'yards', 'each')
        base_unit_type: Target base unit type ('each', 'linear_inches', 'square_inches')

    Returns:
        Converted quantity in base units

    Raises:
        ValidationError: If unit conversion is not recognized

    Examples:
        >>> convert_to_base_units(100, 'feet', 'linear_inches')
        1200.0
        >>> convert_to_base_units(50, 'yards', 'linear_inches')
        1800.0
        >>> convert_to_base_units(10, 'each', 'each')
        10.0
    """
    from_unit_lower = from_unit.lower()

    if base_unit_type == "each":
        # No conversion needed for 'each' type
        return float(quantity)

    elif base_unit_type == "linear_inches":
        if from_unit_lower in LINEAR_UNIT_TO_INCHES:
            return float(quantity) * LINEAR_UNIT_TO_INCHES[from_unit_lower]
        raise ValidationError([
            f"Cannot convert '{from_unit}' to linear_inches. "
            f"Valid units: {', '.join(LINEAR_UNIT_TO_INCHES.keys())}"
        ])

    elif base_unit_type == "square_inches":
        if from_unit_lower in AREA_UNIT_TO_SQUARE_INCHES:
            return float(quantity) * AREA_UNIT_TO_SQUARE_INCHES[from_unit_lower]
        raise ValidationError([
            f"Cannot convert '{from_unit}' to square_inches. "
            f"Valid units: {', '.join(AREA_UNIT_TO_SQUARE_INCHES.keys())}"
        ])

    else:
        raise ValidationError([f"Unknown base_unit_type: {base_unit_type}"])


# =============================================================================
# Weighted Average Calculation
# =============================================================================


def calculate_weighted_average(
    current_quantity: float,
    current_avg_cost: Decimal,
    added_quantity: float,
    added_unit_cost: Decimal,
) -> Decimal:
    """Calculate new weighted average cost after adding inventory.

    Formula: (current_qty * current_avg + added_qty * added_cost) / (current_qty + added_qty)

    Args:
        current_quantity: Current inventory quantity
        current_avg_cost: Current weighted average cost
        added_quantity: Quantity being added
        added_unit_cost: Unit cost of added inventory

    Returns:
        New weighted average cost as Decimal

    Special Cases:
        - If current_quantity == 0: Returns added_unit_cost (first purchase)
        - If added_quantity == 0: Returns current_avg_cost (unchanged)

    Examples:
        >>> calculate_weighted_average(200, Decimal("0.12"), 100, Decimal("0.15"))
        Decimal('0.1300')
        >>> calculate_weighted_average(0, Decimal("0"), 100, Decimal("0.15"))
        Decimal('0.15')
    """
    current_qty = Decimal(str(current_quantity))
    added_qty = Decimal(str(added_quantity))

    # Special case: first purchase (no existing inventory)
    if current_qty == 0:
        return added_unit_cost

    # Special case: no quantity being added
    if added_qty == 0:
        return current_avg_cost

    # Standard weighted average calculation
    total_value = (current_qty * current_avg_cost) + (added_qty * added_unit_cost)
    total_quantity = current_qty + added_qty

    # Return with 4 decimal precision for currency
    return (total_value / total_quantity).quantize(Decimal("0.0001"))


# =============================================================================
# Internal Implementation Functions
# =============================================================================


def _update_inventory_on_purchase(
    product: MaterialProduct,
    units_added: float,
    unit_cost: Decimal,
    session: Session,
) -> None:
    """Update product inventory and weighted average cost atomically.

    This internal function updates the product's current_inventory and
    weighted_avg_cost in a single transaction. Called by record_purchase().

    Args:
        product: MaterialProduct to update
        units_added: Number of base units added
        unit_cost: Cost per base unit
        session: Active database session

    Note:
        This modifies the product object in-place and flushes to ensure
        the changes are part of the calling transaction.
    """
    # Calculate new weighted average
    new_avg_cost = calculate_weighted_average(
        current_quantity=product.current_inventory,
        current_avg_cost=product.weighted_avg_cost,
        added_quantity=units_added,
        added_unit_cost=unit_cost,
    )

    # Update product
    product.current_inventory += units_added
    product.weighted_avg_cost = new_avg_cost

    session.flush()


def _record_purchase_impl(
    product_id: int,
    supplier_id: int,
    purchase_date: date,
    packages_purchased: int,
    package_price: Decimal,
    notes: Optional[str],
    session: Session,
) -> MaterialPurchase:
    """Implementation for record_purchase."""
    # Validate product exists
    product = session.query(MaterialProduct).filter_by(id=product_id).first()
    if not product:
        raise MaterialProductNotFoundError(product_id)

    # Validate supplier exists
    supplier = session.query(Supplier).filter_by(id=supplier_id).first()
    if not supplier:
        raise SupplierNotFoundError(supplier_id)

    # Validate packages_purchased > 0
    if packages_purchased <= 0:
        raise ValidationError(["packages_purchased must be positive"])

    # Validate package_price >= 0
    if package_price < 0:
        raise ValidationError(["package_price cannot be negative"])

    # Calculate units added from packages
    units_added = packages_purchased * product.quantity_in_base_units

    # Calculate unit cost (cost per base unit)
    # unit_cost = package_price / quantity_in_base_units
    if product.quantity_in_base_units > 0:
        unit_cost = package_price / Decimal(str(product.quantity_in_base_units))
    else:
        unit_cost = package_price

    # Create the purchase record
    purchase = MaterialPurchase(
        product_id=product_id,
        supplier_id=supplier_id,
        purchase_date=purchase_date,
        packages_purchased=packages_purchased,
        package_price=package_price,
        units_added=units_added,
        unit_cost=unit_cost,
        notes=notes,
    )
    session.add(purchase)
    session.flush()

    # Update inventory atomically
    _update_inventory_on_purchase(product, units_added, unit_cost, session)

    return purchase


def _adjust_inventory_impl(
    product_id: int,
    new_quantity: Optional[float],
    percentage: Optional[float],
    notes: Optional[str],
    session: Session,
) -> MaterialProduct:
    """Implementation for adjust_inventory."""
    # Validate exactly one parameter provided
    if (new_quantity is None) == (percentage is None):
        raise ValidationError(["Provide exactly one of: new_quantity or percentage"])

    # Get product
    product = session.query(MaterialProduct).filter_by(id=product_id).first()
    if not product:
        raise MaterialProductNotFoundError(product_id)

    # Apply adjustment
    if new_quantity is not None:
        if new_quantity < 0:
            raise ValidationError(["new_quantity cannot be negative"])
        product.current_inventory = new_quantity
    else:
        # percentage adjustment
        if percentage < 0:
            raise ValidationError(["percentage cannot be negative"])
        product.current_inventory = product.current_inventory * percentage

    # Note: weighted_avg_cost is NOT changed on adjustments
    session.flush()

    return product


def _get_purchase_impl(
    purchase_id: int,
    session: Session,
) -> MaterialPurchase:
    """Implementation for get_purchase."""
    purchase = session.query(MaterialPurchase).filter_by(id=purchase_id).first()
    if not purchase:
        raise ValidationError([f"MaterialPurchase not found: {purchase_id}"])
    return purchase


def _list_purchases_impl(
    product_id: Optional[int],
    supplier_id: Optional[int],
    start_date: Optional[date],
    end_date: Optional[date],
    limit: Optional[int],
    session: Session,
) -> list:
    """Implementation for list_purchases."""
    query = session.query(MaterialPurchase)

    if product_id is not None:
        query = query.filter(MaterialPurchase.product_id == product_id)

    if supplier_id is not None:
        query = query.filter(MaterialPurchase.supplier_id == supplier_id)

    if start_date is not None:
        query = query.filter(MaterialPurchase.purchase_date >= start_date)

    if end_date is not None:
        query = query.filter(MaterialPurchase.purchase_date <= end_date)

    # Order by purchase date descending (most recent first)
    query = query.order_by(MaterialPurchase.purchase_date.desc())

    if limit is not None:
        query = query.limit(limit)

    return query.all()


def _get_product_inventory_impl(
    product_id: int,
    session: Session,
) -> dict:
    """Implementation for get_product_inventory."""
    product = session.query(MaterialProduct).filter_by(id=product_id).first()
    if not product:
        raise MaterialProductNotFoundError(product_id)

    return {
        "product_id": product.id,
        "product_name": product.display_name,
        "current_inventory": product.current_inventory,
        "weighted_avg_cost": product.weighted_avg_cost,
        "inventory_value": product.inventory_value,
        "package_unit": product.package_unit,
        "base_unit_type": product.material.base_unit_type if product.material else None,
    }


# =============================================================================
# Public API Functions
# =============================================================================


def record_purchase(
    product_id: int,
    supplier_id: int,
    purchase_date: date,
    packages_purchased: int,
    package_price: Decimal,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> MaterialPurchase:
    """Record a material purchase and update inventory atomically.

    Creates a MaterialPurchase record and updates the product's current_inventory
    and weighted_avg_cost in a single transaction.

    Args:
        product_id: ID of the MaterialProduct being purchased
        supplier_id: ID of the Supplier
        purchase_date: Date of purchase
        packages_purchased: Number of packages bought (must be > 0)
        package_price: Price per package (must be >= 0)
        notes: Optional purchase notes
        session: Optional database session for transaction sharing

    Returns:
        Created MaterialPurchase record

    Raises:
        MaterialProductNotFoundError: If product_id doesn't exist
        SupplierNotFoundError: If supplier_id doesn't exist
        ValidationError: If validation fails

    Example:
        >>> from decimal import Decimal
        >>> from datetime import date
        >>> purchase = record_purchase(
        ...     product_id=1,
        ...     supplier_id=2,
        ...     purchase_date=date.today(),
        ...     packages_purchased=2,
        ...     package_price=Decimal("12.00"),
        ... )
        >>> purchase.units_added  # 2 packages * quantity_in_base_units
        2400.0
    """
    if session is not None:
        return _record_purchase_impl(
            product_id, supplier_id, purchase_date,
            packages_purchased, package_price, notes, session
        )
    with session_scope() as sess:
        return _record_purchase_impl(
            product_id, supplier_id, purchase_date,
            packages_purchased, package_price, notes, sess
        )


def adjust_inventory(
    product_id: int,
    new_quantity: Optional[float] = None,
    percentage: Optional[float] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> MaterialProduct:
    """Adjust product inventory manually.

    Use this for inventory corrections (shrinkage, counting errors, etc.).
    The weighted_avg_cost is NOT changed by adjustments.

    Args:
        product_id: ID of the MaterialProduct
        new_quantity: Set inventory to this absolute value
        percentage: Multiply current inventory by this (0.0 to 1.0 for reduction)
        notes: Optional adjustment notes
        session: Optional database session

    Returns:
        Updated MaterialProduct

    Raises:
        MaterialProductNotFoundError: If product_id doesn't exist
        ValidationError: If neither or both of new_quantity/percentage provided

    Example:
        >>> # Set inventory to 100 units
        >>> adjust_inventory(product_id=1, new_quantity=100)
        >>> # Apply 50% shrinkage
        >>> adjust_inventory(product_id=1, percentage=0.5)
    """
    if session is not None:
        return _adjust_inventory_impl(
            product_id, new_quantity, percentage, notes, session
        )
    with session_scope() as sess:
        return _adjust_inventory_impl(
            product_id, new_quantity, percentage, notes, sess
        )


def get_purchase(
    purchase_id: int,
    session: Optional[Session] = None,
) -> MaterialPurchase:
    """Retrieve a material purchase by ID.

    Args:
        purchase_id: Purchase identifier
        session: Optional database session

    Returns:
        MaterialPurchase record

    Raises:
        ValidationError: If purchase_id doesn't exist
    """
    if session is not None:
        return _get_purchase_impl(purchase_id, session)
    with session_scope() as sess:
        return _get_purchase_impl(purchase_id, sess)


def list_purchases(
    product_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: Optional[int] = None,
    session: Optional[Session] = None,
) -> list:
    """List material purchases with optional filters.

    Args:
        product_id: Filter by product
        supplier_id: Filter by supplier
        start_date: Filter by purchase date >= this
        end_date: Filter by purchase date <= this
        limit: Maximum number of results
        session: Optional database session

    Returns:
        List of MaterialPurchase records, ordered by purchase_date desc
    """
    if session is not None:
        return _list_purchases_impl(
            product_id, supplier_id, start_date, end_date, limit, session
        )
    with session_scope() as sess:
        return _list_purchases_impl(
            product_id, supplier_id, start_date, end_date, limit, sess
        )


def get_product_inventory(
    product_id: int,
    session: Optional[Session] = None,
) -> dict:
    """Get current inventory details for a product.

    Args:
        product_id: Product identifier
        session: Optional database session

    Returns:
        Dict with:
            - product_id: int
            - product_name: str
            - current_inventory: float
            - weighted_avg_cost: Decimal
            - inventory_value: Decimal
            - package_unit: str
            - base_unit_type: str

    Raises:
        MaterialProductNotFoundError: If product doesn't exist
    """
    if session is not None:
        return _get_product_inventory_impl(product_id, session)
    with session_scope() as sess:
        return _get_product_inventory_impl(product_id, sess)
