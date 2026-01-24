"""
MaterialUnitSnapshot model for immutable capture of MaterialUnit definitions.

Follows RecipeSnapshot pattern: JSON Text column stores denormalized definition data,
dual context FKs support both planning and assembly use cases.
"""

import json

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class MaterialUnitSnapshot(BaseModel):
    """Immutable snapshot of MaterialUnit definition data."""

    __tablename__ = "material_unit_snapshots"

    # Source reference (RESTRICT: can't delete catalog item with snapshots)
    material_unit_id = Column(
        Integer,
        ForeignKey("material_units.id", ondelete="RESTRICT"),
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
    material_unit = relationship("MaterialUnit")
    planning_snapshot = relationship(
        "PlanningSnapshot",
        back_populates="material_unit_snapshots",
    )

    __table_args__ = (
        Index("idx_mu_snapshot_unit", "material_unit_id"),
        Index("idx_mu_snapshot_planning", "planning_snapshot_id"),
        Index("idx_mu_snapshot_assembly", "assembly_run_id"),
        Index("idx_mu_snapshot_date", "snapshot_date"),
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
            f"MaterialUnitSnapshot(id={self.id}, material_unit_id={self.material_unit_id})"
        )
