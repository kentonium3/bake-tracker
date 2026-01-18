"""
MaterialPurchase model for purchase transactions.

This model represents a purchase transaction with an immutable cost snapshot.
Part of Feature 047: Materials Management System.
"""

from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Date,
    ForeignKey,
    Index,
    CheckConstraint,
    Numeric,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class MaterialPurchase(BaseModel):
    """
    MaterialPurchase model representing purchase transactions.

    Each record represents a single purchase event: a material product bought
    from a supplier at a specific price on a specific date.

    This model is IMMUTABLE after creation - no updated_at field.

    Attributes:
        product_id: Foreign key to MaterialProduct
        supplier_id: Foreign key to Supplier
        purchase_date: Date of purchase
        packages_purchased: Number of packages bought
        package_price: Price per package
        units_added: Total base units added to inventory
        unit_cost: Cost per base unit (immutable snapshot)
        notes: Purchase notes

    Relationships:
        product: Many-to-One with MaterialProduct
        supplier: Many-to-One with Supplier
    """

    __tablename__ = "material_purchases"

    # Override BaseModel's updated_at - purchases are immutable
    updated_at = None

    # Foreign keys
    product_id = Column(
        Integer,
        ForeignKey("material_products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Purchase details
    purchase_date = Column(Date, nullable=False, index=True)
    packages_purchased = Column(Integer, nullable=False)
    package_price = Column(Numeric(10, 4), nullable=False)
    units_added = Column(Float, nullable=False)
    unit_cost = Column(Numeric(10, 4), nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    product = relationship(
        "MaterialProduct",
        back_populates="purchases",
    )
    supplier = relationship(
        "Supplier",
        foreign_keys=[supplier_id],
    )
    # Feature 058: One purchase creates exactly one inventory item (1:1)
    inventory_item = relationship(
        "MaterialInventoryItem",
        back_populates="purchase",
        uselist=False,  # 1:1 relationship
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_material_purchase_product", "product_id"),
        Index("idx_material_purchase_supplier", "supplier_id"),
        Index("idx_material_purchase_date", "purchase_date"),
        CheckConstraint("packages_purchased > 0", name="ck_material_purchase_packages_positive"),
        CheckConstraint("package_price >= 0", name="ck_material_purchase_price_non_negative"),
        CheckConstraint("units_added > 0", name="ck_material_purchase_units_positive"),
        CheckConstraint("unit_cost >= 0", name="ck_material_purchase_unit_cost_non_negative"),
    )

    def __repr__(self) -> str:
        """String representation of material purchase."""
        price = float(self.package_price) if self.package_price else 0
        return (
            f"MaterialPurchase(id={self.id}, "
            f"product_id={self.product_id}, "
            f"date={self.purchase_date}, "
            f"packages={self.packages_purchased}, "
            f"price=${price:.2f})"
        )

    @property
    def total_cost(self) -> Decimal:
        """
        Calculate total cost for this purchase.

        Returns:
            package_price * packages_purchased
        """
        return self.package_price * self.packages_purchased

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert material purchase to dictionary.

        Args:
            include_relationships: If True, include product and supplier

        Returns:
            Dictionary representation
        """
        result = {
            "id": self.id,
            "uuid": self.uuid,
            "product_id": self.product_id,
            "supplier_id": self.supplier_id,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "packages_purchased": self.packages_purchased,
            "package_price": str(self.package_price) if self.package_price else None,
            "units_added": self.units_added,
            "unit_cost": str(self.unit_cost) if self.unit_cost else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "total_cost": str(self.total_cost) if self.package_price else None,
        }

        if include_relationships:
            if self.product:
                result["product"] = {
                    "id": self.product.id,
                    "display_name": self.product.display_name,
                    "material_name": self.product.material.name if self.product.material else None,
                }
            if self.supplier:
                result["supplier_name"] = self.supplier.name

        return result
