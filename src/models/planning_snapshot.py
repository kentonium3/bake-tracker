"""
PlanningSnapshot model for grouping snapshots by planning session.

Container record that links an optional event to all snapshots created
during plan finalization. Enables atomic cleanup and event-scoped queries.

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

    Attributes:
        event_id: FK to Event (optional, SET NULL on delete)
        created_at: When the planning snapshot was created
        notes: Optional notes

    Relationships:
        event: Optional Event this snapshot is for
        finished_unit_snapshots: FinishedUnitSnapshot records (cascade delete)
        material_unit_snapshots: MaterialUnitSnapshot records (cascade delete)
        finished_good_snapshots: FinishedGoodSnapshot records (cascade delete)
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

    # Relationship to Event (bidirectional)
    event = relationship("Event", back_populates="planning_snapshots")

    # Relationships to snapshot types (one-to-many)
    # CASCADE: deleting PlanningSnapshot deletes all child snapshots
    finished_unit_snapshots = relationship(
        "FinishedUnitSnapshot",
        back_populates="planning_snapshot",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    material_unit_snapshots = relationship(
        "MaterialUnitSnapshot",
        back_populates="planning_snapshot",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    finished_good_snapshots = relationship(
        "FinishedGoodSnapshot",
        back_populates="planning_snapshot",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # Indexes
    __table_args__ = (
        Index("idx_planning_snapshot_event", "event_id"),
        Index("idx_planning_snapshot_created", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation of planning snapshot."""
        return f"PlanningSnapshot(id={self.id}, event_id={self.event_id})"
