"""
FinishedUnit model for individual consumable baked items.

This model represents the renamed and enhanced version of the original FinishedGood
model, focused on tracking individual consumable units that can be used as components
in assemblies or consumed directly.

Migration Note:
- This model preserves all existing FinishedGood functionality
- Field mappings: name → display_name, cost calculated → unit_cost stored
- New fields: production_notes, inventory_count, slug for unique reference
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Numeric,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Index,
    Enum,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class YieldMode(enum.Enum):
    """Enum for finished unit yield modes."""

    DISCRETE_COUNT = "discrete_count"  # Fixed count items (cookies, truffles)
    BATCH_PORTION = "batch_portion"  # Portion of batch (cakes)


class FinishedUnit(BaseModel):
    """
    FinishedUnit model representing individual consumable baked items.

    This is the renamed and enhanced version of the original FinishedGood model,
    representing individual items that can be consumed directly or used as
    components in assemblies.

    Key Features:
    - Preserves all original FinishedGood functionality
    - Adds inventory tracking with non-negative constraints
    - Includes production notes for baking/storage information
    - Uses slug for unique, URL-safe identification
    - Stores unit cost as field rather than calculation

    Attributes:
        slug: Unique URL-safe identifier for references
        display_name: Product name (e.g., "Sugar Cookie", "Chocolate Truffle")
        description: Optional detailed description
        recipe_id: Foreign key to Recipe
        yield_mode: How this product relates to recipe yield
        items_per_batch: Number of items per recipe batch (discrete_count mode)
        item_unit: Unit name for discrete items (e.g., "cookie", "truffle")
        batch_percentage: Percentage of recipe batch used (batch_portion mode)
        portion_description: Description of portion size (e.g., "9-inch round pan")
        category: Product category
        unit_cost: Cost per individual unit (stored field for performance)
        inventory_count: Current available quantity
        production_notes: Notes about production, storage, handling
        notes: Additional general notes
    """

    __tablename__ = "finished_units"

    # Unique identification
    slug = Column(String(100), nullable=False, unique=True, index=True)

    # Basic information
    display_name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)

    # Yield mode (preserved from original FinishedGood)
    yield_mode = Column(Enum(YieldMode), nullable=False, default=YieldMode.DISCRETE_COUNT)

    # For DISCRETE_COUNT mode (cookies, truffles, etc.)
    items_per_batch = Column(Integer, nullable=True)
    item_unit = Column(String(50), nullable=True)  # "cookie", "truffle", "piece"

    # For BATCH_PORTION mode (cakes)
    batch_percentage = Column(Numeric(5, 2), nullable=True)
    portion_description = Column(String(200), nullable=True)  # "9-inch round", "8x8 square"

    # Cost and inventory
    unit_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    inventory_count = Column(Integer, nullable=False, default=0)

    # Additional information
    category = Column(String(100), nullable=True, index=True)
    production_notes = Column(Text, nullable=True)  # New field for production info
    notes = Column(Text, nullable=True)

    # Enhanced timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipe = relationship("Recipe", back_populates="finished_units", lazy="joined")

    # Relationships for composition (will be added when Composition model is created)
    # components_in = relationship("Composition", foreign_keys="Composition.finished_unit_id",
    #                            back_populates="finished_unit_component")

    # Table constraints
    __table_args__ = (
        # Single column indexes for fast lookups
        Index("idx_finished_unit_slug", "slug"),
        Index("idx_finished_unit_display_name", "display_name"),
        Index("idx_finished_unit_recipe", "recipe_id"),
        Index("idx_finished_unit_category", "category"),
        Index("idx_finished_unit_inventory", "inventory_count"),
        Index("idx_finished_unit_created_at", "created_at"),
        # Composite indexes for complex queries
        Index("idx_finished_unit_recipe_inventory", "recipe_id", "inventory_count"),
        # Unique constraints
        UniqueConstraint("slug", name="uq_finished_unit_slug"),
        CheckConstraint("unit_cost >= 0", name="ck_finished_unit_unit_cost_non_negative"),
        CheckConstraint("inventory_count >= 0", name="ck_finished_unit_inventory_non_negative"),
        CheckConstraint(
            "items_per_batch IS NULL OR items_per_batch > 0",
            name="ck_finished_unit_items_per_batch_positive",
        ),
        CheckConstraint(
            "batch_percentage IS NULL OR (batch_percentage > 0 AND batch_percentage <= 100)",
            name="ck_finished_unit_batch_percentage_valid",
        ),
    )

    def __repr__(self) -> str:
        """String representation of finished unit."""
        return f"FinishedUnit(id={self.id}, slug='{self.slug}', display_name='{self.display_name}')"

    def calculate_batches_needed(self, quantity: int) -> float:
        """
        Calculate how many recipe batches are needed for a given quantity.

        Args:
            quantity: Number of finished units needed

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
            return quantity * (float(self.batch_percentage) / 100.0)

        return 0.0

    def calculate_recipe_cost_per_item(self) -> Decimal:
        """
        Calculate cost per finished unit item based on current recipe cost.

        This method calculates the cost dynamically from the recipe,
        separate from the stored unit_cost field.

        Returns:
            Cost per item based on recipe cost
        """
        if not self.recipe:
            return Decimal("0.0000")

        recipe_cost = Decimal(str(self.recipe.calculate_cost()))

        if self.yield_mode == YieldMode.DISCRETE_COUNT:
            if not self.items_per_batch or self.items_per_batch <= 0:
                return Decimal("0.0000")
            return recipe_cost / Decimal(str(self.items_per_batch))

        elif self.yield_mode == YieldMode.BATCH_PORTION:
            if not self.batch_percentage or self.batch_percentage <= 0:
                return Decimal("0.0000")
            return recipe_cost * (self.batch_percentage / Decimal("100.0"))

        return Decimal("0.0000")

    def update_unit_cost_from_recipe(self) -> None:
        """
        Update the stored unit_cost field based on current recipe cost.

        This method should be called when recipe costs change to keep
        the stored unit cost in sync.
        """
        self.unit_cost = self.calculate_recipe_cost_per_item()

    def is_available(self, quantity: int = 1) -> bool:
        """
        Check if the specified quantity is available in inventory.

        Args:
            quantity: Quantity needed

        Returns:
            True if available, False otherwise
        """
        return self.inventory_count >= quantity

    def update_inventory(self, quantity_change: int) -> bool:
        """
        Update inventory count with the specified change.

        Args:
            quantity_change: Positive or negative change to inventory

        Returns:
            True if successful, False if would result in negative inventory
        """
        new_count = self.inventory_count + quantity_change
        if new_count < 0:
            return False

        self.inventory_count = new_count
        self.updated_at = datetime.utcnow()  # Update timestamp
        return True

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert finished unit to dictionary.

        Args:
            include_relationships: If True, include recipe details

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Convert enum to string
        result["yield_mode"] = self.yield_mode.value if self.yield_mode else None

        # Convert Decimal fields to float for JSON serialization
        result["unit_cost"] = float(self.unit_cost) if self.unit_cost else 0.0
        result["batch_percentage"] = float(self.batch_percentage) if self.batch_percentage else None

        # Add calculated fields
        result["recipe_cost_per_item"] = float(self.calculate_recipe_cost_per_item())
        result["is_in_stock"] = self.inventory_count > 0

        return result

    @classmethod
    def create_from_finished_good(
        cls, finished_good_data: dict, slug: str, unit_cost: Decimal = None
    ) -> "FinishedUnit":
        """
        Factory method to create FinishedUnit from existing FinishedGood data.

        This method is used during migration to convert existing FinishedGood
        records to the new FinishedUnit structure.

        Args:
            finished_good_data: Dictionary of FinishedGood field values
            slug: Unique slug for the new FinishedUnit
            unit_cost: Optional unit cost override

        Returns:
            New FinishedUnit instance
        """
        # Map old field names to new field names
        field_mapping = {
            "name": "display_name",
            "date_added": "created_at",
            "last_modified": "updated_at",
        }

        # Create new instance data
        unit_data = {}
        for old_field, new_field in field_mapping.items():
            if old_field in finished_good_data:
                unit_data[new_field] = finished_good_data[old_field]

        # Copy fields that don't need mapping
        copy_fields = [
            "recipe_id",
            "yield_mode",
            "items_per_batch",
            "item_unit",
            "batch_percentage",
            "portion_description",
            "category",
            "notes",
        ]
        for field in copy_fields:
            if field in finished_good_data:
                unit_data[field] = finished_good_data[field]

        # Set new required fields
        unit_data["slug"] = slug
        unit_data["unit_cost"] = unit_cost or Decimal("0.0000")
        unit_data["inventory_count"] = 0  # Start with zero inventory

        return cls(**unit_data)
