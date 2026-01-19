"""
Product model for specific purchasable versions of ingredients.

This model represents a specific brand, package size, and supplier combination
for an Ingredient. Multiple products can exist for the same ingredient.

Example: "King Arthur All-Purpose Flour 25 lb bag from Costco" is a product
         of the "All-Purpose Flour" ingredient.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship, validates

from .base import BaseModel
from src.utils.datetime_utils import utc_now


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
        product_name: Variant name (e.g., "70% Cacao", "Extra Virgin", "Original Recipe")
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
    # Variant name to differentiate products with same brand/packaging
    # (e.g., "70% Cacao", "Extra Virgin", "Original Recipe", "Unsweetened")
    product_name = Column(String(200), nullable=True)
    package_size = Column(String(100), nullable=True)  # e.g., "25 lb", "5 kg"
    package_type = Column(String(50), nullable=True)  # bag, box, jar, bottle, etc.

    # Package contents information (renamed from purchase_unit/purchase_quantity in v3.4)
    package_unit = Column(String(50), nullable=False)  # Unit the package contains
    package_unit_quantity = Column(Float, nullable=False)  # Quantity per package

    # Identification codes (for future use)
    upc_code = Column(
        String(20), nullable=True, index=True
    )  # UPC/barcode (legacy name, use gtin for GS1)

    # F057: Unique slug for portability and AI data augmentation
    # Format: ingredient_slug:brand:qty:unit (with collision suffix if needed)
    slug = Column(
        String(200),
        nullable=True,
        unique=True,
        index=True,
        comment="Unique human-readable identifier for export/import portability",
    )

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

    # Feature 027: Supplier reference and visibility
    preferred_supplier_id = Column(
        Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_hidden = Column(Boolean, nullable=False, default=False, index=True)

    # F057: Provisional Product Support
    is_provisional = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="True if product was created during purchase entry and needs review",
    )

    # Additional information
    notes = Column(Text, nullable=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=utc_now)
    last_modified = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    ingredient = relationship("Ingredient", back_populates="products")
    purchases = relationship("Purchase", back_populates="product", lazy="select")
    inventory_items = relationship(
        "InventoryItem", back_populates="product", cascade="all, delete-orphan", lazy="select"
    )
    preferred_supplier = relationship("Supplier", foreign_keys=[preferred_supplier_id])

    # Indexes and constraints
    __table_args__ = (
        Index("idx_product_ingredient", "ingredient_id"),
        Index("idx_product_brand", "brand"),
        Index("idx_product_upc", "upc_code"),
        # Feature 027: Indexes for new columns
        Index("idx_product_preferred_supplier", "preferred_supplier_id"),
        Index("idx_product_hidden", "is_hidden"),
        # F057: Index for provisional product filtering
        Index("idx_product_provisional", "is_provisional"),
        # Unique constraint to prevent duplicate product variants
        # Note: SQLite treats NULL as distinct, so multiple products with NULL product_name are allowed
        UniqueConstraint(
            "ingredient_id",
            "brand",
            "product_name",
            "package_size",
            "package_unit",
            name="uq_product_variant",
        ),
    )

    @validates("product_name")
    def _normalize_product_name(self, key, value):
        """Normalize empty strings to None for consistency with unique constraint."""
        if value == "":
            return None
        return value

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
            Formatted display name (e.g., "Lindt 70% Cacao 3.5 oz bar")
            Format: "Brand ProductName Size Type"
        """
        parts = []
        if self.brand:
            parts.append(self.brand)
        if self.product_name:
            parts.append(self.product_name)
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

        total_cost = sum(float(p.unit_price) for p in recent_purchases)
        return total_cost / len(recent_purchases)

    def get_current_cost_per_unit(self) -> float:
        """
        Get current cost per purchase unit (most recent purchase).

        Returns:
            Unit price from most recent purchase, or 0.0 if no purchases
        """
        recent = self.get_most_recent_purchase()
        return float(recent.unit_price) if recent else 0.0

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
