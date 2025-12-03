"""
Contract: PantryService consume_fifo() Dry Run Extension

This file defines the interface contract for the dry_run parameter
to be added to PantryService.consume_fifo(). This is NOT production
code - it defines the expected signature and behavior contract.

Feature: 005-recipe-fifo-cost
Date: 2025-12-02
"""

from decimal import Decimal
from typing import Any, Dict, List, Protocol, TypedDict
from datetime import date


class ConsumptionBreakdownItem(TypedDict):
    """Structure for each lot in the consumption breakdown."""

    pantry_item_id: int
    variant_id: int
    lot_date: date
    quantity_consumed: Decimal
    unit: str
    remaining_in_lot: Decimal
    unit_cost: Decimal  # NEW: Cost per unit for this lot


class ConsumeFifoResult(TypedDict):
    """Structure returned by consume_fifo()."""

    consumed: Decimal  # Amount consumed in recipe_unit
    breakdown: List[ConsumptionBreakdownItem]  # Per-lot details
    shortfall: Decimal  # Amount unavailable (0.0 if satisfied)
    satisfied: bool  # True if fully satisfied
    total_cost: Decimal  # NEW: Total cost of consumed amount (FIFO)


class PantryServiceDryRunProtocol(Protocol):
    """
    Protocol defining the extended consume_fifo() signature with dry_run.

    The existing consume_fifo() method will be modified to accept an
    optional dry_run parameter that enables read-only cost simulation.
    """

    def consume_fifo(
        self,
        ingredient_slug: str,
        quantity_needed: Decimal,
        dry_run: bool = False,  # NEW PARAMETER
    ) -> ConsumeFifoResult:
        """
        Consume (or simulate consuming) inventory using FIFO ordering.

        Processes pantry items in purchase_date order (oldest first),
        consuming the specified quantity and tracking what was used
        from each lot.

        Args:
            ingredient_slug: Slug identifier for the ingredient
            quantity_needed: Amount to consume in recipe units
            dry_run: If True, calculate costs without modifying database.
                    If False (default), actually consume inventory.

        Returns:
            ConsumeFifoResult dict containing:
            - consumed: Amount actually consumed (may be less than needed)
            - breakdown: List of per-lot consumption details with costs
            - shortfall: Amount that couldn't be satisfied from pantry
            - satisfied: True if quantity_needed was fully satisfied
            - total_cost: FIFO cost of the consumed portion

        Raises:
            IngredientNotFound: If ingredient_slug does not exist
            ValidationError: If unit conversion fails

        Behavior when dry_run=False (existing):
            - Updates pantry_item quantities in database
            - Commits changes within transaction
            - Empty lots preserved for audit trail

        Behavior when dry_run=True (NEW):
            - Calculates what WOULD be consumed
            - Returns cost breakdown without any database changes
            - Session is read-only (no flush/commit)
            - Useful for recipe costing calculations
        """
        ...
