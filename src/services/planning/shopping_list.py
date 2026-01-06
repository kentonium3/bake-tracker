"""
Shopping list service for production planning (Feature 039).

This module provides functions for:
- Generating aggregated shopping lists with Need/Have/Buy columns
- Calculating inventory gaps: max(0, needed - available)
- Tracking shopping completion status
- Wrapping existing event_service.get_shopping_list()
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import ProductionPlanSnapshot
from src.services.database import session_scope
from src.services import event_service
from src.utils.datetime_utils import utc_now


@dataclass
class ShoppingListItem:
    """Single item in the shopping list.

    Attributes:
        ingredient_id: Database ID of the ingredient
        ingredient_slug: URL-safe slug for the ingredient
        ingredient_name: Display name of the ingredient
        needed: Total quantity required for the plan
        in_stock: Current inventory quantity
        to_buy: Quantity to purchase: max(0, needed - in_stock)
        unit: Unit of measurement
        is_sufficient: True if in_stock >= needed
    """

    ingredient_id: int
    ingredient_slug: str
    ingredient_name: str
    needed: Decimal
    in_stock: Decimal
    to_buy: Decimal
    unit: str
    is_sufficient: bool


def calculate_purchase_gap(needed: Decimal, in_stock: Decimal) -> Decimal:
    """Calculate how much to buy.

    This is the core gap calculation that determines purchase quantity.
    Never returns negative values.

    Args:
        needed: Total quantity required
        in_stock: Current inventory quantity

    Returns:
        max(0, needed - in_stock)

    Examples:
        >>> calculate_purchase_gap(Decimal("10"), Decimal("5"))
        Decimal('5')
        >>> calculate_purchase_gap(Decimal("5"), Decimal("10"))
        Decimal('0')
        >>> calculate_purchase_gap(Decimal("5"), Decimal("5"))
        Decimal('0')
    """
    return max(Decimal(0), needed - in_stock)


def get_shopping_list(
    event_id: int,
    *,
    include_sufficient: bool = True,
    session: Optional[Session] = None,
) -> List[ShoppingListItem]:
    """Get shopping list with inventory comparison.

    Wraps event_service.get_shopping_list() and transforms results
    to ShoppingListItem DTOs.

    Args:
        event_id: Event to get list for
        include_sufficient: If True, include items with sufficient stock
        session: Optional database session

    Returns:
        List of ShoppingListItem sorted by ingredient name
    """
    if session is not None:
        return _get_shopping_list_impl(event_id, include_sufficient, session)
    with session_scope() as session:
        return _get_shopping_list_impl(event_id, include_sufficient, session)


def _get_shopping_list_impl(
    event_id: int,
    include_sufficient: bool,
    session: Session,
) -> List[ShoppingListItem]:
    """Implementation of get_shopping_list."""
    # Call the existing event_service function
    # Note: event_service.get_shopping_list doesn't support session parameter,
    # so we can't pass it through. This is a known limitation.
    result = event_service.get_shopping_list(event_id, include_packaging=False)

    items = []
    for item_data in result.get("items", []):
        needed = Decimal(str(item_data.get("quantity_needed", 0)))
        in_stock = Decimal(str(item_data.get("quantity_on_hand", 0)))
        to_buy = calculate_purchase_gap(needed, in_stock)
        is_sufficient = in_stock >= needed

        # Filter out sufficient items if requested
        if not include_sufficient and is_sufficient:
            continue

        shopping_item = ShoppingListItem(
            ingredient_id=item_data.get("ingredient_id", 0),
            ingredient_slug=item_data.get("ingredient_slug", ""),
            ingredient_name=item_data.get("ingredient_name", ""),
            needed=needed,
            in_stock=in_stock,
            to_buy=to_buy,
            unit=item_data.get("unit", ""),
            is_sufficient=is_sufficient,
        )
        items.append(shopping_item)

    return items


def get_items_to_buy(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> List[ShoppingListItem]:
    """Get only items that need to be purchased.

    Convenience function that returns only items where to_buy > 0.

    Args:
        event_id: Event to get list for
        session: Optional database session

    Returns:
        List of ShoppingListItem where is_sufficient is False
    """
    return get_shopping_list(event_id, include_sufficient=False, session=session)


def get_shopping_summary(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> Dict[str, any]:
    """Get summary statistics for the shopping list.

    Args:
        event_id: Event to get summary for
        session: Optional database session

    Returns:
        Dict with:
            - total_items: Total number of ingredients
            - items_sufficient: Items with sufficient stock
            - items_to_buy: Items needing purchase
            - all_sufficient: True if nothing needs to be purchased
    """
    all_items = get_shopping_list(event_id, include_sufficient=True, session=session)

    items_sufficient = sum(1 for item in all_items if item.is_sufficient)
    items_to_buy = len(all_items) - items_sufficient

    return {
        "total_items": len(all_items),
        "items_sufficient": items_sufficient,
        "items_to_buy": items_to_buy,
        "all_sufficient": items_to_buy == 0,
    }


def mark_shopping_complete(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> bool:
    """Mark shopping as complete for the event.

    Updates the latest ProductionPlanSnapshot for the event:
    - Sets shopping_complete = True
    - Sets shopping_completed_at = current UTC time

    Args:
        event_id: Event to mark as complete
        session: Optional database session

    Returns:
        True if snapshot was updated, False if no snapshot found
    """
    if session is not None:
        return _mark_shopping_complete_impl(event_id, session)
    with session_scope() as session:
        return _mark_shopping_complete_impl(event_id, session)


def _mark_shopping_complete_impl(event_id: int, session: Session) -> bool:
    """Implementation of mark_shopping_complete."""
    # Get the latest ProductionPlanSnapshot for this event
    snapshot = (
        session.query(ProductionPlanSnapshot)
        .filter(ProductionPlanSnapshot.event_id == event_id)
        .order_by(ProductionPlanSnapshot.calculated_at.desc())
        .first()
    )

    if snapshot is None:
        return False

    snapshot.shopping_complete = True
    snapshot.shopping_completed_at = utc_now()
    session.commit()

    return True


def unmark_shopping_complete(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> bool:
    """Unmark shopping completion for the event.

    Resets shopping status on the latest ProductionPlanSnapshot:
    - Sets shopping_complete = False
    - Sets shopping_completed_at = None

    Args:
        event_id: Event to unmark
        session: Optional database session

    Returns:
        True if snapshot was updated, False if no snapshot found
    """
    if session is not None:
        return _unmark_shopping_complete_impl(event_id, session)
    with session_scope() as session:
        return _unmark_shopping_complete_impl(event_id, session)


def _unmark_shopping_complete_impl(event_id: int, session: Session) -> bool:
    """Implementation of unmark_shopping_complete."""
    snapshot = (
        session.query(ProductionPlanSnapshot)
        .filter(ProductionPlanSnapshot.event_id == event_id)
        .order_by(ProductionPlanSnapshot.calculated_at.desc())
        .first()
    )

    if snapshot is None:
        return False

    snapshot.shopping_complete = False
    snapshot.shopping_completed_at = None
    session.commit()

    return True


def is_shopping_complete(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> bool:
    """Check if shopping is marked complete for the event.

    Args:
        event_id: Event to check
        session: Optional database session

    Returns:
        True if shopping is complete, False otherwise
    """
    if session is not None:
        return _is_shopping_complete_impl(event_id, session)
    with session_scope() as session:
        return _is_shopping_complete_impl(event_id, session)


def _is_shopping_complete_impl(event_id: int, session: Session) -> bool:
    """Implementation of is_shopping_complete."""
    snapshot = (
        session.query(ProductionPlanSnapshot)
        .filter(ProductionPlanSnapshot.event_id == event_id)
        .order_by(ProductionPlanSnapshot.calculated_at.desc())
        .first()
    )

    if snapshot is None:
        return False

    return snapshot.shopping_complete
