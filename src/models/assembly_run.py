"""
AssemblyRun model for tracking assembly events.

This module contains the AssemblyRun model which represents
assembly events where FinishedUnits and packaging materials
are combined into FinishedGoods with cost tracking.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class AssemblyRun(BaseModel):
    """
    AssemblyRun model for tracking assembly events.

    Records when FinishedUnits and packaging materials are assembled
    into FinishedGoods. Tracks quantity assembled, component costs,
    and provides an audit trail through consumption ledger records.

    Attributes:
        finished_good_id: Foreign key to FinishedGood being assembled
        quantity_assembled: Number of FinishedGoods created (must be > 0)
        assembled_at: Timestamp when assembly occurred
        notes: Optional assembly notes
        total_component_cost: Total cost of components + packaging consumed
        per_unit_cost: Cost per assembled unit (total / quantity)
    """

    __tablename__ = "assembly_runs"

    # Foreign keys
    finished_good_id = Column(
        Integer, ForeignKey("finished_goods.id", ondelete="RESTRICT"), nullable=False
    )

    # Assembly data
    quantity_assembled = Column(Integer, nullable=False)
    assembled_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Cost data
    total_component_cost = Column(
        Numeric(10, 4), nullable=False, default=Decimal("0.0000")
    )
    per_unit_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))

    # Relationships
    finished_good = relationship("FinishedGood", back_populates="assembly_runs")
    finished_unit_consumptions = relationship(
        "AssemblyFinishedUnitConsumption",
        back_populates="assembly_run",
        cascade="all, delete-orphan",
    )
    packaging_consumptions = relationship(
        "AssemblyPackagingConsumption",
        back_populates="assembly_run",
        cascade="all, delete-orphan",
    )

    # Constraints and indexes
    __table_args__ = (
        # Indexes
        Index("idx_assembly_run_finished_good", "finished_good_id"),
        Index("idx_assembly_run_assembled_at", "assembled_at"),
        # Constraints
        CheckConstraint(
            "quantity_assembled > 0", name="ck_assembly_run_quantity_positive"
        ),
        CheckConstraint(
            "total_component_cost >= 0",
            name="ck_assembly_run_total_cost_non_negative",
        ),
        CheckConstraint(
            "per_unit_cost >= 0", name="ck_assembly_run_per_unit_cost_non_negative"
        ),
    )

    def __repr__(self) -> str:
        """String representation of assembly run."""
        return (
            f"AssemblyRun(id={self.id}, finished_good_id={self.finished_good_id}, "
            f"quantity_assembled={self.quantity_assembled})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert assembly run to dictionary.

        Args:
            include_relationships: If True, include consumption details

        Returns:
            Dictionary representation with formatted fields
        """
        result = super().to_dict(include_relationships)

        # Format assembled_at as ISO string
        if self.assembled_at:
            result["assembled_at"] = self.assembled_at.isoformat()

        # Convert Decimals to strings for JSON compatibility (preserving precision)
        if self.total_component_cost is not None:
            result["total_component_cost"] = str(self.total_component_cost)
        if self.per_unit_cost is not None:
            result["per_unit_cost"] = str(self.per_unit_cost)

        # Add convenience fields when including relationships
        if include_relationships:
            if self.finished_good:
                result["finished_good_name"] = self.finished_good.display_name

        return result
