"""
Service Contract: Manual Inventory Adjustment

This contract defines the interface for the manual_adjustment() function
to be added to inventory_item_service.py.

Location: src/services/inventory_item_service.py
"""

from decimal import Decimal
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

# Import paths (relative to src/)
from models.inventory_item import InventoryItem
from models.inventory_depletion import InventoryDepletion  # NEW MODEL
from models.enums import DepletionReason  # NEW ENUM


def manual_adjustment(
    inventory_item_id: int,
    quantity_to_deplete: Decimal,
    reason: DepletionReason,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> InventoryDepletion:
    """
    Manually adjust inventory by recording a depletion.

    Creates an immutable InventoryDepletion audit record and updates
    the InventoryItem quantity. Supports spoilage, gifts, corrections,
    ad hoc usage, and other manual adjustments.

    Args:
        inventory_item_id: ID of the InventoryItem to adjust
        quantity_to_deplete: Amount to reduce (must be positive, <= current quantity)
        reason: DepletionReason enum value (SPOILAGE, GIFT, CORRECTION, AD_HOC_USAGE, OTHER)
        notes: Optional explanation (REQUIRED when reason is OTHER)
        session: Optional SQLAlchemy session for transaction composability.
                 If None, function creates its own session_scope().

    Returns:
        InventoryDepletion: The created depletion record with:
            - quantity_depleted: The amount depleted
            - depletion_reason: The reason string
            - cost: Calculated cost impact (quantity * unit_cost)
            - depletion_date: Timestamp of adjustment
            - created_by: "desktop-user"

    Raises:
        InventoryItemNotFound: If inventory_item_id doesn't exist
        ValidationError: If:
            - quantity_to_deplete <= 0
            - quantity_to_deplete > current quantity
            - reason is OTHER and notes is empty/None

    Example:
        >>> from decimal import Decimal
        >>> from src.models.enums import DepletionReason
        >>> from src.services.inventory_item_service import manual_adjustment
        >>>
        >>> # Record spoilage
        >>> depletion = manual_adjustment(
        ...     inventory_item_id=123,
        ...     quantity_to_deplete=Decimal("5.0"),
        ...     reason=DepletionReason.SPOILAGE,
        ...     notes="Weevils discovered in bag"
        ... )
        >>> depletion.cost
        Decimal('3.20')  # 5 units * $0.64/unit

    Transaction Behavior:
        - If session is provided, caller owns the transaction (no commit here)
        - If session is None, creates session_scope() and commits on success
        - On error, transaction is rolled back

    Audit Trail:
        - InventoryDepletion record is immutable (never updated/deleted)
        - created_by set to "desktop-user" (hardcoded for single-user app)
        - depletion_date set to datetime.now() at creation

    Integration:
        - Updates InventoryItem.quantity atomically with depletion record
        - Cost calculated from InventoryItem.unit_cost at time of adjustment
    """
    pass  # Implementation in src/services/inventory_item_service.py


# =============================================================================
# Supporting Contracts
# =============================================================================


def get_depletion_history(
    inventory_item_id: int,
    session: Optional[Session] = None,
) -> list:
    """
    Get depletion history for an inventory item.

    Args:
        inventory_item_id: ID of the InventoryItem
        session: Optional SQLAlchemy session

    Returns:
        List[InventoryDepletion]: Depletion records ordered by depletion_date DESC
    """
    pass  # Implementation in src/services/inventory_item_service.py
