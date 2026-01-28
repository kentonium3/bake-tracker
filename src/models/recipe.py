"""
Recipe models for baking recipes.

This module contains:
- Recipe: Main recipe model with metadata
- RecipeIngredient: Junction table linking recipes to ingredients
- RecipeComponent: Junction table linking parent recipes to child (component) recipes

Feature 037: Added variant support (base_recipe_id, variant_name) and
production readiness (is_production_ready) fields.

Feature 080: Added slug and previous_slug for portable identification.
"""

import re
import unicodedata
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
    event,
)
from sqlalchemy.orm import relationship, validates

from .base import BaseModel
from src.utils.datetime_utils import utc_now


def _generate_recipe_slug(name: str) -> str:
    """Generate a URL-safe slug from recipe name.

    Args:
        name: Recipe name to convert to slug

    Returns:
        Lowercase slug with hyphens, alphanumeric only
    """
    if not name:
        return "unknown-recipe"

    # Normalize unicode characters (handles accents like e -> e)
    slug = unicodedata.normalize("NFKD", name)
    slug = slug.encode("ascii", "ignore").decode("ascii")

    # Convert to lowercase
    slug = slug.lower()

    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)

    # Remove non-alphanumeric characters (except hyphens)
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Ensure not empty
    if not slug:
        return "unknown-recipe"

    # Limit length (200 chars)
    if len(slug) > 200:
        slug = slug[:200].rstrip("-")

    return slug


class Recipe(BaseModel):
    """
    Recipe model representing baking recipes.

    Attributes:
        name: Recipe name (required)
        category: Recipe category (e.g., "Cookies", "Cakes")
        source: Where recipe came from
        estimated_time_minutes: Prep + bake time in minutes
        notes: Additional notes
        is_archived: Whether the recipe is archived (soft delete)
        date_added: When recipe was added
        last_modified: Last modification timestamp

    Note: Yield information (quantity, unit, description) was removed in F056.
    Use FinishedUnit records for yield data instead.
    """

    __tablename__ = "recipes"

    # Basic information
    name = Column(String(200), nullable=False, index=True)
    # Feature 080: Portable identifier for export/import
    slug = Column(
        String(200),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique human-readable identifier for export/import portability",
    )
    # Feature 080: Previous slug for one-rename grace period
    previous_slug = Column(
        String(200),
        nullable=True,
        index=True,
        comment="Previous slug retained after rename for import compatibility",
    )
    category = Column(String(100), nullable=False, index=True)
    source = Column(String(500), nullable=True)

    # Time and notes
    estimated_time_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    # Archival status (for soft delete)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)

    # Feature 037: Variant support
    # Self-referential FK for variant relationships (e.g., "Raspberry Thumbprint" -> "Thumbprint Cookies")
    base_recipe_id = Column(
        Integer,
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    variant_name = Column(String(100), nullable=True)  # e.g., "Raspberry", "Strawberry"

    # Feature 037: Production readiness flag
    # New recipes default to experimental (False), user marks as ready for production
    is_production_ready = Column(Boolean, nullable=False, default=False, index=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=utc_now)
    last_modified = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

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

    # Feature 037: Variant relationships (self-referential)
    base_recipe = relationship(
        "Recipe",
        remote_side="Recipe.id",
        foreign_keys=[base_recipe_id],
        backref="variants",
    )

    # Feature 037: Snapshot relationships
    snapshots = relationship("RecipeSnapshot", back_populates="recipe")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_recipe_name", "name"),
        Index("idx_recipe_category", "category"),
        # Feature 080: Slug indexes for portable identification
        Index("idx_recipe_slug", "slug", unique=True),
        Index("idx_recipe_previous_slug", "previous_slug"),
        # Feature 037: Prevent self-referential variants
        CheckConstraint(
            "base_recipe_id IS NULL OR base_recipe_id != id",
            name="ck_recipe_no_self_variant",
        ),
    )

    @validates("slug")
    def validate_slug(self, key, value):
        """Validate and normalize slug format.

        Feature 080: Ensures slugs conform to expected format:
        - Lowercase
        - Alphanumeric and hyphens only
        - Max 200 characters

        Args:
            key: The attribute name ('slug')
            value: The slug value to validate

        Returns:
            Normalized slug value
        """
        if value is None:
            return value  # Allow None during construction, event listener will populate

        # Check format: lowercase, alphanumeric, hyphens only
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", value):
            # Auto-normalize if invalid
            normalized = re.sub(r"[^\w\s-]", "", value.lower())
            normalized = re.sub(r"[\s_]+", "-", normalized).strip("-")
            return normalized or "recipe"

        # Check length
        if len(value) > 200:
            return value[:200].rstrip("-")

        return value

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
        Calculate cost per unit of yield using FinishedUnit data.

        Returns:
            Cost per unit (total_cost / items_per_batch of primary FinishedUnit)

        Note: Returns 0.0 if no FinishedUnits exist or items_per_batch is 0.
        """
        total_cost = self.calculate_cost()
        # Use the first FinishedUnit's items_per_batch for cost calculation
        if self.finished_units:
            primary_unit = self.finished_units[0]
            if primary_unit.items_per_batch and primary_unit.items_per_batch > 0:
                return total_cost / primary_unit.items_per_batch
        return 0.0

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
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
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


# Feature 080: Event listener for auto-generating recipe slugs
@event.listens_for(Recipe, "before_insert")
def _generate_recipe_slug_on_insert(mapper, connection, target):
    """Auto-generate slug before insert if not provided.

    This ensures every recipe has a slug for portable identification.
    The slug is generated from the recipe name using lowercase, hyphens,
    and alphanumeric characters only.

    Note: This provides basic slug generation. For unique slug generation
    with collision handling, use RecipeService._generate_unique_slug().
    """
    if not target.slug and target.name:
        target.slug = _generate_recipe_slug(target.name)
