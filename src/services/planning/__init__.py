"""
Planning services module for production planning (Feature 039).

This module provides services for:
- Batch calculation with mandatory round-up
- Waste percentage calculation
- Bundle explosion to unit quantities
- Recipe aggregation from FinishedUnits

Usage:
    from src.services.planning import (
        calculate_batches,
        calculate_waste,
        explode_bundle_requirements,
        aggregate_by_recipe,
        RecipeBatchResult,
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

__all__ = [
    "calculate_batches",
    "calculate_waste",
    "create_batch_result",
    "explode_bundle_requirements",
    "aggregate_by_recipe",
    "calculate_event_batch_requirements",
    "RecipeBatchResult",
]
