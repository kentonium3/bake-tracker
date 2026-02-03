"""Purchase Service - Price history tracking and trend analysis.

This module provides business logic for managing purchase records including
price tracking, cost trend analysis, and automated price alert detection.

All functions are stateless and use session_scope() for transaction management.

Key Features:
- Purchase record creation with auto-cost calculation
- Price history tracking per product
- Average price calculation (60-day rolling window)
- Price change detection with configurable alert thresholds
- Linear regression price trend analysis
- Purchase date filtering and sorting

Example Usage:
    >>> from src.services.purchase_service import record_purchase, get_price_trend
    >>> from decimal import Decimal
    >>> from datetime import date
    >>>
    >>> # Record a purchase
    >>> purchase = record_purchase(
    ...     product_id=123,
    ...     quantity=Decimal("25.0"),
    ...     total_cost=Decimal("18.99"),
    ...     purchase_date=date(2025, 1, 15),
    ...     store="Costco"
    ... )
    >>> purchase.unit_cost  # Auto-calculated
    Decimal('0.76')
    >>>
    >>> # Analyze price trend
    >>> trend = get_price_trend(product_id=123, days=90)
    >>> trend["direction"]  # "increasing", "decreasing", or "stable"
    'increasing'
    >>> trend["slope_per_day"]
    Decimal('0.012')
"""

from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from datetime import date, timedelta
from statistics import linear_regression

from sqlalchemy.orm import Session, joinedload

from ..models import Purchase, Product, Supplier
from ..models.inventory_item import InventoryItem
from ..models.inventory_depletion import InventoryDepletion
from .database import session_scope
from .ingredient_service import get_ingredient
from .exceptions import (
    PurchaseNotFound,
    ProductNotFound,
    ValidationError as ServiceValidationError,
    DatabaseError,
)
from .product_service import get_product


# Price change alert thresholds (percentage)
PRICE_ALERT_WARNING = Decimal("0.20")  # 20% change
PRICE_ALERT_CRITICAL = Decimal("0.40")  # 40% change


