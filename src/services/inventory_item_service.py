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

from sqlalchemy.orm import Session, joinedload

from ..models import InventoryItem, Product, Purchase, Supplier
from .database import session_scope
from .exceptions import (
    ProductNotFound,
    InventoryItemNotFound,
    ValidationError as ServiceValidationError,
    DatabaseError,
)
from .product_service import get_product
from .ingredient_service import get_ingredient


def add_to_inventory(
    product_id: int,
    quantity: Decimal,
    supplier_id: int,
    unit_price: Decimal,
    purchase_date: Optional[date] = None,
    expiration_date: Optional[date] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> InventoryItem:
    """Add a new inventory item (lot) to inventory with linked Purchase record.

    This function creates an atomic transaction that:
    1. Creates a Purchase record linking product, supplier, price, and date
    2. Creates an InventoryItem with purchase_id set to the new Purchase
    3. Sets InventoryItem.unit_cost from the purchase unit_price for FIFO costing

    Feature 028: Purchase Tracking & Enhanced Costing

    Args:
        product_id: ID of product being added
        quantity: Amount being added (must be > 0)
        supplier_id: ID of supplier where purchased (required)
        unit_price: Price per unit at time of purchase (required, >= 0)
        purchase_date: Date this lot was purchased (defaults to today)
        expiration_date: Optional expiration date (must be >= purchase_date)
        location: Optional storage location (e.g., "Main Storage", "Basement")
        notes: Optional user notes (stored on InventoryItem, not Purchase)
        session: Optional database session for transaction composability

    Returns:
        InventoryItem: Created inventory item with assigned ID and purchase linkage

    Raises:
        ProductNotFound: If product_id doesn't exist
        ValidationError: If supplier_id invalid, quantity <= 0, unit_price < 0,
                        or expiration_date < purchase_date
        DatabaseError: If database operation fails

    Example:
        >>> from decimal import Decimal
        >>> from datetime import date
        >>> item = add_to_inventory(
        ...     product_id=123,
        ...     quantity=Decimal("25.0"),
        ...     supplier_id=1,
        ...     unit_price=Decimal("8.99"),
        ...     purchase_date=date(2025, 1, 15),
        ...     expiration_date=date(2026, 1, 15),
        ...     location="Main Storage"
        ... )
        >>> item.purchase_id is not None
        True
    """
    # Default purchase_date to today (FR-013)
    actual_purchase_date = purchase_date or date.today()

    # Validate quantity > 0
    if quantity <= 0:
        raise ServiceValidationError(["Quantity must be positive"])

    # Validate unit_price >= 0 (FR-008: negative prices rejected)
    if unit_price < 0:
        raise ServiceValidationError(["Unit price cannot be negative"])

    # Validate dates
    if expiration_date and expiration_date < actual_purchase_date:
        raise ServiceValidationError(["Expiration date cannot be before purchase date"])

    def _add_to_inventory_impl(sess: Session) -> InventoryItem:
        """Implementation with provided session."""
        # Validate product exists
        product = sess.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ProductNotFound(product_id)

        # Validate supplier exists
        supplier = sess.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise ServiceValidationError([f"Supplier with id {supplier_id} not found"])

        # Create Purchase record FIRST (same session for atomicity)
        purchase = Purchase(
            product_id=product_id,
            supplier_id=supplier_id,
            purchase_date=actual_purchase_date,
            unit_price=unit_price,
            quantity_purchased=int(quantity),  # Purchase tracks package units
            notes=None,  # Notes stored on InventoryItem per FR-014
        )
        sess.add(purchase)
        sess.flush()  # Get purchase.id

        # Create InventoryItem with purchase linkage
        item = InventoryItem(
            product_id=product_id,
            quantity=float(quantity),  # Model uses Float
            unit_cost=float(unit_price),  # For FIFO costing
            purchase_id=purchase.id,  # Link to Purchase (FR-001)
            purchase_date=actual_purchase_date,
            expiration_date=expiration_date,
            location=location,
            notes=notes,  # User notes here (FR-014)
        )
        sess.add(item)
        sess.flush()
        return item

    try:
        # Use provided session or create new one (session=None pattern per CLAUDE.md)
        if session is not None:
            return _add_to_inventory_impl(session)
        else:
            with session_scope() as sess:
                return _add_to_inventory_impl(sess)

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
        unit = item.product.package_unit
        if unit:
            if unit not in unit_totals:
                unit_totals[unit] = Decimal("0.0")
            unit_totals[unit] += Decimal(str(item.quantity))

    return unit_totals


def consume_fifo(
    ingredient_slug: str,
    quantity_needed: Decimal,
    target_unit: str,
    dry_run: bool = False,
    session=None,
) -> Dict[str, Any]:
    """Consume inventory inventory using FIFO (First In, First Out) logic.

    **CRITICAL FUNCTION**: This implements the core inventory consumption algorithm.

    Algorithm:
        1. Query all lots for ingredient ordered by purchase_date ASC (oldest first)
        2. Iterate through lots, consuming from each until quantity_needed satisfied
        3. Convert between lot units and target_unit as needed
        4. Update lot quantities atomically within single transaction (unless dry_run)
        5. Track consumption breakdown for audit trail
        6. Calculate shortfall if insufficient inventory
        7. Calculate total FIFO cost of consumed inventory

    Args:
        ingredient_slug: Ingredient to consume from
        quantity_needed: Amount to consume in the target_unit
        target_unit: The unit that quantity_needed is expressed in (from recipe)
        dry_run: If True, simulate consumption without modifying database.
                 Returns cost data for recipe costing calculations.
                 If False (default), actually consume inventory.
        session: Optional database session. If provided, the caller owns the
                 transaction and this function will NOT commit. If None,
                 this function manages its own transaction via session_scope().

    Returns:
        Dict[str, Any]: Consumption result with keys:
            - "consumed" (Decimal): Amount actually consumed in target_unit
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
        - Unit conversion uses ingredient's density for cross-type conversions
        - Empty lots (quantity=0) are kept for audit trail, not deleted
        - When dry_run=True, inventory quantities are NOT modified (read-only)
        - When session is provided, caller is responsible for commit/rollback
    """
    from ..services.unit_converter import convert_any_units

    def _do_consume(sess):
        """Inner function that performs the actual FIFO consumption logic."""
        # Validate ingredient exists using the provided session
        ingredient = get_ingredient(ingredient_slug, session=sess)

        # Calculate density in g/cup if available (using 4-field density model)
        density_g_per_cup = None
        density_g_per_ml = ingredient.get_density_g_per_ml()
        if density_g_per_ml:
            density_g_per_cup = density_g_per_ml * 236.588  # Convert g/ml to g/cup

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

            # Convert lot quantity to target_unit
            item_qty_decimal = Decimal(str(item.quantity))
            success, available_float, error = convert_any_units(
                float(item_qty_decimal),
                item.product.package_unit,
                target_unit,
                ingredient=ingredient,
            )
            if not success:
                raise ValueError(f"Unit conversion failed: {error}")
            available = Decimal(str(available_float))

            # Consume up to available amount
            to_consume_in_target_unit = min(available, remaining_needed)

            # Convert back to lot's unit for deduction
            success, to_consume_float, error = convert_any_units(
                float(to_consume_in_target_unit),
                target_unit,
                item.product.package_unit,
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

            consumed += to_consume_in_target_unit
            remaining_needed -= to_consume_in_target_unit

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
                    "unit": item.product.package_unit,
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


# =============================================================================
# Recency Intelligence Methods (Feature 029)
# =============================================================================


def get_recent_products(
    ingredient_id: int,
    days: int = 30,
    min_frequency: int = 3,
    frequency_days: int = 90,
    limit: int = 20,
    session: Optional[Session] = None,
) -> List[int]:
    """
    Get product IDs that are "recent" for an ingredient.

    A product is considered "recent" if it meets EITHER criterion:
    - Temporal: Added within last 'days' days
    - Frequency: Added 'min_frequency' or more times in last 'frequency_days' days

    This hybrid approach captures both "recently purchased" and "regularly
    purchased" patterns.

    Args:
        ingredient_id: The ingredient to query products for
        days: Number of days for temporal recency (default: 30)
        min_frequency: Minimum additions for frequency recency (default: 3)
        frequency_days: Days window for frequency check (default: 90)
        limit: Maximum number of product IDs to return (default: 20)
        session: Optional database session for transaction composability

    Returns:
        List of product IDs sorted by most recent purchase date (newest first)

    Example:
        >>> # Get recent products for All-Purpose Flour
        >>> recent_ids = get_recent_products(ingredient_id=42)
        >>> len(recent_ids)  # At most 20
        5
    """
    if session is not None:
        return _get_recent_products_impl(
            ingredient_id, days, min_frequency, frequency_days, limit, session
        )
    with session_scope() as sess:
        return _get_recent_products_impl(
            ingredient_id, days, min_frequency, frequency_days, limit, sess
        )


def _get_recent_products_impl(
    ingredient_id: int,
    days: int,
    min_frequency: int,
    frequency_days: int,
    limit: int,
    session: Session,
) -> List[int]:
    """Implementation of get_recent_products with provided session."""
    from sqlalchemy import func, and_

    today = date.today()
    temporal_cutoff = today - timedelta(days=days)
    frequency_cutoff = today - timedelta(days=frequency_days)

    # Query 1: Products added within last N days (temporal recency)
    temporal_query = (
        session.query(
            InventoryItem.product_id,
            func.max(InventoryItem.purchase_date).label("last_purchase"),
        )
        .filter(
            and_(
                InventoryItem.product_id.isnot(None),
                InventoryItem.purchase_date >= temporal_cutoff,
            )
        )
        .join(Product, InventoryItem.product_id == Product.id)
        .filter(Product.ingredient_id == ingredient_id)
        .group_by(InventoryItem.product_id)
    )

    # Query 2: Products added 3+ times in last 90 days (frequency recency)
    frequency_query = (
        session.query(
            InventoryItem.product_id,
            func.max(InventoryItem.purchase_date).label("last_purchase"),
        )
        .filter(
            and_(
                InventoryItem.product_id.isnot(None),
                InventoryItem.purchase_date >= frequency_cutoff,
            )
        )
        .join(Product, InventoryItem.product_id == Product.id)
        .filter(Product.ingredient_id == ingredient_id)
        .group_by(InventoryItem.product_id)
        .having(func.count(InventoryItem.id) >= min_frequency)
    )

    # Execute both queries and merge results
    temporal_results = {row.product_id: row.last_purchase for row in temporal_query.all()}
    frequency_results = {row.product_id: row.last_purchase for row in frequency_query.all()}

    # Merge with max date (OR logic - product appears if in EITHER result)
    merged = {}
    for pid, dt in temporal_results.items():
        merged[pid] = dt
    for pid, dt in frequency_results.items():
        if pid in merged:
            # Keep the more recent date
            if dt and (merged[pid] is None or dt > merged[pid]):
                merged[pid] = dt
        else:
            merged[pid] = dt

    # Sort by date descending (most recent first), limit results
    sorted_products = sorted(
        merged.items(),
        key=lambda x: x[1] if x[1] else date.min,
        reverse=True,
    )
    return [pid for pid, _ in sorted_products[:limit]]


def get_recent_ingredients(
    category: str,
    days: int = 30,
    min_frequency: int = 3,
    frequency_days: int = 90,
    limit: int = 20,
    session: Optional[Session] = None,
) -> List[int]:
    """
    Get ingredient IDs that are "recent" for a category.

    A ingredient is considered "recent" if it meets EITHER criterion:
    - Temporal: Added within last 'days' days
    - Frequency: Added 'min_frequency' or more times in last 'frequency_days' days

    Args:
        category: The category to query ingredients for
        days: Number of days for temporal recency (default: 30)
        min_frequency: Minimum additions for frequency recency (default: 3)
        frequency_days: Days window for frequency check (default: 90)
        limit: Maximum number of ingredient IDs to return (default: 20)
        session: Optional database session for transaction composability

    Returns:
        List of ingredient IDs sorted by most recent purchase date (newest first)

    Example:
        >>> # Get recent ingredients for Baking category
        >>> recent_ids = get_recent_ingredients(category="Baking")
        >>> len(recent_ids)  # At most 20
        8
    """
    if session is not None:
        return _get_recent_ingredients_impl(
            category, days, min_frequency, frequency_days, limit, session
        )
    with session_scope() as sess:
        return _get_recent_ingredients_impl(
            category, days, min_frequency, frequency_days, limit, sess
        )


def _get_recent_ingredients_impl(
    category: str,
    days: int,
    min_frequency: int,
    frequency_days: int,
    limit: int,
    session: Session,
) -> List[int]:
    """Implementation of get_recent_ingredients with provided session."""
    from sqlalchemy import func, and_
    from ..models import Ingredient

    today = date.today()
    temporal_cutoff = today - timedelta(days=days)
    frequency_cutoff = today - timedelta(days=frequency_days)

    # Query 1: Ingredients with items added within last N days (temporal recency)
    temporal_query = (
        session.query(
            Product.ingredient_id,
            func.max(InventoryItem.purchase_date).label("last_purchase"),
        )
        .join(InventoryItem, InventoryItem.product_id == Product.id)
        .join(Ingredient, Product.ingredient_id == Ingredient.id)
        .filter(
            and_(
                Ingredient.category == category,
                InventoryItem.purchase_date >= temporal_cutoff,
            )
        )
        .group_by(Product.ingredient_id)
    )

    # Query 2: Ingredients added 3+ times in last 90 days (frequency recency)
    frequency_query = (
        session.query(
            Product.ingredient_id,
            func.max(InventoryItem.purchase_date).label("last_purchase"),
        )
        .join(InventoryItem, InventoryItem.product_id == Product.id)
        .join(Ingredient, Product.ingredient_id == Ingredient.id)
        .filter(
            and_(
                Ingredient.category == category,
                InventoryItem.purchase_date >= frequency_cutoff,
            )
        )
        .group_by(Product.ingredient_id)
        .having(func.count(InventoryItem.id) >= min_frequency)
    )

    # Execute both queries and merge results
    temporal_results = {row.ingredient_id: row.last_purchase for row in temporal_query.all()}
    frequency_results = {row.ingredient_id: row.last_purchase for row in frequency_query.all()}

    # Merge with max date (OR logic)
    merged = {}
    for iid, dt in temporal_results.items():
        merged[iid] = dt
    for iid, dt in frequency_results.items():
        if iid in merged:
            if dt and (merged[iid] is None or dt > merged[iid]):
                merged[iid] = dt
        else:
            merged[iid] = dt

    # Sort by date descending (most recent first), limit results
    sorted_ingredients = sorted(
        merged.items(),
        key=lambda x: x[1] if x[1] else date.min,
        reverse=True,
    )
    return [iid for iid, _ in sorted_ingredients[:limit]]
