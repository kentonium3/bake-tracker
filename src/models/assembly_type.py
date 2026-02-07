"""
Assembly Type Enumeration and Metadata Support

This module defines the AssemblyType enum with metadata support
and business rules for package types used in the FinishedGood
assembly system.

Two assembly types:
- BARE: Single FinishedUnit with no additional packaging
- BUNDLE: Any multi-component assembly (gift boxes, variety packs, etc.)
"""

import enum
from typing import Dict, Any, Optional
from decimal import Decimal


class AssemblyType(enum.Enum):
    """
    Enumeration for finished good assembly types.

    BARE: Single FinishedUnit served as-is with no additional packaging.
    BUNDLE: Multi-component assembly with flexible composition rules.
    """

    BARE = "bare"  # Single FinishedUnit with no additional packaging
    BUNDLE = "bundle"  # Any multi-component assembly

    def __str__(self) -> str:
        """Return the display name for this assembly type."""
        return self.get_display_name()

    def get_display_name(self) -> str:
        """Get human-readable display name for this assembly type."""
        return ASSEMBLY_TYPE_METADATA[self]["display_name"]

    def get_description(self) -> str:
        """Get detailed description for this assembly type."""
        return ASSEMBLY_TYPE_METADATA[self]["description"]

    def get_component_limits(self) -> Dict[str, int]:
        """Get component limit constraints for this assembly type."""
        return ASSEMBLY_TYPE_METADATA[self]["component_limits"]

    def get_business_rules(self) -> Dict[str, Any]:
        """Get business rules and constraints for this assembly type."""
        return ASSEMBLY_TYPE_METADATA[self]["business_rules"]

    def is_seasonal(self) -> bool:
        """Check if this assembly type is seasonal."""
        return ASSEMBLY_TYPE_METADATA[self]["is_seasonal"]

    def get_packaging_priority(self) -> int:
        """Get packaging priority level (lower number = higher priority)."""
        return ASSEMBLY_TYPE_METADATA[self]["packaging_priority"]

    def requires_special_handling(self) -> bool:
        """Check if this assembly type requires special packaging handling."""
        return ASSEMBLY_TYPE_METADATA[self]["requires_special_handling"]

    def get_pricing_markup(self) -> Decimal:
        """Get suggested pricing markup percentage for this assembly type."""
        return ASSEMBLY_TYPE_METADATA[self]["pricing_markup"]

    @classmethod
    def get_all_metadata(cls) -> Dict[str, Dict[str, Any]]:
        """Get complete metadata for all assembly types."""
        return {assembly_type.value: ASSEMBLY_TYPE_METADATA[assembly_type] for assembly_type in cls}

    @classmethod
    def from_string(cls, value: str) -> Optional["AssemblyType"]:
        """Create AssemblyType from string value."""
        try:
            return cls(value)
        except ValueError:
            return None

    @classmethod
    def from_display_name(cls, display_name: str) -> Optional["AssemblyType"]:
        """
        Get AssemblyType from its display name.

        Args:
            display_name: Human-readable display name (e.g., "Bundle")

        Returns:
            Matching AssemblyType or None if not found
        """
        for assembly_type in cls:
            if assembly_type.get_display_name() == display_name:
                return assembly_type
        return None

    @classmethod
    def get_seasonal_types(cls) -> list["AssemblyType"]:
        """Get all seasonal assembly types."""
        return [assembly_type for assembly_type in cls if assembly_type.is_seasonal()]

    @classmethod
    def get_types_by_priority(cls) -> list["AssemblyType"]:
        """Get assembly types ordered by packaging priority."""
        return sorted(cls, key=lambda t: t.get_packaging_priority())

    def validate_component_count(self, component_count: int) -> tuple[bool, str]:
        """
        Validate component count against business rules for this assembly type.

        Args:
            component_count: Number of components in the assembly

        Returns:
            Tuple of (is_valid, error_message)
        """
        limits = self.get_component_limits()
        min_components = limits["min_components"]
        max_components = limits["max_components"]

        if component_count < min_components:
            return False, f"{self.get_display_name()} requires at least {min_components} components"

        if component_count > max_components:
            return (
                False,
                f"{self.get_display_name()} cannot have more than {max_components} components",
            )

        return True, ""

    def validate_cost_constraints(self, total_cost: Decimal) -> tuple[bool, str]:
        """
        Validate total cost against business rules for this assembly type.

        Args:
            total_cost: Total cost of the assembly

        Returns:
            Tuple of (is_valid, error_message)
        """
        rules = self.get_business_rules()
        min_cost = rules.get("min_total_cost", Decimal("0.00"))
        max_cost = rules.get("max_total_cost")

        if total_cost < min_cost:
            return False, f"{self.get_display_name()} requires minimum total cost of ${min_cost}"

        if max_cost and total_cost > max_cost:
            return (
                False,
                f"{self.get_display_name()} cannot exceed maximum total cost of ${max_cost}",
            )

        return True, ""


