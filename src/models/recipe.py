"""
Recipe models for baking recipes.

This module contains:
- Recipe: Main recipe model with metadata
- RecipeIngredient: Junction table linking recipes to ingredients
- RecipeComponent: Junction table linking parent recipes to child (component) recipes
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
    UniqueConstraint,
    Boolean,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


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
        is_archived: Whether the recipe is archived (soft delete)
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

    # Archival status (for soft delete)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=utc_now)
    last_modified = Column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    recipe_ingredients = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    finished_units = relationship("FinishedUnit", back_populates="recipe")

    # Production tracking (Feature 013)
    production_runs = relationship("ProductionRun", back_populates="recipe")

    # Recipe component relationships (nested recipes / sub-recipes)
    recipe_components = relationship(
        "RecipeComponent",
        foreign_keys="RecipeComponent.recipe_id",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    used_in_recipes = relationship(
        "RecipeComponent",
        foreign_keys="RecipeComponent.component_recipe_id",
        back_populates="component_recipe",
        lazy="select",  # Only load when accessed
    )

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
    Junction table linking recipes to ingredients with quantities.

    This model represents an ingredient used in a recipe with specific
    quantity and unit requirements.

    Attributes:
        recipe_id: Foreign key to Recipe
        ingredient_id: Foreign key to Ingredient (brand-agnostic reference)
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
    recipe = relationship("Recipe", back_populates="recipe_ingredients", lazy="joined")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients", lazy="joined")

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

        Note: Cost calculation requires the ingredient to have an associated
        preferred product with purchase history. Returns 0.0 if no cost data
        is available.

        Returns:
            Cost of this ingredient for the recipe
        """
        if not self.ingredient:
            return 0.0

        # Get preferred product for cost calculation
        preferred_product = self.ingredient.get_preferred_product()
        if not preferred_product:
            return 0.0

        # Import here to avoid circular import
        from src.services.unit_converter import convert_any_units

        package_unit = preferred_product.package_unit
        if not package_unit:
            return 0.0

        # Convert recipe unit to package_unit
        success, quantity_in_package_units, error = convert_any_units(
            self.quantity,
            self.unit,
            package_unit,
            ingredient=self.ingredient,
        )

        if not success:
            return 0.0

        # Calculate how many packages needed
        if preferred_product.package_unit_quantity == 0:
            return 0.0
        packages_needed = quantity_in_package_units / preferred_product.package_unit_quantity

        # Calculate cost
        unit_cost = preferred_product.get_current_cost_per_unit()
        cost = packages_needed * unit_cost

        return cost

    def get_package_unit_quantity(self) -> float:
        """
        Calculate how many package units (in standard units) are needed.

        This method handles conversion from any recipe unit to package units,
        supporting cross-unit conversions (volume↔weight) when needed.

        Returns:
            Quantity in package units (not packages)
        """
        if not self.ingredient:
            return 0.0

        # Get preferred product for unit information
        preferred_product = self.ingredient.get_preferred_product()
        if not preferred_product:
            return 0.0

        # Import here to avoid circular import
        from src.services.unit_converter import convert_any_units

        package_unit = preferred_product.package_unit
        if not package_unit:
            return 0.0

        # Convert recipe unit to package_unit
        success, quantity_in_package_units, error = convert_any_units(
            self.quantity,
            self.unit,
            package_unit,
            ingredient=self.ingredient,
        )

        if not success:
            return 0.0

        return quantity_in_package_units

    def get_packages_needed(self) -> float:
        """
        Calculate how many packages are needed for this ingredient.

        Returns:
            Number of packages needed
        """
        if not self.ingredient:
            return 0.0

        preferred_product = self.ingredient.get_preferred_product()
        if not preferred_product or preferred_product.package_unit_quantity == 0:
            return 0.0

        quantity_in_package_units = self.get_package_unit_quantity()
        return quantity_in_package_units / preferred_product.package_unit_quantity

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
        result["package_unit_quantity"] = self.get_package_unit_quantity()

        return result


class RecipeComponent(BaseModel):
    """
    Junction table linking parent recipes to child (component) recipes.

    This model enables hierarchical recipe structures where a recipe can contain
    other recipes as components (e.g., "Frosted Layer Cake" includes "Chocolate Cake",
    "Vanilla Cake", and "Buttercream Frosting" recipes).

    Attributes:
        recipe_id: Foreign key to parent Recipe (the recipe containing sub-recipes)
        component_recipe_id: Foreign key to child Recipe (the sub-recipe being included)
        quantity: Batch multiplier (e.g., 2.0 = 2 batches of the sub-recipe)
        notes: Optional notes for this component usage (e.g., "prepare day before")
        sort_order: Display order within parent recipe
    """

    __tablename__ = "recipe_components"

    # Foreign keys
    recipe_id = Column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    component_recipe_id = Column(
        Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False
    )

    # Component attributes
    quantity = Column(Float, nullable=False, default=1.0)
    notes = Column(String(500), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)

    # Relationships
    recipe = relationship(
        "Recipe",
        foreign_keys=[recipe_id],
        back_populates="recipe_components",
        lazy="joined",
    )
    component_recipe = relationship(
        "Recipe",
        foreign_keys=[component_recipe_id],
        back_populates="used_in_recipes",
        lazy="joined",
    )

    # Constraints and indexes
    __table_args__ = (
        # Constraints
        CheckConstraint("quantity > 0", name="ck_recipe_component_quantity_positive"),
        CheckConstraint(
            "recipe_id != component_recipe_id",
            name="ck_recipe_component_no_self_reference",
        ),
        UniqueConstraint(
            "recipe_id",
            "component_recipe_id",
            name="uq_recipe_component_recipe_component",
        ),
        # Indexes
        Index("idx_recipe_component_recipe", "recipe_id"),
        Index("idx_recipe_component_component", "component_recipe_id"),
        Index("idx_recipe_component_sort", "recipe_id", "sort_order"),
    )

    def __repr__(self) -> str:
        """String representation of recipe component."""
        return (
            f"RecipeComponent(recipe_id={self.recipe_id}, "
            f"component_recipe_id={self.component_recipe_id}, "
            f"quantity={self.quantity})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert recipe component to dictionary.

        Args:
            include_relationships: If True, include component recipe details

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Add component recipe name if available
        if self.component_recipe:
            result["component_recipe_name"] = self.component_recipe.name

        return result
