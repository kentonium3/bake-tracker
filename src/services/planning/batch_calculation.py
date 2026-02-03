"""
Batch calculation service for production planning (Feature 039).

This module provides functions for:
- Calculating batch counts that ALWAYS round up (never short)
- Calculating waste percentage for each recipe
- Exploding bundle requirements to unit quantities
- Aggregating FinishedUnits by recipe
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session

from src.models import FinishedGood, FinishedUnit, Recipe, Composition
from src.services.database import session_scope
from src.services import recipe_service


@dataclass
class RecipeBatchResult:
    """Result of batch calculation for a single recipe.

    Attributes:
        recipe_id: The recipe ID
        recipe_name: The recipe display name
        units_needed: Total FinishedUnits required
        batches: Number of batches to produce (always rounded UP)
        yield_per_batch: Units produced per batch
        total_yield: Total units that will be produced (batches * yield_per_batch)
        waste_units: Units produced beyond what's needed (total_yield - units_needed)
        waste_percent: Percentage of total yield that is waste
    """

    recipe_id: int
    recipe_name: str
    units_needed: int
    batches: int
    yield_per_batch: int
    total_yield: int
    waste_units: int
    waste_percent: float


def calculate_batches(units_needed: int, yield_per_batch: int) -> int:
    """Calculate batches needed. Always rounds UP to prevent shortfall.

    Transaction boundary: Pure computation (no database access).
    Calculates required batch count from units and yield.

    This is the core calculation function that ensures we NEVER produce
    fewer units than required. Uses math.ceil() exclusively.

    Args:
        units_needed: Total units required
        yield_per_batch: Number of units produced per batch

    Returns:
        Number of batches to produce (always >= 1 if units_needed > 0)

    Raises:
        ValueError: If yield_per_batch is <= 0

    Examples:
        >>> calculate_batches(48, 48)  # Exact fit
        1
        >>> calculate_batches(49, 48)  # Needs 2 batches
        2
        >>> calculate_batches(300, 48)  # 300/48 = 6.25 -> 7
        7
    """
    if yield_per_batch <= 0:
        raise ValueError("yield_per_batch must be greater than 0")

    if units_needed <= 0:
        return 0

    return math.ceil(units_needed / yield_per_batch)


def calculate_waste(units_needed: int, batches: int, yield_per_batch: int) -> tuple[int, float]:
    """Calculate waste units and percentage.

    Transaction boundary: Pure computation (no database access).
    Calculates excess production from batch rounding.

    Waste is the number of units produced beyond what is needed.
    Waste percentage is relative to total yield, not units needed.

    Args:
        units_needed: Total units required
        batches: Number of batches being produced
        yield_per_batch: Units produced per batch

    Returns:
        Tuple of (waste_units, waste_percent)
        - waste_units: Absolute number of extra units
        - waste_percent: Percentage of total yield that is waste (0-100)

    Examples:
        >>> calculate_waste(48, 1, 48)  # Zero waste
        (0, 0.0)
        >>> calculate_waste(49, 2, 48)  # 96 - 49 = 47 waste
        (47, 48.958...)
    """
    total_yield = batches * yield_per_batch
    waste_units = total_yield - units_needed

    if total_yield > 0:
        waste_percent = (waste_units / total_yield) * 100
    else:
        waste_percent = 0.0

    return waste_units, waste_percent


def create_batch_result(
    recipe_id: int,
    recipe_name: str,
    units_needed: int,
    yield_per_batch: int,
) -> RecipeBatchResult:
    """Create a RecipeBatchResult with all calculations performed.

    Transaction boundary: Pure computation (no database access).
    Combines calculate_batches() and calculate_waste() results.

    This is a convenience function that combines calculate_batches()
    and calculate_waste() to produce a complete result.

    Args:
        recipe_id: The recipe ID
        recipe_name: The recipe display name
        units_needed: Total FinishedUnits required
        yield_per_batch: Units produced per batch

    Returns:
        RecipeBatchResult with all fields populated
    """
    batches = calculate_batches(units_needed, yield_per_batch)
    total_yield = batches * yield_per_batch
    waste_units, waste_percent = calculate_waste(units_needed, batches, yield_per_batch)

    return RecipeBatchResult(
        recipe_id=recipe_id,
        recipe_name=recipe_name,
        units_needed=units_needed,
        batches=batches,
        yield_per_batch=yield_per_batch,
        total_yield=total_yield,
        waste_units=waste_units,
        waste_percent=waste_percent,
    )


def explode_bundle_requirements(
    finished_good_id: int,
    bundle_quantity: int,
    session: Session,
    *,
    _visited: Optional[Set[int]] = None,
) -> Dict[int, int]:
    """Explode bundle to component FinishedUnit quantities.

    Transaction boundary: Inherits session from caller (required parameter).
    Read-only recursive query within the caller's transaction scope.
    Queries FinishedGood and Composition tables recursively.

    Takes a FinishedGood (bundle) and quantity, and recursively expands
    all component FinishedUnits with their total quantities.

    Args:
        finished_good_id: The bundle (FinishedGood) ID
        bundle_quantity: How many bundles needed
        session: Database session
        _visited: Internal set for cycle detection (do not pass)

    Returns:
        Dict mapping finished_unit_id -> total quantity needed

    Raises:
        ValueError: If circular reference detected in bundle structure

    Example:
        If bundle A contains:
        - 3x Cookie (FinishedUnit id=1)
        - 2x Brownie (FinishedUnit id=2)
        - 1x Bundle B (FinishedGood)

        And Bundle B contains:
        - 2x Cookie (FinishedUnit id=1)

        Then explode_bundle_requirements(A.id, 10, session) returns:
        {1: 50, 2: 20}  # (3*10 + 2*10) cookies, 2*10 brownies
    """
    # Initialize cycle detection set
    if _visited is None:
        _visited = set()

    # Check for circular reference
    if finished_good_id in _visited:
        raise ValueError(
            f"Circular reference detected: FinishedGood {finished_good_id} "
            f"appears in its own composition hierarchy"
        )

    _visited.add(finished_good_id)

    # Query the FinishedGood to get its components
    finished_good = session.get(FinishedGood, finished_good_id)
    if finished_good is None:
        return {}

    # Aggregate FinishedUnit quantities
    result: Dict[int, int] = {}

    # Query Composition records for this FinishedGood (assembly)
    compositions = (
        session.query(Composition).filter(Composition.assembly_id == finished_good_id).all()
    )

    for comp in compositions:
        component_qty = comp.component_quantity * bundle_quantity

        if comp.finished_unit_id is not None:
            # Direct FinishedUnit component
            component_qty_int = int(component_qty)
            if comp.finished_unit_id in result:
                result[comp.finished_unit_id] += component_qty_int
            else:
                result[comp.finished_unit_id] = component_qty_int

        elif comp.finished_good_id is not None:
            # Nested FinishedGood - recursively explode
            nested_units = explode_bundle_requirements(
                comp.finished_good_id,
                int(component_qty),
                session,
                _visited=_visited.copy(),  # Copy to allow parallel branches
            )
            for unit_id, qty in nested_units.items():
                if unit_id in result:
                    result[unit_id] += qty
                else:
                    result[unit_id] = qty

    return result


def aggregate_by_recipe(
    unit_quantities: Dict[int, int],
    session: Session,
) -> List[RecipeBatchResult]:
    """Aggregate FinishedUnit quantities by recipe.

    Transaction boundary: Inherits session from caller (required parameter).
    Read-only queries within the caller's transaction scope.
    Queries FinishedUnit, Recipe tables to group quantities.

    Takes a mapping of FinishedUnit IDs to quantities and groups them
    by their associated recipes, producing batch calculations for each.

    Args:
        unit_quantities: Dict of finished_unit_id -> quantity needed
        session: Database session

    Returns:
        List of RecipeBatchResult for each unique recipe

    Raises:
        ValueError: If a FinishedUnit has no associated recipe

    Example:
        If unit_quantities = {1: 100, 2: 50} and:
        - Unit 1 uses Recipe A (yield 48)
        - Unit 2 uses Recipe A (yield 48)

        Result aggregates both to Recipe A needing 150 units:
        [RecipeBatchResult(recipe_id=A.id, units_needed=150, batches=4, ...)]
    """
    if not unit_quantities:
        return []

    # Group quantities by recipe_id
    recipe_quantities: Dict[int, int] = {}
    recipe_info: Dict[int, tuple[str, int]] = {}  # recipe_id -> (name, yield)

    for finished_unit_id, quantity in unit_quantities.items():
        finished_unit = session.get(FinishedUnit, finished_unit_id)
        if finished_unit is None:
            continue

        if finished_unit.recipe_id is None:
            raise ValueError(
                f"FinishedUnit {finished_unit_id} ('{finished_unit.display_name}') "
                f"has no associated recipe"
            )

        recipe_id = finished_unit.recipe_id

        # Aggregate quantities for same recipe
        if recipe_id in recipe_quantities:
            recipe_quantities[recipe_id] += quantity
        else:
            recipe_quantities[recipe_id] = quantity

            # Cache recipe info on first encounter
            recipe = session.get(Recipe, recipe_id)
            if recipe:
                # F066: Use get_finished_units() primitive for decoupled yield access
                items_per_batch = 1
                finished_units = recipe_service.get_finished_units(recipe_id, session=session)
                if finished_units:
                    primary_unit = finished_units[0]
                    if primary_unit["items_per_batch"] and primary_unit["items_per_batch"] > 0:
                        items_per_batch = primary_unit["items_per_batch"]
                recipe_info[recipe_id] = (
                    recipe.name,
                    items_per_batch,
                )

    # Create RecipeBatchResult for each recipe
    results = []
    for recipe_id, units_needed in recipe_quantities.items():
        if recipe_id in recipe_info:
            recipe_name, yield_per_batch = recipe_info[recipe_id]
            result = create_batch_result(
                recipe_id=recipe_id,
                recipe_name=recipe_name,
                units_needed=units_needed,
                yield_per_batch=yield_per_batch,
            )
            results.append(result)

    return results


def calculate_event_batch_requirements(
    event_bundle_requirements: Dict[int, int],
    *,
    session: Optional[Session] = None,
) -> List[RecipeBatchResult]:
    """Calculate batch requirements for an event's bundle requirements.

    Transaction boundary: Read-only operation.
    Explodes bundles and aggregates batch requirements by recipe.

    This is the main entry point for batch calculation. Takes a mapping
    of FinishedGood IDs to quantities (from event requirements) and
    produces recipe batch calculations.

    Args:
        event_bundle_requirements: Dict of finished_good_id -> quantity needed
        session: Optional database session

    Returns:
        List of RecipeBatchResult for all recipes needed

    Example:
        Given event needs:
        - 50x "Holiday Gift Bag" (FinishedGood id=1)
        - 30x "Cookie Sampler" (FinishedGood id=2)

        Returns recipe batch calculations for all component recipes.
    """
    if session is not None:
        return _calculate_event_batch_requirements_impl(event_bundle_requirements, session)
    with session_scope() as session:
        return _calculate_event_batch_requirements_impl(event_bundle_requirements, session)


def _calculate_event_batch_requirements_impl(
    event_bundle_requirements: Dict[int, int],
    session: Session,
) -> List[RecipeBatchResult]:
    """Implementation of calculate_event_batch_requirements.

    Transaction boundary: Inherits session from caller.
    Read-only computation within the caller's transaction scope.
    """
    # Aggregate all FinishedUnit quantities across all bundles
    all_unit_quantities: Dict[int, int] = {}

    for finished_good_id, quantity in event_bundle_requirements.items():
        unit_quantities = explode_bundle_requirements(finished_good_id, quantity, session)
        for unit_id, unit_qty in unit_quantities.items():
            if unit_id in all_unit_quantities:
                all_unit_quantities[unit_id] += unit_qty
            else:
                all_unit_quantities[unit_id] = unit_qty

    # Aggregate by recipe and calculate batches
    return aggregate_by_recipe(all_unit_quantities, session)
