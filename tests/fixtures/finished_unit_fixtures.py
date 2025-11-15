"""
Test fixtures for FinishedUnit testing.

Provides comprehensive test data including mock objects, sample data,
and fixture functions for unit and integration testing.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock

import pytest


class MockRecipe:
    """Mock Recipe for testing FinishedUnit without database dependencies."""

    def __init__(self, recipe_id: int = 1, name: str = "Test Recipe", cost: float = 10.0):
        self.id = recipe_id
        self.name = name
        self._cost = cost

    def calculate_cost(self) -> float:
        """Mock cost calculation."""
        return self._cost


@pytest.fixture
def mock_recipe():
    """Create a mock Recipe for testing."""
    return MockRecipe()


@pytest.fixture
def mock_expensive_recipe():
    """Create a mock expensive Recipe for testing."""
    return MockRecipe(recipe_id=2, name="Expensive Recipe", cost=25.0)


@pytest.fixture
def sample_finished_unit_data():
    """Sample data for creating FinishedUnit instances."""
    return {
        "display_name": "Chocolate Chip Cookie",
        "description": "Classic chocolate chip cookies",
        "recipe_id": 1,
        "yield_mode": "discrete_count",
        "items_per_batch": 24,
        "item_unit": "cookie",
        "category": "cookies",
        "unit_cost": Decimal('0.5000'),
        "inventory_count": 48,
        "production_notes": "Bake at 350°F for 12 minutes",
        "notes": "Popular item"
    }


@pytest.fixture
def batch_portion_unit_data():
    """Sample data for batch portion FinishedUnit."""
    return {
        "display_name": "9-inch Chocolate Cake",
        "description": "Rich chocolate cake",
        "recipe_id": 2,
        "yield_mode": "batch_portion",
        "batch_percentage": Decimal('100.00'),
        "portion_description": "9-inch round cake pan",
        "category": "cakes",
        "unit_cost": Decimal('12.5000'),
        "inventory_count": 3
    }


@pytest.fixture
def invalid_finished_unit_data():
    """Invalid data for testing validation."""
    return [
        # Missing display name
        {"recipe_id": 1},
        # Empty display name
        {"display_name": "", "recipe_id": 1},
        # Negative unit cost
        {"display_name": "Test Item", "unit_cost": Decimal('-1.0000')},
        # Negative inventory
        {"display_name": "Test Item", "inventory_count": -5},
        # Invalid recipe reference
        {"display_name": "Test Item", "recipe_id": 99999}
    ]


@pytest.fixture
def search_test_data():
    """Test data for search functionality."""
    return [
        {
            "display_name": "Chocolate Chip Cookie",
            "description": "Classic cookie with chocolate chips",
            "category": "cookies",
            "notes": "Very popular"
        },
        {
            "display_name": "Oatmeal Raisin Cookie",
            "description": "Hearty oatmeal cookie",
            "category": "cookies",
            "notes": "Healthy option"
        },
        {
            "display_name": "Chocolate Brownie",
            "description": "Fudgy chocolate brownie",
            "category": "brownies",
            "notes": "Rich and decadent"
        },
        {
            "display_name": "Vanilla Cupcake",
            "description": "Light vanilla cupcake with frosting",
            "category": "cupcakes",
            "notes": "Birthday favorite"
        }
    ]


@pytest.fixture
def inventory_test_scenarios():
    """Test scenarios for inventory management."""
    return [
        # Normal addition
        {"initial": 10, "change": 5, "expected": 15, "should_succeed": True},
        # Normal subtraction
        {"initial": 10, "change": -3, "expected": 7, "should_succeed": True},
        # Zero out inventory
        {"initial": 10, "change": -10, "expected": 0, "should_succeed": True},
        # Attempt negative inventory
        {"initial": 5, "change": -10, "expected": 5, "should_succeed": False},
        # Large addition
        {"initial": 100, "change": 1000, "expected": 1100, "should_succeed": True}
    ]


@pytest.fixture
def cost_calculation_scenarios():
    """Test scenarios for cost calculations."""
    return [
        # Discrete count scenario
        {
            "yield_mode": "discrete_count",
            "items_per_batch": 24,
            "recipe_cost": 12.0,
            "expected_unit_cost": Decimal('0.5000')
        },
        # Batch portion scenario
        {
            "yield_mode": "batch_portion",
            "batch_percentage": Decimal('100.0'),
            "recipe_cost": 25.0,
            "expected_unit_cost": Decimal('25.0000')
        },
        # Partial batch scenario
        {
            "yield_mode": "batch_portion",
            "batch_percentage": Decimal('50.0'),
            "recipe_cost": 20.0,
            "expected_unit_cost": Decimal('10.0000')
        },
        # No recipe scenario
        {
            "yield_mode": "discrete_count",
            "items_per_batch": 12,
            "recipe_cost": None,
            "expected_unit_cost": Decimal('0.0000')
        }
    ]


@pytest.fixture
def performance_test_data():
    """Data for performance testing."""
    return {
        "bulk_create_count": 100,
        "search_dataset_size": 1000,
        "max_acceptable_time_ms": {
            "single_crud": 500,
            "bulk_operations": 2000,
            "search_operations": 300,
            "inventory_operations": 200
        }
    }


@pytest.fixture
def edge_case_data():
    """Edge cases for comprehensive testing."""
    return {
        "long_display_name": "A" * 200,  # Test length limits
        "unicode_display_name": "Café Crème Brûlée 🍰",  # Unicode characters
        "special_chars_name": "Cookie's & Cream (Premium)",  # Special characters
        "numeric_name": "123 Number Cookie",  # Starting with numbers
        "empty_optional_fields": {
            "description": None,
            "category": None,
            "notes": None,
            "production_notes": None
        },
        "boundary_values": {
            "zero_cost": Decimal('0.0000'),
            "max_precision_cost": Decimal('9999.9999'),
            "zero_inventory": 0,
            "large_inventory": 1000000,
            "min_batch_items": 1,
            "max_batch_items": 10000,
            "min_batch_percentage": Decimal('0.01'),
            "max_batch_percentage": Decimal('100.00')
        }
    }


@pytest.fixture
def mock_database_session():
    """Mock database session for unit testing without database."""
    session = MagicMock()

    # Configure common query patterns
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    session.query.return_value.count.return_value = 0
    session.query.return_value.options.return_value = session.query.return_value

    return session


@pytest.fixture
def mock_finished_unit():
    """Mock FinishedUnit instance for testing."""
    from src.models.finished_unit import YieldMode

    unit = Mock()
    unit.id = 1
    unit.slug = "chocolate-chip-cookie"
    unit.display_name = "Chocolate Chip Cookie"
    unit.description = "Classic cookie"
    unit.recipe_id = 1
    unit.yield_mode = YieldMode.DISCRETE_COUNT
    unit.items_per_batch = 24
    unit.item_unit = "cookie"
    unit.batch_percentage = None
    unit.portion_description = None
    unit.category = "cookies"
    unit.unit_cost = Decimal('0.5000')
    unit.inventory_count = 48
    unit.production_notes = "Bake at 350°F"
    unit.notes = "Popular item"
    unit.created_at = datetime.now() - timedelta(days=1)
    unit.updated_at = datetime.now()

    # Mock methods
    unit.calculate_recipe_cost_per_item.return_value = Decimal('0.5000')
    unit.update_unit_cost_from_recipe.return_value = None
    unit.is_available.return_value = True
    unit.update_inventory.return_value = True
    unit.to_dict.return_value = {
        "id": unit.id,
        "slug": unit.slug,
        "display_name": unit.display_name,
        "unit_cost": float(unit.unit_cost),
        "inventory_count": unit.inventory_count
    }

    return unit


def create_test_finished_unit_data(count: int = 10) -> List[Dict[str, Any]]:
    """
    Create multiple test FinishedUnit data entries for bulk testing.

    Args:
        count: Number of test entries to create

    Returns:
        List of FinishedUnit data dictionaries
    """
    test_data = []
    categories = ["cookies", "cakes", "brownies", "cupcakes", "bars"]

    for i in range(count):
        data = {
            "display_name": f"Test Item {i+1}",
            "description": f"Test description for item {i+1}",
            "recipe_id": (i % 3) + 1,  # Cycle through recipe IDs 1-3
            "yield_mode": "discrete_count" if i % 2 == 0 else "batch_portion",
            "category": categories[i % len(categories)],
            "unit_cost": Decimal(f"{(i + 1) * 0.5:.4f}"),
            "inventory_count": (i + 1) * 10,
            "notes": f"Test notes for item {i+1}"
        }

        # Add yield-specific fields
        if data["yield_mode"] == "discrete_count":
            data["items_per_batch"] = (i + 1) * 12
            data["item_unit"] = "piece"
        else:
            data["batch_percentage"] = Decimal(f"{min(100, (i + 1) * 10)}.00")
            data["portion_description"] = f"Test portion {i+1}"

        test_data.append(data)

    return test_data


# Utility functions for test assertions

def assert_finished_unit_fields(unit, expected_data):
    """Assert that a FinishedUnit matches expected field values."""
    for field, expected_value in expected_data.items():
        actual_value = getattr(unit, field, None)
        assert actual_value == expected_value, f"Field {field}: expected {expected_value}, got {actual_value}"


def assert_slug_format(slug: str):
    """Assert that a slug follows the expected format."""
    assert slug is not None, "Slug should not be None"
    assert isinstance(slug, str), "Slug should be a string"
    assert len(slug) > 0, "Slug should not be empty"
    assert slug.islower(), "Slug should be lowercase"
    assert " " not in slug, "Slug should not contain spaces"
    assert slug.replace("-", "").replace("_", "").isalnum(), "Slug should only contain alphanumeric characters and hyphens"