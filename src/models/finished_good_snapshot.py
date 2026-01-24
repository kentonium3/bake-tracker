"""
FinishedGoodSnapshot model for immutable capture of FinishedGood definitions.

Includes full component hierarchy in definition_data JSON. Component snapshots
are created recursively and their IDs stored in the components array.

Feature 064: FinishedGoods Snapshot Architecture
"""

import json

from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class FinishedGoodSnapshot(BaseModel):
    """Immutable snapshot of FinishedGood definition data with component hierarchy."""

    __tablename__ = "finished_good_snapshots"

    # Source reference (RESTRICT: can't delete catalog item with snapshots)
    finished_good_id = Column(
        Integer,
        ForeignKey("finished_goods.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Context linkage (exactly one should be set at service layer)
    planning_snapshot_id = Column(
        Integer,
        ForeignKey("planning_snapshots.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    assembly_run_id = Column(
        Integer,
        ForeignKey("assembly_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Snapshot metadata
    snapshot_date = Column(DateTime, nullable=False, default=utc_now)
    is_backfilled = Column(Boolean, nullable=False, default=False)

    # Denormalized definition data (JSON) - includes components array
    definition_data = Column(Text, nullable=False)

    # Relationships
    finished_good = relationship("FinishedGood")
    planning_snapshot = relationship(
        "PlanningSnapshot",
        back_populates="finished_good_snapshots",
    )

    __table_args__ = (
        Index("idx_fg_snapshot_good", "finished_good_id"),
        Index("idx_fg_snapshot_planning", "planning_snapshot_id"),
        Index("idx_fg_snapshot_assembly", "assembly_run_id"),
        Index("idx_fg_snapshot_date", "snapshot_date"),
    )

    def get_definition_data(self) -> dict:
        """Parse and return definition_data JSON."""
        if not self.definition_data:
            return {}
        try:
            return json.loads(self.definition_data)
        except json.JSONDecodeError:
            return {}

    def __repr__(self) -> str:
        return (
            f"FinishedGoodSnapshot(id={self.id}, finished_good_id={self.finished_good_id})"
        )
