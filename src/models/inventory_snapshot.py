"""
Inventory Snapshot models for point-in-time inventory captures.

This module contains:
- InventorySnapshot: Main snapshot model
- SnapshotIngredient: Junction table storing ingredient quantities at snapshot time

Snapshots allow event planning based on historical inventory states without
affecting current live inventory.
"""

from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class InventorySnapshot(BaseModel):
    """
    Inventory snapshot capturing ingredient quantities at a point in time.

    Snapshots are used for event planning, allowing planning against a
    specific inventory state without affecting live inventory.

    Attributes:
        name: Snapshot name (e.g., "Pre-Christmas 2025")
        snapshot_date: Date/time when snapshot was taken
        description: Optional description of the snapshot
    """

    __tablename__ = "inventory_snapshots"

    # Basic information
    name = Column(String(200), nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False, default=utc_now)
    description = Column(Text, nullable=True)

    # Relationships
    snapshot_ingredients = relationship(
        "SnapshotIngredient",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    # events = relationship("Event", back_populates="snapshot")

    # Indexes
    __table_args__ = (Index("idx_snapshot_date", "snapshot_date"),)

    def __repr__(self) -> str:
        """String representation of snapshot."""
        return f"InventorySnapshot(id={self.id}, name='{self.name}', date='{self.snapshot_date}')"

    def calculate_total_value(self) -> float:
        """
        Calculate total inventory value at snapshot time.

        Note: Value calculation requires Product cost data. Since Ingredient
        no longer has unit_cost (it's on Product), this returns sum of
        individual snapshot ingredient values.

        Returns:
            Total value of all ingredients in the snapshot
        """
        total_value = 0.0
        for snapshot_ingredient in self.snapshot_ingredients:
            total_value += snapshot_ingredient.calculate_value()
        return total_value

    def get_ingredient_quantity(self, ingredient_id: int) -> float:
        """
        Get quantity of a specific ingredient in this snapshot.

        Args:
            ingredient_id: ID of the ingredient to look up

        Returns:
            Quantity in snapshot, or 0.0 if not found
        """
        for snapshot_ingredient in self.snapshot_ingredients:
            if snapshot_ingredient.ingredient_id == ingredient_id:
                return snapshot_ingredient.quantity
        return 0.0

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert snapshot to dictionary.

        Args:
            include_relationships: If True, include ingredient quantities

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["total_value"] = self.calculate_total_value()
        result["ingredient_count"] = len(self.snapshot_ingredients)

        return result


class SnapshotIngredient(BaseModel):
    """
    Junction table storing ingredient quantities in a snapshot.

    This preserves the quantity of each ingredient at the time
    the snapshot was created.

    Attributes:
        snapshot_id: Foreign key to InventorySnapshot
        ingredient_id: Foreign key to Ingredient
        quantity: Quantity in purchase units at snapshot time
    """

    __tablename__ = "snapshot_ingredients"

    # Foreign keys
    snapshot_id = Column(
        Integer, ForeignKey("inventory_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id = Column(
        Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )

    # Quantity at snapshot time
    quantity = Column(Float, nullable=False, default=0.0)

    # Relationships
    snapshot = relationship("InventorySnapshot", back_populates="snapshot_ingredients")
    ingredient = relationship("Ingredient")  # References new Ingredient model

    # Indexes
    __table_args__ = (
        Index("idx_snapshot_ingredient_snapshot", "snapshot_id"),
        Index("idx_snapshot_ingredient_ingredient", "ingredient_id"),
    )

    def __repr__(self) -> str:
        """String representation of snapshot ingredient."""
        return (
            f"SnapshotIngredient(snapshot_id={self.snapshot_id}, "
            f"ingredient_id={self.ingredient_id}, "
            f"quantity={self.quantity})"
        )

    def calculate_value(self) -> float:
        """
        Calculate value of this ingredient in the snapshot.

        Note: Since Ingredient no longer has unit_cost (cost is on Product),
        this attempts to get cost from the preferred product. Returns 0.0
        if no preferred product or no cost data available.

        Returns:
            Value (quantity × unit_cost from preferred product), or 0.0
        """
        if not self.ingredient:
            return 0.0
        preferred = self.ingredient.get_preferred_product()
        if preferred and hasattr(preferred, "unit_cost") and preferred.unit_cost:
            return self.quantity * preferred.unit_cost
        return 0.0

    def get_recipe_unit_quantity(self) -> float:
        """
        Get quantity (no conversion - deprecated).

        Note: The concept of 'recipe_unit' per ingredient was removed in v3.3.
        Recipes now specify their own units via RecipeIngredient.unit.
        This method returns the raw quantity for backward compatibility.

        Returns:
            Raw quantity (no conversion applied)
        """
        return self.quantity

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert snapshot ingredient to dictionary.

        Args:
            include_relationships: If True, include ingredient details

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["value"] = self.calculate_value()
        # Note: quantity is already included from base to_dict()
        # The legacy recipe_unit_quantity field was removed in v3.3

        return result
