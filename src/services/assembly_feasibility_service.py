"""
Assembly Feasibility Service for F076.

Calculates whether batch production decisions produce enough items to fulfill
finished goods requirements. Integrates with F072 bundle decomposition and
F073 batch decision service.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from dataclasses import dataclass
from typing import Dict, List

from sqlalchemy.orm import Session

from src.models import Event, EventFinishedGood, FinishedGood
from src.models.finished_unit import YieldMode
from src.services.database import session_scope
from src.services.exceptions import ValidationError


@dataclass
class ComponentStatus:
    """Status of a single FinishedUnit component."""

    finished_unit_id: int
    finished_unit_name: str
    quantity_needed: int
    quantity_available: int  # From batch decision yields
    is_sufficient: bool  # quantity_available >= quantity_needed


@dataclass
class FGFeasibilityStatus:
    """Feasibility status for one finished good."""

    finished_good_id: int
    finished_good_name: str
    quantity_needed: int  # From EventFinishedGood.quantity
    can_assemble: bool  # All components sufficient
    shortfall: int  # max(0, quantity_needed - achievable)
    components: List[ComponentStatus]  # FU components with status


@dataclass
class AssemblyFeasibilityResult:
    """Complete feasibility analysis for an event."""

    overall_feasible: bool  # All FGs can be assembled
    finished_goods: List[FGFeasibilityStatus]
    decided_count: int  # FUs with batch decisions
    total_fu_count: int  # Total FUs required


def _get_production_availability(
    event_id: int,
    session: Session,
) -> Dict[int, int]:
    """
    Build map of finished_unit_id → total_yield from batch decisions.

    Args:
        event_id: Event to analyze
        session: Database session

    Returns:
        Dict mapping finished_unit_id to total items that will be produced
    """
    from src.services.batch_decision_service import get_batch_decisions

    decisions = get_batch_decisions(event_id, session=session)

    availability: Dict[int, int] = {}
    for bd in decisions:
        fu = bd.finished_unit
        if fu is None:
            continue

        # Calculate yield per batch (match planning_service.py logic)
        yield_per_batch = fu.items_per_batch or 1
        if fu.yield_mode == YieldMode.BATCH_PORTION:
            yield_per_batch = 1

        total_yield = bd.batches * yield_per_batch

        # Accumulate (same FU may appear in multiple batch decisions)
        availability[fu.id] = availability.get(fu.id, 0) + total_yield

    return availability


def _calculate_fg_feasibility(
    fg_id: int,
    quantity_needed: int,
    availability: Dict[int, int],
    session: Session,
) -> FGFeasibilityStatus:
    """
    Calculate feasibility for one FinishedGood.

    Uses F072 decomposition to get FU requirements, then checks
    if production availability meets those requirements.

    Args:
        fg_id: FinishedGood ID to analyze
        quantity_needed: How many of this FG are needed
        availability: Map of FU ID to available quantity
        session: Database session

    Returns:
        FGFeasibilityStatus with component details
    """
    from src.services.planning_service import _decompose_fg_to_fus

    # Get FG for name
    fg = session.query(FinishedGood).filter(FinishedGood.id == fg_id).first()
fg_name = fg.display_name if fg else f"FG#{fg_id}"

    # Handle zero quantity as always feasible
    if quantity_needed <= 0:
        return FGFeasibilityStatus(
            finished_good_id=fg_id,
            finished_good_name=fg_name,
            quantity_needed=quantity_needed,
            can_assemble=True,
            shortfall=0,
            components=[],
        )

    # Decompose to FU requirements (handles bundles recursively)
    try:
        fu_requirements = _decompose_fg_to_fus(
            fg_id,
            quantity_needed,
            session,
            set(),  # Fresh path for cycle detection
            0,  # Start at depth 0
        )
    except Exception:
        # If decomposition fails, treat as infeasible
        return FGFeasibilityStatus(
            finished_good_id=fg_id,
            finished_good_name=fg_name,
            quantity_needed=quantity_needed,
            can_assemble=False,
            shortfall=quantity_needed,
            components=[],
        )

    # Handle FG with no components (packaging only)
    if not fu_requirements:
        return FGFeasibilityStatus(
            finished_good_id=fg_id,
            finished_good_name=fg_name,
            quantity_needed=quantity_needed,
            can_assemble=True,
            shortfall=0,
            components=[],
        )

    # Build component status list
    components: List[ComponentStatus] = []
    min_ratio = float("inf")  # Track limiting factor

    for fu_req in fu_requirements:
        fu = fu_req.finished_unit
        needed = fu_req.quantity_needed
        available = availability.get(fu.id, 0)
        is_sufficient = available >= needed

        components.append(
            ComponentStatus(
                finished_unit_id=fu.id,
                finished_unit_name=fu.display_name,
                quantity_needed=needed,
                quantity_available=available,
                is_sufficient=is_sufficient,
            )
        )

        # Track ratio for shortfall calculation
        if needed > 0:
            ratio = available / needed
            min_ratio = min(min_ratio, ratio)

    # Determine overall feasibility
    can_assemble = all(c.is_sufficient for c in components)

    # Calculate shortfall (how many FGs we can't make)
    if min_ratio == float("inf"):
        shortfall = 0  # No components needed
    elif min_ratio >= 1.0:
        shortfall = 0  # Can make all
    else:
        # Shortfall = needed - (what we can actually make)
        achievable = int(quantity_needed * min_ratio)
        shortfall = quantity_needed - achievable

    return FGFeasibilityStatus(
        finished_good_id=fg_id,
        finished_good_name=fg_name,
        quantity_needed=quantity_needed,
        can_assemble=can_assemble,
        shortfall=shortfall,
        components=components,
    )


def _calculate_assembly_feasibility_impl(
    event_id: int,
    session: Session,
) -> AssemblyFeasibilityResult:
    """Internal implementation of calculate_assembly_feasibility."""
    from src.services.planning_service import decompose_event_to_fu_requirements

    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise ValidationError([f"Event {event_id} not found"])

    # Get production availability from batch decisions
    availability = _get_production_availability(event_id, session)

    # Get FG selections for this event
    efgs = (
        session.query(EventFinishedGood)
        .filter(EventFinishedGood.event_id == event_id)
        .all()
    )

    # Handle empty event
    if not efgs:
        return AssemblyFeasibilityResult(
            overall_feasible=True,
            finished_goods=[],
            decided_count=0,
            total_fu_count=0,
        )

    # Calculate feasibility for each FG
    fg_statuses: List[FGFeasibilityStatus] = []
    for efg in efgs:
        status = _calculate_fg_feasibility(
            efg.finished_good_id,
            efg.quantity,
            availability,
            session,
        )
        fg_statuses.append(status)

    # Determine overall feasibility
    overall_feasible = all(fg.can_assemble for fg in fg_statuses)

    # Count FU decision coverage
    fu_requirements = decompose_event_to_fu_requirements(event_id, session=session)
    total_fu_count = len(fu_requirements)
    unique_fu_ids = {req.finished_unit.id for req in fu_requirements}
    decided_count = len(unique_fu_ids & set(availability.keys()))

    return AssemblyFeasibilityResult(
        overall_feasible=overall_feasible,
        finished_goods=fg_statuses,
        decided_count=decided_count,
        total_fu_count=total_fu_count,
    )


def calculate_assembly_feasibility(
    event_id: int,
    session: Session = None,
) -> AssemblyFeasibilityResult:
    """
    Calculate assembly feasibility for all FGs in an event.

    Analyzes whether the batch production decisions produce enough items
    to fulfill the finished goods requirements. For bundles, validates
    all component availability recursively.

    Args:
        event_id: Event to analyze
        session: Optional session for transaction sharing

    Returns:
        AssemblyFeasibilityResult with per-FG status and overall feasibility

    Raises:
        ValidationError: If event not found
    """
    if session is not None:
        return _calculate_assembly_feasibility_impl(event_id, session)
    with session_scope() as session:
        return _calculate_assembly_feasibility_impl(event_id, session)
