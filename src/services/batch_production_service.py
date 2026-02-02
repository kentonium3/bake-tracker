"""
Batch Production Service for recording batch production runs.

This module provides functions for:
- Checking ingredient availability before production (dry run)
- Recording batch production with FIFO consumption
- Creating production runs with consumption ledger entries
- Tracking yield-based costing

The service integrates with:
- inventory_item_service.consume_fifo() for FIFO inventory consumption
- recipe_service.get_aggregated_ingredients() for nested recipe support
- ProductionRun and ProductionConsumption models for persistence

Feature 013: Production & Inventory Tracking
"""

from contextlib import nullcontext
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime
from src.utils.datetime_utils import utc_now

from sqlalchemy.orm import joinedload, Session

from src.services.dto_utils import cost_to_string
from src.services.logging_utils import get_service_logger, log_operation

# Module logger
logger = get_service_logger(__name__)

from src.models import (
    ProductionRun,
    ProductionConsumption,
    ProductionLoss,
    Recipe,
    FinishedUnit,
    Event,
    EventProductionTarget,  # F065: For snapshot reuse lookup
    ProductionStatus,
    LossCategory,
)
from src.services.database import session_scope
from src.services import inventory_item_service
from src.services.recipe_service import get_aggregated_ingredients
from src.services import recipe_snapshot_service  # Feature 037
from src.services import finished_goods_inventory_service as fg_inv  # Feature 061
from src.services.exceptions import ServiceError


# =============================================================================
# Custom Exceptions
# =============================================================================


class RecipeNotFoundError(ServiceError):
    """Raised when a recipe cannot be found.

    Args:
        recipe_id: The recipe ID that was not found
        correlation_id: Optional correlation ID for tracing

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, recipe_id: int, correlation_id: Optional[str] = None):
        self.recipe_id = recipe_id
        super().__init__(
            f"Recipe with ID {recipe_id} not found",
            correlation_id=correlation_id,
            recipe_id=recipe_id
        )


class FinishedUnitNotFoundError(ServiceError):
    """Raised when a finished unit cannot be found.

    Args:
        finished_unit_id: The finished unit ID that was not found
        correlation_id: Optional correlation ID for tracing

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, finished_unit_id: int, correlation_id: Optional[str] = None):
        self.finished_unit_id = finished_unit_id
        super().__init__(
            f"FinishedUnit with ID {finished_unit_id} not found",
            correlation_id=correlation_id,
            finished_unit_id=finished_unit_id
        )


class FinishedUnitRecipeMismatchError(ServiceError):
    """Raised when a finished unit does not belong to the specified recipe.

    Args:
        finished_unit_id: The finished unit ID
        recipe_id: The recipe ID it should belong to
        correlation_id: Optional correlation ID for tracing

    HTTP Status: 400 Bad Request
    """

    http_status_code = 400

    def __init__(self, finished_unit_id: int, recipe_id: int, correlation_id: Optional[str] = None):
        self.finished_unit_id = finished_unit_id
        self.recipe_id = recipe_id
        super().__init__(
            f"FinishedUnit {finished_unit_id} does not belong to Recipe {recipe_id}",
            correlation_id=correlation_id,
            finished_unit_id=finished_unit_id,
            recipe_id=recipe_id
        )


class InsufficientInventoryError(ServiceError):
    """Raised when there is insufficient inventory for production.

    Args:
        ingredient_slug: The ingredient slug
        needed: Quantity needed
        available: Quantity available
        unit: Unit of measurement
        correlation_id: Optional correlation ID for tracing

    HTTP Status: 422 Unprocessable Entity (business rule violation)
    """

    http_status_code = 422

    def __init__(
        self,
        ingredient_slug: str,
        needed: Decimal,
        available: Decimal,
        unit: str,
        correlation_id: Optional[str] = None
    ):
        self.ingredient_slug = ingredient_slug
        self.needed = needed
        self.available = available
        self.unit = unit
        super().__init__(
            f"Insufficient {ingredient_slug}: need {needed} {unit}, have {available} {unit}",
            correlation_id=correlation_id,
            ingredient_slug=ingredient_slug,
            needed=str(needed),
            available=str(available),
            unit=unit
        )


