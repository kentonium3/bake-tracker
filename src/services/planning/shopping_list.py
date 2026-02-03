"""
Shopping list service for production planning (Feature 039, F079).

This module provides functions for:
- Generating aggregated shopping lists with Need/Have/Buy columns
- Calculating inventory gaps: max(0, needed - available)
- Tracking shopping completion status
- Wrapping existing event_service.get_shopping_list()
- Production-aware calculations (F079): needs for remaining batches only

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import EventProductionTarget, ProductionPlanSnapshot
from src.services.database import session_scope
from src.services import event_service, recipe_service
from src.services.planning.progress import get_remaining_production_needs
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

    Transaction boundary: Pure computation (no database access).
    Calculates gap between needed and available quantities.

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
    production_aware: bool = True,
    session: Optional[Session] = None,
) -> List[ShoppingListItem]:
    """Get shopping list with inventory comparison.

    Transaction boundary: Read-only operation.
    Queries production targets, recipes, and inventory to build shopping list.

    Wraps event_service.get_shopping_list() and transforms results
    to ShoppingListItem DTOs.

    Args:
        event_id: Event to get list for
        include_sufficient: If True, include items with sufficient stock
        production_aware: If True (default), calculate needs for remaining
                         production only. If False, calculate for total planned.
        session: Optional database session

    Returns:
        List of ShoppingListItem sorted by ingredient name
    """
    if session is not None:
        return _get_shopping_list_impl(event_id, include_sufficient, production_aware, session)
    with session_scope() as session:
        return _get_shopping_list_impl(event_id, include_sufficient, production_aware, session)


def _calculate_ingredient_needs_for_remaining(
    event_id: int,
    session: Session,
) -> Dict[str, Dict[str, Any]]:
    """Calculate ingredient needs for remaining production only.

    Transaction boundary: Inherits session from caller.
    Read-only computation within the caller's transaction scope.

    Args:
        event_id: Event to calculate for
        session: Database session

    Returns:
        Dict mapping ingredient_slug to {
            ingredient_id, ingredient_name, needed, unit
        }
    """
    # Get remaining batches per recipe
    remaining_by_recipe = get_remaining_production_needs(event_id, session=session)

    # Aggregate ingredients across all recipes with remaining batches
    ingredient_needs: Dict[str, Dict[str, Any]] = {}

    # Get production targets to know which recipes are in the plan
    targets = (
        session.query(EventProductionTarget)
        .filter(EventProductionTarget.event_id == event_id)
        .all()
    )

    for target in targets:
        remaining = remaining_by_recipe.get(target.recipe_id, 0)
        if remaining == 0:
            continue  # Skip complete recipes

        # Get aggregated ingredients for this recipe
        # This handles nested recipes
        ingredients = recipe_service.get_aggregated_ingredients(
            target.recipe_id,
            session=session,
        )

        for ing in ingredients:
            slug = ing.get("ingredient_slug", "")
            if not slug:
                # Fall back to creating slug from name if not present
                name = ing.get("ingredient_name", "")
                slug = name.lower().replace(" ", "_") if name else ""
            if not slug:
                continue

            # Scale by remaining batches
            base_quantity = ing.get("total_quantity", 0)
            if base_quantity == 0:
                base_quantity = ing.get("quantity", 0)
            needed_for_remaining = float(base_quantity) * remaining

            if slug in ingredient_needs:
                ingredient_needs[slug]["needed"] += needed_for_remaining
            else:
                ingredient_needs[slug] = {
                    "ingredient_id": ing.get("ingredient_id", 0),
                    "ingredient_slug": slug,
                    "ingredient_name": ing.get("ingredient_name", ""),
                    "needed": needed_for_remaining,
                    "unit": ing.get("unit", ""),
                }

    return ingredient_needs


def _get_inventory_for_ingredient(
    ingredient_id: int,
    unit: str,
    session: Session,
) -> Decimal:
    """Get inventory quantity for an ingredient in the specified unit.

    Transaction boundary: Inherits session from caller.
    Read-only query within the caller's transaction scope.

    Args:
        ingredient_id: Ingredient ID
        unit: Unit to get quantity in
        session: Database session

    Returns:
        Quantity in stock (Decimal)
    """
    from src.services import inventory_item_service, ingredient_service

    try:
        # Get ingredient slug
        ingredient = ingredient_service.get_ingredient_by_id(ingredient_id, session=session)
        if ingredient is None:
            return Decimal("0")

        # Get total quantity by unit
        totals = inventory_item_service.get_total_quantity(ingredient.slug)

        # Return quantity in the requested unit, or 0 if not found
        return totals.get(unit, Decimal("0"))
    except Exception:
        return Decimal("0")


def _get_shopping_list_impl(
    event_id: int,
    include_sufficient: bool,
    production_aware: bool,
    session: Session,
) -> List[ShoppingListItem]:
    """Implementation of get_shopping_list.

    Transaction boundary: Inherits session from caller.
    Read-only computation within the caller's transaction scope.
    """
    if production_aware:
        # Calculate needs from remaining production only
        ingredient_needs = _calculate_ingredient_needs_for_remaining(event_id, session)

        # If no remaining production, return empty list
        if not ingredient_needs:
            return []

        items = []
        for slug, need_data in ingredient_needs.items():
            # Get current stock
            in_stock = _get_inventory_for_ingredient(
                need_data["ingredient_id"],
                need_data["unit"],
                session,
            )

            needed = Decimal(str(need_data["needed"]))
            to_buy = calculate_purchase_gap(needed, in_stock)
            is_sufficient = in_stock >= needed

            if not include_sufficient and is_sufficient:
                continue

            items.append(
                ShoppingListItem(
                    ingredient_id=need_data["ingredient_id"],
                    ingredient_slug=slug,
                    ingredient_name=need_data["ingredient_name"],
                    needed=needed,
                    in_stock=in_stock,
                    to_buy=to_buy,
                    unit=need_data["unit"],
                    is_sufficient=is_sufficient,
                )
            )

        return sorted(items, key=lambda x: x.ingredient_name)

    else:
        # Legacy behavior: use event_service for total needs
        result = event_service.get_shopping_list(
            event_id,
            session=session,
            include_packaging=False,
        )

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
    production_aware: bool = True,
    session: Optional[Session] = None,
) -> List[ShoppingListItem]:
    """Get only items that need to be purchased.

    Transaction boundary: Read-only operation.
    Delegates to get_shopping_list() with filtering.

    Convenience function that returns only items where to_buy > 0.

    Args:
        event_id: Event to get list for
        production_aware: If True (default), calculate needs for remaining
                         production only. If False, calculate for total planned.
        session: Optional database session

    Returns:
        List of ShoppingListItem where is_sufficient is False
    """
    return get_shopping_list(
        event_id,
        include_sufficient=False,
        production_aware=production_aware,
        session=session,
    )


def get_shopping_summary(
    event_id: int,
    *,
    production_aware: bool = True,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Get summary statistics for the shopping list.

    Transaction boundary: Read-only operation.
    Delegates to get_shopping_list() and aggregates results.

    Args:
        event_id: Event to get summary for
        production_aware: If True (default), calculate needs for remaining
                         production only. If False, calculate for total planned.
        session: Optional database session

    Returns:
        Dict with:
            - total_items: Total number of ingredients
            - items_sufficient: Items with sufficient stock
            - items_to_buy: Items needing purchase
            - all_sufficient: True if nothing needs to be purchased
    """
    all_items = get_shopping_list(
        event_id,
        include_sufficient=True,
        production_aware=production_aware,
        session=session,
    )

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

    Transaction boundary: Single-step write.
    Updates ProductionPlanSnapshot.shopping_complete flag.

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
    """Implementation of mark_shopping_complete.

    Transaction boundary: Inherits session from caller.
    Updates ProductionPlanSnapshot within the caller's transaction scope.
    """
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
    # Note: Do NOT commit here - let caller control transaction
    # When called without session, session_scope auto-commits on clean exit

    return True


def unmark_shopping_complete(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> bool:
    """Unmark shopping completion for the event.

    Transaction boundary: Single-step write.
    Clears ProductionPlanSnapshot.shopping_complete flag.

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
    """Implementation of unmark_shopping_complete.

    Transaction boundary: Inherits session from caller.
    Updates ProductionPlanSnapshot within the caller's transaction scope.
    """
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
    # Note: Do NOT commit here - let caller control transaction
    # When called without session, session_scope auto-commits on clean exit

    return True


def is_shopping_complete(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> bool:
    """Check if shopping is marked complete for the event.

    Transaction boundary: Read-only operation.
    Queries ProductionPlanSnapshot.shopping_complete flag.

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
    """Implementation of is_shopping_complete.

    Transaction boundary: Inherits session from caller.
    Read-only query within the caller's transaction scope.
    """
    snapshot = (
        session.query(ProductionPlanSnapshot)
        .filter(ProductionPlanSnapshot.event_id == event_id)
        .order_by(ProductionPlanSnapshot.calculated_at.desc())
        .first()
    )

    if snapshot is None:
        return False

    return snapshot.shopping_complete
