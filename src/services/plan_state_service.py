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


def _get_event_or_raise(event_id: int, session: Session) -> Event:
    """Get event by ID or raise ValidationError if not found.

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
    """Internal implementation of lock_plan."""
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
    """Internal implementation of start_production."""
    event = _get_event_or_raise(event_id, session)

    if event.plan_state != PlanState.LOCKED:
        raise PlanStateError(
            event_id,
            event.plan_state,
            "start production (must be in LOCKED state)"
        )

    event.plan_state = PlanState.IN_PRODUCTION
    session.flush()
    return event


def start_production(event_id: int, session: Session = None) -> Event:
    """Transition event plan from LOCKED to IN_PRODUCTION.

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
    """Internal implementation of complete_production."""
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
