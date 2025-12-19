"""
Product model for specific purchasable versions of ingredients.

This model represents a specific brand, package size, and supplier combination
for an Ingredient. Multiple products can exist for the same ingredient.

Example: "King Arthur All-Purpose Flour 25 lb bag from Costco" is a product
         of the "All-Purpose Flour" ingredient.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel


class Product(BaseModel):
    """
    Product model representing specific purchasable versions of ingredients.

    Each product represents a specific combination of:
    - Brand (e.g., "King Arthur", "Bob's Red Mill", "Generic")
    - Package size (e.g., "25 lb", "5 kg")
    - Package type (e.g., "bag", "box", "jar")
    - Supplier (e.g., "Costco", "Wegmans", "Amazon")

    Attributes:
        ingredient_id: Foreign key to Ingredient
        brand: Brand name
        package_size: Size description (e.g., "25 lb", "5 kg")
        package_type: Package type (bag, box, jar, bottle, etc.)
        package_unit: Unit the package contains (bag, lb, oz, etc.)
        package_unit_quantity: Quantity per package in package_unit
        upc_code: UPC/barcode for scanning (future use)
        supplier: Supplier/store name
        supplier_sku: Supplier's SKU/product code
        preferred: Is this the preferred product for this ingredient?
        notes: Additional notes
        date_added: When product was created
        last_modified: Last modification timestamp
    """

    __tablename__ = "products"

    # Foreign key to Ingredient
    ingredient_id = Column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Brand and package information
    brand = Column(String(200), nullable=True, index=True)
    package_size = Column(String(100), nullable=True)  # e.g., "25 lb", "5 kg"
    package_type = Column(String(50), nullable=True)  # bag, box, jar, bottle, etc.

    # Package contents information (renamed from purchase_unit/purchase_quantity in v3.4)
    package_unit = Column(String(50), nullable=False)  # Unit the package contains
    package_unit_quantity = Column(Float, nullable=False)  # Quantity per package

    # Identification codes (for future use)
    upc_code = Column(
        String(20), nullable=True, index=True
    )  # UPC/barcode (legacy name, use gtin for GS1)
    supplier = Column(String(200), nullable=True)  # Where to buy
    supplier_sku = Column(String(100), nullable=True)  # Supplier's product code

    # Industry standard identifiers (FUTURE READY - all nullable)
    gtin = Column(
        String(20), nullable=True, unique=True, index=True
    )  # GS1 GTIN (preferred over upc_code)
    brand_owner = Column(String(200), nullable=True)  # Brand owner/manufacturer
    gpc_brick_code = Column(String(20), nullable=True)  # GS1 GPC category code
    net_content_value = Column(Float, nullable=True)  # Net content quantity from label
    net_content_uom = Column(
        String(20), nullable=True
    )  # Net content unit of measure (g, kg, ml, L, oz)
    country_of_sale = Column(String(3), nullable=True)  # ISO 3166-1 alpha-3 country code
    off_id = Column(String(50), nullable=True)  # Open Food Facts product code

    # Preference flag
    preferred = Column(Boolean, nullable=False, default=False)

    # Additional information
    notes = Column(Text, nullable=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    ingredient = relationship("Ingredient", back_populates="products")
    purchases = relationship(
        "Purchase", back_populates="product", cascade="all, delete-orphan", lazy="select"
    )
    inventory_items = relationship(
        "InventoryItem", back_populates="product", cascade="all, delete-orphan", lazy="select"
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_product_ingredient", "ingredient_id"),
        Index("idx_product_brand", "brand"),
        Index("idx_product_upc", "upc_code"),
        # Prevent duplicate products: same ingredient + brand + size + unit
        UniqueConstraint(
            "ingredient_id", "brand", "package_size", "package_unit",
            name="uq_product_ingredient_brand_size_unit"
        ),
    )

    def __repr__(self) -> str:
        """String representation of product."""
        brand_str = f" {self.brand}" if self.brand else ""
        size_str = f" {self.package_size}" if self.package_size else ""
        return f"Product(id={self.id}, ingredient='{self.ingredient.display_name}'{brand_str}{size_str})"

    @property
    def display_name(self) -> str:
        """
        Get display name for this product.

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
            return f"{self.ingredient.display_name} (generic)"

        return " ".join(parts)

    def get_most_recent_purchase(self):
        """
        Get the most recent purchase for this product.

        Returns:
            Purchase instance or None if no purchases
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
        recent_purchases = [p for p in self.purchases if p.purchase_date >= cutoff_date]

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

    def get_total_inventory_quantity(self) -> float:
        """
        Get total quantity for this product across all inventory items.

        Returns:
            Total quantity in purchase units
        """
        return sum(item.quantity for item in self.inventory_items)

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert product to dictionary.

        Args:
            include_relationships: If True, include purchases and inventory items

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["display_name"] = self.display_name
        result["current_cost"] = self.get_current_cost_per_unit()
        result["total_inventory_quantity"] = self.get_total_inventory_quantity()

        if include_relationships:
            result["purchases"] = [p.to_dict(False) for p in self.purchases]
            result["inventory_items"] = [item.to_dict(False) for item in self.inventory_items]

        return result
