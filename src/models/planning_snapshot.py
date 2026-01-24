"""
PlanningSnapshot model for grouping snapshots by planning session.

This is a STUB model created in WP02 to satisfy FK constraints.
The full model with relationships will be implemented in WP04.

Feature 064: FinishedGoods Snapshot Architecture
"""

from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class PlanningSnapshot(BaseModel):
    """
    Container record linking an optional event to all snapshots created during
    plan finalization.

    Note: This is a stub model. Full implementation with complete relationships
    will be added in WP04.

    Attributes:
        event_id: FK to Event (optional, SET NULL on delete)
        created_at: When the planning snapshot was created
        notes: Optional notes
    """

    __tablename__ = "planning_snapshots"

    # Optional event linkage (SET NULL: event deletion preserves snapshot)
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Metadata
    created_at = Column(DateTime, nullable=False, default=utc_now)
    notes = Column(Text, nullable=True)

    # Relationships - to be completed in WP04
    event = relationship("Event")

    # Stub relationship placeholders for WP01-03 snapshot models
    # These will be properly configured with back_populates in WP04
    material_unit_snapshots = relationship(
        "MaterialUnitSnapshot",
        back_populates="planning_snapshot",
    )

    # Indexes
    __table_args__ = (
        Index("idx_planning_snapshot_event", "event_id"),
        Index("idx_planning_snapshot_created", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation of planning snapshot."""
        return f"PlanningSnapshot(id={self.id}, event_id={self.event_id})"
