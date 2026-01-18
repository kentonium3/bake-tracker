"""
MaterialInventoryItem model for FIFO material inventory tracking.

This model represents a specific lot of material inventory from a purchase.
Parallels InventoryItem (for food ingredients) exactly per constitutional compliance.

Part of Feature 058: Materials FIFO Foundation.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Text,
    Date,
    ForeignKey,
    Index,
    CheckConstraint,
    Numeric,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class MaterialInventoryItem(BaseModel):
    """
    MaterialInventoryItem model for FIFO material inventory tracking.

    Each record represents a specific lot of material inventory from a purchase.
    Tracks quantity_purchased (immutable snapshot), quantity_remaining (mutable,
    decremented on consumption), and cost_per_unit (immutable snapshot).

    All quantities are stored in metric base units (cm for linear/area, count for each).

    FIFO Consumption:
    Items are consumed in purchase_date order (oldest first).

    Attributes:
        material_product_id: Foreign key to MaterialProduct (what)
        material_purchase_id: Foreign key to MaterialPurchase (when/where purchased)
        quantity_purchased: Original quantity purchased in base units (IMMUTABLE)
        quantity_remaining: Current quantity remaining in base units (MUTABLE)
        cost_per_unit: Cost per base unit at time of purchase (IMMUTABLE)
        purchase_date: Date of purchase (for FIFO ordering)
        location: Storage location (optional)
        notes: Additional notes (optional)

    Relationships:
        product: Many-to-One with MaterialProduct
        purchase: One-to-One with MaterialPurchase
        consumptions: One-to-Many with MaterialConsumption
    """

    __tablename__ = "material_inventory_items"

    # Foreign Keys
    material_product_id = Column(
        Integer,
        ForeignKey("material_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_purchase_id = Column(
        Integer,
        ForeignKey("material_purchases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Quantity Tracking (in base units - cm for linear/area, count for each)
    quantity_purchased = Column(Float, nullable=False)  # Immutable snapshot
    quantity_remaining = Column(Float, nullable=False)  # Mutable, decremented on consumption

    # Cost Tracking
    cost_per_unit = Column(Numeric(10, 4), nullable=False)  # Immutable snapshot ($/base unit)

    # Date Tracking
    purchase_date = Column(Date, nullable=False, index=True)  # For FIFO ordering

    # Optional Fields
    location = Column(String(100), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    # Relationships
    product = relationship(
        "MaterialProduct",
        back_populates="inventory_items",
    )
    purchase = relationship(
        "MaterialPurchase",
        back_populates="inventory_item",
    )
    consumptions = relationship(
        "MaterialConsumption",
        back_populates="inventory_item",
    )

    # Table constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "quantity_purchased > 0",
            name="ck_mat_inv_qty_purchased_positive",
        ),
        CheckConstraint(
            "quantity_remaining >= 0",
            name="ck_mat_inv_qty_remaining_non_negative",
        ),
        CheckConstraint(
            "cost_per_unit >= 0",
            name="ck_mat_inv_cost_non_negative",
        ),
        Index("idx_material_inventory_product", "material_product_id"),
        Index("idx_material_inventory_purchase_date", "purchase_date"),
        Index("idx_material_inventory_purchase", "material_purchase_id"),
        Index("idx_material_inventory_location", "location"),
    )

    def __repr__(self) -> str:
        """String representation of material inventory item."""
        return (
            f"MaterialInventoryItem(id={self.id}, "
            f"product_id={self.material_product_id}, "
            f"qty_remaining={self.quantity_remaining}, "
            f"purchase_date={self.purchase_date})"
        )

    @property
    def is_depleted(self) -> bool:
        """
        Check if item is depleted (quantity_remaining near zero).

        Uses small threshold to handle floating-point dust.

        Returns:
            True if quantity_remaining < 0.001
        """
        return self.quantity_remaining < 0.001

    @property
    def quantity_consumed(self) -> float:
        """
        Calculate total quantity consumed from this lot.

        Returns:
            quantity_purchased - quantity_remaining
        """
        return self.quantity_purchased - self.quantity_remaining

    @property
    def consumption_percentage(self) -> float:
        """
        Calculate percentage of lot consumed.

        Returns:
            Percentage (0-100) of original quantity consumed
        """
        if self.quantity_purchased == 0:
            return 0.0
        return (self.quantity_consumed / self.quantity_purchased) * 100

    @property
    def remaining_value(self) -> Decimal:
        """
        Calculate value of remaining inventory.

        Returns:
            quantity_remaining * cost_per_unit
        """
        return Decimal(str(self.quantity_remaining)) * self.cost_per_unit

    def consume(self, quantity: float) -> float:
        """
        Consume quantity from this lot.

        Args:
            quantity: Amount to consume (in base units)

        Returns:
            Amount actually consumed (may be less if insufficient quantity)
        """
        consumed = min(quantity, self.quantity_remaining)
        self.quantity_remaining -= consumed
        return consumed

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert material inventory item to dictionary.

        Args:
            include_relationships: If True, include product and purchase info

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["is_depleted"] = self.is_depleted
        result["quantity_consumed"] = self.quantity_consumed
        result["consumption_percentage"] = self.consumption_percentage
        result["remaining_value"] = str(self.remaining_value)

        if include_relationships:
            if self.product:
                result["product"] = {
                    "id": self.product.id,
                    "display_name": self.product.display_name,
                    "material_name": (
                        self.product.material.name if self.product.material else None
                    ),
                }
            if self.purchase:
                result["purchase"] = {
                    "id": self.purchase.id,
                    "purchase_date": (
                        self.purchase.purchase_date.isoformat()
                        if self.purchase.purchase_date
                        else None
                    ),
                }

        return result
