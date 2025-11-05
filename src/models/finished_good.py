"""
Finished Good models for tracking final baked products.

This module contains:
- FinishedGood: Products made from recipes (cakes, cookies, etc.)
- Bundle: Grouped finished goods (e.g., bag of 4 cookies)
"""

from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, Text, DateTime, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class YieldMode(enum.Enum):
    """Enum for finished good yield modes."""
    DISCRETE_COUNT = "discrete_count"  # Fixed count items (cookies, truffles)
    BATCH_PORTION = "batch_portion"    # Portion of batch (cakes)


class FinishedGood(BaseModel):
    """
    Finished Good model representing final baked products.

    Finished goods are created from recipes and represent the actual items
    that go into packages for recipients.

    Two yield modes:
    1. DISCRETE_COUNT: Recipe yields a fixed number of items (e.g., 24 cookies)
    2. BATCH_PORTION: Item uses a percentage of recipe batch (e.g., large cake = 100%)

    Attributes:
        name: Product name (e.g., "Sugar Cookie", "9-inch Chocolate Cake")
        recipe_id: Foreign key to Recipe
        yield_mode: How this product relates to recipe yield
        items_per_batch: Number of items per recipe batch (discrete_count mode)
        item_unit: Unit name for discrete items (e.g., "cookie", "truffle")
        batch_percentage: Percentage of recipe batch used (batch_portion mode)
        portion_description: Description of portion size (e.g., "9-inch round pan")
        category: Product category
        notes: Additional notes
    """

    __tablename__ = "finished_goods"

    # Basic information
    name = Column(String(200), nullable=False, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)

    # Yield mode
    yield_mode = Column(
        Enum(YieldMode),
        nullable=False,
        default=YieldMode.DISCRETE_COUNT
    )

    # For DISCRETE_COUNT mode (cookies, truffles, etc.)
    items_per_batch = Column(Integer, nullable=True)
    item_unit = Column(String(50), nullable=True)  # "cookie", "truffle", "piece"

    # For BATCH_PORTION mode (cakes)
    batch_percentage = Column(Float, nullable=True)
    portion_description = Column(String(200), nullable=True)  # "9-inch round", "8x8 square"

    # Additional information
    category = Column(String(100), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    recipe = relationship("Recipe", back_populates="finished_goods")
    bundles = relationship("Bundle", back_populates="finished_good", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_finished_good_name", "name"),
        Index("idx_finished_good_recipe", "recipe_id"),
        Index("idx_finished_good_category", "category"),
    )

    def __repr__(self) -> str:
        """String representation of finished good."""
        return f"FinishedGood(id={self.id}, name='{self.name}', mode='{self.yield_mode.value}')"

    def calculate_batches_needed(self, quantity: int) -> float:
        """
        Calculate how many recipe batches are needed for a given quantity.

        Args:
            quantity: Number of finished goods needed

        Returns:
            Number of recipe batches required
        """
        if self.yield_mode == YieldMode.DISCRETE_COUNT:
            if not self.items_per_batch or self.items_per_batch <= 0:
                return 0.0
            return quantity / self.items_per_batch

        elif self.yield_mode == YieldMode.BATCH_PORTION:
            if not self.batch_percentage or self.batch_percentage <= 0:
                return 0.0
            return quantity * (self.batch_percentage / 100.0)

        return 0.0

    def get_cost_per_item(self) -> float:
        """
        Calculate cost per finished good item.

        Returns:
            Cost per item based on recipe cost
        """
        if not self.recipe:
            return 0.0

        recipe_cost = self.recipe.calculate_cost()

        if self.yield_mode == YieldMode.DISCRETE_COUNT:
            if not self.items_per_batch or self.items_per_batch <= 0:
                return 0.0
            return recipe_cost / self.items_per_batch

        elif self.yield_mode == YieldMode.BATCH_PORTION:
            if not self.batch_percentage or self.batch_percentage <= 0:
                return 0.0
            return recipe_cost * (self.batch_percentage / 100.0)

        return 0.0

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert finished good to dictionary.

        Args:
            include_relationships: If True, include recipe details

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Convert enum to string
        result["yield_mode"] = self.yield_mode.value

        # Add calculated fields
        result["cost_per_item"] = self.get_cost_per_item()

        return result


class Bundle(BaseModel):
    """
    Bundle model representing grouped finished goods.

    Bundles are quantities of the same finished good packaged together
    (e.g., "Bag of 4 Sugar Cookies", "Box of 6 Truffles").

    Attributes:
        name: Bundle name
        finished_good_id: Foreign key to FinishedGood
        quantity: Number of items in bundle
        packaging_notes: Notes about packaging
    """

    __tablename__ = "bundles"

    # Basic information
    name = Column(String(200), nullable=False, index=True)
    finished_good_id = Column(
        Integer, ForeignKey("finished_goods.id", ondelete="RESTRICT"), nullable=False
    )
    quantity = Column(Integer, nullable=False)  # Number of items per bundle

    # Additional information
    packaging_notes = Column(Text, nullable=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    finished_good = relationship("FinishedGood", back_populates="bundles")

    # Indexes
    __table_args__ = (
        Index("idx_bundle_name", "name"),
        Index("idx_bundle_finished_good", "finished_good_id"),
    )

    def __repr__(self) -> str:
        """String representation of bundle."""
        return f"Bundle(id={self.id}, name='{self.name}', qty={self.quantity})"

    def calculate_cost(self) -> float:
        """
        Calculate cost of bundle.

        Returns:
            Total cost (cost per item × quantity)
        """
        if not self.finished_good:
            return 0.0

        cost_per_item = self.finished_good.get_cost_per_item()
        return cost_per_item * self.quantity

    def calculate_batches_needed(self, bundle_count: int) -> float:
        """
        Calculate recipe batches needed for a given number of bundles.

        Args:
            bundle_count: Number of bundles needed

        Returns:
            Number of recipe batches required
        """
        if not self.finished_good:
            return 0.0

        total_items = self.quantity * bundle_count
        return self.finished_good.calculate_batches_needed(total_items)

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert bundle to dictionary.

        Args:
            include_relationships: If True, include finished good details

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["cost"] = self.calculate_cost()

        return result
