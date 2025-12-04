"""
Production Service - Business logic for production tracking.

This service provides:
- Recording recipe production with FIFO inventory consumption
- Package status management
- Production progress tracking and dashboard data

Feature 008: Production Tracking
"""

from typing import Dict, Any, List, Optional, Set
from decimal import Decimal
from datetime import datetime, timezone
from math import ceil

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from src.models import (
    ProductionRecord,
    Event,
    EventRecipientPackage,
    Recipe,
    RecipeIngredient,
    Package,
    PackageFinishedGood,
    FinishedGood,
    Composition,
    FinishedUnit,
    PackageStatus,
)
from src.services.database import session_scope
from src.services.exceptions import ValidationError, DatabaseError
from src.services import pantry_service
from src.services.event_service import EventNotFoundError


# Custom exceptions for production service


class InsufficientInventoryError(Exception):
    """Raised when pantry doesn't have enough ingredients for production."""

    def __init__(self, ingredient_slug: str, needed: Decimal, available: Decimal):
        self.ingredient_slug = ingredient_slug
        self.needed = needed
        self.available = available
        super().__init__(
            f"Insufficient inventory for {ingredient_slug}: need {needed}, have {available}"
        )


class RecipeNotFoundError(Exception):
    """Raised when recipe cannot be found."""

    def __init__(self, recipe_id: int):
        self.recipe_id = recipe_id
        super().__init__(f"Recipe with ID {recipe_id} not found")


class ProductionExceedsPlannedError(Exception):
    """Warning when production would exceed planned batches."""

    def __init__(self, recipe_id: int, planned: int, would_produce: int):
        self.recipe_id = recipe_id
        self.planned = planned
        self.would_produce = would_produce
        super().__init__(
            f"Production would exceed planned: {would_produce} vs {planned} planned"
        )


class InvalidStatusTransitionError(Exception):
    """Raised when package status transition is not allowed."""

    def __init__(self, current: PackageStatus, target: PackageStatus):
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition from {current.value} to {target.value}")


class IncompleteProductionError(Exception):
    """Raised when trying to assemble package with incomplete production."""

    def __init__(self, assignment_id: int, missing_recipes: List[Dict]):
        self.assignment_id = assignment_id
        self.missing_recipes = missing_recipes
        recipe_names = ", ".join(r["recipe_name"] for r in missing_recipes)
        super().__init__(
            f"Cannot assemble package {assignment_id}: missing production for {recipe_names}"
        )


class AssignmentNotFoundError(Exception):
    """Raised when EventRecipientPackage not found."""

    def __init__(self, assignment_id: int):
        self.assignment_id = assignment_id
        super().__init__(f"Assignment with ID {assignment_id} not found")


# Valid status transitions map
VALID_TRANSITIONS: Dict[PackageStatus, Set[PackageStatus]] = {
    PackageStatus.PENDING: {PackageStatus.ASSEMBLED},
    PackageStatus.ASSEMBLED: {PackageStatus.DELIVERED},
    PackageStatus.DELIVERED: set(),  # No transitions from delivered
}


def record_production(
    event_id: int,
    recipe_id: int,
    batches: int,
    notes: Optional[str] = None,
) -> ProductionRecord:
    """
    Record batches of a recipe as produced for an event.

    Consumes pantry inventory via FIFO and captures actual costs.

    Args:
        event_id: Event to record production for
        recipe_id: Recipe that was produced
        batches: Number of batches produced (must be > 0)
        notes: Optional production notes

    Returns:
        ProductionRecord with actual FIFO cost

    Raises:
        ValidationError: If batches <= 0
        EventNotFoundError: If event doesn't exist
        RecipeNotFoundError: If recipe doesn't exist
        InsufficientInventoryError: If pantry lacks ingredients
    """
    # Validation
    if batches <= 0:
        raise ValidationError(["Batches must be greater than 0"])

    try:
        with session_scope() as session:
            # Verify event exists
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise EventNotFoundError(event_id)

            # Verify recipe exists and load ingredients
            # Load both ingredient relationships (legacy and new) to avoid detached session issues
            recipe = (
                session.query(Recipe)
                .options(
                    joinedload(Recipe.recipe_ingredients).joinedload(
                        RecipeIngredient.ingredient
                    ),
                    joinedload(Recipe.recipe_ingredients).joinedload(
                        RecipeIngredient.ingredient_new
                    ),
                )
                .filter(Recipe.id == recipe_id)
                .first()
            )
            if not recipe:
                raise RecipeNotFoundError(recipe_id)

            # Calculate and consume ingredients
            total_actual_cost = Decimal("0.0000")

            for ri in recipe.recipe_ingredients:
                # Use active_ingredient property which handles legacy vs new FK
                ingredient = ri.active_ingredient
                if not ingredient:
                    continue

                # Calculate quantity for N batches
                qty_needed = Decimal(str(ri.quantity)) * Decimal(str(batches))

                # Consume via FIFO (actual consumption, not dry run)
                result = pantry_service.consume_fifo(
                    ingredient_slug=ingredient.slug,
                    quantity_needed=qty_needed,
                    dry_run=False,
                )

                if not result["satisfied"]:
                    raise InsufficientInventoryError(
                        ingredient_slug=ingredient.slug,
                        needed=qty_needed,
                        available=result["consumed"],
                    )

                total_actual_cost += result["total_cost"]

            # Create production record
            record = ProductionRecord(
                event_id=event_id,
                recipe_id=recipe_id,
                batches=batches,
                actual_cost=total_actual_cost,
                produced_at=datetime.now(timezone.utc),
                notes=notes,
            )
            session.add(record)
            session.flush()

            # Reload to ensure all fields populated
            session.refresh(record)
            return record

    except (EventNotFoundError, RecipeNotFoundError, InsufficientInventoryError):
        # Re-raise domain exceptions as-is
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to record production: {str(e)}")


