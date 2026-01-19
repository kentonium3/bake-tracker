"""
ProductionRecord model for tracking recipe production.

This module contains the ProductionRecord model which represents
batches of a recipe produced for an event, with actual FIFO cost
captured at production time.
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
from src.utils.datetime_utils import utc_now


class ProductionRecord(BaseModel):
    """
    ProductionRecord model for tracking recipe production.

    Represents batches of a recipe produced for an event,
    with actual FIFO cost captured at production time.

    Attributes:
        event_id: Foreign key to Event being produced for
        recipe_id: Foreign key to Recipe that was produced
        batches: Number of batches produced (must be > 0)
        actual_cost: FIFO cost at time of production (snapshot)
        produced_at: Timestamp when production was recorded
        notes: Optional production notes
    """

    __tablename__ = "production_records"

    # Foreign keys
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)

    # Production data
    batches = Column(Integer, nullable=False)
    actual_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    produced_at = Column(DateTime, nullable=False, default=utc_now)
    notes = Column(Text, nullable=True)

    # Relationships
    event = relationship("Event", back_populates="production_records")
    recipe = relationship("Recipe")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_production_event_recipe", "event_id", "recipe_id"),
        Index("idx_production_event", "event_id"),
        Index("idx_production_recipe", "recipe_id"),
        Index("idx_production_produced_at", "produced_at"),
        CheckConstraint("batches > 0", name="ck_production_batches_positive"),
        CheckConstraint("actual_cost >= 0", name="ck_production_cost_non_negative"),
    )

    def __repr__(self) -> str:
        """String representation of production record."""
        return (
            f"ProductionRecord(id={self.id}, event_id={self.event_id}, "
            f"recipe_id={self.recipe_id}, batches={self.batches})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert production record to dictionary.

        Args:
            include_relationships: If True, include recipe details

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Format produced_at as ISO string
        if self.produced_at:
            result["produced_at"] = self.produced_at.isoformat()

        # Convert actual_cost to float for JSON compatibility
        if self.actual_cost is not None:
            result["actual_cost"] = float(self.actual_cost)

        if include_relationships and self.recipe:
            result["recipe_name"] = self.recipe.name

        return result
