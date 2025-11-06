"""
PurchaseHistory model for tracking ingredient purchase events and price history.

This model records each purchase transaction, enabling:
- Price trend analysis
- Cost tracking over time
- Receipt reference
- Purchase frequency analysis
"""

from datetime import date, datetime, timedelta

from sqlalchemy import Column, Integer, String, Float, Text, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class PurchaseHistory(BaseModel):
    """
    PurchaseHistory model representing individual purchase transactions.

    Each record represents a single purchase event for a specific product variant.

    Attributes:
        product_variant_id: Foreign key to ProductVariant
        purchase_date: When the purchase was made
        unit_cost: Cost per purchase unit
        quantity_purchased: How many units were purchased
        total_cost: Total cost (quantity × unit_cost)
        supplier: Where purchased (can differ from variant's default)
        receipt_number: Optional receipt reference
        notes: Additional notes
        created_at: When this record was created
    """

    __tablename__ = "purchase_history"

    # Foreign key to ProductVariant
    product_variant_id = Column(
        Integer,
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Purchase details
    purchase_date = Column(Date, nullable=False, index=True)
    unit_cost = Column(Float, nullable=False)  # Cost per purchase unit
    quantity_purchased = Column(Float, nullable=False)  # Quantity purchased
    total_cost = Column(Float, nullable=False)  # Total cost

    # Purchase metadata
    supplier = Column(String(200), nullable=True)  # Where purchased
    receipt_number = Column(String(100), nullable=True)  # Receipt reference
    notes = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    product_variant = relationship("ProductVariant", back_populates="purchases")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_purchase_variant", "product_variant_id"),
        Index("idx_purchase_date", "purchase_date"),
    )

    def __repr__(self) -> str:
        """String representation of purchase."""
        return (
            f"PurchaseHistory(id={self.id}, "
            f"variant_id={self.product_variant_id}, "
            f"date={self.purchase_date}, "
            f"cost=${self.total_cost:.2f})"
        )

    @property
    def cost_per_unit(self) -> float:
        """
        Get cost per unit (same as unit_cost, provided for clarity).

        Returns:
            Cost per purchase unit
        """
        return self.unit_cost

    @property
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
            include_relationships: If True, include variant information

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["cost_per_unit"] = self.cost_per_unit
        result["is_recent"] = self.is_recent

        if include_relationships and self.product_variant:
            result["product_variant"] = {
                "id": self.product_variant.id,
                "display_name": self.product_variant.display_name,
                "product_name": self.product_variant.product.name
            }

        return result


# Module-level helper functions for price analysis

def get_average_price(product_variant_id: int, days: int = 90, session=None) -> float:
    """
    Get average purchase price for a variant over specified time period.

    Args:
        product_variant_id: ProductVariant ID
        days: Number of days to look back (default: 90)
        session: SQLAlchemy session (if None, uses session_scope)

    Returns:
        Average unit cost, or 0.0 if no purchases
    """
    from src.services.database import session_scope

    cutoff_date = date.today() - timedelta(days=days)

    if session:
        purchases = (
            session.query(PurchaseHistory)
            .filter(
                PurchaseHistory.product_variant_id == product_variant_id,
                PurchaseHistory.purchase_date >= cutoff_date
            )
            .all()
        )
    else:
        with session_scope() as sess:
            purchases = (
                sess.query(PurchaseHistory)
                .filter(
                    PurchaseHistory.product_variant_id == product_variant_id,
                    PurchaseHistory.purchase_date >= cutoff_date
                )
                .all()
            )

    if not purchases:
        return 0.0

    total_cost = sum(p.unit_cost for p in purchases)
    return total_cost / len(purchases)


def get_most_recent_price(product_variant_id: int, session=None) -> float:
    """
    Get most recent purchase price for a variant.

    Args:
        product_variant_id: ProductVariant ID
        session: SQLAlchemy session (if None, uses session_scope)

    Returns:
        Most recent unit cost, or 0.0 if no purchases
    """
    from src.services.database import session_scope

    if session:
        purchase = (
            session.query(PurchaseHistory)
            .filter(PurchaseHistory.product_variant_id == product_variant_id)
            .order_by(PurchaseHistory.purchase_date.desc())
            .first()
        )
    else:
        with session_scope() as sess:
            purchase = (
                sess.query(PurchaseHistory)
                .filter(PurchaseHistory.product_variant_id == product_variant_id)
                .order_by(PurchaseHistory.purchase_date.desc())
                .first()
            )

    return purchase.unit_cost if purchase else 0.0


def get_price_trend(product_variant_id: int, days: int = 180, session=None) -> dict:
    """
    Get price trend data for a variant.

    Args:
        product_variant_id: ProductVariant ID
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
            session.query(PurchaseHistory)
            .filter(
                PurchaseHistory.product_variant_id == product_variant_id,
                PurchaseHistory.purchase_date >= cutoff_date
            )
            .order_by(PurchaseHistory.purchase_date)
            .all()
        )
    else:
        with session_scope() as sess:
            purchases = (
                sess.query(PurchaseHistory)
                .filter(
                    PurchaseHistory.product_variant_id == product_variant_id,
                    PurchaseHistory.purchase_date >= cutoff_date
                )
                .order_by(PurchaseHistory.purchase_date)
                .all()
            )

    if not purchases:
        return {
            "average": 0.0,
            "min": 0.0,
            "max": 0.0,
            "trend": "unknown",
            "percent_change": 0.0
        }

    prices = [p.unit_cost for p in purchases]
    average = sum(prices) / len(prices)
    min_price = min(prices)
    max_price = max(prices)

    # Calculate trend
    if len(purchases) >= 2:
        oldest_price = purchases[0].unit_cost
        newest_price = purchases[-1].unit_cost
        percent_change = ((newest_price - oldest_price) / oldest_price) * 100

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
        "percent_change": percent_change
    }