# Assembly Type Metadata Configuration
ASSEMBLY_TYPE_METADATA = {
    AssemblyType.BARE: {
        "display_name": "Bare",
        "description": "Single FinishedUnit served as-is with no additional packaging or bundling. Used for items like whole cakes that are deliverable without modification.",
        "component_limits": {
            "min_components": 1,
            "max_components": 1,
            "recommended_components": 1,
        },
        "business_rules": {
            "min_total_cost": Decimal("0.00"),
            "max_total_cost": None,
            "requires_unique_items": False,
            "allows_duplicate_categories": True,
            "packaging_cost_multiplier": Decimal("1.00"),
        },
        "is_seasonal": False,
        "packaging_priority": 5,
        "requires_special_handling": False,
        "pricing_markup": Decimal("0.00"),
        "packaging_notes": "No additional packaging required",
    },
    AssemblyType.BUNDLE: {
        "display_name": "Bundle",
        "description": "Multi-component assembly combining multiple FinishedUnits and/or materials into a single package.",
        "component_limits": {
            "min_components": 1,
            "max_components": 50,
            "recommended_components": 5,
        },
        "business_rules": {
            "min_total_cost": Decimal("0.00"),
            "max_total_cost": None,
            "requires_unique_items": False,
            "allows_duplicate_categories": True,
            "packaging_cost_multiplier": Decimal("1.10"),
        },
        "is_seasonal": False,
        "packaging_priority": 2,
        "requires_special_handling": False,
        "pricing_markup": Decimal("0.10"),
        "packaging_notes": "Package per assembly instructions",
    },
}


def get_assembly_type_choices() -> list[tuple[str, str]]:
    """Get assembly type choices for forms and UIs."""
    return [(at.value, at.get_display_name()) for at in AssemblyType]


def validate_assembly_type_business_rules(
    assembly_type: AssemblyType, component_count: int, total_cost: Decimal
) -> tuple[bool, list[str]]:
    """
    Validate complete business rules for an assembly type.

    Args:
        assembly_type: The assembly type to validate
        component_count: Number of components in the assembly
        total_cost: Total cost of the assembly

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors = []

    # Validate component count
    is_valid_count, count_error = assembly_type.validate_component_count(component_count)
    if not is_valid_count:
        errors.append(count_error)

    # Validate cost constraints
    is_valid_cost, cost_error = assembly_type.validate_cost_constraints(total_cost)
    if not is_valid_cost:
        errors.append(cost_error)

    return len(errors) == 0, errors


def calculate_packaging_cost(assembly_type: AssemblyType, component_cost: Decimal) -> Decimal:
    """
    Calculate packaging cost for an assembly type.

    Args:
        assembly_type: The assembly type
        component_cost: Total cost of components

    Returns:
        Calculated packaging cost
    """
    multiplier = assembly_type.get_business_rules()["packaging_cost_multiplier"]
    return component_cost * (multiplier - Decimal("1.0"))


def get_suggested_retail_price(assembly_type: AssemblyType, total_cost: Decimal) -> Decimal:
    """
    Calculate suggested retail price based on assembly type markup.

    Args:
        assembly_type: The assembly type
        total_cost: Total cost including components and packaging

    Returns:
        Suggested retail price
    """
    markup = assembly_type.get_pricing_markup()
    return total_cost * (Decimal("1.0") + markup)
