"""
IngredientCrosswalk model for external identifier mappings.

This model stores mappings between internal ingredients and external
taxonomy/nutrition systems like FoodOn, USDA FDC, FoodEx2, etc.
"""

from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class IngredientCrosswalk(BaseModel):
    """
    IngredientCrosswalk model for mapping ingredients to external systems.

    Links ingredients to external taxonomies and databases for:
    - Nutrition data (USDA FDC)
    - Food ontology (FoodOn)
    - Regulatory compliance (FoodEx2)
    - Product databases (Open Food Facts)

    Attributes:
        ingredient_id: Foreign key to Ingredient
        system: External system name (e.g., "FOODON", "FDC", "FOODEx2", "OFF")
        code: External system's code/ID for this ingredient
        meta: Optional JSON metadata for additional system-specific data
    """

    __tablename__ = "ingredient_crosswalks"

    # Foreign key to Ingredient
    ingredient_id = Column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # External system mapping
    system = Column(String(50), nullable=False, index=True)  # e.g., "FOODON", "FDC", "FOODEx2"
    code = Column(String(100), nullable=False)  # External code/ID
    meta = Column(JSON, nullable=True)  # Optional system-specific metadata

    # Relationships
    # passive_deletes="all" lets database CASCADE handle deletion without ORM interference
    ingredient = relationship("Ingredient", backref="crosswalks", passive_deletes="all")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_crosswalk_ingredient", "ingredient_id"),
        Index("idx_crosswalk_system", "system"),
        Index("idx_crosswalk_code", "code"),
        Index("idx_crosswalk_system_code", "system", "code"),  # Composite for lookups
    )

    def __repr__(self) -> str:
        """String representation of crosswalk."""
        return f"IngredientCrosswalk(id={self.id}, system='{self.system}', code='{self.code}')"

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert crosswalk to dictionary.

        Args:
            include_relationships: If True, include ingredient info

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        if include_relationships and self.ingredient:
            result["ingredient"] = {
                "id": self.ingredient.id,
                "display_name": self.ingredient.display_name,
            }

        return result
