"""
BatchProductionService Contract

Service interface for batch production tracking.
Handles Recipe -> FinishedUnit production with FIFO ingredient consumption.
"""

from typing import Dict, Any, List, Optional, TypedDict
from decimal import Decimal
from datetime import datetime


class MissingIngredient(TypedDict):
    """Structure for missing ingredient details."""
    ingredient_slug: str
    ingredient_name: str
    needed: Decimal
    available: Decimal
    unit: str


class AvailabilityResult(TypedDict):
    """Result of check_can_produce()."""
    can_produce: bool
    missing: List[MissingIngredient]


class ConsumptionRecord(TypedDict):
    """Structure for ingredient consumption ledger entry."""
    ingredient_slug: str
    quantity_consumed: Decimal
    unit: str
    total_cost: Decimal


class ProductionResult(TypedDict):
    """Result of record_batch_production()."""
    production_run_id: int
    recipe_id: int
    finished_unit_id: int
    num_batches: int
    expected_yield: int
    actual_yield: int
    total_ingredient_cost: Decimal
    per_unit_cost: Decimal
    consumptions: List[ConsumptionRecord]


# ============================================================================
# Service Interface
# ============================================================================

def check_can_produce(
    recipe_id: int,
    num_batches: int,
    *,
    session=None
) -> AvailabilityResult:
    """
    Check if sufficient inventory exists to produce the specified batches.

    Uses dry_run mode of consume_fifo to check availability without mutation.
    Supports nested recipes via get_aggregated_ingredients().

    Args:
        recipe_id: Recipe to produce
        num_batches: Number of batches to produce
        session: Optional database session (creates new if not provided)

    Returns:
        AvailabilityResult with can_produce=True if all ingredients available,
        or can_produce=False with list of missing ingredients.

    Raises:
        RecipeNotFoundError: If recipe_id doesn't exist
        DatabaseError: If database operation fails
    """
    ...


def record_batch_production(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    *,
    produced_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    session=None
) -> ProductionResult:
    """
    Record batch production with FIFO ingredient consumption.

    This is an atomic operation that:
    1. Validates recipe and finished_unit exist and are linked
    2. Gets aggregated ingredients (handles nested recipes)
    3. Consumes ingredients via FIFO
    4. Increments FinishedUnit.inventory_count by actual_yield
    5. Creates ProductionRun and ProductionConsumption records

    Args:
        recipe_id: Recipe that was produced
        finished_unit_id: FinishedUnit being created (must belong to recipe)
        num_batches: Number of recipe batches made
        actual_yield: Actual quantity produced
        produced_at: When production occurred (defaults to now)
        notes: Optional production notes
        session: Optional database session (creates new if not provided)

    Returns:
        ProductionResult with production run details and consumption ledger

    Raises:
        RecipeNotFoundError: If recipe_id doesn't exist
        FinishedUnitNotFoundError: If finished_unit_id doesn't exist
        FinishedUnitRecipeMismatchError: If finished_unit doesn't belong to recipe
        InsufficientInventoryError: If ingredients not available
        DatabaseError: If database operation fails

    Transaction:
        All operations occur within a single transaction.
        Rollback on any failure - no partial consumption.
    """
    ...


def get_production_history(
    *,
    recipe_id: Optional[int] = None,
    finished_unit_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    session=None
) -> List[Dict[str, Any]]:
    """
    Query production run history with optional filters.

    Args:
        recipe_id: Filter by recipe
        finished_unit_id: Filter by finished unit
        start_date: Filter by produced_at >= start_date
        end_date: Filter by produced_at <= end_date
        limit: Maximum results to return
        offset: Pagination offset
        session: Optional database session

    Returns:
        List of ProductionRun records with consumption details
    """
    ...


def get_production_run(
    production_run_id: int,
    *,
    include_consumptions: bool = True,
    session=None
) -> Dict[str, Any]:
    """
    Get a single production run by ID.

    Args:
        production_run_id: Production run to retrieve
        include_consumptions: Include consumption ledger details
        session: Optional database session

    Returns:
        ProductionRun record with optional consumption details

    Raises:
        ProductionRunNotFoundError: If production_run_id doesn't exist
    """
    ...
