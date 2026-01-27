"""
Planning Service for F072 Recipe Decomposition & Aggregation (F073 Enhanced).

Provides FinishedUnit-level requirement decomposition for event planning:
- Recursive bundle decomposition with quantity tracking
- FU-level data preservation (not recipe-level aggregation)
- Cycle detection and depth limiting
- Batch option calculation (floor/ceil options with shortfall flags)

F073 Change: Returns List[FURequirement] instead of Dict[Recipe, int]
to preserve FU-level yield context for batch calculation.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

import math
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
from src.models.finished_unit import YieldMode


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


# =============================================================================
# F073 WP02: Batch Calculation
# =============================================================================


@dataclass
class BatchOption:
    """One batch option for user selection.

    Represents either a floor option (may shortfall) or ceil option (meets/exceeds).
    """

    batches: int  # Number of batches to make
    total_yield: int  # batches * yield_per_batch
    quantity_needed: int  # From FURequirement.quantity_needed
    difference: int  # total_yield - quantity_needed
    is_shortfall: bool  # difference < 0
    is_exact_match: bool  # difference == 0
    yield_per_batch: int  # From FinishedUnit (for display)


@dataclass
class BatchOptionsResult:
    """Batch options for one FinishedUnit.

    Contains all the context needed for UI display plus the calculated options.
    """

    finished_unit_id: int
    finished_unit_name: str
    recipe_id: int
    recipe_name: str
    quantity_needed: int
    yield_per_batch: int
    yield_mode: str  # "discrete_count" or "batch_portion"
    item_unit: str  # "cookie", "cake", etc.
    options: List[BatchOption]


def calculate_batch_options_for_fu(
    finished_unit: FinishedUnit,
    quantity_needed: int,
) -> List[BatchOption]:
    """
    Calculate floor/ceil batch options for a single FinishedUnit.

    Args:
        finished_unit: The FU to calculate for
        quantity_needed: How many items/portions needed

    Returns:
        List of 0-2 BatchOptions:
        - Empty if quantity_needed <= 0 or invalid yield
        - One option if floor == ceil (exact division)
        - Two options otherwise (floor may shortfall, ceil meets/exceeds)
    """
    if quantity_needed <= 0:
        return []

    # Use existing method to get raw batch count
    raw_batches = finished_unit.calculate_batches_needed(quantity_needed)

    if raw_batches <= 0:
        return []

    # Determine yield per batch based on mode
    yield_per_batch = finished_unit.items_per_batch or 1
    if finished_unit.yield_mode == YieldMode.BATCH_PORTION:
        yield_per_batch = 1  # One batch = one portion

    # Guard against invalid yield configuration
    if yield_per_batch <= 0:
        return []

    options = []

    # Floor option (may shortfall)
    floor_batches = math.floor(raw_batches)
    if floor_batches > 0:
        floor_yield = floor_batches * yield_per_batch
        floor_diff = floor_yield - quantity_needed
        options.append(
            BatchOption(
                batches=floor_batches,
                total_yield=floor_yield,
                quantity_needed=quantity_needed,
                difference=floor_diff,
                is_shortfall=floor_diff < 0,
                is_exact_match=floor_diff == 0,
                yield_per_batch=yield_per_batch,
            )
        )

    # Ceil option (if different from floor)
    ceil_batches = math.ceil(raw_batches)
    if ceil_batches != floor_batches:
        ceil_yield = ceil_batches * yield_per_batch
        ceil_diff = ceil_yield - quantity_needed
        options.append(
            BatchOption(
                batches=ceil_batches,
                total_yield=ceil_yield,
                quantity_needed=quantity_needed,
                difference=ceil_diff,
                is_shortfall=False,  # Ceil never shortfalls
                is_exact_match=ceil_diff == 0,
                yield_per_batch=yield_per_batch,
            )
        )

    return options


def calculate_batch_options(
    event_id: int,
    session: Session = None,
) -> List[BatchOptionsResult]:
    """
    Calculate batch options for all FUs in an event.

    Uses decompose_event_to_fu_requirements() to get FU-level data,
    then calculates floor/ceil options for each.

    Args:
        event_id: The Event to calculate for
        session: Optional session for transaction sharing

    Returns:
        List of BatchOptionsResult, one per FURequirement from F072

    Raises:
        ValidationError: If event not found
    """
    if session is not None:
        return _calculate_batch_options_impl(event_id, session)
    with session_scope() as session:
        return _calculate_batch_options_impl(event_id, session)


def _calculate_batch_options_impl(
    event_id: int,
    session: Session,
) -> List[BatchOptionsResult]:
    """Implementation of calculate_batch_options."""
    # Get FU-level requirements from F072
    fu_requirements = decompose_event_to_fu_requirements(event_id, session=session)

    results = []
    for fu_req in fu_requirements:
        fu = fu_req.finished_unit
        recipe = fu_req.recipe

        # Calculate options for this FU
        options = calculate_batch_options_for_fu(fu, fu_req.quantity_needed)

        # Determine yield per batch for display
        yield_per_batch = fu.items_per_batch or 1
        if fu.yield_mode == YieldMode.BATCH_PORTION:
            yield_per_batch = 1

        results.append(
            BatchOptionsResult(
                finished_unit_id=fu.id,
                finished_unit_name=fu.display_name,
                recipe_id=recipe.id,
                recipe_name=recipe.name,
                quantity_needed=fu_req.quantity_needed,
                yield_per_batch=yield_per_batch,
                yield_mode=fu.yield_mode.value if fu.yield_mode else "discrete_count",
                item_unit=fu.item_unit or "item",
                options=options,
            )
        )

    return results
