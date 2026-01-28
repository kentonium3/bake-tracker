"""Plan Snapshot Service for F078.

Provides functions to create and retrieve plan snapshots.
Snapshots capture complete plan state when production starts.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from typing import Optional

from sqlalchemy.orm import Session

from src.models import Event, PlanSnapshot, EventRecipe, EventFinishedGood, BatchDecision
from src.services.database import session_scope
from src.services.exceptions import ValidationError
from src.utils.datetime_utils import utc_now


def _build_snapshot_data(event: Event, session: Session) -> dict:
    """Build snapshot JSON data from current plan state.

    Args:
        event: Event to snapshot
        session: Database session

    Returns:
        Dict containing complete plan state
    """
    # Get recipes
    event_recipes = session.query(EventRecipe).filter(
        EventRecipe.event_id == event.id
    ).all()
    recipes_data = [
        {
            "recipe_id": er.recipe_id,
            "recipe_name": er.recipe.name if er.recipe else "Unknown",
        }
        for er in event_recipes
    ]

    # Get finished goods
    event_fgs = session.query(EventFinishedGood).filter(
        EventFinishedGood.event_id == event.id
    ).all()
    fgs_data = [
        {
            "fg_id": efg.finished_good_id,
            "fg_name": efg.finished_good.display_name if efg.finished_good else "Unknown",
            "fg_slug": efg.finished_good.slug if efg.finished_good else "unknown",
            "quantity": efg.quantity,
        }
        for efg in event_fgs
    ]

    # Get batch decisions
    batch_decisions = session.query(BatchDecision).filter(
        BatchDecision.event_id == event.id
    ).all()
    batches_data = [
        {
            "recipe_id": bd.recipe_id,
            "recipe_name": bd.recipe.name if bd.recipe else "Unknown",
            "batches": bd.batches,
            "finished_unit_id": bd.finished_unit_id,
        }
        for bd in batch_decisions
    ]

    return {
        "snapshot_version": "1.0",
        "created_at": utc_now().isoformat(),
        "recipes": recipes_data,
        "finished_goods": fgs_data,
        "batch_decisions": batches_data,
    }


def _create_plan_snapshot_impl(event_id: int, session: Session) -> PlanSnapshot:
    """Internal implementation of create_plan_snapshot."""
    # Check if snapshot already exists (idempotent)
    existing = session.query(PlanSnapshot).filter(
        PlanSnapshot.event_id == event_id
    ).first()
    if existing:
        return existing

    # Get event
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError([f"Event {event_id} not found"])

    # Build snapshot data
    snapshot_data = _build_snapshot_data(event, session)

    # Create snapshot
    snapshot = PlanSnapshot(
        event_id=event_id,
        snapshot_data=snapshot_data,
    )
    session.add(snapshot)
    session.flush()

    return snapshot


def create_plan_snapshot(event_id: int, session: Session = None) -> PlanSnapshot:
    """Create a snapshot of the plan state for an event.

    Captures all recipes, finished goods, quantities, and batch decisions
    as JSON. Idempotent - returns existing snapshot if one exists.

    Args:
        event_id: Event ID to snapshot
        session: Optional session for transaction sharing

    Returns:
        PlanSnapshot instance (new or existing)

    Raises:
        ValidationError: If event not found
    """
    if session is not None:
        return _create_plan_snapshot_impl(event_id, session)

    with session_scope() as session:
        return _create_plan_snapshot_impl(event_id, session)


def _get_plan_snapshot_impl(event_id: int, session: Session) -> Optional[PlanSnapshot]:
    """Internal implementation of get_plan_snapshot."""
    return session.query(PlanSnapshot).filter(
        PlanSnapshot.event_id == event_id
    ).first()


def get_plan_snapshot(event_id: int, session: Session = None) -> Optional[PlanSnapshot]:
    """Get the plan snapshot for an event.

    Args:
        event_id: Event ID to query
        session: Optional session for transaction sharing

    Returns:
        PlanSnapshot if exists, None otherwise
    """
    if session is not None:
        return _get_plan_snapshot_impl(event_id, session)

    with session_scope() as session:
        snapshot = _get_plan_snapshot_impl(event_id, session)
        if snapshot:
            # Ensure data is loaded before session closes
            _ = snapshot.snapshot_data
        return snapshot
