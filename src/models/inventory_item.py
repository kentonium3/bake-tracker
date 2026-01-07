"""
InventoryItem model for tracking actual inventory.

This model represents physical items currently in inventory, including:
- What product is on hand
- How much quantity
- When purchased and when it expires
- Where it's stored
- FIFO tracking for consumption

Note: Renamed from PantryItem to InventoryItem for consistent domain naming.
"""

from datetime import date, datetime

from sqlalchemy import Column, Integer, String, Float, Text, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class InventoryItem(BaseModel):
    """
    InventoryItem model representing actual inventory on hand.

    Each record represents a specific instance of a product that's
    currently on hand. Multiple items can exist for the same product
    (different purchase dates, locations, expiration dates, etc.).

    FIFO Consumption:
    Items are consumed in purchase_date order (oldest first).

    Attributes:
        product_id: Foreign key to Product
        quantity: Quantity on hand (in purchase units)
        unit_cost: Cost per unit at time of purchase (for FIFO costing)
        purchase_date: When this item was purchased
        expiration_date: When it expires (if applicable)
        opened_date: When package was opened (if applicable)
        location: Where stored (e.g., "Main Storage", "Garage Shelf 2")
        notes: Additional notes
        last_updated: Last modification timestamp
    """

    __tablename__ = "inventory_items"

    # Foreign key to Product
    product_id = Column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Feature 027: Link to Purchase record
    purchase_id = Column(
        Integer,
        ForeignKey("purchases.id", ondelete="RESTRICT"),
        nullable=True,  # Nullable for migration transition
        index=True
    )

    # Inventory tracking
    quantity = Column(Float, nullable=False, default=0.0)  # Quantity on hand (qty_on_hand in spec)
    unit_cost = Column(Float, nullable=True)  # Cost per unit at time of purchase (for FIFO costing)

    # Date tracking
    purchase_date = Column(Date, nullable=True, index=True)  # When purchased
    expiration_date = Column(Date, nullable=True, index=True)  # When expires (best_by in spec)
    opened_date = Column(Date, nullable=True)  # When opened (opened_at in spec)

    # Location tracking
    location = Column(String(100), nullable=True, index=True)  # Where stored

    # Industry standard tracking (FUTURE READY - nullable)
    lot_or_batch = Column(String(100), nullable=True)  # Lot or batch number for tracking

    # Additional information
    notes = Column(Text, nullable=True)

    # Timestamp
    last_updated = Column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    product = relationship("Product", back_populates="inventory_items")
    purchase = relationship("Purchase", back_populates="inventory_items")
    depletions = relationship("InventoryDepletion", back_populates="inventory_item")  # Feature 041

    # Indexes for common queries
    __table_args__ = (
        Index("idx_inventory_product", "product_id"),
        Index("idx_inventory_location", "location"),
        Index("idx_inventory_expiration", "expiration_date"),
        Index("idx_inventory_purchase", "purchase_date"),
        # Feature 027: Index for purchase_id
        Index("idx_inventory_purchase_id", "purchase_id"),
    )

    def __repr__(self) -> str:
        """String representation of inventory item."""
        return (
            f"InventoryItem(id={self.id}, "
            f"product_id={self.product_id}, "
            f"quantity={self.quantity}, "
            f"location='{self.location}')"
        )

    @property
    def is_expired(self) -> bool:
        """
        Check if item is expired.

        Returns:
            True if expiration_date is in the past
        """
        if not self.expiration_date:
            return False
        return self.expiration_date < date.today()

    @property
    def is_opened(self) -> bool:
        """
        Check if package has been opened.

        Returns:
            True if opened_date is set
        """
        return self.opened_date is not None

    @property
    def days_until_expiration(self) -> int:
        """
        Get days until expiration.

        Returns:
            Days until expiration, or None if no expiration date
        """
        if not self.expiration_date:
            return None

        delta = self.expiration_date - date.today()
        return delta.days

    def is_expiring_soon(self, days: int = 30) -> bool:
        """
        Check if item is expiring soon.

        Args:
            days: Threshold in days (default: 30)

        Returns:
            True if expiring within specified days
        """
        days_left = self.days_until_expiration
        if days_left is None:
            return False
        return 0 < days_left <= days

    def update_quantity(self, new_quantity: float) -> None:
        """
        Update item quantity and timestamp.

        Args:
            new_quantity: New quantity value
        """
        self.quantity = new_quantity
        self.last_updated = utc_now()

    def consume(self, quantity: float) -> float:
        """
        Consume quantity from this item (FIFO logic).

        Args:
            quantity: Amount to consume

        Returns:
            Amount actually consumed (may be less if insufficient quantity)
        """
        consumed = min(quantity, self.quantity)
        self.quantity -= consumed
        self.last_updated = utc_now()
        return consumed

    def add_quantity(self, quantity: float) -> None:
        """
        Add quantity to this item.

        Args:
            quantity: Amount to add
        """
        self.quantity += quantity
        self.last_updated = utc_now()

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert inventory item to dictionary.

        Args:
            include_relationships: If True, include product information

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["is_expired"] = self.is_expired
        result["is_opened"] = self.is_opened
        result["days_until_expiration"] = self.days_until_expiration
        result["is_expiring_soon"] = self.is_expiring_soon()

        if include_relationships and self.product:
            result["product"] = {
                "id": self.product.id,
                "display_name": self.product.display_name,
                "ingredient_name": self.product.ingredient.display_name,
                "ingredient_id": self.product.ingredient.id,
            }

        return result


