"""
Assembly Type Enumeration and Metadata Support

This module defines the AssemblyType enum with comprehensive metadata support
and business rules for different package types used in the FinishedGood
assembly system.

Features:
- Extensible assembly type enumeration
- Display names and descriptions for UI presentation
- Assembly type-specific business rules and constraints
- Component limit guidelines and pricing rules
- Validation helpers and metadata access
"""

import enum
from typing import Dict, Any, Optional
from decimal import Decimal


class AssemblyType(enum.Enum):
    """
    Enumeration for finished good assembly types.

    Each assembly type defines specific packaging scenarios with their own
    business rules, component constraints, and presentation guidelines.
    """

    GIFT_BOX = "gift_box"          # Curated gift boxes with multiple items
    VARIETY_PACK = "variety_pack"  # Variety packs with different flavors
    HOLIDAY_SET = "holiday_set"    # Seasonal collections
    BULK_PACK = "bulk_pack"        # Large quantities of same/similar items
    CUSTOM_ORDER = "custom_order"  # Customer-specific combinations

    def __str__(self) -> str:
        """Return the display name for this assembly type."""
        return self.get_display_name()

    def get_display_name(self) -> str:
        """Get human-readable display name for this assembly type."""
        return ASSEMBLY_TYPE_METADATA[self]['display_name']

    def get_description(self) -> str:
        """Get detailed description for this assembly type."""
        return ASSEMBLY_TYPE_METADATA[self]['description']

    def get_component_limits(self) -> Dict[str, int]:
        """Get component limit constraints for this assembly type."""
        return ASSEMBLY_TYPE_METADATA[self]['component_limits']

    def get_business_rules(self) -> Dict[str, Any]:
        """Get business rules and constraints for this assembly type."""
        return ASSEMBLY_TYPE_METADATA[self]['business_rules']

    def is_seasonal(self) -> bool:
        """Check if this assembly type is seasonal."""
        return ASSEMBLY_TYPE_METADATA[self]['is_seasonal']

    def get_packaging_priority(self) -> int:
        """Get packaging priority level (lower number = higher priority)."""
        return ASSEMBLY_TYPE_METADATA[self]['packaging_priority']

    def requires_special_handling(self) -> bool:
        """Check if this assembly type requires special packaging handling."""
        return ASSEMBLY_TYPE_METADATA[self]['requires_special_handling']

    def get_pricing_markup(self) -> Decimal:
        """Get suggested pricing markup percentage for this assembly type."""
        return ASSEMBLY_TYPE_METADATA[self]['pricing_markup']

    @classmethod
    def get_all_metadata(cls) -> Dict[str, Dict[str, Any]]:
        """Get complete metadata for all assembly types."""
        return {assembly_type.value: ASSEMBLY_TYPE_METADATA[assembly_type]
                for assembly_type in cls}

    @classmethod
    def from_string(cls, value: str) -> Optional['AssemblyType']:
        """Create AssemblyType from string value."""
        try:
            return cls(value)
        except ValueError:
            return None

    @classmethod
    def get_seasonal_types(cls) -> list['AssemblyType']:
        """Get all seasonal assembly types."""
        return [assembly_type for assembly_type in cls if assembly_type.is_seasonal()]

    @classmethod
    def get_types_by_priority(cls) -> list['AssemblyType']:
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
        min_components = limits['min_components']
        max_components = limits['max_components']

        if component_count < min_components:
            return False, f"{self.get_display_name()} requires at least {min_components} components"

        if component_count > max_components:
            return False, f"{self.get_display_name()} cannot have more than {max_components} components"

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
        min_cost = rules.get('min_total_cost', Decimal('0.00'))
        max_cost = rules.get('max_total_cost')

        if total_cost < min_cost:
            return False, f"{self.get_display_name()} requires minimum total cost of ${min_cost}"

        if max_cost and total_cost > max_cost:
            return False, f"{self.get_display_name()} cannot exceed maximum total cost of ${max_cost}"

        return True, ""


