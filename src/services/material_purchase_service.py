"""Material Purchase Service - Purchase recording and FIFO inventory management.

This module provides business logic for recording material purchases and creating
MaterialInventoryItem records for FIFO costing. Part of Feature 047 (Materials Management)
and Feature 058 (Materials FIFO Foundation).

Key Features:
- Purchase recording with automatic MaterialInventoryItem creation (FIFO)
- Unit conversion from package units to metric base units (cm, sq cm)
- Inventory adjustments (by count or percentage) - DEPRECATED for FIFO
- Atomicity: Purchase and inventory item created in same transaction

All functions accept optional session parameter per CLAUDE.md session management rules.
"""

from typing import Optional
from decimal import Decimal
from datetime import date

from sqlalchemy.orm import Session

from ..models import MaterialProduct, MaterialPurchase, MaterialInventoryItem, Supplier
from .database import session_scope
from .exceptions import ValidationError
from . import material_unit_converter


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
# Unit Conversion (delegated to material_unit_converter)
# =============================================================================


def convert_to_base_units(
    quantity: float,
    from_unit: str,
    base_unit_type: str,
) -> float:
    """Convert quantity from package unit to metric base units.

    This is a wrapper around material_unit_converter.convert_to_base_units()
    that maintains backward compatibility with float quantities.

    Args:
        quantity: Quantity in package units
        from_unit: Package unit (e.g., 'feet', 'yards', 'each')
        base_unit_type: Target base unit type ('each', 'linear_cm', 'square_cm')

    Returns:
        Converted quantity in base units (float)

    Raises:
        ValidationError: If unit conversion is not recognized or incompatible

    Examples:
        >>> convert_to_base_units(100, 'feet', 'linear_cm')
        3048.0  # 100 feet = 3048 cm
        >>> convert_to_base_units(50, 'yards', 'linear_cm')
        4572.0  # 50 yards = 4572 cm
        >>> convert_to_base_units(10, 'each', 'each')
        10.0
    """
    success, result, error = material_unit_converter.convert_to_base_units(
        Decimal(str(quantity)),
        from_unit,
        base_unit_type,
    )
    if not success:
        raise ValidationError([error])
    return float(result)


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


def _create_inventory_item_on_purchase(
    purchase: MaterialPurchase,
    product: MaterialProduct,
    units_added: float,
    unit_cost: Decimal,
    session: Session,
) -> MaterialInventoryItem:
    """Create a MaterialInventoryItem for FIFO tracking on purchase.

    This creates a new inventory lot record for the purchase. Each purchase
    creates exactly one MaterialInventoryItem (1:1 relationship).

    Args:
        purchase: The MaterialPurchase record (must already be flushed with ID)
        product: MaterialProduct being purchased
        units_added: Number of base units added (in metric: cm, sq cm, or count)
        unit_cost: Cost per base unit
        session: Active database session

    Returns:
        Created MaterialInventoryItem

    Note:
        The purchase must be flushed before calling this function so that
        purchase.id is available for the foreign key.
    """
    inventory_item = MaterialInventoryItem(
        material_product_id=product.id,
        material_purchase_id=purchase.id,
        quantity_purchased=units_added,
        quantity_remaining=units_added,
        cost_per_unit=unit_cost,
        purchase_date=purchase.purchase_date,
        location=None,  # Can be set later via update
        notes=purchase.notes,
    )
    session.add(inventory_item)
    session.flush()
    return inventory_item


# DEPRECATED: Feature 058 removed weighted average tracking on MaterialProduct.
# Kept for backward compatibility but no longer used by record_purchase().
def _update_inventory_on_purchase(
    product: MaterialProduct,
    units_added: float,
    unit_cost: Decimal,
    session: Session,
) -> None:
    """DEPRECATED: Update product inventory and weighted average cost.

    This function is deprecated as of Feature 058. MaterialProduct no longer
    tracks current_inventory or weighted_avg_cost. Inventory is now tracked
    via MaterialInventoryItem records using FIFO costing.

    This function is kept for backward compatibility with tests but will
    raise an error if called on a product without inventory fields.
    """
    # Feature 058: MaterialProduct no longer has current_inventory or weighted_avg_cost
    # This function is deprecated and should not be called
    raise NotImplementedError(
        "DEPRECATED: Feature 058 moved inventory tracking to MaterialInventoryItem. "
        "Use _create_inventory_item_on_purchase() instead."
    )


