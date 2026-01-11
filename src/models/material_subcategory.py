"""
MaterialSubcategory model for second-level material grouping.

This model represents the second-level grouping within a category
(e.g., "Satin Ribbon" under "Ribbons"). Part of Feature 047: Materials Management System.
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel


class MaterialSubcategory(BaseModel):
    """
    MaterialSubcategory model representing second-level material grouping.

    Subcategories are the second level of the mandatory 3-level hierarchy:
    MaterialCategory > MaterialSubcategory > Material

    Attributes:
        category_id: Foreign key to parent MaterialCategory
        name: Subcategory display name (e.g., "Satin", "Grosgrain")
        slug: URL-friendly identifier (e.g., "satin", "grosgrain")
        description: Optional description text
        sort_order: Display ordering (default 0)

    Relationships:
        category: Many-to-One with MaterialCategory
        materials: One-to-Many with Material (cascade delete)
    """

    __tablename__ = "material_subcategories"

    # Foreign key to parent category
    category_id = Column(
        Integer,
        ForeignKey("material_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic information
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)

    # Relationships
    category = relationship(
        "MaterialCategory",
        back_populates="subcategories",
    )
    materials = relationship(
        "Material",
        back_populates="subcategory",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_material_subcategory_category", "category_id"),
        Index("idx_material_subcategory_slug", "slug"),
        UniqueConstraint("category_id", "name", name="uq_material_subcategory_name_category"),
    )

    def __repr__(self) -> str:
        """String representation of material subcategory."""
        return f"MaterialSubcategory(id={self.id}, name='{self.name}')"

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert material subcategory to dictionary.

        Args:
            include_relationships: If True, include category and materials

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        if include_relationships:
            if self.category:
                result["category"] = self.category.to_dict(False)
            result["materials"] = [m.to_dict(False) for m in self.materials]

        return result
