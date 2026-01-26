"""
PlanAmendment model for tracking amendments to locked plans.

Records changes made to locked plans during production.
Feature 068: Event Management & Planning Data Model
"""

from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class AmendmentType(str, Enum):
    """
    Types of amendments that can be made to locked plans.
    """

    DROP_FG = "drop_fg"  # Remove a finished good from plan
    ADD_FG = "add_fg"  # Add a finished good to plan
    MODIFY_BATCH = "modify_batch"  # Change batch count for a recipe


class PlanAmendment(BaseModel):
    """
    Tracks amendments to locked plans during production.

    When a plan is locked (plan_state = 'locked') but needs changes
    during production, amendments are recorded here to track what
    changed and why.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        amendment_type: Type of amendment (DROP_FG, ADD_FG, MODIFY_BATCH)
        amendment_data: JSON containing type-specific details
        reason: User-provided reason for the amendment
        created_at: When amendment was made
    """

    __tablename__ = "plan_amendments"

    # Foreign keys
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Amendment details
    amendment_type = Column(
        SQLEnum(AmendmentType),
        nullable=False,
        index=True,
    )
    amendment_data = Column(JSON, nullable=False)
    reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    event = relationship("Event", back_populates="plan_amendments")

    # Indexes
    __table_args__ = (
        Index("idx_plan_amendment_event", "event_id"),
        Index("idx_plan_amendment_type", "amendment_type"),
        Index("idx_plan_amendment_created", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"PlanAmendment(id={self.id}, event_id={self.event_id}, "
            f"amendment_type={self.amendment_type.value})"
        )
