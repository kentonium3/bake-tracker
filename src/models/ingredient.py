"""
Ingredient model for raw materials and supplies.

This model represents ingredients used in recipes, including:
- Basic information (name, brand, category)
- Purchase and recipe units with conversion factors
- Inventory tracking (quantity, cost)
- Timestamps and notes
"""

from datetime import datetime

from sqlalchemy import Column, String, Float, Text, DateTime, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class Ingredient(BaseModel):
    """
    Ingredient model representing raw materials and supplies.

    Attributes:
        name: Ingredient name (required)
        brand: Brand or supplier name
        category: Category (e.g., "Flour/Grains", "Sugar/Sweeteners")
        purchase_unit: Unit purchased in (e.g., "bag", "lb")
        purchase_unit_size: Size description (e.g., "50 lb")
        recipe_unit: Optional default unit hint for recipes (e.g., "cup", "oz")
        conversion_factor: Purchase units to recipe units (e.g., 200 = 1 bag = 200 cups)
        density_g_per_cup: Density in grams per cup for volume-weight conversions
        quantity: Current quantity in purchase units
        unit_cost: Cost per purchase unit
        last_updated: Last modification timestamp
        notes: Additional notes
    """

    __tablename__ = "ingredients"

    # Basic information
    name = Column(String(200), nullable=False, index=True)
    brand = Column(String(200), nullable=True)
    category = Column(String(100), nullable=False, index=True)

    # Unit information
    purchase_unit = Column(String(50), nullable=False)
    purchase_unit_size = Column(String(100), nullable=True)
    recipe_unit = Column(String(50), nullable=True)  # Optional: used as default unit hint
    conversion_factor = Column(Float, nullable=False)

    # Density for volume-weight conversions (grams per cup)
    density_g_per_cup = Column(Float, nullable=True)

    # Inventory tracking
    quantity = Column(Float, nullable=False, default=0.0)
    unit_cost = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Additional information
    notes = Column(Text, nullable=True)

    # Relationships
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")
    snapshot_ingredients = relationship("SnapshotIngredient", back_populates="ingredient")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_ingredient_name", "name"),
        Index("idx_ingredient_category", "category"),
    )

    def __repr__(self) -> str:
        """String representation of ingredient."""
        return f"Ingredient(id={self.id}, name='{self.name}', brand='{self.brand}')"

    @property
    def total_value(self) -> float:
        """
        Calculate total inventory value.

        Returns:
            Total value (quantity × unit_cost)
        """
        return self.quantity * self.unit_cost

    @property
    def available_recipe_units(self) -> float:
        """
        Calculate available quantity in recipe units.

        Returns:
            Quantity in recipe units (quantity × conversion_factor)
        """
        return self.quantity * self.conversion_factor

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert ingredient to dictionary.

        Args:
            include_relationships: If True, include related objects

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["total_value"] = self.total_value
        result["available_recipe_units"] = self.available_recipe_units

        return result

    def convert_to_recipe_units(self, purchase_unit_quantity: float) -> float:
        """
        Convert a quantity from purchase units to recipe units.

        Args:
            purchase_unit_quantity: Quantity in purchase units

        Returns:
            Quantity in recipe units
        """
        return purchase_unit_quantity * self.conversion_factor

    def convert_from_recipe_units(self, recipe_unit_quantity: float) -> float:
        """
        Convert a quantity from recipe units to purchase units.

        Args:
            recipe_unit_quantity: Quantity in recipe units

        Returns:
            Quantity in purchase units
        """
        return recipe_unit_quantity / self.conversion_factor

    def get_cost_per_recipe_unit(self) -> float:
        """
        Calculate cost per recipe unit.

        Returns:
            Cost per recipe unit
        """
        if self.conversion_factor == 0:
            return 0.0
        return self.unit_cost / self.conversion_factor

    def update_quantity(self, new_quantity: float) -> None:
        """
        Update ingredient quantity and timestamp.

        Args:
            new_quantity: New quantity value
        """
        self.quantity = new_quantity
        self.last_updated = datetime.utcnow()

    def adjust_quantity(self, adjustment: float) -> None:
        """
        Adjust ingredient quantity by a delta amount.

        Args:
            adjustment: Amount to add (positive) or subtract (negative)
        """
        self.quantity += adjustment
        self.last_updated = datetime.utcnow()

    def get_density(self) -> float:
        """
        Get ingredient density (grams per cup).

        Returns stored density if available, otherwise looks up from constants.

        Returns:
            Density in grams per cup, or 0.0 if not available
        """
        if self.density_g_per_cup is not None and self.density_g_per_cup > 0:
            return self.density_g_per_cup

        # Fallback to constants lookup
        from src.utils.constants import get_ingredient_density
        return get_ingredient_density(self.name)

    def has_density_data(self) -> bool:
        """
        Check if ingredient has density data available for volume-weight conversions.

        Returns:
            True if density data is available
        """
        return self.get_density() > 0.0
