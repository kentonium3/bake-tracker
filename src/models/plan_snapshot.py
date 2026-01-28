"""
PlanSnapshot model for capturing plan state at production start.

Feature 078: Plan Snapshots & Amendments
"""

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class PlanSnapshot(BaseModel):
    """
    Captures complete plan state when production starts.

    Created automatically when start_production() transitions
    an event from LOCKED to IN_PRODUCTION state. Stores the
    original plan as JSON for later comparison.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        snapshot_data: JSON containing recipes, FGs, batch decisions
        created_at: When snapshot was created
    """

    __tablename__ = "plan_snapshots"

    # Foreign keys
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One snapshot per event
        index=True,
    )

    # Snapshot data
    snapshot_data = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    event = relationship("Event", back_populates="plan_snapshot")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_plan_snapshot_event", "event_id"),
        UniqueConstraint("event_id", name="uq_plan_snapshot_event"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"PlanSnapshot(id={self.id}, event_id={self.event_id})"
