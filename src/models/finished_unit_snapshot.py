"""
FinishedUnitSnapshot model for immutable capture of FinishedUnit definitions.

Follows RecipeSnapshot pattern: JSON Text column stores denormalized definition data,
dual context FKs support both planning and assembly use cases.

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


class FinishedUnitSnapshot(BaseModel):
    """
    Immutable snapshot of FinishedUnit definition at planning/assembly time.

    FinishedUnitSnapshots capture the complete FinishedUnit state (metadata and
    recipe reference) at the moment a planning snapshot or assembly run is created.
    This ensures historical records remain accurate even when definitions change.

    Attributes:
        finished_unit_id: FK to the source FinishedUnit (RESTRICT on delete)
        planning_snapshot_id: FK to PlanningSnapshot context (CASCADE on delete)
        assembly_run_id: FK to AssemblyRun context (CASCADE on delete)
        snapshot_date: When the snapshot was captured
        definition_data: JSON string with FinishedUnit definition at snapshot time
        is_backfilled: True if snapshot was created during migration (approximated)

    Note:
        - ON DELETE RESTRICT: Cannot delete a FinishedUnit that has snapshots
        - Exactly one context FK should be set (planning_snapshot_id or assembly_run_id)
        - JSON column uses Text type for SQLite compatibility
    """

    __tablename__ = "finished_unit_snapshots"

    # Source reference (RESTRICT: can't delete catalog item with snapshots)
    finished_unit_id = Column(
        Integer,
        ForeignKey("finished_units.id", ondelete="RESTRICT"),
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

    # Denormalized definition data (JSON)
    definition_data = Column(Text, nullable=False)

    # Relationships
    finished_unit = relationship("FinishedUnit")
    planning_snapshot = relationship(
        "PlanningSnapshot",
        back_populates="finished_unit_snapshots",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_fu_snapshot_unit", "finished_unit_id"),
        Index("idx_fu_snapshot_planning", "planning_snapshot_id"),
        Index("idx_fu_snapshot_assembly", "assembly_run_id"),
        Index("idx_fu_snapshot_date", "snapshot_date"),
    )

    def get_definition_data(self) -> dict:
        """
        Parse and return the definition data from JSON.

        Returns:
            Dictionary containing FinishedUnit definition at snapshot time.
            Empty dict if definition_data is None or invalid JSON.
        """
        if not self.definition_data:
            return {}
        try:
            return json.loads(self.definition_data)
        except json.JSONDecodeError:
            return {}

    def __repr__(self) -> str:
        """String representation of finished unit snapshot."""
        return (
            f"FinishedUnitSnapshot(id={self.id}, "
            f"finished_unit_id={self.finished_unit_id})"
        )
