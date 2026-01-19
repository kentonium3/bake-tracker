"""
MaterialProduct model for specific purchasable material items.

This model represents a specific purchasable item from a supplier
(e.g., "Michaels Red Satin 100ft Roll"). Part of Feature 047: Materials Management System.

Feature 058: Removed current_inventory and weighted_avg_cost fields.
Inventory and costing now tracked via MaterialInventoryItem (FIFO).
"""

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
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class MaterialProduct(BaseModel):
    """
    MaterialProduct model representing catalog definitions for purchasable material items.

    Each MaterialProduct is a specific item from a supplier that can be
    purchased. This is a DEFINITION entity - actual inventory and costing
    are tracked in MaterialInventoryItem (FIFO pattern per Feature 058).

    Attributes:
        material_id: Foreign key to parent Material
        supplier_id: Foreign key to preferred Supplier (nullable)
        name: Product display name (e.g., "100ft Red Satin Roll")
        slug: URL-friendly identifier for stable import/export references
        brand: Brand name (e.g., "Michaels")
        sku: Supplier SKU (nullable)
        package_quantity: Quantity per package (e.g., 100 for 100ft)
        package_unit: Unit of package (e.g., 'feet', 'yards', 'each')
        quantity_in_base_units: Converted quantity in base units (cm)
        is_hidden: Hide from selection lists
        is_provisional: Product created with minimal info, needs completion (F059)
        notes: User notes

    Relationships:
        material: Many-to-One with Material
        supplier: Many-to-One with Supplier (existing table)
        purchases: One-to-Many with MaterialPurchase
        inventory_items: One-to-Many with MaterialInventoryItem (FIFO lots)
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

    # Feature 058: Removed current_inventory and weighted_avg_cost fields
    # Inventory and costing now tracked via MaterialInventoryItem (FIFO)

    # Visibility and status
    is_hidden = Column(Boolean, nullable=False, default=False, index=True)
    # Feature 059: Provisional products created via CLI with minimal info
    is_provisional = Column(Boolean, nullable=False, default=False, index=True)

    # Feature 059: Provisional product support
    # Provisional products are created with minimal metadata and can be enriched later
    is_provisional = Column(Boolean, nullable=False, default=False, index=True)

    # Feature 059: Provisional product flag for products created via CLI
    # with minimal information that need enrichment later
    is_provisional = Column(Boolean, nullable=False, default=False, index=True)

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
    # Feature 058: FIFO inventory tracking
    inventory_items = relationship(
        "MaterialInventoryItem",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Indexes and constraints
    # Feature 058: Removed CheckConstraints for current_inventory and weighted_avg_cost
    __table_args__ = (
        Index("idx_material_product_material", "material_id"),
        Index("idx_material_product_supplier", "supplier_id"),
        Index("idx_material_product_slug", "slug"),
        Index("idx_material_product_hidden", "is_hidden"),
        Index("idx_material_product_provisional", "is_provisional"),
        CheckConstraint("package_quantity > 0", name="ck_material_product_quantity_positive"),
        CheckConstraint(
            "quantity_in_base_units > 0", name="ck_material_product_base_units_positive"
        ),
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

    # Feature 058: Removed inventory_value property
    # Inventory value now calculated from MaterialInventoryItem lots

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
        # Feature 058: Removed inventory_value from output

        if include_relationships:
            if self.material:
                result["material"] = self.material.to_dict(False)
            if self.supplier:
                result["supplier_name"] = self.supplier.name

        return result
