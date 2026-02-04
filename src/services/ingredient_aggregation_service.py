"""
Ingredient Aggregation Service for F074.

Aggregates recipe ingredients across batch decisions for shopping list generation.
Converts batch decisions (from F073) into total ingredient quantities keyed by
(ingredient_id, unit) tuple.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.models import BatchDecision, Recipe
from src.services.database import session_scope
from src.services.exceptions import ValidationError


# Type alias for aggregation key
IngredientKey = Tuple[int, str]  # (ingredient_id, unit)


@dataclass
class IngredientTotal:
    """Aggregated ingredient total for shopping list generation."""

    ingredient_id: int
    ingredient_name: str
    unit: str
    total_quantity: float  # Rounded to 3 decimal places


def _scale_recipe_ingredients(
    recipe: Recipe,
    batches: int,
) -> List[Tuple[int, str, str, float]]:
    """
    Scale a recipe's ingredients by batch count.

    Args:
        recipe: Recipe with recipe_ingredients relationship loaded
        batches: Number of batches to make

    Returns:
        List of (ingredient_id, ingredient_name, unit, scaled_quantity) tuples
    """
    results = []
    for ri in recipe.recipe_ingredients:
        if ri.ingredient is None:
            continue  # Skip orphaned recipe ingredients

        scaled_qty = ri.quantity * batches
        results.append(
            (
                ri.ingredient_id,
                ri.ingredient.display_name,
                ri.unit,
                scaled_qty,
            )
        )
    return results


def aggregate_ingredients_for_event(
    event_id: int,
    session: Optional[Session] = None,
) -> Dict[IngredientKey, IngredientTotal]:
    """
    Aggregate ingredients across all batch decisions for an event.

    Queries BatchDecision records, scales recipe ingredients by batch count,
    and aggregates same (ingredient_id, unit) pairs into totals.

    Args:
        event_id: Event to aggregate for
        session: Optional session for transaction sharing

    Returns:
        Dict keyed by (ingredient_id, unit) with IngredientTotal values

    Raises:
        ValidationError: If event not found
    """
    if session is not None:
        return _aggregate_ingredients_impl(event_id, session)
    with session_scope() as session:
        return _aggregate_ingredients_impl(event_id, session)


def _aggregate_ingredients_impl(
    event_id: int,
    session: Session,
) -> Dict[IngredientKey, IngredientTotal]:
    """Internal implementation of aggregate_ingredients_for_event."""
    from src.models import Event  # Import here to avoid circular

    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise ValidationError([f"Event {event_id} not found"])

    # Query batch decisions for this event
    batch_decisions = (
        session.query(BatchDecision).filter(BatchDecision.event_id == event_id).all()
    )

    # Handle empty event
    if not batch_decisions:
        return {}

    # Aggregate ingredients
    totals: Dict[IngredientKey, float] = {}
    names: Dict[int, str] = {}  # ingredient_id -> name cache

    for bd in batch_decisions:
        # Skip invalid batch decisions
        if bd.batches <= 0:
            continue

        # Get recipe via FinishedUnit
        fu = bd.finished_unit
        if fu is None or fu.recipe is None:
            continue

        recipe = fu.recipe
        scaled_ingredients = _scale_recipe_ingredients(recipe, bd.batches)

        for ing_id, ing_name, unit, qty in scaled_ingredients:
            key = (ing_id, unit)
            totals[key] = totals.get(key, 0.0) + qty
            names[ing_id] = ing_name

    # Build result with IngredientTotal objects
    result: Dict[IngredientKey, IngredientTotal] = {}
    for (ing_id, unit), total_qty in totals.items():
        result[(ing_id, unit)] = IngredientTotal(
            ingredient_id=ing_id,
            ingredient_name=names[ing_id],
            unit=unit,
            total_quantity=round(total_qty, 3),
        )

    return result
