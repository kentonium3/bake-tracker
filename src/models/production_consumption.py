"""
ProductionConsumption model for tracking ingredient consumption during production.

This module contains the ProductionConsumption model which represents
ingredient-level consumption ledger entries for production runs.
Each row records what ingredient was consumed, in what quantity, and at what cost.
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


class ProductionConsumption(BaseModel):
    """
    ProductionConsumption model for ingredient-level consumption ledger.

    Records the ingredients consumed during a production run with their
    quantities and FIFO costs. This provides an immutable audit trail
    of what was consumed at what price.

    Note: We store ingredient_slug as String rather than FK because:
    - Allows flexibility for ingredient renames
    - Consumption ledger is an immutable snapshot of point-in-time data
    - Preserves historical record even if ingredient is deleted

    Attributes:
        production_run_id: Foreign key to parent ProductionRun
        ingredient_slug: Slug of the ingredient that was consumed
        quantity_consumed: Amount consumed (in recipe units)
        unit: Unit of measure for the quantity
        total_cost: FIFO cost of this ingredient consumption
    """

    __tablename__ = "production_consumptions"

    # Foreign keys
    production_run_id = Column(
        Integer,
        ForeignKey("production_runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Consumption data (ingredient_slug is NOT a foreign key)
    ingredient_slug = Column(String(100), nullable=False)
    quantity_consumed = Column(Numeric(10, 3), nullable=False)
    unit = Column(String(50), nullable=False)
    total_cost = Column(Numeric(10, 4), nullable=False)

    # Relationships
    production_run = relationship(
        "ProductionRun", back_populates="consumptions"
    )

    # Constraints and indexes
    __table_args__ = (
        # Indexes
        Index("idx_prod_consumption_run", "production_run_id"),
        Index("idx_prod_consumption_ingredient", "ingredient_slug"),
        # Constraints
        CheckConstraint(
            "quantity_consumed > 0", name="ck_prod_consumption_quantity_positive"
        ),
        CheckConstraint(
            "total_cost >= 0", name="ck_prod_consumption_cost_non_negative"
        ),
    )

    def __repr__(self) -> str:
        """String representation of production consumption."""
        return (
            f"ProductionConsumption(id={self.id}, "
            f"production_run_id={self.production_run_id}, "
            f"ingredient_slug='{self.ingredient_slug}', "
            f"quantity={self.quantity_consumed} {self.unit})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert production consumption to dictionary.

        Args:
            include_relationships: If True, include production run details

        Returns:
            Dictionary representation with formatted fields
        """
        result = super().to_dict(include_relationships)

        # Convert Decimals to strings for JSON compatibility (preserving precision)
        if self.quantity_consumed is not None:
            result["quantity_consumed"] = str(self.quantity_consumed)
        if self.total_cost is not None:
            result["total_cost"] = str(self.total_cost)

        return result
