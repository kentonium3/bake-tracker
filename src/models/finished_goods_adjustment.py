"""
FinishedGoodsAdjustment model for tracking inventory changes.

This model provides an audit trail for all inventory changes to finished units
and finished goods. Every adjustment to inventory_count creates a corresponding
record for traceability and reporting.

Feature: F061 - Finished Goods Inventory Service
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class FinishedGoodsAdjustment(BaseModel):
    """
    Audit record for finished goods inventory adjustments.

    Every change to inventory_count on FinishedUnit or FinishedGood
    creates a corresponding adjustment record for traceability.

    Supports polymorphic tracking - exactly one of finished_unit_id
    or finished_good_id must be set (enforced by CHECK constraint).

    Attributes:
        finished_unit_id: FK to FinishedUnit (XOR with finished_good_id)
        finished_good_id: FK to FinishedGood (XOR with finished_unit_id)
        quantity_change: Positive (add) or negative (consume) adjustment
        previous_count: Inventory count before adjustment
        new_count: Inventory count after adjustment
        reason: Category of adjustment (production, assembly, etc.)
        notes: Optional context for the adjustment
        adjusted_at: Timestamp when adjustment was made
    """

    __tablename__ = "finished_goods_adjustments"

    # Polymorphic target (XOR - exactly one must be set)
    finished_unit_id = Column(
        Integer,
        ForeignKey("finished_units.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    finished_good_id = Column(
        Integer,
        ForeignKey("finished_goods.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Adjustment details
    quantity_change = Column(Integer, nullable=False)
    previous_count = Column(Integer, nullable=False)
    new_count = Column(Integer, nullable=False)

    # Tracking
    reason = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    adjusted_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    finished_unit = relationship(
        "FinishedUnit",
        back_populates="inventory_adjustments",
        lazy="joined",
    )
    finished_good = relationship(
        "FinishedGood",
        back_populates="inventory_adjustments",
        lazy="joined",
    )

    __table_args__ = (
        # XOR constraint: exactly one target must be set
        CheckConstraint(
            "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL) OR "
            "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL)",
            name="ck_adjustment_target_xor",
        ),
        # Validate new_count matches calculation
        CheckConstraint(
            "new_count = previous_count + quantity_change",
            name="ck_adjustment_count_consistency",
        ),
        # Non-negative result
        CheckConstraint(
            "new_count >= 0",
            name="ck_adjustment_new_count_non_negative",
        ),
        # Index for chronological queries
        Index("idx_adjustment_adjusted_at", "adjusted_at"),
    )

    def __repr__(self) -> str:
        """String representation of adjustment."""
        return (
            f"FinishedGoodsAdjustment(id={self.id}, "
            f"item_type='{self.item_type}', "
            f"change={self.quantity_change:+d})"
        )

    @property
    def item_type(self) -> str:
        """Return 'finished_unit' or 'finished_good' based on which FK is set."""
        if self.finished_unit_id is not None:
            return "finished_unit"
        return "finished_good"

    @property
    def item_name(self) -> str:
        """Return display name of the adjusted item."""
        if self.finished_unit:
            return self.finished_unit.display_name
        if self.finished_good:
            return self.finished_good.display_name
        return "Unknown"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "uuid": str(self.uuid) if self.uuid else None,
            "item_type": self.item_type,
            "finished_unit_id": self.finished_unit_id,
            "finished_good_id": self.finished_good_id,
            "item_name": self.item_name,
            "quantity_change": self.quantity_change,
            "previous_count": self.previous_count,
            "new_count": self.new_count,
            "reason": self.reason,
            "notes": self.notes,
            "adjusted_at": self.adjusted_at.isoformat() if self.adjusted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
