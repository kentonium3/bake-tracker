"""
RecipeCategory model for recipe grouping.

This model represents flat categories for organizing recipes
(e.g., "Cakes", "Cookies", "Candies"). Part of Feature 096:
Recipe Category Management.
"""

from sqlalchemy import Column, String, Text, Integer, Index

from .base import BaseModel


class RecipeCategory(BaseModel):
    """
    RecipeCategory model representing recipe grouping.

    Categories are flat (no hierarchy). Used to organize recipes
    in dropdowns and admin UI.

    Attributes:
        name: Category display name (e.g., "Cakes", "Cookies")
        slug: URL-friendly identifier (e.g., "cakes", "cookies")
        description: Optional description text
        sort_order: Display ordering (default 0)
    """

    __tablename__ = "recipe_categories"

    # Basic information
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)

    # Indexes
    __table_args__ = (
        Index("idx_recipe_category_name", "name"),
        Index("idx_recipe_category_slug", "slug"),
    )

    def __repr__(self) -> str:
        """String representation of recipe category."""
        return f"<RecipeCategory(name='{self.name}')>"

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert recipe category to dictionary.

        Args:
            include_relationships: Unused (no relationships), kept for API consistency

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)
        return result
