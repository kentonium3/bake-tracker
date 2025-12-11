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

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import joinedload

from src.models import ProductionRun, ProductionConsumption, Recipe, FinishedUnit, Event
from src.services.database import session_scope
from src.services import inventory_item_service
from src.services.recipe_service import get_aggregated_ingredients


# =============================================================================
# Custom Exceptions
# =============================================================================


class RecipeNotFoundError(Exception):
    """Raised when a recipe cannot be found."""

    def __init__(self, recipe_id: int):
        self.recipe_id = recipe_id
        super().__init__(f"Recipe with ID {recipe_id} not found")


class FinishedUnitNotFoundError(Exception):
    """Raised when a finished unit cannot be found."""

    def __init__(self, finished_unit_id: int):
        self.finished_unit_id = finished_unit_id
        super().__init__(f"FinishedUnit with ID {finished_unit_id} not found")


class FinishedUnitRecipeMismatchError(Exception):
    """Raised when a finished unit does not belong to the specified recipe."""

    def __init__(self, finished_unit_id: int, recipe_id: int):
        self.finished_unit_id = finished_unit_id
        self.recipe_id = recipe_id
        super().__init__(
            f"FinishedUnit {finished_unit_id} does not belong to Recipe {recipe_id}"
        )


class InsufficientInventoryError(Exception):
    """Raised when there is insufficient inventory for production."""

    def __init__(
        self, ingredient_slug: str, needed: Decimal, available: Decimal, unit: str
    ):
        self.ingredient_slug = ingredient_slug
        self.needed = needed
        self.available = available
        self.unit = unit
        super().__init__(
            f"Insufficient {ingredient_slug}: need {needed} {unit}, have {available} {unit}"
        )


class EventNotFoundError(Exception):
    """Raised when an event cannot be found."""

    def __init__(self, event_id: int):
        self.event_id = event_id
        super().__init__(f"Event with ID {event_id} not found")


# =============================================================================
# Availability Check Functions
# =============================================================================


