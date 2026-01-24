"""
ProductionPlanSnapshot model - lightweight container for production plans.

This module contains the ProductionPlanSnapshot model which serves as a
container linking an event to its planning timestamp. Calculation results
are computed on-demand via get_plan_summary(), not cached in this model.

Feature: F039 Planning Workspace, refactored in F065
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class ProductionPlanSnapshot(BaseModel):
    """Lightweight container linking an event to its planning timestamp.

    References snapshots via EventProductionTarget.recipe_snapshot_id
    and EventAssemblyTarget.finished_good_snapshot_id.

    Calculation results are computed on-demand via get_plan_summary(),
    not cached in this model.

    Attributes:
        event_id: Foreign key to the Event this plan is for
        calculated_at: When this plan was created
        input_hash: Optional SHA256 hash of inputs for version tracking
        shopping_complete: Whether shopping has been marked complete
        shopping_completed_at: When shopping was marked complete
    """

    __tablename__ = "production_plan_snapshots"

    # Primary relationship
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Calculation metadata
    calculated_at = Column(DateTime, nullable=False, default=utc_now)

    # Input version tracking (optional)
    input_hash = Column(String(64), nullable=True)  # SHA256 of inputs

    # Shopping status
    shopping_complete = Column(Boolean, default=False, nullable=False)
    shopping_completed_at = Column(DateTime, nullable=True)

    # Relationships
    event = relationship("Event", back_populates="production_plan_snapshots")

    # Indexes
    __table_args__ = (
        Index("idx_pps_event", "event_id"),
        Index("idx_pps_calculated_at", "calculated_at"),
    )

    def __repr__(self) -> str:
        """String representation of production plan snapshot."""
        return (
            f"ProductionPlanSnapshot(id={self.id}, event_id={self.event_id}, "
            f"calculated_at={self.calculated_at})"
        )

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Args:
            include_relationships: If True, include event details

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Convert datetime fields to ISO format
        if self.calculated_at:
            result["calculated_at"] = self.calculated_at.isoformat()
        if self.shopping_completed_at:
            result["shopping_completed_at"] = self.shopping_completed_at.isoformat()

        if include_relationships:
            if self.event:
                result["event_name"] = self.event.name

        return result
