"""
Enumerations for production and inventory tracking.

This module contains enums used across production-related models:
- ProductionStatus: Outcome classification for production runs
- LossCategory: Reason classification for production losses
- DepletionReason: Reason classification for inventory depletions
"""

from enum import Enum


class ProductionStatus(str, Enum):
    """
    Production run outcome status.

    Classifies the result of a production run based on whether
    the actual yield matched the expected yield.

    Values:
        COMPLETE: All expected units produced (loss_quantity = 0)
        PARTIAL_LOSS: Some units lost (0 < loss_quantity < expected_yield)
        TOTAL_LOSS: All units lost (loss_quantity = expected_yield, actual_yield = 0)
    """

    COMPLETE = "complete"
    PARTIAL_LOSS = "partial_loss"
    TOTAL_LOSS = "total_loss"


class LossCategory(str, Enum):
    """
    Categories for production losses.

    Classifies the reason why items were lost during production.
    Used for trend analysis and process improvement.

    Values:
        BURNT: Overcooked/burnt items
        BROKEN: Physical damage during handling
        CONTAMINATED: Contamination (hair, debris, etc.)
        DROPPED: Dropped on floor/ground
        WRONG_INGREDIENTS: Recipe error requiring discard
        OTHER: Catch-all category; use notes for specifics
    """

    BURNT = "burnt"
    BROKEN = "broken"
    CONTAMINATED = "contaminated"
    DROPPED = "dropped"
    WRONG_INGREDIENTS = "wrong_ingredients"
    OTHER = "other"


class DepletionReason(str, Enum):
    """
    Reasons for inventory depletion.

    Categorizes why inventory was reduced. Supports both automatic
    system-generated depletions and manual user-initiated adjustments.

    Automatic (system-generated):
        PRODUCTION: Recipe execution consumed ingredients
        ASSEMBLY: Bundle assembly consumed finished units (future)

    Manual (user-initiated):
        SPOILAGE: Ingredient went bad (mold, weevils, expiration)
        GIFT: Gave to friend/family
        CORRECTION: Physical count adjustment
        AD_HOC_USAGE: Personal/testing usage outside app
        OTHER: User-specified reason (requires notes)
    """

    # Automatic (system-generated)
    PRODUCTION = "production"
    ASSEMBLY = "assembly"

    # Manual (user-initiated)
    SPOILAGE = "spoilage"
    GIFT = "gift"
    CORRECTION = "correction"
    AD_HOC_USAGE = "ad_hoc_usage"
    OTHER = "other"
