"""
MaterialConsumption model for assembly consumption records.

This model represents a consumption record during assembly with a full
denormalized snapshot for historical accuracy.
Part of Feature 047: Materials Management System.
"""

from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    ForeignKey,
    Index,
    CheckConstraint,
    Numeric,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class MaterialConsumption(BaseModel):
    """
    MaterialConsumption model representing assembly consumption records.

    Each record captures what material was consumed during an assembly run,
    including a full denormalized snapshot of the product/material hierarchy
    at the time of consumption. This ensures historical accuracy even if
    catalog data changes later.

    This model is IMMUTABLE after creation - no updated_at field.

    Attributes:
        assembly_run_id: Foreign key to parent AssemblyRun
        product_id: Foreign key to MaterialProduct (nullable for historical ref)
        quantity_consumed: Base units consumed
        unit_cost: Cost per base unit at consumption time
        total_cost: Total cost (quantity * unit_cost)

        Snapshot fields (denormalized for history):
        product_name: Product name at consumption time
        material_name: Material name at consumption time
        subcategory_name: Subcategory name at consumption time
        category_name: Category name at consumption time
        supplier_name: Supplier name at consumption time (nullable)

    Relationships:
        assembly_run: Many-to-One with AssemblyRun (existing table)
        product: Many-to-One with MaterialProduct (nullable)
    """

    __tablename__ = "material_consumptions"

    # Override BaseModel's updated_at - consumption records are immutable
    updated_at = None

    # Foreign keys
    assembly_run_id = Column(
        Integer,
        ForeignKey("assembly_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("material_products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Consumption data
    quantity_consumed = Column(Float, nullable=False)
    unit_cost = Column(Numeric(10, 4), nullable=False)
    total_cost = Column(Numeric(10, 4), nullable=False)

    # Snapshot fields (denormalized for historical accuracy)
    product_name = Column(String(200), nullable=False)
    material_name = Column(String(200), nullable=False)
    subcategory_name = Column(String(100), nullable=False)
    category_name = Column(String(100), nullable=False)
    supplier_name = Column(String(200), nullable=True)

    # Relationships
    assembly_run = relationship(
        "AssemblyRun",
        foreign_keys=[assembly_run_id],
    )
    product = relationship(
        "MaterialProduct",
        foreign_keys=[product_id],
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_material_consumption_assembly_run", "assembly_run_id"),
        Index("idx_material_consumption_product", "product_id"),
        CheckConstraint("quantity_consumed > 0", name="ck_material_consumption_quantity_positive"),
        CheckConstraint("total_cost >= 0", name="ck_material_consumption_cost_non_negative"),
    )

    def __repr__(self) -> str:
        """String representation of material consumption."""
        return (
            f"MaterialConsumption(id={self.id}, "
            f"assembly_run_id={self.assembly_run_id}, "
            f"product_name='{self.product_name}', "
            f"quantity={self.quantity_consumed})"
        )

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert material consumption to dictionary.

        Args:
            include_relationships: If True, include assembly_run details

        Returns:
            Dictionary representation with formatted fields
        """
        result = {
            "id": self.id,
            "uuid": self.uuid,
            "assembly_run_id": self.assembly_run_id,
            "product_id": self.product_id,
            "quantity_consumed": self.quantity_consumed,
            "unit_cost": str(self.unit_cost) if self.unit_cost else None,
            "total_cost": str(self.total_cost) if self.total_cost else None,
            # Snapshot fields
            "product_name": self.product_name,
            "material_name": self.material_name,
            "subcategory_name": self.subcategory_name,
            "category_name": self.category_name,
            "supplier_name": self.supplier_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if include_relationships:
            if self.assembly_run:
                result["assembly_run"] = {
                    "id": self.assembly_run.id,
                    "assembled_at": (
                        self.assembly_run.assembled_at.isoformat()
                        if self.assembly_run.assembled_at
                        else None
                    ),
                }

        return result
