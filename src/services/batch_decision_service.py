"""Service layer for batch decision CRUD operations.

Feature 073: Batch Calculation User Decisions
Work Package: WP03 - Batch Decision CRUD Service

This service provides CRUD operations for BatchDecision persistence, allowing
users to save and manage their batch choices for each FinishedUnit in an event plan.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.batch_decision import BatchDecision
from src.models.event import Event, PlanState
from src.models.finished_unit import FinishedUnit
from src.services.database import session_scope
from src.services.exceptions import PlanStateError, ValidationError


logger = logging.getLogger(__name__)


@dataclass
class BatchDecisionInput:
    """User's batch decision for one FU.

    Attributes:
        finished_unit_id: The FinishedUnit ID this decision is for
        batches: Number of batches to make (must be > 0)
        is_shortfall: Whether this batch count results in a shortfall
        confirmed_shortfall: Whether user has confirmed acceptance of shortfall
    """

    finished_unit_id: int
    batches: int
    is_shortfall: bool = False
    confirmed_shortfall: bool = False


# =============================================================================
# Validation Functions
# =============================================================================


def _validate_event_exists(event_id: int, session: Session) -> Event:
    """Validate that event exists and return it.

    Args:
        event_id: Event ID to validate
        session: SQLAlchemy session

    Returns:
        Event instance

    Raises:
        ValidationError: If event does not exist
    """
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError([f"Event with ID {event_id} does not exist"])
    return event


def _validate_finished_unit_exists(finished_unit_id: int, session: Session) -> FinishedUnit:
    """Validate that finished unit exists and return it.

    Args:
        finished_unit_id: FinishedUnit ID to validate
        session: SQLAlchemy session

    Returns:
        FinishedUnit instance

    Raises:
        ValidationError: If FinishedUnit does not exist
    """
    fu = session.query(FinishedUnit).filter(FinishedUnit.id == finished_unit_id).first()
    if not fu:
        raise ValidationError([f"FinishedUnit with ID {finished_unit_id} does not exist"])
    return fu


def _validate_batches(batches: int) -> None:
    """Validate that batches is positive.

    Args:
        batches: Number of batches

    Raises:
        ValidationError: If batches is not positive
    """
    if batches is None or batches <= 0:
        raise ValidationError(["Batches must be a positive integer (> 0)"])


def _validate_shortfall_confirmation(decision: BatchDecisionInput) -> None:
    """Validate shortfall confirmation if is_shortfall is True.

    Args:
        decision: The batch decision input to validate

    Raises:
        ValidationError: If is_shortfall is True but confirmed_shortfall is False
    """
    if decision.is_shortfall and not decision.confirmed_shortfall:
        raise ValidationError(
            ["Shortfall must be confirmed: is_shortfall=True requires confirmed_shortfall=True"]
        )


# =============================================================================
# Helper Functions
# =============================================================================


def is_shortfall_option(batches: int, yield_per_batch: int, quantity_needed: int) -> bool:
    """Determine if a batch selection results in a shortfall.

    This helper function checks whether the total yield from the given number
    of batches is less than the quantity needed.

    Args:
        batches: Number of batches to make
        yield_per_batch: Number of items produced per batch
        quantity_needed: Total quantity required

    Returns:
        True if total yield is less than quantity needed, False otherwise

    Example:
        >>> is_shortfall_option(2, 24, 60)
        True  # 2 batches * 24/batch = 48, which is < 60
        >>> is_shortfall_option(3, 24, 60)
        False  # 3 batches * 24/batch = 72, which is >= 60
    """
    total_yield = batches * yield_per_batch
    return total_yield < quantity_needed


# =============================================================================
# CRUD Functions - Internal Implementations
# =============================================================================


def _save_batch_decision_impl(
    event_id: int,
    decision: BatchDecisionInput,
    session: Session,
) -> BatchDecision:
    """Internal implementation for saving a batch decision.

    Args:
        event_id: Event ID to save decision for
        decision: BatchDecisionInput with decision data
        session: SQLAlchemy session

    Returns:
        Created or updated BatchDecision instance
    """
    # Validate inputs
    event = _validate_event_exists(event_id, session)

    # F077: Check plan state - DRAFT and LOCKED allow batch decision modifications
    if event.plan_state not in (PlanState.DRAFT, PlanState.LOCKED):
        raise PlanStateError(
            event_id,
            event.plan_state,
            "modify batch decisions"
        )
    fu = _validate_finished_unit_exists(decision.finished_unit_id, session)
    _validate_batches(decision.batches)
    _validate_shortfall_confirmation(decision)

    # Check for existing decision (upsert pattern)
    existing = (
        session.query(BatchDecision)
        .filter(
            BatchDecision.event_id == event_id,
            BatchDecision.finished_unit_id == decision.finished_unit_id,
        )
        .first()
    )

    if existing:
        # Update existing
        existing.batches = decision.batches
        # recipe_id is denormalized from FU for convenience
        existing.recipe_id = fu.recipe_id
        logger.info(
            f"Updated BatchDecision: event_id={event_id}, "
            f"finished_unit_id={decision.finished_unit_id}, batches={decision.batches}"
        )
        return existing
    else:
        # Create new
        batch_decision = BatchDecision(
            event_id=event_id,
            finished_unit_id=decision.finished_unit_id,
            recipe_id=fu.recipe_id,  # Denormalized from FU for convenience
            batches=decision.batches,
        )
        session.add(batch_decision)
        session.flush()
        logger.info(
            f"Created BatchDecision: event_id={event_id}, "
            f"finished_unit_id={decision.finished_unit_id}, batches={decision.batches}"
        )
        return batch_decision


def _get_batch_decisions_impl(event_id: int, session: Session) -> List[BatchDecision]:
    """Internal implementation for getting all batch decisions for an event.

    Args:
        event_id: Event ID to get decisions for
        session: SQLAlchemy session

    Returns:
        List of BatchDecision instances
    """
    return (
        session.query(BatchDecision)
        .filter(BatchDecision.event_id == event_id)
        .order_by(BatchDecision.finished_unit_id)
        .all()
    )


def _get_batch_decision_impl(
    event_id: int,
    finished_unit_id: int,
    session: Session,
) -> Optional[BatchDecision]:
    """Internal implementation for getting a single batch decision.

    Args:
        event_id: Event ID
        finished_unit_id: FinishedUnit ID
        session: SQLAlchemy session

    Returns:
        BatchDecision instance or None if not found
    """
    return (
        session.query(BatchDecision)
        .filter(
            BatchDecision.event_id == event_id,
            BatchDecision.finished_unit_id == finished_unit_id,
        )
        .first()
    )


def _delete_batch_decisions_impl(event_id: int, session: Session) -> int:
    """Internal implementation for deleting all batch decisions for an event.

    Args:
        event_id: Event ID to delete decisions for
        session: SQLAlchemy session

    Returns:
        Number of deleted records
    """
    # Validate event and check state
    event = _validate_event_exists(event_id, session)

    # F077: Check plan state - DRAFT and LOCKED allow batch decision modifications
    if event.plan_state not in (PlanState.DRAFT, PlanState.LOCKED):
        raise PlanStateError(
            event_id,
            event.plan_state,
            "modify batch decisions"
        )

    count = (
        session.query(BatchDecision)
        .filter(BatchDecision.event_id == event_id)
        .delete(synchronize_session="fetch")
    )
    logger.info(f"Deleted {count} BatchDecision(s) for event_id={event_id}")
    return count


# =============================================================================
# CRUD Functions - Public API
# =============================================================================


def save_batch_decision(
    event_id: int,
    decision: BatchDecisionInput,
    session: Session = None,
) -> BatchDecision:
    """Save (create or update) a batch decision for a FinishedUnit in an event.

    This function implements an upsert pattern: if a BatchDecision already exists
    for the given (event_id, finished_unit_id) pair, it will be updated.
    Otherwise, a new BatchDecision will be created.

    Args:
        event_id: Event ID to save decision for
        decision: BatchDecisionInput with the decision data
        session: Optional SQLAlchemy session for transaction sharing.
                 If None, creates a new session scope.

    Returns:
        Created or updated BatchDecision instance

    Raises:
        ValidationError: If validation fails (event/FU doesn't exist,
                        batches <= 0, or unconfirmed shortfall)

    Example:
        >>> decision = BatchDecisionInput(
        ...     finished_unit_id=42,
        ...     batches=3,
        ...     is_shortfall=False,
        ... )
        >>> save_batch_decision(event_id=1, decision=decision)
        BatchDecision(event_id=1, finished_unit_id=42, batches=3)
    """
    if session is not None:
        return _save_batch_decision_impl(event_id, decision, session)

    with session_scope() as session:
        return _save_batch_decision_impl(event_id, decision, session)


def get_batch_decisions(event_id: int, session: Session = None) -> List[BatchDecision]:
    """Get all batch decisions for an event.

    Args:
        event_id: Event ID to get decisions for
        session: Optional SQLAlchemy session for transaction sharing.
                 If None, creates a new session scope.

    Returns:
        List of BatchDecision instances, ordered by finished_unit_id

    Example:
        >>> decisions = get_batch_decisions(event_id=1)
        >>> for d in decisions:
        ...     print(f"FU {d.finished_unit_id}: {d.batches} batches")
    """
    if session is not None:
        return _get_batch_decisions_impl(event_id, session)

    with session_scope() as session:
        return _get_batch_decisions_impl(event_id, session)


def get_batch_decision(
    event_id: int,
    finished_unit_id: int,
    session: Session = None,
) -> Optional[BatchDecision]:
    """Get a single batch decision by event_id and finished_unit_id.

    Args:
        event_id: Event ID
        finished_unit_id: FinishedUnit ID
        session: Optional SQLAlchemy session for transaction sharing.
                 If None, creates a new session scope.

    Returns:
        BatchDecision instance or None if not found

    Example:
        >>> decision = get_batch_decision(event_id=1, finished_unit_id=42)
        >>> if decision:
        ...     print(f"Making {decision.batches} batches")
    """
    if session is not None:
        return _get_batch_decision_impl(event_id, finished_unit_id, session)

    with session_scope() as session:
        return _get_batch_decision_impl(event_id, finished_unit_id, session)


def delete_batch_decisions(event_id: int, session: Session = None) -> int:
    """Delete all batch decisions for an event.

    This is useful when resetting an event's planning state or when
    the event is being re-planned from scratch.

    Args:
        event_id: Event ID to delete decisions for
        session: Optional SQLAlchemy session for transaction sharing.
                 If None, creates a new session scope.

    Returns:
        Number of deleted records

    Example:
        >>> count = delete_batch_decisions(event_id=1)
        >>> print(f"Deleted {count} batch decisions")
    """
    if session is not None:
        return _delete_batch_decisions_impl(event_id, session)

    with session_scope() as session:
        return _delete_batch_decisions_impl(event_id, session)