# Module-level helper functions for FIFO operations


def get_inventory_items_fifo(ingredient_id: int, session) -> list:
    """
    Get inventory items for an ingredient ordered by purchase date (FIFO).

    Args:
        ingredient_id: Ingredient ID
        session: SQLAlchemy session

    Returns:
        List of InventoryItem instances ordered by purchase_date (oldest first)
    """
    from src.models.product import Product

    items = (
        session.query(InventoryItem)
        .join(Product)
        .filter(Product.ingredient_id == ingredient_id)
        .filter(InventoryItem.quantity > 0)
        .order_by(InventoryItem.purchase_date.asc().nullslast())
        .all()
    )

    return items


def consume_fifo(ingredient_id: int, quantity_needed: float, session) -> tuple:
    """
    Consume quantity from inventory using FIFO logic.

    Consumes from oldest items first, updating quantities.

    Args:
        ingredient_id: Ingredient ID
        quantity_needed: Amount to consume (in recipe units)
        session: SQLAlchemy session

    Returns:
        Tuple of (total_consumed, cost_breakdown)
        - total_consumed: Amount actually consumed
        - cost_breakdown: List of (item_id, quantity, cost) tuples
    """
    items = get_inventory_items_fifo(ingredient_id, session)

    total_consumed = 0.0
    cost_breakdown = []
    remaining = quantity_needed

    for item in items:
        if remaining <= 0:
            break

        # TODO: Convert item.quantity from purchase units to recipe units
        # For now, assuming same units
        available = item.quantity

        consumed = min(remaining, available)
        item.consume(consumed)

        # Calculate cost for this consumption
        product_cost = item.product.get_current_cost_per_unit()
        cost = consumed * product_cost

        cost_breakdown.append(
            {
                "item_id": item.id,
                "product_id": item.product_id,
                "quantity": consumed,
                "cost": cost,
                "purchase_date": item.purchase_date,
            }
        )

        total_consumed += consumed
        remaining -= consumed

    return total_consumed, cost_breakdown


def get_expiring_soon(days: int = 30, session=None) -> list:
    """
    Get all inventory items expiring within specified days.

    Args:
        days: Number of days to look ahead (default: 30)
        session: SQLAlchemy session (if None, uses session_scope)

    Returns:
        List of InventoryItem instances expiring soon
    """
    from datetime import timedelta
    from src.services.database import session_scope

    cutoff_date = date.today() + timedelta(days=days)

    if session:
        items = (
            session.query(InventoryItem)
            .filter(
                InventoryItem.expiration_date.isnot(None),
                InventoryItem.expiration_date <= cutoff_date,
                InventoryItem.expiration_date >= date.today(),
                InventoryItem.quantity > 0,
            )
            .order_by(InventoryItem.expiration_date.asc())
            .all()
        )
    else:
        with session_scope() as sess:
            items = (
                sess.query(InventoryItem)
                .filter(
                    InventoryItem.expiration_date.isnot(None),
                    InventoryItem.expiration_date <= cutoff_date,
                    InventoryItem.expiration_date >= date.today(),
                    InventoryItem.quantity > 0,
                )
                .order_by(InventoryItem.expiration_date.asc())
                .all()
            )

    return items


def get_total_quantity_for_ingredient(ingredient_id: int, session) -> float:
    """
    Get total quantity for an ingredient across all inventory items.

    Args:
        ingredient_id: Ingredient ID
        session: SQLAlchemy session

    Returns:
        Total quantity (in purchase units, needs conversion)
    """
    from src.models.product import Product

    items = session.query(InventoryItem).join(Product).filter(Product.ingredient_id == ingredient_id).all()

    # TODO: Convert quantities to common unit (recipe_unit)
    # For now, just sum raw quantities
    return sum(item.quantity for item in items)
