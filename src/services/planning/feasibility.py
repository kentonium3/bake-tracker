"""
Feasibility service for production planning (Feature 039).

This module provides functions for:
- Checking production feasibility (ingredient availability for recipes)
- Checking assembly feasibility (component availability for bundles)
- Supporting partial assembly calculations
- Returning structured DTOs for UI consumption

The service wraps existing services:
- batch_production_service.check_can_produce() for production checks
- assembly_service.check_can_assemble() for assembly checks
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import (
    EventAssemblyTarget,
    EventProductionTarget,
    FinishedGood,
    Composition,
    FinishedUnit,
)
from src.services.database import session_scope
from src.services import assembly_service, batch_production_service
from src.services.assembly_service import FinishedGoodNotFoundError


class FeasibilityStatus(Enum):
    """Status of feasibility check for assembly.

    Values:
        CAN_ASSEMBLE: All components available, can fully meet target
        PARTIAL: Some components available, can partially assemble
        CANNOT_ASSEMBLE: Cannot assemble (no components or blocking issues)
        AWAITING_PRODUCTION: Components not ready; production incomplete
    """

    CAN_ASSEMBLE = "can_assemble"
    PARTIAL = "partial"
    CANNOT_ASSEMBLE = "cannot_assemble"
    AWAITING_PRODUCTION = "awaiting_production"


@dataclass
class FeasibilityResult:
    """Result of assembly feasibility check.

    Attributes:
        finished_good_id: ID of the FinishedGood being checked
        finished_good_name: Display name of the FinishedGood
        target_quantity: How many are needed/targeted
        can_assemble: How many CAN be assembled with current inventory
        status: FeasibilityStatus enum value
        missing_components: List of components that are short
    """

    finished_good_id: int
    finished_good_name: str
    target_quantity: int
    can_assemble: int
    status: FeasibilityStatus
    missing_components: List[Dict[str, Any]]


def check_production_feasibility(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Check production feasibility for all production targets of an event.

    Wraps batch_production_service.check_can_produce() for each EventProductionTarget
    to determine if recipes can be produced with current inventory.

    Args:
        event_id: Event to check production targets for
        session: Optional database session

    Returns:
        List of dicts with:
            - recipe_id: int
            - recipe_name: str
            - target_batches: int
            - can_produce: bool
            - missing: List[Dict] with ingredient details if not feasible
    """
    if session is not None:
        return _check_production_feasibility_impl(event_id, session)
    with session_scope() as session:
        return _check_production_feasibility_impl(event_id, session)


def _check_production_feasibility_impl(
    event_id: int,
    session: Session,
) -> List[Dict[str, Any]]:
    """Implementation of check_production_feasibility."""
    # Query all production targets for this event
    targets = (
        session.query(EventProductionTarget)
        .filter(EventProductionTarget.event_id == event_id)
        .all()
    )

    results = []

    for target in targets:
        # Get recipe name
        recipe_name = target.recipe.name if target.recipe else f"Recipe {target.recipe_id}"

        # Use existing check_can_produce with session passed through
        check_result = batch_production_service.check_can_produce(
            target.recipe_id,
            target.target_batches,
            session=session,
        )

        results.append({
            "recipe_id": target.recipe_id,
            "recipe_name": recipe_name,
            "target_batches": target.target_batches,
            "can_produce": check_result["can_produce"],
            "missing": check_result["missing"],
        })

    return results


