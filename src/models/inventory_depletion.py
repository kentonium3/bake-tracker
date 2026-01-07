"""
InventoryDepletion model for tracking inventory reductions.

This module contains the InventoryDepletion model which provides an
immutable audit trail for all inventory depletions (automatic and manual).
Each record tracks what was depleted, how much, why, and by whom.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Index,
    Numeric,
    DateTime,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class InventoryDepletion(BaseModel):
    """
    InventoryDepletion model for immutable depletion audit trail.

    Records every inventory reduction with reason, quantity, cost, and
    user identifier. Supports both automatic depletions (production,
    assembly) and manual adjustments (spoilage, gifts, corrections).

    Attributes:
        uuid: Unique identifier for distributed scenarios
        inventory_item_id: FK to InventoryItem being depleted
        quantity_depleted: Amount reduced (positive number)
        depletion_reason: Enum value (spoilage, gift, correction, etc.)
        depletion_date: When depletion occurred
        notes: Optional user explanation (required for OTHER reason)
        cost: Calculated cost impact (quantity * unit_cost)
        created_by: User identifier for audit
        created_at: Record creation timestamp

    Relationships:
        inventory_item: The InventoryItem that was depleted

    Note:
        Records are immutable after creation - no updates or deletes
        allowed to maintain audit integrity.
    """

    __tablename__ = "inventory_depletions"

    # UUID for future distributed scenarios (Constitution Principle III)
    uuid = Column(
        String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    # Foreign key to InventoryItem
    inventory_item_id = Column(
        Integer,
        ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Depletion data
    quantity_depleted = Column(Numeric(10, 3), nullable=False)
    depletion_reason = Column(String(50), nullable=False)
    depletion_date = Column(DateTime, nullable=False, default=datetime.now)
    notes = Column(Text, nullable=True)
    cost = Column(Numeric(10, 4), nullable=False)

    # Audit fields
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    # Relationships
    inventory_item = relationship("InventoryItem", back_populates="depletions")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_depletion_inventory_item", "inventory_item_id"),
        Index("idx_depletion_reason", "depletion_reason"),
        Index("idx_depletion_date", "depletion_date"),
        CheckConstraint(
            "quantity_depleted > 0",
            name="ck_depletion_quantity_positive",
        ),
    )

    def __repr__(self) -> str:
        """String representation of inventory depletion."""
        return (
            f"InventoryDepletion(id={self.id}, "
            f"inventory_item_id={self.inventory_item_id}, "
            f"quantity={self.quantity_depleted}, "
            f"reason='{self.depletion_reason}')"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert inventory depletion to dictionary.

        Args:
            include_relationships: If True, include inventory item details

        Returns:
            Dictionary representation with formatted fields
        """
        result = super().to_dict(include_relationships)

        # Convert Decimals to strings for JSON compatibility
        if self.quantity_depleted is not None:
            result["quantity_depleted"] = str(self.quantity_depleted)
        if self.cost is not None:
            result["cost"] = str(self.cost)

        return result