class EventNotFoundError(ServiceError):
    """Raised when an event cannot be found.

    Args:
        event_id: The event ID that was not found
        correlation_id: Optional correlation ID for tracing

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, event_id: int, correlation_id: Optional[str] = None):
        self.event_id = event_id
        super().__init__(
            f"Event with ID {event_id} not found",
            correlation_id=correlation_id,
            event_id=event_id
        )


class ActualYieldExceedsExpectedError(ServiceError):
    """Raised when actual yield exceeds expected yield.

    Feature 025: Production Loss Tracking

    Args:
        actual_yield: The actual yield produced
        expected_yield: The expected yield
        correlation_id: Optional correlation ID for tracing

    HTTP Status: 422 Unprocessable Entity (business rule violation)
    """

    http_status_code = 422

    def __init__(self, actual_yield: int, expected_yield: int, correlation_id: Optional[str] = None):
        self.actual_yield = actual_yield
        self.expected_yield = expected_yield
        super().__init__(
            f"Actual yield ({actual_yield}) cannot exceed expected yield ({expected_yield})",
            correlation_id=correlation_id,
            actual_yield=actual_yield,
            expected_yield=expected_yield
        )


# =============================================================================
# Availability Check Functions
# =============================================================================


def check_can_produce(
    recipe_id: int,
    num_batches: int,
    *,
    scale_factor: float = 1.0,  # Feature 037
    session=None,
) -> Dict[str, Any]:
    """
    Check if a recipe can be produced with current inventory.

    Performs a dry-run FIFO consumption check for all ingredients
    (including nested recipe ingredients) and returns detailed
    availability information.

    Args:
        recipe_id: ID of the recipe to produce
        num_batches: Number of batches to produce
        scale_factor: Recipe size multiplier (default 1.0, Feature 037)
        session: Optional database session (uses session_scope if not provided)

    Returns:
        Dict with keys:
            - "can_produce" (bool): True if all ingredients available
            - "missing" (List[Dict]): List of missing ingredients with details:
                - ingredient_slug: str
                - ingredient_name: str
                - needed: Decimal
                - available: Decimal
                - unit: str

    Raises:
        RecipeNotFoundError: If recipe doesn't exist
    """
    # Use provided session or create a new one
    if session is not None:
        return _check_can_produce_impl(recipe_id, num_batches, scale_factor, session)
    with session_scope() as session:
        return _check_can_produce_impl(recipe_id, num_batches, scale_factor, session)


def _check_can_produce_impl(
    recipe_id: int,
    num_batches: int,
    scale_factor: float,
    session,
) -> Dict[str, Any]:
    """Implementation of check_can_produce that uses provided session."""
    # Validate recipe exists
    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        raise RecipeNotFoundError(recipe_id)

    # Get aggregated ingredients (handles nested recipes)
    # Pass session to maintain transactional consistency
    try:
        aggregated = get_aggregated_ingredients(recipe_id, multiplier=1, session=session)
    except Exception as e:
        raise RecipeNotFoundError(recipe_id) from e

    missing = []

    for item in aggregated:
        ingredient = item["ingredient"]
        ingredient_slug = ingredient.slug
        ingredient_name = ingredient.display_name
        base_quantity = Decimal(str(item["total_quantity"]))
        unit = item["unit"]

        # Feature 037: Apply scale_factor and num_batches to base quantity
        quantity_needed = base_quantity * Decimal(str(scale_factor)) * Decimal(str(num_batches))

        # Perform dry-run FIFO check - pass session for consistency
        result = inventory_item_service.consume_fifo(
            ingredient_slug, quantity_needed, unit, dry_run=True, session=session
        )

        if not result["satisfied"]:
            available = result["consumed"]
            missing.append(
                {
                    "ingredient_slug": ingredient_slug,
                    "ingredient_name": ingredient_name,
                    "needed": quantity_needed,
                    "available": available,
                    "unit": unit,
                }
            )

    can_produce = len(missing) == 0

    if can_produce:
        logger.debug(
            "Production check passed",
            extra={"recipe_id": recipe_id, "num_batches": num_batches, "scale_factor": scale_factor},
        )
    else:
        log_operation(
            logger,
            operation="check_can_produce",
            outcome="insufficient_inventory",
            recipe_id=recipe_id,
            num_batches=num_batches,
            missing_count=len(missing),
            missing_ingredients=[m["ingredient_slug"] for m in missing],
        )

    return {
        "can_produce": can_produce,
        "missing": missing,
    }


# =============================================================================
# Production Recording Functions
# =============================================================================


def record_batch_production(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    *,
    produced_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    event_id: Optional[int] = None,
    loss_category: Optional[LossCategory] = None,
    loss_notes: Optional[str] = None,
    scale_factor: float = 1.0,  # Feature 037: Recipe scaling
    session=None,
) -> Dict[str, Any]:
    """
    Record a batch production run with FIFO consumption.

    This function atomically:
    1. Validates recipe and finished unit
    2. Validates event if provided (Feature 016)
    3. Creates recipe snapshot FIRST (Feature 037)
    4. Validates actual_yield <= expected_yield (Feature 025)
    5. Consumes ingredients from snapshot data via FIFO
    6. Increments FinishedUnit.inventory_count by actual_yield
    7. Creates ProductionRun with snapshot reference
    8. Creates ProductionLoss record if loss_quantity > 0 (Feature 025)
    9. Calculates per-unit cost based on actual yield

    Args:
        recipe_id: ID of the recipe being produced
        finished_unit_id: ID of the FinishedUnit being produced
        num_batches: Number of recipe batches made
        actual_yield: Actual number of units produced (can be 0 for failed batches)
        produced_at: Optional production timestamp (defaults to now)
        notes: Optional production notes
        event_id: Optional event ID to link production to (Feature 016)
        loss_category: Optional loss category enum (Feature 025, defaults to OTHER if loss exists)
        loss_notes: Optional notes about the loss (Feature 025)
        scale_factor: Recipe size multiplier (default 1.0, Feature 037)
        session: Optional database session (uses session_scope if not provided)

    Returns:
        Dict with keys:
            - "production_run_id": int
            - "recipe_id": int
            - "finished_unit_id": int
            - "num_batches": int
            - "expected_yield": int
            - "actual_yield": int
            - "total_ingredient_cost": Decimal
            - "per_unit_cost": Decimal
            - "consumptions": List[Dict] - consumption ledger details
            - "event_id": Optional[int] - linked event ID (Feature 016)
            - "production_status": str - COMPLETE, PARTIAL_LOSS, or TOTAL_LOSS (Feature 025)
            - "loss_quantity": int - expected_yield - actual_yield (Feature 025)
            - "loss_record_id": Optional[int] - ID of ProductionLoss record if created (Feature 025)
            - "total_loss_cost": str - cost of lost units (Feature 025)
            - "snapshot_id": int - Recipe snapshot ID (Feature 037)
            - "scale_factor": float - Applied scale factor (Feature 037)
            - "snapshot_reused": bool - True if planning snapshot was reused (F065)

    Raises:
        RecipeNotFoundError: If recipe doesn't exist
        FinishedUnitNotFoundError: If finished unit doesn't exist
        FinishedUnitRecipeMismatchError: If finished unit doesn't belong to recipe
        InsufficientInventoryError: If ingredient inventory is insufficient
        EventNotFoundError: If event_id is provided but event doesn't exist
        ActualYieldExceedsExpectedError: If actual_yield > expected_yield (Feature 025)
    """
    # Log entry point at DEBUG level
    logger.debug(
        "Recording batch production",
        extra={
            "recipe_id": recipe_id,
            "finished_unit_id": finished_unit_id,
            "num_batches": num_batches,
            "actual_yield": actual_yield,
            "event_id": event_id,
            "scale_factor": scale_factor,
        },
    )

    # Honor passed session per CLAUDE.md session management pattern
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # Validate recipe exists
        recipe = session.query(Recipe).filter_by(id=recipe_id).first()
        if not recipe:
            log_operation(
                logger,
                operation="record_batch_production",
                outcome="recipe_not_found",
                level=logging.WARNING,
                recipe_id=recipe_id,
            )
            raise RecipeNotFoundError(recipe_id)

        # Validate finished unit exists and belongs to recipe
        finished_unit = session.query(FinishedUnit).filter_by(id=finished_unit_id).first()
        if not finished_unit:
            raise FinishedUnitNotFoundError(finished_unit_id)
        if finished_unit.recipe_id != recipe_id:
            raise FinishedUnitRecipeMismatchError(finished_unit_id, recipe_id)

        # Feature 016: Validate event exists if event_id provided
        if event_id is not None:
            event = session.query(Event).filter_by(id=event_id).first()
            if not event:
                raise EventNotFoundError(event_id)

        # Feature 037: Calculate expected yield with scale_factor
        # expected_yield = base_yield x scale_factor x num_batches
        base_yield = finished_unit.items_per_batch or 1
        expected_yield = int(base_yield * scale_factor * num_batches)

        # Feature 025: Validate actual_yield <= expected_yield (fail fast)
        if actual_yield > expected_yield:
            raise ActualYieldExceedsExpectedError(actual_yield, expected_yield)

        # Feature 025: Calculate loss quantity and determine production status
        loss_quantity = expected_yield - actual_yield

        if loss_quantity == 0:
            production_status = ProductionStatus.COMPLETE
        elif actual_yield == 0:
            production_status = ProductionStatus.TOTAL_LOSS
        else:
            production_status = ProductionStatus.PARTIAL_LOSS

        # F065: Check for planning snapshot reuse
        # If production is for a planned event, check if target has recipe_snapshot_id
        planning_snapshot_id = None
        snapshot_reused = False
        if event_id:
            target = session.query(EventProductionTarget).filter(
                EventProductionTarget.event_id == event_id,
                EventProductionTarget.recipe_id == recipe_id
            ).first()

            if target and target.recipe_snapshot_id:
                # Reuse snapshot from planning phase
                planning_snapshot_id = target.recipe_snapshot_id
                snapshot_reused = True
                logger.debug(
                    "Reusing planning snapshot",
                    extra={
                        "recipe_id": recipe_id,
                        "event_id": event_id,
                        "planning_snapshot_id": planning_snapshot_id,
                    },
                )

        if planning_snapshot_id:
            # F065: Reuse planning snapshot - create ProductionRun with existing snapshot
            snapshot_id = planning_snapshot_id

            # Get the snapshot data for ingredient consumption
            from src.models import RecipeSnapshot
            snapshot_model = session.get(RecipeSnapshot, snapshot_id)
            if not snapshot_model:
                raise RecipeNotFoundError(recipe_id)  # Snapshot missing, shouldn't happen
            # Use the accessor method to parse JSON string to list
            ingredients_data = snapshot_model.get_ingredients_data()

            # Create production run with planning snapshot reference
            temp_production_run = ProductionRun(
                recipe_id=recipe_id,
                finished_unit_id=finished_unit_id,
                num_batches=num_batches,
                expected_yield=expected_yield,
                actual_yield=actual_yield,
                produced_at=produced_at or utc_now(),
                notes=notes,
                total_ingredient_cost=Decimal("0.0000"),  # Will be updated
                per_unit_cost=Decimal("0.0000"),  # Will be updated
                event_id=event_id,
                production_status=production_status.value,
                loss_quantity=loss_quantity,
                recipe_snapshot_id=snapshot_id,  # Link to planning snapshot
            )
            session.add(temp_production_run)
            session.flush()

        else:
            # Legacy/ad-hoc production: Create new snapshot
            # Feature 037: Create snapshot FIRST - captures recipe state before production
            # Note: We create a temporary ProductionRun to get an ID for the snapshot,
            # then update it after. Alternative: create snapshot without run_id, then link.
            # Using the simpler approach: create snapshot with placeholder, update later
            temp_production_run = ProductionRun(
                recipe_id=recipe_id,
                finished_unit_id=finished_unit_id,
                num_batches=num_batches,
                expected_yield=expected_yield,
                actual_yield=actual_yield,
                produced_at=produced_at or utc_now(),
                notes=notes,
                total_ingredient_cost=Decimal("0.0000"),  # Will be updated
                per_unit_cost=Decimal("0.0000"),  # Will be updated
                event_id=event_id,
                production_status=production_status.value,
                loss_quantity=loss_quantity,
            )
            session.add(temp_production_run)
            session.flush()  # Get the ID

            # Now create the snapshot with the production_run_id
            snapshot = recipe_snapshot_service.create_recipe_snapshot(
                recipe_id=recipe_id,
                scale_factor=scale_factor,
                production_run_id=temp_production_run.id,
                session=session,
            )
            snapshot_id = snapshot["id"]

            # Link snapshot to production run
            temp_production_run.recipe_snapshot_id = snapshot_id

            # Get ingredients_data from the newly created snapshot
            ingredients_data = snapshot["ingredients_data"]

        # Feature 037: Use snapshot data for ingredient consumption
        # This ensures costs are calculated from the snapshot, not the live recipe
        # Note: ingredients_data is set in both branches above

        # Track consumption data
        total_ingredient_cost = Decimal("0.0000")
        consumption_records = []

        # Feature 037: Consume ingredients from snapshot data via FIFO
        # Apply scale_factor to base quantities, then multiply by num_batches
        for item in ingredients_data:
            ingredient_slug = item["ingredient_slug"]
            base_quantity = Decimal(str(item["quantity"]))
            unit = item["unit"]

            # quantity_needed = base_quantity x scale_factor x num_batches
            quantity_needed = base_quantity * Decimal(str(scale_factor)) * Decimal(str(num_batches))

            # Perform actual FIFO consumption - pass session for atomic transaction
            result = inventory_item_service.consume_fifo(
                ingredient_slug, quantity_needed, unit, dry_run=False, session=session
            )

            if not result["satisfied"]:
                # This shouldn't happen if check_can_produce was called first,
                # but handle it gracefully - rollback happens automatically
                log_operation(
                    logger,
                    operation="record_batch_production",
                    outcome="insufficient_inventory",
                    level=logging.WARNING,
                    recipe_id=recipe_id,
                    ingredient_slug=ingredient_slug,
                    quantity_needed=str(quantity_needed),
                    quantity_available=str(result["consumed"]),
                )
                raise InsufficientInventoryError(
                    ingredient_slug,
                    quantity_needed,
                    result["consumed"],
                    unit,
                )

            # Accumulate total cost
            consumed_cost = result["total_cost"]
            total_ingredient_cost += consumed_cost

            # Create consumption record data
            consumption_records.append(
                {
                    "ingredient_slug": ingredient_slug,
                    "quantity_consumed": result["consumed"],
                    "unit": unit,
                    "total_cost": consumed_cost,
                }
            )

        # Increment FinishedUnit inventory with audit trail (Feature 061)
        fg_inv.adjust_inventory(
            item_type="finished_unit",
            item_id=finished_unit_id,
            quantity=actual_yield,
            reason="production",
            notes=f"Production run #{temp_production_run.id}",
            session=session,
        )

        # Calculate per-unit cost (handle division by zero)
        if actual_yield > 0:
            per_unit_cost = total_ingredient_cost / Decimal(str(actual_yield))
        else:
            per_unit_cost = Decimal("0.0000")

        # Update the ProductionRun with actual costs (it was created earlier with placeholders)
        temp_production_run.total_ingredient_cost = total_ingredient_cost
        temp_production_run.per_unit_cost = per_unit_cost
        production_run = temp_production_run  # Use the same reference for the rest

        # Feature 025: Create ProductionLoss record if there are losses
        loss_record_id = None
        total_loss_cost = Decimal("0.0000")
        if loss_quantity > 0:
            total_loss_cost = loss_quantity * per_unit_cost
            loss_record = ProductionLoss(
                production_run_id=production_run.id,
                finished_unit_id=finished_unit_id,
                loss_category=(loss_category or LossCategory.OTHER).value,
                loss_quantity=loss_quantity,
                per_unit_cost=per_unit_cost,
                total_loss_cost=total_loss_cost,
                notes=loss_notes,
            )
            session.add(loss_record)
            session.flush()
            loss_record_id = loss_record.id

        # Create ProductionConsumption records
        for consumption_data in consumption_records:
            consumption = ProductionConsumption(
                production_run_id=production_run.id,
                ingredient_slug=consumption_data["ingredient_slug"],
                quantity_consumed=consumption_data["quantity_consumed"],
                unit=consumption_data["unit"],
                total_cost=consumption_data["total_cost"],
            )
            session.add(consumption)

        # Commit happens automatically via session_scope

        # Log successful production
        log_operation(
            logger,
            operation="record_batch_production",
            outcome="success",
            production_run_id=production_run.id,
            recipe_id=recipe_id,
            finished_unit_id=finished_unit_id,
            actual_yield=actual_yield,
            production_status=production_status.value,
            total_ingredient_cost=str(total_ingredient_cost),
        )

        return {
            "production_run_id": production_run.id,
            "recipe_id": recipe_id,
            "finished_unit_id": finished_unit_id,
            "num_batches": num_batches,
            "expected_yield": expected_yield,
            "actual_yield": actual_yield,
            "total_ingredient_cost": total_ingredient_cost,
            "per_unit_cost": per_unit_cost,
            "consumptions": consumption_records,
            "event_id": event_id,  # Feature 016
            "production_status": production_status.value,  # Feature 025
            "loss_quantity": loss_quantity,  # Feature 025
            "loss_record_id": loss_record_id,  # Feature 025
            "total_loss_cost": str(total_loss_cost),  # Feature 025
            "snapshot_id": snapshot_id,  # Feature 037
            "scale_factor": scale_factor,  # Feature 037
            "snapshot_reused": snapshot_reused,  # F065: True if planning snapshot was reused
        }


# =============================================================================
# Custom Exception for History Queries
# =============================================================================


class ProductionRunNotFoundError(ServiceError):
    """Raised when a production run cannot be found.

    Args:
        production_run_id: The production run ID that was not found
        correlation_id: Optional correlation ID for tracing

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, production_run_id: int, correlation_id: Optional[str] = None):
        self.production_run_id = production_run_id
        super().__init__(
            f"ProductionRun with ID {production_run_id} not found",
            correlation_id=correlation_id,
            production_run_id=production_run_id
        )