def get_production_records(event_id: int) -> List[ProductionRecord]:
    """
    Get all production records for an event.

    Args:
        event_id: Event to get records for

    Returns:
        List of ProductionRecord objects
    """
    try:
        with session_scope() as session:
            records = (
                session.query(ProductionRecord)
                .options(joinedload(ProductionRecord.recipe))
                .filter(ProductionRecord.event_id == event_id)
                .order_by(ProductionRecord.produced_at.desc())
                .all()
            )

            # Detach from session so they can be used outside
            for record in records:
                session.expunge(record)

            return records

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get production records: {str(e)}")


def get_production_total(event_id: int, recipe_id: int) -> Dict[str, Any]:
    """
    Get total batches produced and cost for a recipe in an event.

    Args:
        event_id: Event ID
        recipe_id: Recipe ID

    Returns:
        Dict with batches_produced, total_actual_cost
    """
    try:
        with session_scope() as session:
            result = (
                session.query(
                    func.sum(ProductionRecord.batches).label("batches"),
                    func.sum(ProductionRecord.actual_cost).label("cost"),
                )
                .filter(
                    ProductionRecord.event_id == event_id,
                    ProductionRecord.recipe_id == recipe_id,
                )
                .first()
            )

            return {
                "batches_produced": result.batches or 0,
                "total_actual_cost": result.cost or Decimal("0.00"),
            }

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get production total: {str(e)}")


def _calculate_package_recipe_needs(assignment: EventRecipientPackage) -> List[Dict]:
    """
    Helper to calculate recipe needs for a single package assignment.

    Args:
        assignment: EventRecipientPackage with loaded relationships

    Returns:
        List of dicts with recipe_id, recipe_name, batches_required
    """
    recipe_totals: Dict[int, int] = {}
    recipe_info: Dict[int, Dict] = {}

    if not assignment.package:
        return []

    for pfg in assignment.package.package_finished_goods:
        if not pfg.finished_good:
            continue

        for composition in pfg.finished_good.components:
            if not composition.finished_unit_component:
                continue

            fu = composition.finished_unit_component
            if not fu.recipe:
                continue

            recipe_id = fu.recipe_id
            items_per_batch = fu.items_per_batch or 1
            units = int(composition.component_quantity) * pfg.quantity * assignment.quantity

            recipe_totals[recipe_id] = recipe_totals.get(recipe_id, 0) + units
            recipe_info[recipe_id] = {
                "name": fu.recipe.name,
                "items_per_batch": items_per_batch,
            }

    result = []
    for recipe_id, total_units in recipe_totals.items():
        info = recipe_info[recipe_id]
        batches_needed = ceil(total_units / info["items_per_batch"])
        result.append(
            {
                "recipe_id": recipe_id,
                "recipe_name": info["name"],
                "batches_required": batches_needed,
            }
        )

    return result


