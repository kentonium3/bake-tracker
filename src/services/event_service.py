"""
Event Service - Business logic for events and planning.

This service provides:
- CRUD operations for events
- Assignment of recipients to packages for events
- Calculation of ingredient needs and shopping lists
- Event cloning and comparison

Architecture Note (Feature 006):
- Bundle concept eliminated per research decision D1
- Package now references FinishedGood assemblies via PackageFinishedGood
- Cost calculation chains: Event -> ERP -> Package -> FinishedGood for FIFO accuracy
- Recipe needs traverse: Package -> FinishedGood -> Composition -> FinishedUnit -> Recipe
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from collections import defaultdict
from math import ceil

from sqlalchemy import or_, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from src.models import (
    Event,
    EventRecipientPackage,
    Recipient,
    Package,
    PackageFinishedGood,
    FinishedGood,
    FinishedUnit,
    Composition,
    Recipe,
    RecipeIngredient,
    Ingredient,
)
from src.services.database import session_scope
from src.services.exceptions import DatabaseError, ValidationError


# ============================================================================
# Custom Exceptions
# ============================================================================


class EventNotFoundError(Exception):
    """Raised when an event is not found."""

    def __init__(self, event_id: int):
        self.event_id = event_id
        super().__init__(f"Event with ID {event_id} not found")


class EventHasAssignmentsError(Exception):
    """Raised when trying to delete an event that has assignments."""

    def __init__(self, event_id: int, assignment_count: int):
        self.event_id = event_id
        self.assignment_count = assignment_count
        super().__init__(
            f"Event {event_id} has {assignment_count} assignment(s). Use cascade_assignments=True to delete."
        )


class AssignmentNotFoundError(Exception):
    """Raised when an assignment is not found."""

    def __init__(self, assignment_id: int):
        self.assignment_id = assignment_id
        super().__init__(f"Assignment with ID {assignment_id} not found")


class RecipientNotFoundError(Exception):
    """Raised when a recipient is not found."""

    def __init__(self, recipient_id: int):
        self.recipient_id = recipient_id
        super().__init__(f"Recipient with ID {recipient_id} not found")


class DuplicateAssignmentError(Exception):
    """Raised when assignment already exists."""

    def __init__(self, event_id: int, recipient_id: int, package_id: int):
        self.event_id = event_id
        self.recipient_id = recipient_id
        self.package_id = package_id
        super().__init__(
            f"Assignment already exists: Event {event_id}, Recipient {recipient_id}, Package {package_id}"
        )


# ============================================================================
# Event CRUD Operations
# ============================================================================


def create_event(
    name: str,
    event_date: date,
    year: int,
    notes: Optional[str] = None,
) -> Event:
    """
    Create a new event.

    Args:
        name: Event name (required)
        event_date: Event date (required)
        year: Event year (required)
        notes: Optional notes

    Returns:
        Created Event instance

    Raises:
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    errors = []
    if not name or not name.strip():
        errors.append("Name is required")
    if not event_date:
        errors.append("Event date is required")
    if not year:
        errors.append("Year is required")
    if errors:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            event = Event(
                name=name.strip(),
                event_date=event_date,
                year=year,
                notes=notes,
            )
            session.add(event)
            session.flush()

            # Reload with relationships
            event = (
                session.query(Event)
                .options(joinedload(Event.event_recipient_packages))
                .filter(Event.id == event.id)
                .one()
            )
            return event

    except ValidationError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to create event: {str(e)}")


def get_event_by_id(event_id: int) -> Optional[Event]:
    """
    Get an event by ID.

    Args:
        event_id: Event ID

    Returns:
        Event instance or None if not found
    """
    try:
        with session_scope() as session:
            event = (
                session.query(Event)
                .options(
                    joinedload(Event.event_recipient_packages).joinedload(
                        EventRecipientPackage.recipient
                    ),
                    joinedload(Event.event_recipient_packages).joinedload(
                        EventRecipientPackage.package
                    ),
                )
                .filter(Event.id == event_id)
                .first()
            )
            return event

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get event: {str(e)}")


def get_event_by_name(name: str) -> Optional[Event]:
    """
    Get an event by exact name match.

    Args:
        name: Event name

    Returns:
        Event instance or None if not found
    """
    try:
        with session_scope() as session:
            event = (
                session.query(Event)
                .options(joinedload(Event.event_recipient_packages))
                .filter(Event.name == name)
                .first()
            )
            return event

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get event by name: {str(e)}")


