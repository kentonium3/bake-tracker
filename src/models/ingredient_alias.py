"""
IngredientAlias model for synonyms and multilingual ingredient names.

This model stores alternative names for ingredients to support:
- Autocomplete and search
- Regional/multilingual naming (e.g., "AP flour" vs "plain flour")
- Common abbreviations and nicknames
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class IngredientAlias(BaseModel):
    """
    IngredientAlias model for storing alternative names for ingredients.

    Supports synonyms, abbreviations, and multilingual names to improve
    search and autocomplete UX.

    Attributes:
        ingredient_id: Foreign key to Ingredient
        alias: Alternative name (e.g., "AP flour", "plain flour", "farine tout usage")
        locale: Optional locale code (e.g., "en-US", "en-GB", "fr-FR")
    """

    __tablename__ = "ingredient_aliases"

    # Foreign key to Ingredient
    ingredient_id = Column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Alias information
    alias = Column(String(200), nullable=False, index=True)  # Alternative name
    locale = Column(String(10), nullable=True)  # Optional locale (e.g., "en-US", "fr-FR")

    # Relationships
    # passive_deletes="all" lets database CASCADE handle deletion without ORM interference
    ingredient = relationship("Ingredient", backref="aliases", passive_deletes="all")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_alias_ingredient", "ingredient_id"),
        Index("idx_alias_name", "alias"),
        Index("idx_alias_locale", "locale"),
    )

    def __repr__(self) -> str:
        """String representation of alias."""
        locale_str = f" ({self.locale})" if self.locale else ""
        return f"IngredientAlias(id={self.id}, alias='{self.alias}'{locale_str})"

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert alias to dictionary.

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