def record_purchase(
    product_id: int,
    quantity: Decimal,
    total_cost: Decimal,
    purchase_date: date,
    store: Optional[str] = None,
    receipt_number: Optional[str] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> Purchase:
    """Record a new purchase with automatic unit cost calculation and inventory creation.

    Transaction boundary: Multi-step atomic operation.
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
    1. Validate product exists
    2. Find or create Supplier record from store name
    3. Create Purchase record with calculated unit_price
    4. Create linked InventoryItem record for FIFO tracking

    CRITICAL: If session is provided, all operations execute within caller's
    transaction. If session is None, creates own session_scope() for atomicity.
    Never creates nested session_scope() when session is passed.

    Per spec FR-014: System MUST create both Purchase and InventoryItem records
    atomically on save.

    This function creates a purchase record, auto-calculates the unit cost
    by dividing total_cost by quantity, and creates the linked InventoryItem
    records atomically. All monetary values use Decimal for precision.

    Args:
        product_id: ID of product purchased
        quantity: Quantity purchased in packages (must be > 0)
        total_cost: Total amount paid (must be >= 0)
        purchase_date: Date of purchase
        store: Optional store/supplier name
        receipt_number: Optional receipt identifier for tracking
        notes: Optional user notes
        session: Optional database session for transaction sharing

    Returns:
        Purchase: Created purchase record with calculated unit_cost

    Raises:
        ProductNotFound: If product_id doesn't exist
        ValidationError: If quantity <= 0 or total_cost < 0
        DatabaseError: If database operation fails

    Example:
        >>> from decimal import Decimal
        >>> from datetime import date
        >>> purchase = record_purchase(
        ...     product_id=123,
        ...     quantity=Decimal("25.0"),
        ...     total_cost=Decimal("18.99"),
        ...     purchase_date=date(2025, 1, 15),
        ...     store="Costco",
        ...     receipt_number="R-2025-001"
        ... )
        >>> purchase.unit_cost
        Decimal('0.7596')
        >>> purchase.quantity
        Decimal('25.0')
    """
    if session is not None:
        return _record_purchase_impl(
            product_id, quantity, total_cost, purchase_date, store, receipt_number, notes, session
        )
    with session_scope() as sess:
        return _record_purchase_impl(
            product_id, quantity, total_cost, purchase_date, store, receipt_number, notes, sess
        )


def _record_purchase_impl(
    product_id: int,
    quantity: Decimal,
    total_cost: Decimal,
    purchase_date: date,
    store: Optional[str],
    receipt_number: Optional[str],
    notes: Optional[str],
    session: Session,
) -> Purchase:
    """Implementation for record_purchase.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). All operations execute within the
    caller's transaction boundary.
    """
    # Validate product exists - need to query within session
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        raise ProductNotFound(product_id)

    # Validate quantity > 0
    if quantity <= 0:
        raise ServiceValidationError("Quantity must be positive")

    # Validate total_cost >= 0
    if total_cost < 0:
        raise ServiceValidationError("Total cost cannot be negative")

    # Calculate unit price from total cost and quantity (price per package)
    unit_price = total_cost / quantity if quantity > 0 else Decimal("0.0")

    try:
        # Find or create supplier from store name
        store_name = store if store else "Unknown"
        supplier = session.query(Supplier).filter(Supplier.name == store_name).first()
        if not supplier:
            # Create a minimal supplier record with required fields
            supplier = Supplier(
                name=store_name,
                city="Unknown",
                state="XX",
                zip_code="00000",
            )
            session.add(supplier)
            session.flush()
        supplier_id = supplier.id

        # Combine receipt_number into notes if provided
        full_notes = notes
        if receipt_number:
            if full_notes:
                full_notes = f"Receipt: {receipt_number}; {full_notes}"
            else:
                full_notes = f"Receipt: {receipt_number}"

        # Create the Purchase record
        purchase = Purchase(
            product_id=product_id,
            supplier_id=supplier_id,
            purchase_date=purchase_date,
            unit_price=unit_price,
            quantity_purchased=int(quantity),  # Model expects int
            notes=full_notes,
        )

        session.add(purchase)
        session.flush()  # Get purchase ID before creating inventory

        # FR-014: Create InventoryItem record linked to this purchase
        # Calculate inventory quantity and unit cost
        package_unit_qty = Decimal("1")
        if product.package_unit_quantity:
            package_unit_qty = Decimal(str(product.package_unit_quantity))

        # Total units = packages * units per package
        total_units = Decimal(str(int(quantity))) * package_unit_qty

        # Unit cost = price per package / units per package
        unit_cost = (
            float(unit_price / package_unit_qty) if package_unit_qty > 0 else float(unit_price)
        )

        inventory_item = InventoryItem(
            product_id=product_id,
            purchase_id=purchase.id,
            quantity=float(total_units),
            unit_cost=unit_cost,
            purchase_date=purchase_date,
        )

        session.add(inventory_item)
        session.flush()

        return purchase

    except ProductNotFound:
        raise
    except ServiceValidationError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to record purchase", original_error=e)


def get_purchase(
    purchase_id: int,
    session: Optional[Session] = None,
) -> Purchase:
    """Retrieve purchase record by ID with eager-loaded relationships.

    Transaction boundary: Read-only, no transaction needed.
    If session provided, query executes within caller's transaction for
    consistent reads. If session is None, uses session_scope() internally.
    Safe to call standalone - no modifications performed.

    Args:
        purchase_id: Purchase identifier
        session: Optional database session for transaction sharing

    Returns:
        Purchase: Purchase object with product, supplier, and inventory_items
            relationships eager-loaded for use outside session.

    Raises:
        PurchaseNotFound: If purchase_id doesn't exist

    Example:
        >>> purchase = get_purchase(456)
        >>> purchase.product.brand
        'King Arthur'
        >>> purchase.total_cost
        Decimal('18.99')
    """
    if session is not None:
        return _get_purchase_impl(purchase_id, session)
    with session_scope() as sess:
        return _get_purchase_impl(purchase_id, sess)


def _get_purchase_impl(purchase_id: int, session: Session) -> Purchase:
    """Implementation for get_purchase with eager loading.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). All queries execute within the
    caller's transaction boundary for read consistency.
    """
    purchase = (
        session.query(Purchase)
        .options(
            joinedload(Purchase.product),
            joinedload(Purchase.supplier),
            joinedload(Purchase.inventory_items).joinedload(InventoryItem.depletions),
        )
        .filter(Purchase.id == purchase_id)
        .first()
    )

    if not purchase:
        raise PurchaseNotFound(purchase_id)

    # Ensure all attributes are loaded before returning
    # This forces SQLAlchemy to load everything while session is open
    _ = purchase.product.display_name if purchase.product else None
    _ = purchase.supplier.name if purchase.supplier else None
    for item in purchase.inventory_items:
        _ = item.quantity
        for dep in item.depletions:
            _ = dep.quantity_depleted

    return purchase


def get_purchase_history(
    product_id: Optional[int] = None,
    ingredient_slug: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    store: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Purchase]:
    """Retrieve purchase history with flexible filtering.

    Transaction boundary: Read-only, no transaction needed.
    Uses session_scope() internally for isolated query. Safe to call
    standalone - creates temporary session for query execution.
    Calls get_ingredient() which uses its own session for ingredient lookup.

    This function supports filtering by product, ingredient, date range, and store.
    Results are ordered by purchase_date DESC (most recent first).

    Args:
        product_id: Optional filter for specific product
        ingredient_slug: Optional filter for all products of ingredient
        start_date: Optional earliest purchase date (inclusive)
        end_date: Optional latest purchase date (inclusive)
        store: Optional store name filter (exact match)
        limit: Optional maximum number of results

    Returns:
        List[Purchase]: Matching purchase records, ordered by date DESC

    Example:
        >>> from datetime import date
        >>> # Get all flour purchases in January 2025
        >>> purchases = get_purchase_history(
        ...     ingredient_slug="all_purpose_flour",
        ...     start_date=date(2025, 1, 1),
        ...     end_date=date(2025, 1, 31)
        ... )
        >>> len(purchases)
        3
        >>> purchases[0].purchase_date > purchases[1].purchase_date
        True
    """
    with session_scope() as session:
        q = session.query(Purchase)

        # Join Product if filtering by ingredient_slug
        if ingredient_slug:
            ingredient = get_ingredient(ingredient_slug)
            q = q.join(Product).filter(Product.ingredient_id == ingredient.id)

        # Apply other filters
        if product_id:
            q = q.filter(Purchase.product_id == product_id)
        if start_date:
            q = q.filter(Purchase.purchase_date >= start_date)
        if end_date:
            q = q.filter(Purchase.purchase_date <= end_date)
        if store:
            q = q.join(Supplier).filter(Supplier.name == store)

        # Order by date DESC (most recent first)
        q = q.order_by(Purchase.purchase_date.desc())

        # Apply limit
        if limit:
            q = q.limit(limit)

        return q.all()


def get_most_recent_purchase(product_id: int) -> Optional[Purchase]:
    """Get the most recent purchase for a product.

    Transaction boundary: Read-only, no transaction needed.
    Calls get_product() for validation (uses its own session), then
    uses session_scope() internally for the purchase query.
    Safe to call standalone - no modifications performed.

    Args:
        product_id: Product identifier

    Returns:
        Optional[Purchase]: Most recent purchase, or None if no purchases exist

    Raises:
        ProductNotFound: If product_id doesn't exist

    Example:
        >>> recent = get_most_recent_purchase(123)
        >>> recent.purchase_date if recent else "No purchases yet"
        date(2025, 1, 15)

        >>> recent = get_most_recent_purchase(456)  # New product
        >>> recent is None
        True
    """
    # Validate product exists
    get_product(product_id)

    with session_scope() as session:
        return (
            session.query(Purchase)
            .filter_by(product_id=product_id)
            .order_by(Purchase.purchase_date.desc())
            .first()
        )


def calculate_average_price(product_id: int, days: int = 60) -> Optional[Decimal]:
    """Calculate average unit cost over specified time window.

    Transaction boundary: Read-only, no transaction needed.
    Calls get_product() for validation (uses its own session), then
    uses session_scope() internally for aggregation query.
    Safe to call standalone - no modifications performed.

    This function computes the mean unit_cost for all purchases within the
    specified number of days from today. Returns None if no purchases in window.

    Args:
        product_id: Product identifier
        days: Number of days to look back (default: 60)

    Returns:
        Optional[Decimal]: Average unit cost, or None if no purchases in window

    Raises:
        ProductNotFound: If product_id doesn't exist

    Example:
        >>> from decimal import Decimal
        >>> avg = calculate_average_price(product_id=123, days=60)
        >>> avg
        Decimal('0.7234')

        >>> avg = calculate_average_price(product_id=456, days=30)
        >>> avg is None  # No purchases in last 30 days
        True
    """
    # Validate product exists
    get_product(product_id)

    cutoff_date = date.today() - timedelta(days=days)

    with session_scope() as session:
        purchases = (
            session.query(Purchase)
            .filter(Purchase.product_id == product_id, Purchase.purchase_date >= cutoff_date)
            .all()
        )

        if not purchases:
            return None

        # Calculate average
        total = sum(p.unit_cost for p in purchases)
        count = len(purchases)
        return Decimal(str(total)) / Decimal(str(count))


def detect_price_change(
    product_id: int, new_unit_cost: Decimal, comparison_days: int = 60
) -> Dict[str, Any]:
    """Detect significant price changes compared to historical average.

    Transaction boundary: Read-only, no transaction needed.
    Calls calculate_average_price() which performs read-only queries.
    Safe to call standalone - no modifications performed. Each sub-call
    uses its own session for query isolation.

    This function compares a new unit cost against the historical average and
    calculates the percentage change. It categorizes changes using configurable
    thresholds.

    Args:
        product_id: Product identifier
        new_unit_cost: New unit cost to compare
        comparison_days: Days to use for average calculation (default: 60)

    Returns:
        Dict[str, Any]: Price change analysis with keys:
            - "average_price" (Decimal): Historical average (or None)
            - "new_price" (Decimal): The new unit cost
            - "change_amount" (Decimal): Absolute difference (or None)
            - "change_percent" (Decimal): Percentage change (or None)
            - "alert_level" (str): "none", "warning", or "critical"
            - "message" (str): Human-readable summary

    Raises:
        ProductNotFound: If product_id doesn't exist

    Note:
        Alert levels:
        - "none": Change < 20%
        - "warning": Change 20-40%
        - "critical": Change > 40%

    Example:
        >>> from decimal import Decimal
        >>> result = detect_price_change(
        ...     product_id=123,
        ...     new_unit_cost=Decimal("0.95")
        ... )
        >>> result["alert_level"]
        'warning'
        >>> result["change_percent"]
        Decimal('31.5')
        >>> result["message"]
        'Price increased by 31.5% (WARNING)'
    """
    # Get historical average
    avg_price = calculate_average_price(product_id, comparison_days)

    # No historical data
    if avg_price is None:
        return {
            "average_price": None,
            "new_price": new_unit_cost,
            "change_amount": None,
            "change_percent": None,
            "alert_level": "none",
            "message": "No historical data for comparison",
        }

    # Calculate change
    change_amount = new_unit_cost - avg_price
    change_percent = (change_amount / avg_price * 100).quantize(Decimal("0.1"))

    # Determine alert level
    abs_change_percent = abs(change_percent)
    if abs_change_percent >= PRICE_ALERT_CRITICAL * 100:
        alert_level = "critical"
    elif abs_change_percent >= PRICE_ALERT_WARNING * 100:
        alert_level = "warning"
    else:
        alert_level = "none"

    # Generate message
    direction = "increased" if change_amount > 0 else "decreased"
    alert_suffix = ""
    if alert_level == "warning":
        alert_suffix = " (WARNING)"
    elif alert_level == "critical":
        alert_suffix = " (CRITICAL)"

    message = f"Price {direction} by {abs_change_percent}%{alert_suffix}"

    return {
        "average_price": avg_price,
        "new_price": new_unit_cost,
        "change_amount": change_amount,
        "change_percent": change_percent,
        "alert_level": alert_level,
        "message": message,
    }


def get_price_trend(product_id: int, days: int = 90) -> Dict[str, Any]:
    """Analyze price trend using linear regression.

    Transaction boundary: Read-only, no transaction needed.
    Calls get_product() for validation, then uses session_scope() for
    purchase history query. Linear regression is calculated in-memory
    after query completes. Safe to call standalone - no modifications.

    This function performs linear regression on purchase history to identify
    pricing trends over time. It calculates slope (price change per day) and
    categorizes the trend direction.

    Args:
        product_id: Product identifier
        days: Number of days to analyze (default: 90)

    Returns:
        Dict[str, Any]: Trend analysis with keys:
            - "direction" (str): "increasing", "decreasing", or "stable"
            - "slope_per_day" (Decimal): Daily price change rate
            - "data_points" (int): Number of purchases analyzed
            - "oldest_date" (date): Earliest purchase in dataset
            - "newest_date" (date): Most recent purchase in dataset
            - "message" (str): Human-readable summary

    Raises:
        ProductNotFound: If product_id doesn't exist

    Note:
        - Requires at least 2 data points for regression
        - "stable" defined as |slope| < $0.001/day
        - Uses Python's statistics.linear_regression for calculation

    Example:
        >>> trend = get_price_trend(product_id=123, days=90)
        >>> trend["direction"]
        'increasing'
        >>> trend["slope_per_day"]
        Decimal('0.012')
        >>> trend["message"]
        'Price increasing at $0.012 per day over 90 days (5 purchases)'
    """
    # Validate product exists
    get_product(product_id)

    cutoff_date = date.today() - timedelta(days=days)

    with session_scope() as session:
        purchases = (
            session.query(Purchase)
            .filter(Purchase.product_id == product_id, Purchase.purchase_date >= cutoff_date)
            .order_by(Purchase.purchase_date.asc())
            .all()
        )

        # Need at least 2 data points for regression
        if len(purchases) < 2:
            return {
                "direction": "stable",
                "slope_per_day": Decimal("0.0"),
                "data_points": len(purchases),
                "oldest_date": purchases[0].purchase_date if purchases else None,
                "newest_date": purchases[0].purchase_date if purchases else None,
                "message": f"Insufficient data for trend analysis ({len(purchases)} purchase)",
            }

        # Prepare data for linear regression
        # x = days since oldest purchase
        # y = unit cost
        oldest_date = purchases[0].purchase_date
        x_values = [(p.purchase_date - oldest_date).days for p in purchases]
        y_values = [float(p.unit_cost) for p in purchases]

        # Perform linear regression
        slope, intercept = linear_regression(x_values, y_values)
        slope_decimal = Decimal(str(slope)).quantize(Decimal("0.0001"))

        # Determine direction (threshold: $0.001/day)
        if abs(slope_decimal) < Decimal("0.001"):
            direction = "stable"
        elif slope_decimal > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        # Generate message
        message = (
            f"Price {direction} at ${abs(slope_decimal)} per day "
            f"over {days} days ({len(purchases)} purchases)"
        )

        return {
            "direction": direction,
            "slope_per_day": slope_decimal,
            "data_points": len(purchases),
            "oldest_date": oldest_date,
            "newest_date": purchases[-1].purchase_date,
            "message": message,
        }


# =============================================================================
# Price Suggestion Functions (Feature 028)
# =============================================================================


def get_last_price_at_supplier(
    product_id: int,
    supplier_id: int,
    session: Optional[Session] = None,
) -> Optional[Dict[str, Any]]:
    """Get last purchase price for product at specific supplier.

    Transaction boundary: Read-only, no transaction needed.
    If session provided, query executes within caller's transaction for
    consistent reads. If session is None, uses session_scope() internally.
    Safe to call standalone - no modifications performed.

    Returns the most recent purchase record for a product at a specific supplier,
    enabling price suggestion hints in the UI when users select a product/supplier
    combination.

    Args:
        product_id: Product ID to look up
        supplier_id: Supplier ID to filter by
        session: Optional database session for transaction sharing

    Returns:
        Dict with unit_price (Decimal as str), purchase_date (ISO str), supplier_id
        None if no purchase history at this supplier

    Example:
        >>> result = get_last_price_at_supplier(product_id=123, supplier_id=1)
        >>> result
        {"unit_price": "9.99", "purchase_date": "2025-01-15", "supplier_id": 1}

        >>> result = get_last_price_at_supplier(product_id=456, supplier_id=2)
        >>> result is None  # No history at this supplier
        True
    """
    if session is not None:
        return _get_last_price_at_supplier_impl(product_id, supplier_id, session)
    with session_scope() as session:
        return _get_last_price_at_supplier_impl(product_id, supplier_id, session)


def _get_last_price_at_supplier_impl(
    product_id: int,
    supplier_id: int,
    session: Session,
) -> Optional[Dict[str, Any]]:
    """Implementation for get_last_price_at_supplier.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). Query executes within the caller's
    transaction boundary.
    """
    purchase = (
        session.query(Purchase)
        .filter(Purchase.product_id == product_id)
        .filter(Purchase.supplier_id == supplier_id)
        .order_by(Purchase.purchase_date.desc())
        .first()
    )

    if not purchase:
        return None

    return {
        "unit_price": str(purchase.unit_price),
        "purchase_date": purchase.purchase_date.isoformat(),
        "supplier_id": purchase.supplier_id,
    }


def get_last_price_any_supplier(
    product_id: int,
    session: Optional[Session] = None,
) -> Optional[Dict[str, Any]]:
    """Get last purchase price for product at any supplier.

    Transaction boundary: Read-only, no transaction needed.
    If session provided, query executes within caller's transaction for
    consistent reads. If session is None, uses session_scope() internally.
    Safe to call standalone - no modifications performed.

    Returns the most recent purchase record for a product regardless of supplier,
    used as a fallback price suggestion when no history exists at the selected
    supplier.

    Args:
        product_id: Product ID to look up
        session: Optional database session for transaction sharing

    Returns:
        Dict with unit_price (Decimal as str), purchase_date (ISO str),
        supplier_id, and supplier_name (for display in hint)
        None if no purchase history exists

    Example:
        >>> result = get_last_price_any_supplier(product_id=123)
        >>> result
        {"unit_price": "9.99", "purchase_date": "2025-01-15",
         "supplier_id": 1, "supplier_name": "Costco (Waltham, MA)"}

        >>> result = get_last_price_any_supplier(product_id=456)
        >>> result is None  # No purchase history
        True
    """
    if session is not None:
        return _get_last_price_any_supplier_impl(product_id, session)
    with session_scope() as session:
        return _get_last_price_any_supplier_impl(product_id, session)


def _get_last_price_any_supplier_impl(
    product_id: int,
    session: Session,
) -> Optional[Dict[str, Any]]:
    """Implementation for get_last_price_any_supplier.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). Query executes within the caller's
    transaction boundary.
    """
    purchase = (
        session.query(Purchase)
        .filter(Purchase.product_id == product_id)
        .order_by(Purchase.purchase_date.desc())
        .first()
    )

    if not purchase:
        return None

    # Get supplier name for display hint
    supplier = session.query(Supplier).filter(Supplier.id == purchase.supplier_id).first()
    supplier_name = supplier.display_name if supplier else "Unknown"

    return {
        "unit_price": str(purchase.unit_price),
        "purchase_date": purchase.purchase_date.isoformat(),
        "supplier_id": purchase.supplier_id,
        "supplier_name": supplier_name,
    }


def delete_purchase(
    purchase_id: int,
    session: Optional[Session] = None,
) -> bool:
    """Delete purchase record and linked inventory items.

    Transaction boundary: Multi-step atomic operation.
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
    1. Load purchase with linked inventory items
    2. Delete all linked InventoryItem records
    3. Delete the Purchase record

    CRITICAL: If session is provided, all operations execute within caller's
    transaction. If session is None, creates own session_scope() for atomicity.
    Never creates nested session_scope() when session is passed.

    Per spec FR-024: Delete MUST cascade to remove linked InventoryItem records.
    This function should only be called after validating with can_delete_purchase()
    that no depletions exist. If depletions exist, the FK constraint on
    InventoryDepletion will prevent deletion.

    Args:
        purchase_id: Purchase identifier
        session: Optional database session for transaction sharing

    Returns:
        bool: True if deletion successful

    Raises:
        PurchaseNotFound: If purchase_id doesn't exist
        DatabaseError: If database operation fails (e.g., FK constraint violation)

    Note:
        Deletion is permanent and cannot be undone. Always call can_delete_purchase()
        first to verify deletion is allowed.

    Example:
        >>> allowed, reason = can_delete_purchase(789)
        >>> if allowed:
        ...     delete_purchase(789)
        True
    """
    if session is not None:
        return _delete_purchase_impl(purchase_id, session)
    with session_scope() as sess:
        return _delete_purchase_impl(purchase_id, sess)


def _delete_purchase_impl(purchase_id: int, session: Session) -> bool:
    """Implementation for delete_purchase with cascade to InventoryItems.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). All delete operations execute within
    the caller's transaction boundary.
    """
    try:
        # Load purchase with inventory items
        purchase = (
            session.query(Purchase)
            .options(joinedload(Purchase.inventory_items))
            .filter(Purchase.id == purchase_id)
            .first()
        )

        if not purchase:
            raise PurchaseNotFound(purchase_id)

        # FR-024: Delete linked InventoryItem records first
        # This must happen before deleting the purchase due to FK constraint
        for item in purchase.inventory_items:
            session.delete(item)

        # Now delete the purchase
        session.delete(purchase)
        session.flush()

        return True

    except PurchaseNotFound:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete purchase {purchase_id}", original_error=e)


# =============================================================================
# CRUD Operations for Purchases Tab (Feature 042)
# =============================================================================


def get_purchases_filtered(
    date_range: str = "last_30_days",
    supplier_id: Optional[int] = None,
    search_query: Optional[str] = None,
    session: Optional[Session] = None,
) -> List[Dict]:
    """Get purchase history with filters.

    Transaction boundary: Read-only, no transaction needed.
    If session provided, query executes within caller's transaction for
    consistent reads. If session is None, uses session_scope() internally.
    Safe to call standalone - no modifications performed.

    This function returns purchases filtered by date range, supplier, and search
    query. Results include remaining inventory calculated via FIFO tracking.

    Args:
        date_range: One of "last_30_days", "last_90_days", "last_year", "all_time"
        supplier_id: Optional supplier ID to filter by
        search_query: Optional search string to filter by product name (case-insensitive)
        session: Optional database session for transaction sharing

    Returns:
        List of dicts with:
        - id: int
        - product_name: str
        - supplier_name: str
        - purchase_date: date
        - quantity_purchased: Decimal
        - unit_price: Decimal
        - total_cost: Decimal
        - remaining_inventory: Decimal (from FIFO tracking)
        - notes: Optional[str]

    Ordered by purchase_date DESC.

    Example:
        >>> purchases = get_purchases_filtered(date_range="last_30_days")
        >>> len(purchases)
        5
        >>> purchases[0]["product_name"]
        'King Arthur All-Purpose Flour 5lb'
    """
    if session is not None:
        return _get_purchases_filtered_impl(date_range, supplier_id, search_query, session)
    with session_scope() as sess:
        return _get_purchases_filtered_impl(date_range, supplier_id, search_query, sess)


def _get_purchases_filtered_impl(
    date_range: str,
    supplier_id: Optional[int],
    search_query: Optional[str],
    session: Session,
) -> List[Dict]:
    """Implementation for get_purchases_filtered.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). Query executes within the caller's
    transaction boundary.
    """
    # Calculate date cutoff based on date_range
    cutoff_date = None
    if date_range == "last_30_days":
        cutoff_date = date.today() - timedelta(days=30)
    elif date_range == "last_90_days":
        cutoff_date = date.today() - timedelta(days=90)
    elif date_range == "last_year":
        cutoff_date = date.today() - timedelta(days=365)
    # "all_time" has no cutoff

    # Build query with eager loading
    query = session.query(Purchase).options(
        joinedload(Purchase.product),
        joinedload(Purchase.supplier),
        joinedload(Purchase.inventory_items),
    )

    # Apply date filter
    if cutoff_date:
        query = query.filter(Purchase.purchase_date >= cutoff_date)

    # Apply supplier filter
    if supplier_id:
        query = query.filter(Purchase.supplier_id == supplier_id)

    # Apply search filter (case-insensitive on product_name or brand)
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.join(Purchase.product).filter(
            (Product.product_name.ilike(search_pattern)) | (Product.brand.ilike(search_pattern))
        )

    # Order by purchase_date DESC
    query = query.order_by(Purchase.purchase_date.desc())

    purchases = query.all()

    # Build result list
    result = []
    for purchase in purchases:
        # Calculate remaining inventory from linked inventory items
        remaining = Decimal("0")
        for item in purchase.inventory_items:
            if item.quantity is not None:
                remaining += Decimal(str(item.quantity))

        result.append(
            {
                "id": purchase.id,
                "product_name": purchase.product.display_name if purchase.product else "Unknown",
                "supplier_name": purchase.supplier.name if purchase.supplier else "Unknown",
                "purchase_date": purchase.purchase_date,
                "quantity_purchased": Decimal(str(purchase.quantity_purchased)),
                "unit_price": purchase.unit_price,
                "total_cost": purchase.total_cost,
                "remaining_inventory": remaining,
                "notes": purchase.notes,
            }
        )

    return result


def get_remaining_inventory(
    purchase_id: int,
    session: Optional[Session] = None,
) -> Decimal:
    """Calculate remaining inventory from this purchase.

    Transaction boundary: Read-only, no transaction needed.
    If session provided, query executes within caller's transaction for
    consistent reads. If session is None, uses session_scope() internally.
    Safe to call standalone - no modifications performed.

    Sums current_quantity across all linked InventoryItems for the purchase.

    Args:
        purchase_id: Purchase ID to check
        session: Optional database session for transaction sharing

    Returns:
        Decimal representing total remaining quantity.
        Returns Decimal("0") if fully consumed or no items.

    Raises:
        PurchaseNotFound: If purchase_id doesn't exist

    Example:
        >>> remaining = get_remaining_inventory(purchase_id=123)
        >>> remaining
        Decimal('2.5')
    """
    if session is not None:
        return _get_remaining_inventory_impl(purchase_id, session)
    with session_scope() as sess:
        return _get_remaining_inventory_impl(purchase_id, sess)


def _get_remaining_inventory_impl(
    purchase_id: int,
    session: Session,
) -> Decimal:
    """Implementation for get_remaining_inventory.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). Query executes within the caller's
    transaction boundary.
    """
    purchase = (
        session.query(Purchase)
        .options(joinedload(Purchase.inventory_items))
        .filter(Purchase.id == purchase_id)
        .first()
    )

    if not purchase:
        raise PurchaseNotFound(purchase_id)

    remaining = Decimal("0")
    for item in purchase.inventory_items:
        if item.quantity is not None:
            remaining += Decimal(str(item.quantity))

    return remaining


def can_edit_purchase(
    purchase_id: int,
    new_quantity: Decimal,
    session: Optional[Session] = None,
) -> Tuple[bool, str]:
    """Validate if purchase can be edited with new quantity.

    Transaction boundary: Read-only, no transaction needed.
    If session provided, query executes within caller's transaction for
    consistent reads. If session is None, uses session_scope() internally.
    Safe to call standalone - no modifications performed.

    Checks if the new quantity is greater than or equal to the total consumed
    quantity from this purchase. The product cannot be changed.

    Args:
        purchase_id: Purchase ID to validate
        new_quantity: Proposed new quantity (in packages)
        session: Optional database session for transaction sharing

    Returns:
        Tuple of (allowed: bool, reason: str)
        - (True, "") if edit is allowed
        - (False, "reason") if edit is blocked

    Raises:
        PurchaseNotFound: If purchase_id doesn't exist

    Example:
        >>> allowed, reason = can_edit_purchase(123, Decimal("5.0"))
        >>> allowed
        True

        >>> allowed, reason = can_edit_purchase(123, Decimal("0.5"))
        >>> allowed
        False
        >>> reason
        'Cannot reduce below 2.0 units (already consumed)'
    """
    if session is not None:
        return _can_edit_purchase_impl(purchase_id, new_quantity, session)
    with session_scope() as sess:
        return _can_edit_purchase_impl(purchase_id, new_quantity, sess)


def _can_edit_purchase_impl(
    purchase_id: int,
    new_quantity: Decimal,
    session: Session,
) -> Tuple[bool, str]:
    """Implementation for can_edit_purchase.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). Query executes within the caller's
    transaction boundary.
    """
    purchase = (
        session.query(Purchase)
        .options(
            joinedload(Purchase.product),
            joinedload(Purchase.inventory_items).joinedload(InventoryItem.depletions),
        )
        .filter(Purchase.id == purchase_id)
        .first()
    )

    if not purchase:
        raise PurchaseNotFound(purchase_id)

    # Calculate total consumed quantity across all inventory items
    total_consumed = Decimal("0")
    for item in purchase.inventory_items:
        for depletion in item.depletions:
            # quantity_depleted is positive in the model
            total_consumed += Decimal(str(depletion.quantity_depleted))

    # Get package_unit_quantity to convert new_quantity to units
    package_unit_qty = Decimal("1")
    if purchase.product and purchase.product.package_unit_quantity:
        package_unit_qty = Decimal(str(purchase.product.package_unit_quantity))

    # Calculate new total units from packages
    new_total_units = new_quantity * package_unit_qty

    if new_total_units < total_consumed:
        return (False, f"Cannot reduce below {total_consumed} units (already consumed)")

    return (True, "")


def can_delete_purchase(
    purchase_id: int,
    session: Optional[Session] = None,
) -> Tuple[bool, str]:
    """Check if purchase can be deleted.

    Transaction boundary: Read-only, no transaction needed.
    If session provided, query executes within caller's transaction for
    consistent reads. If session is None, uses session_scope() internally.
    Safe to call standalone - no modifications performed.

    A purchase can only be deleted if no inventory from it has been consumed.

    Args:
        purchase_id: Purchase ID to check
        session: Optional database session for transaction sharing

    Returns:
        Tuple of (allowed: bool, reason: str)
        - (True, "") if no depletions exist
        - (False, "Cannot delete - X units already used in: Recipe1, Recipe2")

    Raises:
        PurchaseNotFound: If purchase_id doesn't exist

    Example:
        >>> allowed, reason = can_delete_purchase(123)
        >>> allowed
        True

        >>> allowed, reason = can_delete_purchase(456)
        >>> allowed
        False
        >>> reason
        'Cannot delete - 5.0 units already used in: Chocolate Chip Cookies, Banana Bread'
    """
    if session is not None:
        return _can_delete_purchase_impl(purchase_id, session)
    with session_scope() as sess:
        return _can_delete_purchase_impl(purchase_id, sess)


def _can_delete_purchase_impl(
    purchase_id: int,
    session: Session,
) -> Tuple[bool, str]:
    """Implementation for can_delete_purchase.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). Query executes within the caller's
    transaction boundary.
    """
    purchase = (
        session.query(Purchase)
        .options(
            joinedload(Purchase.product),
            joinedload(Purchase.inventory_items).joinedload(InventoryItem.depletions),
        )
        .filter(Purchase.id == purchase_id)
        .first()
    )

    if not purchase:
        raise PurchaseNotFound(purchase_id)

    # Check for any depletions
    total_consumed = Decimal("0")
    depletion_ids = []

    for item in purchase.inventory_items:
        for depletion in item.depletions:
            total_consumed += Decimal(str(depletion.quantity_depleted))
            depletion_ids.append(depletion.id)

    if total_consumed == Decimal("0"):
        return (True, "")

    # Get recipe names from production runs
    # Note: depletions link to production_runs which link to recipes
    recipe_names = set()

    # Query depletions to get production runs
    depletions = (
        session.query(InventoryDepletion).filter(InventoryDepletion.id.in_(depletion_ids)).all()
    )

    for depletion in depletions:
        # Check the depletion_reason for the recipe info
        # In this codebase, depletion_reason contains the reason string
        if depletion.depletion_reason:
            recipe_names.add(depletion.depletion_reason)

    # Get unit from product
    unit = "units"
    if purchase.product and purchase.product.package_unit:
        unit = purchase.product.package_unit

    recipes_str = ", ".join(sorted(recipe_names)) if recipe_names else "production runs"

    return (False, f"Cannot delete - {total_consumed} {unit} already used in: {recipes_str}")


def update_purchase(
    purchase_id: int,
    updates: Dict[str, Any],
    session: Optional[Session] = None,
) -> Purchase:
    """Update purchase fields and recalculate FIFO costs if needed.

    Transaction boundary: Multi-step atomic operation.
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
    1. Load purchase with linked inventory items and depletions
    2. Validate product_id not changed and quantity >= consumed
    3. Update purchase fields (date, quantity, price, supplier, notes)
    4. Recalculate unit_cost on linked InventoryItems if price changed
    5. Adjust inventory quantities proportionally if quantity changed

    CRITICAL: If session is provided, all operations execute within caller's
    transaction. If session is None, creates own session_scope() for atomicity.
    Never creates nested session_scope() when session is passed.

    Updates allowed:
    - purchase_date
    - quantity_purchased (if >= consumed)
    - unit_price (triggers unit_cost recalc on linked InventoryItems)
    - supplier_id
    - notes

    NOT allowed:
    - product_id (raises ValueError)

    Args:
        purchase_id: Purchase ID to update
        updates: Dict of field -> new_value
        session: Optional database session for transaction sharing

    Returns:
        Updated Purchase object

    Raises:
        PurchaseNotFound: If purchase_id doesn't exist
        ValueError: If trying to change product_id
        ValueError: If quantity < consumed

    Example:
        >>> purchase = update_purchase(123, {"unit_price": Decimal("9.99")})
        >>> purchase.unit_price
        Decimal('9.99')
    """
    if session is not None:
        return _update_purchase_impl(purchase_id, updates, session)
    with session_scope() as sess:
        return _update_purchase_impl(purchase_id, updates, sess)


def _update_purchase_impl(
    purchase_id: int,
    updates: Dict[str, Any],
    session: Session,
) -> Purchase:
    """Implementation for update_purchase.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). All update operations execute within
    the caller's transaction boundary.
    """
    purchase = (
        session.query(Purchase)
        .options(
            joinedload(Purchase.product),
            joinedload(Purchase.inventory_items).joinedload(InventoryItem.depletions),
        )
        .filter(Purchase.id == purchase_id)
        .first()
    )

    if not purchase:
        raise PurchaseNotFound(purchase_id)

    # Check for disallowed updates
    if "product_id" in updates and updates["product_id"] != purchase.product_id:
        raise ValueError("Cannot change product_id on an existing purchase")

    # Validate quantity change if present
    if "quantity_purchased" in updates:
        new_qty = Decimal(str(updates["quantity_purchased"]))
        allowed, reason = _can_edit_purchase_impl(purchase_id, new_qty, session)
        if not allowed:
            raise ValueError(reason)

    # Track old values for recalculations
    old_unit_price = purchase.unit_price
    old_quantity = purchase.quantity_purchased

    # Apply updates
    if "purchase_date" in updates:
        purchase.purchase_date = updates["purchase_date"]

    if "quantity_purchased" in updates:
        purchase.quantity_purchased = updates["quantity_purchased"]

    if "unit_price" in updates:
        purchase.unit_price = updates["unit_price"]

    if "supplier_id" in updates:
        purchase.supplier_id = updates["supplier_id"]

    if "notes" in updates:
        purchase.notes = updates["notes"]

    # If unit_price changed, recalculate unit_cost on linked InventoryItems
    if "unit_price" in updates and updates["unit_price"] != old_unit_price:
        new_price = Decimal(str(updates["unit_price"]))
        package_unit_qty = Decimal("1")
        if purchase.product and purchase.product.package_unit_quantity:
            package_unit_qty = Decimal(str(purchase.product.package_unit_quantity))

        new_unit_cost = new_price / package_unit_qty if package_unit_qty > 0 else new_price

        for item in purchase.inventory_items:
            item.unit_cost = float(new_unit_cost)

    # If quantity changed, adjust current_quantity on InventoryItems proportionally
    if "quantity_purchased" in updates and updates["quantity_purchased"] != old_quantity:
        new_qty = Decimal(str(updates["quantity_purchased"]))

        # Get package unit quantity
        package_unit_qty = Decimal("1")
        if purchase.product and purchase.product.package_unit_quantity:
            package_unit_qty = Decimal(str(purchase.product.package_unit_quantity))

        # Calculate consumed quantity
        total_consumed = Decimal("0")
        for item in purchase.inventory_items:
            for depletion in item.depletions:
                total_consumed += Decimal(str(depletion.quantity_depleted))

        # New total units
        new_total_units = new_qty * package_unit_qty

        # Remaining should be new_total - consumed
        new_remaining = new_total_units - total_consumed

        # Distribute remaining across inventory items proportionally
        # For simplicity, if there's only one item, set it directly
        if len(purchase.inventory_items) == 1:
            purchase.inventory_items[0].quantity = float(new_remaining)
        elif purchase.inventory_items:
            # Proportional distribution based on current quantities
            current_remaining = sum(
                Decimal(str(item.quantity)) for item in purchase.inventory_items
            )
            if current_remaining > 0:
                for item in purchase.inventory_items:
                    old_item_qty = Decimal(str(item.quantity))
                    proportion = old_item_qty / current_remaining
                    item.quantity = float(new_remaining * proportion)
            else:
                # If no current remaining, put all in first item
                purchase.inventory_items[0].quantity = float(new_remaining)

    session.flush()
    return purchase


def get_purchase_usage_history(
    purchase_id: int,
    session: Optional[Session] = None,
) -> List[Dict]:
    """Get consumption history for a purchase.

    Transaction boundary: Read-only, no transaction needed.
    If session provided, query executes within caller's transaction for
    consistent reads. If session is None, uses session_scope() internally.
    Safe to call standalone - no modifications performed.

    Returns all depletions from inventory items linked to this purchase,
    including the recipe/reason for each consumption.

    Args:
        purchase_id: Purchase ID to get history for
        session: Optional database session for transaction sharing

    Returns:
        List of dicts with:
        - depletion_id: int
        - depleted_at: datetime
        - recipe_name: str (from depletion_reason)
        - quantity_used: Decimal (positive)
        - cost: Decimal (quantity * unit_cost at time of consumption)

    Ordered by depleted_at ASC.

    Raises:
        PurchaseNotFound: If purchase_id doesn't exist

    Example:
        >>> history = get_purchase_usage_history(123)
        >>> len(history)
        2
        >>> history[0]["recipe_name"]
        'Chocolate Chip Cookies'
    """
    if session is not None:
        return _get_purchase_usage_history_impl(purchase_id, session)
    with session_scope() as sess:
        return _get_purchase_usage_history_impl(purchase_id, sess)


def _get_purchase_usage_history_impl(
    purchase_id: int,
    session: Session,
) -> List[Dict]:
    """Implementation for get_purchase_usage_history.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). Query executes within the caller's
    transaction boundary.
    """
    purchase = (
        session.query(Purchase)
        .options(
            joinedload(Purchase.inventory_items).joinedload(InventoryItem.depletions),
        )
        .filter(Purchase.id == purchase_id)
        .first()
    )

    if not purchase:
        raise PurchaseNotFound(purchase_id)

    result = []

    for item in purchase.inventory_items:
        for depletion in item.depletions:
            quantity_used = Decimal(str(depletion.quantity_depleted))
            # Cost is quantity * unit_cost (stored on depletion)
            cost = Decimal(str(depletion.cost)) if depletion.cost else Decimal("0")

            result.append(
                {
                    "depletion_id": depletion.id,
                    "depleted_at": depletion.depletion_date,
                    "recipe_name": depletion.depletion_reason or "Unknown",
                    "quantity_used": quantity_used,
                    "cost": cost,
                }
            )

    # Sort by depleted_at ASC
    result.sort(key=lambda x: x["depleted_at"] if x["depleted_at"] else "")

    return result