def check_can_produce(
    recipe_id: int,
    num_batches: int,
    *,
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
    with session_scope() as session:
        # Validate recipe exists
        recipe = session.query(Recipe).filter_by(id=recipe_id).first()
        if not recipe:
            raise RecipeNotFoundError(recipe_id)

        # Get aggregated ingredients (handles nested recipes)
        try:
            aggregated = get_aggregated_ingredients(recipe_id, multiplier=num_batches)
        except Exception as e:
            raise RecipeNotFoundError(recipe_id) from e

        missing = []

        for item in aggregated:
            ingredient = item["ingredient"]
            ingredient_slug = ingredient.slug
            ingredient_name = ingredient.display_name
            quantity_needed = Decimal(str(item["total_quantity"]))
            unit = item["unit"]

            # Perform dry-run FIFO check
            result = inventory_item_service.consume_fifo(
                ingredient_slug, quantity_needed, dry_run=True
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

        return {
            "can_produce": len(missing) == 0,
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
    session=None,
) -> Dict[str, Any]:
    """
    Record a batch production run with FIFO consumption.

    This function atomically:
    1. Validates recipe and finished unit
    2. Validates event if provided (Feature 016)
    3. Consumes ingredients from inventory via FIFO
    4. Increments FinishedUnit.inventory_count by actual_yield
    5. Creates ProductionRun and ProductionConsumption records
    6. Calculates per-unit cost based on actual yield

    Args:
        recipe_id: ID of the recipe being produced
        finished_unit_id: ID of the FinishedUnit being produced
        num_batches: Number of recipe batches made
        actual_yield: Actual number of units produced (can be 0 for failed batches)
        produced_at: Optional production timestamp (defaults to now)
        notes: Optional production notes
        event_id: Optional event ID to link production to (Feature 016)
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

    Raises:
        RecipeNotFoundError: If recipe doesn't exist
        FinishedUnitNotFoundError: If finished unit doesn't exist
        FinishedUnitRecipeMismatchError: If finished unit doesn't belong to recipe
        InsufficientInventoryError: If ingredient inventory is insufficient
        EventNotFoundError: If event_id is provided but event doesn't exist
    """
    with session_scope() as session:
        # Validate recipe exists
        recipe = session.query(Recipe).filter_by(id=recipe_id).first()
        if not recipe:
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

        # Calculate expected yield based on finished unit configuration
        if finished_unit.items_per_batch:
            expected_yield = num_batches * finished_unit.items_per_batch
        else:
            expected_yield = num_batches  # Fallback if not configured

        # Get aggregated ingredients (handles nested recipes)
        aggregated = get_aggregated_ingredients(recipe_id, multiplier=num_batches)

        # Track consumption data
        total_ingredient_cost = Decimal("0.0000")
        consumption_records = []

        # Consume ingredients via FIFO - ALL within this same session for atomicity
        for item in aggregated:
            ingredient = item["ingredient"]
            ingredient_slug = ingredient.slug
            quantity_needed = Decimal(str(item["total_quantity"]))
            unit = item["unit"]

            # Perform actual FIFO consumption - pass session for atomic transaction
            result = inventory_item_service.consume_fifo(
                ingredient_slug, quantity_needed, dry_run=False, session=session
            )

            if not result["satisfied"]:
                # This shouldn't happen if check_can_produce was called first,
                # but handle it gracefully - rollback happens automatically
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

        # Increment FinishedUnit inventory (same session, atomic with consumption)
        finished_unit.inventory_count += actual_yield

        # Calculate per-unit cost (handle division by zero)
        if actual_yield > 0:
            per_unit_cost = total_ingredient_cost / Decimal(str(actual_yield))
        else:
            per_unit_cost = Decimal("0.0000")

        # Create ProductionRun record
        production_run = ProductionRun(
            recipe_id=recipe_id,
            finished_unit_id=finished_unit_id,
            num_batches=num_batches,
            expected_yield=expected_yield,
            actual_yield=actual_yield,
            produced_at=produced_at or datetime.utcnow(),
            notes=notes,
            total_ingredient_cost=total_ingredient_cost,
            per_unit_cost=per_unit_cost,
            event_id=event_id,  # Feature 016
        )
        session.add(production_run)
        session.flush()  # Get the ID

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
        }


# =============================================================================
# Custom Exception for History Queries
# =============================================================================


class ProductionRunNotFoundError(Exception):
    """Raised when a production run cannot be found."""

    def __init__(self, production_run_id: int):
        self.production_run_id = production_run_id
        super().__init__(f"ProductionRun with ID {production_run_id} not found")


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
    session=None,
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
        session: Optional database session

    Returns:
        List of production run dictionaries with details
    """
    with session_scope() as session:
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

        # Order and paginate
        query = query.order_by(ProductionRun.produced_at.desc())
        query = query.offset(offset).limit(limit)

        runs = query.all()
        return [_production_run_to_dict(run, include_consumptions) for run in runs]


def get_production_run(
    production_run_id: int,
    *,
    include_consumptions: bool = True,
    session=None,
) -> Dict[str, Any]:
    """
    Get a single production run with full details.

    Args:
        production_run_id: ID of the production run
        include_consumptions: If True, include consumption ledger details
        session: Optional database session

    Returns:
        Production run dictionary with details

    Raises:
        ProductionRunNotFoundError: If production run doesn't exist
    """
    with session_scope() as session:
        query = session.query(ProductionRun).filter(
            ProductionRun.id == production_run_id
        )

        query = query.options(
            joinedload(ProductionRun.recipe),
            joinedload(ProductionRun.finished_unit),
        )
        if include_consumptions:
            query = query.options(joinedload(ProductionRun.consumptions))

        run = query.first()
        if not run:
            raise ProductionRunNotFoundError(production_run_id)

        return _production_run_to_dict(run, include_consumptions)


def _production_run_to_dict(
    run: ProductionRun, include_consumptions: bool = False
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
        "total_ingredient_cost": str(run.total_ingredient_cost),
        "per_unit_cost": str(run.per_unit_cost),
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
                "total_cost": str(c.total_cost),
            }
            for c in run.consumptions
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

    Args:
        recipe_id: Optional filter by recipe ID
        start_date: Optional filter by minimum produced_at
        end_date: Optional filter by maximum produced_at
        session: Optional database session

    Returns:
        Dict with version, exported_at timestamp, and production_runs list
    """
    runs = get_production_history(
        recipe_id=recipe_id,
        start_date=start_date,
        end_date=end_date,
        include_consumptions=True,
        limit=10000,  # Export all matching
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
        }
        exported_runs.append(exported_run)

    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
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

    with session_scope() as session:
        for run_data in data.get("production_runs", []):
            try:
                run_uuid = run_data.get("uuid")

                # Check for duplicate by UUID if provided
                if run_uuid:
                    existing = (
                        session.query(ProductionRun).filter_by(uuid=run_uuid).first()
                    )
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
                finished_unit = (
                    session.query(FinishedUnit).filter_by(slug=fu_slug).first()
                )
                if not finished_unit:
                    errors.append(f"FinishedUnit not found: {fu_slug}")
                    continue

                # Create ProductionRun
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

                imported += 1

            except Exception as e:
                errors.append(
                    f"Error importing {run_data.get('uuid', 'unknown')}: {str(e)}"
                )

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
    }
