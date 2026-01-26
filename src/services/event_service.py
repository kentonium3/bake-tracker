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
from dataclasses import dataclass
from datetime import datetime, date
from src.utils.datetime_utils import utc_now
from decimal import Decimal
from math import ceil
import csv

from sqlalchemy import and_, func  # noqa: F401 - used in complex queries
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from src.services.dto_utils import cost_to_string

from src.models import (
    Event,
    EventRecipientPackage,
    EventProductionTarget,
    EventAssemblyTarget,
    FulfillmentStatus,
    PlanState,  # Feature 068
    ProductionRun,
    AssemblyRun,
    Recipient,
    Package,
    PackageFinishedGood,
    FinishedGood,
    FinishedUnit,
    Composition,
    Recipe,
    RecipeIngredient,
    Product,
    InventoryItem,
)
from src.services.database import session_scope
from src.services.exceptions import DatabaseError, ValidationError


# ============================================================================
# Feature 011: Packaging Data Classes
# ============================================================================


@dataclass
class PackagingNeed:
    """Represents packaging requirement for shopping list."""

    product_id: int
    product: Product
    ingredient_name: str
    product_display_name: str
    total_needed: float
    on_hand: float
    to_buy: float
    unit: str
    # Feature 026: Generic packaging support
    is_generic: bool = False
    generic_product_name: Optional[str] = None
    estimated_cost: Optional[Decimal] = None


@dataclass
class PackagingSource:
    """Tracks where packaging need originated."""

    source_type: str  # "finished_good" or "package"
    source_id: int
    source_name: str
    quantity_per: float
    source_count: int
    total_for_source: float


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
    *,
    session: Session,
) -> Event:
    """
    Create a new event.

    Args:
        name: Event name (required)
        event_date: Event date (required)
        year: Event year (required)
        notes: Optional notes
        session: Database session (required)

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


def get_event_by_id(event_id: int, *, session: Session) -> Optional[Event]:
    """
    Get an event by ID.

    Args:
        event_id: Event ID
        session: Database session (required)

    Returns:
        Event instance or None if not found
    """
    try:
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


def get_event_by_name(name: str, *, session: Session) -> Optional[Event]:
    """
    Get an event by exact name match.

    Args:
        name: Event name
        session: Database session (required)

    Returns:
        Event instance or None if not found
    """
    try:
        event = (
            session.query(Event)
            .options(joinedload(Event.event_recipient_packages))
            .filter(Event.name == name)
            .first()
        )
        return event

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get event by name: {str(e)}")


def get_all_events(*, session: Session) -> List[Event]:
    """
    Get all events ordered by event_date descending.

    Args:
        session: Database session (required)

    Returns:
        List of Event instances
    """
    try:
        events = (
            session.query(Event)
            .options(joinedload(Event.event_recipient_packages))
            .order_by(Event.event_date.desc())
            .all()
        )
        return events

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get events: {str(e)}")


def get_events_by_year(year: int, *, session: Session) -> List[Event]:
    """
    Get events filtered by year (FR-020).

    Args:
        year: Year to filter by
        session: Database session (required)

    Returns:
        List of Event instances for that year
    """
    try:
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


def get_available_years(*, session: Session) -> List[int]:
    """
    Get list of distinct years with events (for year filter dropdown).

    Args:
        session: Database session (required)

    Returns:
        List of years in descending order
    """
    try:
        years = session.query(Event.year).distinct().order_by(Event.year.desc()).all()
        return [y[0] for y in years]

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get available years: {str(e)}")


def update_event(event_id: int, *, session: Session, **updates) -> Event:
    """
    Update an existing event.

    Args:
        event_id: Event ID to update
        session: Database session (required)
        **updates: Field updates (name, event_date, year, notes)

    Returns:
        Updated Event instance

    Raises:
        EventNotFoundError: If event not found
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    try:
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

        event.last_modified = utc_now()
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


def delete_event(
    event_id: int, cascade_assignments: bool = False, *, session: Session
) -> bool:
    """
    Delete an event.

    Args:
        event_id: Event ID to delete
        cascade_assignments: If True, delete assignments too (FR-022)
        session: Database session (required)

    Returns:
        True if deleted successfully

    Raises:
        EventNotFoundError: If event not found
        EventHasAssignmentsError: If event has assignments and cascade_assignments=False
        DatabaseError: If database operation fails
    """
    try:
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
    *,
    session: Session,
) -> EventRecipientPackage:
    """
    Assign a package to a recipient for an event.

    Args:
        event_id: Event ID
        recipient_id: Recipient ID
        package_id: Package ID
        quantity: Number of packages (default 1)
        notes: Optional notes
        session: Database session (required)

    Returns:
        Created EventRecipientPackage instance

    Raises:
        ValidationError: If validation fails
        DatabaseError: If database operation fails
    """
    if quantity < 1:
        raise ValidationError(["Quantity must be at least 1"])

    try:
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
    *,
    session: Session,
) -> EventRecipientPackage:
    """
    Update an existing assignment.

    Args:
        assignment_id: Assignment ID
        package_id: New package ID (optional)
        quantity: New quantity (optional)
        notes: New notes (optional)
        session: Database session (required)

    Returns:
        Updated EventRecipientPackage instance

    Raises:
        AssignmentNotFoundError: If assignment not found
        ValidationError: If validation fails
        DatabaseError: If database operation fails
    """
    try:
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


def remove_assignment(assignment_id: int, *, session: Session) -> bool:
    """
    Remove an assignment.

    Args:
        assignment_id: Assignment ID
        session: Database session (required)

    Returns:
        True if removed successfully

    Raises:
        AssignmentNotFoundError: If assignment not found
        DatabaseError: If database operation fails
    """
    try:
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


def get_event_assignments(event_id: int, *, session: Session) -> List[EventRecipientPackage]:
    """
    Get all assignments for an event.

    Args:
        event_id: Event ID
        session: Database session (required)

    Returns:
        List of EventRecipientPackage instances
    """
    try:
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
    event_id: int, recipient_id: int, *, session: Session
) -> List[EventRecipientPackage]:
    """
    Get all assignments for a specific recipient in an event.

    Args:
        event_id: Event ID
        recipient_id: Recipient ID
        session: Database session (required)

    Returns:
        List of EventRecipientPackage instances
    """
    try:
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


def get_event_total_cost(event_id: int, *, session: Session) -> Decimal:
    """
    Calculate total cost of all packages in an event.

    Cost chains through: Event -> ERP -> Package -> FinishedGood for FIFO accuracy.

    Args:
        event_id: Event ID
        session: Database session (required)

    Returns:
        Total cost as Decimal
    """
    try:
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


