"""
Planning Service for F072 Recipe Decomposition & Aggregation (F073 Enhanced).

Provides FinishedUnit-level requirement decomposition for event planning:
- Recursive bundle decomposition with quantity tracking
- FU-level data preservation (not recipe-level aggregation)
- Cycle detection and depth limiting

F073 Change: Returns List[FURequirement] instead of Dict[Recipe, int]
to preserve FU-level yield context for batch calculation.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from dataclasses import dataclass
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from src.models import (
    Event,
    EventFinishedGood,
    FinishedGood,
    FinishedUnit,
    Recipe,
)
from src.services.database import session_scope
from src.services.event_service import (
    CircularReferenceError,
    MaxDepthExceededError,
    MAX_FG_NESTING_DEPTH,
)
from src.services.exceptions import ValidationError


@dataclass
class FURequirement:
    """Requirement for a single FinishedUnit from bundle decomposition.

    Preserves FU identity for downstream batch calculation which needs
    yield information (items_per_batch, yield_mode) that varies by FU.
    """

    finished_unit: FinishedUnit
    quantity_needed: int
    recipe: Recipe  # Convenience reference (same as finished_unit.recipe)


def decompose_event_to_fu_requirements(
    event_id: int,
    session: Session = None,
) -> List[FURequirement]:
    """
    Decompose event FG selections into FinishedUnit-level requirements.

    Traverses bundle hierarchies, multiplying quantities at each level.
    Returns FU-level data (not recipe-level aggregation) to preserve
    yield context for downstream batch calculation.

    Args:
        event_id: The Event to decompose
        session: Optional session for transaction sharing

    Returns:
        List of FURequirement objects, one per atomic FinishedUnit found

    Raises:
        ValidationError: If event not found or FU has no recipe
        CircularReferenceError: If bundle contains circular reference
        MaxDepthExceededError: If nesting exceeds MAX_FG_NESTING_DEPTH
    """
    if session is not None:
        return _decompose_event_to_fu_requirements_impl(event_id, session)
    with session_scope() as session:
        return _decompose_event_to_fu_requirements_impl(event_id, session)


def _decompose_event_to_fu_requirements_impl(
    event_id: int,
    session: Session,
) -> List[FURequirement]:
    """Internal implementation of decompose_event_to_fu_requirements."""
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
        return []

    # Collect FU requirements across all FG selections (no aggregation)
    result: List[FURequirement] = []
    for efg in efgs:
        fu_requirements = _decompose_fg_to_fus(
            efg.finished_good_id,
            efg.quantity,
            session,
            set(),  # Fresh path for each top-level FG
            0,  # Start at depth 0
        )
        result.extend(fu_requirements)

    return result


def _decompose_fg_to_fus(
    fg_id: int,
    multiplier: int,
    session: Session,
    _path: Set[int],
    _depth: int,
) -> List[FURequirement]:
    """
    Recursively decompose a FinishedGood to FU-level requirements.

    Uses path-based cycle detection (allows DAG patterns, catches true cycles).
    Returns FU-level data to preserve yield context for batch calculation.

    Args:
        fg_id: FinishedGood ID to decompose
        multiplier: Quantity multiplier from parent (accumulates through nesting)
        session: Database session
        _path: Set of FG IDs in current ancestry path (for cycle detection)
        _depth: Current nesting depth

    Returns:
        List of FURequirement objects for this FG subtree
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

        result: List[FURequirement] = []

        # Traverse components
        for comp in fg.components:
            # Calculate effective quantity at this level
            effective_qty = int(comp.component_quantity * multiplier)

            # Skip zero-quantity components
            if effective_qty <= 0:
                continue

            if comp.finished_unit_id is not None:
                # Atomic component: create FURequirement preserving FU identity
                fu = comp.finished_unit_component
                if fu is None:
                    raise ValidationError(
                        [f"FinishedUnit {comp.finished_unit_id} not found"]
                    )
                if fu.recipe is None:
                    raise ValidationError(
                        [f"FinishedUnit '{fu.display_name}' (id={fu.id}) has no recipe"]
                    )

                result.append(
                    FURequirement(
                        finished_unit=fu,
                        quantity_needed=effective_qty,
                        recipe=fu.recipe,
                    )
                )

            elif comp.finished_good_id is not None:
                # Nested bundle: recurse
                child_result = _decompose_fg_to_fus(
                    comp.finished_good_id,
                    effective_qty,
                    session,
                    _path,
                    _depth + 1,
                )
                # Extend with child results (no aggregation)
                result.extend(child_result)

            # else: packaging/material component - no recipe needed (skip)

        return result

    finally:
        # Clean up path when returning (backtracking)
        _path.discard(fg_id)
