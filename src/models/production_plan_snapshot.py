"""
ProductionPlanSnapshot model for persisting calculated production plans.

This module contains the ProductionPlanSnapshot model which stores calculated
production plan results for an event, enabling staleness detection and plan
persistence across sessions.

Feature: F039 Planning Workspace
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class ProductionPlanSnapshot(BaseModel):
    """
    Persisted production plan calculation for an event.

    Stores the results of a production plan calculation, including batch
    counts per recipe, aggregated ingredients, and shopping list. Supports
    staleness detection by comparing input timestamps against calculation time.

    Attributes:
        event_id: Foreign key to the Event this plan is for
        calculated_at: When this plan was calculated
        input_hash: Optional SHA256 hash of inputs for backup staleness check
        requirements_updated_at: Latest timestamp from assembly/production targets
        recipes_updated_at: Latest timestamp from recipes in the plan
        bundles_updated_at: Latest timestamp from finished goods in the plan
        calculation_results: JSON blob containing all calculation results
        is_stale: Whether this plan is known to be stale
        stale_reason: Human-readable reason why plan is stale
        shopping_complete: Whether shopping has been marked complete
        shopping_completed_at: When shopping was marked complete
    """

    __tablename__ = "production_plan_snapshots"

    # Primary relationship
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Calculation metadata
    calculated_at = Column(DateTime, nullable=False, default=utc_now)

    # Input version tracking (for staleness detection)
    input_hash = Column(String(64), nullable=True)  # SHA256 of inputs (optional backup)
    requirements_updated_at = Column(DateTime, nullable=False)
    recipes_updated_at = Column(DateTime, nullable=False)
    bundles_updated_at = Column(DateTime, nullable=False)

    # Calculation results (JSON blob for flexibility)
    # Structure defined in data-model.md:
    # {
    #     "recipe_batches": [...],
    #     "aggregated_ingredients": [...],
    #     "shopping_list": [...]
    # }
    calculation_results = Column(JSON, nullable=False)

    # Status tracking
    is_stale = Column(Boolean, default=False, nullable=False)
    stale_reason = Column(String(200), nullable=True)

    # Shopping status
    shopping_complete = Column(Boolean, default=False, nullable=False)
    shopping_completed_at = Column(DateTime, nullable=True)

    # Relationships
    event = relationship("Event", back_populates="production_plan_snapshots")

    # Indexes
    __table_args__ = (
        Index("idx_pps_event", "event_id"),
        Index("idx_pps_calculated_at", "calculated_at"),
        Index("idx_pps_is_stale", "is_stale"),
    )

    def __repr__(self) -> str:
        """String representation of production plan snapshot."""
        return (
            f"ProductionPlanSnapshot(id={self.id}, event_id={self.event_id}, "
            f"calculated_at={self.calculated_at}, is_stale={self.is_stale})"
        )

    def get_recipe_batches(self) -> List[Dict[str, Any]]:
        """
        Extract recipe batch data from calculation_results.

        Returns:
            List of recipe batch dictionaries with keys:
            - recipe_id, recipe_name, units_needed, batches,
            - yield_per_batch, total_yield, waste_units, waste_percent
        """
        if not self.calculation_results:
            return []
        return self.calculation_results.get("recipe_batches", [])

    def get_shopping_list(self) -> List[Dict[str, Any]]:
        """
        Extract shopping list from calculation_results.

        Returns:
            List of shopping list item dictionaries with keys:
            - ingredient_slug, needed, in_stock, to_buy, unit
        """
        if not self.calculation_results:
            return []
        return self.calculation_results.get("shopping_list", [])

    def get_aggregated_ingredients(self) -> List[Dict[str, Any]]:
        """
        Extract aggregated ingredients from calculation_results.

        Returns:
            List of aggregated ingredient dictionaries with keys:
            - ingredient_id, ingredient_slug, ingredient_name, total_quantity, unit
        """
        if not self.calculation_results:
            return []
        return self.calculation_results.get("aggregated_ingredients", [])

    def mark_stale(self, reason: str) -> None:
        """
        Mark this plan as stale with a reason.

        Args:
            reason: Human-readable explanation of why plan is stale
        """
        self.is_stale = True
        self.stale_reason = reason

    def mark_fresh(self) -> None:
        """
        Mark this plan as fresh (not stale).

        Clears the stale flag and reason.
        """
        self.is_stale = False
        self.stale_reason = None

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Args:
            include_relationships: If True, include event details

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Convert datetime fields to ISO format
        if self.calculated_at:
            result["calculated_at"] = self.calculated_at.isoformat()
        if self.requirements_updated_at:
            result["requirements_updated_at"] = self.requirements_updated_at.isoformat()
        if self.recipes_updated_at:
            result["recipes_updated_at"] = self.recipes_updated_at.isoformat()
        if self.bundles_updated_at:
            result["bundles_updated_at"] = self.bundles_updated_at.isoformat()
        if self.shopping_completed_at:
            result["shopping_completed_at"] = self.shopping_completed_at.isoformat()

        if include_relationships:
            if self.event:
                result["event_name"] = self.event.name

        return result
