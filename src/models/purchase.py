"""
Purchase model for tracking shopping transactions (Feature 027).

This model records each purchase transaction, enabling:
- Price tracking over time
- Supplier tracking for each purchase
- FIFO cost calculations via linked InventoryItems
- Purchase history per product
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, ForeignKey,
    Index, CheckConstraint, Numeric
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class Purchase(BaseModel):
    """
    Purchase model representing shopping transactions.

    Each record represents a single purchase event: a product bought from
    a supplier at a specific price on a specific date.

    This model is IMMUTABLE after creation - no updated_at field.

    Attributes:
        product_id: Foreign key to Product (RESTRICT delete)
        supplier_id: Foreign key to Supplier (RESTRICT delete)
        purchase_date: When the purchase was made
        unit_price: Price per package unit (Numeric for precision)
        quantity_purchased: Number of package units bought
        notes: Optional notes (sale info, etc.)
        created_at: When this record was created

    Relationships:
        product: The Product that was purchased
        supplier: The Supplier where it was purchased
        inventory_items: InventoryItem records created from this purchase
    """

    __tablename__ = "purchases"

    # Override BaseModel's updated_at - purchases are immutable
    updated_at = None

    # Foreign keys with RESTRICT delete behavior
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Purchase details
    purchase_date = Column(Date, nullable=False, index=True)
    unit_price = Column(Numeric(10, 4), nullable=False)  # Precise decimal for prices
    quantity_purchased = Column(Integer, nullable=False)  # Number of units bought
    notes = Column(Text, nullable=True)

    # Timestamp (no updated_at - immutable)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="purchases")
    supplier = relationship("Supplier", back_populates="purchases")
    inventory_items = relationship("InventoryItem", back_populates="purchase")

    # Indexes and constraints
    __table_args__ = (
        # Check constraints for data integrity
        CheckConstraint("unit_price >= 0", name="ck_purchase_unit_price_non_negative"),
        CheckConstraint("quantity_purchased > 0", name="ck_purchase_quantity_positive"),
        # Indexes for common query patterns
        Index("idx_purchase_product", "product_id"),
        Index("idx_purchase_supplier", "supplier_id"),
        Index("idx_purchase_date", "purchase_date"),
        Index("idx_purchase_product_date", "product_id", "purchase_date"),
    )

    def __repr__(self) -> str:
        """String representation of purchase."""
        price = float(self.unit_price) if self.unit_price else 0
        return (
            f"Purchase(id={self.id}, "
            f"product_id={self.product_id}, "
            f"supplier_id={self.supplier_id}, "
            f"date={self.purchase_date}, "
            f"price=${price:.2f})"
        )

    @property
    def total_cost(self) -> Decimal:
        """
        Calculate total cost for this purchase.

        Returns:
            unit_price * quantity_purchased
        """
        return self.unit_price * self.quantity_purchased

    @property
    def unit_cost(self) -> Decimal:
        """
        Alias for unit_price (for backwards compatibility).

        Returns:
            unit_price value
        """
        return self.unit_price

    def is_recent(self, days: int = 30) -> bool:
        """
        Check if purchase is recent.

        Args:
            days: Number of days to consider recent (default: 30)

        Returns:
            True if purchase was within last N days
        """
        cutoff = date.today() - timedelta(days=days)
        return self.purchase_date >= cutoff

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert purchase to dictionary.

        Args:
            include_relationships: If True, include product/supplier info

        Returns:
            Dictionary representation
        """
        result = {
            "id": self.id,
            "uuid": self.uuid,
            "product_id": self.product_id,
            "supplier_id": self.supplier_id,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "unit_price": str(self.unit_price) if self.unit_price else None,
            "quantity_purchased": self.quantity_purchased,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "total_cost": str(self.total_cost) if self.unit_price else None,
        }

        if include_relationships:
            if self.product:
                result["product"] = {
                    "id": self.product.id,
                    "display_name": self.product.display_name,
                    "ingredient_name": self.product.ingredient.display_name,
                }
            if self.supplier:
                result["supplier_name"] = self.supplier.name
                result["supplier_location"] = self.supplier.location

        return result


