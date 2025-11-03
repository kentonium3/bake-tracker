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

    # finished_goods = relationship("FinishedGood", back_populates="recipe")

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

        Returns:
            Total cost of all ingredients in the recipe
        """
        total_cost = 0.0
        for recipe_ingredient in self.recipe_ingredients:
            ingredient = recipe_ingredient.ingredient
            if ingredient:
                # Cost = (unit_cost / conversion_factor) × recipe_quantity
                cost_per_recipe_unit = ingredient.get_cost_per_recipe_unit()
                ingredient_cost = cost_per_recipe_unit * recipe_ingredient.quantity
                total_cost += ingredient_cost
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
    Junction table linking recipes to ingredients with quantities.

    This model represents an ingredient used in a recipe with specific
    quantity and unit requirements.

    Attributes:
        recipe_id: Foreign key to Recipe
        ingredient_id: Foreign key to Ingredient
        quantity: Amount needed (in ingredient's recipe_unit)
        unit: Unit of measurement (must match ingredient's recipe_unit)
        notes: Optional notes (e.g., "sifted", "melted")
    """

    __tablename__ = "recipe_ingredients"

    # Foreign keys
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(
        Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )

    # Quantity information
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)

    # Additional information
    notes = Column(String(500), nullable=True)

    # Relationships
    recipe = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient = relationship("Ingredient")

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

        Returns:
            Cost of this ingredient for the recipe
        """
        if not self.ingredient:
            return 0.0

        cost_per_recipe_unit = self.ingredient.get_cost_per_recipe_unit()
        return cost_per_recipe_unit * self.quantity

    def get_purchase_unit_quantity(self) -> float:
        """
        Calculate how many purchase units are needed for this ingredient.

        Returns:
            Quantity in purchase units
        """
        if not self.ingredient:
            return 0.0

        return self.ingredient.convert_from_recipe_units(self.quantity)

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