def get_event_recipient_count(event_id: int, *, session: Session) -> int:
    """
    Get number of unique recipients in an event.

    Args:
        event_id: Event ID
        session: Database session (required)

    Returns:
        Number of unique recipients
    """
    try:
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


def get_event_package_count(event_id: int, *, session: Session) -> int:
    """
    Get total number of packages in an event (sum of quantities).

    Args:
        event_id: Event ID
        session: Database session (required)

    Returns:
        Total package count
    """
    try:
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


def get_event_summary(event_id: int, *, session: Session) -> Dict[str, Any]:
    """
    Get complete event summary for Summary tab.

    Args:
        event_id: Event ID
        session: Database session (required)

    Returns:
        Dict with total_cost, recipient_count, package_count, assignment_count, cost_by_recipient
    """
    try:
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
                "total_cost": "0.00",
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
            "total_cost": cost_to_string(event.get_total_cost()),
            "recipient_count": event.get_recipient_count(),
            "package_count": event.get_package_count(),
            "assignment_count": len(event.event_recipient_packages),
            "cost_by_recipient": [
                {"recipient_name": name, "cost": cost_to_string(cost)}
                for name, cost in sorted(cost_by_recipient.items())
            ],
        }

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get event summary: {str(e)}")


# ============================================================================
# Recipe Needs (FR-025)
# ============================================================================


def get_recipe_needs(event_id: int, *, session: Session) -> List[Dict[str, Any]]:
    """
    Calculate batch counts needed for all recipes in an event.

    Traverses: Event -> ERP -> Package -> FinishedGood -> Composition -> FinishedUnit -> Recipe

    Args:
        event_id: Event ID
        session: Database session (required)

    Returns:
        List of dicts with recipe_id, recipe_name, total_units_needed, batches_needed, items_per_batch
    """
    try:
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
# Shopping List (FR-026) - Extended for Feature 007 Product Recommendations
# ============================================================================


def _calculate_total_estimated_cost(items: List[Dict[str, Any]]) -> Decimal:
    """
    Calculate total estimated cost for shopping list.

    Only includes items with:
    - product_status = 'preferred' (user has a clear recommendation)
    - product_recommendation is not None
    - product_recommendation has valid total_cost

    Items with 'multiple' status are excluded (user hasn't chosen).
    Items with 'none' status are excluded (no product to price).
    Items with 'sufficient' status are excluded (no purchase needed).

    Args:
        items: List of shopping list item dicts

    Returns:
        Total estimated cost as Decimal
    """
    total = Decimal("0.00")
    for item in items:
        if item.get("product_status") == "preferred":
            rec = item.get("product_recommendation")
            if rec and rec.get("total_cost"):
                total += Decimal(str(rec["total_cost"]))
    return total


def get_shopping_list(
    event_id: int,
    session: Session,
    include_packaging: bool = True,
) -> Dict[str, Any]:
    """
    Calculate ingredients needed with inventory comparison and product recommendations.

    Feature 007 Extension: Each item with a shortfall includes product
    recommendation data (product_status, product_recommendation, all_products).

    Feature 011 Extension: Optionally includes packaging materials section.

    Args:
        event_id: Event ID
        include_packaging: Whether to include packaging section (default True)
        session: SQLAlchemy session for database operations

    Returns:
        Dict with:
        - items: List of shopping list items with product data
        - total_estimated_cost: Sum of preferred product purchase costs
        - items_count: Total number of ingredients
        - items_with_shortfall: Count of items needing purchase
        - packaging: List of packaging needs (if include_packaging=True and needs exist)
    """
    # Use provided session or create new one
    if session is not None:
        return _get_shopping_list_with_session(event_id, include_packaging, session)

    try:
        with session_scope() as session:
            return _get_shopping_list_with_session(event_id, include_packaging, session)
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to generate shopping list: {str(e)}")


def _get_shopping_list_with_session(
    event_id: int, include_packaging: bool, session: Session
) -> Dict[str, Any]:
    """Get shopping list using provided session."""
    # Get recipe needs first (pass session since it's now required)
    recipe_needs = get_recipe_needs(event_id, session=session)

    if not recipe_needs:
        # No recipe needs, but may still have packaging needs
        result = {
            "items": [],
            "total_estimated_cost": cost_to_string(Decimal("0.00")),
            "items_count": 0,
            "items_with_shortfall": 0,
        }
        # Feature 011: Add packaging section if requested
        # Feature 026: Include generic packaging info
        if include_packaging:
            try:
                packaging_needs = get_event_packaging_needs(event_id, session=session)
                if packaging_needs:  # Only add if not empty
                    result["packaging"] = [
                        {
                            "product_id": need.product_id,
                            "ingredient_name": need.ingredient_name,
                            "product_name": need.product_display_name,
                            "total_needed": need.total_needed,
                            "on_hand": need.on_hand,
                            "to_buy": need.to_buy,
                            "unit": need.unit,
                            # Feature 026: Generic packaging fields
                            "is_generic": need.is_generic,
                            "generic_product_name": need.generic_product_name,
                            "estimated_cost": need.estimated_cost,
                        }
                        for need in packaging_needs.values()
                    ]
            except EventNotFoundError:
                pass
        return result

    return _get_shopping_list_impl(event_id, include_packaging, recipe_needs, session)


