"""
Event models for tracking seasonal baking events.

This module contains:
- Event: Annual baking events (e.g., Christmas 2024)
- EventRecipientPackage: Junction table linking events, recipients, and packages
- EventProductionTarget: Production targets per event/recipe
- EventAssemblyTarget: Assembly targets per event/finished_good
- FulfillmentStatus: Enum for package fulfillment workflow
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .package_status import PackageStatus

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class FulfillmentStatus(str, Enum):
    """
    Fulfillment status for package assignments.

    Workflow is sequential: pending -> ready -> delivered
    """
    PENDING = "pending"
    READY = "ready"
    DELIVERED = "delivered"


class OutputMode(str, Enum):
    """
    Output mode for event production requirements.

    Determines how requirements are specified for production planning:
    - BULK_COUNT: Direct FinishedUnit quantities (e.g., "make 300 cookies")
    - BUNDLED: FinishedGood/bundle quantities (e.g., "make 50 gift bags")
    """
    BULK_COUNT = "bulk_count"
    BUNDLED = "bundled"


class Event(BaseModel):
    """
    Event model representing annual baking events.

    Events organize the annual cycle of baking, packaging, and gifting.
    Each event tracks which recipients receive which packages.

    Attributes:
        name: Event name (e.g., "Christmas 2024", "Teacher Gifts 2024")
        event_date: Date of the event
        year: Year for easy filtering and comparison
        notes: Additional notes about the event
    """

    __tablename__ = "events"

    # Basic information
    name = Column(String(200), nullable=False, index=True)
    event_date = Column(Date, nullable=False)
    year = Column(Integer, nullable=False, index=True)
    notes = Column(Text, nullable=True)

    # Planning configuration (Feature 039)
    output_mode = Column(SQLEnum(OutputMode), nullable=True, index=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=utc_now)
    last_modified = Column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    event_recipient_packages = relationship(
        "EventRecipientPackage", back_populates="event", cascade="all, delete-orphan", lazy="joined"
    )
    production_records = relationship(
        "ProductionRecord",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Feature 016: Event-centric production relationships
    production_runs = relationship(
        "ProductionRun",
        back_populates="event",
        lazy="selectin",
    )
    assembly_runs = relationship(
        "AssemblyRun",
        back_populates="event",
        lazy="selectin",
    )
    production_targets = relationship(
        "EventProductionTarget",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    assembly_targets = relationship(
        "EventAssemblyTarget",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Feature 039: Planning workspace relationships
    production_plan_snapshots = relationship(
        "ProductionPlanSnapshot",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index("idx_event_name", "name"),
        Index("idx_event_year", "year"),
        Index("idx_event_date", "event_date"),
    )

    def __repr__(self) -> str:
        """String representation of event."""
        return f"Event(id={self.id}, name='{self.name}', year={self.year})"

    def get_total_cost(self) -> Decimal:
        """
        Calculate total cost of all packages in this event.

        Cost chains through: Event -> ERP -> Package -> FinishedGood for FIFO accuracy.

        Returns:
            Total cost as Decimal summed across all recipient-package assignments
        """
        if not self.event_recipient_packages:
            return Decimal("0.00")

        total_cost = Decimal("0.00")
        for erp in self.event_recipient_packages:
            total_cost += erp.calculate_cost()

        return total_cost

    def get_recipient_count(self) -> int:
        """
        Get number of unique recipients in this event.

        Returns:
            Number of unique recipients
        """
        if not self.event_recipient_packages:
            return 0

        unique_recipients = set()
        for erp in self.event_recipient_packages:
            unique_recipients.add(erp.recipient_id)

        return len(unique_recipients)

    def get_package_count(self) -> int:
        """
        Get total number of packages in this event.

        Returns:
            Total packages (sum of quantities)
        """
        if not self.event_recipient_packages:
            return 0

        total = 0
        for erp in self.event_recipient_packages:
            total += erp.quantity

        return total

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert event to dictionary.

        Args:
            include_relationships: If True, include assignments

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["total_cost"] = float(self.get_total_cost())
        result["recipient_count"] = self.get_recipient_count()
        result["package_count"] = self.get_package_count()

        # Format date
        if self.event_date:
            result["event_date"] = self.event_date.isoformat()

        return result


class EventRecipientPackage(BaseModel):
    """
    EventRecipientPackage junction table.

    Links events, recipients, and packages - tracking which recipient
    gets which package for a specific event.

    Attributes:
        event_id: Foreign key to Event
        recipient_id: Foreign key to Recipient
        package_id: Foreign key to Package
        quantity: Number of this package for this recipient (default 1)
        notes: Optional notes (e.g., "Likes chocolate")
    """

    __tablename__ = "event_recipient_packages"

    # Foreign keys
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("recipients.id", ondelete="RESTRICT"), nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id", ondelete="RESTRICT"), nullable=False)

    # Quantity and notes
    quantity = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)

    # Production status tracking
    status = Column(
        SQLEnum(PackageStatus), nullable=False, default=PackageStatus.PENDING
    )
    delivered_to = Column(String(500), nullable=True)

    # Feature 016: Fulfillment status workflow (pending -> ready -> delivered)
    fulfillment_status = Column(
        String(20),
        nullable=False,
        default=FulfillmentStatus.PENDING.value
    )

    # Relationships
    event = relationship("Event", back_populates="event_recipient_packages")
    recipient = relationship("Recipient", lazy="joined")
    package = relationship("Package", lazy="joined")

    # Indexes
    __table_args__ = (
        Index("idx_erp_event", "event_id"),
        Index("idx_erp_recipient", "recipient_id"),
        Index("idx_erp_package", "package_id"),
        Index("idx_erp_status", "status"),
        Index("idx_erp_fulfillment_status", "fulfillment_status"),
    )

    def __repr__(self) -> str:
        """String representation of event recipient package."""
        return (
            f"EventRecipientPackage(event_id={self.event_id}, "
            f"recipient_id={self.recipient_id}, package_id={self.package_id}, "
            f"quantity={self.quantity})"
        )

    def calculate_cost(self) -> Decimal:
        """
        Calculate cost for this assignment.

        Cost chains through: ERP -> Package -> FinishedGood for FIFO accuracy.

        Returns:
            Package cost (Decimal) multiplied by quantity
        """
        if not self.package:
            return Decimal("0.00")

        package_cost = self.package.calculate_cost()
        return package_cost * Decimal(str(self.quantity))

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert to dictionary.

        Args:
            include_relationships: If True, include recipient/package details

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Add calculated cost
        result["cost"] = float(self.calculate_cost())

        # Add status as string value
        if self.status:
            result["status"] = self.status.value

        # Add fulfillment status
        if self.fulfillment_status:
            result["fulfillment_status"] = self.fulfillment_status

        if include_relationships:
            if self.recipient:
                result["recipient_name"] = self.recipient.name
            if self.package:
                result["package_name"] = self.package.name

        return result


class EventProductionTarget(BaseModel):
    """
    EventProductionTarget model for tracking recipe production targets per event.

    Stores how many batches of a recipe are targeted for a specific event.
    Used for progress tracking in the event-centric production model.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        recipe_id: Foreign key to Recipe (RESTRICT delete)
        target_batches: Number of batches to produce (must be > 0)
        notes: Optional notes about the target
    """

    __tablename__ = "event_production_targets"

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

    # Target data
    target_batches = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    event = relationship("Event", back_populates="production_targets")
    recipe = relationship("Recipe")

    # Constraints
    __table_args__ = (
        UniqueConstraint("event_id", "recipe_id", name="uq_event_recipe_target"),
        CheckConstraint("target_batches > 0", name="ck_target_batches_positive"),
        Index("idx_ept_event", "event_id"),
        Index("idx_ept_recipe", "recipe_id"),
    )

    def __repr__(self) -> str:
        """String representation of production target."""
        return (
            f"EventProductionTarget(event_id={self.event_id}, "
            f"recipe_id={self.recipe_id}, target_batches={self.target_batches})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert to dictionary.

        Args:
            include_relationships: If True, include recipe name

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        if include_relationships:
            if self.recipe:
                result["recipe_name"] = self.recipe.name
            if self.event:
                result["event_name"] = self.event.name

        return result


class EventAssemblyTarget(BaseModel):
    """
    EventAssemblyTarget model for tracking finished good assembly targets per event.

    Stores how many units of a finished good are targeted for a specific event.
    Used for progress tracking in the event-centric production model.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        finished_good_id: Foreign key to FinishedGood (RESTRICT delete)
        target_quantity: Number of units to assemble (must be > 0)
        notes: Optional notes about the target
    """

    __tablename__ = "event_assembly_targets"

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

    # Target data
    target_quantity = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    event = relationship("Event", back_populates="assembly_targets")
    finished_good = relationship("FinishedGood")

    # Constraints
    __table_args__ = (
        UniqueConstraint("event_id", "finished_good_id", name="uq_event_fg_target"),
        CheckConstraint("target_quantity > 0", name="ck_target_quantity_positive"),
        Index("idx_eat_event", "event_id"),
        Index("idx_eat_finished_good", "finished_good_id"),
    )

    def __repr__(self) -> str:
        """String representation of assembly target."""
        return (
            f"EventAssemblyTarget(event_id={self.event_id}, "
            f"finished_good_id={self.finished_good_id}, target_quantity={self.target_quantity})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert to dictionary.

        Args:
            include_relationships: If True, include finished good name

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        if include_relationships:
            if self.finished_good:
                result["finished_good_name"] = self.finished_good.display_name
            if self.event:
                result["event_name"] = self.event.name

        return result
