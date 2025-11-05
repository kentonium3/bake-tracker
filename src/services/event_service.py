"""
Event Service - Business logic for events and planning.

This service provides:
- CRUD operations for events
- Assignment of recipients to packages for events
- Calculation of ingredient needs and shopping lists
- Event cloning and comparison
"""

from typing import List, Optional, Dict, Tuple
from datetime import datetime, date
from collections import defaultdict

from sqlalchemy import or_, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from src.models import (
    Event,
    EventRecipientPackage,
    Recipient,
    Package,
    PackageBundle,
    Bundle,
    FinishedGood,
    Recipe,
    RecipeIngredient,
    Ingredient,
)
from src.services.database import session_scope
from src.services.exceptions import DatabaseError, ValidationError


# ============================================================================
# Custom Exceptions
# ============================================================================


class EventNotFound(Exception):
    """Raised when an event is not found."""

    def __init__(self, event_id: int):
        self.event_id = event_id
        super().__init__(f"Event with ID {event_id} not found")


class EventInUse(Exception):
    """Raised when trying to delete an event that has assignments."""

    def __init__(self, event_id: int, assignment_count: int):
        self.event_id = event_id
        self.assignment_count = assignment_count
        super().__init__(
            f"Event {event_id} has {assignment_count} assignment(s) and cannot be deleted"
        )


class AssignmentNotFound(Exception):
    """Raised when an assignment is not found."""

    def __init__(self, assignment_id: int):
        self.assignment_id = assignment_id
        super().__init__(f"Assignment with ID {assignment_id} not found")


# ============================================================================
# Event CRUD Operations
# ============================================================================


def create_event(data: Dict) -> Event:
    """
    Create a new event.

    Args:
        data: Dictionary with event fields (name, event_date, year, notes)

    Returns:
        Created Event instance

    Raises:
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    # Validate required fields
    errors = []

    if not data.get("name"):
        errors.append("Name is required")

    if not data.get("event_date"):
        errors.append("Event date is required")

    if not data.get("year"):
        errors.append("Year is required")

    if errors:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            event = Event(
                name=data["name"],
                event_date=data["event_date"],
                year=data["year"],
                notes=data.get("notes"),
            )

            session.add(event)
            session.commit()

            # Reload with relationships
            event = session.query(Event).filter(Event.id == event.id).one()

            return event

    except ValidationError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to create event: {str(e)}")


def get_event(event_id: int) -> Event:
    """
    Get an event by ID with all relationships loaded.

    Args:
        event_id: Event ID

    Returns:
        Event instance

    Raises:
        EventNotFound: If event not found
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            event = (
                session.query(Event)
                .options(
                    joinedload(Event.event_recipient_packages)
                    .joinedload(EventRecipientPackage.recipient),
                    joinedload(Event.event_recipient_packages)
                    .joinedload(EventRecipientPackage.package)
                    .joinedload(Package.package_bundles)
                    .joinedload(PackageBundle.bundle)
                    .joinedload(Bundle.finished_good)
                    .joinedload(FinishedGood.recipe)
                    .joinedload(Recipe.recipe_ingredients)
                    .joinedload(RecipeIngredient.ingredient),
                )
                .filter(Event.id == event_id)
                .first()
            )

            if not event:
                raise EventNotFound(event_id)

            return event

    except EventNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get event: {str(e)}")