def _get_shopping_list_impl(
    event_id: int,
    include_packaging: bool,
    recipe_needs: List[Dict],
    session: Session,
) -> Dict[str, Any]:
    """Implementation of get_shopping_list using provided session."""
    # Aggregate ingredient needs across all recipes
    ingredient_totals: Dict[int, Decimal] = {}  # ingredient_id -> quantity needed
    ingredient_info: Dict[int, Dict] = {}  # ingredient_id -> {name, unit, slug}

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
                "slug": ri.ingredient.slug,  # Added for product lookup
            }

    # Get on-hand quantities from inventory
    # Import here to avoid circular imports
    from src.services import inventory_item_service
    from src.services.product_service import get_product_recommendation

    items = []
    for ing_id, qty_needed in ingredient_totals.items():
        info = ingredient_info[ing_id]

        # Get on-hand quantity from inventory service
        try:
            qty_on_hand = Decimal(
                str(inventory_item_service.get_ingredient_quantity_on_hand(ing_id))
            )
        except Exception:
            qty_on_hand = Decimal("0")

        shortfall = max(Decimal("0"), qty_needed - qty_on_hand)

        item = {
            "ingredient_id": ing_id,
            "ingredient_name": info["name"],
            "ingredient_slug": info["slug"],
            "unit": info["unit"],
            "quantity_needed": qty_needed,
            "quantity_on_hand": qty_on_hand,
            "shortfall": shortfall,
        }

        # Feature 007: Add product recommendations if shortfall > 0
        if shortfall > 0:
            product_data = get_product_recommendation(
                info["slug"],
                shortfall,
                info["unit"],
            )
            item["product_status"] = product_data["product_status"]
            item["product_recommendation"] = product_data.get("product_recommendation")
            item["all_products"] = product_data.get("all_products", [])
        else:
            # No shortfall - sufficient stock
            item["product_status"] = "sufficient"
            item["product_recommendation"] = None
            item["all_products"] = []

        items.append(item)

    # Sort by ingredient name
    items.sort(key=lambda x: x["ingredient_name"])

    # Calculate total estimated cost (T006)
    total_estimated_cost = _calculate_total_estimated_cost(items)

    result = {
        "items": items,
        "total_estimated_cost": cost_to_string(total_estimated_cost),
        "items_count": len(items),
        "items_with_shortfall": sum(1 for i in items if i["shortfall"] > 0),
    }

    # Feature 011: Add packaging section if requested
    # Feature 026: Include generic packaging info
    if include_packaging:
        try:
            packaging_needs = get_event_packaging_needs(event_id, session=session)
            if packaging_needs:  # Only add if not empty
                result["packaging"] = [
                    {
                        "product_id": need.product_id,
                        "ingredient_name": need.ingredient_name,
                        "product_name": need.product_display_name,
                        "total_needed": need.total_needed,
                        "on_hand": need.on_hand,
                        "to_buy": need.to_buy,
                        "unit": need.unit,
                        # Feature 026: Generic packaging fields
                        "is_generic": need.is_generic,
                        "generic_product_name": need.generic_product_name,
                        "estimated_cost": cost_to_string(need.estimated_cost) if need.estimated_cost else None,
                    }
                    for need in packaging_needs.values()
                ]
        except EventNotFoundError:
            # Event exists (we already checked), so this shouldn't happen
            pass

    return result


