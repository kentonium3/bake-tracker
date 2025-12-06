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
    snapshot_date = Column(DateTime, nullable=False, default=datetime.utcnow)
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

        Returns:
            Total value of all ingredients in the snapshot
        """
        total_value = 0.0
        for snapshot_ingredient in self.snapshot_ingredients:
            ingredient = snapshot_ingredient.ingredient
            if ingredient:
                value = snapshot_ingredient.quantity * ingredient.unit_cost
                total_value += value
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

        Uses current ingredient unit_cost (cost at snapshot time not stored).

        Returns:
            Value (quantity × unit_cost)
        """
        if not self.ingredient:
            return 0.0
        return self.quantity * self.ingredient.unit_cost

    def get_recipe_unit_quantity(self) -> float:
        """
        Convert quantity to recipe units.

        Returns:
            Quantity in recipe units
        """
        if not self.ingredient:
            return 0.0
        return self.ingredient.convert_to_recipe_units(self.quantity)

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
        result["recipe_unit_quantity"] = self.get_recipe_unit_quantity()

        return result