def check_assembly_feasibility(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> List[FeasibilityResult]:
    """Check assembly feasibility for all assembly targets of an event.

    Wraps assembly_service.check_can_assemble() for each EventAssemblyTarget
    to determine if bundles can be assembled with current inventory.

    Supports partial assembly: calculates how many complete units can be
    assembled even if the full target cannot be met.

    Args:
        event_id: Event to check assembly targets for
        session: Optional database session

    Returns:
        List of FeasibilityResult for each assembly target
    """
    if session is not None:
        return _check_assembly_feasibility_impl(event_id, session)
    with session_scope() as session:
        return _check_assembly_feasibility_impl(event_id, session)


def _check_assembly_feasibility_impl(
    event_id: int,
    session: Session,
) -> List[FeasibilityResult]:
    """Implementation of check_assembly_feasibility."""
    # Query all assembly targets for this event
    targets = (
        session.query(EventAssemblyTarget)
        .filter(EventAssemblyTarget.event_id == event_id)
        .all()
    )

    results = []

    for target in targets:
        # Get finished good name
        finished_good = session.get(FinishedGood, target.finished_good_id)
        fg_name = finished_good.display_name if finished_good else f"FinishedGood {target.finished_good_id}"

        # Calculate how many can actually be assembled
        can_assemble_count = _calculate_max_assemblable(
            target.finished_good_id,
            target.target_quantity,
            session,
        )

        # Check if fully achievable using existing service
        check_result = assembly_service.check_can_assemble(
            target.finished_good_id,
            target.target_quantity,
            session=session,
        )

        # Determine status based on can_assemble count and other factors
        status = _determine_feasibility_status(
            can_assemble_count,
            target.target_quantity,
            check_result,
            target.finished_good_id,
            session,
        )

        results.append(FeasibilityResult(
            finished_good_id=target.finished_good_id,
            finished_good_name=fg_name,
            target_quantity=target.target_quantity,
            can_assemble=can_assemble_count,
            status=status,
            missing_components=check_result["missing"],
        ))

    return results


def _calculate_max_assemblable(
    finished_good_id: int,
    target_quantity: int,
    session: Session,
) -> int:
    """Calculate maximum number of units that can be assembled.

    Uses binary search approach: check decreasing quantities until we find
    the maximum that can be assembled. Also checks component availability
    directly to calculate the mathematical maximum.

    Args:
        finished_good_id: The bundle to check
        target_quantity: The target we're trying to reach
        session: Database session

    Returns:
        Maximum number that can be assembled (0 to target_quantity)
    """
    # First check if we can fully assemble
    check_result = assembly_service.check_can_assemble(
        finished_good_id, target_quantity, session=session
    )

    if check_result["can_assemble"]:
        return target_quantity

    # If not, calculate the maximum based on component availability
    # Get compositions for this finished good
    compositions = (
        session.query(Composition)
        .filter(Composition.assembly_id == finished_good_id)
        .all()
    )

    if not compositions:
        return 0

    max_assemblable = target_quantity  # Start with target as upper bound

    for comp in compositions:
        if comp.component_quantity <= 0:
            # Guard against division by zero
            continue

        available = 0
        needed_per_unit = int(comp.component_quantity)

        if comp.finished_unit_id:
            # FinishedUnit component
            fu = session.get(FinishedUnit, comp.finished_unit_id)
            if fu:
                available = fu.inventory_count
        elif comp.finished_good_id:
            # Nested FinishedGood component
            nested_fg = session.get(FinishedGood, comp.finished_good_id)
            if nested_fg:
                available = nested_fg.inventory_count
        elif comp.packaging_product_id:
            # Packaging is more complex - we'd need to check FIFO inventory
            # For now, if the full check failed due to packaging, we limit to 0
            # for that component. The assembly_service already handles this.
            # Skip packaging in max calculation - assembly_service handles it
            continue

        if needed_per_unit > 0:
            # How many complete units can this component support?
            component_max = available // needed_per_unit
            max_assemblable = min(max_assemblable, component_max)

    return max(0, max_assemblable)


def _determine_feasibility_status(
    can_assemble_count: int,
    target_quantity: int,
    check_result: Dict[str, Any],
    finished_good_id: int,
    session: Session,
) -> FeasibilityStatus:
    """Determine the appropriate FeasibilityStatus.

    Status logic:
    - CAN_ASSEMBLE: can_assemble >= target
    - PARTIAL: 0 < can_assemble < target
    - AWAITING_PRODUCTION: can_assemble == 0 and production is incomplete
    - CANNOT_ASSEMBLE: can_assemble == 0 and production is complete

    Args:
        can_assemble_count: How many can be assembled
        target_quantity: How many are targeted
        check_result: Result from assembly_service.check_can_assemble
        finished_good_id: The finished good being checked
        session: Database session

    Returns:
        Appropriate FeasibilityStatus enum value
    """
    if can_assemble_count >= target_quantity:
        return FeasibilityStatus.CAN_ASSEMBLE

    if can_assemble_count > 0:
        return FeasibilityStatus.PARTIAL

    # can_assemble_count == 0
    # Check if this is because production isn't complete
    # (components are FinishedUnits that need to be produced)
    production_incomplete = _check_production_incomplete(finished_good_id, session)

    if production_incomplete:
        return FeasibilityStatus.AWAITING_PRODUCTION

    return FeasibilityStatus.CANNOT_ASSEMBLE


def _check_production_incomplete(
    finished_good_id: int,
    session: Session,
) -> bool:
    """Check if production is incomplete for a finished good's components.

    This checks if any FinishedUnit components have zero inventory,
    suggesting that production hasn't happened yet.

    Args:
        finished_good_id: The finished good to check
        session: Database session

    Returns:
        True if production appears to be incomplete, False otherwise
    """
    # Get compositions with FinishedUnit components
    compositions = (
        session.query(Composition)
        .filter(Composition.assembly_id == finished_good_id)
        .filter(Composition.finished_unit_id.isnot(None))
        .all()
    )

    for comp in compositions:
        fu = session.get(FinishedUnit, comp.finished_unit_id)
        if fu and fu.inventory_count == 0:
            # At least one FinishedUnit has zero inventory
            # This suggests production hasn't happened
            return True

    return False


def check_single_assembly_feasibility(
    finished_good_id: int,
    quantity: int,
    *,
    session: Optional[Session] = None,
) -> FeasibilityResult:
    """Check assembly feasibility for a single finished good.

    Convenience function for checking a single assembly without
    requiring an EventAssemblyTarget.

    Args:
        finished_good_id: The finished good to check
        quantity: Target quantity to check
        session: Optional database session

    Returns:
        FeasibilityResult for this finished good
    """
    if session is not None:
        return _check_single_assembly_impl(finished_good_id, quantity, session)
    with session_scope() as session:
        return _check_single_assembly_impl(finished_good_id, quantity, session)


def _check_single_assembly_impl(
    finished_good_id: int,
    quantity: int,
    session: Session,
) -> FeasibilityResult:
    """Implementation of check_single_assembly_feasibility."""
    # Get finished good name
    finished_good = session.get(FinishedGood, finished_good_id)
    fg_name = finished_good.display_name if finished_good else f"FinishedGood {finished_good_id}"

    # Handle nonexistent finished good gracefully
    if finished_good is None:
        return FeasibilityResult(
            finished_good_id=finished_good_id,
            finished_good_name=fg_name,
            target_quantity=quantity,
            can_assemble=0,
            status=FeasibilityStatus.CANNOT_ASSEMBLE,
            missing_components=[],
        )

    # Calculate how many can be assembled
    can_assemble_count = _calculate_max_assemblable(
        finished_good_id, quantity, session
    )

    # Check full feasibility
    try:
        check_result = assembly_service.check_can_assemble(
            finished_good_id, quantity, session=session
        )
    except FinishedGoodNotFoundError:
        # Shouldn't happen since we checked above, but handle gracefully
        return FeasibilityResult(
            finished_good_id=finished_good_id,
            finished_good_name=fg_name,
            target_quantity=quantity,
            can_assemble=0,
            status=FeasibilityStatus.CANNOT_ASSEMBLE,
            missing_components=[],
        )

    # Determine status
    status = _determine_feasibility_status(
        can_assemble_count, quantity, check_result, finished_good_id, session
    )

    return FeasibilityResult(
        finished_good_id=finished_good_id,
        finished_good_name=fg_name,
        target_quantity=quantity,
        can_assemble=can_assemble_count,
        status=status,
        missing_components=check_result["missing"],
    )