def get_all_events(year: Optional[int] = None) -> List[Event]:
    """
    Get all events with optional year filter.

    Args:
        year: Optional year filter

    Returns:
        List of Event instances ordered by event_date descending

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            query = session.query(Event).options(
                joinedload(Event.event_recipient_packages)
            )

            # Apply year filter if provided
            if year is not None:
                query = query.filter(Event.year == year)

            # Order by event_date descending (most recent first)
            query = query.order_by(Event.event_date.desc())

            events = query.all()

            return events

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get events: {str(e)}")


def update_event(event_id: int, data: Dict) -> Event:
    """
    Update an existing event.

    Args:
        event_id: Event ID to update
        data: Dictionary with updated event fields

    Returns:
        Updated Event instance

    Raises:
        EventNotFound: If event not found
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    # Validate required fields
    errors = []

    if not data.get("name"):
        errors.append("Name is required")

    if not data.get("event_date"):
        errors.append("Event date is required")

    if not data.get("year"):
        errors.append("Year is required")

    if errors:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise EventNotFound(event_id)

            # Update fields
            event.name = data["name"]
            event.event_date = data["event_date"]
            event.year = data["year"]
            event.notes = data.get("notes")
            event.last_modified = datetime.utcnow()

            session.commit()

            # Reload with relationships
            event = session.query(Event).filter(Event.id == event.id).one()

            return event

    except (EventNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update event: {str(e)}")


def delete_event(event_id: int) -> bool:
    """
    Delete an event.

    Args:
        event_id: Event ID to delete

    Returns:
        True if deleted successfully

    Raises:
        EventNotFound: If event not found
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise EventNotFound(event_id)

            # Delete event (cascade will delete EventRecipientPackage records)
            session.delete(event)
            session.commit()

            return True

    except EventNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete event: {str(e)}")


# ============================================================================
# Event Assignment Operations
# ============================================================================


def assign_package_to_recipient(
    event_id: int, recipient_id: int, package_id: int, quantity: int = 1, notes: str = None
) -> EventRecipientPackage:
    """
    Assign a package to a recipient for an event.

    Args:
        event_id: Event ID
        recipient_id: Recipient ID
        package_id: Package ID
        quantity: Number of packages (default 1)
        notes: Optional notes

    Returns:
        Created EventRecipientPackage instance

    Raises:
        ValidationError: If validation fails
        DatabaseError: If database operation fails
    """
    # Validate
    errors = []

    if quantity <= 0:
        errors.append("Quantity must be greater than 0")

    if errors:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            # Verify event, recipient, and package exist
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise ValidationError([f"Event with ID {event_id} not found"])

            recipient = session.query(Recipient).filter(Recipient.id == recipient_id).first()
            if not recipient:
                raise ValidationError([f"Recipient with ID {recipient_id} not found"])

            package = session.query(Package).filter(Package.id == package_id).first()
            if not package:
                raise ValidationError([f"Package with ID {package_id} not found"])

            # Create assignment
            assignment = EventRecipientPackage(
                event_id=event_id,
                recipient_id=recipient_id,
                package_id=package_id,
                quantity=quantity,
                notes=notes,
            )

            session.add(assignment)
            session.commit()

            # Reload with relationships
            assignment = (
                session.query(EventRecipientPackage)
                .options(
                    joinedload(EventRecipientPackage.recipient),
                    joinedload(EventRecipientPackage.package),
                )
                .filter(EventRecipientPackage.id == assignment.id)
                .one()
            )

            return assignment

    except ValidationError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to assign package: {str(e)}")


def get_event_assignments(event_id: int) -> List[EventRecipientPackage]:
    """
    Get all package assignments for an event.

    Args:
        event_id: Event ID

    Returns:
        List of EventRecipientPackage instances

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            assignments = (
                session.query(EventRecipientPackage)
                .options(
                    joinedload(EventRecipientPackage.recipient),
                    joinedload(EventRecipientPackage.package),
                )
                .filter(EventRecipientPackage.event_id == event_id)
                .order_by(EventRecipientPackage.recipient_id)
                .all()
            )

            return assignments

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get assignments: {str(e)}")


def update_assignment(
    assignment_id: int, package_id: int, quantity: int = 1, notes: str = None
) -> EventRecipientPackage:
    """
    Update an existing assignment.

    Args:
        assignment_id: Assignment ID
        package_id: New package ID
        quantity: New quantity
        notes: New notes

    Returns:
        Updated EventRecipientPackage instance

    Raises:
        AssignmentNotFound: If assignment not found
        ValidationError: If validation fails
        DatabaseError: If database operation fails
    """
    # Validate
    errors = []

    if quantity <= 0:
        errors.append("Quantity must be greater than 0")

    if errors:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            assignment = (
                session.query(EventRecipientPackage)
                .filter(EventRecipientPackage.id == assignment_id)
                .first()
            )
            if not assignment:
                raise AssignmentNotFound(assignment_id)

            # Verify package exists
            package = session.query(Package).filter(Package.id == package_id).first()
            if not package:
                raise ValidationError([f"Package with ID {package_id} not found"])

            # Update
            assignment.package_id = package_id
            assignment.quantity = quantity
            assignment.notes = notes

            session.commit()

            # Reload with relationships
            assignment = (
                session.query(EventRecipientPackage)
                .options(
                    joinedload(EventRecipientPackage.recipient),
                    joinedload(EventRecipientPackage.package),
                )
                .filter(EventRecipientPackage.id == assignment_id)
                .one()
            )

            return assignment

    except (AssignmentNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update assignment: {str(e)}")


def delete_assignment(assignment_id: int) -> bool:
    """
    Delete an assignment.

    Args:
        assignment_id: Assignment ID

    Returns:
        True if deleted successfully

    Raises:
        AssignmentNotFound: If assignment not found
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            assignment = (
                session.query(EventRecipientPackage)
                .filter(EventRecipientPackage.id == assignment_id)
                .first()
            )
            if not assignment:
                raise AssignmentNotFound(assignment_id)

            session.delete(assignment)
            session.commit()

            return True

    except AssignmentNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete assignment: {str(e)}")


# ============================================================================
# Event Planning and Calculation Functions
# ============================================================================


def calculate_recipe_needs(event_id: int) -> Dict[int, Dict]:
    """
    Calculate recipe batch needs for an event.

    Args:
        event_id: Event ID

    Returns:
        Dictionary: {recipe_id: {"recipe": Recipe, "batches": float, "items": int}}

    Raises:
        EventNotFound: If event not found
        DatabaseError: If database operation fails
    """
    try:
        event = get_event(event_id)

        recipe_needs = defaultdict(lambda: {"recipe": None, "batches": 0.0, "items": 0})

        # Iterate through all assignments
        for erp in event.event_recipient_packages:
            if not erp.package:
                continue

            # Iterate through bundles in package
            for pb in erp.package.package_bundles:
                if not pb.bundle or not pb.bundle.finished_good:
                    continue

                bundle = pb.bundle
                finished_good = bundle.finished_good
                recipe = finished_good.recipe

                if not recipe:
                    continue

                # Calculate items needed: package_quantity × bundle_quantity × bundles_per_package
                items_needed = erp.quantity * bundle.quantity * pb.quantity

                # Calculate batches needed based on finished good yield mode
                batches_needed = finished_good.get_batches_needed(items_needed)

                # Add to total
                recipe_id = recipe.id
                if recipe_needs[recipe_id]["recipe"] is None:
                    recipe_needs[recipe_id]["recipe"] = recipe

                recipe_needs[recipe_id]["batches"] += batches_needed
                recipe_needs[recipe_id]["items"] += items_needed

        return dict(recipe_needs)

    except EventNotFound:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to calculate recipe needs: {str(e)}")


def calculate_ingredient_needs(event_id: int) -> Dict[int, Dict]:
    """
    Calculate ingredient needs for an event.

    Args:
        event_id: Event ID

    Returns:
        Dictionary: {ingredient_id: {"ingredient": Ingredient, "quantity": float, "unit": str}}

    Raises:
        EventNotFound: If event not found
        DatabaseError: If database operation fails
    """
    try:
        # Get recipe needs first
        recipe_needs = calculate_recipe_needs(event_id)

        ingredient_needs = defaultdict(lambda: {"ingredient": None, "quantity": 0.0, "unit": None})

        # Import converter for unit conversions
        from src.services.unit_converter import convert_any_units

        # Iterate through recipe needs
        for recipe_data in recipe_needs.values():
            recipe = recipe_data["recipe"]
            batches = recipe_data["batches"]

            # Iterate through recipe ingredients
            for recipe_ingredient in recipe.recipe_ingredients:
                ingredient = recipe_ingredient.ingredient
                if not ingredient:
                    continue

                # Calculate quantity needed for this recipe (recipe_unit × batches)
                quantity_in_recipe_unit = recipe_ingredient.quantity * batches

                # Convert to ingredient's purchase unit
                ingredient_density = ingredient.get_density() if hasattr(ingredient, "get_density") else 0.0

                try:
                    quantity_in_purchase_unit = convert_any_units(
                        quantity_in_recipe_unit,
                        recipe_ingredient.unit,
                        ingredient.purchase_unit,
                        ingredient_density,
                    )
                except Exception:
                    # If conversion fails, use recipe unit as-is
                    quantity_in_purchase_unit = quantity_in_recipe_unit

                # Add to total
                ingredient_id = ingredient.id
                if ingredient_needs[ingredient_id]["ingredient"] is None:
                    ingredient_needs[ingredient_id]["ingredient"] = ingredient
                    ingredient_needs[ingredient_id]["unit"] = ingredient.purchase_unit

                ingredient_needs[ingredient_id]["quantity"] += quantity_in_purchase_unit

        return dict(ingredient_needs)

    except EventNotFound:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to calculate ingredient needs: {str(e)}")


def generate_shopping_list(event_id: int) -> List[Dict]:
    """
    Generate shopping list comparing needs vs current inventory.

    Args:
        event_id: Event ID

    Returns:
        List of dictionaries with shopping items:
        [{
            "ingredient": Ingredient,
            "needed": float,
            "on_hand": float,
            "to_buy": float,
            "unit": str,
            "cost": float
        }]

    Raises:
        EventNotFound: If event not found
        DatabaseError: If database operation fails
    """
    try:
        ingredient_needs = calculate_ingredient_needs(event_id)

        shopping_list = []

        for ingredient_id, need_data in ingredient_needs.items():
            ingredient = need_data["ingredient"]
            needed = need_data["quantity"]
            on_hand = ingredient.quantity if ingredient.quantity else 0.0
            to_buy = max(0.0, needed - on_hand)

            # Calculate cost (to_buy / purchase_quantity × unit_cost)
            if ingredient.purchase_quantity and ingredient.purchase_quantity > 0:
                cost = (to_buy / ingredient.purchase_quantity) * ingredient.unit_cost
            else:
                cost = 0.0

            shopping_list.append({
                "ingredient": ingredient,
                "needed": needed,
                "on_hand": on_hand,
                "to_buy": to_buy,
                "unit": need_data["unit"],
                "cost": cost,
            })

        # Sort by ingredient name
        shopping_list.sort(key=lambda x: x["ingredient"].name)

        return shopping_list

    except EventNotFound:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to generate shopping list: {str(e)}")


def clone_event(source_event_id: int, new_name: str, new_year: int, new_event_date: date) -> Event:
    """
    Clone an event and all its assignments to a new year.

    Args:
        source_event_id: Event ID to clone
        new_name: Name for new event
        new_year: Year for new event
        new_event_date: Date for new event

    Returns:
        New Event instance with cloned assignments

    Raises:
        EventNotFound: If source event not found
        ValidationError: If validation fails
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            # Get source event with assignments
            source_event = (
                session.query(Event)
                .options(
                    joinedload(Event.event_recipient_packages)
                )
                .filter(Event.id == source_event_id)
                .first()
            )

            if not source_event:
                raise EventNotFound(source_event_id)

            # Create new event
            new_event = Event(
                name=new_name,
                event_date=new_event_date,
                year=new_year,
                notes=source_event.notes,
            )
            session.add(new_event)
            session.flush()  # Get new_event.id

            # Clone assignments
            for source_assignment in source_event.event_recipient_packages:
                new_assignment = EventRecipientPackage(
                    event_id=new_event.id,
                    recipient_id=source_assignment.recipient_id,
                    package_id=source_assignment.package_id,
                    quantity=source_assignment.quantity,
                    notes=source_assignment.notes,
                )
                session.add(new_assignment)

            session.commit()

            # Reload with relationships
            new_event = session.query(Event).filter(Event.id == new_event.id).one()

            return new_event

    except EventNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to clone event: {str(e)}")


def get_recipient_history(recipient_id: int) -> List[Dict]:
    """
    Get package history for a recipient across all events.

    Args:
        recipient_id: Recipient ID

    Returns:
        List of dictionaries with event assignments:
        [{
            "event": Event,
            "package": Package,
            "quantity": int,
            "notes": str
        }]
        Ordered by event date descending

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            assignments = (
                session.query(EventRecipientPackage)
                .join(Event)
                .options(
                    joinedload(EventRecipientPackage.event),
                    joinedload(EventRecipientPackage.package),
                )
                .filter(EventRecipientPackage.recipient_id == recipient_id)
                .order_by(Event.event_date.desc())
                .all()
            )

            history = []
            for assignment in assignments:
                history.append({
                    "event": assignment.event,
                    "package": assignment.package,
                    "quantity": assignment.quantity,
                    "notes": assignment.notes,
                })

            return history

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipient history: {str(e)}")
