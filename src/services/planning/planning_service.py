"""
Planning Service Facade for production planning (Feature 039).

This module provides a unified facade that orchestrates all planning modules:
- batch_calculation: Batch counts and recipe aggregation
- shopping_list: Shopping list generation and status
- feasibility: Production and assembly feasibility checks
- progress: Production and assembly progress tracking

The facade provides:
- calculate_plan(): Full plan calculation with persistence
- check_staleness(): Detect when plan needs recalculation
- get_plan_summary(): Get summary with phase statuses
- Delegation methods for all underlying module functions
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session


def _normalize_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize datetime to naive UTC for comparison.

    SQLite stores datetimes as naive (no timezone info), but our code
    uses timezone-aware datetimes from utc_now(). This function strips
    timezone info for consistent comparison.

    Args:
        dt: Datetime to normalize (may be None, naive, or aware)

    Returns:
        Naive datetime in UTC, or None if input is None
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convert to UTC then make naive
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


from collections import defaultdict

from src.models import (
    Event,
    EventAssemblyTarget,
    EventProductionTarget,
    FinishedGood,
    FinishedUnit,
    ProductionPlanSnapshot,
    Recipe,
    Composition,
)
from src.models.event import OutputMode
from src.services.database import session_scope
from src.services import recipe_service
from src.utils.datetime_utils import utc_now

# Import from sibling modules
from .batch_calculation import (
    calculate_batches,
    calculate_waste,
    create_batch_result,
    explode_bundle_requirements,
    aggregate_by_recipe,
    calculate_event_batch_requirements,
    RecipeBatchResult,
)
from .shopping_list import (
    calculate_purchase_gap,
    get_shopping_list as _get_shopping_list,
    get_items_to_buy,
    get_shopping_summary,
    mark_shopping_complete as _mark_shopping_complete,
    unmark_shopping_complete,
    is_shopping_complete,
    ShoppingListItem,
)
from .feasibility import (
    check_production_feasibility as _check_production_feasibility,
    check_assembly_feasibility as _check_assembly_feasibility,
    check_single_assembly_feasibility,
    FeasibilityStatus,
    FeasibilityResult,
)
from .progress import (
    get_production_progress as _get_production_progress,
    get_assembly_progress as _get_assembly_progress,
    get_overall_progress as _get_overall_progress,
    ProductionProgress,
    AssemblyProgress,
)


# =============================================================================
# Exceptions
# =============================================================================


class PlanningError(Exception):
    """Base exception for planning service errors."""

    pass


class StalePlanError(PlanningError):
    """Plan is stale and needs recalculation."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Plan is stale: {reason}")


class IncompleteRequirementsError(PlanningError):
    """Event requirements are incomplete."""

    def __init__(self, missing: List[str]):
        self.missing = missing
        super().__init__(f"Missing requirements: {', '.join(missing)}")


class EventNotConfiguredError(PlanningError):
    """Event output_mode not set."""

    def __init__(self, event_id: int):
        self.event_id = event_id
        super().__init__(
            f"Event {event_id} has no output_mode configured. "
            f"Set output_mode to BUNDLED or BULK_COUNT before calculating plan."
        )


class EventNotFoundError(PlanningError):
    """Event not found."""

    def __init__(self, event_id: int):
        self.event_id = event_id
        super().__init__(f"Event {event_id} not found")


# =============================================================================
# Plan Phase Enum and Summary DTO
# =============================================================================


class PlanPhase(str, Enum):
    """Phases of the production plan workflow."""

    REQUIREMENTS = "requirements"  # Define what to make
    SHOPPING = "shopping"  # Buy ingredients
    PRODUCTION = "production"  # Bake recipes
    ASSEMBLY = "assembly"  # Assemble bundles


