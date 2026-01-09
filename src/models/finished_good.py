"""
FinishedGood model for assembled packages containing multiple components.

This model represents the new assembly-focused FinishedGood in the two-tier
hierarchical system, where FinishedGood contains multiple FinishedUnits and/or
other FinishedGoods in complex packaging scenarios.

Migration Note:
- Original FinishedGood functionality moved to FinishedUnit model
- This new model focuses on assemblies and packaged combinations
- Uses Composition model for component relationships

Cost Architecture (F045):
- Costs are NOT stored on definition models (FinishedUnit, FinishedGood)
- Costs are captured on production/assembly instances (F046+)
- Philosophy: "Costs on Instances, Not Definitions"
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    Index,
    Enum,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now
from .assembly_type import AssemblyType


class FinishedGood(BaseModel):
    """
    FinishedGood model representing assembled packages with multiple components.

    This is the new assembly-focused model in the two-tier hierarchical system.
    FinishedGoods contain multiple FinishedUnits and/or other FinishedGoods
    through the Composition junction model.

    Key Features:
    - Represents packaged assemblies rather than individual items
    - Components managed through Composition relationships
    - Support for complex hierarchical packaging scenarios
    - Assembly-specific packaging and presentation instructions

    Attributes:
        slug: Unique URL-safe identifier for references
        display_name: Package name (e.g., "Holiday Gift Box", "Cookie Sampler")
        description: Detailed description of the assembly
        assembly_type: Type of assembly (gift_box, variety_pack, etc.)
        packaging_instructions: Detailed instructions for assembly and packaging
        inventory_count: Current available quantity of assembled packages
        notes: Additional notes about the assembly
    """

    __tablename__ = "finished_goods"

    # Unique identification
    slug = Column(String(100), nullable=False, unique=True, index=True)

    # Basic information
    display_name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Assembly-specific attributes
    assembly_type = Column(Enum(AssemblyType), nullable=False, default=AssemblyType.CUSTOM_ORDER)
    packaging_instructions = Column(Text, nullable=True)

    # Inventory tracking
    inventory_count = Column(Integer, nullable=False, default=0)

    # Additional information
    notes = Column(Text, nullable=True)

    # Enhanced timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    # Components managed through Composition model
    components = relationship(
        "Composition",
        foreign_keys="Composition.assembly_id",
        back_populates="assembly",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    # Assembly tracking (Feature 013)
    assembly_runs = relationship("AssemblyRun", back_populates="finished_good")

    # Table constraints
    __table_args__ = (
        Index("idx_finished_good_slug", "slug"),
        Index("idx_finished_good_display_name", "display_name"),
        Index("idx_finished_good_assembly_type", "assembly_type"),
        Index("idx_finished_good_inventory", "inventory_count"),
        UniqueConstraint("slug", name="uq_finished_good_slug"),
        CheckConstraint("inventory_count >= 0", name="ck_finished_good_inventory_non_negative"),
    )

    def __repr__(self) -> str:
        """String representation of finished good assembly."""
        return f"FinishedGood(id={self.id}, slug='{self.slug}', display_name='{self.display_name}')"

    def get_component_breakdown(self) -> list:
        """
        Get detailed breakdown of all components in the assembly.

        Returns:
            List of dictionaries with component details including costs
        """
        if not hasattr(self, "components") or not self.components:
            return []

        breakdown = []

        for composition in self.components:
            component_info = {
                "composition_id": composition.id,
                "quantity": composition.component_quantity,
                "notes": composition.component_notes,
                "sort_order": composition.sort_order,
                "type": None,
                "name": None,
            }

            if composition.finished_unit_component:
                component_info.update(
                    {
                        "type": "finished_unit",
                        "name": composition.finished_unit_component.display_name,
                    }
                )

            elif composition.finished_good_component:
                component_info.update(
                    {
                        "type": "finished_good",
                        "name": composition.finished_good_component.display_name,
                    }
                )

            breakdown.append(component_info)

        # Sort by sort_order if specified
        breakdown.sort(key=lambda x: x.get("sort_order", 999))
        return breakdown

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
        return True

    def can_assemble(self, quantity: int = 1) -> dict:
        """
        Check if the assembly can be created with current component inventory.

        Args:
            quantity: Number of assemblies to create

        Returns:
            Dictionary with availability status and missing components
        """
        result = {"can_assemble": True, "missing_components": [], "sufficient_components": []}

        if not hasattr(self, "components") or not self.components:
            result["can_assemble"] = False
            return result

        for composition in self.components:
            required_qty = composition.component_quantity * quantity
            component_info = {
                "type": None,
                "name": None,
                "required": required_qty,
                "available": 0,
                "shortage": 0,
            }

            if composition.finished_unit_component:
                component = composition.finished_unit_component
                component_info.update(
                    {
                        "type": "finished_unit",
                        "name": component.display_name,
                        "available": component.inventory_count,
                    }
                )

                if component.inventory_count < required_qty:
                    component_info["shortage"] = required_qty - component.inventory_count
                    result["missing_components"].append(component_info)
                    result["can_assemble"] = False
                else:
                    result["sufficient_components"].append(component_info)

            elif composition.finished_good_component:
                component = composition.finished_good_component
                component_info.update(
                    {
                        "type": "finished_good",
                        "name": component.display_name,
                        "available": component.inventory_count,
                    }
                )

                if component.inventory_count < required_qty:
                    component_info["shortage"] = required_qty - component.inventory_count
                    result["missing_components"].append(component_info)
                    result["can_assemble"] = False
                else:
                    result["sufficient_components"].append(component_info)

        return result

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert finished good assembly to dictionary.

        Args:
            include_relationships: If True, include component details

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Convert enum to string
        result["assembly_type"] = self.assembly_type.value if self.assembly_type else None

        # Add calculated fields
        result["is_in_stock"] = self.inventory_count > 0

        if include_relationships:
            result["components"] = self.get_component_breakdown()

        return result
