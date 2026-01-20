"""
Progress tracking service for production planning (Feature 039).

This module provides functions for:
- Tracking production progress per recipe (batches complete vs target)
- Tracking assembly progress per bundle (assembled vs target)
- Calculating overall event progress
- Providing structured DTOs for UI consumption

Wraps existing event_service progress functions and transforms
results into standardized DTOs per the planning service contract.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.services.database import session_scope
from src.services import event_service
from src.services.planning import feasibility


@dataclass
class ProductionProgress:
    """Progress for a single recipe target.

    Attributes:
        recipe_id: The recipe ID
        recipe_name: The recipe display name
        target_batches: Number of batches planned to produce
        completed_batches: Number of batches actually produced
        progress_percent: Percentage complete (0-100+, can exceed 100%)
        is_complete: True if completed_batches >= target_batches
    """

    recipe_id: int
    recipe_name: str
    target_batches: int
    completed_batches: int
    progress_percent: float
    is_complete: bool


@dataclass
class AssemblyProgress:
    """Progress for a single assembly target.

    Attributes:
        finished_good_id: The finished good ID
        finished_good_name: The finished good display name
        target_quantity: Number of units planned to assemble
        assembled_quantity: Number of units actually assembled
        available_to_assemble: How many more can be assembled (from feasibility)
        progress_percent: Percentage complete (0-100+, can exceed 100%)
        is_complete: True if assembled_quantity >= target_quantity
    """

    finished_good_id: int
    finished_good_name: str
    target_quantity: int
    assembled_quantity: int
    available_to_assemble: int
    progress_percent: float
    is_complete: bool


def get_production_progress(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> List[ProductionProgress]:
    """Get production progress for all recipe targets.

    Wraps event_service.get_production_progress() and transforms
    the results into ProductionProgress DTOs.

    Args:
        event_id: Event to get progress for
        session: Optional database session

    Returns:
        List of ProductionProgress DTOs
    """
    if session is not None:
        return _get_production_progress_impl(event_id, session)
    with session_scope() as session:
        return _get_production_progress_impl(event_id, session)


def _get_production_progress_impl(
    event_id: int,
    session: Session,
) -> List[ProductionProgress]:
    """Implementation of get_production_progress."""
    # Get raw progress data from event_service
    # Pass session to allow transactional atomicity with caller
    raw_progress = event_service.get_production_progress(event_id, session=session)

    results = []
    for item in raw_progress:
        target = item["target_batches"]
        completed = item["produced_batches"]

        # Calculate progress percentage (guard against zero division)
        if target > 0:
            progress_percent = round((completed / target) * 100, 2)
        else:
            progress_percent = 0.0

        results.append(
            ProductionProgress(
                recipe_id=item["recipe_id"],
                recipe_name=item["recipe_name"],
                target_batches=target,
                completed_batches=completed,
                progress_percent=progress_percent,
                is_complete=completed >= target,
            )
        )

    return results


def get_assembly_progress(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> List[AssemblyProgress]:
    """Get assembly progress for all finished good targets.

    Wraps event_service.get_assembly_progress() and transforms
    the results into AssemblyProgress DTOs.

    Args:
        event_id: Event to get progress for
        session: Optional database session

    Returns:
        List of AssemblyProgress DTOs
    """
    if session is not None:
        return _get_assembly_progress_impl(event_id, session)
    with session_scope() as session:
        return _get_assembly_progress_impl(event_id, session)


def _get_assembly_progress_impl(
    event_id: int,
    session: Session,
) -> List[AssemblyProgress]:
    """Implementation of get_assembly_progress."""
    # Get raw progress data from event_service
    # Pass session to allow transactional atomicity with caller
    raw_progress = event_service.get_assembly_progress(event_id, session=session)

    # Get feasibility data to calculate available_to_assemble
    # Build a lookup dict by finished_good_id for efficiency
    feasibility_results = feasibility.check_assembly_feasibility(event_id, session=session)
    feasibility_by_fg_id = {
        fr.finished_good_id: fr.can_assemble
        for fr in feasibility_results
    }

    results = []
    for item in raw_progress:
        target = item["target_quantity"]
        assembled = item["assembled_quantity"]
        finished_good_id = item["finished_good_id"]

        # Calculate progress percentage (guard against zero division)
        if target > 0:
            progress_percent = round((assembled / target) * 100, 2)
        else:
            progress_percent = 0.0

        # Get available_to_assemble from feasibility service
        # This shows how many MORE can be assembled with current inventory
        available_to_assemble = feasibility_by_fg_id.get(finished_good_id, 0)

        results.append(
            AssemblyProgress(
                finished_good_id=finished_good_id,
                finished_good_name=item["finished_good_name"],
                target_quantity=target,
                assembled_quantity=assembled,
                available_to_assemble=available_to_assemble,
                progress_percent=progress_percent,
                is_complete=assembled >= target,
            )
        )

    return results


def get_overall_progress(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Get overall event progress summary.

    Calculates aggregate progress across all production and assembly targets.

    Args:
        event_id: Event to get progress for
        session: Optional database session

    Returns:
        Dict with:
        - production_percent: Average progress across all recipes (0-100)
        - assembly_percent: Average progress across all bundles (0-100)
        - overall_percent: Combined average ((production + assembly) / 2)
        - status: One of "not_started", "in_progress", "complete"
        - production_targets: Number of production targets
        - production_complete: Number of completed production targets
        - assembly_targets: Number of assembly targets
        - assembly_complete: Number of completed assembly targets
    """
    if session is not None:
        return _get_overall_progress_impl(event_id, session)
    with session_scope() as session:
        return _get_overall_progress_impl(event_id, session)