def export_shopping_list_csv(event_id: int, file_path: str, session: Session) -> bool:
    """
    Export shopping list to CSV file.

    Args:
        event_id: Event ID
        file_path: Destination file path
        session: SQLAlchemy session for database operations

    Returns:
        True if export was successful and file was written.
        False if there was nothing to export (empty shopping list).

    Raises:
        IOError: If file write fails
    """
    # Get shopping list data
    shopping_data = get_shopping_list(
        event_id,
        session=session,
        include_packaging=True,
    )

    if not shopping_data["items"] and not shopping_data.get("packaging"):
        # Nothing to export - return False so UI can show appropriate message
        return False

    try:
        with open(file_path, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.writer(csvfile)

            # Header row (FR-008)
            writer.writerow(
                [
                    "Ingredient",
                    "Quantity Needed",
                    "On Hand",
                    "To Buy",
                    "Unit",
                    "Preferred Brand",
                    "Estimated Cost",
                ]
            )

            # Data rows
            for item in shopping_data["items"]:
                brand = ""
                cost = ""
                if item.get("product_recommendation"):
                    brand = item["product_recommendation"].get("display_name", "")
                    cost = str(item["product_recommendation"].get("total_cost", ""))

                writer.writerow(
                    [
                        item["ingredient_name"],
                        str(item["quantity_needed"]),
                        str(item["quantity_on_hand"]),
                        str(item["shortfall"]),
                        item["unit"],
                        brand,
                        cost,
                    ]
                )

            # Packaging section if present
            if shopping_data.get("packaging"):
                writer.writerow([])  # Blank row
                writer.writerow(["--- Packaging Materials ---", "", "", "", "", "", ""])
                for pkg in shopping_data["packaging"]:
                    writer.writerow(
                        [
                            pkg["ingredient_name"],
                            str(pkg["total_needed"]),
                            str(pkg["on_hand"]),
                            str(pkg["to_buy"]),
                            pkg["unit"],
                            pkg["product_name"],
                            "",
                        ]
                    )

        return True

    except (IOError, OSError) as e:
        raise IOError(f"Failed to write CSV file: {str(e)}")


# ============================================================================
# Event Cloning
# ============================================================================


def clone_event(
    source_event_id: int,
    new_name: str,
    new_year: int,
    new_event_date: date,
    session: Session,
) -> Event:
    """
    Clone an event and all its assignments to a new year.

    Args:
        source_event_id: Event ID to clone
        new_name: Name for new event
        new_year: Year for new event
        new_event_date: Date for new event
        session: SQLAlchemy session for database operations

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
# Feature 011: Packaging Needs (FR-010 through FR-013)
# ============================================================================


def _get_packaging_on_hand(session: Session, product_id: int) -> float:
    """
    Get current inventory quantity for a packaging product.

    Args:
        session: Database session
        product_id: Product ID

    Returns:
        Total quantity on hand
    """
    total = (
        session.query(func.sum(InventoryItem.quantity))
        .filter(InventoryItem.product_id == product_id)
        .scalar()
    )
    return float(total) if total else 0.0


@dataclass
class _RawPackagingNeed:
    """Internal structure for aggregating packaging needs."""

    product_id: int
    quantity: float
    is_generic: bool
    product_name: Optional[str]  # For generic compositions


def _aggregate_packaging(
    session: Session,
    event: Event,
) -> tuple[Dict[int, float], Dict[str, float]]:
    """
    Aggregate packaging quantities for an event.

    Feature 026: Now separates specific and generic packaging needs.

    Traverses:
    - Event -> ERP -> Package -> packaging_compositions (direct package packaging)
    - Event -> ERP -> Package -> package_finished_goods -> FinishedGood -> components (FG-level packaging)

    Args:
        session: Database session
        event: Event instance (with relationships loaded)

    Returns:
        Tuple of:
        - Dict mapping product_id to total quantity needed (specific items)
        - Dict mapping product_name to total quantity needed (generic items)
    """
    specific_needs: Dict[int, float] = {}
    generic_needs: Dict[str, float] = {}  # product_name -> quantity

    for erp in event.event_recipient_packages:
        package = erp.package
        if not package:
            continue

        package_qty = erp.quantity or 1

        # Package-level packaging (direct - from Package.packaging_compositions)
        for comp in package.packaging_compositions:
            if comp.packaging_product_id:
                qty = comp.component_quantity * package_qty
                if comp.is_generic and comp.packaging_product:
                    product_name = comp.packaging_product.product_name
                    if product_name:
                        generic_needs[product_name] = generic_needs.get(product_name, 0.0) + qty
                    else:
                        # Fallback if product_name not set
                        specific_needs[comp.packaging_product_id] = (
                            specific_needs.get(comp.packaging_product_id, 0.0) + qty
                        )
                else:
                    specific_needs[comp.packaging_product_id] = (
                        specific_needs.get(comp.packaging_product_id, 0.0) + qty
                    )

        # FinishedGood-level packaging (through package contents)
        for pfg in package.package_finished_goods:
            fg = pfg.finished_good
            if not fg:
                continue

            fg_qty = pfg.quantity * package_qty

            for comp in fg.components:
                if comp.packaging_product_id:
                    qty = comp.component_quantity * fg_qty
                    if comp.is_generic and comp.packaging_product:
                        product_name = comp.packaging_product.product_name
                        if product_name:
                            generic_needs[product_name] = generic_needs.get(product_name, 0.0) + qty
                        else:
                            # Fallback if product_name not set
                            specific_needs[comp.packaging_product_id] = (
                                specific_needs.get(comp.packaging_product_id, 0.0) + qty
                            )
                    else:
                        specific_needs[comp.packaging_product_id] = (
                            specific_needs.get(comp.packaging_product_id, 0.0) + qty
                        )

    return specific_needs, generic_needs


def _get_generic_packaging_on_hand(session: Session, product_name: str) -> float:
    """
    Get total on-hand quantity for all products with a given product_name.

    Feature 026: Aggregates inventory across all products matching the generic type.

    Args:
        session: Database session
        product_name: Generic product type name (e.g., "Cellophane Bags 6x10")

    Returns:
        Total quantity on hand across all matching products
    """
    # Find all products with this product_name
    products = session.query(Product).filter(Product.product_name == product_name).all()

    total_on_hand = 0.0
    for product in products:
        total_on_hand += _get_packaging_on_hand(session, product.id)

    return total_on_hand


def get_event_packaging_needs(event_id: int, session: Session) -> Dict[str, PackagingNeed]:
    """
    Calculate packaging material needs for an event.

    Aggregates packaging from both Package-level and FinishedGood-level compositions,
    calculates on-hand inventory, and determines quantities to buy.

    Feature 026: Now handles both specific and generic packaging needs.
    - Specific items: keyed by "specific_{product_id}"
    - Generic items: keyed by "generic_{product_name}"

    Args:
        event_id: Event ID
        session: SQLAlchemy session for database operations

    Returns:
        Dict mapping key to PackagingNeed dataclass
        Keys are "specific_{product_id}" or "generic_{product_name}"

    Raises:
        EventNotFoundError: If event not found
        DatabaseError: If database operation fails
    """
    # Import here to avoid circular imports
    from src.services import packaging_service

    try:
        # Load event with full traversal chain for packaging
        event = (
            session.query(Event)
            .options(
                # Package-level packaging
                joinedload(Event.event_recipient_packages)
                .joinedload(EventRecipientPackage.package)
                .joinedload(Package.packaging_compositions)
                .joinedload(Composition.packaging_product),
                # FinishedGood-level packaging
                joinedload(Event.event_recipient_packages)
                .joinedload(EventRecipientPackage.package)
                .joinedload(Package.package_finished_goods)
                .joinedload(PackageFinishedGood.finished_good)
                .joinedload(FinishedGood.components)
                .joinedload(Composition.packaging_product),
            )
            .filter(Event.id == event_id)
            .first()
        )

        if not event:
            raise EventNotFoundError(event_id)

        # Feature 026: Aggregate raw quantities (now returns tuple)
        specific_needs, generic_needs = _aggregate_packaging(session, event)

        # Build PackagingNeed objects
        needs: Dict[str, PackagingNeed] = {}

        # Process specific packaging needs
        for product_id, total_needed in specific_needs.items():
            product = session.get(Product, product_id)
            if not product:
                continue

            ingredient = product.ingredient
            on_hand = _get_packaging_on_hand(session, product_id)
            to_buy = max(0.0, total_needed - on_hand)

            key = f"specific_{product_id}"
            needs[key] = PackagingNeed(
                product_id=product_id,
                product=product,
                ingredient_name=ingredient.display_name if ingredient else "Unknown",
                product_display_name=product.display_name,
                total_needed=total_needed,
                on_hand=on_hand,
                to_buy=to_buy,
                unit=product.package_unit or "each",
                is_generic=False,
            )

        # Feature 026: Process generic packaging needs
        for product_name, total_needed in generic_needs.items():
            # Get on-hand across all products with this product_name
            on_hand = _get_generic_packaging_on_hand(session, product_name)
            to_buy = max(0.0, total_needed - on_hand)

            # Get estimated cost from packaging service
            try:
                estimated_cost = packaging_service.get_estimated_cost(
                    product_name, float(total_needed), session=session
                )
            except Exception:
                estimated_cost = None

            # Get a sample product for ingredient/unit info
            sample_product = (
                session.query(Product).filter(Product.product_name == product_name).first()
            )

            ingredient_name = "Unknown"
            unit = "each"
            if sample_product:
                if sample_product.ingredient:
                    ingredient_name = sample_product.ingredient.display_name
                unit = sample_product.package_unit or "each"

            key = f"generic_{product_name}"
            needs[key] = PackagingNeed(
                product_id=sample_product.id if sample_product else 0,
                product=sample_product,
                ingredient_name=ingredient_name,
                product_display_name=product_name,  # Use generic name
                total_needed=total_needed,
                on_hand=on_hand,
                to_buy=to_buy,
                unit=unit,
                is_generic=True,
                generic_product_name=product_name,
                estimated_cost=estimated_cost,
            )

        return needs

    except EventNotFoundError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to calculate packaging needs: {str(e)}")


def get_event_packaging_breakdown(
    event_id: int,
    session: Session,
) -> Dict[int, List[PackagingSource]]:
    """
    Get detailed breakdown of where packaging needs come from.

    Args:
        event_id: Event ID
        session: SQLAlchemy session for database operations

    Returns:
        Dict mapping product_id to list of PackagingSource instances

    Raises:
        EventNotFoundError: If event not found
        DatabaseError: If database operation fails
    """
    try:
        # Load event with traversal chain
        event = (
            session.query(Event)
            .options(
                joinedload(Event.event_recipient_packages)
                .joinedload(EventRecipientPackage.package)
                .joinedload(Package.packaging_compositions),
                joinedload(Event.event_recipient_packages)
                .joinedload(EventRecipientPackage.package)
                .joinedload(Package.package_finished_goods)
                .joinedload(PackageFinishedGood.finished_good)
                .joinedload(FinishedGood.components),
            )
            .filter(Event.id == event_id)
            .first()
        )

        if not event:
            raise EventNotFoundError(event_id)

        breakdown: Dict[int, List[PackagingSource]] = {}

        for erp in event.event_recipient_packages:
            package = erp.package
            if not package:
                continue

            package_qty = erp.quantity or 1

            # Package-level packaging
            for comp in package.packaging_compositions:
                if comp.packaging_product_id:
                    pid = comp.packaging_product_id
                    if pid not in breakdown:
                        breakdown[pid] = []

                    breakdown[pid].append(
                        PackagingSource(
                            source_type="package",
                            source_id=package.id,
                            source_name=package.name,
                            quantity_per=comp.component_quantity,
                            source_count=package_qty,
                            total_for_source=comp.component_quantity * package_qty,
                        )
                    )

            # FinishedGood-level packaging
            for pfg in package.package_finished_goods:
                fg = pfg.finished_good
                if not fg:
                    continue

                fg_qty = pfg.quantity * package_qty

                for comp in fg.components:
                    if comp.packaging_product_id:
                        pid = comp.packaging_product_id
                        if pid not in breakdown:
                            breakdown[pid] = []

                        breakdown[pid].append(
                            PackagingSource(
                                source_type="finished_good",
                                source_id=fg.id,
                                source_name=fg.display_name,
                                quantity_per=comp.component_quantity,
                                source_count=fg_qty,
                                total_for_source=comp.component_quantity * fg_qty,
                            )
                        )

        return breakdown

    except EventNotFoundError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get packaging breakdown: {str(e)}")


# ============================================================================
# Recipient History
# ============================================================================


def get_recipient_history(recipient_id: int, session: Session) -> List[Dict[str, Any]]:
    """
    Get package history for a recipient across all events.

    Args:
        recipient_id: Recipient ID
        session: SQLAlchemy session for database operations

    Returns:
        List of dicts with event, package, quantity, notes - ordered by event date descending
    """
    try:
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
                "fulfillment_status": assignment.fulfillment_status,
            }
            for assignment in assignments
        ]

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipient history: {str(e)}")


# ============================================================================
# Feature 016: Production/Assembly Target CRUD
# ============================================================================


def set_production_target(
    event_id: int,
    recipe_id: int,
    target_batches: int,
    notes: Optional[str] = None,
    *,
    session: Session,
) -> EventProductionTarget:
    """
    Create or update production target for a recipe in an event.

    Uses upsert pattern: if target already exists, updates it; otherwise creates new.

    Args:
        event_id: Event ID
        recipe_id: Recipe ID
        target_batches: Number of batches to produce (must be > 0)
        notes: Optional notes
        session: Database session (required)

    Returns:
        EventProductionTarget instance (created or updated)

    Raises:
        ValueError: If target_batches is not positive
        DatabaseError: If database operation fails
    """
    if target_batches <= 0:
        raise ValueError("target_batches must be positive")

    try:
        # Check if target already exists
        existing = (
            session.query(EventProductionTarget)
            .filter_by(event_id=event_id, recipe_id=recipe_id)
            .first()
        )

        if existing:
            existing.target_batches = target_batches
            existing.notes = notes
            session.flush()
            return existing
        else:
            target = EventProductionTarget(
                event_id=event_id,
                recipe_id=recipe_id,
                target_batches=target_batches,
                notes=notes,
            )
            session.add(target)
            session.flush()
            return target

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to set production target: {str(e)}")


def set_assembly_target(
    event_id: int,
    finished_good_id: int,
    target_quantity: int,
    notes: Optional[str] = None,
    *,
    session: Session,
) -> EventAssemblyTarget:
    """
    Create or update assembly target for a finished good in an event.

    Uses upsert pattern: if target already exists, updates it; otherwise creates new.

    Args:
        event_id: Event ID
        finished_good_id: FinishedGood ID
        target_quantity: Number of units to assemble (must be > 0)
        notes: Optional notes
        session: Database session (required)

    Returns:
        EventAssemblyTarget instance (created or updated)

    Raises:
        ValueError: If target_quantity is not positive
        DatabaseError: If database operation fails
    """
    if target_quantity <= 0:
        raise ValueError("target_quantity must be positive")

    try:
        # Check if target already exists
        existing = (
            session.query(EventAssemblyTarget)
            .filter_by(event_id=event_id, finished_good_id=finished_good_id)
            .first()
        )

        if existing:
            existing.target_quantity = target_quantity
            existing.notes = notes
            session.flush()
            return existing
        else:
            target = EventAssemblyTarget(
                event_id=event_id,
                finished_good_id=finished_good_id,
                target_quantity=target_quantity,
                notes=notes,
            )
            session.add(target)
            session.flush()
            return target

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to set assembly target: {str(e)}")


def get_production_targets(event_id: int, *, session: Session) -> List[EventProductionTarget]:
    """
    Get all production targets for an event.

    Eager loads recipe relationship to avoid N+1 queries.

    Args:
        event_id: Event ID
        session: Database session (required)

    Returns:
        List of EventProductionTarget instances with recipe data
    """
    try:
        return (
            session.query(EventProductionTarget)
            .options(joinedload(EventProductionTarget.recipe))
            .filter_by(event_id=event_id)
            .all()
        )

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get production targets: {str(e)}")


def get_assembly_targets(event_id: int, *, session: Session) -> List[EventAssemblyTarget]:
    """
    Get all assembly targets for an event.

    Eager loads finished_good relationship to avoid N+1 queries.

    Args:
        event_id: Event ID
        session: Database session (required)

    Returns:
        List of EventAssemblyTarget instances with finished_good data
    """
    try:
        return (
            session.query(EventAssemblyTarget)
            .options(joinedload(EventAssemblyTarget.finished_good))
            .filter_by(event_id=event_id)
            .all()
        )

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get assembly targets: {str(e)}")


def delete_production_target(event_id: int, recipe_id: int, *, session: Session) -> bool:
    """
    Remove a production target from an event.

    Args:
        event_id: Event ID
        recipe_id: Recipe ID
        session: Database session (required)

    Returns:
        True if target was deleted, False if not found
    """
    try:
        target = (
            session.query(EventProductionTarget)
            .filter_by(event_id=event_id, recipe_id=recipe_id)
            .first()
        )
        if target:
            session.delete(target)
            return True
        return False

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete production target: {str(e)}")


def delete_assembly_target(event_id: int, finished_good_id: int, *, session: Session) -> bool:
    """
    Remove an assembly target from an event.

    Args:
        event_id: Event ID
        finished_good_id: FinishedGood ID
        session: Database session (required)

    Returns:
        True if target was deleted, False if not found
    """
    try:
        target = (
            session.query(EventAssemblyTarget)
            .filter_by(event_id=event_id, finished_good_id=finished_good_id)
            .first()
        )
        if target:
            session.delete(target)
            return True
        return False

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete assembly target: {str(e)}")


# ============================================================================
# Feature 016: Progress Calculation
# ============================================================================


def get_production_progress(event_id: int, session=None) -> List[Dict[str, Any]]:
    """
    Get production progress for all targets in an event.

    Calculates how many batches have been produced for each target recipe,
    only counting production runs that are linked to this specific event.

    Args:
        event_id: Event ID
        session: Optional SQLAlchemy session. If provided, all operations
                 use this session and caller controls commit/rollback.
                 If None, method manages its own transaction.

    Returns:
        List of dicts with:
        - recipe_id: int
        - recipe_name: str
        - target_batches: int
        - produced_batches: int
        - produced_yield: int
        - progress_pct: float (can exceed 100%)
        - is_complete: bool
    """
    if session is not None:
        return _get_production_progress_impl(event_id, session)
    try:
        with session_scope() as session:
            return _get_production_progress_impl(event_id, session)
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get production progress: {str(e)}")


def _get_production_progress_impl(event_id: int, session) -> List[Dict[str, Any]]:
    """Implementation of get_production_progress using provided session."""
    # Get all targets for this event with recipes eager-loaded
    targets = (
        session.query(EventProductionTarget)
        .options(joinedload(EventProductionTarget.recipe))
        .filter_by(event_id=event_id)
        .all()
    )

    if not targets:
        return []

    # Get all production totals in a single GROUP BY query
    # This avoids N+1 queries by fetching all production sums at once
    production_totals = (
        session.query(
            ProductionRun.recipe_id,
            func.coalesce(func.sum(ProductionRun.num_batches), 0).label("total_batches"),
            func.coalesce(func.sum(ProductionRun.actual_yield), 0).label("total_yield"),
        )
        .filter(ProductionRun.event_id == event_id)
        .group_by(ProductionRun.recipe_id)
        .all()
    )

    # Build lookup dict: recipe_id -> (total_batches, total_yield)
    production_by_recipe = {
        row.recipe_id: (int(row.total_batches), int(row.total_yield))
        for row in production_totals
    }

    # Merge targets with production totals
    results = []
    for target in targets:
        produced_batches, produced_yield = production_by_recipe.get(
            target.recipe_id, (0, 0)
        )
        progress_pct = (produced_batches / target.target_batches) * 100

        results.append(
            {
                "recipe_id": target.recipe_id,
                "recipe_name": target.recipe.name,
                "target_batches": target.target_batches,
                "produced_batches": produced_batches,
                "produced_yield": produced_yield,
                "progress_pct": progress_pct,
                "is_complete": produced_batches >= target.target_batches,
            }
        )

    return results


def get_assembly_progress(event_id: int, session=None) -> List[Dict[str, Any]]:
    """
    Get assembly progress for all targets in an event.

    Calculates how many units have been assembled for each target finished good,
    only counting assembly runs that are linked to this specific event.

    Args:
        event_id: Event ID
        session: Optional SQLAlchemy session. If provided, all operations
                 use this session and caller controls commit/rollback.
                 If None, method manages its own transaction.

    Returns:
        List of dicts with:
        - finished_good_id: int
        - finished_good_name: str
        - target_quantity: int
        - assembled_quantity: int
        - progress_pct: float (can exceed 100%)
        - is_complete: bool
    """
    if session is not None:
        return _get_assembly_progress_impl(event_id, session)
    try:
        with session_scope() as session:
            return _get_assembly_progress_impl(event_id, session)
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get assembly progress: {str(e)}")


def _get_assembly_progress_impl(event_id: int, session) -> List[Dict[str, Any]]:
    """Implementation of get_assembly_progress using provided session."""
    # Get all targets for this event with finished goods eager-loaded
    targets = (
        session.query(EventAssemblyTarget)
        .options(joinedload(EventAssemblyTarget.finished_good))
        .filter_by(event_id=event_id)
        .all()
    )

    if not targets:
        return []

    # Get all assembly totals in a single GROUP BY query
    # This avoids N+1 queries by fetching all assembly sums at once
    assembly_totals = (
        session.query(
            AssemblyRun.finished_good_id,
            func.coalesce(func.sum(AssemblyRun.quantity_assembled), 0).label(
                "total_assembled"
            ),
        )
        .filter(AssemblyRun.event_id == event_id)
        .group_by(AssemblyRun.finished_good_id)
        .all()
    )

    # Build lookup dict: finished_good_id -> total_assembled
    assembly_by_fg = {
        row.finished_good_id: int(row.total_assembled) for row in assembly_totals
    }

    # Merge targets with assembly totals
    results = []
    for target in targets:
        assembled_qty = assembly_by_fg.get(target.finished_good_id, 0)
        progress_pct = (assembled_qty / target.target_quantity) * 100

        results.append(
            {
                "finished_good_id": target.finished_good_id,
                "finished_good_name": target.finished_good.display_name,
                "target_quantity": target.target_quantity,
                "assembled_quantity": assembled_qty,
                "progress_pct": progress_pct,
                "is_complete": assembled_qty >= target.target_quantity,
            }
        )

    return results


def get_event_overall_progress(event_id: int, session: Session) -> Dict[str, Any]:
    """
    Get overall progress summary for an event.

    Aggregates production progress, assembly progress, and package fulfillment
    status into a single summary.

    Args:
        event_id: Event ID
        session: SQLAlchemy session for database operations

    Returns:
        Dict with:
        - production_targets_count: int
        - production_complete_count: int
        - production_complete: bool
        - assembly_targets_count: int
        - assembly_complete_count: int
        - assembly_complete: bool
        - packages_pending: int
        - packages_ready: int
        - packages_delivered: int
        - packages_total: int
    """
    try:
        # Get production progress (reuse function, but we're in same session context)
        prod_targets = session.query(EventProductionTarget).filter_by(event_id=event_id).all()
        prod_complete = 0
        for target in prod_targets:
            produced = (
                session.query(func.coalesce(func.sum(ProductionRun.num_batches), 0))
                .filter(
                    ProductionRun.recipe_id == target.recipe_id,
                    ProductionRun.event_id == event_id,
                )
                .scalar()
            )
            if produced and int(produced) >= target.target_batches:
                prod_complete += 1

        # Get assembly progress
        asm_targets = session.query(EventAssemblyTarget).filter_by(event_id=event_id).all()
        asm_complete = 0
        for target in asm_targets:
            assembled = (
                session.query(func.coalesce(func.sum(AssemblyRun.quantity_assembled), 0))
                .filter(
                    AssemblyRun.finished_good_id == target.finished_good_id,
                    AssemblyRun.event_id == event_id,
                )
                .scalar()
            )
            if assembled and int(assembled) >= target.target_quantity:
                asm_complete += 1

        # Get package counts by status
        packages = session.query(EventRecipientPackage).filter_by(event_id=event_id).all()

        pending = sum(
            1 for p in packages if p.fulfillment_status == FulfillmentStatus.PENDING.value
        )
        ready = sum(
            1 for p in packages if p.fulfillment_status == FulfillmentStatus.READY.value
        )
        delivered = sum(
            1 for p in packages if p.fulfillment_status == FulfillmentStatus.DELIVERED.value
        )

        return {
            "production_targets_count": len(prod_targets),
            "production_complete_count": prod_complete,
            "production_complete": len(prod_targets) == 0 or prod_complete == len(prod_targets),
            "assembly_targets_count": len(asm_targets),
            "assembly_complete_count": asm_complete,
            "assembly_complete": len(asm_targets) == 0 or asm_complete == len(asm_targets),
            "packages_pending": pending,
            "packages_ready": ready,
            "packages_delivered": delivered,
            "packages_total": len(packages),
        }

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get event overall progress: {str(e)}")


# ============================================================================
# Feature 018: Batch Event Progress
# ============================================================================


def get_events_with_progress(
    filter_type: str = "active_future",
    date_from: date = None,
    date_to: date = None,
    *,
    session: Session,
) -> List[Dict[str, Any]]:
    """
    Get all events matching filter with their progress summaries.

    Args:
        filter_type: One of "active_future" (default), "past", "all"
        date_from: Optional start date for date range filter
        date_to: Optional end date for date range filter
        session: SQLAlchemy session for database operations

    Returns:
        List of dicts with:
        - event_id: int
        - event_name: str
        - event_date: date
        - production_progress: list (from get_production_progress)
        - assembly_progress: list (from get_assembly_progress)
        - overall_progress: dict (from get_event_overall_progress)
    """
    try:
        today = date.today()

        # Build base query
        query = session.query(Event)

        # Apply filter based on filter_type
        if filter_type == "active_future":
            query = query.filter(Event.event_date >= today)
        elif filter_type == "past":
            query = query.filter(Event.event_date < today)
        # "all" - no date filter

        # Apply date range if provided
        if date_from:
            query = query.filter(Event.event_date >= date_from)
        if date_to:
            query = query.filter(Event.event_date <= date_to)

        # Order by date ascending, then name
        query = query.order_by(Event.event_date.asc(), Event.name.asc())

        events = query.all()

        results = []
        for event in events:
            results.append(
                {
                    "event_id": event.id,
                    "event_name": event.name,
                    "event_date": event.event_date,
                    "production_progress": get_production_progress(event.id, session=session),
                    "assembly_progress": get_assembly_progress(event.id, session=session),
                    "overall_progress": get_event_overall_progress(event.id, session=session),
                }
            )

        return results

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get events with progress: {str(e)}")


def get_event_cost_analysis(event_id: int, *, session: Session) -> Dict[str, Any]:
    """
    Get cost breakdown for an event.

    Calculates actual costs from ProductionRun.total_ingredient_cost and
    AssemblyRun.total_component_cost, which are derived from cost_at_time
    in consumption records.

    Args:
        event_id: Event ID
        session: Database session (required)

    Returns:
        Dict with:
        - production_costs: List[{recipe_name, run_count, total_cost}]
        - assembly_costs: List[{finished_good_name, run_count, total_cost}]
        - total_production_cost: Decimal
        - total_assembly_cost: Decimal
        - grand_total: Decimal
        - estimated_cost: Decimal (from shopping list)
        - variance: Decimal (estimated - actual, positive = under budget)
    """
    try:
        # Get production costs grouped by recipe
        # Note: ProductionRun uses total_ingredient_cost field
        prod_costs = (
            session.query(
                Recipe.name,
                func.count(ProductionRun.id).label("run_count"),
                func.coalesce(
                    func.sum(ProductionRun.total_ingredient_cost), Decimal("0")
                ).label("total_cost"),
            )
            .join(ProductionRun, ProductionRun.recipe_id == Recipe.id)
            .filter(ProductionRun.event_id == event_id)
            .group_by(Recipe.id, Recipe.name)
            .all()
        )

        production_costs = [
            {
                "recipe_name": name,
                "run_count": count,
                "total_cost": cost_to_string(cost),
            }
            for name, count, cost in prod_costs
        ]
        total_production_cost = sum(
            Decimal(p["total_cost"]) for p in production_costs
        ) or Decimal("0")

        # Get assembly costs grouped by finished good
        # Note: AssemblyRun uses total_component_cost field
        asm_costs = (
            session.query(
                FinishedGood.display_name,
                func.count(AssemblyRun.id).label("run_count"),
                func.coalesce(func.sum(AssemblyRun.total_component_cost), Decimal("0")).label(
                    "total_cost"
                ),
            )
            .join(AssemblyRun, AssemblyRun.finished_good_id == FinishedGood.id)
            .filter(AssemblyRun.event_id == event_id)
            .group_by(FinishedGood.id, FinishedGood.display_name)
            .all()
        )

        assembly_costs = [
            {
                "finished_good_name": name,
                "run_count": count,
                "total_cost": cost_to_string(cost),
            }
            for name, count, cost in asm_costs
        ]
        total_assembly_cost = sum(
            Decimal(a["total_cost"]) for a in assembly_costs
        ) or Decimal("0")

        # Grand total
        grand_total = total_production_cost + total_assembly_cost

        # Get estimated cost from shopping list (pass session for consistency)
        shopping_data = get_shopping_list(event_id, include_packaging=False, session=session)
        # Convert string back to Decimal for calculation
        estimated_cost = Decimal(shopping_data["total_estimated_cost"])

        # Variance (positive = under budget, negative = over budget)
        variance = estimated_cost - grand_total

        return {
            "production_costs": production_costs,
            "assembly_costs": assembly_costs,
            "total_production_cost": cost_to_string(total_production_cost),
            "total_assembly_cost": cost_to_string(total_assembly_cost),
            "grand_total": cost_to_string(grand_total),
            "estimated_cost": cost_to_string(estimated_cost),
            "variance": cost_to_string(variance),
        }

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get event cost analysis: {str(e)}")


# ============================================================================
# Feature 016: Fulfillment Status Management
# ============================================================================


def update_fulfillment_status(
    event_recipient_package_id: int,
    new_status: FulfillmentStatus,
    *,
    session: Session,
) -> EventRecipientPackage:
    """
    Update package fulfillment status with sequential workflow enforcement.

    Valid transitions:
      pending -> ready
      ready -> delivered

    Args:
        event_recipient_package_id: Package assignment ID
        new_status: New status to transition to
        session: Database session (required)

    Returns:
        Updated EventRecipientPackage instance

    Raises:
        ValueError: If package not found or transition is invalid
        DatabaseError: If database operation fails
    """
    # Define valid transitions
    valid_transitions = {
        FulfillmentStatus.PENDING: [FulfillmentStatus.READY],
        FulfillmentStatus.READY: [FulfillmentStatus.DELIVERED],
        FulfillmentStatus.DELIVERED: [],
    }

    try:
        package = (
            session.query(EventRecipientPackage)
            .filter_by(id=event_recipient_package_id)
            .first()
        )

        if not package:
            raise ValueError(f"Package with id {event_recipient_package_id} not found")

        current_status = FulfillmentStatus(package.fulfillment_status)

        if new_status not in valid_transitions[current_status]:
            allowed = [s.value for s in valid_transitions[current_status]]
            raise ValueError(
                f"Invalid transition: {current_status.value} -> {new_status.value}. "
                f"Allowed: {allowed}"
            )

        package.fulfillment_status = new_status.value
        session.flush()

        # Reload with relationships
        package = (
            session.query(EventRecipientPackage)
            .options(
                joinedload(EventRecipientPackage.recipient),
                joinedload(EventRecipientPackage.package),
            )
            .filter(EventRecipientPackage.id == event_recipient_package_id)
            .one()
        )
        return package

    except ValueError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update fulfillment status: {str(e)}")


def get_packages_by_status(
    event_id: int,
    status: Optional[FulfillmentStatus] = None,
    *,
    session: Session,
) -> List[EventRecipientPackage]:
    """
    Get packages filtered by fulfillment status (or all if None).

    Eager loads recipient and package relationships for UI display.

    Args:
        event_id: Event ID
        status: Optional status to filter by (None returns all)
        session: Database session (required)

    Returns:
        List of EventRecipientPackage instances
    """
    try:
        query = (
            session.query(EventRecipientPackage)
            .options(
                joinedload(EventRecipientPackage.recipient),
                joinedload(EventRecipientPackage.package),
            )
            .filter_by(event_id=event_id)
        )

        if status is not None:
            query = query.filter(EventRecipientPackage.fulfillment_status == status.value)

        return query.all()

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get packages by status: {str(e)}")


# ============================================================================
# F068: Planning Module Methods
# ============================================================================


def _validate_expected_attendees(value: Optional[int]) -> None:
    """
    Validate expected_attendees value.

    Args:
        value: Attendee count to validate

    Raises:
        ValidationError: If value is not positive (when provided)
    """
    if value is not None and value <= 0:
        raise ValidationError(["Expected attendees must be a positive integer"])


def get_events_for_planning(
    session: Session,
    include_completed: bool = False,
) -> List[Event]:
    """
    Get events for the Planning workspace.

    Args:
        session: Database session
        include_completed: If True, include COMPLETED events

    Returns:
        List of Event objects sorted by event_date (most recent first)
    """
    query = session.query(Event)

    if not include_completed:
        query = query.filter(Event.plan_state != PlanState.COMPLETED)

    return query.order_by(Event.event_date.desc()).all()


def create_planning_event(
    session: Session,
    name: str,
    event_date: date,
    expected_attendees: Optional[int] = None,
    notes: Optional[str] = None,
) -> Event:
    """
    Create a new event for planning.

    Args:
        session: Database session
        name: Event name (required)
        event_date: Event date (required)
        expected_attendees: Optional attendee count (must be positive)
        notes: Optional notes

    Returns:
        Created Event object

    Raises:
        ValidationError: If validation fails
    """
    # Validate expected_attendees
    _validate_expected_attendees(expected_attendees)

    # Create event with planning defaults
    event = Event(
        name=name,
        event_date=event_date,
        year=event_date.year,
        expected_attendees=expected_attendees,
        plan_state=PlanState.DRAFT,
        notes=notes,
    )

    session.add(event)
    session.flush()

    return event


def update_planning_event(
    session: Session,
    event_id: int,
    name: Optional[str] = None,
    event_date: Optional[date] = None,
    expected_attendees: Optional[int] = None,
    notes: Optional[str] = None,
    # NOTE: plan_state is intentionally NOT a parameter.
    # State transitions are implemented in F077 (Plan State Management).
) -> Event:
    """
    Update an existing event's planning metadata.

    Args:
        session: Database session
        event_id: ID of event to update
        name: New name (if provided)
        event_date: New date (if provided)
        expected_attendees: New attendee count (if provided, must be positive or 0 to clear)
        notes: New notes (if provided)

    Returns:
        Updated Event object

    Raises:
        ValidationError: If event not found or validation fails
    """
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError([f"Event with ID {event_id} not found"])

    # Validate and update expected_attendees
    # Special handling: pass 0 to clear, positive to set
    if expected_attendees is not None:
        if expected_attendees == 0:
            event.expected_attendees = None
        elif expected_attendees < 0:
            raise ValidationError(["Expected attendees must be a positive integer"])
        else:
            event.expected_attendees = expected_attendees

    # Update other fields if provided
    if name is not None:
        event.name = name
    if event_date is not None:
        event.event_date = event_date
        event.year = event_date.year
    if notes is not None:
        event.notes = notes

    session.flush()
    return event


def delete_planning_event(
    session: Session,
    event_id: int,
) -> bool:
    """
    Delete an event and all its planning associations.

    Cascade delete removes: event_recipes, event_finished_goods,
    batch_decisions, plan_amendments.

    Args:
        session: Database session
        event_id: ID of event to delete

    Returns:
        True if deleted, False if not found
    """
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        return False

    session.delete(event)
    session.flush()
    return True
