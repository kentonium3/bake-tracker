"""
AssemblyService Contract

Service interface for assembly tracking.
Handles FinishedUnit + Packaging -> FinishedGood assembly with inventory updates.
"""

from typing import Dict, Any, List, Optional, TypedDict, Literal
from decimal import Decimal
from datetime import datetime


class MissingComponent(TypedDict):
    """Structure for missing component details."""
    component_type: Literal["finished_unit", "packaging"]
    component_id: int
    component_name: str
    needed: Decimal
    available: Decimal
    unit: Optional[str]  # Only for packaging


class AssemblyAvailabilityResult(TypedDict):
    """Result of check_can_assemble()."""
    can_assemble: bool
    missing: List[MissingComponent]


class FinishedUnitConsumptionRecord(TypedDict):
    """Structure for FinishedUnit consumption ledger entry."""
    finished_unit_id: int
    finished_unit_name: str
    quantity_consumed: int
    unit_cost_at_consumption: Decimal
    total_cost: Decimal


class PackagingConsumptionRecord(TypedDict):
    """Structure for packaging consumption ledger entry."""
    product_id: int
    product_name: str
    quantity_consumed: Decimal
    unit: str
    total_cost: Decimal


class AssemblyResult(TypedDict):
    """Result of record_assembly()."""
    assembly_run_id: int
    finished_good_id: int
    quantity_assembled: int
    total_component_cost: Decimal
    per_unit_cost: Decimal
    finished_unit_consumptions: List[FinishedUnitConsumptionRecord]
    packaging_consumptions: List[PackagingConsumptionRecord]


# ============================================================================
# Service Interface
# ============================================================================

def check_can_assemble(
    finished_good_id: int,
    quantity: int,
    *,
    session=None
) -> AssemblyAvailabilityResult:
    """
    Check if sufficient components exist to assemble the specified quantity.

    Validates:
    - FinishedUnit components have sufficient inventory_count
    - Packaging products have sufficient inventory (via dry_run FIFO check)

    Args:
        finished_good_id: FinishedGood to assemble
        quantity: Number of FinishedGoods to assemble
        session: Optional database session (creates new if not provided)

    Returns:
        AssemblyAvailabilityResult with can_assemble=True if all components available,
        or can_assemble=False with list of missing components.

    Raises:
        FinishedGoodNotFoundError: If finished_good_id doesn't exist
        DatabaseError: If database operation fails
    """
    ...


def record_assembly(
    finished_good_id: int,
    quantity: int,
    *,
    assembled_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    session=None
) -> AssemblyResult:
    """
    Record assembly with component consumption.

    This is an atomic operation that:
    1. Validates FinishedGood exists
    2. Gets Composition components (FinishedUnits and packaging)
    3. Decrements FinishedUnit.inventory_count for each component
    4. Consumes packaging via FIFO
    5. Increments FinishedGood.inventory_count by quantity
    6. Creates AssemblyRun and consumption records

    Args:
        finished_good_id: FinishedGood being assembled
        quantity: Number of FinishedGoods to create
        assembled_at: When assembly occurred (defaults to now)
        notes: Optional assembly notes
        session: Optional database session (creates new if not provided)

    Returns:
        AssemblyResult with assembly run details and consumption ledgers

    Raises:
        FinishedGoodNotFoundError: If finished_good_id doesn't exist
        InsufficientFinishedUnitError: If FinishedUnit inventory insufficient
        InsufficientPackagingError: If packaging inventory insufficient
        DatabaseError: If database operation fails

    Transaction:
        All operations occur within a single transaction.
        Rollback on any failure - no partial consumption.
    """
    ...


def get_assembly_history(
    *,
    finished_good_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    session=None
) -> List[Dict[str, Any]]:
    """
    Query assembly run history with optional filters.

    Args:
        finished_good_id: Filter by finished good
        start_date: Filter by assembled_at >= start_date
        end_date: Filter by assembled_at <= end_date
        limit: Maximum results to return
        offset: Pagination offset
        session: Optional database session

    Returns:
        List of AssemblyRun records with consumption details
    """
    ...


def get_assembly_run(
    assembly_run_id: int,
    *,
    include_consumptions: bool = True,
    session=None
) -> Dict[str, Any]:
    """
    Get a single assembly run by ID.

    Args:
        assembly_run_id: Assembly run to retrieve
        include_consumptions: Include consumption ledger details
        session: Optional database session

    Returns:
        AssemblyRun record with optional consumption details

    Raises:
        AssemblyRunNotFoundError: If assembly_run_id doesn't exist
    """
    ...
