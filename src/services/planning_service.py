"""
Planning Service for F072 Recipe Decomposition & Aggregation.

Provides recipe requirement calculation for event planning:
- Recursive bundle decomposition with quantity tracking
- Recipe aggregation across multiple FG selections
- Cycle detection and depth limiting

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from typing import Dict, Optional, Set

from sqlalchemy.orm import Session

from src.models import (
    Event,
    EventFinishedGood,
    FinishedGood,
    Recipe,
)
from src.services.database import session_scope
from src.services.event_service import (
    CircularReferenceError,
    MaxDepthExceededError,
    MAX_FG_NESTING_DEPTH,
)
from src.services.exceptions import ValidationError


def calculate_recipe_requirements(
    event_id: int,
    session: Session = None,
) -> Dict[Recipe, int]:
    """
    Calculate aggregated recipe requirements for an event.

    Decomposes all FG selections for the event into atomic recipe requirements,
    multiplying quantities through bundle hierarchies and aggregating by recipe.

    Args:
        event_id: The Event to calculate requirements for
        session: Optional session for transaction sharing

    Returns:
        Dictionary mapping Recipe objects to total quantities needed

    Raises:
        ValidationError: If event not found or FG has no recipe
        CircularReferenceError: If bundle contains circular reference
        MaxDepthExceededError: If nesting exceeds MAX_FG_NESTING_DEPTH
    """
    if session is not None:
        return _calculate_recipe_requirements_impl(event_id, session)
    with session_scope() as session:
        return _calculate_recipe_requirements_impl(event_id, session)


def _calculate_recipe_requirements_impl(
    event_id: int,
    session: Session,
) -> Dict[Recipe, int]:
    """Internal implementation of calculate_recipe_requirements."""
    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise ValidationError([f"Event {event_id} not found"])

    # Query EventFinishedGoods for this event
    efgs = (
        session.query(EventFinishedGood)
        .filter(EventFinishedGood.event_id == event_id)
        .all()
    )

    # Handle empty event
    if not efgs:
        return {}

    # Aggregate across all FG selections
    result: Dict[Recipe, int] = {}
    for efg in efgs:
        fg_result = _decompose_fg_to_recipes(
            efg.finished_good_id,
            efg.quantity,
            session,
            set(),  # Fresh path for each top-level FG
            0,  # Start at depth 0
        )
        for recipe, qty in fg_result.items():
            result[recipe] = result.get(recipe, 0) + qty

    return result


def _decompose_fg_to_recipes(
    fg_id: int,
    multiplier: int,
    session: Session,
    _path: Set[int],
    _depth: int,
) -> Dict[Recipe, int]:
    """
    Recursively decompose a FinishedGood to recipe requirements with quantities.

    Uses path-based cycle detection (allows DAG patterns, catches true cycles).

    Args:
        fg_id: FinishedGood ID to decompose
        multiplier: Quantity multiplier from parent (accumulates through nesting)
        session: Database session
        _path: Set of FG IDs in current ancestry path (for cycle detection)
        _depth: Current nesting depth

    Returns:
        Dictionary mapping Recipe objects to quantities for this FG subtree
    """
    # Check depth limit
    if _depth > MAX_FG_NESTING_DEPTH:
        raise MaxDepthExceededError(_depth, MAX_FG_NESTING_DEPTH)

    # Check for circular reference (path-based detection)
    if fg_id in _path:
        raise CircularReferenceError(fg_id, list(_path))

    # Add to current path
    _path.add(fg_id)

    try:
        # Query FinishedGood with components (eager loaded per model)
        fg = session.query(FinishedGood).filter(FinishedGood.id == fg_id).first()
        if fg is None:
            raise ValidationError([f"FinishedGood {fg_id} not found"])

        result: Dict[Recipe, int] = {}

        # Traverse components
        for comp in fg.components:
            # Calculate effective quantity at this level
            effective_qty = int(comp.component_quantity * multiplier)

            # Skip zero-quantity components
            if effective_qty <= 0:
                continue

            if comp.finished_unit_id is not None:
                # Atomic component: get recipe from FinishedUnit
                fu = comp.finished_unit_component
                if fu is None:
                    raise ValidationError(
                        [f"FinishedUnit {comp.finished_unit_id} not found"]
                    )
                if fu.recipe is None:
                    raise ValidationError(
                        [f"FinishedUnit '{fu.display_name}' (id={fu.id}) has no recipe"]
                    )

                recipe = fu.recipe
                result[recipe] = result.get(recipe, 0) + effective_qty

            elif comp.finished_good_id is not None:
                # Nested bundle: recurse
                child_result = _decompose_fg_to_recipes(
                    comp.finished_good_id,
                    effective_qty,
                    session,
                    _path,
                    _depth + 1,
                )
                # Merge child results
                for recipe, qty in child_result.items():
                    result[recipe] = result.get(recipe, 0) + qty

            # else: packaging/material component - no recipe needed (skip)

        return result

    finally:
        # Clean up path when returning (backtracking)
        _path.discard(fg_id)
