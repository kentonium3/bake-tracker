"""
Recipient Service - Business logic for package recipients.

This service provides CRUD operations for:
- Recipients (people who receive gift packages)

Updated for Feature 006 Event Planning Restoration:
- Added assignment dependency checking (FR-018)
- Added search and filtering operations
- Added get_recipient_events for event history
"""

from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from src.models import Recipient, Event, EventRecipientPackage
from src.services.database import session_scope
from src.services.exceptions import (
    DatabaseError,
    ValidationError,
)


# ============================================================================
# Custom Exceptions
# ============================================================================


class RecipientNotFound(Exception):
    """Raised when a recipient is not found."""
    def __init__(self, recipient_id: int):
        self.recipient_id = recipient_id
        super().__init__(f"Recipient with ID {recipient_id} not found")


class RecipientInUse(Exception):
    """Raised when trying to delete a recipient that's used in events."""
    def __init__(self, recipient_id: int, event_count: int):
        self.recipient_id = recipient_id
        self.event_count = event_count
        super().__init__(
            f"Recipient {recipient_id} is used in {event_count} event(s)"
        )


class RecipientHasAssignmentsError(Exception):
    """Raised when trying to delete a recipient that has event assignments."""
    def __init__(self, recipient_id: int, assignment_count: int):
        self.recipient_id = recipient_id
        self.assignment_count = assignment_count
        super().__init__(
            f"Recipient {recipient_id} has {assignment_count} event assignment(s). "
            "Use force=True to delete."
        )


# ============================================================================
# Recipient CRUD Operations
# ============================================================================


def create_recipient(data: Dict) -> Recipient:
    """
    Create a new recipient.

    Args:
        data: Dictionary with recipient fields

    Returns:
        Created Recipient instance

    Raises:
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    # Validate required fields
    errors = []

    if not data.get("name"):
        errors.append("Name is required")

    if errors:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            # Create recipient
            recipient = Recipient(
                name=data["name"],
                household_name=data.get("household_name"),
                address=data.get("address"),
                notes=data.get("notes"),
            )

            session.add(recipient)
            session.commit()
            session.refresh(recipient)

            return recipient

    except ValidationError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to create recipient: {str(e)}")


def get_recipient(recipient_id: int) -> Recipient:
    """
    Get a recipient by ID.

    Args:
        recipient_id: Recipient ID

    Returns:
        Recipient instance

    Raises:
        RecipientNotFound: If recipient not found
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            recipient = session.query(Recipient).filter(Recipient.id == recipient_id).first()

            if not recipient:
                raise RecipientNotFound(recipient_id)

            return recipient

    except RecipientNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipient: {str(e)}")


def get_recipient_by_name(name: str) -> Optional[Recipient]:
    """
    Get a recipient by exact name match.

    Args:
        name: Recipient name (case-insensitive)

    Returns:
        Recipient instance or None if not found

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            recipient = session.query(Recipient).filter(
                Recipient.name.ilike(name)
            ).first()

            return recipient

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipient by name: {str(e)}")


def get_all_recipients(
    name_search: Optional[str] = None,
    household_search: Optional[str] = None
) -> List[Recipient]:
    """
    Get all recipients with optional filters.

    Args:
        name_search: Optional name filter (partial match)
        household_search: Optional household name filter (partial match)

    Returns:
        List of Recipient instances

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            query = session.query(Recipient)

            # Apply filters
            if name_search:
                query = query.filter(Recipient.name.ilike(f"%{name_search}%"))

            if household_search:
                query = query.filter(Recipient.household_name.ilike(f"%{household_search}%"))

            # Order by name
            query = query.order_by(Recipient.name)

            recipients = query.all()

            return recipients

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipients: {str(e)}")


