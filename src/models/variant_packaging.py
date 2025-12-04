"""
VariantPackaging model for detailed packaging hierarchy information.

This model stores packaging details for variants at different levels
(each, inner, case, pallet) following GS1 standards.
"""

from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel


class VariantPackaging(BaseModel):
    """
    VariantPackaging model for packaging hierarchy and specifications.

    Supports multi-level packaging (e.g., each → case → pallet) and
    GS1-compatible packaging data for future supply chain integration.

    Attributes:
        variant_id: Foreign key to Variant
        packaging_level: Level in hierarchy ("each", "inner", "case", "pallet")
        packaging_type_code: GS1 packaging type code (optional)
        packaging_material_code: GS1 packaging material code (optional)
        qty_of_next_lower_level: Quantity of next lower level (e.g., 12 each per case)
        dimensions_l_w_h_uom: JSON with length, width, height, and unit of measure
        gross_weight_value_uom: JSON with gross weight value and unit of measure
    """

    __tablename__ = "variant_packaging"

    # Foreign key to Variant
    variant_id = Column(
        Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Packaging hierarchy
    packaging_level = Column(
        String(20), nullable=False, index=True
    )  # Valid values: "each", "inner", "case", "pallet"

    # GS1 packaging codes (FUTURE READY - nullable)
    packaging_type_code = Column(String(20), nullable=True)  # GS1 packaging type
    packaging_material_code = Column(String(20), nullable=True)  # GS1 packaging material

    # Packaging quantities and hierarchy
    qty_of_next_lower_level = Column(Integer, nullable=True)  # e.g., 12 each per case

    # Physical dimensions and weight (stored as JSON for flexibility)
    dimensions_l_w_h_uom = Column(JSON, nullable=True)  # {"l": 10, "w": 8, "h": 6, "uom": "in"}
    gross_weight_value_uom = Column(JSON, nullable=True)  # {"value": 15.5, "uom": "lb"}

    # Relationships
    variant = relationship("Variant", backref="packaging_levels")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_packaging_variant", "variant_id"),
        Index("idx_packaging_level", "packaging_level"),
        CheckConstraint(
            "packaging_level IN ('each', 'inner', 'case', 'pallet')",
            name="ck_packaging_level_valid",
        ),
    )

    def __repr__(self) -> str:
        """String representation of packaging."""
        return f"VariantPackaging(id={self.id}, variant_id={self.variant_id}, level='{self.packaging_level}')"

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert packaging to dictionary.

        Args:
            include_relationships: If True, include variant info

        Returns:
            Dictionary representation
        """
        result = super().to_dict(include_relationships)

        if include_relationships and self.variant:
            result["variant"] = {"id": self.variant.id, "display_name": self.variant.display_name}

        return result
