"""
Recipe models for baking recipes.

This module contains:
- Recipe: Main recipe model with metadata
- RecipeIngredient: Junction table linking recipes to ingredients
"""

from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class Recipe(BaseModel):
    """
    Recipe model representing baking recipes.

    Attributes:
        name: Recipe name (required)
        category: Recipe category (e.g., "Cookies", "Cakes")
        source: Where recipe came from
        yield_quantity: Number of items produced
        yield_unit: Unit of yield (e.g., "cookies", "servings")
        yield_description: Description of yield (e.g., "2-inch cookies")
        estimated_time_minutes: Prep + bake time in minutes
        notes: Additional notes
        date_added: When recipe was added
        last_modified: Last modification timestamp
    """

    __tablename__ = "recipes"

    # Basic information
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    source = Column(String(500), nullable=True)

    # Yield information
    yield_quantity = Column(Float, nullable=False)
    yield_unit = Column(String(50), nullable=False)
    yield_description = Column(String(200), nullable=True)

    # Time and notes
    estimated_time_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    recipe_ingredients = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    finished_goods = relationship("FinishedGood", back_populates="recipe")

    # Indexes
    __table_args__ = (
        Index("idx_recipe_name", "name"),
        Index("idx_recipe_category", "category"),
    )

    def __repr__(self) -> str:
        """String representation of recipe."""
        return f"Recipe(id={self.id}, name='{self.name}', category='{self.category}')"

    def calculate_cost(self) -> float:
        """
        Calculate total recipe cost based on ingredient costs.

        Uses each RecipeIngredient's calculate_cost() which handles
        unit conversions and density-based calculations.

        Returns:
            Total cost of all ingredients in the recipe
        """
        total_cost = 0.0
        for recipe_ingredient in self.recipe_ingredients:
            total_cost += recipe_ingredient.calculate_cost()
        return total_cost

    def get_cost_per_unit(self) -> float:
        """
        Calculate cost per unit of yield.

        Returns:
            Cost per unit (total_cost / yield_quantity)
        """
        total_cost = self.calculate_cost()
        if self.yield_quantity == 0:
            return 0.0
        return total_cost / self.yield_quantity

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert recipe to dictionary.

        Args:
            include_relationships: If True, include ingredients

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["total_cost"] = self.calculate_cost()
        result["cost_per_unit"] = self.get_cost_per_unit()

        return result


class RecipeIngredient(BaseModel):
    """
    Junction table linking recipes to ingredients/products with quantities.

    This model represents an ingredient used in a recipe with specific
    quantity and unit requirements.

    MIGRATION NOTE: During refactoring, both ingredient_id (old) and product_id (new)
    exist. After migration, ingredient_id will be removed.

    Attributes:
        recipe_id: Foreign key to Recipe
        ingredient_id: Foreign key to Ingredient (LEGACY - for migration only)
        product_id: Foreign key to Product (NEW - brand-agnostic reference)
        quantity: Amount needed (in product's recipe_unit)
        unit: Unit of measurement (must match product's recipe_unit)
        notes: Optional notes (e.g., "sifted", "melted")
    """

    __tablename__ = "recipe_ingredients"

    # Foreign keys
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)

    # LEGACY: ingredient_id for backward compatibility during migration
    ingredient_id = Column(
        Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=True
    )

    # NEW: product_id for brand-agnostic recipe ingredients
    product_id = Column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=True
    )

    # Quantity information
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)

    # Additional information
    notes = Column(String(500), nullable=True)

    # Relationships
    recipe = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient = relationship("Ingredient")  # LEGACY - for migration only
    product = relationship("Product", back_populates="recipe_ingredients")  # NEW

    # Indexes
    __table_args__ = (
        Index("idx_recipe_ingredient_recipe", "recipe_id"),
        Index("idx_recipe_ingredient_ingredient", "ingredient_id"),
    )

    def __repr__(self) -> str:
        """String representation of recipe ingredient."""
        return (
            f"RecipeIngredient(recipe_id={self.recipe_id}, "
            f"ingredient_id={self.ingredient_id}, "
            f"quantity={self.quantity}, unit='{self.unit}')"
        )

    def calculate_cost(self) -> float:
        """
        Calculate cost of this ingredient in the recipe.

        This method handles conversion from any recipe unit to the ingredient's
        purchase units, supporting cross-unit conversions (volume↔weight) when needed.

        Returns:
            Cost of this ingredient for the recipe
        """
        if not self.ingredient:
            return 0.0

        # Import here to avoid circular import
        from src.services.unit_converter import convert_any_units

        # Get ingredient density for cross-unit conversions
        ingredient_density = self.ingredient.get_density() if hasattr(self.ingredient, 'get_density') else 0.0

        # Convert recipe unit to purchase_unit
        success, quantity_in_purchase_units, error = convert_any_units(
            self.quantity,
            self.unit,
            self.ingredient.purchase_unit,
            ingredient_name=self.ingredient.name,
            density_override=ingredient_density if ingredient_density > 0 else None,
        )

        if not success:
            # Conversion failed - cannot calculate cost
            return 0.0

        # Calculate how many packages needed
        packages_needed = quantity_in_purchase_units / self.ingredient.purchase_quantity

        # Calculate cost
        cost = packages_needed * self.ingredient.unit_cost

        return cost

    def get_purchase_unit_quantity(self) -> float:
        """
        Calculate how many purchase units (in standard units) are needed.

        This method handles conversion from any recipe unit to purchase units,
        supporting cross-unit conversions (volume↔weight) when needed.

        Returns:
            Quantity in purchase units (not packages)
        """
        if not self.ingredient:
            return 0.0

        # Import here to avoid circular import
        from src.services.unit_converter import convert_any_units

        # Get ingredient density for cross-unit conversions
        ingredient_density = self.ingredient.get_density() if hasattr(self.ingredient, 'get_density') else 0.0

        # Convert recipe unit to purchase_unit
        success, quantity_in_purchase_units, error = convert_any_units(
            self.quantity,
            self.unit,
            self.ingredient.purchase_unit,
            ingredient_name=self.ingredient.name,
            density_override=ingredient_density if ingredient_density > 0 else None,
        )

        if not success:
            # Conversion failed
            return 0.0

        return quantity_in_purchase_units

    def get_packages_needed(self) -> float:
        """
        Calculate how many packages are needed for this ingredient.

        Returns:
            Number of packages needed
        """
        if not self.ingredient:
            return 0.0

        quantity_in_purchase_units = self.get_purchase_unit_quantity()
        return quantity_in_purchase_units / self.ingredient.purchase_quantity

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert recipe ingredient to dictionary.

        Args:
            include_relationships: If True, include ingredient details

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["cost"] = self.calculate_cost()
        result["purchase_unit_quantity"] = self.get_purchase_unit_quantity()

        return result
