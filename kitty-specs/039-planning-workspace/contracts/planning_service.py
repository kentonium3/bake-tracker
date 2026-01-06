"""
PlanningService Facade - Contract Definition

This file defines the public API contract for the PlanningService facade.
Implementation should match these signatures exactly.

Feature: F039 Planning Workspace
Date: 2026-01-05
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session


# =============================================================================
# Enums
# =============================================================================

class PlanPhase(Enum):
    """Phases in the planning workflow."""
    CALCULATE = "calculate"
    SHOP = "shop"
    PRODUCE = "produce"
    ASSEMBLE = "assemble"


class PhaseStatus(Enum):
    """Status of a planning phase."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class FeasibilityStatus(Enum):
    """Assembly feasibility status."""
    CAN_ASSEMBLE = "can_assemble"
    PARTIAL = "partial"  # Can assemble some but not all
    CANNOT_ASSEMBLE = "cannot_assemble"
    AWAITING_PRODUCTION = "awaiting_production"


# =============================================================================
# Data Transfer Objects
# =============================================================================

@dataclass
class RecipeBatchResult:
    """Result of batch calculation for a single recipe."""
    recipe_id: int
    recipe_name: str
    units_needed: int
    batches: int
    yield_per_batch: int
    total_yield: int
    waste_units: int
    waste_percent: float


@dataclass
class ShoppingListItem:
    """Single item in the shopping list."""
    ingredient_id: int
    ingredient_slug: str
    ingredient_name: str
    needed: Decimal
    in_stock: Decimal
    to_buy: Decimal
    unit: str
    is_sufficient: bool  # True if in_stock >= needed


@dataclass
class FeasibilityResult:
    """Result of assembly feasibility check."""
    finished_good_id: int
    finished_good_name: str
    target_quantity: int
    can_assemble: int  # How many CAN be assembled now
    status: FeasibilityStatus
    missing_components: List[Dict[str, Any]]  # What's short


@dataclass
class ProductionProgress:
    """Progress for a single recipe target."""
    recipe_id: int
    recipe_name: str
    target_batches: int
    completed_batches: int
    progress_percent: float
    is_complete: bool


@dataclass
class AssemblyProgress:
    """Progress for a single assembly target."""
    finished_good_id: int
    finished_good_name: str
    target_quantity: int
    assembled_quantity: int
    available_to_assemble: int  # How many more can be assembled
    progress_percent: float
    is_complete: bool


@dataclass
class PlanSummary:
    """Summary of the entire production plan."""
    event_id: int
    event_name: str
    calculated_at: Optional[datetime]
    is_stale: bool
    stale_reason: Optional[str]
    phase_statuses: Dict[PlanPhase, PhaseStatus]
    shopping_complete: bool
    production_progress_percent: float
    assembly_progress_percent: float
    overall_status: str  # "not_started", "in_progress", "complete"


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
    pass


# =============================================================================
# Service Contract
# =============================================================================

