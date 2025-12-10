"""
AssemblyFinishedUnitConsumption model for tracking FinishedUnit consumption during assembly.

This module contains the AssemblyFinishedUnitConsumption model which records
which FinishedUnits were consumed during an assembly run and at what cost.
"""

from decimal import Decimal

from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Index,
    Numeric,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class AssemblyFinishedUnitConsumption(BaseModel):
    """
    AssemblyFinishedUnitConsumption model for FinishedUnit consumption ledger.

    Records the FinishedUnits consumed during an assembly run with their
    quantities and costs. This provides an immutable audit trail
    of what was consumed at what price.

    Note: quantity_consumed is Integer because FinishedUnits are discrete
    whole items (cookies, truffles, etc.) that cannot be fractionally consumed.

    Attributes:
        assembly_run_id: Foreign key to parent AssemblyRun
        finished_unit_id: Foreign key to FinishedUnit that was consumed
        quantity_consumed: Number of units consumed (whole units only)
        unit_cost_at_consumption: Unit cost at time of consumption (snapshot)
        total_cost: Total cost of this consumption (qty * unit_cost)
    """

    __tablename__ = "assembly_finished_unit_consumptions"

    # Foreign keys
    assembly_run_id = Column(
        Integer,
        ForeignKey("assembly_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    finished_unit_id = Column(
        Integer,
        ForeignKey("finished_units.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Consumption data - INTEGER for whole units
    quantity_consumed = Column(Integer, nullable=False)
    unit_cost_at_consumption = Column(Numeric(10, 4), nullable=False)
    total_cost = Column(Numeric(10, 4), nullable=False)

    # Relationships
    assembly_run = relationship(
        "AssemblyRun", back_populates="finished_unit_consumptions"
    )
    finished_unit = relationship("FinishedUnit")

    # Constraints and indexes
    __table_args__ = (
        # Indexes
        Index("idx_asm_fu_consumption_run", "assembly_run_id"),
        Index("idx_asm_fu_consumption_unit", "finished_unit_id"),
        # Constraints
        CheckConstraint(
            "quantity_consumed > 0", name="ck_asm_fu_consumption_quantity_positive"
        ),
        CheckConstraint(
            "unit_cost_at_consumption >= 0",
            name="ck_asm_fu_consumption_unit_cost_non_negative",
        ),
        CheckConstraint(
            "total_cost >= 0", name="ck_asm_fu_consumption_total_cost_non_negative"
        ),
    )

    def __repr__(self) -> str:
        """String representation of assembly finished unit consumption."""
        return (
            f"AssemblyFinishedUnitConsumption(id={self.id}, "
            f"assembly_run_id={self.assembly_run_id}, "
            f"finished_unit_id={self.finished_unit_id}, "
            f"quantity={self.quantity_consumed})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert assembly finished unit consumption to dictionary.

        Args:
            include_relationships: If True, include assembly run and finished unit details

        Returns:
            Dictionary representation with formatted fields
        """
        result = super().to_dict(include_relationships)

        # Convert Decimals to strings for JSON compatibility (preserving precision)
        if self.unit_cost_at_consumption is not None:
            result["unit_cost_at_consumption"] = str(self.unit_cost_at_consumption)
        if self.total_cost is not None:
            result["total_cost"] = str(self.total_cost)

        # Add convenience fields when including relationships
        if include_relationships:
            if self.finished_unit:
                result["finished_unit_name"] = self.finished_unit.display_name

        return result
