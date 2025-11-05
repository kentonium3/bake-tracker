"""
Recipient Service - Business logic for package recipients.

This service provides CRUD operations for:
- Recipients (people who receive gift packages)
"""

from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from src.models import Recipient
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


def delete_recipient(recipient_id: int) -> bool:
    """
    Delete a recipient.

    Args:
        recipient_id: Recipient ID to delete

    Returns:
        True if deleted successfully

    Raises:
        RecipientNotFound: If recipient not found
        RecipientInUse: If recipient is used in events
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            # Get recipient
            recipient = session.query(Recipient).filter(Recipient.id == recipient_id).first()
            if not recipient:
                raise RecipientNotFound(recipient_id)

            # TODO: Check if recipient is used in events (Phase 3b)
            # For now, just delete

            # Delete recipient
            session.delete(recipient)
            session.commit()

            return True

    except RecipientNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete recipient: {str(e)}")
