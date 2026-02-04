"""
PlanningSnapshot Service for F064 FinishedGoods Snapshot Architecture.

Provides container management for grouping snapshots by planning session.
Each PlanningSnapshot can link to an optional Event and contain multiple
FinishedUnitSnapshot, MaterialUnitSnapshot, and FinishedGoodSnapshot records.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.models import PlanningSnapshot
from src.services.database import session_scope
from src.services.exceptions import ServiceError


class PlanningSnapshotError(ServiceError):
    """Raised when PlanningSnapshot operations fail.

    HTTP Status: 500 Server Error
    """

    http_status_code = 500


def create_planning_snapshot(
    event_id: Optional[int] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> dict:
    """
    Create empty PlanningSnapshot container.

    Args:
        event_id: Optional event to link
        notes: Optional notes
        session: Optional session for transaction sharing

    Returns:
        dict with planning_snapshot id, event_id, created_at, notes
    """
    if session is not None:
        return _create_planning_snapshot_impl(event_id, notes, session)

    try:
        with session_scope() as session:
            return _create_planning_snapshot_impl(event_id, notes, session)
    except SQLAlchemyError as e:
        raise PlanningSnapshotError(f"Database error creating planning snapshot: {e}")


def _create_planning_snapshot_impl(
    event_id: Optional[int],
    notes: Optional[str],
    session: Session,
) -> dict:
    """Internal implementation of create_planning_snapshot."""
    ps = PlanningSnapshot(
        event_id=event_id,
        notes=notes,
    )
    session.add(ps)
    session.flush()

    return {
        "id": ps.id,
        "event_id": ps.event_id,
        "created_at": ps.created_at.isoformat(),
        "notes": ps.notes,
    }


def get_planning_snapshot(
    planning_snapshot_id: int,
    include_snapshots: bool = True,
    session: Optional[Session] = None,
) -> Optional[dict]:
    """
    Get planning snapshot with optionally all linked snapshots.

    Args:
        planning_snapshot_id: PlanningSnapshot ID
        include_snapshots: If True, include all linked snapshot data
        session: Optional session

    Returns:
        dict with planning snapshot and linked snapshots, or None if not found
    """
    if session is not None:
        return _get_planning_snapshot_impl(
            planning_snapshot_id, include_snapshots, session
        )

    with session_scope() as session:
        return _get_planning_snapshot_impl(
            planning_snapshot_id, include_snapshots, session
        )


def _get_planning_snapshot_impl(
    planning_snapshot_id: int,
    include_snapshots: bool,
    session: Session,
) -> Optional[dict]:
    """Internal implementation of get_planning_snapshot."""
    ps = session.query(PlanningSnapshot).filter_by(id=planning_snapshot_id).first()

    if not ps:
        return None

    result = {
        "id": ps.id,
        "event_id": ps.event_id,
        "created_at": ps.created_at.isoformat(),
        "notes": ps.notes,
    }

    if include_snapshots:
        # Aggregate all linked snapshots
        result["finished_unit_snapshots"] = [
            {
                "id": s.id,
                "finished_unit_id": s.finished_unit_id,
                "snapshot_date": s.snapshot_date.isoformat(),
                "definition_data": s.get_definition_data(),
            }
            for s in ps.finished_unit_snapshots
        ]

        result["material_unit_snapshots"] = [
            {
                "id": s.id,
                "material_unit_id": s.material_unit_id,
                "snapshot_date": s.snapshot_date.isoformat(),
                "definition_data": s.get_definition_data(),
            }
            for s in ps.material_unit_snapshots
        ]

        result["finished_good_snapshots"] = [
            {
                "id": s.id,
                "finished_good_id": s.finished_good_id,
                "snapshot_date": s.snapshot_date.isoformat(),
                "definition_data": s.get_definition_data(),
            }
            for s in ps.finished_good_snapshots
        ]

        result["total_snapshots"] = (
            len(result["finished_unit_snapshots"])
            + len(result["material_unit_snapshots"])
            + len(result["finished_good_snapshots"])
        )

    return result


def get_planning_snapshots_by_event(
    event_id: int,
    session: Optional[Session] = None,
) -> list:
    """
    Get all planning snapshots for an event.

    Args:
        event_id: Event ID to query
        session: Optional session

    Returns:
        List of planning snapshot dicts, ordered by created_at descending
    """
    if session is not None:
        return _get_ps_by_event_impl(event_id, session)

    with session_scope() as session:
        return _get_ps_by_event_impl(event_id, session)


def _get_ps_by_event_impl(event_id: int, session: Session) -> list:
    """Internal implementation of get_planning_snapshots_by_event."""
    snapshots = (
        session.query(PlanningSnapshot)
        .filter_by(event_id=event_id)
        .order_by(PlanningSnapshot.created_at.desc())
        .all()
    )

    return [
        {
            "id": ps.id,
            "event_id": ps.event_id,
            "created_at": ps.created_at.isoformat(),
            "notes": ps.notes,
        }
        for ps in snapshots
    ]


def delete_planning_snapshot(
    planning_snapshot_id: int,
    session: Optional[Session] = None,
) -> bool:
    """
    Delete planning snapshot and all associated snapshots.

    Relies on cascade="all, delete-orphan" for cleanup of child snapshots.

    Args:
        planning_snapshot_id: PlanningSnapshot ID
        session: Optional session

    Returns:
        True if deleted, False if not found
    """
    if session is not None:
        return _delete_planning_snapshot_impl(planning_snapshot_id, session)

    with session_scope() as session:
        return _delete_planning_snapshot_impl(planning_snapshot_id, session)


def _delete_planning_snapshot_impl(
    planning_snapshot_id: int,
    session: Session,
) -> bool:
    """Internal implementation of delete_planning_snapshot."""
    ps = session.query(PlanningSnapshot).filter_by(id=planning_snapshot_id).first()

    if not ps:
        return False

    session.delete(ps)
    session.flush()
    return True
