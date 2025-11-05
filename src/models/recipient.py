"""
Recipient model for tracking gift package recipients.

This module contains:
- Recipient: People who receive gift packages
"""

from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Index

from .base import BaseModel


class Recipient(BaseModel):
    """
    Recipient model representing people receiving gift packages.

    Recipients are assigned packages through events. They can represent
    individuals or households.

    Attributes:
        name: Recipient name (e.g., "John Smith", "The Smiths")
        household_name: Optional household identifier
        address: Optional delivery address
        notes: Additional notes (preferences, allergies, etc.)
    """

    __tablename__ = "recipients"

    # Basic information
    name = Column(String(200), nullable=False, index=True)
    household_name = Column(String(200), nullable=True, index=True)
    address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Indexes
    __table_args__ = (
        Index("idx_recipient_name", "name"),
        Index("idx_recipient_household", "household_name"),
    )

    def __repr__(self) -> str:
        """String representation of recipient."""
        household = f" ({self.household_name})" if self.household_name else ""
        return f"Recipient(id={self.id}, name='{self.name}'{household})"

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert recipient to dictionary.

        Args:
            include_relationships: Not used for recipients currently

        Returns:
            Dictionary representation
        """
        return super().to_dict(include_relationships)