def can_assemble_package(assignment_id: int) -> Dict[str, Any]:
    """
    Check if a package can be marked as assembled.

    Verifies all required recipes for the package's contents have
    sufficient production records for the event.

    Args:
        assignment_id: EventRecipientPackage ID

    Returns:
        Dict with:
        - can_assemble: bool
        - missing_recipes: List of recipes needing more production
    """
    try:
        with session_scope() as session:
            # Load assignment with full chain for recipe needs calculation
            assignment = (
                session.query(EventRecipientPackage)
                .options(
                    joinedload(EventRecipientPackage.package)
                    .joinedload(Package.package_finished_goods)
                    .joinedload(PackageFinishedGood.finished_good)
                    .joinedload(FinishedGood.components)
                    .joinedload(Composition.finished_unit_component)
                    .joinedload(FinishedUnit.recipe)
                )
                .filter(EventRecipientPackage.id == assignment_id)
                .first()
            )

            if not assignment:
                raise AssignmentNotFoundError(assignment_id)

            event_id = assignment.event_id

            # Get recipe needs for this specific package
            recipe_needs = _calculate_package_recipe_needs(assignment)

            # Get production totals for this event
            production_totals = (
                session.query(
                    ProductionRecord.recipe_id,
                    func.sum(ProductionRecord.batches).label("produced"),
                )
                .filter(ProductionRecord.event_id == event_id)
                .group_by(ProductionRecord.recipe_id)
                .all()
            )
            produced_map = {r.recipe_id: r.produced for r in production_totals}

            # Check each required recipe
            missing = []
            for need in recipe_needs:
                produced = produced_map.get(need["recipe_id"], 0)
                if produced < need["batches_required"]:
                    missing.append(
                        {
                            "recipe_id": need["recipe_id"],
                            "recipe_name": need["recipe_name"],
                            "batches_required": need["batches_required"],
                            "batches_produced": produced,
                            "batches_missing": need["batches_required"] - produced,
                        }
                    )

            return {"can_assemble": len(missing) == 0, "missing_recipes": missing}

    except AssignmentNotFoundError:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to check assembly readiness: {str(e)}")


def update_package_status(
    assignment_id: int,
    new_status: PackageStatus,
    delivered_to: Optional[str] = None,
) -> EventRecipientPackage:
    """
    Update the status of a package assignment.

    Args:
        assignment_id: EventRecipientPackage ID
        new_status: Target status
        delivered_to: Optional delivery note (only for DELIVERED status)

    Returns:
        Updated EventRecipientPackage

    Raises:
        AssignmentNotFoundError: Assignment doesn't exist
        InvalidStatusTransitionError: Transition not allowed
        IncompleteProductionError: Trying to assemble with incomplete production
    """
    # First, get current status without holding session open
    try:
        with session_scope() as session:
            assignment = (
                session.query(EventRecipientPackage)
                .filter(EventRecipientPackage.id == assignment_id)
                .first()
            )

            if not assignment:
                raise AssignmentNotFoundError(assignment_id)

            current_status = assignment.status
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get assignment status: {str(e)}")

    # Validate transition (outside session)
    if new_status not in VALID_TRANSITIONS.get(current_status, set()):
        raise InvalidStatusTransitionError(current_status, new_status)

    # If transitioning to ASSEMBLED, verify production complete (uses its own session)
    if new_status == PackageStatus.ASSEMBLED:
        assembly_check = can_assemble_package(assignment_id)
        if not assembly_check["can_assemble"]:
            raise IncompleteProductionError(
                assignment_id, assembly_check["missing_recipes"]
            )

    # Now perform the update in a fresh session
    try:
        with session_scope() as session:
            assignment = (
                session.query(EventRecipientPackage)
                .filter(EventRecipientPackage.id == assignment_id)
                .first()
            )

            # Update status
            assignment.status = new_status

            # Set delivered_to if transitioning to DELIVERED
            if new_status == PackageStatus.DELIVERED and delivered_to:
                assignment.delivered_to = delivered_to

            session.flush()
            session.refresh(assignment)

            # Expunge to allow use outside session
            session.expunge(assignment)
            return assignment

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update package status: {str(e)}")


