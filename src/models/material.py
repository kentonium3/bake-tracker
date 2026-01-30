"""
Material model for abstract material definitions.

This model represents an abstract material definition (e.g., "Red Satin Ribbon",
"6-inch Cellophane Bag"). Part of Feature 047: Materials Management System.
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel


class Material(BaseModel):
    """
    Material model representing abstract material definitions.

    Materials are the third level of the mandatory 3-level hierarchy:
    MaterialCategory > MaterialSubcategory > Material

    Each Material can have multiple MaterialProducts (specific purchasable items)
    and multiple MaterialUnits (consumption definitions).

    Attributes:
        subcategory_id: Foreign key to parent MaterialSubcategory
        name: Material display name (e.g., "Red Satin Ribbon")
        slug: URL-friendly identifier (e.g., "red-satin-ribbon")
        description: Optional description text
        base_unit_type: Unit type for inventory ('each', 'linear_inches', 'square_inches')
        notes: User notes

    Relationships:
        subcategory: Many-to-One with MaterialSubcategory
        products: One-to-Many with MaterialProduct (cascade delete)

    Note (Feature 084): MaterialUnits are now children of MaterialProduct,
    not Material. Access units via material.products[*].material_units.
    """

    __tablename__ = "materials"

    # Foreign key to parent subcategory
    subcategory_id = Column(
        Integer,
        ForeignKey("material_subcategories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic information
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    base_unit_type = Column(String(20), nullable=False)  # 'each', 'linear_inches', 'square_inches'
    notes = Column(Text, nullable=True)

    # Relationships
    subcategory = relationship(
        "MaterialSubcategory",
        back_populates="materials",
    )
    products = relationship(
        "MaterialProduct",
        back_populates="material",
        cascade="all, delete-orphan",
        lazy="select",
    )
    # Feature 084: Removed 'units' relationship - MaterialUnits are now
    # children of MaterialProduct, not Material. Access units via:
    # material.products[*].material_units

    # Indexes and constraints
    __table_args__ = (
        Index("idx_material_subcategory", "subcategory_id"),
        Index("idx_material_slug", "slug"),
        Index("idx_material_name", "name"),
        CheckConstraint(
            "base_unit_type IN ('each', 'linear_cm', 'square_cm')",
            name="ck_material_base_unit_type",
        ),
    )

    def __repr__(self) -> str:
        """String representation of material."""
        return f"Material(id={self.id}, name='{self.name}')"

    @property
    def product_count(self) -> int:
        """Get number of products for this material."""
        return len(self.products)

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert material to dictionary.

        Args:
            include_relationships: If True, include subcategory and products

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)
        result["product_count"] = self.product_count

        if include_relationships:
            if self.subcategory:
                result["subcategory"] = self.subcategory.to_dict(False)
            result["products"] = [p.to_dict(False) for p in self.products]
            # Feature 084: Removed units from to_dict - units are now
            # accessed via products[*].material_units

        return result
