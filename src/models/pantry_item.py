"""
PantryItem model for tracking actual inventory.

This model represents physical items currently in the pantry, including:
- What variant is on hand
- How much quantity
- When purchased and when it expires
- Where it's stored
- FIFO tracking for consumption
"""

from datetime import date, datetime

from sqlalchemy import Column, Integer, String, Float, Text, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class PantryItem(BaseModel):
    """
    PantryItem model representing actual inventory in the pantry.

    Each record represents a specific instance of a product variant that's
    currently on hand. Multiple items can exist for the same variant
    (different purchase dates, locations, expiration dates, etc.).

    FIFO Consumption:
    Items are consumed in purchase_date order (oldest first).

    Attributes:
        product_variant_id: Foreign key to ProductVariant
        quantity: Quantity on hand (in purchase units)
        purchase_date: When this item was purchased
        expiration_date: When it expires (if applicable)
        opened_date: When package was opened (if applicable)
        location: Where stored (e.g., "Main Pantry", "Garage Shelf 2")
        notes: Additional notes
        last_updated: Last modification timestamp
    """

    __tablename__ = "pantry_items"

    # Foreign key to ProductVariant
    product_variant_id = Column(
        Integer,
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Inventory tracking
    quantity = Column(Float, nullable=False, default=0.0)  # Quantity on hand

    # Date tracking
    purchase_date = Column(Date, nullable=True, index=True)  # When purchased
    expiration_date = Column(Date, nullable=True, index=True)  # When expires
    opened_date = Column(Date, nullable=True)  # When opened

    # Location tracking
    location = Column(String(100), nullable=True, index=True)  # Where stored

    # Additional information
    notes = Column(Text, nullable=True)

    # Timestamp
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product_variant = relationship("ProductVariant", back_populates="pantry_items")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_pantry_variant", "product_variant_id"),
        Index("idx_pantry_location", "location"),
        Index("idx_pantry_expiration", "expiration_date"),
        Index("idx_pantry_purchase", "purchase_date"),
    )

    def __repr__(self) -> str:
        """String representation of pantry item."""
        return (
            f"PantryItem(id={self.id}, "
            f"variant_id={self.product_variant_id}, "
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
        self.last_updated = datetime.utcnow()

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
        self.last_updated = datetime.utcnow()
        return consumed

    def add_quantity(self, quantity: float) -> None:
        """
        Add quantity to this item.

        Args:
            quantity: Amount to add
        """
        self.quantity += quantity
        self.last_updated = datetime.utcnow()

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert pantry item to dictionary.

        Args:
            include_relationships: If True, include variant information

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["is_expired"] = self.is_expired
        result["is_opened"] = self.is_opened
        result["days_until_expiration"] = self.days_until_expiration
        result["is_expiring_soon"] = self.is_expiring_soon()

        if include_relationships and self.product_variant:
            result["product_variant"] = {
                "id": self.product_variant.id,
                "display_name": self.product_variant.display_name,
                "product_name": self.product_variant.product.name,
                "product_id": self.product_variant.product.id
            }

        return result


# Module-level helper functions for FIFO operations

def get_pantry_items_fifo(product_id: int, session) -> list:
    """
    Get pantry items for a product ordered by purchase date (FIFO).

    Args:
        product_id: Product ID
        session: SQLAlchemy session

    Returns:
        List of PantryItem instances ordered by purchase_date (oldest first)
    """
    from src.models.product_variant import ProductVariant

    items = (
        session.query(PantryItem)
        .join(ProductVariant)
        .filter(ProductVariant.product_id == product_id)
        .filter(PantryItem.quantity > 0)
        .order_by(PantryItem.purchase_date.asc().nullslast())
        .all()
    )

    return items


def consume_fifo(product_id: int, quantity_needed: float, session) -> tuple:
    """
    Consume quantity from pantry using FIFO logic.

    Consumes from oldest items first, updating quantities.

    Args:
        product_id: Product ID
        quantity_needed: Amount to consume (in recipe units)
        session: SQLAlchemy session

    Returns:
        Tuple of (total_consumed, cost_breakdown)
        - total_consumed: Amount actually consumed
        - cost_breakdown: List of (item_id, quantity, cost) tuples
    """
    items = get_pantry_items_fifo(product_id, session)

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
        variant_cost = item.product_variant.get_current_cost_per_unit()
        cost = consumed * variant_cost

        cost_breakdown.append({
            "item_id": item.id,
            "variant_id": item.product_variant_id,
            "quantity": consumed,
            "cost": cost,
            "purchase_date": item.purchase_date
        })

        total_consumed += consumed
        remaining -= consumed

    return total_consumed, cost_breakdown


def get_expiring_soon(days: int = 30, session=None) -> list:
    """
    Get all pantry items expiring within specified days.

    Args:
        days: Number of days to look ahead (default: 30)
        session: SQLAlchemy session (if None, uses session_scope)

    Returns:
        List of PantryItem instances expiring soon
    """
    from datetime import timedelta
    from src.services.database import session_scope

    cutoff_date = date.today() + timedelta(days=days)

    if session:
        items = (
            session.query(PantryItem)
            .filter(
                PantryItem.expiration_date.isnot(None),
                PantryItem.expiration_date <= cutoff_date,
                PantryItem.expiration_date >= date.today(),
                PantryItem.quantity > 0
            )
            .order_by(PantryItem.expiration_date.asc())
            .all()
        )
    else:
        with session_scope() as sess:
            items = (
                sess.query(PantryItem)
                .filter(
                    PantryItem.expiration_date.isnot(None),
                    PantryItem.expiration_date <= cutoff_date,
                    PantryItem.expiration_date >= date.today(),
                    PantryItem.quantity > 0
                )
                .order_by(PantryItem.expiration_date.asc())
                .all()
            )

    return items


def get_total_quantity_for_product(product_id: int, session) -> float:
    """
    Get total quantity for a product across all pantry items.

    Args:
        product_id: Product ID
        session: SQLAlchemy session

    Returns:
        Total quantity (in purchase units, needs conversion)
    """
    from src.models.product_variant import ProductVariant

    items = (
        session.query(PantryItem)
        .join(ProductVariant)
        .filter(ProductVariant.product_id == product_id)
        .all()
    )

    # TODO: Convert quantities to common unit (recipe_unit)
    # For now, just sum raw quantities
    return sum(item.quantity for item in items)
