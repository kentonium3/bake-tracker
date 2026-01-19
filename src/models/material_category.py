"""
MaterialCategory model for top-level material grouping.

This model represents the top-level grouping for materials (e.g., "Ribbons",
"Boxes", "Bags", "Tags"). Part of Feature 047: Materials Management System.
"""

from sqlalchemy import Column, String, Text, Integer, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class MaterialCategory(BaseModel):
    """
    MaterialCategory model representing top-level material grouping.

    Categories are the first level of the mandatory 3-level material hierarchy:
    MaterialCategory > MaterialSubcategory > Material

    Attributes:
        name: Category display name (e.g., "Ribbons", "Boxes")
        slug: URL-friendly identifier (e.g., "ribbons", "boxes")
        description: Optional description text
        sort_order: Display ordering (default 0)

    Relationships:
        subcategories: One-to-Many with MaterialSubcategory (cascade delete)
    """

    __tablename__ = "material_categories"

    # Basic information
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)

    # Relationships
    subcategories = relationship(
        "MaterialSubcategory",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Indexes
    __table_args__ = (
        Index("idx_material_category_name", "name"),
        Index("idx_material_category_slug", "slug"),
    )

    def __repr__(self) -> str:
        """String representation of material category."""
        return f"MaterialCategory(id={self.id}, name='{self.name}')"

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert material category to dictionary.

        Args:
            include_relationships: If True, include subcategories

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        if include_relationships:
            result["subcategories"] = [s.to_dict(False) for s in self.subcategories]

        return result
