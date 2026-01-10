"""
MaterialUnit model for atomic consumption units.

This model represents an atomic consumption unit defining quantity per use
(e.g., "6-inch ribbon" = 6 inches per unit). Part of Feature 047: Materials Management System.
"""

from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel


class MaterialUnit(BaseModel):
    """
    MaterialUnit model representing atomic consumption units.

    A MaterialUnit defines how much of a material is consumed per use
    in a finished good composition. For example, "6-inch ribbon" means
    6 inches of the parent material is consumed each time.

    Attributes:
        material_id: Foreign key to parent Material
        name: Unit display name (e.g., "6-inch Red Ribbon")
        slug: URL-friendly identifier (e.g., "6-inch-red-ribbon")
        quantity_per_unit: Base units consumed per use (e.g., 6 for 6 inches)
        description: Optional description

    Relationships:
        material: Many-to-One with Material

    Computed Properties (calculated by service layer):
        available_inventory: Sum of (product.current_inventory / quantity_per_unit)
        current_cost: weighted_avg_cost * quantity_per_unit
    """

    __tablename__ = "material_units"

    # Foreign key to parent material
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic information
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, unique=True, index=True)
    quantity_per_unit = Column(Float, nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    material = relationship(
        "Material",
        back_populates="units",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_material_unit_material", "material_id"),
        Index("idx_material_unit_slug", "slug"),
        CheckConstraint("quantity_per_unit > 0", name="ck_material_unit_quantity_positive"),
    )

    def __repr__(self) -> str:
        """String representation of material unit."""
        return f"MaterialUnit(id={self.id}, name='{self.name}')"

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert material unit to dictionary.

        Args:
            include_relationships: If True, include material

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        if include_relationships:
            if self.material:
                result["material"] = self.material.to_dict(False)

        return result
