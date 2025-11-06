"""
Product model for generic ingredient definitions.

This model represents the "platonic ideal" of an ingredient - the generic
concept without brand, package, or inventory specifics.

Example: "All-Purpose Flour" as a product concept, separate from
         "King Arthur All-Purpose Flour 25 lb bag" (which is a ProductVariant)
"""

from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class Product(BaseModel):
    """
    Product model representing generic ingredient definitions.

    This is the base catalog entry for an ingredient type. Multiple
    ProductVariants (brands, package sizes) can exist for each Product.

    Attributes:
        name: Product name (e.g., "All-Purpose Flour", "White Granulated Sugar")
        category: Category (e.g., "Flour", "Sugar", "Dairy")
        recipe_unit: Default unit for recipes (e.g., "cup", "oz", "g")
        description: Optional detailed description
        notes: Additional notes
        date_added: When product was created
        last_modified: Last modification timestamp
    """

    __tablename__ = "products"

    # Basic information
    name = Column(String(200), nullable=False, unique=True, index=True)
    category = Column(String(100), nullable=False, index=True)
    recipe_unit = Column(String(50), nullable=False)  # Default unit for recipes

    # Additional information
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    variants = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="select"
    )
    conversions = relationship(
        "UnitConversion",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="select"
    )
    recipe_ingredients = relationship(
        "RecipeIngredient",
        back_populates="product",
        lazy="select"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_product_name", "name"),
        Index("idx_product_category", "category"),
    )

    def __repr__(self) -> str:
        """String representation of product."""
        return f"Product(id={self.id}, name='{self.name}', category='{self.category}')"

    def get_preferred_variant(self):
        """
        Get the preferred variant for this product.

        Returns:
            ProductVariant marked as preferred, or None if no preference set
        """
        for variant in self.variants:
            if variant.preferred:
                return variant
        return None

    def get_all_variants(self):
        """
        Get all variants for this product.

        Returns:
            List of ProductVariant instances
        """
        return self.variants

    def get_total_pantry_quantity(self):
        """
        Get total quantity across all pantry items for this product.

        Aggregates across all variants and converts to recipe_unit.

        Returns:
            Total quantity in recipe units
        """
        total = 0.0
        for variant in self.variants:
            for pantry_item in variant.pantry_items:
                # Convert pantry item quantity to recipe units
                # TODO: Implement conversion logic
                total += pantry_item.quantity
        return total

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert product to dictionary.

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