# =============================================================================
# History Query Functions
# =============================================================================


def get_production_history(
    *,
    recipe_id: Optional[int] = None,
    finished_unit_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    include_consumptions: bool = False,
    include_losses: bool = False,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """
    Query production run history with optional filters.

    Args:
        recipe_id: Optional filter by recipe ID
        finished_unit_id: Optional filter by finished unit ID
        start_date: Optional filter by minimum produced_at
        end_date: Optional filter by maximum produced_at
        limit: Maximum number of results (default 100)
        offset: Number of results to skip (for pagination)
        include_consumptions: If True, include consumption ledger details
        include_losses: If True, include ProductionLoss records (Feature 025)
        session: Database session (optional, creates one if not provided)

    Returns:
        List of production run dictionaries with details
    """
    if session is None:
        with session_scope() as session:
            return get_production_history(
                recipe_id=recipe_id,
                finished_unit_id=finished_unit_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset,
                include_consumptions=include_consumptions,
                include_losses=include_losses,
                session=session,
            )

    query = session.query(ProductionRun)

    # Apply filters
    if recipe_id:
        query = query.filter(ProductionRun.recipe_id == recipe_id)
    if finished_unit_id:
        query = query.filter(ProductionRun.finished_unit_id == finished_unit_id)
    if start_date:
        query = query.filter(ProductionRun.produced_at >= start_date)
    if end_date:
        query = query.filter(ProductionRun.produced_at <= end_date)

    # Eager load relationships to avoid N+1
    query = query.options(
        joinedload(ProductionRun.recipe),
        joinedload(ProductionRun.finished_unit),
    )
    if include_consumptions:
        query = query.options(joinedload(ProductionRun.consumptions))
    # Feature 025: Eager load losses relationship
    if include_losses:
        query = query.options(joinedload(ProductionRun.losses))

    # Order and paginate
    query = query.order_by(ProductionRun.produced_at.desc())
    query = query.offset(offset).limit(limit)

    runs = query.all()
    return [_production_run_to_dict(run, include_consumptions, include_losses) for run in runs]


def get_production_run(
    production_run_id: int,
    *,
    include_consumptions: bool = True,
    include_losses: bool = False,
    session: Session,
) -> Dict[str, Any]:
    """
    Get a single production run with full details.

    Args:
        production_run_id: ID of the production run
        include_consumptions: If True, include consumption ledger details
        include_losses: If True, include ProductionLoss records (Feature 025)
        session: Database session (required)

    Returns:
        Production run dictionary with details

    Raises:
        ProductionRunNotFoundError: If production run doesn't exist
    """
    query = session.query(ProductionRun).filter(ProductionRun.id == production_run_id)

    query = query.options(
        joinedload(ProductionRun.recipe),
        joinedload(ProductionRun.finished_unit),
    )
    if include_consumptions:
        query = query.options(joinedload(ProductionRun.consumptions))
    # Feature 025: Eager load losses relationship
    if include_losses:
        query = query.options(joinedload(ProductionRun.losses))

    run = query.first()
    if not run:
        raise ProductionRunNotFoundError(production_run_id)

    return _production_run_to_dict(run, include_consumptions, include_losses)


def _production_run_to_dict(
    run: ProductionRun,
    include_consumptions: bool = False,
    include_losses: bool = False,
) -> Dict[str, Any]:
    """Convert a ProductionRun to a dictionary representation."""
    result = {
        "id": run.id,
        "uuid": str(run.uuid) if run.uuid else None,
        "recipe_id": run.recipe_id,
        "finished_unit_id": run.finished_unit_id,
        "num_batches": run.num_batches,
        "expected_yield": run.expected_yield,
        "actual_yield": run.actual_yield,
        "produced_at": run.produced_at.isoformat() if run.produced_at else None,
        "notes": run.notes,
        "total_ingredient_cost": cost_to_string(run.total_ingredient_cost),
        "per_unit_cost": cost_to_string(run.per_unit_cost),
        # Feature 025: Always include loss tracking fields
        "production_status": run.production_status,
        "loss_quantity": run.loss_quantity,
    }

    # Add relationship data
    if run.recipe:
        result["recipe"] = {
            "id": run.recipe.id,
            "name": run.recipe.name,
            "slug": getattr(run.recipe, "slug", None),
        }
        result["recipe_name"] = run.recipe.name

    if run.finished_unit:
        result["finished_unit"] = {
            "id": run.finished_unit.id,
            "slug": run.finished_unit.slug,
            "display_name": run.finished_unit.display_name,
        }
        result["finished_unit_name"] = run.finished_unit.display_name

    if include_consumptions and run.consumptions:
        result["consumptions"] = [
            {
                "id": c.id,
                "uuid": str(c.uuid) if c.uuid else None,
                "ingredient_slug": c.ingredient_slug,
                "quantity_consumed": str(c.quantity_consumed),
                "unit": c.unit,
                "total_cost": cost_to_string(c.total_cost),
            }
            for c in run.consumptions
        ]

    # Feature 025: Include losses when requested
    if include_losses and run.losses:
        result["losses"] = [
            {
                "id": loss.id,
                "uuid": str(loss.uuid) if loss.uuid else None,
                "loss_category": loss.loss_category,
                "loss_quantity": loss.loss_quantity,
                "per_unit_cost": cost_to_string(loss.per_unit_cost),
                "total_loss_cost": cost_to_string(loss.total_loss_cost),
                "notes": loss.notes,
            }
            for loss in run.losses
        ]

    return result


# =============================================================================
# Import/Export Functions
# =============================================================================


def export_production_history(
    *,
    recipe_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    session=None,
) -> Dict[str, Any]:
    """
    Export production history to JSON-compatible dict.

    Uses slugs/names instead of IDs for portability.
    Decimal values are serialized as strings to preserve precision.

    Feature 025: v1.1 schema includes production_status, loss_quantity, and losses array.

    Args:
        recipe_id: Optional filter by recipe ID
        start_date: Optional filter by minimum produced_at
        end_date: Optional filter by maximum produced_at
        session: Optional database session

    Returns:
        Dict with version, exported_at timestamp, and production_runs list
    """
    # Create session if not provided
    if session is None:
        with session_scope() as session:
            return export_production_history(
                recipe_id=recipe_id,
                start_date=start_date,
                end_date=end_date,
                session=session,
            )

    # Feature 025: Include losses in export
    runs = get_production_history(
        recipe_id=recipe_id,
        start_date=start_date,
        end_date=end_date,
        include_consumptions=True,
        include_losses=True,  # Feature 025
        limit=10000,  # Export all matching
        session=session,
    )

    exported_runs = []
    for run in runs:
        exported_run = {
            "uuid": run.get("uuid"),
            "recipe_name": run.get("recipe", {}).get("name"),
            "finished_unit_slug": run.get("finished_unit", {}).get("slug"),
            "num_batches": run["num_batches"],
            "expected_yield": run["expected_yield"],
            "actual_yield": run["actual_yield"],
            "produced_at": run["produced_at"],
            "notes": run.get("notes"),
            "total_ingredient_cost": run["total_ingredient_cost"],
            "per_unit_cost": run["per_unit_cost"],
            # Feature 025: Add loss tracking fields
            "production_status": run.get("production_status", "complete"),
            "loss_quantity": run.get("loss_quantity", 0),
            "consumptions": [
                {
                    "uuid": c.get("uuid"),
                    "ingredient_slug": c["ingredient_slug"],
                    "quantity_consumed": c["quantity_consumed"],
                    "unit": c["unit"],
                    "total_cost": c["total_cost"],
                }
                for c in run.get("consumptions", [])
            ],
            # Feature 025: Add losses array
            "losses": [
                {
                    "uuid": loss.get("uuid"),
                    "loss_category": loss["loss_category"],
                    "loss_quantity": loss["loss_quantity"],
                    "per_unit_cost": loss["per_unit_cost"],
                    "total_loss_cost": loss["total_loss_cost"],
                    "notes": loss.get("notes"),
                }
                for loss in run.get("losses", [])
            ],
        }
        exported_runs.append(exported_run)

    return {
        "version": "1.1",  # Feature 025: Updated from 1.0
        "exported_at": utc_now().isoformat(),
        "production_runs": exported_runs,
    }


def import_production_history(
    data: Dict[str, Any],
    *,
    skip_duplicates: bool = True,
    session=None,
) -> Dict[str, Any]:
    """
    Import production history from JSON-compatible dict.

    Resolves references by name/slug. Validates all foreign keys exist.
    Uses UUIDs for duplicate detection.

    Feature 025: Handles both v1.0 (no loss data) and v1.1 (with loss data) schemas.

    Args:
        data: Dict with production_runs to import
        skip_duplicates: If True, skip existing UUIDs; if False, report as error
        session: Optional database session

    Returns:
        Dict with imported count, skipped count, and errors list
    """
    imported = 0
    skipped = 0
    errors = []

    # Feature 025: Detect version and transform v1.0 data to v1.1 format
    version = data.get("version", "1.0")
    if version == "1.0":
        for run_data in data.get("production_runs", []):
            # Add default loss fields for v1.0 data
            run_data.setdefault("production_status", "complete")
            run_data.setdefault("loss_quantity", 0)
            run_data.setdefault("losses", [])

    with session_scope() as session:
        for run_data in data.get("production_runs", []):
            try:
                run_uuid = run_data.get("uuid")

                # Check for duplicate by UUID if provided
                if run_uuid:
                    existing = session.query(ProductionRun).filter_by(uuid=run_uuid).first()
                    if existing:
                        if skip_duplicates:
                            skipped += 1
                            continue
                        else:
                            errors.append(f"Duplicate UUID: {run_uuid}")
                            continue

                # Resolve recipe by name
                recipe_name = run_data.get("recipe_name")
                recipe = session.query(Recipe).filter_by(name=recipe_name).first()
                if not recipe:
                    errors.append(f"Recipe not found: {recipe_name}")
                    continue

                # Resolve finished_unit by slug
                fu_slug = run_data.get("finished_unit_slug")
                finished_unit = session.query(FinishedUnit).filter_by(slug=fu_slug).first()
                if not finished_unit:
                    errors.append(f"FinishedUnit not found: {fu_slug}")
                    continue

                # Create ProductionRun (Feature 025: include loss tracking fields)
                run = ProductionRun(
                    uuid=run_uuid,
                    recipe_id=recipe.id,
                    finished_unit_id=finished_unit.id,
                    num_batches=run_data["num_batches"],
                    expected_yield=run_data["expected_yield"],
                    actual_yield=run_data["actual_yield"],
                    produced_at=datetime.fromisoformat(run_data["produced_at"]),
                    notes=run_data.get("notes"),
                    total_ingredient_cost=Decimal(run_data["total_ingredient_cost"]),
                    per_unit_cost=Decimal(run_data["per_unit_cost"]),
                    # Feature 025: Add loss tracking fields
                    production_status=run_data.get("production_status", "complete"),
                    loss_quantity=run_data.get("loss_quantity", 0),
                )
                session.add(run)
                session.flush()  # Get ID

                # Create consumptions
                for c_data in run_data.get("consumptions", []):
                    consumption = ProductionConsumption(
                        uuid=c_data.get("uuid"),
                        production_run_id=run.id,
                        ingredient_slug=c_data["ingredient_slug"],
                        quantity_consumed=Decimal(c_data["quantity_consumed"]),
                        unit=c_data["unit"],
                        total_cost=Decimal(c_data["total_cost"]),
                    )
                    session.add(consumption)

                # Feature 025: Create ProductionLoss records
                for loss_data in run_data.get("losses", []):
                    loss = ProductionLoss(
                        uuid=loss_data.get("uuid"),
                        production_run_id=run.id,
                        finished_unit_id=finished_unit.id,
                        loss_category=loss_data["loss_category"],
                        loss_quantity=loss_data["loss_quantity"],
                        per_unit_cost=Decimal(loss_data["per_unit_cost"]),
                        total_loss_cost=Decimal(loss_data["total_loss_cost"]),
                        notes=loss_data.get("notes"),
                    )
                    session.add(loss)

                imported += 1

            except Exception as e:
                errors.append(f"Error importing {run_data.get('uuid', 'unknown')}: {str(e)}")

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
    }
