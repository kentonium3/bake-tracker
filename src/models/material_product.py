"""
MaterialProduct model for specific purchasable material items.

This model represents a specific purchasable item from a supplier
(e.g., "Michaels Red Satin 100ft Roll"). Part of Feature 047: Materials Management System.
"""

from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    Index,
    CheckConstraint,
    Numeric,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class MaterialProduct(BaseModel):
    """
    MaterialProduct model representing specific purchasable material items.

    Each MaterialProduct is a specific item from a supplier that can be
    purchased and tracked in inventory. Uses weighted average costing
    (not FIFO) for non-perishable materials.

    Attributes:
        material_id: Foreign key to parent Material
        supplier_id: Foreign key to preferred Supplier (nullable)
        name: Product display name (e.g., "100ft Red Satin Roll")
        slug: URL-friendly identifier for stable import/export references
        brand: Brand name (e.g., "Michaels")
        sku: Supplier SKU (nullable)
        package_quantity: Quantity per package (e.g., 100 for 100ft)
        package_unit: Unit of package (e.g., 'feet', 'yards', 'each')
        quantity_in_base_units: Converted quantity in base units (e.g., 1200 inches)
        current_inventory: Current inventory in base units
        weighted_avg_cost: Weighted average cost per base unit
        is_hidden: Hide from selection lists
        notes: User notes

    Relationships:
        material: Many-to-One with Material
        supplier: Many-to-One with Supplier (existing table)
        purchases: One-to-Many with MaterialPurchase
    """

    __tablename__ = "material_products"

    # Foreign keys
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Product information
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=True, unique=True, index=True)
    brand = Column(String(100), nullable=True)
    sku = Column(String(100), nullable=True)

    # Package information
    package_quantity = Column(Float, nullable=False)
    package_unit = Column(String(20), nullable=False)
    quantity_in_base_units = Column(Float, nullable=False)

    # Inventory tracking
    current_inventory = Column(Float, nullable=False, default=0)
    weighted_avg_cost = Column(Numeric(10, 4), nullable=False, default=0)

    # Visibility
    is_hidden = Column(Boolean, nullable=False, default=False, index=True)

    # Additional information
    notes = Column(Text, nullable=True)

    # Relationships
    material = relationship(
        "Material",
        back_populates="products",
    )
    supplier = relationship(
        "Supplier",
        foreign_keys=[supplier_id],
    )
    purchases = relationship(
        "MaterialPurchase",
        back_populates="product",
        lazy="select",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_material_product_material", "material_id"),
        Index("idx_material_product_supplier", "supplier_id"),
        Index("idx_material_product_slug", "slug"),
        Index("idx_material_product_hidden", "is_hidden"),
        CheckConstraint("package_quantity > 0", name="ck_material_product_quantity_positive"),
        CheckConstraint(
            "quantity_in_base_units > 0", name="ck_material_product_base_units_positive"
        ),
        CheckConstraint(
            "current_inventory >= 0", name="ck_material_product_inventory_non_negative"
        ),
        CheckConstraint("weighted_avg_cost >= 0", name="ck_material_product_cost_non_negative"),
    )

    def __repr__(self) -> str:
        """String representation of material product."""
        return f"MaterialProduct(id={self.id}, name='{self.name}')"

    @property
    def display_name(self) -> str:
        """
        Get display name for this product.

        Returns:
            Formatted display name (e.g., "Michaels 100ft Red Satin Roll")
        """
        parts = []
        if self.brand:
            parts.append(self.brand)
        parts.append(self.name)
        return " ".join(parts)

    @property
    def inventory_value(self) -> Decimal:
        """
        Calculate total value of current inventory.

        Returns:
            current_inventory * weighted_avg_cost
        """
        return Decimal(str(self.current_inventory)) * self.weighted_avg_cost

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert material product to dictionary.

        Args:
            include_relationships: If True, include material and supplier

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)
        result["display_name"] = self.display_name
        result["inventory_value"] = str(self.inventory_value)

        if include_relationships:
            if self.material:
                result["material"] = self.material.to_dict(False)
            if self.supplier:
                result["supplier_name"] = self.supplier.name

        return result
