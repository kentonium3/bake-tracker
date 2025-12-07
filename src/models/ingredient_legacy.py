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


class IngredientLegacy(BaseModel):
    """
    LEGACY Ingredient model for migration compatibility.

    This model represents the old ingredient structure before the Ingredient/Product refactoring.
    After migration is complete, this model and table will be removed.

    Attributes:
        name: Ingredient name (required)
        brand: Brand or supplier name
        category: Category (e.g., "Flour/Grains", "Sugar/Sweeteners")
        package_type: Optional package descriptor (e.g., "bag", "box", "bar")
        purchase_quantity: Quantity per package (e.g., 25)
        purchase_unit: Standard unit (e.g., "lb", "oz", "kg", "g")
        density_g_per_cup: Density in grams per cup for volume-weight conversions
        quantity: Current inventory quantity in packages
        unit_cost: Cost per package
        last_updated: Last modification timestamp
        notes: Additional notes
    """

    __tablename__ = "ingredients"

    # Basic information
    name = Column(String(200), nullable=False, index=True)
    brand = Column(String(200), nullable=True)
    category = Column(String(100), nullable=False, index=True)

    # Purchase information
    package_type = Column(String(50), nullable=True)  # Optional: bag, box, bar, etc.
    purchase_quantity = Column(Float, nullable=False)  # Quantity per package
    purchase_unit = Column(String(50), nullable=False)  # Standard unit: lb, oz, kg, g, etc.

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
        return f"IngredientLegacy(id={self.id}, name='{self.name}', brand='{self.brand}')"

    @property
    def total_value(self) -> float:
        """
        Calculate total inventory value.

        Returns:
            Total value (quantity × unit_cost)
        """
        return self.quantity * self.unit_cost

    @property
    def total_quantity_in_purchase_units(self) -> float:
        """
        Calculate total inventory in purchase units.

        Returns:
            Total quantity in purchase units (quantity × purchase_quantity)
        """
        return self.quantity * self.purchase_quantity

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
        result["total_quantity_in_purchase_units"] = self.total_quantity_in_purchase_units

        return result

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

        # DEPRECATED: Fallback removed in Feature 010. Now returns 0.0 if not set.
        return 0.0

    def has_density_data(self) -> bool:
        """
        Check if ingredient has density data available for volume-weight conversions.

        Returns:
            True if density data is available
        """
        return self.get_density() > 0.0
