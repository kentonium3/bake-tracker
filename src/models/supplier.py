"""
Supplier model for tracking ingredient and product suppliers.

This model represents vendors/suppliers where ingredients and products
are purchased from. Supports both physical stores and online vendors.

Example: "Costco" in "Waltham, MA" as a physical store supplier
         "King Arthur Baking" at "kingarthurbaking.com" as an online vendor
"""

from sqlalchemy import Column, String, Boolean, Text, Index, CheckConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel


class Supplier(BaseModel):
    """
    Supplier model representing vendors where products are purchased.

    Suppliers can be linked to products as preferred suppliers, and
    purchases record which supplier was used for each transaction.

    Supports two types:
    - 'physical': Physical stores requiring city/state/zip
    - 'online': Online vendors requiring only name (URL recommended)

    Attributes:
        name: Supplier name (e.g., "Costco", "King Arthur Baking")
        supplier_type: 'physical' or 'online' (default: 'physical')
        website_url: Website URL (recommended for online, optional for physical)
        street_address: Optional street address (physical stores)
        city: City name (required for physical, optional for online)
        state: Two-letter state code (required for physical, optional for online)
        zip_code: ZIP code (required for physical, optional for online)
        notes: Optional notes (e.g., membership info, directions)
        is_active: Soft delete flag (True = active, False = deactivated)

    Relationships:
        products: Products that have this supplier as preferred
        purchases: Purchase transactions from this supplier
    """

    __tablename__ = "suppliers"

    # Supplier information
    name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    supplier_type = Column(String(20), nullable=False, default="physical")
    website_url = Column(String(500), nullable=True)
    street_address = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)  # Required for physical, optional for online
    state = Column(String(2), nullable=True)   # Required for physical, optional for online
    zip_code = Column(String(10), nullable=True)  # Required for physical, optional for online
    notes = Column(Text, nullable=True)

    # Soft delete flag
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    purchases = relationship("Purchase", back_populates="supplier")

    # Table constraints and indexes
    __table_args__ = (
        # Enforce 2-letter uppercase state codes (when state is provided)
        CheckConstraint(
            "state IS NULL OR (state = UPPER(state) AND LENGTH(state) = 2)",
            name="ck_supplier_state_format"
        ),
        # Enforce valid supplier_type values
        CheckConstraint(
            "supplier_type IN ('physical', 'online')",
            name="ck_supplier_type_valid"
        ),
        # Unique index for slug (portable identifier)
        Index("idx_supplier_slug", "slug", unique=True),
        # Index for name + city lookups (e.g., "Costco in Waltham")
        Index("idx_supplier_name_city", "name", "city"),
        # Index for filtering active suppliers in dropdowns
        Index("idx_supplier_active", "is_active"),
        # Index for filtering by supplier type
        Index("idx_supplier_type", "supplier_type"),
    )

    @property
    def is_online(self) -> bool:
        """Check if this is an online vendor."""
        return self.supplier_type == "online"

    def __repr__(self) -> str:
        """String representation of supplier."""
        if self.is_online:
            return (
                f"Supplier(id={self.id}, "
                f"name='{self.name}', "
                f"type='online')"
            )
        return (
            f"Supplier(id={self.id}, "
            f"name='{self.name}', "
            f"city='{self.city}', "
            f"state='{self.state}')"
        )

    @property
    def location(self) -> str:
        """Format city, state for display. Returns 'Online' for online vendors."""
        if self.is_online:
            return "Online"
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.state or ""

    @property
    def display_name(self) -> str:
        """Format name with location for display."""
        if self.is_online:
            return f"{self.name} (Online)"
        if self.city and self.state:
            return f"{self.name} ({self.city}, {self.state})"
        return self.name

    @property
    def full_address(self) -> str:
        """Format full address for display. Returns URL for online vendors."""
        if self.is_online:
            return self.website_url or "Online"
        if self.street_address:
            return f"{self.street_address}, {self.city}, {self.state} {self.zip_code}"
        if self.city and self.state:
            return f"{self.city}, {self.state} {self.zip_code or ''}".strip()
        return ""

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
        result["is_online"] = self.is_online
        result["location"] = self.location
        result["display_name"] = self.display_name
        result["full_address"] = self.full_address

        return result
