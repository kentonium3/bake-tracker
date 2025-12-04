"""
Event models for tracking seasonal baking events.

This module contains:
- Event: Annual baking events (e.g., Christmas 2024)
- EventRecipientPackage: Junction table linking events, recipients, and packages
"""

from datetime import datetime
from decimal import Decimal

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
)
from sqlalchemy.orm import relationship

from .package_status import PackageStatus

from .base import BaseModel


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

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
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

    # Relationships
    event = relationship("Event", back_populates="event_recipient_packages")
    recipient = relationship("Recipient")
    package = relationship("Package")

    # Indexes
    __table_args__ = (
        Index("idx_erp_event", "event_id"),
        Index("idx_erp_recipient", "recipient_id"),
        Index("idx_erp_package", "package_id"),
        Index("idx_erp_status", "status"),
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

        if include_relationships:
            if self.recipient:
                result["recipient_name"] = self.recipient.name
            if self.package:
                result["package_name"] = self.package.name

        return result
