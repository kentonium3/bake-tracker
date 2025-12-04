"""
UnitConversion model for ingredient-specific unit conversions.

This model stores conversion factors between purchase units and recipe units
for each ingredient. Multiple conversions can exist per ingredient.

Example: All-Purpose Flour
- 1 lb = 3.6 cups (unsifted)
- 1 lb = 4.0 cups (sifted)
- 1 kg = 8 cups (approx)
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class UnitConversion(BaseModel):
    """
    UnitConversion model for ingredient-specific unit conversion factors.

    Each conversion defines how to convert between two units for a specific ingredient.

    Example:
        from_unit: "lb"
        from_quantity: 1.0
        to_unit: "cup"
        to_quantity: 3.6
        Meaning: 1 lb = 3.6 cups

    Attributes:
        ingredient_id: Foreign key to Ingredient
        from_unit: Source unit (e.g., "lb", "kg", "bag")
        from_quantity: Amount in source unit (typically 1.0)
        to_unit: Target unit (e.g., "cup", "oz", "g")
        to_quantity: Equivalent amount in target unit
        notes: Additional notes (e.g., "sifted", "packed", "spooned and leveled")
    """

    __tablename__ = "unit_conversions"

    # Foreign key to Ingredient (NEW refactored model - "products" table)
    ingredient_id = Column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Conversion specification
    from_unit = Column(String(50), nullable=False)
    from_quantity = Column(Float, nullable=False)  # Typically 1.0
    to_unit = Column(String(50), nullable=False)
    to_quantity = Column(Float, nullable=False)

    # Additional information
    notes = Column(Text, nullable=True)

    # Relationships
    ingredient = relationship("Ingredient", back_populates="conversions")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_conversion_ingredient", "ingredient_id"),
        Index("idx_conversion_from_to", "ingredient_id", "from_unit", "to_unit"),
    )

    def __repr__(self) -> str:
        """String representation of conversion."""
        return (
            f"UnitConversion(id={self.id}, "
            f"ingredient_id={self.ingredient_id}, "
            f"{self.from_quantity} {self.from_unit} = {self.to_quantity} {self.to_unit})"
        )

    @property
    def conversion_factor(self) -> float:
        """
        Get conversion factor (to_quantity / from_quantity).

        Returns:
            Conversion factor
        """
        return self.to_quantity / self.from_quantity

    def convert(self, quantity: float) -> float:
        """
        Convert quantity from from_unit to to_unit.

        Args:
            quantity: Amount in from_unit

        Returns:
            Equivalent amount in to_unit
        """
        return quantity * self.conversion_factor

    def reverse_convert(self, quantity: float) -> float:
        """
        Convert quantity from to_unit to from_unit.

        Args:
            quantity: Amount in to_unit

        Returns:
            Equivalent amount in from_unit
        """
        return quantity / self.conversion_factor

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert conversion to dictionary.

        Args:
            include_relationships: If True, include ingredient information

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["conversion_factor"] = self.conversion_factor

        if include_relationships and self.ingredient:
            result["ingredient"] = {"id": self.ingredient.id, "name": self.ingredient.name}

        return result


# Module-level helper functions for unit conversion


def get_conversion(ingredient_id: int, from_unit: str, to_unit: str, session) -> UnitConversion:
    """
    Get conversion for ingredient between specified units.

    Args:
        ingredient_id: Ingredient ID
        from_unit: Source unit
        to_unit: Target unit
        session: SQLAlchemy session

    Returns:
        UnitConversion instance, or None if not found
    """
    conversion = (
        session.query(UnitConversion)
        .filter(
            UnitConversion.ingredient_id == ingredient_id,
            UnitConversion.from_unit == from_unit,
            UnitConversion.to_unit == to_unit,
        )
        .first()
    )

    # If not found, try reverse conversion
    if not conversion:
        reverse = (
            session.query(UnitConversion)
            .filter(
                UnitConversion.ingredient_id == ingredient_id,
                UnitConversion.from_unit == to_unit,
                UnitConversion.to_unit == from_unit,
            )
            .first()
        )
        return reverse

    return conversion


def convert_quantity(
    ingredient_id: int, quantity: float, from_unit: str, to_unit: str, session
) -> float:
    """
    Convert quantity between units for a ingredient.

    Args:
        ingredient_id: Ingredient ID
        quantity: Amount to convert
        from_unit: Source unit
        to_unit: Target unit
        session: SQLAlchemy session

    Returns:
        Converted quantity, or None if conversion not found
    """
    # Same unit - no conversion needed
    if from_unit == to_unit:
        return quantity

    # Look up conversion
    conversion = get_conversion(ingredient_id, from_unit, to_unit, session)

    if not conversion:
        # Try standard conversions from unit_converter module
        from src.services.unit_converter import convert as standard_convert

        try:
            return standard_convert(quantity, from_unit, to_unit)
        except ValueError:
            return None

    # Apply conversion
    if conversion.from_unit == from_unit:
        return conversion.convert(quantity)
    else:
        # Using reverse conversion
        return conversion.reverse_convert(quantity)


def create_standard_conversions(ingredient_id: int, ingredient_name: str, session) -> list:
    """
    Create standard conversions for a ingredient based on ingredient name.

    Uses density data from constants to create volume-weight conversions.

    Args:
        ingredient_id: Ingredient ID
        ingredient_name: Ingredient name for density lookup
        session: SQLAlchemy session

    Returns:
        List of created UnitConversion instances
    """
    from src.utils.constants import get_ingredient_density

    density_g_per_cup = get_ingredient_density(ingredient_name)

    if density_g_per_cup == 0:
        # No standard density data available
        return []

    conversions = []

    # Create cup ↔ g conversion
    conversion_cup_g = UnitConversion(
        ingredient_id=ingredient_id,
        from_unit="cup",
        from_quantity=1.0,
        to_unit="g",
        to_quantity=density_g_per_cup,
        notes="Based on standard density data",
    )
    session.add(conversion_cup_g)
    conversions.append(conversion_cup_g)

    # Create lb ↔ cup conversion (via grams)
    # 1 lb = 453.592 g
    lb_to_g = 453.592
    cups_per_lb = lb_to_g / density_g_per_cup

    conversion_lb_cup = UnitConversion(
        ingredient_id=ingredient_id,
        from_unit="lb",
        from_quantity=1.0,
        to_unit="cup",
        to_quantity=cups_per_lb,
        notes="Calculated from density",
    )
    session.add(conversion_lb_cup)
    conversions.append(conversion_lb_cup)

    return conversions