def _get_overall_progress_impl(
    event_id: int,
    session: Session,
) -> Dict[str, Any]:
    """Implementation of get_overall_progress."""
    # Get individual progress lists
    production_progress = get_production_progress(event_id, session=session)
    assembly_progress = get_assembly_progress(event_id, session=session)

    # Calculate production progress
    production_targets = len(production_progress)
    production_complete = sum(1 for p in production_progress if p.is_complete)

    if production_targets > 0:
        # Average of individual progress percentages (capped at 100 for average)
        production_percent = round(
            sum(min(p.progress_percent, 100.0) for p in production_progress) / production_targets,
            2,
        )
    else:
        production_percent = 0.0

    # Calculate assembly progress
    assembly_targets = len(assembly_progress)
    assembly_complete = sum(1 for a in assembly_progress if a.is_complete)

    if assembly_targets > 0:
        # Average of individual progress percentages (capped at 100 for average)
        assembly_percent = round(
            sum(min(a.progress_percent, 100.0) for a in assembly_progress) / assembly_targets,
            2,
        )
    else:
        assembly_percent = 0.0

    # Calculate overall progress
    # If both are empty, overall is 0
    # If one is empty, use the other
    # If both have targets, average them
    if production_targets == 0 and assembly_targets == 0:
        overall_percent = 0.0
    elif production_targets == 0:
        overall_percent = assembly_percent
    elif assembly_targets == 0:
        overall_percent = production_percent
    else:
        overall_percent = round((production_percent + assembly_percent) / 2, 2)

    # Determine status
    if production_percent == 0.0 and assembly_percent == 0.0:
        status = "not_started"
    elif (
        production_targets == production_complete
        and assembly_targets == assembly_complete
        and (production_targets > 0 or assembly_targets > 0)
    ):
        status = "complete"
    else:
        status = "in_progress"

    return {
        "production_percent": production_percent,
        "assembly_percent": assembly_percent,
        "overall_percent": overall_percent,
        "status": status,
        "production_targets": production_targets,
        "production_complete": production_complete,
        "assembly_targets": assembly_targets,
        "assembly_complete": assembly_complete,
    }
