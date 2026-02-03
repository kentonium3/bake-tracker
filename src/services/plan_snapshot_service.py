"""Plan Snapshot Service for F078.

Provides functions to create, retrieve, and compare plan snapshots.
Snapshots capture complete plan state when production starts.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session


# =============================================================================
# Comparison Dataclasses (T021)
# =============================================================================


@dataclass
class FGComparisonItem:
    """Comparison item for a finished good."""

    fg_id: int
    fg_name: str
    original_quantity: Optional[int]  # None if added via amendment
    current_quantity: Optional[int]  # None if dropped via amendment
    status: str  # "unchanged", "added", "dropped", "modified"

    @property
    def is_changed(self) -> bool:
        return self.status != "unchanged"


@dataclass
class BatchComparisonItem:
    """Comparison item for a batch decision."""

    recipe_id: int
    recipe_name: str
    original_batches: Optional[int]  # None if recipe added
    current_batches: Optional[int]  # None if recipe removed
    status: str  # "unchanged", "modified", "added", "dropped"

    @property
    def is_changed(self) -> bool:
        return self.status != "unchanged"


@dataclass
class PlanComparison:
    """Complete plan comparison result."""

    has_snapshot: bool
    finished_goods: List[FGComparisonItem]
    batch_decisions: List[BatchComparisonItem]

    @property
    def total_changes(self) -> int:
        fg_changes = sum(1 for fg in self.finished_goods if fg.is_changed)
        batch_changes = sum(1 for bd in self.batch_decisions if bd.is_changed)
        return fg_changes + batch_changes

    @property
    def has_changes(self) -> bool:
        return self.total_changes > 0

from src.models import Event, PlanSnapshot, EventRecipe, EventFinishedGood, BatchDecision
from src.services.database import session_scope
from src.services.exceptions import ValidationError
from src.utils.datetime_utils import utc_now


def _build_snapshot_data(event: Event, session: Session) -> dict:
    """Build snapshot JSON data from current plan state.

    Transaction boundary: Inherits session from caller.
    Read-only queries within the caller's transaction scope.

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
    """Internal implementation of create_plan_snapshot.

    Transaction boundary: Inherits session from caller.
    Multi-step operation within the caller's transaction scope:
        1. Check for existing snapshot (idempotent - returns existing if found)
        2. Query event and validate existence
        3. Build snapshot data from current plan state
        4. Create and persist PlanSnapshot record
    """
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

    Transaction boundary: Multi-step operation (atomic).
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
        1. Check for existing snapshot (idempotent - returns existing if found)
        2. Query event and validate existence
        3. Build snapshot data (recipes, finished goods, batch decisions)
        4. Create and persist PlanSnapshot record

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
    """Internal implementation of get_plan_snapshot.

    Transaction boundary: Inherits session from caller.
    Read-only query within the caller's transaction scope.
    """
    return session.query(PlanSnapshot).filter(
        PlanSnapshot.event_id == event_id
    ).first()


