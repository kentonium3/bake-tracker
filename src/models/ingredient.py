"""
Ingredient model for generic ingredient definitions.

This model represents the "platonic ideal" of an ingredient - the generic
concept without brand, package, or inventory specifics.

Example: "All-Purpose Flour" as an ingredient concept, separate from
         "King Arthur All-Purpose Flour 25 lb bag" (which is a Product)
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Text, DateTime, Float, JSON, Index, Boolean,
    Integer, ForeignKey, CheckConstraint
)
from sqlalchemy.orm import relationship, backref

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class Ingredient(BaseModel):
    """
    Ingredient model representing generic ingredient definitions.

    This is the base catalog entry for an ingredient type. Multiple
    Products (brands, package sizes) can exist for each Ingredient.

    Ingredients are organized in a three-tier hierarchy (Feature 031):
    - Level 0 (root): Top-level categories (e.g., "Chocolate")
    - Level 1 (mid): Sub-categories (e.g., "Dark Chocolate")
    - Level 2 (leaf): Specific ingredients usable in recipes (e.g., "Semi-Sweet Chips")

    Only leaf ingredients (level 2) can have Products or be used in Recipes.

    Attributes:
        display_name: Ingredient name (e.g., "All-Purpose Flour", "White Granulated Sugar")
        slug: URL-friendly identifier (e.g., "all_purpose_flour")
        parent_ingredient_id: FK to parent ingredient (None for root ingredients)
        hierarchy_level: Position in hierarchy (0=root, 1=mid, 2=leaf)
        category: Category (deprecated, retained for rollback safety)
        description: Optional detailed description
        notes: Additional notes

        # Industry standard identifiers (future-ready, nullable):
        foodon_id: FoodOn ontology ID (e.g., "FOODON:03309942")
        foodex2_code: EU FoodEx2 code for regulatory purposes
        langual_terms: List of LanguaL facet codes for descriptive classification
        fdc_ids: List of USDA FDC IDs for nutrition data linkage

        # User-friendly density specification (4-field model):
        density_volume_value: Volume amount for density (e.g., 1.0)
        density_volume_unit: Volume unit for density (e.g., "cup")
        density_weight_value: Weight amount for density (e.g., 4.25)
        density_weight_unit: Weight unit for density (e.g., "oz")
        Example: "1 cup = 4.25 oz" stored as (1.0, "cup", 4.25, "oz")

        # Physical properties (future-ready, nullable):
        moisture_pct: Moisture percentage for advanced baking calculations
        allergens: List of allergen codes (e.g., ["gluten", "tree_nut"])

        date_added: When ingredient was created
        last_modified: Last modification timestamp
    """

    __tablename__ = "ingredients"

    # Basic information (REQUIRED NOW)
    display_name = Column(String(200), nullable=False, unique=True, index=True)
    slug = Column(
        String(200), nullable=True, unique=True, index=True
    )  # Will be required after migration

    # Hierarchy fields (Feature 031)
    # parent_ingredient_id enables self-referential parent-child relationships
    # Nullable to support root ingredients (level 0) which have no parent
    parent_ingredient_id = Column(
        Integer, ForeignKey("ingredients.id"), nullable=True, index=True
    )
    # hierarchy_level: 0=root category, 1=mid-tier category, 2=leaf (usable in recipes)
    # Default=2 ensures existing ingredients become leaves
    hierarchy_level = Column(Integer, nullable=False, default=2)

    # category field retained for rollback safety (deprecated - use hierarchy instead)
    category = Column(String(100), nullable=False, index=True)

    # Packaging indicator (Feature 011)
    is_packaging = Column(Boolean, nullable=False, default=False, index=True)

    # Additional information
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Industry standard identifiers (FUTURE READY - all nullable)
    foodon_id = Column(String(50), nullable=True, index=True)  # Primary external ID
    foodex2_code = Column(String(50), nullable=True)  # EU regulatory code
    langual_terms = Column(JSON, nullable=True)  # Array of LanguaL facet codes
    fdc_ids = Column(JSON, nullable=True)  # Array of USDA FDC IDs

    # User-friendly density specification (4-field model)
    # Example: "1 cup = 4.25 oz" stored as (1.0, "cup", 4.25, "oz")
    density_volume_value = Column(Float, nullable=True)
    density_volume_unit = Column(String(20), nullable=True)
    density_weight_value = Column(Float, nullable=True)
    density_weight_unit = Column(String(20), nullable=True)

    # Physical properties (FUTURE READY - all nullable)
    moisture_pct = Column(Float, nullable=True)  # For advanced calculations
    allergens = Column(JSON, nullable=True)  # Array of allergen codes

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=utc_now)
    last_modified = Column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    products = relationship(
        "Product", back_populates="ingredient", cascade="all, delete-orphan", lazy="select"
    )
    recipe_ingredients = relationship(
        "RecipeIngredient", back_populates="ingredient", lazy="select"
    )

    # Self-referential relationship for ingredient hierarchy (Feature 031)
    # children: Query direct child ingredients of this parent
    # parent: Access the parent ingredient (backref creates this automatically)
    # lazy='dynamic' allows filtering children without loading all
    children = relationship(
        "Ingredient",
        backref=backref("parent", remote_side="Ingredient.id"),
        lazy="dynamic",
        foreign_keys=[parent_ingredient_id],
    )

    # Indexes for common queries and hierarchy constraints
    __table_args__ = (
        Index("idx_ingredient_display_name", "display_name"),
        Index("idx_ingredient_category", "category"),
        Index("idx_ingredient_is_packaging", "is_packaging"),
        # Hierarchy indexes for tree traversal performance (Feature 031)
        Index("idx_ingredient_parent", "parent_ingredient_id"),
        Index("idx_ingredient_hierarchy_level", "hierarchy_level"),
        # CHECK constraint ensures hierarchy_level is valid (0=root, 1=mid, 2=leaf)
        CheckConstraint("hierarchy_level IN (0, 1, 2)", name="ck_ingredient_hierarchy_level"),
    )

    def __repr__(self) -> str:
        """String representation of ingredient."""
        return f"Ingredient(id={self.id}, display_name='{self.display_name}', category='{self.category}')"

    def get_preferred_product(self):
        """
        Get the preferred product for this ingredient.

        Returns:
            Product marked as preferred, or None if no preference set
        """
        for product in self.products:
            if product.preferred:
                return product
        return None

    def get_all_products(self):
        """
        Get all products for this ingredient.

        Returns:
            List of Product instances
        """
        return self.products

    def get_total_inventory_quantity(self):
        """
        Get total quantity across all inventory items for this ingredient.

        Note: This returns quantities in their original units and should not
        be aggregated directly. Use inventory_item_service.get_total_quantity() for
        proper unit conversion and aggregation.

        Returns:
            Raw total without unit conversion (deprecated)
        """
        total = 0.0
        for product in self.products:
            for inventory_item in product.inventory_items:
                # Note: Raw quantity addition without unit conversion
                total += inventory_item.quantity
        return total

    def get_density_g_per_ml(self) -> Optional[float]:
        """
        Calculate density in g/ml from the 4-field specification.

        Returns:
            Density in grams per milliliter, or None if density not specified.
        """
        if not all([
            self.density_volume_value,
            self.density_volume_unit,
            self.density_weight_value,
            self.density_weight_unit
        ]):
            return None

        # Local import to avoid circular dependency
        from src.services.unit_converter import convert_standard_units

        # Convert volume to ml
        success, ml, _ = convert_standard_units(
            self.density_volume_value,
            self.density_volume_unit,
            "ml"
        )
        if not success or ml <= 0:
            return None

        # Convert weight to grams
        success, grams, _ = convert_standard_units(
            self.density_weight_value,
            self.density_weight_unit,
            "g"
        )
        if not success or grams <= 0:
            return None

        return grams / ml

    def format_density_display(self) -> str:
        """Format density for UI display."""
        if not self.get_density_g_per_ml():
            return "Not set"
        return (
            f"{self.density_volume_value:g} {self.density_volume_unit} = "
            f"{self.density_weight_value:g} {self.density_weight_unit}"
        )

    # =========================================================================
    # Hierarchy Methods (Feature 031)
    # =========================================================================

    @property
    def is_leaf(self) -> bool:
        """
        Check if this ingredient is a leaf (usable in recipes/products).

        Returns:
            True if hierarchy_level == 2 (leaf), False otherwise
        """
        return self.hierarchy_level == 2

    def get_ancestors(self) -> list:
        """
        Get path from this ingredient to the root (for breadcrumb display).

        Returns:
            List of ancestor Ingredient objects, ordered from immediate parent to root.
            Empty list if this is a root ingredient.
        """
        ancestors = []
        current = self.parent
        while current is not None:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_descendants(self) -> list:
        """
        Get all descendants (recursive) of this ingredient.

        Returns:
            List of all descendant Ingredient objects (all levels below this).
            Empty list if this is a leaf ingredient.
        """
        descendants = []
        self._collect_descendants(descendants)
        return descendants

    def _collect_descendants(self, descendants: list) -> None:
        """Recursively collect all descendants into the provided list."""
        # children is a dynamic relationship, need to call .all()
        for child in self.children.all():
            descendants.append(child)
            child._collect_descendants(descendants)

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert ingredient to dictionary.

        Args:
            include_relationships: If True, include products

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Add computed hierarchy property (Feature 031)
        # is_leaf indicates whether this ingredient can be used in recipes/products
        result["is_leaf"] = self.hierarchy_level == 2

        # Add computed density display for UI
        result["density_display"] = self.format_density_display()

        if include_relationships:
            result["products"] = [p.to_dict(False) for p in self.products]
            result["preferred_product_id"] = (
                self.get_preferred_product().id if self.get_preferred_product() else None
            )

        return result
