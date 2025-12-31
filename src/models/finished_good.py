"""
FinishedGood model for assembled packages containing multiple components.

This model represents the new assembly-focused FinishedGood in the two-tier
hierarchical system, where FinishedGood contains multiple FinishedUnits and/or
other FinishedGoods in complex packaging scenarios.

Migration Note:
- Original FinishedGood functionality moved to FinishedUnit model
- This new model focuses on assemblies and packaged combinations
- Uses Composition model for component relationships
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
    - Calculated costs derived from component costs and quantities
    - Support for complex hierarchical packaging scenarios
    - Assembly-specific packaging and presentation instructions

    Attributes:
        slug: Unique URL-safe identifier for references
        display_name: Package name (e.g., "Holiday Gift Box", "Cookie Sampler")
        description: Detailed description of the assembly
        assembly_type: Type of assembly (gift_box, variety_pack, etc.)
        packaging_instructions: Detailed instructions for assembly and packaging
        total_cost: Calculated total cost from all components
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

    # Cost and inventory
    total_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
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
        CheckConstraint("total_cost >= 0", name="ck_finished_good_total_cost_non_negative"),
        CheckConstraint("inventory_count >= 0", name="ck_finished_good_inventory_non_negative"),
    )

    def __repr__(self) -> str:
        """String representation of finished good assembly."""
        return f"FinishedGood(id={self.id}, slug='{self.slug}', display_name='{self.display_name}')"

    def calculate_component_cost(self) -> Decimal:
        """
        Calculate total cost from all components in the assembly.

        This method dynamically calculates the cost by summing all
        component costs through the Composition relationships.

        Returns:
            Total cost based on current component costs and quantities
        """
        if not hasattr(self, "components") or not self.components:
            return Decimal("0.0000")

        total_cost = Decimal("0.0000")

        for composition in self.components:
            if composition.finished_unit_component:
                # FinishedUnit component cost
                unit_cost = composition.finished_unit_component.unit_cost or Decimal("0.0000")
                component_cost = unit_cost * Decimal(str(composition.component_quantity))
                total_cost += component_cost

            elif composition.finished_good_component:
                # FinishedGood component cost (recursive assembly)
                assembly_cost = composition.finished_good_component.total_cost or Decimal("0.0000")
                component_cost = assembly_cost * Decimal(str(composition.component_quantity))
                total_cost += component_cost

        return total_cost

    def update_total_cost_from_components(self) -> None:
        """
        Update the stored total_cost field based on current component costs.

        This method should be called when component costs or quantities change
        to keep the stored cost in sync.
        """
        self.total_cost = self.calculate_component_cost()

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
                "unit_cost": Decimal("0.0000"),
                "total_cost": Decimal("0.0000"),
            }

            if composition.finished_unit_component:
                component_info.update(
                    {
                        "type": "finished_unit",
                        "name": composition.finished_unit_component.display_name,
                        "unit_cost": composition.finished_unit_component.unit_cost,
                        "total_cost": composition.finished_unit_component.unit_cost
                        * composition.component_quantity,
                    }
                )

            elif composition.finished_good_component:
                component_info.update(
                    {
                        "type": "finished_good",
                        "name": composition.finished_good_component.display_name,
                        "unit_cost": composition.finished_good_component.total_cost,
                        "total_cost": composition.finished_good_component.total_cost
                        * composition.component_quantity,
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

        # Convert Decimal fields to float for JSON serialization
        result["total_cost"] = float(self.total_cost) if self.total_cost else 0.0

        # Add calculated fields
        result["component_cost"] = float(self.calculate_component_cost())
        result["is_in_stock"] = self.inventory_count > 0

        if include_relationships:
            result["components"] = self.get_component_breakdown()

        return result
