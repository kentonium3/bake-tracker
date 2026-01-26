"""
BatchDecision model for storing user's batch choices.

Records the number of batches chosen for each recipe in an event plan.
Feature 068: Event Management & Planning Data Model
"""

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class BatchDecision(BaseModel):
    """
    Stores user's batch choice per recipe for an event.

    When planning, users decide how many batches of each recipe to make.
    This table records those decisions, optionally linked to a specific
    FinishedUnit for recipes with multiple yield types.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        recipe_id: Foreign key to Recipe (RESTRICT delete)
        batches: Number of batches to make (must be positive)
        finished_unit_id: Optional FK to FinishedUnit (for multi-yield recipes)
        created_at: When decision was made
        updated_at: Last modification
    """

    __tablename__ = "batch_decisions"

    # Foreign keys
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    finished_unit_id = Column(
        Integer,
        ForeignKey("finished_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Batch count
    batches = Column(Integer, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    event = relationship("Event", back_populates="batch_decisions")
    recipe = relationship("Recipe")
    finished_unit = relationship("FinishedUnit")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("event_id", "recipe_id", name="uq_batch_decision_event_recipe"),
        CheckConstraint("batches > 0", name="ck_batch_decision_batches_positive"),
        Index("idx_batch_decision_event", "event_id"),
        Index("idx_batch_decision_recipe", "recipe_id"),
        Index("idx_batch_decision_finished_unit", "finished_unit_id"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"BatchDecision(event_id={self.event_id}, "
            f"recipe_id={self.recipe_id}, batches={self.batches})"
        )