class PhaseStatus(str, Enum):
    """Status of a plan phase."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclass
class PlanSummary:
    """Summary of production plan status.

    Attributes:
        event_id: Event this plan is for
        event_name: Event display name
        plan_id: ProductionPlanSnapshot ID (None if no plan)
        calculated_at: When plan was last calculated
        is_stale: Whether plan needs recalculation
        stale_reason: Why plan is stale (if applicable)
        phase_statuses: Status of each plan phase
        overall_status: Overall plan status
        production_progress: Production completion percentage
        assembly_progress: Assembly completion percentage
    """

    event_id: int
    event_name: str
    plan_id: Optional[int]
    calculated_at: Optional[datetime]
    is_stale: bool
    stale_reason: Optional[str]
    phase_statuses: Dict[PlanPhase, PhaseStatus]
    overall_status: PhaseStatus
    production_progress: float
    assembly_progress: float


# =============================================================================
# Core Planning Functions
# =============================================================================


def calculate_plan(
    event_id: int,
    *,
    force_recalculate: bool = False,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Calculate production plan for an event.

    This is the main orchestration function that:
    1. Validates event configuration
    2. Checks for existing non-stale plan (unless force_recalculate)
    3. Gets requirements based on output_mode
    4. Explodes bundles to unit quantities (if BUNDLED mode)
    5. Aggregates by recipe for batch calculations
    6. Generates shopping list
    7. Checks feasibility
    8. Persists to ProductionPlanSnapshot

    Args:
        event_id: Event to calculate plan for
        force_recalculate: If True, recalculate even if existing plan is fresh
        session: Optional database session

    Returns:
        Dict with:
            - plan_id: ProductionPlanSnapshot ID
            - calculated_at: Calculation timestamp
            - recipe_batches: List of recipe batch calculations
            - shopping_list: List of shopping list items
            - feasibility: Assembly feasibility results

    Raises:
        EventNotFoundError: Event doesn't exist
        EventNotConfiguredError: Event output_mode not set
    """
    if session is not None:
        return _calculate_plan_impl(event_id, force_recalculate, session)
    with session_scope() as session:
        return _calculate_plan_impl(event_id, force_recalculate, session)


def _calculate_plan_impl(
    event_id: int,
    force_recalculate: bool,
    session: Session,
) -> Dict[str, Any]:
    """Implementation of calculate_plan."""
    # Get and validate event
    event = session.get(Event, event_id)
    if event is None:
        raise EventNotFoundError(event_id)

    if event.output_mode is None:
        raise EventNotConfiguredError(event_id)

    # Check for existing non-stale plan
    if not force_recalculate:
        existing_plan = _get_latest_plan(event_id, session)
        if existing_plan and not existing_plan.is_stale:
            # Check if actually stale
            is_stale, reason = _check_staleness_impl(event_id, session)
            if not is_stale:
                # Return existing plan
                return _plan_to_dict(existing_plan)

    # Calculate batch requirements based on output mode
    if event.output_mode == OutputMode.BUNDLED:
        recipe_batches = _calculate_bundled_requirements(event, session)
    else:  # BULK_COUNT
        recipe_batches = _calculate_bulk_requirements(event, session)

    # Get timestamps for staleness tracking
    now = utc_now()
    requirements_ts = _get_latest_requirements_timestamp(event, session)
    recipes_ts = _get_latest_recipes_timestamp(recipe_batches, session)
    bundles_ts = _get_latest_bundles_timestamp(event, session)

    # Get shopping list for the event
    shopping_items = _get_shopping_list(event_id, session=session)

    # Aggregate ingredients across all recipes in the plan (WP04)
    aggregated_ingredients = _aggregate_plan_ingredients(recipe_batches, session)

    # Build calculation results JSON
    calculation_results = {
        "recipe_batches": [
            {
                "recipe_id": rb.recipe_id,
                "recipe_name": rb.recipe_name,
                "units_needed": rb.units_needed,
                "batches": rb.batches,
                "yield_per_batch": rb.yield_per_batch,
                "total_yield": rb.total_yield,
                "waste_units": rb.waste_units,
                "waste_percent": rb.waste_percent,
            }
            for rb in recipe_batches
        ],
        "aggregated_ingredients": aggregated_ingredients,
        "shopping_list": [
            {
                "ingredient_id": item.ingredient_id,
                "ingredient_slug": item.ingredient_slug,
                "ingredient_name": item.ingredient_name,
                "needed": str(item.needed),
                "in_stock": str(item.in_stock),
                "to_buy": str(item.to_buy),
                "unit": item.unit,
                "is_sufficient": item.is_sufficient,
            }
            for item in shopping_items
        ],
    }

    # Create or update snapshot
    snapshot = ProductionPlanSnapshot(
        event_id=event_id,
        calculated_at=now,
        requirements_updated_at=requirements_ts or now,
        recipes_updated_at=recipes_ts or now,
        bundles_updated_at=bundles_ts or now,
        calculation_results=calculation_results,
        is_stale=False,
        stale_reason=None,
    )
    session.add(snapshot)
    session.flush()

    # Get feasibility results
    feasibility_results = _check_assembly_feasibility(event_id, session=session)

    return {
        "plan_id": snapshot.id,
        "calculated_at": now.isoformat(),
        "recipe_batches": calculation_results["recipe_batches"],
        "shopping_list": calculation_results["shopping_list"],
        "feasibility": [
            {
                "finished_good_id": fr.finished_good_id,
                "finished_good_name": fr.finished_good_name,
                "target_quantity": fr.target_quantity,
                "can_assemble": fr.can_assemble,
                "status": fr.status.value,
                "missing_components": fr.missing_components,
            }
            for fr in feasibility_results
        ],
    }