def get_plan_snapshot(event_id: int, session: Session = None) -> Optional[PlanSnapshot]:
    """Get the plan snapshot for an event.

    Transaction boundary: Read-only operation.
    Queries PlanSnapshot table by event_id.

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


# =============================================================================
# Plan Comparison (T022)
# =============================================================================


def _get_plan_comparison_impl(event_id: int, session: Session) -> PlanComparison:
    """Internal implementation of get_plan_comparison.

    Transaction boundary: Inherits session from caller.
    Read-only computation within the caller's transaction scope.
    """
    # Get snapshot
    snapshot = session.query(PlanSnapshot).filter(
        PlanSnapshot.event_id == event_id
    ).first()

    if snapshot is None:
        return PlanComparison(
            has_snapshot=False,
            finished_goods=[],
            batch_decisions=[],
        )

    snapshot_data = snapshot.snapshot_data

    # Parse original FGs from snapshot
    original_fgs = {
        fg["fg_id"]: fg
        for fg in snapshot_data.get("finished_goods", [])
    }

    # Get current FGs
    current_event_fgs = session.query(EventFinishedGood).filter(
        EventFinishedGood.event_id == event_id
    ).all()
    current_fgs = {
        efg.finished_good_id: {
            "fg_id": efg.finished_good_id,
            "fg_name": efg.finished_good.display_name if efg.finished_good else "Unknown",
            "quantity": efg.quantity,
        }
        for efg in current_event_fgs
    }

    # Compare FGs
    fg_comparison = []
    all_fg_ids = set(original_fgs.keys()) | set(current_fgs.keys())

    for fg_id in sorted(all_fg_ids):
        original = original_fgs.get(fg_id)
        current = current_fgs.get(fg_id)

        if original and current:
            # Present in both
            orig_qty = original.get("quantity")
            curr_qty = current.get("quantity")
            status = "unchanged" if orig_qty == curr_qty else "modified"
            fg_comparison.append(FGComparisonItem(
                fg_id=fg_id,
                fg_name=original.get("fg_name", "Unknown"),
                original_quantity=orig_qty,
                current_quantity=curr_qty,
                status=status,
            ))
        elif original and not current:
            # Dropped
            fg_comparison.append(FGComparisonItem(
                fg_id=fg_id,
                fg_name=original.get("fg_name", "Unknown"),
                original_quantity=original.get("quantity"),
                current_quantity=None,
                status="dropped",
            ))
        elif current and not original:
            # Added
            fg_comparison.append(FGComparisonItem(
                fg_id=fg_id,
                fg_name=current.get("fg_name", "Unknown"),
                original_quantity=None,
                current_quantity=current.get("quantity"),
                status="added",
            ))

    # Parse original batch decisions from snapshot
    original_batches = {
        bd["recipe_id"]: bd
        for bd in snapshot_data.get("batch_decisions", [])
    }

    # Get current batch decisions
    current_batch_decisions = session.query(BatchDecision).filter(
        BatchDecision.event_id == event_id
    ).all()
    current_batches = {
        bd.recipe_id: {
            "recipe_id": bd.recipe_id,
            "recipe_name": bd.recipe.name if bd.recipe else "Unknown",
            "batches": bd.batches,
        }
        for bd in current_batch_decisions
    }

    # Compare batches
    batch_comparison = []
    all_recipe_ids = set(original_batches.keys()) | set(current_batches.keys())

    for recipe_id in sorted(all_recipe_ids):
        original = original_batches.get(recipe_id)
        current = current_batches.get(recipe_id)

        if original and current:
            orig_count = original.get("batches")
            curr_count = current.get("batches")
            status = "unchanged" if orig_count == curr_count else "modified"
            batch_comparison.append(BatchComparisonItem(
                recipe_id=recipe_id,
                recipe_name=original.get("recipe_name", "Unknown"),
                original_batches=orig_count,
                current_batches=curr_count,
                status=status,
            ))
        elif original and not current:
            batch_comparison.append(BatchComparisonItem(
                recipe_id=recipe_id,
                recipe_name=original.get("recipe_name", "Unknown"),
                original_batches=original.get("batches"),
                current_batches=None,
                status="dropped",
            ))
        elif current and not original:
            batch_comparison.append(BatchComparisonItem(
                recipe_id=recipe_id,
                recipe_name=current.get("recipe_name", "Unknown"),
                original_batches=None,
                current_batches=current.get("batches"),
                status="added",
            ))

    return PlanComparison(
        has_snapshot=True,
        finished_goods=fg_comparison,
        batch_decisions=batch_comparison,
    )


def get_plan_comparison(event_id: int, session: Session = None) -> PlanComparison:
    """Compare original plan (snapshot) with current plan state.

    Transaction boundary: Read-only operation.
    Queries snapshot data and current state, computes differences.

    Returns structured comparison showing what changed since
    production started.

    Args:
        event_id: Event ID to compare
        session: Optional session for transaction sharing

    Returns:
        PlanComparison with original vs current differences
    """
    if session is not None:
        return _get_plan_comparison_impl(event_id, session)

    with session_scope() as session:
        return _get_plan_comparison_impl(event_id, session)
