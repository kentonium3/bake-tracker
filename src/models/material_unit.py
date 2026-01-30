"""
MaterialUnit model for atomic consumption units.

This model represents an atomic consumption unit defining quantity per use
(e.g., "6-inch ribbon" = 6 inches per unit). Part of Feature 047: Materials Management System.

Feature 084: Changed parent from Material to MaterialProduct. MaterialUnits are now
scoped to specific products, enabling product-specific unit definitions.
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    ForeignKey,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class MaterialUnit(BaseModel):
    """
    MaterialUnit model representing atomic consumption units.

    A MaterialUnit defines how much of a material is consumed per use
    in a finished good composition. For example, "6-inch ribbon" means
    6 inches of the parent material is consumed each time.

    Feature 084: MaterialUnits are now children of MaterialProduct (not Material).
    This enables product-specific unit definitions and auto-generation for "each" type products.

    Attributes:
        material_product_id: Foreign key to parent MaterialProduct
        name: Unit display name (e.g., "6-inch Red Ribbon")
        slug: URL-friendly identifier (e.g., "6-inch-red-ribbon")
        quantity_per_unit: Base units consumed per use (e.g., 6 for 6 inches)
        description: Optional description

    Relationships:
        material_product: Many-to-One with MaterialProduct

    Computed Properties (calculated by service layer):
        available_inventory: Sum of (product.current_inventory / quantity_per_unit)
        current_cost: weighted_avg_cost * quantity_per_unit
    """

    __tablename__ = "material_units"

    # Foreign key to parent material product (Feature 084: changed from material_id)
    material_product_id = Column(
        Integer,
        ForeignKey("material_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic information
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, index=True)
    quantity_per_unit = Column(Float, nullable=False)
    description = Column(Text, nullable=True)

    # Relationships (Feature 084: changed from material to material_product)
    material_product = relationship(
        "MaterialProduct",
        back_populates="material_units",
        lazy="joined",
    )

    # Indexes and constraints (Feature 084: compound unique constraints scoped to product)
    __table_args__ = (
        Index("idx_material_unit_material_product", "material_product_id"),
        Index("idx_material_unit_slug", "slug"),
        UniqueConstraint("material_product_id", "slug", name="uq_material_unit_product_slug"),
        UniqueConstraint("material_product_id", "name", name="uq_material_unit_product_name"),
        CheckConstraint("quantity_per_unit > 0", name="ck_material_unit_quantity_positive"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        """String representation of material unit."""
        return f"MaterialUnit(id={self.id}, name='{self.name}')"

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert material unit to dictionary.

        Args:
            include_relationships: If True, include material_product

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        if include_relationships:
            if self.material_product:
                result["material_product"] = self.material_product.to_dict(False)

        return result
