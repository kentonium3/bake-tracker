"""
ProductionRun model for tracking batch production.

This module contains the ProductionRun model which represents
batch production events where a recipe is made, ingredients are
consumed via FIFO, and FinishedUnits are created with yield-based costing.

Feature 037: Added recipe_snapshot_id FK to link production runs to
immutable recipe snapshots for historical cost accuracy.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    Integer,
    String,
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


class ProductionRun(BaseModel):
    """
    ProductionRun model for tracking batch production events.

    Records when a recipe is produced, including how many batches were made,
    the expected vs actual yield, the ingredients consumed via FIFO, and
    the resulting cost data.

    Attributes:
        recipe_id: Foreign key to Recipe that was produced
        finished_unit_id: Foreign key to FinishedUnit being produced
        num_batches: Number of recipe batches made (must be > 0)
        expected_yield: Expected output quantity
        actual_yield: Actual output quantity (can be 0 if production failed)
        produced_at: Timestamp when production occurred
        notes: Optional production notes
        total_ingredient_cost: Total FIFO cost of ingredients consumed
        per_unit_cost: Cost per unit (total / actual_yield, 0 if yield is 0)
    """

    __tablename__ = "production_runs"

    # Foreign keys
    recipe_id = Column(
        Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False
    )
    finished_unit_id = Column(
        Integer, ForeignKey("finished_units.id", ondelete="RESTRICT"), nullable=False
    )
    # Feature 016: Optional event linkage for progress tracking
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # Feature 037: Link to immutable recipe snapshot for historical accuracy
    # Nullable initially for migration; after backfill, new runs require snapshot
    recipe_snapshot_id = Column(
        Integer,
        ForeignKey("recipe_snapshots.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # Production data
    num_batches = Column(Integer, nullable=False)
    expected_yield = Column(Integer, nullable=False)
    actual_yield = Column(Integer, nullable=False)
    produced_at = Column(DateTime, nullable=False, default=utc_now)
    notes = Column(Text, nullable=True)

    # Feature 025: Loss tracking fields
    production_status = Column(String(20), nullable=False, default="complete")
    loss_quantity = Column(Integer, nullable=False, default=0)

    # Cost data
    total_ingredient_cost = Column(
        Numeric(10, 4), nullable=False, default=Decimal("0.0000")
    )
    per_unit_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))

    # Relationships
    recipe = relationship("Recipe", back_populates="production_runs")
    finished_unit = relationship("FinishedUnit", back_populates="production_runs")
    consumptions = relationship(
        "ProductionConsumption",
        back_populates="production_run",
        cascade="all, delete-orphan",
    )
    # Feature 016: Event relationship
    event = relationship("Event", back_populates="production_runs")

    # Feature 037: Snapshot relationship (1:1)
    snapshot = relationship(
        "RecipeSnapshot",
        back_populates="production_run",
        uselist=False,
        foreign_keys="RecipeSnapshot.production_run_id",
    )

    # Feature 025: Loss records relationship
    # Note: Uses passive_deletes=True to let DB handle SET NULL on production_run_id
    # when ProductionRun is deleted, preserving loss records for audit trail (FR-017)
    losses = relationship(
        "ProductionLoss",
        back_populates="production_run",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    # Constraints and indexes
    __table_args__ = (
        # Indexes
        Index("idx_production_run_recipe", "recipe_id"),
        Index("idx_production_run_finished_unit", "finished_unit_id"),
        Index("idx_production_run_produced_at", "produced_at"),
        Index("idx_production_run_event", "event_id"),
        Index("idx_production_run_status", "production_status"),  # Feature 025
        Index("idx_production_run_snapshot", "recipe_snapshot_id"),  # Feature 037
        # Constraints
        CheckConstraint("num_batches > 0", name="ck_production_run_batches_positive"),
        CheckConstraint(
            "expected_yield >= 0", name="ck_production_run_expected_yield_non_negative"
        ),
        CheckConstraint(
            "actual_yield >= 0", name="ck_production_run_actual_yield_non_negative"
        ),
        CheckConstraint(
            "total_ingredient_cost >= 0",
            name="ck_production_run_total_cost_non_negative",
        ),
        CheckConstraint(
            "per_unit_cost >= 0", name="ck_production_run_per_unit_cost_non_negative"
        ),
        # Feature 025: Loss tracking constraints
        CheckConstraint(
            "loss_quantity >= 0", name="ck_production_run_loss_non_negative"
        ),
    )

    def __repr__(self) -> str:
        """String representation of production run."""
        return (
            f"ProductionRun(id={self.id}, recipe_id={self.recipe_id}, "
            f"num_batches={self.num_batches}, actual_yield={self.actual_yield})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert production run to dictionary.

        Args:
            include_relationships: If True, include recipe and consumption details

        Returns:
            Dictionary representation with formatted fields
        """
        result = super().to_dict(include_relationships)

        # Format produced_at as ISO string
        if self.produced_at:
            result["produced_at"] = self.produced_at.isoformat()

        # Convert Decimals to strings for JSON compatibility (preserving precision)
        if self.total_ingredient_cost is not None:
            result["total_ingredient_cost"] = str(self.total_ingredient_cost)
        if self.per_unit_cost is not None:
            result["per_unit_cost"] = str(self.per_unit_cost)

        # Feature 016: Always include event_id
        result["event_id"] = self.event_id

        # Feature 025: Always include loss tracking fields
        result["production_status"] = self.production_status
        result["loss_quantity"] = self.loss_quantity

        # Add convenience fields when including relationships
        if include_relationships:
            if self.recipe:
                result["recipe_name"] = self.recipe.name
            if self.finished_unit:
                result["finished_unit_name"] = self.finished_unit.display_name
            # Feature 016: Include event_name
            result["event_name"] = self.event.name if self.event else None

        return result
