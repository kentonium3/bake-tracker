"""
RecipeSnapshot model for capturing immutable recipe state at production time.

This module contains the RecipeSnapshot model which stores a complete
snapshot of recipe data (including ingredients) at the moment of production.
This enables accurate historical cost tracking even when recipes change.

Feature 037: Recipe Template & Snapshot System
"""

import json
from sqlalchemy import (
    Column,
    Integer,
    Float,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class RecipeSnapshot(BaseModel):
    """
    Immutable snapshot of recipe state.

    RecipeSnapshots capture the complete recipe state (recipe metadata and
    ingredients) for production tracking or planning. This ensures
    historical production costs remain accurate even when recipes change.

    Context:
        - Production context: production_run_id is set (created at production time)
        - Planning context: production_run_id is None (created at plan time,
          referenced via EventProductionTarget.recipe_snapshot_id)

    Attributes:
        recipe_id: FK to the source recipe (RESTRICT on delete)
        production_run_id: FK to the production run (UNIQUE when set, nullable for planning)
        scale_factor: Batch size multiplier (e.g., 2.0 = double batch)
        snapshot_date: When the snapshot was captured
        recipe_data: JSON string with recipe metadata at snapshot time
        ingredients_data: JSON string with ingredient list at snapshot time
        is_backfilled: True if snapshot was created during migration (approximated)

    Note:
        - ON DELETE RESTRICT: Cannot delete a recipe that has production snapshots
        - UNIQUE on production_run_id: Each production run has exactly one snapshot
        - NULL values in production_run_id indicate planning context
        - JSON columns use Text type for SQLite compatibility
    """

    __tablename__ = "recipe_snapshots"

    # Foreign keys
    recipe_id = Column(
        Integer,
        ForeignKey("recipes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    production_run_id = Column(
        Integer,
        ForeignKey("production_runs.id", ondelete="CASCADE"),
        nullable=True,  # Planning context: no production_run_id
        unique=True,  # Still unique when set (NULL values not considered)
    )

    # Scaling information
    scale_factor = Column(Float, nullable=False, default=1.0)

    # Timestamp
    snapshot_date = Column(DateTime, nullable=False, default=utc_now)

    # Denormalized data (JSON strings)
    recipe_data = Column(Text, nullable=False)  # JSON: name, category, yield, etc.
    ingredients_data = Column(Text, nullable=False)  # JSON: list of ingredients

    # Migration flag
    is_backfilled = Column(Boolean, nullable=False, default=False)

    # Relationships
    recipe = relationship(
        "Recipe",
        back_populates="snapshots",
        foreign_keys=[recipe_id],
    )
    production_run = relationship(
        "ProductionRun",
        back_populates="snapshot",
        uselist=False,
        foreign_keys=[production_run_id],
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_recipe_snapshot_recipe", "recipe_id"),
        Index("idx_recipe_snapshot_date", "snapshot_date"),
        Index("idx_recipe_snapshot_production_run", "production_run_id"),
    )

    def get_recipe_data(self) -> dict:
        """
        Parse and return the recipe data from JSON.

        Returns:
            Dictionary containing recipe metadata at snapshot time.
            Empty dict if recipe_data is None or invalid JSON.
        """
        if not self.recipe_data:
            return {}
        try:
            return json.loads(self.recipe_data)
        except json.JSONDecodeError:
            return {}

    def get_ingredients_data(self) -> list:
        """
        Parse and return the ingredients data from JSON.

        Returns:
            List of ingredient dictionaries at snapshot time.
            Empty list if ingredients_data is None or invalid JSON.
        """
        if not self.ingredients_data:
            return []
        try:
            return json.loads(self.ingredients_data)
        except json.JSONDecodeError:
            return []

    def __repr__(self) -> str:
        """String representation of recipe snapshot."""
        return (
            f"RecipeSnapshot(id={self.id}, recipe_id={self.recipe_id}, "
            f"production_run_id={self.production_run_id}, scale_factor={self.scale_factor})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert snapshot to dictionary.

        Args:
            include_relationships: If True, include recipe details

        Returns:
            Dictionary representation with parsed JSON data
        """
        result = super().to_dict(include_relationships)

        # Add parsed JSON data for convenience
        result["recipe_data_parsed"] = self.get_recipe_data()
        result["ingredients_data_parsed"] = self.get_ingredients_data()

        return result
