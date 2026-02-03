"""
Inventory Gap Analysis Service for F075.

Compares F074's aggregated ingredient totals against current inventory
to identify items requiring purchase vs items already sufficient.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.models import Ingredient
from src.services.database import session_scope
from src.services.ingredient_aggregation_service import (
    aggregate_ingredients_for_event,
    IngredientTotal,
)
from src.services.inventory_item_service import get_total_quantity


@dataclass
class GapItem:
    """Gap analysis result for a single ingredient."""

    ingredient_id: int
    ingredient_name: str
    unit: str
    quantity_needed: float
    quantity_on_hand: float
    gap: float  # max(0, needed - on_hand)


@dataclass
class GapAnalysisResult:
    """Complete gap analysis result with categorized items."""

    purchase_items: List[GapItem]  # Items where gap > 0
    sufficient_items: List[GapItem]  # Items where gap == 0


def _get_inventory_for_ingredient(
    ingredient_id: int,
    unit: str,
    session: Session,
) -> float:
    """
    Get current inventory quantity for an ingredient in specified unit.

    Args:
        ingredient_id: Ingredient to look up
        unit: Unit to match (exact string match)
        session: Database session

    Returns:
        Quantity on hand in the specified unit, or 0.0 if none found
    """
    # Get ingredient to access slug
    ingredient = (
        session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    )
    if ingredient is None:
        return 0.0

    # Query inventory by slug
    try:
        inventory_by_unit = get_total_quantity(ingredient.slug)
    except Exception:
        # If ingredient not found in inventory, treat as zero
        return 0.0

    # Look up specific unit (exact match)
    quantity = inventory_by_unit.get(unit, Decimal("0.0"))
    return float(quantity)


def _calculate_gap(
    ingredient_total: IngredientTotal,
    on_hand: float,
) -> GapItem:
    """
    Calculate gap between needed and on-hand quantities.

    Args:
        ingredient_total: Aggregated ingredient need from F074
        on_hand: Current inventory quantity in matching unit

    Returns:
        GapItem with gap = max(0, needed - on_hand)
    """
    needed = ingredient_total.total_quantity
    gap = max(0.0, needed - on_hand)

    return GapItem(
        ingredient_id=ingredient_total.ingredient_id,
        ingredient_name=ingredient_total.ingredient_name,
        unit=ingredient_total.unit,
        quantity_needed=needed,
        quantity_on_hand=on_hand,
        gap=round(gap, 3),  # Maintain 3 decimal precision
    )


def _partition_results(gap_items: List[GapItem]) -> GapAnalysisResult:
    """
    Partition gap items into purchase_items and sufficient_items.

    Args:
        gap_items: All calculated gap items

    Returns:
        GapAnalysisResult with items categorized by gap > 0 vs gap == 0
    """
    purchase_items = []
    sufficient_items = []

    for item in gap_items:
        if item.gap > 0:
            purchase_items.append(item)
        else:
            sufficient_items.append(item)

    return GapAnalysisResult(
        purchase_items=purchase_items,
        sufficient_items=sufficient_items,
    )


def _analyze_inventory_gaps_impl(
    event_id: int,
    session: Session,
) -> GapAnalysisResult:
    """Internal implementation of analyze_inventory_gaps."""
    # Get aggregated ingredient totals from F074
    totals = aggregate_ingredients_for_event(event_id, session=session)

    # Handle empty event
    if not totals:
        return GapAnalysisResult(purchase_items=[], sufficient_items=[])

    # Calculate gaps for each ingredient
    gap_items: List[GapItem] = []

    for (ingredient_id, unit), ingredient_total in totals.items():
        # Get inventory for this ingredient+unit
        on_hand = _get_inventory_for_ingredient(ingredient_id, unit, session)

        # Calculate gap
        gap_item = _calculate_gap(ingredient_total, on_hand)
        gap_items.append(gap_item)

    # Partition into purchase vs sufficient
    return _partition_results(gap_items)


def analyze_inventory_gaps(
    event_id: int,
    session: Optional[Session] = None,
) -> GapAnalysisResult:
    """
    Analyze inventory gaps for an event's ingredient needs.

    Takes F074's aggregated ingredient totals, queries current inventory,
    and calculates gaps (needed - on_hand) for each ingredient.

    Args:
        event_id: Event to analyze
        session: Optional session for transaction sharing

    Returns:
        GapAnalysisResult with purchase_items and sufficient_items lists

    Raises:
        ValidationError: If event not found (propagated from F074)
    """
    if session is not None:
        return _analyze_inventory_gaps_impl(event_id, session)
    with session_scope() as session:
        return _analyze_inventory_gaps_impl(event_id, session)
