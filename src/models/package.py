"""
Package models for organizing FinishedGood assemblies into gift packages.

This module contains:
- Package: Gift packages containing one or more FinishedGood assemblies
- PackageFinishedGood: Junction table linking packages to FinishedGoods with quantities

Architecture Note (Feature 006):
- Bundle concept eliminated per research decision D1
- Package now directly references FinishedGood assemblies via PackageFinishedGood junction
- FinishedGood assemblies are created via Features 002-004 (Composition model)
- Cost calculation: See Feature 045 - costs are now on production/assembly instances, not definitions
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class Package(BaseModel):
    """
    Package model representing gift packages for recipients.

    Packages contain one or more FinishedGood assemblies and can be assigned
    to recipients for specific events. Packages can be marked as templates
    for reuse across multiple events.

    Attributes:
        name: Package name (e.g., "Deluxe Cookie Assortment", "Standard Gift Box")
        description: Package description
        is_template: Whether this package is a template for reuse
        notes: Additional notes
    """

    __tablename__ = "packages"

    # Basic information
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_template = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)

    # Timestamps
    date_added = Column(DateTime, nullable=False, default=utc_now)
    last_modified = Column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    package_finished_goods = relationship(
        "PackageFinishedGood",
        back_populates="package",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # Packaging compositions (Feature 011) - packaging materials for this package
    packaging_compositions = relationship(
        "Composition",
        foreign_keys="Composition.package_id",
        back_populates="package",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index("idx_package_name", "name"),
        Index("idx_package_is_template", "is_template"),
    )

    def __repr__(self) -> str:
        """String representation of package."""
        template_str = " (Template)" if self.is_template else ""
        return f"Package(id={self.id}, name='{self.name}'{template_str})"

    def calculate_cost(self) -> Decimal:
        """
        Calculate total package cost from FinishedGood component costs.

        Uses dynamic cost calculation from FinishedGood.calculate_current_cost()
        following the F045/F046 "Costs on Instances, Not Definitions" principle.

        Returns:
            Decimal: Total cost for the package, or Decimal("0.00") if no contents
        """
        if not self.package_finished_goods:
            return Decimal("0.00")

        total = Decimal("0.00")
        for pfg in self.package_finished_goods:
            if pfg.finished_good:
                unit_cost = pfg.finished_good.calculate_current_cost()
                total += unit_cost * Decimal(str(pfg.quantity))

        return total.quantize(Decimal("0.01"))

    def get_item_count(self) -> int:
        """
        Get number of distinct FinishedGood items in package.

        Returns:
            Number of distinct FinishedGood entries
        """
        return len(self.package_finished_goods) if self.package_finished_goods else 0

    def get_total_quantity(self) -> int:
        """
        Get total quantity of items across all FinishedGoods.

        Returns:
            Sum of all quantities
        """
        if not self.package_finished_goods:
            return 0
        return sum(pfg.quantity for pfg in self.package_finished_goods)

    def get_cost_breakdown(self) -> list:
        """
        Get detailed cost breakdown by FinishedGood.

        Returns:
            List of dictionaries with item name, quantity, unit cost, and line total
        """
        if not self.package_finished_goods:
            return []

        breakdown = []
        for pfg in self.package_finished_goods:
            if pfg.finished_good:
                fg = pfg.finished_good
                unit_cost = fg.calculate_current_cost()
                line_total = unit_cost * Decimal(str(pfg.quantity))
                breakdown.append(
                    {
                        "finished_good_id": fg.id,
                        "name": fg.display_name,
                        "quantity": pfg.quantity,
                        "unit_cost": float(unit_cost),
                        "line_total": float(line_total.quantize(Decimal("0.01"))),
                    }
                )

        return breakdown

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert package to dictionary.

        Args:
            include_relationships: If True, include FinishedGood details

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["cost"] = float(self.calculate_cost())
        result["item_count"] = self.get_item_count()
        result["total_quantity"] = self.get_total_quantity()

        if include_relationships:
            result["cost_breakdown"] = self.get_cost_breakdown()

        return result


class PackageFinishedGood(BaseModel):
    """
    PackageFinishedGood junction table linking packages to FinishedGood assemblies.

    Represents the quantity of a specific FinishedGood assembly included in a package.
    Replaces the removed PackageBundle model per Feature 006 architecture.

    Attributes:
        package_id: Foreign key to Package (CASCADE on delete)
        finished_good_id: Foreign key to FinishedGood (RESTRICT on delete)
        quantity: Number of this FinishedGood in the package
    """

    __tablename__ = "package_finished_goods"

    # Foreign keys
    package_id = Column(
        Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finished_good_id = Column(
        Integer, ForeignKey("finished_goods.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Quantity
    quantity = Column(Integer, nullable=False, default=1)

    # Relationships
    package = relationship("Package", back_populates="package_finished_goods", lazy="joined")
    finished_good = relationship("FinishedGood", lazy="joined")

    # Indexes
    __table_args__ = (
        Index("idx_package_fg_package", "package_id"),
        Index("idx_package_fg_finished_good", "finished_good_id"),
    )

    def __repr__(self) -> str:
        """String representation of package-finished good link."""
        return f"PackageFinishedGood(package_id={self.package_id}, finished_good_id={self.finished_good_id}, qty={self.quantity})"

    def get_line_cost(self) -> Decimal:
        """
        Calculate line cost for this finished good entry.

        Uses dynamic cost calculation from FinishedGood.calculate_current_cost()
        following the F045/F046 "Costs on Instances, Not Definitions" principle.

        Returns:
            Decimal: Unit cost * quantity, or Decimal("0.00") if no finished good
        """
        if not self.finished_good:
            return Decimal("0.00")
        unit_cost = self.finished_good.calculate_current_cost()
        return (unit_cost * Decimal(str(self.quantity))).quantize(Decimal("0.01"))

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert package-finished good link to dictionary.

        Args:
            include_relationships: If True, include FinishedGood details

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        if include_relationships and self.finished_good:
            result["finished_good_name"] = self.finished_good.display_name
            result["finished_good_cost"] = float(self.finished_good.calculate_current_cost())
            result["line_cost"] = float(self.get_line_cost())

        return result
