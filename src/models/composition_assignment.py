"""
CompositionAssignment junction model for tracking specific inventory assignments.

This model enables deferred packaging decisions by tracking which specific
inventory items fulfill a generic packaging requirement in a composition.

Key Features:
- Links generic compositions to specific inventory items
- Tracks quantity assigned from each inventory item
- Enforces referential integrity (CASCADE on composition, RESTRICT on inventory)
- Records when assignments were made
- Prevents duplicate assignments (unique constraint)

Feature 026: Deferred Packaging Decisions
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class CompositionAssignment(BaseModel):
    """
    CompositionAssignment tracks which specific inventory items fulfill a generic
    packaging requirement.

    When a Composition has is_generic=True, this junction table records which
    specific InventoryItem(s) are assigned to fulfill the requirement. Multiple
    assignments can exist for one composition (e.g., using boxes from different
    brands to meet the total quantity).

    Attributes:
        composition_id: Foreign key to parent Composition (CASCADE delete)
        inventory_item_id: Foreign key to assigned InventoryItem (RESTRICT delete)
        quantity_assigned: Quantity from this inventory item being used
        assigned_at: Timestamp when assignment was made
    """

    __tablename__ = "composition_assignments"

    # Foreign key to Composition (CASCADE - assignment meaningless without composition)
    composition_id = Column(
        Integer,
        ForeignKey("compositions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Foreign key to InventoryItem (RESTRICT - prevent deletion of assigned inventory)
    inventory_item_id = Column(
        Integer,
        ForeignKey("inventory_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Assignment details
    quantity_assigned = Column(Float, nullable=False)
    assigned_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    composition = relationship("Composition", backref="assignments", lazy="joined")
    inventory_item = relationship("InventoryItem", backref="composition_assignments", lazy="joined")

    # Table constraints and indexes
    __table_args__ = (
        # Indexes for common queries
        Index("idx_composition_assignment_composition", "composition_id"),
        Index("idx_composition_assignment_inventory", "inventory_item_id"),
        # Positive quantity constraint
        CheckConstraint(
            "quantity_assigned > 0",
            name="ck_assignment_quantity_positive",
        ),
        # Unique constraint: each inventory item can only be assigned once per composition
        UniqueConstraint(
            "composition_id",
            "inventory_item_id",
            name="uq_composition_assignment",
        ),
    )

    def __repr__(self) -> str:
        """String representation of composition assignment."""
        return (
            f"CompositionAssignment(id={self.id}, "
            f"composition_id={self.composition_id}, "
            f"inventory_item_id={self.inventory_item_id}, "
            f"qty={self.quantity_assigned})"
        )

    @property
    def unit_cost(self) -> float:
        """
        Get unit cost from the assigned inventory item.

        Returns:
            Unit cost per unit, or 0.0 if not available
        """
        if not self.inventory_item:
            return 0.0
        return float(self.inventory_item.unit_cost or 0.0)

    @property
    def total_cost(self) -> float:
        """
        Calculate total cost for this assignment.

        Returns:
            Unit cost × quantity assigned
        """
        return self.unit_cost * self.quantity_assigned

    @property
    def product_name(self) -> str:
        """
        Get product name of the assigned inventory item.

        Returns:
            Product display name or "Unknown"
        """
        if not self.inventory_item or not self.inventory_item.product:
            return "Unknown"
        return self.inventory_item.product.display_name

    def validate_quantity(self) -> bool:
        """
        Validate that assigned quantity doesn't exceed inventory available.

        Returns:
            True if assignment is valid (quantity <= inventory quantity)
        """
        if not self.inventory_item:
            return False
        return self.quantity_assigned <= self.inventory_item.quantity

    def validate_product_match(self) -> bool:
        """
        Validate that assigned inventory item matches the generic requirement.

        Checks that the product_name of the assigned inventory item matches
        the product_name of the template product in the composition.

        Returns:
            True if product names match
        """
        if not self.composition or not self.composition.packaging_product:
            return False
        if not self.inventory_item or not self.inventory_item.product:
            return False

        template_name = self.composition.packaging_product.product_name
        assigned_name = self.inventory_item.product.product_name

        return template_name == assigned_name

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert assignment to dictionary.

        Args:
            include_relationships: If True, include composition and inventory details

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Add computed fields
        result["unit_cost"] = self.unit_cost
        result["total_cost"] = self.total_cost
        result["product_name"] = self.product_name
        result["is_valid_quantity"] = self.validate_quantity()
        result["is_valid_match"] = self.validate_product_match()

        if include_relationships:
            if self.composition:
                result["composition"] = self.composition.to_dict()
            if self.inventory_item:
                result["inventory_item"] = self.inventory_item.to_dict()

        return result
