"""
Composition junction model for polymorphic component references in assemblies.

This model enables FinishedGoods to contain both FinishedUnits and other FinishedGoods
through a flexible association object pattern with proper referential integrity
constraints.

Key Features:
- Polymorphic references supporting FinishedUnit, FinishedGood, packaging, and MaterialUnit
- 4-way XOR constraint ensuring exactly one component type is specified per composition
- Sort ordering for consistent component presentation
- Component quantity and notes for assembly instructions

Feature 084: Removed material_id column and 5-way XOR constraint.
All material compositions must now use material_unit_id.
"""

from sqlalchemy import (
    Column,
    Integer,
    Float,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class Composition(BaseModel):
    """
    Composition junction model for polymorphic component relationships.

    This association object pattern allows FinishedGoods to contain multiple
    components where each component can be either a FinishedUnit (individual item)
    or another FinishedGood (sub-assembly).

    Key Features:
    - Polymorphic component references with integrity constraints
    - Exactly one of finished_unit_id or finished_good_id must be non-null
    - Component quantity for multi-item compositions
    - Sort ordering for consistent presentation
    - Component-specific notes for assembly instructions

    Attributes:
        assembly_id: Foreign key to parent FinishedGood assembly
        finished_unit_id: Foreign key to FinishedUnit component (if applicable)
        finished_good_id: Foreign key to FinishedGood sub-assembly (if applicable)
        component_quantity: Number of this component in the assembly
        component_notes: Notes specific to this component's inclusion
        sort_order: Display order for components (lower = earlier)
    """

    __tablename__ = "compositions"

    # Parent references (exactly one must be non-null: assembly_id XOR package_id)
    assembly_id = Column(
        Integer, ForeignKey("finished_goods.id", ondelete="CASCADE"), nullable=True, index=True
    )
    package_id = Column(
        Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Polymorphic component references (exactly one must be non-null)
    finished_unit_id = Column(
        Integer, ForeignKey("finished_units.id", ondelete="CASCADE"), nullable=True, index=True
    )
    finished_good_id = Column(
        Integer, ForeignKey("finished_goods.id", ondelete="CASCADE"), nullable=True, index=True
    )
    packaging_product_id = Column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    # Feature 047: Materials Management System - material component references
    # Feature 084: material_id removed - use material_unit_id for all material compositions
    material_unit_id = Column(
        Integer, ForeignKey("material_units.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    # Component attributes
    component_quantity = Column(Float, nullable=False, default=1.0)
    component_notes = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)

    # Generic packaging flag (Feature 026)
    # When True, packaging_product_id references a template product whose
    # product_name defines the generic requirement (e.g., "gift box")
    # Actual assignments are tracked in CompositionAssignment table
    is_generic = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    assembly = relationship(
        "FinishedGood", foreign_keys=[assembly_id], back_populates="components", lazy="joined"
    )
    package = relationship(
        "Package", foreign_keys=[package_id], back_populates="packaging_compositions", lazy="joined"
    )

    finished_unit_component = relationship(
        "FinishedUnit", foreign_keys=[finished_unit_id], lazy="joined"
    )
    finished_good_component = relationship(
        "FinishedGood", foreign_keys=[finished_good_id], lazy="joined"
    )
    packaging_product = relationship("Product", foreign_keys=[packaging_product_id], lazy="joined")
    # Feature 047: Materials Management System
    # Feature 084: material_component removed - use material_unit_component only
    material_unit_component = relationship(
        "MaterialUnit", foreign_keys=[material_unit_id], lazy="joined"
    )

    # Table constraints and indexes
    __table_args__ = (
        # Primary indexes
        Index("idx_composition_assembly", "assembly_id"),
        Index("idx_composition_package", "package_id"),
        Index("idx_composition_finished_unit", "finished_unit_id"),
        Index("idx_composition_finished_good", "finished_good_id"),
        Index("idx_composition_packaging_product", "packaging_product_id"),
        Index("idx_composition_sort_order", "assembly_id", "sort_order"),
        # Feature 047: Material component indexes
        # Feature 084: idx_composition_material removed (material_id column removed)
        Index("idx_composition_material_unit", "material_unit_id"),
        # Parent XOR constraint: exactly one of assembly_id or package_id must be set
        CheckConstraint(
            "(assembly_id IS NOT NULL AND package_id IS NULL) OR "
            "(assembly_id IS NULL AND package_id IS NOT NULL)",
            name="ck_composition_exactly_one_parent",
        ),
        # Component XOR constraint: exactly one component type must be set (4-way)
        # Feature 084: Reduced from 5-way to 4-way (material_id removed)
        CheckConstraint(
            "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND "
            "packaging_product_id IS NULL AND material_unit_id IS NULL) OR "
            "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND "
            "packaging_product_id IS NULL AND material_unit_id IS NULL) OR "
            "(finished_unit_id IS NULL AND finished_good_id IS NULL AND "
            "packaging_product_id IS NOT NULL AND material_unit_id IS NULL) OR "
            "(finished_unit_id IS NULL AND finished_good_id IS NULL AND "
            "packaging_product_id IS NULL AND material_unit_id IS NOT NULL)",
            name="ck_composition_exactly_one_component",
        ),
        # Positive quantity constraint
        CheckConstraint(
            "component_quantity > 0", name="ck_composition_component_quantity_positive"
        ),
        # Non-negative sort order constraint
        CheckConstraint("sort_order >= 0", name="ck_composition_sort_order_non_negative"),
        # Prevent self-referential assemblies
        CheckConstraint("assembly_id != finished_good_id", name="ck_composition_no_self_reference"),
        # Unique component within assembly (prevent duplicates)
        UniqueConstraint("assembly_id", "finished_unit_id", name="uq_composition_assembly_unit"),
        UniqueConstraint("assembly_id", "finished_good_id", name="uq_composition_assembly_good"),
        UniqueConstraint(
            "assembly_id", "packaging_product_id", name="uq_composition_assembly_packaging"
        ),
        UniqueConstraint(
            "package_id", "packaging_product_id", name="uq_composition_package_packaging"
        ),
        # Feature 047: Material component uniqueness constraints
        # Feature 084: uq_composition_assembly_material removed (material_id column removed)
        UniqueConstraint(
            "assembly_id", "material_unit_id", name="uq_composition_assembly_material_unit"
        ),
    )

    def __repr__(self) -> str:
        """String representation of composition."""
        if self.finished_unit_id:
            component_type = "unit"
            component_id = self.finished_unit_id
        elif self.finished_good_id:
            component_type = "assembly"
            component_id = self.finished_good_id
        elif self.packaging_product_id:
            component_type = "packaging"
            component_id = self.packaging_product_id
        elif self.material_unit_id:
            component_type = "material_unit"
            component_id = self.material_unit_id
        # Feature 084: Removed material_id branch
        else:
            component_type = "unknown"
            component_id = None
        parent_type = "assembly" if self.assembly_id else "package"
        parent_id = self.assembly_id or self.package_id
        generic_flag = ", generic=True" if self.is_generic else ""
        return (
            f"Composition(id={self.id}, {parent_type}_id={parent_id}, "
            f"{component_type}={component_id}, qty={self.component_quantity}{generic_flag})"
        )

    @property
    def component_type(self) -> str:
        """
        Get the type of component referenced.

        Returns:
            "finished_unit", "finished_good", "packaging_product",
            "material_unit", or "unknown"

        Note (Feature 084): "material" type removed - use material_unit_id only.
        """
        if self.finished_unit_id is not None:
            return "finished_unit"
        elif self.finished_good_id is not None:
            return "finished_good"
        elif self.packaging_product_id is not None:
            return "packaging_product"
        elif self.material_unit_id is not None:
            return "material_unit"
        # Feature 084: Removed material_id branch
        else:
            return "unknown"

    @property
    def component_id(self) -> int:
        """
        Get the ID of the referenced component.

        Returns:
            Component ID or None if no valid component

        Note (Feature 084): material_id removed from component types.
        """
        return (
            self.finished_unit_id
            or self.finished_good_id
            or self.packaging_product_id
            or self.material_unit_id
            # Feature 084: Removed material_id
        )

    @property
    def component_name(self) -> str:
        """
        Get the display name of the referenced component.

        Returns:
            Component display name or "Unknown Component"

        Note (Feature 084): material_component removed - use material_unit_component only.
        """
        if self.finished_unit_component:
            return self.finished_unit_component.display_name
        elif self.finished_good_component:
            return self.finished_good_component.display_name
        elif self.packaging_product:
            return self.packaging_product.display_name
        elif self.material_unit_component:
            return self.material_unit_component.name
        # Feature 084: Removed material_component branch
        else:
            return "Unknown Component"

    def get_component_cost(self) -> float:
        """
        Get the unit cost of the referenced component.

        Uses dynamic cost calculation via calculate_current_cost() for
        FinishedUnit and FinishedGood components (F046).

        For MaterialUnit components (F047), calculates from relationship data.

        Note (Feature 084): Generic Material placeholder support removed.
        All material compositions must use material_unit_id.

        Returns:
            Unit cost for the component (dynamic calculation, not stored)
        """
        if self.finished_unit_component:
            return float(self.finished_unit_component.calculate_current_cost())
        elif self.finished_good_component:
            return float(self.finished_good_component.calculate_current_cost())
        elif self.packaging_product:
            # Packaging products have purchase_price per unit
            return float(self.packaging_product.purchase_price or 0.0)
        elif self.material_unit_component:
            # MaterialUnit - calculate cost from relationship data
            # cost = weighted_avg_cost * quantity_per_unit
            return self._calculate_material_unit_cost()
        # Feature 084: Removed material_component branch
        else:
            return 0.0

    # Feature 084: _estimate_material_cost() removed - generic Material placeholder
    # support has been removed. All material compositions use material_unit_id.

    def _calculate_material_unit_cost(self) -> float:
        """
        Calculate cost for a MaterialUnit component from relationship data.

        Cost = weighted_avg_cost * quantity_per_unit, using inventory-weighted
        average from the parent MaterialProduct's inventory items.

        Note (Feature 084): MaterialUnit now points to MaterialProduct (not Material).
        Cost is calculated from the specific product's FIFO inventory, not across
        all products of a material.

        Returns:
            Cost per unit or 0.0 if no products/inventory
        """
        if not self.material_unit_component or not self.material_unit_component.material_product:
            return 0.0

        product = self.material_unit_component.material_product

        # Calculate inventory-weighted average cost per base unit (F058: FIFO inventory)
        total_value = 0.0
        total_inventory = 0.0
        for item in product.inventory_items:
            if item.quantity_remaining > 0.001:  # Avoid float dust
                total_value += item.quantity_remaining * float(item.cost_per_unit or 0)
                total_inventory += item.quantity_remaining

        if total_inventory == 0:
            return 0.0

        avg_cost_per_base_unit = total_value / total_inventory
        # Cost for this unit = avg cost per base unit × quantity per unit
        return avg_cost_per_base_unit * self.material_unit_component.quantity_per_unit

    def _calculate_material_unit_availability(self) -> int:
        """
        Calculate available inventory for a MaterialUnit from relationship data.

        Available = sum(product.inventory_items.quantity_remaining) / quantity_per_unit
        (how many times we can use this unit)

        Note (Feature 084): MaterialUnit now points to a specific MaterialProduct,
        so availability is calculated from that product's inventory only.

        Returns:
            Number of available units (integer, truncated down)
        """
        if not self.material_unit_component or not self.material_unit_component.material_product:
            return 0

        product = self.material_unit_component.material_product

        # Sum remaining inventory across all FIFO lots (F058)
        total_base_units = sum(item.quantity_remaining for item in product.inventory_items)
        quantity_per_unit = self.material_unit_component.quantity_per_unit

        if quantity_per_unit <= 0:
            return 0

        # Truncate to integer (can't have partial units available)
        return int(total_base_units / quantity_per_unit)

    def get_total_cost(self) -> float:
        """
        Calculate total cost for this composition entry.

        Returns:
            Component unit cost × component quantity
        """
        unit_cost = self.get_component_cost()
        return unit_cost * self.component_quantity

    def get_component_availability(self) -> int:
        """
        Get the available inventory for the referenced component.

        Note (Feature 084): Generic Material support removed.

        Returns:
            Available inventory count
        """
        if self.finished_unit_component:
            return self.finished_unit_component.inventory_count
        elif self.finished_good_component:
            return self.finished_good_component.inventory_count
        elif self.material_unit_component:
            # MaterialUnit - calculate availability from relationship data
            return self._calculate_material_unit_availability()
        # Feature 084: Removed material_component branch
        else:
            return 0

    def is_available(self, required_quantity: int = None) -> bool:
        """
        Check if sufficient component inventory is available.

        Args:
            required_quantity: Quantity needed (defaults to component_quantity)

        Returns:
            True if sufficient inventory available
        """
        if required_quantity is None:
            required_quantity = self.component_quantity

        available = self.get_component_availability()
        return available >= required_quantity

    def validate_polymorphic_constraint(self) -> bool:
        """
        Validate that exactly one component type is specified.

        Note (Feature 084): Reduced from 5-way to 4-way XOR (material_id removed).

        Returns:
            True if constraint is satisfied
        """
        unit_specified = self.finished_unit_id is not None
        good_specified = self.finished_good_id is not None
        packaging_specified = self.packaging_product_id is not None
        material_unit_specified = self.material_unit_id is not None
        # Feature 084: Removed material_specified

        # Exactly one should be true (4-way XOR)
        count = sum(
            [
                unit_specified,
                good_specified,
                packaging_specified,
                material_unit_specified,
            ]
        )
        return count == 1

    def validate_parent_constraint(self) -> bool:
        """
        Validate that exactly one parent type is specified.

        Returns:
            True if constraint is satisfied
        """
        assembly_specified = self.assembly_id is not None
        package_specified = self.package_id is not None

        # Exactly one should be true (XOR)
        return assembly_specified != package_specified

    def validate_no_circular_reference(self) -> bool:
        """
        Validate that this composition doesn't create a circular reference.

        This is a basic check - more comprehensive validation should be done
        at the service layer for deep hierarchy validation.

        Returns:
            True if no immediate circular reference
        """
        return self.assembly_id != self.finished_good_id

    def to_dict(self, include_relationships: bool = False) -> dict:
        """
        Convert composition to dictionary.

        Args:
            include_relationships: If True, include component details

        Returns:
            Dictionary representation with calculated fields
        """
        result = super().to_dict(include_relationships)

        # Add computed fields
        result["component_type"] = self.component_type
        result["component_id"] = self.component_id
        result["component_name"] = self.component_name
        result["unit_cost"] = self.get_component_cost()
        result["total_cost"] = self.get_total_cost()
        result["available_inventory"] = self.get_component_availability()
        result["is_available"] = self.is_available()

        if include_relationships:
            if self.finished_unit_component:
                result["finished_unit_component"] = self.finished_unit_component.to_dict()
            elif self.finished_good_component:
                result["finished_good_component"] = self.finished_good_component.to_dict()
            elif self.packaging_product:
                result["packaging_product"] = self.packaging_product.to_dict()

        return result

    @classmethod
    def create_unit_composition(
        cls,
        assembly_id: int,
        finished_unit_id: int,
        quantity: int = 1,
        notes: str = None,
        sort_order: int = 0,
    ) -> "Composition":
        """
        Factory method to create composition with FinishedUnit component.

        Args:
            assembly_id: Parent FinishedGood ID
            finished_unit_id: Component FinishedUnit ID
            quantity: Number of units in composition
            notes: Component-specific notes
            sort_order: Display order

        Returns:
            New Composition instance
        """
        return cls(
            assembly_id=assembly_id,
            finished_unit_id=finished_unit_id,
            finished_good_id=None,
            component_quantity=quantity,
            component_notes=notes,
            sort_order=sort_order,
        )

    @classmethod
    def create_assembly_composition(
        cls,
        assembly_id: int,
        finished_good_id: int,
        quantity: int = 1,
        notes: str = None,
        sort_order: int = 0,
    ) -> "Composition":
        """
        Factory method to create composition with FinishedGood sub-assembly.

        Args:
            assembly_id: Parent FinishedGood ID
            finished_good_id: Component FinishedGood ID
            quantity: Number of sub-assemblies in composition
            notes: Component-specific notes
            sort_order: Display order

        Returns:
            New Composition instance
        """
        return cls(
            assembly_id=assembly_id,
            finished_unit_id=None,
            finished_good_id=finished_good_id,
            component_quantity=quantity,
            component_notes=notes,
            sort_order=sort_order,
        )

    @classmethod
    def create_packaging_composition(
        cls,
        packaging_product_id: int,
        quantity: float = 1.0,
        notes: str = None,
        sort_order: int = 0,
        assembly_id: int = None,
        package_id: int = None,
    ) -> "Composition":
        """
        Factory method to create composition with packaging product component.

        Exactly one of assembly_id or package_id must be provided.

        Args:
            packaging_product_id: Component packaging Product ID
            quantity: Quantity of packaging (supports decimals)
            notes: Component-specific notes
            sort_order: Display order
            assembly_id: Parent FinishedGood ID (mutually exclusive with package_id)
            package_id: Parent Package ID (mutually exclusive with assembly_id)

        Returns:
            New Composition instance

        Raises:
            ValueError: If both or neither of assembly_id/package_id provided
        """
        if (assembly_id is None) == (package_id is None):
            raise ValueError("Exactly one of assembly_id or package_id must be provided")

        return cls(
            assembly_id=assembly_id,
            package_id=package_id,
            finished_unit_id=None,
            finished_good_id=None,
            packaging_product_id=packaging_product_id,
            component_quantity=quantity,
            component_notes=notes,
            sort_order=sort_order,
        )

    # Feature 047: Material composition factory methods

    @classmethod
    def create_material_unit_composition(
        cls,
        assembly_id: int,
        material_unit_id: int,
        quantity: int = 1,
        notes: str = None,
        sort_order: int = 0,
    ) -> "Composition":
        """
        Factory method to create composition with MaterialUnit component.

        Used when a specific material consumption unit is defined
        (e.g., "6-inch ribbon" where quantity_per_unit = 6 inches).

        Note (Feature 084): This is now the ONLY way to add material components
        to compositions. Generic Material placeholders are no longer supported.

        Args:
            assembly_id: Parent FinishedGood ID
            material_unit_id: Component MaterialUnit ID
            quantity: Number of units in composition
            notes: Component-specific notes
            sort_order: Display order

        Returns:
            New Composition instance
        """
        return cls(
            assembly_id=assembly_id,
            package_id=None,
            finished_unit_id=None,
            finished_good_id=None,
            packaging_product_id=None,
            material_unit_id=material_unit_id,
            # Feature 084: Removed material_id=None (column removed)
            component_quantity=quantity,
            component_notes=notes,
            sort_order=sort_order,
            is_generic=False,
        )

    # Feature 084: create_material_placeholder_composition() removed
    # Generic Material placeholders are no longer supported.
    # All material compositions must use material_unit_id via
    # create_material_unit_composition().