def update_recipient(recipient_id: int, data: Dict) -> Recipient:
    """
    Update an existing recipient.

    Args:
        recipient_id: Recipient ID to update
        data: Dictionary with updated recipient fields

    Returns:
        Updated Recipient instance

    Raises:
        RecipientNotFound: If recipient not found
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    # Validate required fields
    errors = []

    if not data.get("name"):
        errors.append("Name is required")

    if errors:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            # Get existing recipient
            recipient = session.query(Recipient).filter(Recipient.id == recipient_id).first()
            if not recipient:
                raise RecipientNotFound(recipient_id)

            # Update fields
            recipient.name = data["name"]
            recipient.household_name = data.get("household_name")
            recipient.address = data.get("address")
            recipient.notes = data.get("notes")
            recipient.last_modified = datetime.utcnow()

            session.commit()
            session.refresh(recipient)

            return recipient

    except (RecipientNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update recipient: {str(e)}")


def delete_recipient(recipient_id: int, force: bool = False) -> bool:
    """
    Delete a recipient.

    Args:
        recipient_id: Recipient ID to delete
        force: If True, delete even if recipient has event assignments

    Returns:
        True if deleted successfully

    Raises:
        RecipientNotFound: If recipient not found
        RecipientHasAssignmentsError: If recipient has assignments and force=False
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            # Get recipient
            recipient = session.query(Recipient).filter(Recipient.id == recipient_id).first()
            if not recipient:
                raise RecipientNotFound(recipient_id)

            # Check for event assignments (FR-018)
            assignment_count = session.query(EventRecipientPackage).filter(
                EventRecipientPackage.recipient_id == recipient_id
            ).count()

            if assignment_count > 0 and not force:
                raise RecipientHasAssignmentsError(recipient_id, assignment_count)

            # If force, delete assignments first
            if force and assignment_count > 0:
                session.query(EventRecipientPackage).filter(
                    EventRecipientPackage.recipient_id == recipient_id
                ).delete()

            # Delete recipient
            session.delete(recipient)
            session.commit()

            return True

    except (RecipientNotFound, RecipientHasAssignmentsError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete recipient: {str(e)}")


# ============================================================================
# Dependency Checking Operations
# ============================================================================


def check_recipient_has_assignments(recipient_id: int) -> bool:
    """
    Check if a recipient has any event assignments.

    Args:
        recipient_id: Recipient ID to check

    Returns:
        True if recipient has assignments, False otherwise

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            count = session.query(EventRecipientPackage).filter(
                EventRecipientPackage.recipient_id == recipient_id
            ).count()

            return count > 0

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to check recipient assignments: {str(e)}")


def get_recipient_assignment_count(recipient_id: int) -> int:
    """
    Get the number of event assignments for a recipient.

    Args:
        recipient_id: Recipient ID to check

    Returns:
        Number of assignments

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            count = session.query(EventRecipientPackage).filter(
                EventRecipientPackage.recipient_id == recipient_id
            ).count()

            return count

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipient assignment count: {str(e)}")


def get_recipient_events(recipient_id: int) -> List[Event]:
    """
    Get all events where the recipient has assignments.

    Args:
        recipient_id: Recipient ID

    Returns:
        List of Event instances (distinct)

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            events = session.query(Event).join(EventRecipientPackage).filter(
                EventRecipientPackage.recipient_id == recipient_id
            ).distinct().order_by(Event.event_date.desc()).all()

            return events

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipient events: {str(e)}")


# ============================================================================
# Search Operations
# ============================================================================


def search_recipients(query: str) -> List[Recipient]:
    """
    Search recipients by name or household name.

    Args:
        query: Search string (partial match)

    Returns:
        List of matching Recipient instances

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            recipients = session.query(Recipient).filter(
                or_(
                    Recipient.name.ilike(f"%{query}%"),
                    Recipient.household_name.ilike(f"%{query}%")
                )
            ).order_by(Recipient.name).all()

            return recipients

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to search recipients: {str(e)}")


def get_recipients_by_household(household_name: str) -> List[Recipient]:
    """
    Get all recipients belonging to a household.

    Args:
        household_name: Exact household name match

    Returns:
        List of Recipient instances

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            recipients = session.query(Recipient).filter(
                Recipient.household_name == household_name
            ).order_by(Recipient.name).all()

            return recipients

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipients by household: {str(e)}")