def _calculate_bundled_requirements(
    event: Event,
    session: Session,
) -> List[RecipeBatchResult]:
    """Calculate requirements for BUNDLED output mode."""
    # Get bundle requirements from EventAssemblyTarget
    bundle_requirements: Dict[int, int] = {}
    for target in event.assembly_targets:
        bundle_requirements[target.finished_good_id] = target.target_quantity

    if not bundle_requirements:
        return []

    return calculate_event_batch_requirements(bundle_requirements, session=session)


def _calculate_bulk_requirements(
    event: Event,
    session: Session,
) -> List[RecipeBatchResult]:
    """Calculate requirements for BULK_COUNT output mode."""
    # In BULK_COUNT mode, use EventProductionTarget directly
    results = []
    for target in event.production_targets:
        recipe = session.get(Recipe, target.recipe_id)
        if recipe:
            # F056: Use FinishedUnit.items_per_batch instead of deprecated yield_quantity
            items_per_batch = 1
            if recipe.finished_units:
                primary_unit = recipe.finished_units[0]
                if primary_unit.items_per_batch and primary_unit.items_per_batch > 0:
                    items_per_batch = primary_unit.items_per_batch
            result = create_batch_result(
                recipe_id=recipe.id,
                recipe_name=recipe.name,
                units_needed=target.target_batches * items_per_batch,  # Convert batches to units
                yield_per_batch=items_per_batch,
            )
            results.append(result)
    return results


def _get_latest_plan(
    event_id: int,
    session: Session,
) -> Optional[ProductionPlanSnapshot]:
    """Get the latest plan snapshot for an event."""
    return (
        session.query(ProductionPlanSnapshot)
        .filter(ProductionPlanSnapshot.event_id == event_id)
        .order_by(ProductionPlanSnapshot.calculated_at.desc())
        .first()
    )


def _plan_to_dict(plan: ProductionPlanSnapshot) -> Dict[str, Any]:
    """Convert a plan snapshot to the standard return format."""
    return {
        "plan_id": plan.id,
        "calculated_at": (plan.calculated_at.isoformat() if plan.calculated_at else None),
        "recipe_batches": plan.get_recipe_batches(),
        "shopping_list": plan.get_shopping_list(),
        "feasibility": [],  # Would need to recalculate for live data
    }


def _get_latest_requirements_timestamp(
    event: Event,
    session: Session,
) -> Optional[datetime]:
    """Get the latest updated_at from assembly/production targets."""
    latest = None

    for target in event.assembly_targets:
        target_ts = _normalize_datetime(target.updated_at)
        if target_ts and (latest is None or target_ts > latest):
            latest = target_ts

    for target in event.production_targets:
        target_ts = _normalize_datetime(target.updated_at)
        if target_ts and (latest is None or target_ts > latest):
            latest = target_ts

    return latest