class PlanningServiceContract:
    """
    Contract for the PlanningService facade.

    All methods accept optional session parameter for transaction management.
    If session is None, method creates its own session scope.
    """

    # -------------------------------------------------------------------------
    # Plan Calculation
    # -------------------------------------------------------------------------

    def calculate_plan(
        self,
        event_id: int,
        *,
        force_recalculate: bool = False,
        session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Calculate production plan for an event.

        Args:
            event_id: Event to calculate plan for
            force_recalculate: If True, recalculate even if existing plan
            session: Optional database session

        Returns:
            Dict with:
                - plan_id: int (ProductionPlanSnapshot ID)
                - calculated_at: datetime
                - recipe_batches: List[RecipeBatchResult]
                - shopping_list: List[ShoppingListItem]
                - feasibility: List[FeasibilityResult]

        Raises:
            EventNotConfiguredError: If event.output_mode not set
            IncompleteRequirementsError: If no targets defined
        """
        raise NotImplementedError

    def get_plan_summary(
        self,
        event_id: int,
        *,
        session: Optional[Session] = None,
    ) -> PlanSummary:
        """
        Get summary of current plan status.

        Args:
            event_id: Event to get summary for
            session: Optional database session

        Returns:
            PlanSummary with overall status and phase statuses
        """
        raise NotImplementedError

    def check_staleness(
        self,
        event_id: int,
        *,
        session: Optional[Session] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if plan is stale.

        Args:
            event_id: Event to check
            session: Optional database session

        Returns:
            (is_stale: bool, reason: Optional[str])
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Batch Calculation
    # -------------------------------------------------------------------------

    def get_recipe_batches(
        self,
        event_id: int,
        *,
        session: Optional[Session] = None,
    ) -> List[RecipeBatchResult]:
        """
        Get calculated batch counts for all recipes in plan.

        Args:
            event_id: Event to get batches for
            session: Optional database session

        Returns:
            List of RecipeBatchResult with batch counts and waste analysis

        Raises:
            StalePlanError: If plan is stale (optional - may just return cached)
        """
        raise NotImplementedError

    def calculate_batches_for_quantity(
        self,
        recipe_id: int,
        units_needed: int,
        *,
        session: Optional[Session] = None,
    ) -> RecipeBatchResult:
        """
        Calculate batches needed for a specific quantity.

        Utility function for ad-hoc calculations.

        Args:
            recipe_id: Recipe to calculate for
            units_needed: How many units needed
            session: Optional database session

        Returns:
            RecipeBatchResult with calculation
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Shopping List
    # -------------------------------------------------------------------------

    def get_shopping_list(
        self,
        event_id: int,
        *,
        include_sufficient: bool = True,
        session: Optional[Session] = None,
    ) -> List[ShoppingListItem]:
        """
        Get shopping list with inventory comparison.

        Args:
            event_id: Event to get list for
            include_sufficient: If True, include items with sufficient stock
            session: Optional database session

        Returns:
            List of ShoppingListItem
        """
        raise NotImplementedError

    def mark_shopping_complete(
        self,
        event_id: int,
        *,
        session: Optional[Session] = None,
    ) -> None:
        """
        Mark shopping as complete for the event.

        Args:
            event_id: Event to mark
            session: Optional database session
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Feasibility
    # -------------------------------------------------------------------------

    def check_assembly_feasibility(
        self,
        event_id: int,
        *,
        session: Optional[Session] = None,
    ) -> List[FeasibilityResult]:
        """
        Check assembly feasibility for all targets.

        Args:
            event_id: Event to check
            session: Optional database session

        Returns:
            List of FeasibilityResult for each assembly target
        """
        raise NotImplementedError

    def check_production_feasibility(
        self,
        event_id: int,
        *,
        session: Optional[Session] = None,
    ) -> List[Dict[str, Any]]:
        """
        Check production feasibility (ingredient availability).

        Args:
            event_id: Event to check
            session: Optional database session

        Returns:
            List of dicts with recipe_id, can_produce, missing ingredients
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Progress Tracking
    # -------------------------------------------------------------------------

    def get_production_progress(
        self,
        event_id: int,
        *,
        session: Optional[Session] = None,
    ) -> List[ProductionProgress]:
        """
        Get production progress for all recipe targets.

        Args:
            event_id: Event to get progress for
            session: Optional database session

        Returns:
            List of ProductionProgress
        """
        raise NotImplementedError

    def get_assembly_progress(
        self,
        event_id: int,
        *,
        session: Optional[Session] = None,
    ) -> List[AssemblyProgress]:
        """
        Get assembly progress for all finished good targets.

        Args:
            event_id: Event to get progress for
            session: Optional database session

        Returns:
            List of AssemblyProgress
        """
        raise NotImplementedError

    def get_overall_progress(
        self,
        event_id: int,
        *,
        session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Get overall event progress summary.

        Args:
            event_id: Event to get progress for
            session: Optional database session

        Returns:
            Dict with production_percent, assembly_percent, overall_percent, status
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Assembly Checklist
    # -------------------------------------------------------------------------

    def get_assembly_checklist(
        self,
        event_id: int,
        *,
        session: Optional[Session] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get assembly checklist for the event.

        Args:
            event_id: Event to get checklist for
            session: Optional database session

        Returns:
            List of dicts with finished_good info, target, assembled, available
        """
        raise NotImplementedError

    def record_assembly_confirmation(
        self,
        event_id: int,
        finished_good_id: int,
        quantity: int,
        *,
        session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Record assembly confirmation (status tracking only, no inventory).

        Phase 2 does not consume inventory on assembly confirmation.

        Args:
            event_id: Event
            finished_good_id: What was assembled
            quantity: How many assembled
            session: Optional database session

        Returns:
            Dict with confirmation details
        """
        raise NotImplementedError