def _record_purchase_impl(
    product_id: int,
    supplier_id: int,
    purchase_date: date,
    packages_purchased: int,
    package_price: Decimal,
    notes: Optional[str],
    session: Session,
) -> MaterialPurchase:
    """Implementation for record_purchase.

    Feature 058: Now creates MaterialInventoryItem for FIFO tracking instead
    of updating weighted average on MaterialProduct.
    """
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

    # Get the base unit type from the material
    material = product.material
    if not material:
        raise ValidationError([f"Product {product_id} has no associated material"])

    base_unit_type = material.base_unit_type

    # Calculate units added with conversion to metric base units
    # product.quantity_in_base_units is stored in the product's package_unit
    # We need to convert to the material's base unit type (cm, sq cm, or each)
    package_qty_in_source_units = packages_purchased * product.package_quantity

    # Convert from package_unit to base units (cm for linear, sq cm for area, count for each)
    # Validate unit compatibility first
    is_valid, error = material_unit_converter.validate_unit_compatibility(
        product.package_unit, base_unit_type
    )
    if not is_valid:
        raise ValidationError([error])

    # Convert to base units
    units_added = convert_to_base_units(
        package_qty_in_source_units,
        product.package_unit,
        base_unit_type,
    )

    # Calculate unit cost (cost per base unit)
    # Total cost for all packages / total base units
    total_cost = package_price * packages_purchased
    if units_added > 0:
        unit_cost = total_cost / Decimal(str(units_added))
    else:
        unit_cost = Decimal("0")

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
    session.flush()  # Get purchase.id for the inventory item FK

    # Feature 058: Create MaterialInventoryItem for FIFO tracking (atomically)
    _create_inventory_item_on_purchase(
        purchase=purchase,
        product=product,
        units_added=units_added,
        unit_cost=unit_cost,
        session=session,
    )

    return purchase


def _adjust_inventory_impl(
    product_id: int,
    new_quantity: Optional[float],
    percentage: Optional[float],
    notes: Optional[str],
    session: Session,
) -> MaterialProduct:
    """DEPRECATED: Implementation for adjust_inventory.

    Feature 058: MaterialProduct no longer tracks current_inventory.
    This function now raises NotImplementedError.

    For FIFO-based adjustments, use MaterialInventoryItem operations directly
    or implement a new adjustment service that works with inventory items.
    """
    raise NotImplementedError(
        "DEPRECATED: Feature 058 moved inventory tracking to MaterialInventoryItem. "
        "Direct inventory adjustments on MaterialProduct are no longer supported. "
        "Use MaterialInventoryItem operations for FIFO-based inventory management."
    )


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
    """Implementation for get_product_inventory.

    Feature 058: Now aggregates inventory from MaterialInventoryItem records
    using FIFO pattern instead of reading from MaterialProduct fields.
    """
    product = session.query(MaterialProduct).filter_by(id=product_id).first()
    if not product:
        raise MaterialProductNotFoundError(product_id)

    # Aggregate inventory from all non-depleted inventory items (FIFO)
    inventory_items = (
        session.query(MaterialInventoryItem)
        .filter(MaterialInventoryItem.material_product_id == product_id)
        .filter(MaterialInventoryItem.quantity_remaining > 0.001)  # Non-depleted
        .all()
    )

    # Calculate totals from inventory items
    total_quantity = sum(item.quantity_remaining for item in inventory_items)
    total_value = sum(
        (Decimal(str(item.quantity_remaining)) * item.cost_per_unit for item in inventory_items),
        Decimal("0"),  # Start with Decimal(0) to ensure result is Decimal
    )

    # Calculate weighted average cost from FIFO items
    if total_quantity > 0:
        weighted_avg_cost = total_value / Decimal(str(total_quantity))
    else:
        weighted_avg_cost = Decimal("0")

    return {
        "product_id": product.id,
        "product_name": product.display_name,
        "current_inventory": total_quantity,
        "weighted_avg_cost": weighted_avg_cost.quantize(Decimal("0.0001")),
        "inventory_value": total_value.quantize(Decimal("0.01")),
        "package_unit": product.package_unit,
        "base_unit_type": product.material.base_unit_type if product.material else None,
        "inventory_lots": len(inventory_items),  # New: number of FIFO lots
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
            product_id,
            supplier_id,
            purchase_date,
            packages_purchased,
            package_price,
            notes,
            session,
        )
    with session_scope() as sess:
        return _record_purchase_impl(
            product_id, supplier_id, purchase_date, packages_purchased, package_price, notes, sess
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
        return _adjust_inventory_impl(product_id, new_quantity, percentage, notes, session)
    with session_scope() as sess:
        return _adjust_inventory_impl(product_id, new_quantity, percentage, notes, sess)


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
        return _list_purchases_impl(product_id, supplier_id, start_date, end_date, limit, session)
    with session_scope() as sess:
        return _list_purchases_impl(product_id, supplier_id, start_date, end_date, limit, sess)


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
