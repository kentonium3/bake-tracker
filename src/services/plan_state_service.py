"""Plan State Service for F077.

Provides state transition functions for event plan lifecycle management.
State machine: DRAFT -> LOCKED -> IN_PRODUCTION -> COMPLETED

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from sqlalchemy.orm import Session

from src.models.event import Event, PlanState
from src.services.database import session_scope
from src.services.exceptions import PlanStateError, ValidationError
from src.services.plan_snapshot_service import create_plan_snapshot


def _get_event_or_raise(event_id: int, session: Session) -> Event:
    """Get event by ID or raise ValidationError if not found.

    Transaction boundary: Inherits session from caller.
    Read-only query within the caller's transaction scope.

    Args:
        event_id: Event ID to fetch
        session: Database session

    Returns:
        Event instance

    Raises:
        ValidationError: If event does not exist
    """
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise ValidationError([f"Event {event_id} not found"])
    return event


def get_plan_state(event_id: int, session: Session = None) -> PlanState:
    """Get the current plan state for an event.

    Transaction boundary: Read-only operation.
    Queries event and returns plan_state field.

    Args:
        event_id: Event ID to query
        session: Optional session for transaction sharing

    Returns:
        Current PlanState value

    Raises:
        ValidationError: If event not found
    """
    if session is not None:
        event = _get_event_or_raise(event_id, session)
        return event.plan_state

    with session_scope() as session:
        event = _get_event_or_raise(event_id, session)
        return event.plan_state


# =============================================================================
# State Transition Functions
# =============================================================================


def _lock_plan_impl(event_id: int, session: Session) -> Event:
    """Internal implementation of lock_plan.

    Transaction boundary: Inherits session from caller.
    Updates event plan_state within the caller's transaction scope.
    """
    event = _get_event_or_raise(event_id, session)

    if event.plan_state != PlanState.DRAFT:
        raise PlanStateError(
            event_id,
            event.plan_state,
            "lock plan (must be in DRAFT state)"
        )

    event.plan_state = PlanState.LOCKED
    session.flush()
    return event


def lock_plan(event_id: int, session: Session = None) -> Event:
    """Transition event plan from DRAFT to LOCKED.

    Transaction boundary: Single-step write.
    Updates event.plan_state from DRAFT to LOCKED.

    Locking a plan prevents recipe and finished goods modifications.
    Batch decisions can still be modified while locked.

    Args:
        event_id: Event ID to lock
        session: Optional session for transaction sharing

    Returns:
        Updated Event instance

    Raises:
        ValidationError: If event not found
        PlanStateError: If plan is not in DRAFT state
    """
    if session is not None:
        return _lock_plan_impl(event_id, session)

    with session_scope() as session:
        return _lock_plan_impl(event_id, session)


def _start_production_impl(event_id: int, session: Session) -> Event:
    """Internal implementation of start_production.

    Transaction boundary: Inherits session from caller.
    Multi-step operation within the caller's transaction scope:
        1. Create plan snapshot (via create_plan_snapshot)
        2. Update event.plan_state to IN_PRODUCTION
    """
    event = _get_event_or_raise(event_id, session)

    if event.plan_state != PlanState.LOCKED:
        raise PlanStateError(
            event_id,
            event.plan_state,
            "start production (must be in LOCKED state)"
        )

    # F078: Create snapshot BEFORE state transition
    create_plan_snapshot(event_id, session)

    event.plan_state = PlanState.IN_PRODUCTION
    session.flush()
    return event


def start_production(event_id: int, session: Session = None) -> Event:
    """Transition event plan from LOCKED to IN_PRODUCTION.

    Transaction boundary: Multi-step operation (atomic).
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
        1. Validate event exists and is in LOCKED state
        2. Create plan snapshot (F078 - captures complete plan state)
        3. Update event.plan_state from LOCKED to IN_PRODUCTION

    CRITICAL: Session parameter is passed to create_plan_snapshot() to ensure
    atomicity. If snapshot creation fails, state transition is rolled back.

    Starting production prevents most modifications. Only amendments
    (via F078) will be allowed after this point.

    Args:
        event_id: Event ID to start production
        session: Optional session for transaction sharing

    Returns:
        Updated Event instance

    Raises:
        ValidationError: If event not found
        PlanStateError: If plan is not in LOCKED state
    """
    if session is not None:
        return _start_production_impl(event_id, session)

    with session_scope() as session:
        return _start_production_impl(event_id, session)


def _complete_production_impl(event_id: int, session: Session) -> Event:
    """Internal implementation of complete_production.

    Transaction boundary: Inherits session from caller.
    Updates event plan_state within the caller's transaction scope.
    """
    event = _get_event_or_raise(event_id, session)

    if event.plan_state != PlanState.IN_PRODUCTION:
        raise PlanStateError(
            event_id,
            event.plan_state,
            "complete production (must be in IN_PRODUCTION state)"
        )

    event.plan_state = PlanState.COMPLETED
    session.flush()
    return event


def complete_production(event_id: int, session: Session = None) -> Event:
    """Transition event plan from IN_PRODUCTION to COMPLETED.

    Transaction boundary: Single-step write.
    Updates event.plan_state from IN_PRODUCTION to COMPLETED.

    Completing production makes the plan read-only. No further
    modifications are allowed.

    Args:
        event_id: Event ID to complete
        session: Optional session for transaction sharing

    Returns:
        Updated Event instance

    Raises:
        ValidationError: If event not found
        PlanStateError: If plan is not in IN_PRODUCTION state
    """
    if session is not None:
        return _complete_production_impl(event_id, session)

    with session_scope() as session:
        return _complete_production_impl(event_id, session)