# Module-level helper functions for price analysis


def get_average_price(product_id: int, days: int = 90, session=None) -> float:
    """
    Get average purchase price for a product over specified time period.

    Args:
        product_id: Product ID
        days: Number of days to look back (default: 90)
        session: SQLAlchemy session (if None, uses session_scope)

    Returns:
        Average unit price, or 0.0 if no purchases
    """
    from src.services.database import session_scope

    cutoff_date = date.today() - timedelta(days=days)

    if session:
        purchases = (
            session.query(Purchase)
            .filter(
                Purchase.product_id == product_id,
                Purchase.purchase_date >= cutoff_date,
            )
            .all()
        )
    else:
        with session_scope() as sess:
            purchases = (
                sess.query(Purchase)
                .filter(
                    Purchase.product_id == product_id,
                    Purchase.purchase_date >= cutoff_date,
                )
                .all()
            )

    if not purchases:
        return 0.0

    total_price = sum(float(p.unit_price) for p in purchases)
    return total_price / len(purchases)


def get_most_recent_price(product_id: int, session=None) -> float:
    """
    Get most recent purchase price for a product.

    Args:
        product_id: Product ID
        session: SQLAlchemy session (if None, uses session_scope)

    Returns:
        Most recent unit price, or 0.0 if no purchases
    """
    from src.services.database import session_scope

    if session:
        purchase = (
            session.query(Purchase)
            .filter(Purchase.product_id == product_id)
            .order_by(Purchase.purchase_date.desc())
            .first()
        )
    else:
        with session_scope() as sess:
            purchase = (
                sess.query(Purchase)
                .filter(Purchase.product_id == product_id)
                .order_by(Purchase.purchase_date.desc())
                .first()
            )

    return float(purchase.unit_price) if purchase else 0.0


def get_price_trend(product_id: int, days: int = 180, session=None) -> dict:
    """
    Get price trend data for a product.

    Args:
        product_id: Product ID
        days: Number of days to analyze (default: 180)
        session: SQLAlchemy session (if None, uses session_scope)

    Returns:
        Dictionary with trend analysis:
        - average: Average price over period
        - min: Lowest price
        - max: Highest price
        - trend: "increasing", "decreasing", or "stable"
        - percent_change: Percentage change from oldest to newest
    """
    from src.services.database import session_scope

    cutoff_date = date.today() - timedelta(days=days)

    if session:
        purchases = (
            session.query(Purchase)
            .filter(
                Purchase.product_id == product_id,
                Purchase.purchase_date >= cutoff_date,
            )
            .order_by(Purchase.purchase_date)
            .all()
        )
    else:
        with session_scope() as sess:
            purchases = (
                sess.query(Purchase)
                .filter(
                    Purchase.product_id == product_id,
                    Purchase.purchase_date >= cutoff_date,
                )
                .order_by(Purchase.purchase_date)
                .all()
            )

    if not purchases:
        return {"average": 0.0, "min": 0.0, "max": 0.0, "trend": "unknown", "percent_change": 0.0}

    prices = [float(p.unit_price) for p in purchases]
    average = sum(prices) / len(prices)
    min_price = min(prices)
    max_price = max(prices)

    # Calculate trend
    if len(purchases) >= 2:
        oldest_price = float(purchases[0].unit_price)
        newest_price = float(purchases[-1].unit_price)
        if oldest_price > 0:
            percent_change = ((newest_price - oldest_price) / oldest_price) * 100
        else:
            percent_change = 0.0

        if percent_change > 5:
            trend = "increasing"
        elif percent_change < -5:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        percent_change = 0.0
        trend = "stable"

    return {
        "average": average,
        "min": min_price,
        "max": max_price,
        "trend": trend,
        "percent_change": percent_change,
    }
