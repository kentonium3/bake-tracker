"""
Package models for organizing bundles into gift packages.

This module contains:
- Package: Gift packages containing one or more bundles
- PackageBundle: Junction table linking packages to bundles with quantities
"""

from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class Package(BaseModel):
    """
    Package model representing gift packages for recipients.

    Packages contain one or more bundles and can be assigned to recipients
    for specific events. Packages can be marked as templates for reuse
    across multiple events.

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
    date_added = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_modified = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    package_bundles = relationship(
        "PackageBundle",
        back_populates="package",
        cascade="all, delete-orphan",
        lazy="joined"
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

    def calculate_cost(self) -> float:
        """
        Calculate total cost of package.

        Returns:
            Total cost (sum of all bundle costs)
        """
        if not self.package_bundles:
            return 0.0

        total_cost = 0.0
        for pb in self.package_bundles:
            if pb.bundle:
                bundle_cost = pb.bundle.calculate_cost()
                total_cost += bundle_cost * pb.quantity

        return total_cost

    def get_bundle_count(self) -> int:
        """
        Get number of bundles in package.

        Returns:
            Number of bundles
        """
        return len(self.package_bundles) if self.package_bundles else 0

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert package to dictionary.

        Args:
            include_relationships: If True, include bundle details

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Add calculated fields
        result["cost"] = self.calculate_cost()
        result["bundle_count"] = self.get_bundle_count()

        return result


class PackageBundle(BaseModel):
    """
    PackageBundle junction table linking packages to bundles.

    Represents the quantity of a specific bundle included in a package.

    Attributes:
        package_id: Foreign key to Package
        bundle_id: Foreign key to Bundle
        quantity: Number of this bundle in the package
    """

    __tablename__ = "package_bundles"

    # Foreign keys
    package_id = Column(
        Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False
    )
    bundle_id = Column(
        Integer, ForeignKey("bundles.id", ondelete="RESTRICT"), nullable=False
    )

    # Quantity
    quantity = Column(Integer, nullable=False)

    # Relationships
    package = relationship("Package", back_populates="package_bundles")
    bundle = relationship("Bundle")

    # Indexes
    __table_args__ = (
        Index("idx_package_bundle_package", "package_id"),
        Index("idx_package_bundle_bundle", "bundle_id"),
    )

    def __repr__(self) -> str:
        """String representation of package bundle."""
        return f"PackageBundle(package_id={self.package_id}, bundle_id={self.bundle_id}, qty={self.quantity})"

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert package bundle to dictionary.

        Args:
            include_relationships: If True, include bundle details

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        if include_relationships and self.bundle:
            result["bundle_name"] = self.bundle.name
            result["bundle_cost"] = self.bundle.calculate_cost()

        return result
