"""
Planning services module for production planning (Feature 039).

This module provides services for:
- Batch calculation with mandatory round-up
- Waste percentage calculation
- Bundle explosion to unit quantities
- Recipe aggregation from FinishedUnits
- Shopping list generation with inventory comparison
- Shopping completion status tracking
- Progress tracking for production and assembly
- Feasibility checking for production and assembly

Usage:
    from src.services.planning import (
        calculate_batches,
        calculate_waste,
        explode_bundle_requirements,
        aggregate_by_recipe,
        RecipeBatchResult,
        get_shopping_list,
        ShoppingListItem,
        get_production_progress,
        get_assembly_progress,
        get_overall_progress,
        ProductionProgress,
        AssemblyProgress,
        check_production_feasibility,
        check_assembly_feasibility,
        FeasibilityStatus,
        FeasibilityResult,
    )
"""

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
    get_shopping_list,
    get_items_to_buy,
    get_shopping_summary,
    mark_shopping_complete,
    unmark_shopping_complete,
    is_shopping_complete,
    ShoppingListItem,
)

from .progress import (
    get_production_progress,
    get_assembly_progress,
    get_overall_progress,
    ProductionProgress,
    AssemblyProgress,
)

from .feasibility import (
    check_production_feasibility,
    check_assembly_feasibility,
    check_single_assembly_feasibility,
    FeasibilityStatus,
    FeasibilityResult,
)

__all__ = [
    # Batch calculation
    "calculate_batches",
    "calculate_waste",
    "create_batch_result",
    "explode_bundle_requirements",
    "aggregate_by_recipe",
    "calculate_event_batch_requirements",
    "RecipeBatchResult",
    # Shopping list
    "calculate_purchase_gap",
    "get_shopping_list",
    "get_items_to_buy",
    "get_shopping_summary",
    "mark_shopping_complete",
    "unmark_shopping_complete",
    "is_shopping_complete",
    "ShoppingListItem",
    # Progress tracking
    "get_production_progress",
    "get_assembly_progress",
    "get_overall_progress",
    "ProductionProgress",
    "AssemblyProgress",
    # Feasibility checking
    "check_production_feasibility",
    "check_assembly_feasibility",
    "check_single_assembly_feasibility",
    "FeasibilityStatus",
    "FeasibilityResult",
]
