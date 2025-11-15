"""
Test fixtures for Assembly and Composition testing.

Provides comprehensive test data including mock objects, sample data,
and fixture functions for unit and integration testing of assembly
management functionality.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock

import pytest

from src.models.assembly_type import AssemblyType
from src.models import FinishedGood, Composition, FinishedUnit


class MockAssembly:
    """Mock FinishedGood assembly for testing without database dependencies."""

    def __init__(
        self,
        assembly_id: int = 1,
        display_name: str = "Test Assembly",
        assembly_type: AssemblyType = AssemblyType.GIFT_BOX,
        total_cost: float = 25.0
    ):
        self.id = assembly_id
        self.slug = f"test-assembly-{assembly_id}"
        self.display_name = display_name
        self.assembly_type = assembly_type
        self.total_cost = Decimal(str(total_cost))
        self.inventory_count = 5
        self.description = f"Test description for {display_name}"
        self.packaging_instructions = "Standard test packaging"
        self.notes = "Test assembly notes"
        self.created_at = datetime.now() - timedelta(days=1)
        self.updated_at = datetime.now()

        # Mock relationships
        self.components = []

    def calculate_component_cost(self) -> Decimal:
        """Mock cost calculation."""
        return self.total_cost

    def can_assemble(self, quantity: int) -> dict:
        """Mock availability check."""
        return {
            'can_assemble': self.inventory_count >= quantity,
            'missing_components': [] if self.inventory_count >= quantity else ['insufficient inventory']
        }

    def update_inventory(self, quantity_change: int) -> None:
        """Mock inventory update."""
        self.inventory_count += quantity_change

    def update_total_cost_from_components(self) -> None:
        """Mock cost update."""
        pass


class MockComposition:
    """Mock Composition for testing without database dependencies."""

    def __init__(
        self,
        composition_id: int = 1,
        assembly_id: int = 1,
        component_type: str = "finished_unit",
        component_id: int = 1,
        quantity: int = 2
    ):
        self.id = composition_id
        self.assembly_id = assembly_id
        self.component_quantity = quantity
        self.component_notes = "Test component notes"
        self.sort_order = 0

        # Set polymorphic relationships
        if component_type == "finished_unit":
            self.finished_unit_id = component_id
            self.finished_good_id = None
            self.finished_unit_component = MockFinishedUnit(component_id)
            self.finished_good_component = None
        else:
            self.finished_unit_id = None
            self.finished_good_id = component_id
            self.finished_unit_component = None
            self.finished_good_component = MockAssembly(component_id)

        self.assembly = MockAssembly(assembly_id)


class MockFinishedUnit:
    """Mock FinishedUnit for assembly testing."""

    def __init__(self, unit_id: int = 1, unit_cost: float = 2.5, inventory: int = 10):
        self.id = unit_id
        self.slug = f"test-unit-{unit_id}"
        self.display_name = f"Test Unit {unit_id}"
        self.unit_cost = Decimal(str(unit_cost))
        self.inventory_count = inventory
        self.description = f"Test unit {unit_id} description"


# Pytest Fixtures

@pytest.fixture
def mock_assembly():
    """Create a mock FinishedGood assembly for testing."""
    return MockAssembly()


@pytest.fixture
def mock_gift_box():
    """Create a mock Gift Box assembly."""
    return MockAssembly(
        assembly_id=2,
        display_name="Holiday Gift Box",
        assembly_type=AssemblyType.GIFT_BOX,
        total_cost=45.0
    )


@pytest.fixture
def mock_variety_pack():
    """Create a mock Variety Pack assembly."""
    return MockAssembly(
        assembly_id=3,
        display_name="Cookie Variety Pack",
        assembly_type=AssemblyType.VARIETY_PACK,
        total_cost=28.0
    )


@pytest.fixture
def mock_composition():
    """Create a mock Composition for testing."""
    return MockComposition()


@pytest.fixture
def sample_assembly_data():
    """Sample data for creating FinishedGood assemblies."""
    return {
        "display_name": "Premium Gift Box",
        "description": "Assorted premium cookies and treats",
        "assembly_type": AssemblyType.GIFT_BOX,
        "packaging_instructions": "Use premium gift box with ribbon",
        "inventory_count": 0,
        "notes": "Popular holiday item"
    }


@pytest.fixture
def sample_component_specifications():
    """Sample component specifications for assembly creation."""
    return [
        {
            "component_type": "finished_unit",
            "component_id": 1,
            "quantity": 3,
            "notes": "Chocolate chip cookies"
        },
        {
            "component_type": "finished_unit",
            "component_id": 2,
            "quantity": 2,
            "notes": "Oatmeal raisin cookies"
        },
        {
            "component_type": "finished_unit",
            "component_id": 3,
            "quantity": 4,
            "notes": "Sugar cookies"
        }
    ]


@pytest.fixture
def invalid_assembly_data():
    """Invalid data for testing validation."""
    return [
        # Missing display name
        {"assembly_type": AssemblyType.GIFT_BOX},
        # Empty display name
        {"display_name": "", "assembly_type": AssemblyType.GIFT_BOX},
        # Invalid assembly type
        {"display_name": "Test Assembly", "assembly_type": "invalid_type"},
        # Negative total cost
        {"display_name": "Test Assembly", "assembly_type": AssemblyType.GIFT_BOX, "total_cost": Decimal('-1.0')},
        # Negative inventory
        {"display_name": "Test Assembly", "assembly_type": AssemblyType.GIFT_BOX, "inventory_count": -5}
    ]


@pytest.fixture
def component_validation_scenarios():
    """Test scenarios for component validation."""
    return [
        # Valid scenarios
        {"component_type": "finished_unit", "component_id": 1, "quantity": 2, "should_succeed": True},
        {"component_type": "finished_good", "component_id": 2, "quantity": 1, "should_succeed": True},
        # Invalid scenarios
        {"component_type": "invalid_type", "component_id": 1, "quantity": 2, "should_succeed": False},
        {"component_type": "finished_unit", "component_id": 999, "quantity": 2, "should_succeed": False},
        {"component_type": "finished_unit", "component_id": 1, "quantity": 0, "should_succeed": False},
        {"component_type": "finished_unit", "component_id": 1, "quantity": -1, "should_succeed": False}
    ]


@pytest.fixture
def assembly_hierarchy_test_data():
    """Test data for assembly hierarchy operations."""
    return {
        "root_assembly": {
            "id": 1,
            "display_name": "Ultimate Gift Collection",
            "assembly_type": AssemblyType.GIFT_BOX
        },
        "sub_assemblies": [
            {
                "id": 2,
                "display_name": "Cookie Assortment",
                "assembly_type": AssemblyType.VARIETY_PACK,
                "parent_id": 1
            },
            {
                "id": 3,
                "display_name": "Holiday Treats",
                "assembly_type": AssemblyType.HOLIDAY_SET,
                "parent_id": 1
            }
        ],
        "finished_units": [
            {"id": 1, "display_name": "Chocolate Chip Cookie", "unit_cost": 2.0},
            {"id": 2, "display_name": "Sugar Cookie", "unit_cost": 1.5},
            {"id": 3, "display_name": "Gingerbread Cookie", "unit_cost": 2.5},
            {"id": 4, "display_name": "Hot Cocoa Mix", "unit_cost": 3.0}
        ]
    }


@pytest.fixture
def cost_calculation_scenarios():
    """Test scenarios for cost calculations."""
    return [
        # Simple assembly with FinishedUnits only
        {
            "assembly_type": AssemblyType.GIFT_BOX,
            "components": [
                {"type": "finished_unit", "id": 1, "cost": 2.0, "quantity": 3},
                {"type": "finished_unit", "id": 2, "cost": 1.5, "quantity": 2}
            ],
            "expected_component_cost": 9.0,  # (2.0 * 3) + (1.5 * 2)
            "expected_packaging_cost": 1.35,  # 9.0 * 0.15 (gift box markup)
            "expected_total_cost": 10.35
        },
        # Complex assembly with sub-assemblies
        {
            "assembly_type": AssemblyType.CUSTOM_ORDER,
            "components": [
                {"type": "finished_unit", "id": 1, "cost": 2.0, "quantity": 2},
                {"type": "finished_good", "id": 2, "cost": 8.0, "quantity": 1}
            ],
            "expected_component_cost": 12.0,  # (2.0 * 2) + (8.0 * 1)
            "expected_packaging_cost": 1.2,   # 12.0 * 0.10 (custom order markup)
            "expected_total_cost": 13.2
        }
    ]


@pytest.fixture
def business_rule_test_cases():
    """Test cases for assembly type business rule validation."""
    return {
        AssemblyType.GIFT_BOX: {
            "valid_cases": [
                {"component_count": 5, "total_cost": 30.0},
                {"component_count": 3, "total_cost": 15.0},
                {"component_count": 8, "total_cost": 100.0}
            ],
            "invalid_cases": [
                {"component_count": 2, "total_cost": 20.0, "error": "requires at least 3 components"},
                {"component_count": 10, "total_cost": 50.0, "error": "cannot have more than 8 components"},
                {"component_count": 5, "total_cost": 10.0, "error": "requires minimum total cost"},
                {"component_count": 5, "total_cost": 200.0, "error": "cannot exceed maximum total cost"}
            ]
        },
        AssemblyType.BULK_PACK: {
            "valid_cases": [
                {"component_count": 10, "total_cost": 50.0},
                {"component_count": 1, "total_cost": 20.0},
                {"component_count": 20, "total_cost": 100.0}
            ],
            "invalid_cases": [
                {"component_count": 0, "total_cost": 30.0, "error": "requires at least 1 components"},
                {"component_count": 25, "total_cost": 50.0, "error": "cannot have more than 20 components"},
                {"component_count": 5, "total_cost": 15.0, "error": "requires minimum total cost"}
            ]
        }
    }


@pytest.fixture
def inventory_management_scenarios():
    """Test scenarios for inventory management during assembly production."""
    return [
        # Sufficient inventory scenario
        {
            "assembly_quantity": 2,
            "components": [
                {"type": "finished_unit", "id": 1, "required_per_assembly": 3, "available": 10},
                {"type": "finished_unit", "id": 2, "required_per_assembly": 2, "available": 8}
            ],
            "should_succeed": True,
            "expected_consumption": [
                {"id": 1, "consumed": 6},  # 3 * 2
                {"id": 2, "consumed": 4}   # 2 * 2
            ]
        },
        # Insufficient inventory scenario
        {
            "assembly_quantity": 5,
            "components": [
                {"type": "finished_unit", "id": 1, "required_per_assembly": 3, "available": 10},
                {"type": "finished_unit", "id": 2, "required_per_assembly": 2, "available": 5}
            ],
            "should_succeed": False,
            "shortage": [
                {"id": 2, "required": 10, "available": 5, "shortage": 5}
            ]
        }
    ]


@pytest.fixture
def circular_reference_test_data():
    """Test data for circular reference detection."""
    return {
        "assemblies": [
            {"id": 1, "name": "Assembly A"},
            {"id": 2, "name": "Assembly B"},
            {"id": 3, "name": "Assembly C"}
        ],
        "valid_compositions": [
            {"assembly_id": 1, "component_type": "finished_good", "component_id": 2},
            {"assembly_id": 2, "component_type": "finished_good", "component_id": 3}
        ],
        "circular_compositions": [
            {"assembly_id": 3, "component_type": "finished_good", "component_id": 1},  # Creates cycle: 1->2->3->1
            {"assembly_id": 2, "component_type": "finished_good", "component_id": 1}   # Creates cycle: 1->2->1
        ]
    }


@pytest.fixture
def search_and_query_test_data():
    """Test data for search and query operations."""
    return {
        "assemblies": [
            {"display_name": "Chocolate Gift Box", "description": "Premium chocolate collection", "assembly_type": AssemblyType.GIFT_BOX},
            {"display_name": "Cookie Variety Pack", "description": "Assorted cookie flavors", "assembly_type": AssemblyType.VARIETY_PACK},
            {"display_name": "Holiday Cookie Set", "description": "Seasonal cookie collection", "assembly_type": AssemblyType.HOLIDAY_SET},
            {"display_name": "Bulk Cookie Pack", "description": "Large quantity cookies", "assembly_type": AssemblyType.BULK_PACK}
        ],
        "search_tests": [
            {"query": "chocolate", "expected_matches": ["Chocolate Gift Box"]},
            {"query": "cookie", "expected_matches": ["Cookie Variety Pack", "Holiday Cookie Set", "Bulk Cookie Pack"]},
            {"query": "premium", "expected_matches": ["Chocolate Gift Box"]},
            {"query": "nonexistent", "expected_matches": []}
        ]
    }


@pytest.fixture
def performance_test_configuration():
    """Configuration for performance testing."""
    return {
        "bulk_assembly_count": 50,
        "components_per_assembly": 8,
        "hierarchy_depth": 4,
        "max_acceptable_times": {
            "assembly_creation": 2000,  # ms
            "component_addition": 500,  # ms
            "hierarchy_traversal": 500,  # ms
            "cost_calculation": 400,    # ms
            "availability_check": 500,  # ms
            "business_rule_validation": 300  # ms
        }
    }


# Utility functions for test assertions

def assert_assembly_fields(assembly, expected_data):
    """Assert that a FinishedGood assembly matches expected field values."""
    for field, expected_value in expected_data.items():
        actual_value = getattr(assembly, field, None)
        assert actual_value == expected_value, f"Field {field}: expected {expected_value}, got {actual_value}"


def assert_composition_integrity(composition):
    """Assert that a composition has proper polymorphic integrity."""
    # Exactly one component type should be set
    unit_set = composition.finished_unit_id is not None
    good_set = composition.finished_good_id is not None

    assert unit_set != good_set, "Composition must have exactly one component type set"
    assert composition.component_quantity > 0, "Composition quantity must be positive"


def assert_cost_calculation(calculated_cost, expected_cost, tolerance=0.01):
    """Assert that calculated cost matches expected within tolerance."""
    difference = abs(float(calculated_cost) - expected_cost)
    assert difference <= tolerance, f"Cost calculation off by {difference}: expected {expected_cost}, got {calculated_cost}"


def create_test_assembly_data(count: int = 10) -> List[Dict[str, Any]]:
    """
    Create multiple test FinishedGood assembly data entries for bulk testing.

    Args:
        count: Number of test entries to create

    Returns:
        List of FinishedGood assembly data dictionaries
    """
    assembly_types = list(AssemblyType)
    test_data = []

    for i in range(count):
        assembly_type = assembly_types[i % len(assembly_types)]

        data = {
            "display_name": f"Test Assembly {i+1}",
            "description": f"Test description for assembly {i+1}",
            "assembly_type": assembly_type,
            "packaging_instructions": f"Test packaging instructions {i+1}",
            "inventory_count": (i + 1) * 2,
            "notes": f"Test notes for assembly {i+1}"
        }

        test_data.append(data)

    return test_data


def create_test_component_specifications(assembly_id: int, component_count: int = 5) -> List[Dict[str, Any]]:
    """
    Create component specifications for testing assembly creation.

    Args:
        assembly_id: ID of the assembly
        component_count: Number of components to create

    Returns:
        List of component specification dictionaries
    """
    components = []

    for i in range(component_count):
        # Alternate between finished_unit and finished_good components
        component_type = "finished_unit" if i % 2 == 0 else "finished_good"

        component_spec = {
            "component_type": component_type,
            "component_id": (i % 3) + 1,  # Cycle through IDs 1-3
            "quantity": (i + 1) * 2,      # Vary quantities
            "notes": f"Test component {i+1} for assembly {assembly_id}"
        }

        components.append(component_spec)

    return components