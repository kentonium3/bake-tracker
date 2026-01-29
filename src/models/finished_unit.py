"""
FinishedUnit model for individual consumable baked items.

This model represents the renamed and enhanced version of the original FinishedGood
model, focused on tracking individual consumable units that can be used as components
in assemblies or consumed directly.

Migration Note:
- This model preserves all existing FinishedGood functionality
- Field mappings: name → display_name
- New fields: production_notes, inventory_count, slug for unique reference

Cost Architecture (F045):
- Costs are NOT stored on definition models (FinishedUnit, FinishedGood)
- Costs are captured on production/assembly instances (F046+)
- Philosophy: "Costs on Instances, Not Definitions"
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
from src.utils.datetime_utils import utc_now


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
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)

    # Yield mode (preserved from original FinishedGood)
    yield_mode = Column(Enum(YieldMode), nullable=False, default=YieldMode.DISCRETE_COUNT)

    # Yield type classification (Feature 083 - Dual-Yield Support)
    # 'EA' = whole deliverable unit (1 cake, 1 pie)
    # 'SERVING' = individual consumption unit (slice, cookie)
    yield_type = Column(
        String(10),
        nullable=False,
        default="SERVING",
        index=True,
        doc="Yield classification: 'EA' (whole unit) or 'SERVING' (consumption unit)",
    )

    # For DISCRETE_COUNT mode (cookies, truffles, etc.)
    items_per_batch = Column(Integer, nullable=True)
    item_unit = Column(String(50), nullable=True)  # "cookie", "truffle", "piece"

    # For BATCH_PORTION mode (cakes)
    batch_percentage = Column(Numeric(5, 2), nullable=True)
    portion_description = Column(String(200), nullable=True)  # "9-inch round", "8x8 square"

    # Inventory tracking
    inventory_count = Column(Integer, nullable=False, default=0)

    # Additional information
    category = Column(String(100), nullable=True, index=True)
    production_notes = Column(Text, nullable=True)  # New field for production info
    notes = Column(Text, nullable=True)

    # Enhanced timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    recipe = relationship("Recipe", back_populates="finished_units", lazy="joined")

    # Production tracking (Feature 013)
    production_runs = relationship("ProductionRun", back_populates="finished_unit")

    # Inventory adjustment tracking (Feature 061)
    inventory_adjustments = relationship(
        "FinishedGoodsAdjustment",
        back_populates="finished_unit",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

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
        Index("idx_finished_unit_yield_type", "yield_type"),  # Feature 083: yield_type index
        # Composite indexes for complex queries
        Index("idx_finished_unit_recipe_inventory", "recipe_id", "inventory_count"),
        # Unique constraints
        UniqueConstraint("slug", name="uq_finished_unit_slug"),
        # Feature 083: Unique constraint on (recipe_id, item_unit, yield_type)
        # Allows same item_unit to have both EA and SERVING yields
        UniqueConstraint(
            "recipe_id",
            "item_unit",
            "yield_type",
            name="uq_finished_unit_recipe_item_unit_yield_type",
        ),
        # Check constraints
        CheckConstraint("inventory_count >= 0", name="ck_finished_unit_inventory_non_negative"),
        CheckConstraint(
            "items_per_batch IS NULL OR items_per_batch > 0",
            name="ck_finished_unit_items_per_batch_positive",
        ),
        CheckConstraint(
            "batch_percentage IS NULL OR (batch_percentage > 0 AND batch_percentage <= 100)",
            name="ck_finished_unit_batch_percentage_valid",
        ),
        # Feature 083: Valid yield_type values
        CheckConstraint(
            "yield_type IN ('EA', 'SERVING')",
            name="ck_finished_unit_yield_type_valid",
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

    def calculate_current_cost(self) -> Decimal:
        """
        Calculate current average cost per unit from production history.

        Uses weighted average of per_unit_cost from ProductionRuns,
        weighted by actual_yield. This enables dynamic cost calculation
        following the F045 "Costs on Instances, Not Definitions" principle.

        Returns:
            Decimal: Average cost per unit, or Decimal("0.0000") if no production history
        """
        if not self.production_runs:
            return Decimal("0.0000")

        total_cost = Decimal("0.0000")
        total_yield = 0

        for run in self.production_runs:
            if run.actual_yield and run.actual_yield > 0 and run.per_unit_cost:
                total_cost += run.per_unit_cost * run.actual_yield
                total_yield += run.actual_yield

        if total_yield == 0:
            return Decimal("0.0000")

        return (total_cost / Decimal(str(total_yield))).quantize(Decimal("0.0001"))

    def validate_discrete_count_fields(self) -> list[str]:
        """
        Validate fields required for DISCRETE_COUNT mode.

        This method provides model-level validation that can be called
        before save operations. The service layer uses this for enforcement.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        if self.yield_mode == YieldMode.DISCRETE_COUNT:
            if not self.items_per_batch or self.items_per_batch <= 0:
                errors.append("items_per_batch required and must be > 0 for discrete count mode")
            if not self.item_unit:
                errors.append("item_unit required for discrete count mode")
            if not self.display_name:
                errors.append("display_name required")
        elif self.yield_mode == YieldMode.BATCH_PORTION:
            if not self.batch_percentage or self.batch_percentage <= 0:
                errors.append("batch_percentage required and must be > 0 for batch portion mode")
            if not self.display_name:
                errors.append("display_name required")
        return errors

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

        # Include yield_type (Feature 083)
        result["yield_type"] = self.yield_type

        # Convert Decimal fields to float for JSON serialization
        result["batch_percentage"] = float(self.batch_percentage) if self.batch_percentage else None

        # Add calculated fields
        result["is_in_stock"] = self.inventory_count > 0

        return result

    @classmethod
    def create_from_finished_good(cls, finished_good_data: dict, slug: str) -> "FinishedUnit":
        """
        Factory method to create FinishedUnit from existing FinishedGood data.

        This method is used during migration to convert existing FinishedGood
        records to the new FinishedUnit structure.

        Args:
            finished_good_data: Dictionary of FinishedGood field values
            slug: Unique slug for the new FinishedUnit

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
        unit_data["inventory_count"] = 0  # Start with zero inventory

        return cls(**unit_data)
