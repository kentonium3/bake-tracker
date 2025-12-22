"""
Supplier model for tracking ingredient and product suppliers.

This model represents vendors/suppliers where ingredients and products
are purchased from.

Example: "Costco" in "Waltham, MA" as a supplier, with optional
         street address and notes for directions or membership info.
"""

from sqlalchemy import Column, String, Boolean, Text, Index, CheckConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel


class Supplier(BaseModel):
    """
    Supplier model representing vendors where products are purchased.

    Suppliers can be linked to products as preferred suppliers, and
    purchases record which supplier was used for each transaction.

    Attributes:
        name: Supplier name (e.g., "Costco", "Restaurant Depot")
        street_address: Optional street address
        city: City name (e.g., "Waltham")
        state: Two-letter state code, uppercase (e.g., "MA")
        zip_code: ZIP code (e.g., "02451")
        notes: Optional notes (e.g., membership info, directions)
        is_active: Soft delete flag (True = active, False = deactivated)

    Relationships:
        products: Products that have this supplier as preferred
        purchases: Purchase transactions from this supplier
    """

    __tablename__ = "suppliers"

    # Supplier information
    name = Column(String(200), nullable=False)
    street_address = Column(String(200), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)
    notes = Column(Text, nullable=True)

    # Soft delete flag
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships (will be set up when related models are updated)
    # products = relationship("Product", back_populates="preferred_supplier")
    # purchases = relationship("Purchase", back_populates="supplier")

    # Table constraints and indexes
    __table_args__ = (
        # Enforce 2-letter uppercase state codes
        CheckConstraint(
            "state = UPPER(state) AND LENGTH(state) = 2",
            name="ck_supplier_state_format"
        ),
        # Index for name + city lookups (e.g., "Costco in Waltham")
        Index("idx_supplier_name_city", "name", "city"),
        # Index for filtering active suppliers in dropdowns
        Index("idx_supplier_active", "is_active"),
    )

    def __repr__(self) -> str:
        """String representation of supplier."""
        return (
            f"Supplier(id={self.id}, "
            f"name='{self.name}', "
            f"city='{self.city}', "
            f"state='{self.state}')"
        )

    @property
    def location(self) -> str:
        """Format city, state for display."""
        return f"{self.city}, {self.state}"

    @property
    def full_address(self) -> str:
        """Format full address for display."""
        if self.street_address:
            return f"{self.street_address}, {self.city}, {self.state} {self.zip_code}"
        return f"{self.city}, {self.state} {self.zip_code}"

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert supplier to dictionary.

        Args:
            include_relationships: If True, include related products/purchases

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Add computed fields
        result["location"] = self.location
        result["full_address"] = self.full_address

        return result
