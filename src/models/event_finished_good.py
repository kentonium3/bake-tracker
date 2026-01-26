"""
EventFinishedGood model for event FG planning associations.

Tracks finished good selections with quantities for planning.
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


class EventFinishedGood(BaseModel):
    """
    Tracks finished good selections with quantities for an event.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        finished_good_id: Foreign key to FinishedGood (RESTRICT delete)
        quantity: Number of units needed (must be positive)
        created_at: When FG was added
        updated_at: Last modification
    """

    __tablename__ = "event_finished_goods"

    # Foreign keys
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finished_good_id = Column(
        Integer,
        ForeignKey("finished_goods.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Quantity
    quantity = Column(Integer, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    event = relationship("Event", back_populates="event_finished_goods")
    finished_good = relationship("FinishedGood")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("event_id", "finished_good_id", name="uq_event_finished_good"),
        CheckConstraint("quantity > 0", name="ck_event_fg_quantity_positive"),
        Index("idx_event_fg_event", "event_id"),
        Index("idx_event_fg_fg", "finished_good_id"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"EventFinishedGood(event_id={self.event_id}, "
            f"finished_good_id={self.finished_good_id}, quantity={self.quantity})"
        )