def _get_latest_recipes_timestamp(
    recipe_batches: List[RecipeBatchResult],
    session: Session,
) -> Optional[datetime]:
    """Get the latest last_modified from recipes in the plan."""
    latest = None

    for rb in recipe_batches:
        recipe = session.get(Recipe, rb.recipe_id)
        recipe_ts = _normalize_datetime(recipe.last_modified) if recipe else None
        if recipe_ts:
            if latest is None or recipe_ts > latest:
                latest = recipe_ts

    return latest


def _get_latest_bundles_timestamp(
    event: Event,
    session: Session,
) -> Optional[datetime]:
    """Get the latest updated_at from finished goods in the plan."""
    latest = None

    for target in event.assembly_targets:
        fg = session.get(FinishedGood, target.finished_good_id)
        fg_ts = _normalize_datetime(fg.updated_at) if fg else None
        if fg_ts:
            if latest is None or fg_ts > latest:
                latest = fg_ts

    return latest


def _aggregate_plan_ingredients(
    recipe_batches: List[RecipeBatchResult],
    session: Session,
) -> List[Dict[str, Any]]:
    """Aggregate ingredients across all recipe batches in the plan.

    For each recipe in the plan, gets aggregated ingredients (including
    nested sub-recipes) and combines them by ingredient slug.

    Args:
        recipe_batches: List of RecipeBatchResult from batch calculation
        session: SQLAlchemy session for transactional atomicity

    Returns:
        List of aggregated ingredients with structure:
        [
            {
                "ingredient_slug": str,
                "display_name": str,
                "quantity": float,
                "unit": str,
                "cost_per_unit": float
            },
            ...
        ]
    """
    # Aggregate by (ingredient_slug, unit) to handle same ingredient with different units
    totals: Dict[tuple, Dict[str, Any]] = defaultdict(lambda: {
        "ingredient_slug": "",
        "display_name": "",
        "quantity": 0.0,
        "unit": "",
        "cost_per_unit": 0.0,
        "_cost_sources": [],  # Track for weighted average cost
    })

    for rb in recipe_batches:
        # Calculate multiplier: batches needed
        # get_aggregated_ingredients already handles recipe yield internally
        multiplier = float(rb.batches)

        try:
            # Get ingredients for this recipe (includes nested sub-recipes)
            ingredients = recipe_service.get_aggregated_ingredients(
                rb.recipe_id, multiplier=multiplier, session=session
            )
        except Exception:
            # Skip if recipe not found or other error
            continue

        for ing in ingredients:
            # Get ingredient slug from the ingredient object
            ingredient_obj = ing.get("ingredient")
            ingredient_slug = (
                ingredient_obj.slug if ingredient_obj and ingredient_obj.slug
                else f"ingredient-{ing.get('ingredient_id', 'unknown')}"
            )
            unit = ing.get("unit", "")
            key = (ingredient_slug, unit)

            totals[key]["ingredient_slug"] = ingredient_slug
            totals[key]["display_name"] = ing.get("ingredient_name", "Unknown")
            totals[key]["unit"] = unit
            totals[key]["quantity"] += float(ing.get("total_quantity", 0))

            # Get cost from ingredient's preferred product (if available)
            if ingredient_obj:
                preferred = ingredient_obj.get_preferred_product()
                if preferred:
                    cost = preferred.get_current_cost_per_unit()
                    if cost > 0:
                        totals[key]["_cost_sources"].append({
                            "quantity": float(ing.get("total_quantity", 0)),
                            "cost": cost
                        })

    # Build final result with weighted average cost
    result = []
    for key, data in totals.items():
        cost_per_unit = 0.0
        if data["_cost_sources"]:
            total_qty = sum(s["quantity"] for s in data["_cost_sources"])
            if total_qty > 0:
                cost_per_unit = sum(
                    s["quantity"] * s["cost"] for s in data["_cost_sources"]
                ) / total_qty

        result.append({
            "ingredient_slug": data["ingredient_slug"] or "unknown",
            "display_name": data["display_name"] or data["ingredient_slug"],
            "quantity": round(data["quantity"], 4),
            "unit": data["unit"] or "each",
            "cost_per_unit": round(cost_per_unit, 4),
        })

    # Sort by display name for consistent ordering
    return sorted(result, key=lambda x: x["display_name"])


