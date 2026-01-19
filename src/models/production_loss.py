"""
ProductionLoss model for tracking detailed production losses.

This module contains the ProductionLoss model which records detailed
information about items lost during production, including the reason
(category), quantity, cost snapshot, and optional notes.

Feature 025: Production Loss Tracking
"""

from decimal import Decimal

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    Index,
    Numeric,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class ProductionLoss(BaseModel):
    """
    ProductionLoss model for tracking detailed loss information.

    Records the specifics of items lost during a production run,
    including the loss category (burnt, broken, etc.), quantity,
    cost snapshot at production time, and optional notes.

    The production_run_id uses SET NULL on delete to preserve
    loss records for audit trail purposes even if the production
    run is deleted.

    Attributes:
        production_run_id: FK to ProductionRun (nullable for audit trail)
        finished_unit_id: FK to FinishedUnit being produced
        loss_category: Enum value from LossCategory (default: "other")
        loss_quantity: Number of units lost (must be > 0)
        per_unit_cost: Cost per unit snapshot at production time
        total_loss_cost: Calculated as loss_quantity * per_unit_cost
        notes: Optional details about the loss
    """

    __tablename__ = "production_losses"

    # Foreign keys
    production_run_id = Column(
        Integer,
        ForeignKey("production_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    finished_unit_id = Column(
        Integer,
        ForeignKey("finished_units.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Loss details
    loss_category = Column(String(20), nullable=False, default="other")
    loss_quantity = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)

    # Cost snapshot at production time
    per_unit_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    total_loss_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))

    # Relationships
    production_run = relationship("ProductionRun", back_populates="losses")
    finished_unit = relationship("FinishedUnit")

    # Constraints and indexes
    __table_args__ = (
        # Indexes
        Index("idx_production_loss_category", "loss_category"),
        Index("idx_production_loss_created", "created_at"),
        # Constraints
        CheckConstraint("loss_quantity > 0", name="ck_production_loss_quantity_positive"),
        CheckConstraint("per_unit_cost >= 0", name="ck_production_loss_per_unit_cost_non_negative"),
        CheckConstraint("total_loss_cost >= 0", name="ck_production_loss_total_cost_non_negative"),
    )

    def __repr__(self) -> str:
        """String representation of production loss."""
        return (
            f"ProductionLoss(id={self.id}, production_run_id={self.production_run_id}, "
            f"category={self.loss_category}, quantity={self.loss_quantity})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert production loss to dictionary.

        Args:
            include_relationships: If True, include related object details

        Returns:
            Dictionary representation with formatted fields
        """
        result = super().to_dict(include_relationships)

        # Convert Decimals to strings for JSON compatibility
        if self.per_unit_cost is not None:
            result["per_unit_cost"] = str(self.per_unit_cost)
        if self.total_loss_cost is not None:
            result["total_loss_cost"] = str(self.total_loss_cost)

        # Add convenience fields when including relationships
        if include_relationships:
            if self.finished_unit:
                result["finished_unit_name"] = self.finished_unit.display_name

        return result