def get_production_progress(event_id: int) -> Dict[str, Any]:
    """
    Get production progress for an event.

    Aggregates recipe production status, package status, and costs.

    Args:
        event_id: Event to get progress for

    Returns:
        Dict with recipes, packages, costs, and completion status
    """
    from src.services import event_service

    try:
        with session_scope() as session:
            # Verify event exists
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise EventNotFoundError(event_id)

            event_name = event.name
            event_date = event.event_date

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to verify event: {str(e)}")

    # Get required batches from event_service (uses its own session)
    recipe_needs = event_service.get_recipe_needs(event_id)

    try:
        with session_scope() as session:
            # Get produced batches with actual costs
            production_data = (
                session.query(
                    ProductionRecord.recipe_id,
                    func.sum(ProductionRecord.batches).label("produced"),
                    func.sum(ProductionRecord.actual_cost).label("actual_cost"),
                )
                .filter(ProductionRecord.event_id == event_id)
                .group_by(ProductionRecord.recipe_id)
                .all()
            )
            produced_map = {
                r.recipe_id: {"produced": r.produced, "actual_cost": r.actual_cost}
                for r in production_data
            }

            # Build recipe progress list
            recipes = []
            total_actual = Decimal("0.00")
            total_planned = Decimal("0.00")

            for need in recipe_needs:
                recipe_id = need["recipe_id"]
                prod = produced_map.get(
                    recipe_id, {"produced": 0, "actual_cost": Decimal("0")}
                )

                # Get planned cost from recipe (estimated)
                recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
                planned_per_batch = (
                    Decimal(str(recipe.calculate_cost())) if recipe else Decimal("0")
                )
                planned_cost = planned_per_batch * Decimal(str(need["batches_needed"]))

                actual = prod["actual_cost"] or Decimal("0")

                recipes.append(
                    {
                        "recipe_id": recipe_id,
                        "recipe_name": need["recipe_name"],
                        "batches_required": need["batches_needed"],
                        "batches_produced": prod["produced"],
                        "is_complete": prod["produced"] >= need["batches_needed"],
                        "actual_cost": actual,
                        "planned_cost": planned_cost,
                    }
                )

                total_actual += actual
                total_planned += planned_cost

            # Get package status counts
            package_counts = (
                session.query(
                    EventRecipientPackage.status,
                    func.count(EventRecipientPackage.id).label("count"),
                )
                .filter(EventRecipientPackage.event_id == event_id)
                .group_by(EventRecipientPackage.status)
                .all()
            )

            status_map = {s.status.value: s.count for s in package_counts}
            pending = status_map.get("pending", 0)
            assembled = status_map.get("assembled", 0)
            delivered = status_map.get("delivered", 0)
            total_packages = pending + assembled + delivered

            return {
                "event_id": event_id,
                "event_name": event_name,
                "event_date": event_date.isoformat() if event_date else None,
                "recipes": recipes,
                "packages": {
                    "total": total_packages,
                    "pending": pending,
                    "assembled": assembled,
                    "delivered": delivered,
                },
                "costs": {"actual_total": total_actual, "planned_total": total_planned},
                "is_complete": delivered == total_packages and total_packages > 0,
            }

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get production progress: {str(e)}")


def get_dashboard_summary() -> List[Dict[str, Any]]:
    """
    Get production summary across all active events.

    Returns all events that have packages assigned (sorted by event_date ascending).

    Returns:
        List of event summaries with progress information
    """
    try:
        with session_scope() as session:
            # Get all events with packages
            events_with_packages = (
                session.query(Event)
                .join(EventRecipientPackage)
                .distinct()
                .order_by(Event.event_date.asc())
                .all()
            )

            event_ids = [e.id for e in events_with_packages]

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to query events: {str(e)}")

    # Build summaries (get_production_progress uses its own sessions)
    summaries = []
    for event_id in event_ids:
        progress = get_production_progress(event_id)

        # Count complete recipes
        recipes_complete = sum(1 for r in progress["recipes"] if r["is_complete"])
        recipes_total = len(progress["recipes"])

        summaries.append(
            {
                "event_id": progress["event_id"],
                "event_name": progress["event_name"],
                "event_date": progress["event_date"],
                "recipes_complete": recipes_complete,
                "recipes_total": recipes_total,
                "packages_pending": progress["packages"]["pending"],
                "packages_assembled": progress["packages"]["assembled"],
                "packages_delivered": progress["packages"]["delivered"],
                "packages_total": progress["packages"]["total"],
                "actual_cost": progress["costs"]["actual_total"],
                "planned_cost": progress["costs"]["planned_total"],
                "is_complete": progress["is_complete"],
            }
        )

    return summaries


def get_recipe_cost_breakdown(event_id: int) -> List[Dict[str, Any]]:
    """
    Get detailed cost breakdown by recipe for an event.

    Args:
        event_id: Event to get breakdown for

    Returns:
        List of recipe cost details with variance
    """
    progress = get_production_progress(event_id)

    breakdown = []
    for recipe in progress["recipes"]:
        actual = recipe["actual_cost"]
        planned = recipe["planned_cost"]
        variance = actual - planned

        # Calculate variance percent (avoid division by zero)
        if planned > 0:
            variance_percent = float((variance / planned) * 100)
        else:
            variance_percent = 0.0 if actual == 0 else 100.0

        breakdown.append(
            {
                "recipe_id": recipe["recipe_id"],
                "recipe_name": recipe["recipe_name"],
                "batches_required": recipe["batches_required"],
                "batches_produced": recipe["batches_produced"],
                "actual_cost": actual,
                "planned_cost": planned,
                "variance": variance,
                "variance_percent": round(variance_percent, 2),
            }
        )

    return breakdown


def get_event_assignments(event_id: int) -> List[Dict[str, Any]]:
    """
    Get package assignments for an event with status info.

    Args:
        event_id: Event to get assignments for

    Returns:
        List of assignment dicts with recipient, package, status info
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
                .all()
            )

            result = []
            for a in assignments:
                result.append(
                    {
                        "id": a.id,
                        "recipient_name": a.recipient.name if a.recipient else "Unknown",
                        "package_name": a.package.name if a.package else "Unknown",
                        "status": a.status.value if a.status else "pending",
                        "delivered_to": a.delivered_to,
                    }
                )
            return result

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get event assignments: {str(e)}")