def get_all_events() -> List[Event]:
    """
    Get all events ordered by event_date descending.

    Returns:
        List of Event instances
    """
    try:
        with session_scope() as session:
            events = (
                session.query(Event)
                .options(joinedload(Event.event_recipient_packages))
                .order_by(Event.event_date.desc())
                .all()
            )
            return events

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get events: {str(e)}")


def get_events_by_year(year: int) -> List[Event]:
    """
    Get events filtered by year (FR-020).

    Args:
        year: Year to filter by

    Returns:
        List of Event instances for that year
    """
    try:
        with session_scope() as session:
            events = (
                session.query(Event)
                .options(joinedload(Event.event_recipient_packages))
                .filter(Event.year == year)
                .order_by(Event.event_date.desc())
                .all()
            )
            return events

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get events by year: {str(e)}")


def get_available_years() -> List[int]:
    """
    Get list of distinct years with events (for year filter dropdown).

    Returns:
        List of years in descending order
    """
    try:
        with session_scope() as session:
            years = session.query(Event.year).distinct().order_by(Event.year.desc()).all()
            return [y[0] for y in years]

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get available years: {str(e)}")


def update_event(event_id: int, **updates) -> Event:
    """
    Update an existing event.

    Args:
        event_id: Event ID to update
        **updates: Field updates (name, event_date, year, notes)

    Returns:
        Updated Event instance

    Raises:
        EventNotFoundError: If event not found
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise EventNotFoundError(event_id)

            if "name" in updates:
                name = updates["name"]
                if not name or not name.strip():
                    raise ValidationError(["Name is required"])
                event.name = name.strip()

            if "event_date" in updates:
                event.event_date = updates["event_date"]

            if "year" in updates:
                event.year = updates["year"]

            if "notes" in updates:
                event.notes = updates["notes"]

            event.last_modified = datetime.utcnow()
            session.flush()

            # Reload with relationships
            event = (
                session.query(Event)
                .options(joinedload(Event.event_recipient_packages))
                .filter(Event.id == event.id)
                .one()
            )
            return event

    except (EventNotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update event: {str(e)}")


def delete_event(event_id: int, cascade_assignments: bool = False) -> bool:
    """
    Delete an event.

    Args:
        event_id: Event ID to delete
        cascade_assignments: If True, delete assignments too (FR-022)

    Returns:
        True if deleted successfully

    Raises:
        EventNotFoundError: If event not found
        EventHasAssignmentsError: If event has assignments and cascade_assignments=False
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            event = (
                session.query(Event)
                .options(joinedload(Event.event_recipient_packages))
                .filter(Event.id == event_id)
                .first()
            )
            if not event:
                raise EventNotFoundError(event_id)

            assignment_count = len(event.event_recipient_packages)
            if assignment_count > 0 and not cascade_assignments:
                raise EventHasAssignmentsError(event_id, assignment_count)

            # Delete event (cascade will delete assignments if configured)
            session.delete(event)
            return True

    except (EventNotFoundError, EventHasAssignmentsError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete event: {str(e)}")


# ============================================================================
# Event Assignment Operations (FR-024)
# ============================================================================


def assign_package_to_recipient(
    event_id: int,
    recipient_id: int,
    package_id: int,
    quantity: int = 1,
    notes: Optional[str] = None,
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
    if quantity < 1:
        raise ValidationError(["Quantity must be at least 1"])

    try:
        with session_scope() as session:
            # Verify event exists
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise ValidationError([f"Event with ID {event_id} not found"])

            # Verify recipient exists
            recipient = session.query(Recipient).filter(Recipient.id == recipient_id).first()
            if not recipient:
                raise ValidationError([f"Recipient with ID {recipient_id} not found"])

            # Verify package exists
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
            session.flush()

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


def update_assignment(
    assignment_id: int,
    package_id: Optional[int] = None,
    quantity: Optional[int] = None,
    notes: Optional[str] = None,
) -> EventRecipientPackage:
    """
    Update an existing assignment.

    Args:
        assignment_id: Assignment ID
        package_id: New package ID (optional)
        quantity: New quantity (optional)
        notes: New notes (optional)

    Returns:
        Updated EventRecipientPackage instance

    Raises:
        AssignmentNotFoundError: If assignment not found
        ValidationError: If validation fails
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
                raise AssignmentNotFoundError(assignment_id)

            if package_id is not None:
                # Verify package exists
                package = session.query(Package).filter(Package.id == package_id).first()
                if not package:
                    raise ValidationError([f"Package with ID {package_id} not found"])
                assignment.package_id = package_id

            if quantity is not None:
                if quantity < 1:
                    raise ValidationError(["Quantity must be at least 1"])
                assignment.quantity = quantity

            if notes is not None:
                assignment.notes = notes

            session.flush()

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

    except (AssignmentNotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update assignment: {str(e)}")


def remove_assignment(assignment_id: int) -> bool:
    """
    Remove an assignment.

    Args:
        assignment_id: Assignment ID

    Returns:
        True if removed successfully

    Raises:
        AssignmentNotFoundError: If assignment not found
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
                raise AssignmentNotFoundError(assignment_id)

            session.delete(assignment)
            return True

    except AssignmentNotFoundError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to remove assignment: {str(e)}")


def get_event_assignments(event_id: int) -> List[EventRecipientPackage]:
    """
    Get all assignments for an event.

    Args:
        event_id: Event ID

    Returns:
        List of EventRecipientPackage instances
    """
    try:
        with session_scope() as session:
            assignments = (
                session.query(EventRecipientPackage)
                .options(
                    joinedload(EventRecipientPackage.recipient),
                    joinedload(EventRecipientPackage.package).joinedload(
                        Package.package_finished_goods
                    ),
                )
                .filter(EventRecipientPackage.event_id == event_id)
                .order_by(EventRecipientPackage.recipient_id)
                .all()
            )
            return assignments

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get assignments: {str(e)}")


def get_recipient_assignments_for_event(
    event_id: int, recipient_id: int
) -> List[EventRecipientPackage]:
    """
    Get all assignments for a specific recipient in an event.

    Args:
        event_id: Event ID
        recipient_id: Recipient ID

    Returns:
        List of EventRecipientPackage instances
    """
    try:
        with session_scope() as session:
            assignments = (
                session.query(EventRecipientPackage)
                .options(
                    joinedload(EventRecipientPackage.package),
                )
                .filter(
                    EventRecipientPackage.event_id == event_id,
                    EventRecipientPackage.recipient_id == recipient_id,
                )
                .all()
            )
            return assignments

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipient assignments: {str(e)}")


# ============================================================================
# Event Cost Calculations
# ============================================================================


def get_event_total_cost(event_id: int) -> Decimal:
    """
    Calculate total cost of all packages in an event.

    Cost chains through: Event -> ERP -> Package -> FinishedGood for FIFO accuracy.

    Args:
        event_id: Event ID

    Returns:
        Total cost as Decimal
    """
    try:
        with session_scope() as session:
            event = (
                session.query(Event)
                .options(
                    joinedload(Event.event_recipient_packages)
                    .joinedload(EventRecipientPackage.package)
                    .joinedload(Package.package_finished_goods)
                    .joinedload(PackageFinishedGood.finished_good)
                )
                .filter(Event.id == event_id)
                .first()
            )

            if not event:
                return Decimal("0.00")

            return event.get_total_cost()

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to calculate event cost: {str(e)}")


def get_event_recipient_count(event_id: int) -> int:
    """
    Get number of unique recipients in an event.

    Args:
        event_id: Event ID

    Returns:
        Number of unique recipients
    """
    try:
        with session_scope() as session:
            event = (
                session.query(Event)
                .options(joinedload(Event.event_recipient_packages))
                .filter(Event.id == event_id)
                .first()
            )

            if not event:
                return 0

            return event.get_recipient_count()

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to count recipients: {str(e)}")


def get_event_package_count(event_id: int) -> int:
    """
    Get total number of packages in an event (sum of quantities).

    Args:
        event_id: Event ID

    Returns:
        Total package count
    """
    try:
        with session_scope() as session:
            event = (
                session.query(Event)
                .options(joinedload(Event.event_recipient_packages))
                .filter(Event.id == event_id)
                .first()
            )

            if not event:
                return 0

            return event.get_package_count()

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to count packages: {str(e)}")


# ============================================================================
# Event Summary (FR-027)
# ============================================================================


def get_event_summary(event_id: int) -> Dict[str, Any]:
    """
    Get complete event summary for Summary tab.

    Args:
        event_id: Event ID

    Returns:
        Dict with total_cost, recipient_count, package_count, assignment_count, cost_by_recipient
    """
    try:
        with session_scope() as session:
            event = (
                session.query(Event)
                .options(
                    joinedload(Event.event_recipient_packages).joinedload(
                        EventRecipientPackage.recipient
                    ),
                    joinedload(Event.event_recipient_packages)
                    .joinedload(EventRecipientPackage.package)
                    .joinedload(Package.package_finished_goods)
                    .joinedload(PackageFinishedGood.finished_good),
                )
                .filter(Event.id == event_id)
                .first()
            )

            if not event:
                return {
                    "total_cost": Decimal("0.00"),
                    "recipient_count": 0,
                    "package_count": 0,
                    "assignment_count": 0,
                    "cost_by_recipient": [],
                }

            # Calculate cost by recipient
            cost_by_recipient = {}
            for erp in event.event_recipient_packages:
                recipient_name = erp.recipient.name if erp.recipient else "Unknown"
                assignment_cost = erp.calculate_cost()
                cost_by_recipient[recipient_name] = (
                    cost_by_recipient.get(recipient_name, Decimal("0.00")) + assignment_cost
                )

            return {
                "total_cost": event.get_total_cost(),
                "recipient_count": event.get_recipient_count(),
                "package_count": event.get_package_count(),
                "assignment_count": len(event.event_recipient_packages),
                "cost_by_recipient": [
                    {"recipient_name": name, "cost": cost}
                    for name, cost in sorted(cost_by_recipient.items())
                ],
            }

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get event summary: {str(e)}")


# ============================================================================
# Recipe Needs (FR-025)
# ============================================================================


def get_recipe_needs(event_id: int) -> List[Dict[str, Any]]:
    """
    Calculate batch counts needed for all recipes in an event.

    Traverses: Event -> ERP -> Package -> FinishedGood -> Composition -> FinishedUnit -> Recipe

    Args:
        event_id: Event ID

    Returns:
        List of dicts with recipe_id, recipe_name, total_units_needed, batches_needed, items_per_batch
    """
    try:
        with session_scope() as session:
            # Load event with full traversal chain
            event = (
                session.query(Event)
                .options(
                    joinedload(Event.event_recipient_packages)
                    .joinedload(EventRecipientPackage.package)
                    .joinedload(Package.package_finished_goods)
                    .joinedload(PackageFinishedGood.finished_good)
                    .joinedload(FinishedGood.components)
                    .joinedload(Composition.finished_unit_component)
                    .joinedload(FinishedUnit.recipe)
                )
                .filter(Event.id == event_id)
                .first()
            )

            if not event:
                return []

            # Aggregate recipe needs
            recipe_totals: Dict[int, int] = {}  # recipe_id -> total units needed
            recipe_info: Dict[int, Dict] = {}  # recipe_id -> {name, items_per_batch}

            for erp in event.event_recipient_packages:
                if not erp.package:
                    continue

                for pfg in erp.package.package_finished_goods:
                    if not pfg.finished_good:
                        continue

                    fg = pfg.finished_good

                    # Traverse compositions to get FinishedUnits
                    for composition in fg.components:
                        if not composition.finished_unit_component:
                            continue

                        fu = composition.finished_unit_component
                        if not fu.recipe:
                            continue

                        recipe_id = fu.recipe_id
                        items_per_batch = fu.items_per_batch or 1

                        # Calculate units: composition_qty * pfg_qty * erp_qty
                        units = int(composition.component_quantity) * pfg.quantity * erp.quantity

                        recipe_totals[recipe_id] = recipe_totals.get(recipe_id, 0) + units
                        recipe_info[recipe_id] = {
                            "name": fu.recipe.name,
                            "items_per_batch": items_per_batch,
                        }

            # Build result
            result = []
            for recipe_id, total_units in recipe_totals.items():
                info = recipe_info[recipe_id]
                batches_needed = ceil(total_units / info["items_per_batch"])
                result.append(
                    {
                        "recipe_id": recipe_id,
                        "recipe_name": info["name"],
                        "total_units_needed": total_units,
                        "batches_needed": batches_needed,
                        "items_per_batch": info["items_per_batch"],
                    }
                )

            # Sort by recipe name
            result.sort(key=lambda x: x["recipe_name"])
            return result

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to calculate recipe needs: {str(e)}")


# ============================================================================
# Shopping List (FR-026)
# ============================================================================


def get_shopping_list(event_id: int) -> List[Dict[str, Any]]:
    """
    Calculate ingredients needed with pantry comparison.

    Args:
        event_id: Event ID

    Returns:
        List of dicts with ingredient_id, ingredient_name, unit, quantity_needed, quantity_on_hand, shortfall
    """
    try:
        # Get recipe needs first
        recipe_needs = get_recipe_needs(event_id)

        if not recipe_needs:
            return []

        with session_scope() as session:
            # Aggregate ingredient needs across all recipes
            ingredient_totals: Dict[int, Decimal] = {}  # ingredient_id -> quantity needed
            ingredient_info: Dict[int, Dict] = {}  # ingredient_id -> {name, unit}

            for recipe_need in recipe_needs:
                recipe_id = recipe_need["recipe_id"]
                batches_needed = recipe_need["batches_needed"]

                # Get recipe with ingredients
                recipe = (
                    session.query(Recipe)
                    .options(
                        joinedload(Recipe.recipe_ingredients).joinedload(
                            RecipeIngredient.ingredient
                        )
                    )
                    .filter(Recipe.id == recipe_id)
                    .first()
                )

                if not recipe:
                    continue

                for ri in recipe.recipe_ingredients:
                    if not ri.ingredient:
                        continue

                    ing_id = ri.ingredient_id
                    # Scale quantity by batches needed
                    qty = Decimal(str(ri.quantity)) * Decimal(str(batches_needed))

                    ingredient_totals[ing_id] = ingredient_totals.get(ing_id, Decimal("0")) + qty
                    ingredient_info[ing_id] = {
                        "name": ri.ingredient.display_name,
                        "unit": ri.unit,
                    }

            # Get on-hand quantities from pantry
            # Import here to avoid circular imports
            from src.services import pantry_service

            result = []
            for ing_id, qty_needed in ingredient_totals.items():
                info = ingredient_info[ing_id]

                # Get on-hand quantity from pantry service
                try:
                    qty_on_hand = Decimal(
                        str(pantry_service.get_ingredient_quantity_on_hand(ing_id))
                    )
                except Exception:
                    qty_on_hand = Decimal("0")

                shortfall = max(Decimal("0"), qty_needed - qty_on_hand)

                result.append(
                    {
                        "ingredient_id": ing_id,
                        "ingredient_name": info["name"],
                        "unit": info["unit"],
                        "quantity_needed": qty_needed,
                        "quantity_on_hand": qty_on_hand,
                        "shortfall": shortfall,
                    }
                )

            # Sort by ingredient name
            result.sort(key=lambda x: x["ingredient_name"])
            return result

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to generate shopping list: {str(e)}")


# ============================================================================
# Event Cloning
# ============================================================================


def clone_event(
    source_event_id: int,
    new_name: str,
    new_year: int,
    new_event_date: date,
) -> Event:
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
        EventNotFoundError: If source event not found
        ValidationError: If validation fails
        DatabaseError: If database operation fails
    """
    if not new_name or not new_name.strip():
        raise ValidationError(["New event name is required"])

    try:
        with session_scope() as session:
            # Get source event with assignments
            source_event = (
                session.query(Event)
                .options(joinedload(Event.event_recipient_packages))
                .filter(Event.id == source_event_id)
                .first()
            )

            if not source_event:
                raise EventNotFoundError(source_event_id)

            # Create new event
            new_event = Event(
                name=new_name.strip(),
                event_date=new_event_date,
                year=new_year,
                notes=source_event.notes,
            )
            session.add(new_event)
            session.flush()

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

            session.flush()

            # Reload with relationships
            new_event = (
                session.query(Event)
                .options(joinedload(Event.event_recipient_packages))
                .filter(Event.id == new_event.id)
                .one()
            )
            return new_event

    except (EventNotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to clone event: {str(e)}")


# ============================================================================
# Recipient History
# ============================================================================


def get_recipient_history(recipient_id: int) -> List[Dict[str, Any]]:
    """
    Get package history for a recipient across all events.

    Args:
        recipient_id: Recipient ID

    Returns:
        List of dicts with event, package, quantity, notes - ordered by event date descending
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

            return [
                {
                    "event": assignment.event,
                    "package": assignment.package,
                    "quantity": assignment.quantity,
                    "notes": assignment.notes,
                }
                for assignment in assignments
            ]

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipient history: {str(e)}")
