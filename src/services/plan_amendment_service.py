"""Plan Amendment Service for F078.

Provides functions to create and query plan amendments.
Amendments track changes made to plans during production.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()

Feature F079: Production-aware validation added in WP04.
- Amendments are blocked when production has been recorded for the target recipe/FG
- This protects completed work from being modified after the fact
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.models import (
    Event,
    PlanAmendment,
    EventFinishedGood,
    BatchDecision,
    ProductionRun,
    Recipe,
    FinishedGood,
    Composition,
    FinishedUnit,
)
from src.models.plan_amendment import AmendmentType
from src.models.event import PlanState
from src.services.database import session_scope
from src.services.exceptions import ValidationError, PlanStateError


def _validate_amendment_allowed(event: Event, reason: str) -> None:
    """Validate that amendments are allowed for this event.

    Args:
        event: Event to validate
        reason: Amendment reason to validate

    Raises:
        PlanStateError: If plan is not in IN_PRODUCTION state
        ValidationError: If reason is empty
    """
    if event.plan_state != PlanState.IN_PRODUCTION:
        raise PlanStateError(
            event.id,
            event.plan_state,
            "create amendment (plan must be IN_PRODUCTION)"
        )

    if not reason or not reason.strip():
        raise ValidationError(["Amendment reason is required"])


def _get_event_or_raise(event_id: int, session: Session) -> Event:
    """Get event by ID or raise ValidationError."""
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise ValidationError([f"Event {event_id} not found"])
    return event


# =============================================================================
# F079 WP04: Production Validation Helpers
# =============================================================================


def _has_production_for_recipe(
    event_id: int,
    recipe_id: int,
    session: Session
) -> bool:
    """Check if any production has been recorded for a recipe in an event.

    Args:
        event_id: Event to check
        recipe_id: Recipe to check
        session: Database session

    Returns:
        True if at least one ProductionRun exists for this recipe/event
    """
    count = session.query(ProductionRun).filter(
        ProductionRun.event_id == event_id,
        ProductionRun.recipe_id == recipe_id,
    ).count()
    return count > 0


def _get_recipes_for_finished_good(
    fg_id: int,
    session: Session
) -> List[int]:
    """Get all recipe IDs that contribute to a finished good.

    A recipe contributes to an FG if:
    - The FG's composition includes a FinishedUnit
    - That FinishedUnit is produced by the recipe

    Args:
        fg_id: FinishedGood ID to check
        session: Database session

    Returns:
        List of recipe IDs that contribute to this FG
    """
    # Get all compositions for this FG that have a FinishedUnit component
    compositions = (
        session.query(Composition)
        .filter(Composition.assembly_id == fg_id)
        .filter(Composition.finished_unit_id.isnot(None))
        .all()
    )

    recipe_ids = set()
    for comp in compositions:
        # Get the FinishedUnit and its recipe
        fu = session.get(FinishedUnit, comp.finished_unit_id)
        if fu and fu.recipe_id:
            recipe_ids.add(fu.recipe_id)

    return list(recipe_ids)


# =============================================================================
# Base Amendment Creation
# =============================================================================


def _create_amendment_impl(
    event_id: int,
    amendment_type: AmendmentType,
    amendment_data: dict,
    reason: str,
    session: Session
) -> PlanAmendment:
    """Internal implementation of create_amendment."""
    event = _get_event_or_raise(event_id, session)
    _validate_amendment_allowed(event, reason)

    amendment = PlanAmendment(
        event_id=event_id,
        amendment_type=amendment_type,
        amendment_data=amendment_data,
        reason=reason.strip(),
    )
    session.add(amendment)
    session.flush()

    return amendment


def create_amendment(
    event_id: int,
    amendment_type: AmendmentType,
    amendment_data: dict,
    reason: str,
    session: Session = None
) -> PlanAmendment:
    """Create a plan amendment record.

    Base function for creating amendments. Use specific functions
    (drop_finished_good, add_finished_good, modify_batch_decision)
    for type-specific validation and data modification.

    Args:
        event_id: Event to amend
        amendment_type: Type of amendment
        amendment_data: Amendment-specific data
        reason: User-provided reason for amendment
        session: Optional session for transaction sharing

    Returns:
        Created PlanAmendment

    Raises:
        ValidationError: If event not found or reason empty
        PlanStateError: If plan not in IN_PRODUCTION state
    """
    if session is not None:
        return _create_amendment_impl(event_id, amendment_type, amendment_data, reason, session)

    with session_scope() as session:
        return _create_amendment_impl(event_id, amendment_type, amendment_data, reason, session)


# =============================================================================
# DROP_FG: Remove Finished Good from Plan
# =============================================================================


def _drop_finished_good_impl(
    event_id: int,
    fg_id: int,
    reason: str,
    session: Session
) -> PlanAmendment:
    """Internal implementation of drop_finished_good."""
    event = _get_event_or_raise(event_id, session)
    _validate_amendment_allowed(event, reason)

    # F079 WP04: Check for production on contributing recipes
    contributing_recipes = _get_recipes_for_finished_good(fg_id, session)
    recipes_with_production = []

    for recipe_id in contributing_recipes:
        if _has_production_for_recipe(event_id, recipe_id, session):
            recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
            recipe_name = recipe.name if recipe else f"Recipe {recipe_id}"
            recipes_with_production.append(recipe_name)

    if recipes_with_production:
        # Get FG name for error message
        fg = session.query(FinishedGood).filter(FinishedGood.id == fg_id).first()
        fg_name = fg.display_name if fg else f"Finished Good {fg_id}"
        raise ValidationError([
            f"Cannot drop finished good '{fg_name}' - production has been "
            f"recorded for contributing recipe(s): {', '.join(recipes_with_production)}. "
            "Complete or void production first."
        ])

    # Find the EventFinishedGood record
    event_fg = session.query(EventFinishedGood).filter(
        EventFinishedGood.event_id == event_id,
        EventFinishedGood.finished_good_id == fg_id,
    ).first()

    if event_fg is None:
        raise ValidationError([f"Finished good {fg_id} not in event plan"])

    # Capture data for amendment
    amendment_data = {
        "fg_id": fg_id,
        "fg_name": event_fg.finished_good.display_name if event_fg.finished_good else "Unknown",
        "original_quantity": event_fg.quantity,
    }

    # Delete the EventFinishedGood
    session.delete(event_fg)

    # Create amendment record
    amendment = PlanAmendment(
        event_id=event_id,
        amendment_type=AmendmentType.DROP_FG,
        amendment_data=amendment_data,
        reason=reason.strip(),
    )
    session.add(amendment)
    session.flush()

    return amendment


def drop_finished_good(
    event_id: int,
    fg_id: int,
    reason: str,
    session: Session = None
) -> PlanAmendment:
    """Drop a finished good from the event plan.

    Removes the EventFinishedGood record and creates an amendment
    tracking the removal.

    Args:
        event_id: Event to modify
        fg_id: FinishedGood ID to remove
        reason: User-provided reason
        session: Optional session for transaction sharing

    Returns:
        Created PlanAmendment

    Raises:
        ValidationError: If FG not in plan or reason empty
        PlanStateError: If plan not in IN_PRODUCTION state
    """
    if session is not None:
        return _drop_finished_good_impl(event_id, fg_id, reason, session)

    with session_scope() as session:
        return _drop_finished_good_impl(event_id, fg_id, reason, session)


# =============================================================================
# ADD_FG: Add Finished Good to Plan
# =============================================================================


def _add_finished_good_impl(
    event_id: int,
    fg_id: int,
    quantity: int,
    reason: str,
    session: Session
) -> PlanAmendment:
    """Internal implementation of add_finished_good."""
    from src.models import FinishedGood

    event = _get_event_or_raise(event_id, session)
    _validate_amendment_allowed(event, reason)

    # Check FG doesn't already exist in plan
    existing = session.query(EventFinishedGood).filter(
        EventFinishedGood.event_id == event_id,
        EventFinishedGood.finished_good_id == fg_id,
    ).first()

    if existing is not None:
        raise ValidationError([f"Finished good {fg_id} already in event plan"])

    # Validate FG exists
    fg = session.query(FinishedGood).filter(FinishedGood.id == fg_id).first()
    if fg is None:
        raise ValidationError([f"Finished good {fg_id} not found"])

    # Validate quantity
    if quantity <= 0:
        raise ValidationError(["Quantity must be positive"])

    # Create EventFinishedGood
    event_fg = EventFinishedGood(
        event_id=event_id,
        finished_good_id=fg_id,
        quantity=quantity,
    )
    session.add(event_fg)

    # Create amendment record
    amendment_data = {
        "fg_id": fg_id,
        "fg_name": fg.display_name,
        "quantity": quantity,
    }

    amendment = PlanAmendment(
        event_id=event_id,
        amendment_type=AmendmentType.ADD_FG,
        amendment_data=amendment_data,
        reason=reason.strip(),
    )
    session.add(amendment)
    session.flush()

    return amendment


def add_finished_good(
    event_id: int,
    fg_id: int,
    quantity: int,
    reason: str,
    session: Session = None
) -> PlanAmendment:
    """Add a finished good to the event plan.

    Creates an EventFinishedGood record and amendment tracking
    the addition.

    Args:
        event_id: Event to modify
        fg_id: FinishedGood ID to add
        quantity: Quantity to add
        reason: User-provided reason
        session: Optional session for transaction sharing

    Returns:
        Created PlanAmendment

    Raises:
        ValidationError: If FG already in plan, FG not found, or reason empty
        PlanStateError: If plan not in IN_PRODUCTION state
    """
    if session is not None:
        return _add_finished_good_impl(event_id, fg_id, quantity, reason, session)

    with session_scope() as session:
        return _add_finished_good_impl(event_id, fg_id, quantity, reason, session)


# =============================================================================
# MODIFY_BATCH: Change Batch Count for Recipe
# =============================================================================


def _modify_batch_decision_impl(
    event_id: int,
    recipe_id: int,
    new_batches: int,
    reason: str,
    session: Session
) -> PlanAmendment:
    """Internal implementation of modify_batch_decision."""
    event = _get_event_or_raise(event_id, session)
    _validate_amendment_allowed(event, reason)

    # F079 WP04: Check for existing production
    if _has_production_for_recipe(event_id, recipe_id, session):
        # Get recipe name for clear error message
        recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
        recipe_name = recipe.name if recipe else f"Recipe {recipe_id}"
        raise ValidationError([
            f"Cannot modify batch decision for recipe '{recipe_name}' - "
            "production has already been recorded. "
            "Complete or void existing production first."
        ])

    # Find batch decision
    batch_decision = session.query(BatchDecision).filter(
        BatchDecision.event_id == event_id,
        BatchDecision.recipe_id == recipe_id,
    ).first()

    if batch_decision is None:
        raise ValidationError([f"No batch decision for recipe {recipe_id} in event"])

    # Validate new_batches
    if new_batches < 0:
        raise ValidationError(["Batch count cannot be negative"])

    # Capture old value
    old_batches = batch_decision.batches

    # Update batch decision
    batch_decision.batches = new_batches

    # Create amendment record
    amendment_data = {
        "recipe_id": recipe_id,
        "recipe_name": batch_decision.recipe.name if batch_decision.recipe else "Unknown",
        "old_batches": old_batches,
        "new_batches": new_batches,
    }

    amendment = PlanAmendment(
        event_id=event_id,
        amendment_type=AmendmentType.MODIFY_BATCH,
        amendment_data=amendment_data,
        reason=reason.strip(),
    )
    session.add(amendment)
    session.flush()

    return amendment


def modify_batch_decision(
    event_id: int,
    recipe_id: int,
    new_batches: int,
    reason: str,
    session: Session = None
) -> PlanAmendment:
    """Modify batch count for a recipe in the event plan.

    Updates the BatchDecision record and creates an amendment
    tracking the change.

    Args:
        event_id: Event to modify
        recipe_id: Recipe ID to modify batch count for
        new_batches: New batch count
        reason: User-provided reason
        session: Optional session for transaction sharing

    Returns:
        Created PlanAmendment

    Raises:
        ValidationError: If batch decision not found or reason empty
        PlanStateError: If plan not in IN_PRODUCTION state
    """
    if session is not None:
        return _modify_batch_decision_impl(event_id, recipe_id, new_batches, reason, session)

    with session_scope() as session:
        return _modify_batch_decision_impl(event_id, recipe_id, new_batches, reason, session)


# =============================================================================
# Amendment History Retrieval
# =============================================================================


def _get_amendments_impl(event_id: int, session: Session) -> List[PlanAmendment]:
    """Internal implementation of get_amendments."""
    return session.query(PlanAmendment).filter(
        PlanAmendment.event_id == event_id
    ).order_by(PlanAmendment.created_at.asc()).all()


def get_amendments(event_id: int, session: Session = None) -> List[PlanAmendment]:
    """Get all amendments for an event in chronological order.

    Args:
        event_id: Event ID to query
        session: Optional session for transaction sharing

    Returns:
        List of PlanAmendment records, oldest first
    """
    if session is not None:
        return _get_amendments_impl(event_id, session)

    with session_scope() as session:
        amendments = _get_amendments_impl(event_id, session)
        # Ensure data is loaded before session closes
        for a in amendments:
            _ = a.amendment_data
            _ = a.amendment_type
        return amendments
