"""Inventory Item Service - Inventory management with FIFO consumption.

This module provides business logic for managing inventory items including
lot tracking, FIFO (First In, First Out) consumption, expiration monitoring,
and value calculation.

All functions are stateless and use session_scope() for transaction management.

Key Features:
- Lot-based inventory tracking (purchase date, expiration, location)
- **FIFO consumption algorithm** - oldest lots consumed first
- Unit conversion during consumption
- Expiration date monitoring
- Location-based filtering
- Inventory value calculation (when cost data available)

Example Usage:
      >>> from src.services.inventory_item_service import add_to_inventory, consume_fifo
      >>> from decimal import Decimal
      >>> from datetime import date
      >>>
      >>> # Add inventory
      >>> item = add_to_inventory(
      ...     product_id=123,
      ...     quantity=Decimal("25.0"),
      ...     purchase_date=date(2025, 1, 1),
      ...     location="Main Storage"
      ... )
      >>>
      >>> # Consume using FIFO
      >>> result = consume_fifo("all_purpose_flour", Decimal("10.0"))
      >>> result["satisfied"]  # True if enough inventory
      >>> result["shortfall"]  # 0.0 if satisfied, otherwise amount short
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import date, timedelta

from ..models import InventoryItem, Product
from .database import session_scope
from .exceptions import (
    ProductNotFound,
    InventoryItemNotFound,
    ValidationError as ServiceValidationError,
    DatabaseError,
)
from .product_service import get_product
from .ingredient_service import get_ingredient
from sqlalchemy.orm import joinedload


def add_to_inventory(
    product_id: int,
    quantity: Decimal,
    purchase_date: date,
    expiration_date: Optional[date] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
) -> InventoryItem:
    """Add a new inventory item (lot) to inventory.

    This function adds a discrete lot of inventory to the inventory. Each lot
    is tracked separately for FIFO consumption, expiration monitoring, and
    location management.

    Args:
        product_id: ID of product being added
        quantity: Amount being added (must be > 0)
        purchase_date: Date this lot was purchased (for FIFO ordering)
        expiration_date: Optional expiration date (must be >= purchase_date)
        location: Optional storage location (e.g., "Main Storage", "Basement")
        notes: Optional user notes

    Returns:
        InventoryItem: Created inventory item with assigned ID

    Raises:
        ProductNotFound: If product_id doesn't exist
        ValidationError: If quantity <= 0 or expiration_date < purchase_date
        DatabaseError: If database operation fails

    Example:
        >>> from decimal import Decimal
        >>> from datetime import date
        >>> item = add_to_inventory(
        ...     product_id=123,
        ...     quantity=Decimal("25.0"),
        ...     unit="lb",
        ...     purchase_date=date(2025, 1, 15),
        ...     expiration_date=date(2026, 1, 15),
        ...     location="Main Storage"
        ... )
        >>> item.quantity
        Decimal('25.0')
    """
    # Validate product exists
    product = get_product(product_id)

    # Validate quantity > 0
    if quantity <= 0:
        raise ServiceValidationError("Quantity must be positive")

    # Validate dates
    if expiration_date and expiration_date < purchase_date:
        raise ServiceValidationError("Expiration date cannot be before purchase date")

    try:
        with session_scope() as session:
            item = InventoryItem(
                product_id=product_id,
                quantity=float(quantity),  # Model uses Float, convert from Decimal
                purchase_date=purchase_date,
                expiration_date=expiration_date,
                location=location,
                notes=notes,
            )
            session.add(item)
            session.flush()
            return item

    except ProductNotFound:
        raise
    except ServiceValidationError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to add inventory item", original_error=e)


def get_inventory_items(
    ingredient_slug: Optional[str] = None,
    product_id: Optional[int] = None,
    location: Optional[str] = None,
    min_quantity: Optional[Decimal] = None,
) -> List[InventoryItem]:
    """Retrieve inventory items with optional filtering.

    This function supports flexible filtering for inventory queries. Items
    are returned ordered by purchase_date (oldest first) for FIFO visibility.

    Args:
        ingredient_slug: Optional ingredient filter (e.g., "all_purpose_flour")
        product_id: Optional product filter (specific brand/package)
        location: Optional location filter (exact match)
        min_quantity: Optional minimum quantity filter (excludes depleted lots)

    Returns:
        List[InventoryItem]: Matching inventory items, ordered by purchase_date ASC

    Example:
        >>> # Get all flour in main inventory with quantity > 0
        >>> items = get_inventory_items(
        ...     ingredient_slug="all_purpose_flour",
        ...     location="Main Storage",
        ...     min_quantity=Decimal("0.001")
        ... )
        >>> len(items)
        3
        >>> items[0].purchase_date < items[1].purchase_date
        True
    """
    with session_scope() as session:
        q = session.query(InventoryItem).options(
            joinedload(InventoryItem.product).joinedload(Product.ingredient)
        )

        # Join Product if filtering by ingredient_slug
        if ingredient_slug:
            ingredient = get_ingredient(ingredient_slug)
            q = q.join(Product).filter(Product.ingredient_id == ingredient.id)

        # Apply other filters
        if product_id:
            q = q.filter(InventoryItem.product_id == product_id)
        if location:
            q = q.filter(InventoryItem.location == location)
        if min_quantity is not None:
            q = q.filter(InventoryItem.quantity >= float(min_quantity))

        # Order by purchase_date (FIFO order)
        return q.order_by(InventoryItem.purchase_date.asc()).all()


def get_total_quantity(ingredient_slug: str) -> Dict[str, Decimal]:
    """Calculate total quantity for ingredient grouped by unit.

    This function aggregates inventory across all lots, grouping by unit
    since we no longer convert to a single standard unit.

    Args:
        ingredient_slug: Ingredient identifier

    Returns:
        Dict[str, Decimal]: Total quantities by unit (e.g., {"lb": 25.0, "cup": 3.5})

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist

    Example:
        >>> totals = get_total_quantity("all_purpose_flour")
        >>> totals
        {"lb": Decimal('25.0'), "cup": Decimal('3.5')}

        >>> # Empty inventory returns empty dict
        >>> get_total_quantity("new_ingredient")
        {}
    """
    ingredient = get_ingredient(ingredient_slug)  # Validate exists

    # Get all inventory items for this ingredient with quantity > 0
    items = get_inventory_items(ingredient_slug=ingredient_slug, min_quantity=Decimal("0.001"))

    # Group quantities by unit
    unit_totals = {}
    for item in items:
        unit = item.product.purchase_unit
        if unit:
            if unit not in unit_totals:
                unit_totals[unit] = Decimal("0.0")
            unit_totals[unit] += Decimal(str(item.quantity))

    return unit_totals


def consume_fifo(
    ingredient_slug: str,
    quantity_needed: Decimal,
    dry_run: bool = False,
    session=None,
) -> Dict[str, Any]:
    """Consume inventory inventory using FIFO (First In, First Out) logic.

    **CRITICAL FUNCTION**: This implements the core inventory consumption algorithm.

    Algorithm:
        1. Query all lots for ingredient ordered by purchase_date ASC (oldest first)
        2. Iterate through lots, consuming from each until quantity_needed satisfied
        3. Convert between lot units and ingredient recipe_unit as needed
        4. Update lot quantities atomically within single transaction (unless dry_run)
        5. Track consumption breakdown for audit trail
        6. Calculate shortfall if insufficient inventory
        7. Calculate total FIFO cost of consumed inventory

    Args:
        ingredient_slug: Ingredient to consume from
        quantity_needed: Amount to consume in ingredient's recipe_unit
        dry_run: If True, simulate consumption without modifying database.
                 Returns cost data for recipe costing calculations.
                 If False (default), actually consume inventory.
        session: Optional database session. If provided, the caller owns the
                 transaction and this function will NOT commit. If None,
                 this function manages its own transaction via session_scope().

    Returns:
        Dict[str, Any]: Consumption result with keys:
            - "consumed" (Decimal): Amount actually consumed in recipe_unit
            - "breakdown" (List[Dict]): Per-lot consumption details including unit_cost
            - "shortfall" (Decimal): Amount not available (0.0 if satisfied)
            - "satisfied" (bool): True if quantity_needed fully consumed
            - "total_cost" (Decimal): Total FIFO cost of consumed portion

    Raises:
        IngredientNotFoundBySlug: If ingredient_slug doesn't exist
        DatabaseError: If database operation fails

    Note:
        - All updates occur within single transaction (atomic) unless dry_run=True
        - Quantities maintained at 3 decimal precision
        - Unit conversion uses ingredient's unit_converter configuration
        - Empty lots (quantity=0) are kept for audit trail, not deleted
        - When dry_run=True, inventory quantities are NOT modified (read-only)
        - When session is provided, caller is responsible for commit/rollback
    """
    from ..services.unit_converter import convert_any_units

    ingredient = get_ingredient(ingredient_slug)  # Validate exists

    # Calculate density in g/cup if available (using 4-field density model)
    density_g_per_cup = None
    density_g_per_ml = ingredient.get_density_g_per_ml()
    if density_g_per_ml:
        density_g_per_cup = density_g_per_ml * 236.588  # Convert g/ml to g/cup

    def _do_consume(sess):
        """Inner function that performs the actual FIFO consumption logic."""
        # Get all lots ordered by purchase_date ASC (oldest first)
        inventory_items = (
            sess.query(InventoryItem)
            .options(joinedload(InventoryItem.product).joinedload(Product.ingredient))
            .join(Product)
            .filter(
                Product.ingredient_id == ingredient.id,
                InventoryItem.quantity
                >= 0.001,  # Exclude negligible amounts from floating-point errors
            )
            .order_by(InventoryItem.purchase_date.asc())
            .all()
        )

        consumed = Decimal("0.0")
        total_cost = Decimal("0.0")
        breakdown = []
        remaining_needed = quantity_needed

        for item in inventory_items:
            if remaining_needed <= Decimal("0.0"):
                break

            # Convert lot quantity to ingredient recipe_unit
            item_qty_decimal = Decimal(str(item.quantity))
            success, available_float, error = convert_any_units(
                float(item_qty_decimal),
                item.product.purchase_unit,
                ingredient.recipe_unit,
                ingredient=ingredient,
            )
            if not success:
                raise ValueError(f"Unit conversion failed: {error}")
            available = Decimal(str(available_float))

            # Consume up to available amount
            to_consume_in_recipe_unit = min(available, remaining_needed)

            # Convert back to lot's unit for deduction
            success, to_consume_float, error = convert_any_units(
                float(to_consume_in_recipe_unit),
                ingredient.recipe_unit,
                item.product.purchase_unit,
                ingredient=ingredient,
            )
            if not success:
                raise ValueError(f"Unit conversion failed: {error}")
            to_consume_in_lot_unit = Decimal(str(to_consume_float))

            # Get unit cost from the inventory item (if available)
            item_unit_cost = Decimal(str(item.unit_cost)) if item.unit_cost else Decimal("0.0")

            # Calculate cost for this lot's consumption
            lot_cost = to_consume_in_lot_unit * item_unit_cost
            total_cost += lot_cost

            # Update lot quantity only if NOT dry_run
            if not dry_run:
                item.quantity -= float(to_consume_in_lot_unit)

            consumed += to_consume_in_recipe_unit
            remaining_needed -= to_consume_in_recipe_unit

            # Calculate remaining_in_lot (for dry_run, simulate the deduction)
            if dry_run:
                remaining_in_lot = item_qty_decimal - to_consume_in_lot_unit
            else:
                remaining_in_lot = Decimal(str(item.quantity))

            breakdown.append(
                {
                    "inventory_item_id": item.id,
                    "product_id": item.product_id,
                    "lot_date": item.purchase_date,
                    "quantity_consumed": to_consume_in_lot_unit,
                    "unit": item.product.purchase_unit,
                    "remaining_in_lot": remaining_in_lot,
                    "unit_cost": item_unit_cost,
                }
            )

            # Only flush to database if NOT dry_run and we own the session
            if not dry_run:
                sess.flush()  # Persist update within transaction

        # Calculate results
        shortfall = max(Decimal("0.0"), remaining_needed)
        satisfied = shortfall == Decimal("0.0")

        return {
            "consumed": consumed,
            "breakdown": breakdown,
            "shortfall": shortfall,
            "satisfied": satisfied,
            "total_cost": total_cost,
        }

    # Execute with provided session or create new one
    try:
        if session is not None:
            # Caller owns the transaction - don't commit
            return _do_consume(session)
        else:
            # Standalone call - own transaction
            with session_scope() as sess:
                return _do_consume(sess)
    except Exception as e:
        raise DatabaseError(
            f"Failed to consume FIFO for ingredient '{ingredient_slug}'", original_error=e
        )


def get_expiring_soon(days: int = 14) -> List[InventoryItem]:
    """Get inventory items expiring within specified days.

    This function identifies items needing to be used soon to prevent waste.
    Items without expiration dates are excluded.

    Args:
        days: Number of days to look ahead (default: 14)

    Returns:
        List[InventoryItem]: Items expiring within specified days,
                         ordered by expiration_date (soonest first)

    Example:
        >>> # Get items expiring in next 7 days
        >>> expiring = get_expiring_soon(days=7)
        >>> # Items already expired are excluded
        >>> # Items without expiration_date are excluded
    """
    cutoff_date = date.today() + timedelta(days=days)

    with session_scope() as session:
        return (
            session.query(InventoryItem)
            .options(joinedload(InventoryItem.product).joinedload(Product.ingredient))
            .filter(
                InventoryItem.expiration_date.isnot(None),
                InventoryItem.expiration_date <= cutoff_date,
                InventoryItem.quantity > 0,
            )
            .order_by(InventoryItem.expiration_date.asc())
            .all()
        )


def update_inventory_item(inventory_item_id: int, item_data: Dict[str, Any]) -> InventoryItem:
    """Update inventory item attributes.

    Allows updating quantity, expiration_date, location, and notes.
    Immutable fields (product_id, purchase_date) cannot be changed to maintain
    FIFO integrity and audit trail.

    Args:
        inventory_item_id: Inventory item identifier
        item_data: Dictionary with fields to update (partial update supported)

    Returns:
        InventoryItem: Updated inventory item

    Raises:
        InventoryItemNotFound: If inventory_item_id doesn't exist
        ValidationError: If attempting to change product_id or purchase_date
        DatabaseError: If database operation fails

    Note:
        product_id and purchase_date are immutable to maintain FIFO order
        and prevent orphaned references.
    """
    # Prevent changing immutable fields
    if "product_id" in item_data:
        raise ServiceValidationError("Product ID cannot be changed after creation")
    if "purchase_date" in item_data:
        raise ServiceValidationError("Purchase date cannot be changed after creation")

    # Validate quantity if being updated
    if "quantity" in item_data and item_data["quantity"] < 0:
        raise ServiceValidationError("Quantity cannot be negative")

    try:
        with session_scope() as session:
            item = (
                session.query(InventoryItem)
                .options(joinedload(InventoryItem.product).joinedload(Product.ingredient))
                .filter_by(id=inventory_item_id)
                .first()
            )
            if not item:
                raise InventoryItemNotFound(inventory_item_id)

            # Update attributes
            for key, value in item_data.items():
                if hasattr(item, key):
                    # Convert Decimal to float for quantity
                    if key == "quantity" and isinstance(value, Decimal):
                        value = float(value)
                    setattr(item, key, value)

            return item

    except InventoryItemNotFound:
        raise
    except ServiceValidationError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to update inventory item {inventory_item_id}", original_error=e)


def delete_inventory_item(inventory_item_id: int) -> bool:
    """Delete inventory item (lot).

    Deletes a inventory item record. Typically used for cleaning up depleted lots
    or removing erroneous entries.

    Args:
        inventory_item_id: Inventory item identifier

    Returns:
        bool: True if deletion successful

    Raises:
        InventoryItemNotFound: If inventory_item_id doesn't exist
        DatabaseError: If database operation fails

    Note:
        Consider keeping depleted lots (quantity=0) for audit trail rather
        than deleting. Deletion is permanent and cannot be undone.
    """
    try:
        with session_scope() as session:
            item = session.query(InventoryItem).filter_by(id=inventory_item_id).first()
            if not item:
                raise InventoryItemNotFound(inventory_item_id)

            session.delete(item)
            return True

    except InventoryItemNotFound:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete inventory item {inventory_item_id}", original_error=e)


def get_inventory_value() -> Decimal:
    """Calculate total value of all inventory inventory.

    Calculates total monetary value of inventory by multiplying quantities by
    unit costs from purchase history.

    Returns:
        Decimal: Total inventory value (0.0 if cost tracking not implemented)

    Note:
        This function requires cost tracking integration with Purchase model.
        Returns 0.0 as placeholder until purchase_service.py implements
        cost history tracking.

    Future Implementation:
        - Join InventoryItem with Purchase via product_id
        - Get most recent unit_cost for each product
        - Calculate: SUM(inventory_item.quantity * latest_purchase.unit_cost)
        - Handle unit conversions if inventory unit != purchase unit
    """
    # TODO: Implement when Purchase model and purchase_service.py are ready
    # Future logic:
    # 1. Query all InventoryItem with quantity > 0
    # 2. Join with Purchase to get latest unit_cost per product
    # 3. Convert quantities to purchase unit if needed
    # 4. Calculate: SUM(quantity * unit_cost)
    return Decimal("0.0")
