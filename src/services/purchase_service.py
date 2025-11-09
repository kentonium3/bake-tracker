"""Purchase Service - Price history tracking and trend analysis.

This module provides business logic for managing purchase records including
price tracking, cost trend analysis, and automated price alert detection.

All functions are stateless and use session_scope() for transaction management.

Key Features:
- Purchase record creation with auto-cost calculation
- Price history tracking per variant
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
    ...     variant_id=123,
    ...     quantity=Decimal("25.0"),
    ...     total_cost=Decimal("18.99"),
    ...     purchase_date=date(2025, 1, 15),
    ...     store="Costco"
    ... )
    >>> purchase.unit_cost  # Auto-calculated
    Decimal('0.76')
    >>>
    >>> # Analyze price trend
    >>> trend = get_price_trend(variant_id=123, days=90)
    >>> trend["direction"]  # "increasing", "decreasing", or "stable"
    'increasing'
    >>> trend["slope_per_day"]
    Decimal('0.012')
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import date, timedelta
from statistics import linear_regression

from ..models import Purchase, Variant
from .database import session_scope
from .exceptions import (
    PurchaseNotFound,
    VariantNotFound,
    ValidationError as ServiceValidationError,
    DatabaseError,
)
from .variant_service import get_variant


# Price change alert thresholds (percentage)
PRICE_ALERT_WARNING = Decimal("0.20")  # 20% change
PRICE_ALERT_CRITICAL = Decimal("0.40")  # 40% change


def record_purchase(
    variant_id: int,
    quantity: Decimal,
    total_cost: Decimal,
    purchase_date: date,
    store: Optional[str] = None,
    receipt_number: Optional[str] = None,
    notes: Optional[str] = None
) -> Purchase:
    """Record a new purchase with automatic unit cost calculation.

    This function creates a purchase record and auto-calculates the unit cost
    by dividing total_cost by quantity. All monetary values use Decimal for
    precision.

    Args:
        variant_id: ID of product variant purchased
        quantity: Quantity purchased (must be > 0)
        total_cost: Total amount paid (must be >= 0)
        purchase_date: Date of purchase
        store: Optional store/supplier name
        receipt_number: Optional receipt identifier for tracking
        notes: Optional user notes

    Returns:
        Purchase: Created purchase record with calculated unit_cost

    Raises:
        VariantNotFound: If variant_id doesn't exist
        ValidationError: If quantity <= 0 or total_cost < 0
        DatabaseError: If database operation fails

    Example:
        >>> from decimal import Decimal
        >>> from datetime import date
        >>> purchase = record_purchase(
        ...     variant_id=123,
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
    # Validate variant exists
    variant = get_variant(variant_id)

    # Validate quantity > 0
    if quantity <= 0:
        raise ServiceValidationError("Quantity must be positive")

    # Validate total_cost >= 0
    if total_cost < 0:
        raise ServiceValidationError("Total cost cannot be negative")

    # Calculate unit cost
    unit_cost = total_cost / quantity if quantity > 0 else Decimal("0.0")

    try:
        with session_scope() as session:
            purchase = Purchase(
                variant_id=variant_id,
                quantity_purchased=quantity,
                total_cost=total_cost,
                unit_cost=unit_cost,
                purchase_date=purchase_date,
                supplier=store,
                receipt_number=receipt_number,
                notes=notes
            )

            session.add(purchase)
            session.flush()  # Get ID before commit

            return purchase

    except VariantNotFound:
        raise
    except ServiceValidationError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to record purchase", original_error=e)


def get_purchase(purchase_id: int) -> Purchase:
    """Retrieve purchase record by ID.

    Args:
        purchase_id: Purchase identifier

    Returns:
        Purchase: Purchase object with variant relationship eager-loaded

    Raises:
        PurchaseNotFound: If purchase_id doesn't exist

    Example:
        >>> purchase = get_purchase(456)
        >>> purchase.variant.brand
        'King Arthur'
        >>> purchase.total_cost
        Decimal('18.99')
    """
    with session_scope() as session:
        purchase = session.query(Purchase).filter_by(id=purchase_id).first()

        if not purchase:
            raise PurchaseNotFound(purchase_id)

        return purchase


def get_purchase_history(
    variant_id: Optional[int] = None,
    ingredient_slug: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    store: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Purchase]:
    """Retrieve purchase history with flexible filtering.

    This function supports filtering by variant, ingredient, date range, and store.
    Results are ordered by purchase_date DESC (most recent first).

    Args:
        variant_id: Optional filter for specific variant
        ingredient_slug: Optional filter for all variants of ingredient
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

        # Join Variant if filtering by ingredient_slug
        if ingredient_slug:
            ingredient = get_ingredient(ingredient_slug)
            q = q.join(Variant).filter(Variant.ingredient_id == ingredient.id)

        # Apply other filters
        if variant_id:
            q = q.filter(Purchase.variant_id == variant_id)
        if start_date:
            q = q.filter(Purchase.purchase_date >= start_date)
        if end_date:
            q = q.filter(Purchase.purchase_date <= end_date)
        if store:
            q = q.filter(Purchase.supplier == store)

        # Order by date DESC (most recent first)
        q = q.order_by(Purchase.purchase_date.desc())

        # Apply limit
        if limit:
            q = q.limit(limit)

        return q.all()


def get_most_recent_purchase(variant_id: int) -> Optional[Purchase]:
    """Get the most recent purchase for a variant.

    Args:
        variant_id: Variant identifier

    Returns:
        Optional[Purchase]: Most recent purchase, or None if no purchases exist

    Raises:
        VariantNotFound: If variant_id doesn't exist

    Example:
        >>> recent = get_most_recent_purchase(123)
        >>> recent.purchase_date if recent else "No purchases yet"
        date(2025, 1, 15)

        >>> recent = get_most_recent_purchase(456)  # New variant
        >>> recent is None
        True
    """
    # Validate variant exists
    get_variant(variant_id)

    with session_scope() as session:
        return session.query(Purchase).filter_by(
            variant_id=variant_id
        ).order_by(Purchase.purchase_date.desc()).first()


def calculate_average_price(variant_id: int, days: int = 60) -> Optional[Decimal]:
    """Calculate average unit cost over specified time window.

    This function computes the mean unit_cost for all purchases within the
    specified number of days from today. Returns None if no purchases in window.

    Args:
        variant_id: Variant identifier
        days: Number of days to look back (default: 60)

    Returns:
        Optional[Decimal]: Average unit cost, or None if no purchases in window

    Raises:
        VariantNotFound: If variant_id doesn't exist

    Example:
        >>> from decimal import Decimal
        >>> avg = calculate_average_price(variant_id=123, days=60)
        >>> avg
        Decimal('0.7234')

        >>> avg = calculate_average_price(variant_id=456, days=30)
        >>> avg is None  # No purchases in last 30 days
        True
    """
    # Validate variant exists
    get_variant(variant_id)

    cutoff_date = date.today() - timedelta(days=days)

    with session_scope() as session:
        purchases = session.query(Purchase).filter(
            Purchase.variant_id == variant_id,
            Purchase.purchase_date >= cutoff_date
        ).all()

        if not purchases:
            return None

        # Calculate average
        total = sum(p.unit_cost for p in purchases)
        count = len(purchases)
        return Decimal(str(total)) / Decimal(str(count))


def detect_price_change(
    variant_id: int,
    new_unit_cost: Decimal,
    comparison_days: int = 60
) -> Dict[str, Any]:
    """Detect significant price changes compared to historical average.

    This function compares a new unit cost against the historical average and
    calculates the percentage change. It categorizes changes using configurable
    thresholds.

    Args:
        variant_id: Variant identifier
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
        VariantNotFound: If variant_id doesn't exist

    Note:
        Alert levels:
        - "none": Change < 20%
        - "warning": Change 20-40%
        - "critical": Change > 40%

    Example:
        >>> from decimal import Decimal
        >>> result = detect_price_change(
        ...     variant_id=123,
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
    avg_price = calculate_average_price(variant_id, comparison_days)

    # No historical data
    if avg_price is None:
        return {
            "average_price": None,
            "new_price": new_unit_cost,
            "change_amount": None,
            "change_percent": None,
            "alert_level": "none",
            "message": "No historical data for comparison"
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
        "message": message
    }


def get_price_trend(variant_id: int, days: int = 90) -> Dict[str, Any]:
    """Analyze price trend using linear regression.

    This function performs linear regression on purchase history to identify
    pricing trends over time. It calculates slope (price change per day) and
    categorizes the trend direction.

    Args:
        variant_id: Variant identifier
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
        VariantNotFound: If variant_id doesn't exist

    Note:
        - Requires at least 2 data points for regression
        - "stable" defined as |slope| < $0.001/day
        - Uses Python's statistics.linear_regression for calculation

    Example:
        >>> trend = get_price_trend(variant_id=123, days=90)
        >>> trend["direction"]
        'increasing'
        >>> trend["slope_per_day"]
        Decimal('0.012')
        >>> trend["message"]
        'Price increasing at $0.012 per day over 90 days (5 purchases)'
    """
    # Validate variant exists
    get_variant(variant_id)

    cutoff_date = date.today() - timedelta(days=days)

    with session_scope() as session:
        purchases = session.query(Purchase).filter(
            Purchase.variant_id == variant_id,
            Purchase.purchase_date >= cutoff_date
        ).order_by(Purchase.purchase_date.asc()).all()

        # Need at least 2 data points for regression
        if len(purchases) < 2:
            return {
                "direction": "stable",
                "slope_per_day": Decimal("0.0"),
                "data_points": len(purchases),
                "oldest_date": purchases[0].purchase_date if purchases else None,
                "newest_date": purchases[0].purchase_date if purchases else None,
                "message": f"Insufficient data for trend analysis ({len(purchases)} purchase)"
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
            "message": message
        }


def delete_purchase(purchase_id: int) -> bool:
    """Delete purchase record.

    Deletes a purchase record. Typically used for correcting erroneous entries.

    Args:
        purchase_id: Purchase identifier

    Returns:
        bool: True if deletion successful

    Raises:
        PurchaseNotFound: If purchase_id doesn't exist
        DatabaseError: If database operation fails

    Note:
        Deletion is permanent and cannot be undone. Consider adding a 'deleted'
        flag instead for audit trail preservation.

    Example:
        >>> delete_purchase(789)
        True
    """
    try:
        with session_scope() as session:
            purchase = session.query(Purchase).filter_by(id=purchase_id).first()
            if not purchase:
                raise PurchaseNotFound(purchase_id)

            session.delete(purchase)
            return True

    except PurchaseNotFound:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete purchase {purchase_id}", original_error=e)