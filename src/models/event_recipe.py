"""
EventRecipe model for event-recipe planning associations.

Many-to-many junction table linking events to selected recipes.
Feature 068: Event Management & Planning Data Model
"""

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class EventRecipe(BaseModel):
    """
    Junction table linking events to selected recipes for planning.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        recipe_id: Foreign key to Recipe (RESTRICT delete)
        created_at: When recipe was added to event
    """

    __tablename__ = "event_recipes"

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

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    event = relationship("Event", back_populates="event_recipes")
    recipe = relationship("Recipe")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("event_id", "recipe_id", name="uq_event_recipe"),
        Index("idx_event_recipe_event", "event_id"),
        Index("idx_event_recipe_recipe", "recipe_id"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"EventRecipe(event_id={self.event_id}, recipe_id={self.recipe_id})"
