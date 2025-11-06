"""
ProductVariant model for specific purchasable versions of products.

This model represents a specific brand, package size, and supplier combination
for a Product. Multiple variants can exist for the same product.

Example: "King Arthur All-Purpose Flour 25 lb bag from Costco" is a variant
         of the "All-Purpose Flour" product.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class ProductVariant(BaseModel):
    """
    ProductVariant model representing specific purchasable versions of products.

    Each variant represents a specific combination of:
    - Brand (e.g., "King Arthur", "Bob's Red Mill", "Generic")
    - Package size (e.g., "25 lb", "5 kg")
    - Package type (e.g., "bag", "box", "jar")
    - Supplier (e.g., "Costco", "Wegmans", "Amazon")

    Attributes:
        product_id: Foreign key to Product
        brand: Brand name
        package_size: Size description (e.g., "25 lb", "5 kg")
        package_type: Package type (bag, box, jar, bottle, etc.)
        purchase_unit: Unit purchased in (bag, lb, oz, etc.)
        purchase_quantity: Quantity per package
        upc_code: UPC/barcode for scanning (future use)
        supplier: Supplier/store name
        supplier_sku: Supplier's SKU/product code
        preferred: Is this the preferred variant for this product?
        notes: Additional notes
        date_added: When variant was created
        last_modified: Last modification timestamp
    """

    __tablename__ = "product_variants"

    # Foreign key to Product
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)

    # Brand and package information
    brand = Column(String(200), nullable=True, index=True)
    package_size = Column(String(100), nullable=True)  # e.g., "25 lb", "5 kg"
    package_type = Column(String(50), nullable=True)  # bag, box, jar, bottle, etc.

    # Purchase information
    purchase_unit = Column(String(50), nullable=False)  # Unit purchased in
    purchase_quantity = Column(Float, nullable=False)  # Quantity per package

    # Identification codes (for future use)
    upc_code = Column(String(20), nullable=True, index=True)  # UPC/barcode
    supplier = Column(String(200), nullable=True)  # Where to buy
    supplier_sku = Column(String(100), nullable=True)  # Supplier's product code

    # Preference flag
    preferred = Column(Boolean, nullable=False, default=False)

    # Additional information
    notes = Column(Text, nullable=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="variants")
    purchases = relationship(
        "PurchaseHistory",
        back_populates="product_variant",
        cascade="all, delete-orphan",
        lazy="select"
    )
    pantry_items = relationship(
        "PantryItem",
        back_populates="product_variant",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_variant_product", "product_id"),
        Index("idx_variant_brand", "brand"),
        Index("idx_variant_upc", "upc_code"),
    )

    def __repr__(self) -> str:
        """String representation of variant."""
        brand_str = f" {self.brand}" if self.brand else ""
        size_str = f" {self.package_size}" if self.package_size else ""
        return f"ProductVariant(id={self.id}, product='{self.product.name}'{brand_str}{size_str})"

    @property
    def display_name(self) -> str:
        """
        Get display name for this variant.

        Returns:
            Formatted display name (e.g., "King Arthur 25 lb bag")
        """
        parts = []
        if self.brand:
            parts.append(self.brand)
        if self.package_size:
            parts.append(self.package_size)
        if self.package_type:
            parts.append(self.package_type)

        if not parts:
            return f"{self.product.name} (generic)"

        return " ".join(parts)

    def get_most_recent_purchase(self):
        """
        Get the most recent purchase for this variant.

        Returns:
            PurchaseHistory instance or None if no purchases
        """
        if not self.purchases:
            return None

        # Sort by purchase date descending
        sorted_purchases = sorted(self.purchases, key=lambda p: p.purchase_date, reverse=True)
        return sorted_purchases[0]

    def get_average_price(self, days: int = 90) -> float:
        """
        Get average purchase price over specified time period.

        Args:
            days: Number of days to look back (default: 90)

        Returns:
            Average unit cost, or 0.0 if no purchases
        """
        from datetime import date, timedelta

        cutoff_date = date.today() - timedelta(days=days)
        recent_purchases = [
            p for p in self.purchases
            if p.purchase_date >= cutoff_date
        ]

        if not recent_purchases:
            return 0.0

        total_cost = sum(p.unit_cost for p in recent_purchases)
        return total_cost / len(recent_purchases)

    def get_current_cost_per_unit(self) -> float:
        """
        Get current cost per purchase unit (most recent purchase).

        Returns:
            Unit cost from most recent purchase, or 0.0 if no purchases
        """
        recent = self.get_most_recent_purchase()
        return recent.unit_cost if recent else 0.0

    def get_total_pantry_quantity(self) -> float:
        """
        Get total quantity for this variant across all pantry items.

        Returns:
            Total quantity in purchase units
        """
        return sum(item.quantity for item in self.pantry_items)

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert variant to dictionary.

        Args:
            include_relationships: If True, include purchases and pantry items

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["display_name"] = self.display_name
        result["current_cost"] = self.get_current_cost_per_unit()
        result["total_pantry_quantity"] = self.get_total_pantry_quantity()

        if include_relationships:
            result["purchases"] = [p.to_dict(False) for p in self.purchases]
            result["pantry_items"] = [item.to_dict(False) for item in self.pantry_items]

        return result