# Assembly Type Metadata Configuration
ASSEMBLY_TYPE_METADATA = {
    AssemblyType.GIFT_BOX: {
        'display_name': 'Gift Box',
        'description': 'Curated gift boxes with multiple complementary items, typically 3-8 different products presented in an attractive package.',
        'component_limits': {
            'min_components': 3,
            'max_components': 8,
            'recommended_components': 5
        },
        'business_rules': {
            'min_total_cost': Decimal('15.00'),
            'max_total_cost': Decimal('150.00'),
            'requires_unique_items': True,
            'allows_duplicate_categories': False,
            'packaging_cost_multiplier': Decimal('1.15')  # 15% packaging overhead
        },
        'is_seasonal': False,
        'packaging_priority': 1,  # High priority - premium packaging
        'requires_special_handling': True,
        'pricing_markup': Decimal('0.25'),  # 25% markup
        'packaging_notes': 'Use premium gift box with tissue paper and ribbon'
    },

    AssemblyType.VARIETY_PACK: {
        'display_name': 'Variety Pack',
        'description': 'Multiple flavors or varieties of similar items, typically 4-12 different variations of the same product type.',
        'component_limits': {
            'min_components': 4,
            'max_components': 12,
            'recommended_components': 6
        },
        'business_rules': {
            'min_total_cost': Decimal('10.00'),
            'max_total_cost': Decimal('75.00'),
            'requires_unique_items': True,
            'allows_duplicate_categories': True,
            'packaging_cost_multiplier': Decimal('1.08')  # 8% packaging overhead
        },
        'is_seasonal': False,
        'packaging_priority': 3,  # Standard priority
        'requires_special_handling': False,
        'pricing_markup': Decimal('0.15'),  # 15% markup
        'packaging_notes': 'Use variety pack box with clear labeling for each variety'
    },

    AssemblyType.HOLIDAY_SET: {
        'display_name': 'Holiday Set',
        'description': 'Seasonal collections themed around holidays or special occasions, with festive packaging and presentation.',
        'component_limits': {
            'min_components': 3,
            'max_components': 10,
            'recommended_components': 6
        },
        'business_rules': {
            'min_total_cost': Decimal('20.00'),
            'max_total_cost': Decimal('200.00'),
            'requires_unique_items': False,
            'allows_duplicate_categories': True,
            'packaging_cost_multiplier': Decimal('1.20')  # 20% packaging overhead
        },
        'is_seasonal': True,
        'packaging_priority': 1,  # High priority - seasonal timing critical
        'requires_special_handling': True,
        'pricing_markup': Decimal('0.30'),  # 30% markup - seasonal premium
        'packaging_notes': 'Use holiday-themed packaging with seasonal colors and decorations'
    },

    AssemblyType.BULK_PACK: {
        'display_name': 'Bulk Pack',
        'description': 'Large quantities of the same or similar items for cost-conscious customers, focusing on value over presentation.',
        'component_limits': {
            'min_components': 1,
            'max_components': 20,
            'recommended_components': 8
        },
        'business_rules': {
            'min_total_cost': Decimal('20.00'),
            'max_total_cost': None,  # No upper limit
            'requires_unique_items': False,
            'allows_duplicate_categories': True,
            'packaging_cost_multiplier': Decimal('1.03')  # 3% packaging overhead
        },
        'is_seasonal': False,
        'packaging_priority': 4,  # Low priority - efficiency focused
        'requires_special_handling': False,
        'pricing_markup': Decimal('0.05'),  # 5% markup - volume pricing
        'packaging_notes': 'Use efficient bulk packaging, minimal decoration'
    },

    AssemblyType.CUSTOM_ORDER: {
        'display_name': 'Custom Order',
        'description': 'Customer-specific combinations with flexible rules and personalized packaging options.',
        'component_limits': {
            'min_components': 1,
            'max_components': 15,
            'recommended_components': 5
        },
        'business_rules': {
            'min_total_cost': Decimal('5.00'),
            'max_total_cost': None,  # No upper limit
            'requires_unique_items': False,
            'allows_duplicate_categories': True,
            'packaging_cost_multiplier': Decimal('1.10')  # 10% packaging overhead
        },
        'is_seasonal': False,
        'packaging_priority': 2,  # Medium-high priority - customer satisfaction
        'requires_special_handling': True,
        'pricing_markup': Decimal('0.20'),  # 20% markup - customization premium
        'packaging_notes': 'Follow customer-specified packaging preferences and instructions'
    }
}


def get_assembly_type_choices() -> list[tuple[str, str]]:
    """Get assembly type choices for forms and UIs."""
    return [(at.value, at.get_display_name()) for at in AssemblyType]


def validate_assembly_type_business_rules(
    assembly_type: AssemblyType,
    component_count: int,
    total_cost: Decimal
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
    multiplier = assembly_type.get_business_rules()['packaging_cost_multiplier']
    return component_cost * (multiplier - Decimal('1.0'))


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
    return total_cost * (Decimal('1.0') + markup)