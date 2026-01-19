"""
AssemblyPackagingConsumption model for tracking packaging material consumption during assembly.

This module contains the AssemblyPackagingConsumption model which records
packaging materials consumed from inventory during an assembly run,
tracking FIFO consumption and costs.
"""

from decimal import Decimal

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Index,
    Numeric,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class AssemblyPackagingConsumption(BaseModel):
    """
    AssemblyPackagingConsumption model for packaging consumption ledger.

    Records the packaging materials consumed from inventory during an
    assembly run with their quantities and FIFO costs. This provides
    an immutable audit trail of packaging consumption.

    Note: quantity_consumed is Numeric(10,3) because packaging materials
    can be consumed in fractional amounts (e.g., 0.5 meters of ribbon).

    Attributes:
        assembly_run_id: Foreign key to parent AssemblyRun
        product_id: Foreign key to Product (packaging product)
        quantity_consumed: Amount consumed (can be fractional)
        unit: Unit of measure for the quantity
        total_cost: FIFO cost of this packaging consumption
    """

    __tablename__ = "assembly_packaging_consumptions"

    # Foreign keys
    assembly_run_id = Column(
        Integer,
        ForeignKey("assembly_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Consumption data - NUMERIC for fractional packaging quantities
    quantity_consumed = Column(Numeric(10, 3), nullable=False)
    unit = Column(String(50), nullable=False)
    total_cost = Column(Numeric(10, 4), nullable=False)

    # Relationships
    assembly_run = relationship("AssemblyRun", back_populates="packaging_consumptions")
    product = relationship("Product")

    # Constraints and indexes
    __table_args__ = (
        # Indexes
        Index("idx_asm_pkg_consumption_run", "assembly_run_id"),
        Index("idx_asm_pkg_consumption_product", "product_id"),
        # Constraints
        CheckConstraint("quantity_consumed > 0", name="ck_asm_pkg_consumption_quantity_positive"),
        CheckConstraint("total_cost >= 0", name="ck_asm_pkg_consumption_total_cost_non_negative"),
    )

    def __repr__(self) -> str:
        """String representation of assembly packaging consumption."""
        return (
            f"AssemblyPackagingConsumption(id={self.id}, "
            f"assembly_run_id={self.assembly_run_id}, "
            f"product_id={self.product_id}, "
            f"quantity={self.quantity_consumed} {self.unit})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert assembly packaging consumption to dictionary.

        Args:
            include_relationships: If True, include assembly run and product details

        Returns:
            Dictionary representation with formatted fields
        """
        result = super().to_dict(include_relationships)

        # Convert Decimals to strings for JSON compatibility (preserving precision)
        if self.quantity_consumed is not None:
            result["quantity_consumed"] = str(self.quantity_consumed)
        if self.total_cost is not None:
            result["total_cost"] = str(self.total_cost)

        # Add convenience fields when including relationships
        if include_relationships:
            if self.product:
                result["product_name"] = self.product.display_name

        return result