# =============================================================================
# Staleness Detection
# =============================================================================


def check_staleness(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> Tuple[bool, Optional[str]]:
    """Check if plan is stale.

    Compares the calculated_at timestamp of the latest plan against:
    - Event.last_modified
    - EventAssemblyTarget.updated_at (each)
    - EventProductionTarget.updated_at (each)
    - Recipe.last_modified (each in plan)
    - FinishedGood.updated_at (each)
    - Composition.created_at (bundle contents)

    Args:
        event_id: Event to check
        session: Optional database session

    Returns:
        Tuple of (is_stale: bool, reason: Optional[str])
        - is_stale: True if plan needs recalculation
        - reason: Human-readable explanation if stale
    """
    if session is not None:
        return _check_staleness_impl(event_id, session)
    with session_scope() as session:
        return _check_staleness_impl(event_id, session)


def _check_staleness_impl(
    event_id: int,
    session: Session,
) -> Tuple[bool, Optional[str]]:
    """Implementation of check_staleness."""
    # Get latest plan
    plan = _get_latest_plan(event_id, session)
    if plan is None:
        return True, "No plan exists for this event"

    calculated_at = _normalize_datetime(plan.calculated_at)
    if calculated_at is None:
        return True, "Plan has no calculation timestamp"

    # Get event
    event = session.get(Event, event_id)
    if event is None:
        return True, "Event not found"

    # Check event modification
    event_modified = _normalize_datetime(event.last_modified)
    if event_modified and event_modified > calculated_at:
        return True, "Event modified since plan calculation"

    # Check assembly targets
    for target in event.assembly_targets:
        target_updated = _normalize_datetime(target.updated_at)
        if target_updated and target_updated > calculated_at:
            fg = session.get(FinishedGood, target.finished_good_id)
            name = fg.display_name if fg else f"ID {target.finished_good_id}"
            return True, f"Assembly target '{name}' modified"

    # Check production targets
    for target in event.production_targets:
        target_updated = _normalize_datetime(target.updated_at)
        if target_updated and target_updated > calculated_at:
            recipe = session.get(Recipe, target.recipe_id)
            name = recipe.name if recipe else f"ID {target.recipe_id}"
            return True, f"Production target '{name}' modified"

    # Check recipes in plan
    for recipe_batch in plan.get_recipe_batches():
        recipe = session.get(Recipe, recipe_batch["recipe_id"])
        recipe_modified = _normalize_datetime(recipe.last_modified) if recipe else None
        if recipe_modified and recipe_modified > calculated_at:
            return True, f"Recipe '{recipe.name}' modified"

    # Check finished goods
    for target in event.assembly_targets:
        fg = session.get(FinishedGood, target.finished_good_id)
        if fg:
            fg_updated = _normalize_datetime(fg.updated_at)
            if fg_updated and fg_updated > calculated_at:
                return True, f"Bundle '{fg.display_name}' modified"

            # Check compositions (created_at and updated_at)
            compositions = session.query(Composition).filter(Composition.assembly_id == fg.id).all()
            for comp in compositions:
                comp_created = _normalize_datetime(comp.created_at)
                if comp_created and comp_created > calculated_at:
                    return True, f"Bundle '{fg.display_name}' contents changed"
                # Check composition updates (WP05 T023)
                comp_updated = _normalize_datetime(comp.updated_at)
                if comp_updated and comp_updated > calculated_at:
                    return True, f"Bundle '{fg.display_name}' composition modified"

    # Check FinishedUnit yield changes (WP05 T024/T025)
    # Get finished unit IDs from production targets and compositions
    finished_unit_ids = set()

    # From production targets (if recipe links to finished unit)
    for target in event.production_targets:
        recipe = session.get(Recipe, target.recipe_id)
        if recipe:
            # Find finished units that use this recipe
            fus = session.query(FinishedUnit).filter(FinishedUnit.recipe_id == recipe.id).all()
            for fu in fus:
                finished_unit_ids.add(fu.id)

    # From assembly compositions
    for target in event.assembly_targets:
        compositions = session.query(Composition).filter(
            Composition.assembly_id == target.finished_good_id,
            Composition.finished_unit_id.isnot(None)
        ).all()
        for comp in compositions:
            finished_unit_ids.add(comp.finished_unit_id)

    # Check each finished unit for yield changes
    for fu_id in finished_unit_ids:
        fu = session.get(FinishedUnit, fu_id)
        if fu:
            fu_updated = _normalize_datetime(fu.updated_at)
            if fu_updated and fu_updated > calculated_at:
                return True, f"Finished unit '{fu.display_name}' yield changed"

    return False, None


# =============================================================================
# Plan Summary
# =============================================================================


def get_plan_summary(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> PlanSummary:
    """Get summary of current plan status.

    Args:
        event_id: Event to get summary for
        session: Optional database session

    Returns:
        PlanSummary with phase statuses and progress
    """
    if session is not None:
        return _get_plan_summary_impl(event_id, session)
    with session_scope() as session:
        return _get_plan_summary_impl(event_id, session)


def _get_plan_summary_impl(
    event_id: int,
    session: Session,
) -> PlanSummary:
    """Implementation of get_plan_summary."""
    event = session.get(Event, event_id)
    if event is None:
        raise EventNotFoundError(event_id)

    plan = _get_latest_plan(event_id, session)

    # Check staleness
    is_stale, stale_reason = _check_staleness_impl(event_id, session)

    # Get progress
    prod_progress = _get_overall_progress(event_id, session=session)

    # Determine phase statuses
    phase_statuses = _calculate_phase_statuses(event, plan, prod_progress, session)

    # Determine overall status
    overall_status = _calculate_overall_status(phase_statuses)

    return PlanSummary(
        event_id=event_id,
        event_name=event.name,
        plan_id=plan.id if plan else None,
        calculated_at=plan.calculated_at if plan else None,
        is_stale=is_stale,
        stale_reason=stale_reason,
        phase_statuses=phase_statuses,
        overall_status=overall_status,
        production_progress=prod_progress.get("production_percent", 0),
        assembly_progress=prod_progress.get("assembly_percent", 0),
    )


def _calculate_phase_statuses(
    event: Event,
    plan: Optional[ProductionPlanSnapshot],
    progress: Dict[str, Any],
    session: Session,
) -> Dict[PlanPhase, PhaseStatus]:
    """Calculate status for each plan phase."""
    statuses = {}

    # Requirements phase
    has_requirements = len(event.assembly_targets) > 0 or len(event.production_targets) > 0
    if has_requirements:
        statuses[PlanPhase.REQUIREMENTS] = PhaseStatus.COMPLETE
    else:
        statuses[PlanPhase.REQUIREMENTS] = PhaseStatus.NOT_STARTED

    # Shopping phase
    if plan and plan.shopping_complete:
        statuses[PlanPhase.SHOPPING] = PhaseStatus.COMPLETE
    elif plan:
        statuses[PlanPhase.SHOPPING] = PhaseStatus.IN_PROGRESS
    else:
        statuses[PlanPhase.SHOPPING] = PhaseStatus.NOT_STARTED

    # Production phase (progress is a dict with production_percent key)
    prod_pct = progress.get("production_percent", 0)
    if prod_pct >= 100:
        statuses[PlanPhase.PRODUCTION] = PhaseStatus.COMPLETE
    elif prod_pct > 0:
        statuses[PlanPhase.PRODUCTION] = PhaseStatus.IN_PROGRESS
    else:
        statuses[PlanPhase.PRODUCTION] = PhaseStatus.NOT_STARTED

    # Assembly phase
    asm_pct = progress.get("assembly_percent", 0)
    if asm_pct >= 100:
        statuses[PlanPhase.ASSEMBLY] = PhaseStatus.COMPLETE
    elif asm_pct > 0:
        statuses[PlanPhase.ASSEMBLY] = PhaseStatus.IN_PROGRESS
    else:
        statuses[PlanPhase.ASSEMBLY] = PhaseStatus.NOT_STARTED

    return statuses


def _calculate_overall_status(
    phase_statuses: Dict[PlanPhase, PhaseStatus],
) -> PhaseStatus:
    """Calculate overall status from phase statuses."""
    all_complete = all(status == PhaseStatus.COMPLETE for status in phase_statuses.values())
    any_in_progress = any(status == PhaseStatus.IN_PROGRESS for status in phase_statuses.values())
    any_complete = any(status == PhaseStatus.COMPLETE for status in phase_statuses.values())

    if all_complete:
        return PhaseStatus.COMPLETE
    elif any_in_progress or any_complete:
        return PhaseStatus.IN_PROGRESS
    else:
        return PhaseStatus.NOT_STARTED


# =============================================================================
# Facade Methods: Batch Calculation
# =============================================================================


def get_recipe_batches(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> List[RecipeBatchResult]:
    """Get recipe batch calculations for an event.

    Delegates to batch_calculation module.

    Args:
        event_id: Event to get batches for
        session: Optional database session

    Returns:
        List of RecipeBatchResult
    """
    if session is not None:
        return _get_recipe_batches_impl(event_id, session)
    with session_scope() as session:
        return _get_recipe_batches_impl(event_id, session)


def _get_recipe_batches_impl(
    event_id: int,
    session: Session,
) -> List[RecipeBatchResult]:
    """Implementation of get_recipe_batches."""
    event = session.get(Event, event_id)
    if event is None:
        raise EventNotFoundError(event_id)

    if event.output_mode == OutputMode.BUNDLED:
        return _calculate_bundled_requirements(event, session)
    else:
        return _calculate_bulk_requirements(event, session)


def calculate_batches_for_quantity(
    units_needed: int,
    yield_per_batch: int,
) -> Dict[str, Any]:
    """Utility for ad-hoc batch calculation.

    Args:
        units_needed: Total units required
        yield_per_batch: Units per batch

    Returns:
        Dict with batches, total_yield, waste_units, waste_percent
    """
    batches = calculate_batches(units_needed, yield_per_batch)
    total_yield = batches * yield_per_batch
    waste_units, waste_percent = calculate_waste(units_needed, batches, yield_per_batch)

    return {
        "batches": batches,
        "total_yield": total_yield,
        "waste_units": waste_units,
        "waste_percent": waste_percent,
    }


# =============================================================================
# Facade Methods: Shopping List
# =============================================================================


def get_shopping_list(
    event_id: int,
    *,
    include_sufficient: bool = True,
    session: Optional[Session] = None,
) -> List[ShoppingListItem]:
    """Get shopping list for an event.

    Delegates to shopping_list module.

    Args:
        event_id: Event to get shopping list for
        include_sufficient: If True, include items with sufficient stock
        session: Optional database session

    Returns:
        List of ShoppingListItem
    """
    return _get_shopping_list(event_id, include_sufficient=include_sufficient, session=session)


def mark_shopping_complete(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> bool:
    """Mark shopping as complete for an event.

    Delegates to shopping_list module.

    Args:
        event_id: Event to mark shopping complete for
        session: Optional database session

    Returns:
        True if successful, False if no snapshot exists
    """
    return _mark_shopping_complete(event_id, session=session)


# =============================================================================
# Facade Methods: Feasibility
# =============================================================================


def check_production_feasibility(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Check production feasibility for an event.

    Delegates to feasibility module.

    Args:
        event_id: Event to check
        session: Optional database session

    Returns:
        List of production feasibility results
    """
    return _check_production_feasibility(event_id, session=session)


def check_assembly_feasibility(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> List[FeasibilityResult]:
    """Check assembly feasibility for an event.

    Delegates to feasibility module.

    Args:
        event_id: Event to check
        session: Optional database session

    Returns:
        List of FeasibilityResult
    """
    return _check_assembly_feasibility(event_id, session=session)


# =============================================================================
# Facade Methods: Progress
# =============================================================================


def get_production_progress(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> List[ProductionProgress]:
    """Get production progress for an event.

    Delegates to progress module.

    Args:
        event_id: Event to get progress for
        session: Optional database session

    Returns:
        List of ProductionProgress
    """
    return _get_production_progress(event_id, session=session)


def get_assembly_progress(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> List[AssemblyProgress]:
    """Get assembly progress for an event.

    Delegates to progress module.

    Args:
        event_id: Event to get progress for
        session: Optional database session

    Returns:
        List of AssemblyProgress
    """
    return _get_assembly_progress(event_id, session=session)


def get_overall_progress(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> Any:
    """Get overall progress for an event.

    Delegates to progress module.

    Args:
        event_id: Event to get progress for
        session: Optional database session

    Returns:
        OverallProgress dataclass
    """
    return _get_overall_progress(event_id, session=session)


# =============================================================================
# Assembly Checklist Methods
# =============================================================================


def get_assembly_checklist(
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Get assembly checklist for an event.

    Returns list of bundles with:
    - target quantity
    - assembled count
    - available to assemble

    Args:
        event_id: Event to get checklist for
        session: Optional database session

    Returns:
        List of assembly checklist items
    """
    if session is not None:
        return _get_assembly_checklist_impl(event_id, session)
    with session_scope() as session:
        return _get_assembly_checklist_impl(event_id, session)


def _get_assembly_checklist_impl(
    event_id: int,
    session: Session,
) -> List[Dict[str, Any]]:
    """Implementation of get_assembly_checklist."""
    targets = (
        session.query(EventAssemblyTarget).filter(EventAssemblyTarget.event_id == event_id).all()
    )

    checklist = []
    for target in targets:
        fg = session.get(FinishedGood, target.finished_good_id)
        if not fg:
            continue

        # Get feasibility for this bundle
        feasibility = check_single_assembly_feasibility(
            target.finished_good_id, target.target_quantity, session=session
        )

        checklist.append(
            {
                "finished_good_id": target.finished_good_id,
                "finished_good_name": fg.display_name,
                "target_quantity": target.target_quantity,
                "assembled_count": fg.inventory_count or 0,
                "can_assemble": feasibility.can_assemble,
                "status": feasibility.status.value,
                "remaining": max(0, target.target_quantity - (fg.inventory_count or 0)),
            }
        )

    return checklist


def record_assembly_confirmation(
    finished_good_id: int,
    quantity: int,
    event_id: int,
    *,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Record assembly confirmation (Phase 2 - status tracking only).

    This is a status tracking operation only - no inventory transactions
    are performed in Phase 2.

    Args:
        finished_good_id: Bundle being assembled
        quantity: Number assembled
        event_id: Event this assembly is for
        session: Optional database session

    Returns:
        Confirmation details
    """
    if session is not None:
        return _record_assembly_confirmation_impl(finished_good_id, quantity, event_id, session)
    with session_scope() as session:
        return _record_assembly_confirmation_impl(finished_good_id, quantity, event_id, session)


def _record_assembly_confirmation_impl(
    finished_good_id: int,
    quantity: int,
    event_id: int,
    session: Session,
) -> Dict[str, Any]:
    """Implementation of record_assembly_confirmation."""
    fg = session.get(FinishedGood, finished_good_id)
    if not fg:
        raise PlanningError(f"FinishedGood {finished_good_id} not found")

    # Note: In Phase 2, this is status tracking only
    # No inventory consumption happens here
    # The actual inventory transactions happen through assembly_service.record_assembly()

    return {
        "finished_good_id": finished_good_id,
        "finished_good_name": fg.display_name,
        "quantity_confirmed": quantity,
        "event_id": event_id,
        "note": "Phase 2: Status tracking only - use assembly_service for inventory transactions",
    }
