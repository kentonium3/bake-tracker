"""
Ingredient model for generic ingredient definitions.

This model represents the "platonic ideal" of an ingredient - the generic
concept without brand, package, or inventory specifics.

Example: "All-Purpose Flour" as an ingredient concept, separate from
         "King Arthur All-Purpose Flour 25 lb bag" (which is a Variant)
"""

from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Float, JSON, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class Ingredient(BaseModel):
    """
    Ingredient model representing generic ingredient definitions.

    This is the base catalog entry for an ingredient type. Multiple
    Variants (brands, package sizes) can exist for each Ingredient.

    Attributes:
        name: Ingredient name (e.g., "All-Purpose Flour", "White Granulated Sugar")
        slug: URL-friendly identifier (e.g., "all_purpose_flour")
        category: Category (e.g., "Flour", "Sugar", "Dairy")
        recipe_unit: Unit used in recipes (e.g., "cup", "oz", "g")
        description: Optional detailed description
        notes: Additional notes

        # Industry standard identifiers (future-ready, nullable):
        foodon_id: FoodOn ontology ID (e.g., "FOODON:03309942")
        foodex2_code: EU FoodEx2 code for regulatory purposes
        langual_terms: List of LanguaL facet codes for descriptive classification
        fdc_ids: List of USDA FDC IDs for nutrition data linkage

        # Physical properties (future-ready, nullable):
        density_g_per_ml: Density in grams per milliliter for volume-weight conversions
        moisture_pct: Moisture percentage for advanced baking calculations
        allergens: List of allergen codes (e.g., ["gluten", "tree_nut"])

        date_added: When ingredient was created
        last_modified: Last modification timestamp
    """

    __tablename__ = "products"

    # Basic information (REQUIRED NOW)
    name = Column(String(200), nullable=False, unique=True, index=True)
    slug = Column(
        String(200), nullable=True, unique=True, index=True
    )  # Will be required after migration
    category = Column(String(100), nullable=False, index=True)
    recipe_unit = Column(String(50), nullable=True)  # Unit used in recipes (e.g., "cup", "oz", "g")

    # Additional information
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Industry standard identifiers (FUTURE READY - all nullable)
    foodon_id = Column(String(50), nullable=True, index=True)  # Primary external ID
    foodex2_code = Column(String(50), nullable=True)  # EU regulatory code
    langual_terms = Column(JSON, nullable=True)  # Array of LanguaL facet codes
    fdc_ids = Column(JSON, nullable=True)  # Array of USDA FDC IDs

    # Physical properties (FUTURE READY - all nullable)
    density_g_per_ml = Column(Float, nullable=True)  # For volume-weight conversions
    moisture_pct = Column(Float, nullable=True)  # For advanced calculations
    allergens = Column(JSON, nullable=True)  # Array of allergen codes

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    variants = relationship(
        "Variant", back_populates="ingredient", cascade="all, delete-orphan", lazy="select"
    )
    conversions = relationship(
        "UnitConversion", back_populates="ingredient", cascade="all, delete-orphan", lazy="select"
    )
    recipe_ingredients = relationship(
        "RecipeIngredient", back_populates="ingredient_new", lazy="select"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_product_name", "name"),
        Index("idx_product_category", "category"),
    )

    def __repr__(self) -> str:
        """String representation of ingredient."""
        return f"Ingredient(id={self.id}, name='{self.name}', category='{self.category}')"

    def get_preferred_variant(self):
        """
        Get the preferred variant for this ingredient.

        Returns:
            Variant marked as preferred, or None if no preference set
        """
        for variant in self.variants:
            if variant.preferred:
                return variant
        return None

    def get_all_variants(self):
        """
        Get all variants for this ingredient.

        Returns:
            List of Variant instances
        """
        return self.variants

    def get_total_pantry_quantity(self):
        """
        Get total quantity across all pantry items for this ingredient.

        Note: This returns quantities in their original units and should not
        be aggregated directly. Use pantry_service.get_total_quantity() for
        proper unit conversion and aggregation.

        Returns:
            Raw total without unit conversion (deprecated)
        """
        total = 0.0
        for variant in self.variants:
            for pantry_item in variant.pantry_items:
                # Note: Raw quantity addition without unit conversion
                total += pantry_item.quantity
        return total

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert ingredient to dictionary.

        Args:
            include_relationships: If True, include variants and conversions

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        if include_relationships:
            result["variants"] = [v.to_dict(False) for v in self.variants]
            result["conversions"] = [c.to_dict(False) for c in self.conversions]
            result["preferred_variant_id"] = (
                self.get_preferred_variant().id if self.get_preferred_variant() else None
            )

        return result
