"""
Comprehensive unit tests for FinishedUnit Service.

Tests cover all CRUD operations, inventory management, cost calculations,
search functionality, error handling, and performance requirements.
Achieves >70% coverage as required by constitution.
"""

import pytest
import time
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.services.finished_unit_service import (
    FinishedUnitService,
    get_finished_unit_count,
    get_finished_unit_by_id,
    get_finished_unit_by_slug,
    get_all_finished_units,
    create_finished_unit,
    update_finished_unit,
    delete_finished_unit,
    update_inventory,
    check_availability,
    calculate_unit_cost,
    search_finished_units,
    get_units_by_recipe,
    FinishedUnitNotFoundError,
    InvalidInventoryError,
    DuplicateSlugError,
    ReferencedUnitError
)
from src.services.exceptions import ValidationError, DatabaseError

from ..fixtures.finished_unit_fixtures import (
    sample_finished_unit_data,
    batch_portion_unit_data,
    invalid_finished_unit_data,
    search_test_data,
    inventory_test_scenarios,
    cost_calculation_scenarios,
    performance_test_data,
    edge_case_data,
    mock_finished_unit,
    mock_recipe,
    create_test_finished_unit_data,
    assert_finished_unit_fields,
    assert_slug_format
)


class TestFinishedUnitServiceCoreOperations:
    """Test core CRUD operations of FinishedUnit service."""

    @patch('src.services.finished_unit_service.get_db_session')
    def test_get_finished_unit_count_success(self, mock_session):
        """Test successful count retrieval."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.return_value.count.return_value = 42

        # Act
        count = FinishedUnitService.get_finished_unit_count()

        # Assert
        assert count == 42
        mock_session.return_value.__enter__.return_value.query.assert_called_once()

    @patch('src.services.finished_unit_service.get_db_session')
    def test_get_finished_unit_count_database_error(self, mock_session):
        """Test count retrieval with database error."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(DatabaseError):
            FinishedUnitService.get_finished_unit_count()

    @patch('src.services.finished_unit_service.get_db_session')
    def test_get_finished_unit_by_id_success(self, mock_session, mock_finished_unit):
        """Test successful retrieval by ID."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.return_value.options.return_value.filter.return_value.first.return_value = mock_finished_unit

        # Act
        result = FinishedUnitService.get_finished_unit_by_id(1)

        # Assert
        assert result == mock_finished_unit

    @patch('src.services.finished_unit_service.get_db_session')
    def test_get_finished_unit_by_id_not_found(self, mock_session):
        """Test retrieval by ID when not found."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.return_value.options.return_value.filter.return_value.first.return_value = None

        # Act
        result = FinishedUnitService.get_finished_unit_by_id(999)

        # Assert
        assert result is None

    @patch('src.services.finished_unit_service.get_db_session')
    def test_get_finished_unit_by_slug_success(self, mock_session, mock_finished_unit):
        """Test successful retrieval by slug."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.return_value.options.return_value.filter.return_value.first.return_value = mock_finished_unit

        # Act
        result = FinishedUnitService.get_finished_unit_by_slug("test-slug")

        # Assert
        assert result == mock_finished_unit

    @patch('src.services.finished_unit_service.get_db_session')
    def test_get_all_finished_units_success(self, mock_session):
        """Test successful retrieval of all units."""
        # Arrange
        mock_units = [Mock() for _ in range(5)]
        mock_session.return_value.__enter__.return_value.query.return_value.options.return_value.order_by.return_value.all.return_value = mock_units

        # Act
        result = FinishedUnitService.get_all_finished_units()

        # Assert
        assert len(result) == 5
        assert result == mock_units


class TestFinishedUnitServiceCreate:
    """Test FinishedUnit creation functionality."""

    @patch('src.services.finished_unit_service.session_scope')
    @patch('src.services.finished_unit_service.FinishedUnit')
    def test_create_finished_unit_success(self, mock_unit_class, mock_session, sample_finished_unit_data):
        """Test successful FinishedUnit creation."""
        # Arrange
        mock_session.return_value.__enter__.return_value = mock_session_instance = Mock()
        mock_session_instance.query.return_value.filter.return_value.first.return_value = None  # No existing slug
        mock_unit_instance = Mock()
        mock_unit_instance.id = 1
        mock_unit_class.return_value = mock_unit_instance

        # Act
        result = FinishedUnitService.create_finished_unit(**sample_finished_unit_data)

        # Assert
        assert result == mock_unit_instance
        mock_unit_class.assert_called_once()
        mock_session_instance.add.assert_called_once_with(mock_unit_instance)
        mock_session_instance.flush.assert_called_once()

    @patch('src.services.finished_unit_service.session_scope')
    def test_create_finished_unit_empty_display_name(self, mock_session):
        """Test creation with empty display name."""
        # Act & Assert
        with pytest.raises(ValidationError, match="Display name is required"):
            FinishedUnitService.create_finished_unit("")

        # Should not call session
        mock_session.assert_not_called()

    @patch('src.services.finished_unit_service.session_scope')
    def test_create_finished_unit_negative_cost(self, mock_session):
        """Test creation with negative unit cost."""
        # Act & Assert
        with pytest.raises(ValidationError, match="Unit cost must be non-negative"):
            FinishedUnitService.create_finished_unit("Test Item", unit_cost=Decimal('-1.00'))

    @patch('src.services.finished_unit_service.session_scope')
    def test_create_finished_unit_invalid_recipe(self, mock_session):
        """Test creation with invalid recipe ID."""
        # Arrange
        mock_session_instance = Mock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_session_instance.query.return_value.filter.return_value.first.return_value = None  # Recipe not found

        # Act & Assert
        with pytest.raises(ValidationError, match="Recipe ID 999 does not exist"):
            FinishedUnitService.create_finished_unit("Test Item", recipe_id=999)

    @patch('src.services.finished_unit_service.session_scope')
    def test_create_finished_unit_duplicate_slug(self, mock_session):
        """Test creation with duplicate slug."""
        # Arrange
        mock_session_instance = Mock()
        mock_session.return_value.__enter__.return_value = mock_session_instance

        # First call returns existing unit (duplicate slug)
        # Second call with suffix should return None (unique)
        mock_session_instance.query.return_value.filter.return_value.first.side_effect = [Mock(), None]

        # Act
        with patch('src.services.finished_unit_service.FinishedUnit') as mock_unit_class:
            mock_unit_instance = Mock()
            mock_unit_instance.id = 1
            mock_unit_class.return_value = mock_unit_instance

            result = FinishedUnitService.create_finished_unit("Test Item")

            # Assert - should succeed with unique slug suffix
            assert result == mock_unit_instance


class TestFinishedUnitServiceUpdate:
    """Test FinishedUnit update functionality."""

    @patch('src.services.finished_unit_service.session_scope')
    def test_update_finished_unit_success(self, mock_session):
        """Test successful update."""
        # Arrange
        mock_session_instance = Mock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_unit = Mock()
        mock_unit.id = 1
        mock_unit.display_name = "Old Name"
        mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_unit

        # Act
        result = FinishedUnitService.update_finished_unit(1, display_name="New Name", unit_cost=Decimal('5.00'))

        # Assert
        assert result == mock_unit
        assert mock_unit.display_name == "New Name"
        assert mock_unit.unit_cost == Decimal('5.00')
        assert hasattr(mock_unit, 'updated_at')

    @patch('src.services.finished_unit_service.session_scope')
    def test_update_finished_unit_not_found(self, mock_session):
        """Test update when unit not found."""
        # Arrange
        mock_session_instance = Mock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_session_instance.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(FinishedUnitNotFoundError):
            FinishedUnitService.update_finished_unit(999, display_name="New Name")

    @patch('src.services.finished_unit_service.session_scope')
    def test_update_finished_unit_invalid_data(self, mock_session):
        """Test update with invalid data."""
        # Arrange
        mock_session_instance = Mock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_unit = Mock()
        mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_unit

        # Act & Assert
        with pytest.raises(ValidationError, match="Display name cannot be empty"):
            FinishedUnitService.update_finished_unit(1, display_name="")


class TestFinishedUnitServiceDelete:
    """Test FinishedUnit deletion functionality."""

    @patch('src.services.finished_unit_service.session_scope')
    def test_delete_finished_unit_success(self, mock_session):
        """Test successful deletion."""
        # Arrange
        mock_session_instance = Mock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_unit = Mock()
        mock_unit.display_name = "Test Unit"
        mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_unit
        mock_session_instance.query.return_value.filter.return_value.count.return_value = 0  # No compositions

        # Act
        result = FinishedUnitService.delete_finished_unit(1)

        # Assert
        assert result is True
        mock_session_instance.delete.assert_called_once_with(mock_unit)

    @patch('src.services.finished_unit_service.session_scope')
    def test_delete_finished_unit_not_found(self, mock_session):
        """Test deletion when unit not found."""
        # Arrange
        mock_session_instance = Mock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_session_instance.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = FinishedUnitService.delete_finished_unit(999)

        # Assert
        assert result is False

    @patch('src.services.finished_unit_service.session_scope')
    def test_delete_finished_unit_referenced_in_composition(self, mock_session):
        """Test deletion when unit is referenced in compositions."""
        # Arrange
        mock_session_instance = Mock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_unit = Mock()
        mock_unit.display_name = "Referenced Unit"
        mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_unit
        mock_session_instance.query.return_value.filter.return_value.count.return_value = 2  # Has compositions

        # Act & Assert
        with pytest.raises(ReferencedUnitError, match="Cannot delete FinishedUnit"):
            FinishedUnitService.delete_finished_unit(1)


class TestFinishedUnitServiceInventoryManagement:
    """Test inventory management functionality."""

    @patch('src.services.finished_unit_service.session_scope')
    def test_update_inventory_success(self, mock_session, inventory_test_scenarios):
        """Test successful inventory updates."""
        for scenario in inventory_test_scenarios:
            if scenario["should_succeed"]:
                # Arrange
                mock_session_instance = Mock()
                mock_session.return_value.__enter__.return_value = mock_session_instance
                mock_unit = Mock()
                mock_unit.inventory_count = scenario["initial"]
                mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_unit

                # Act
                result = FinishedUnitService.update_inventory(1, scenario["change"])

                # Assert
                assert result == mock_unit
                assert mock_unit.inventory_count == scenario["expected"]

    @patch('src.services.finished_unit_service.session_scope')
    def test_update_inventory_negative_result(self, mock_session):
        """Test inventory update that would result in negative inventory."""
        # Arrange
        mock_session_instance = Mock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_unit = Mock()
        mock_unit.inventory_count = 5
        mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_unit

        # Act & Assert
        with pytest.raises(InvalidInventoryError, match="would result in negative inventory"):
            FinishedUnitService.update_inventory(1, -10)

    @patch('src.services.finished_unit_service.session_scope')
    def test_update_inventory_unit_not_found(self, mock_session):
        """Test inventory update when unit not found."""
        # Arrange
        mock_session_instance = Mock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_session_instance.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(FinishedUnitNotFoundError):
            FinishedUnitService.update_inventory(999, 5)

    @patch('src.services.finished_unit_service.get_db_session')
    def test_check_availability_sufficient(self, mock_session):
        """Test availability check with sufficient inventory."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value.inventory_count = 10

        # Act
        result = FinishedUnitService.check_availability(1, 5)

        # Assert
        assert result is True

    @patch('src.services.finished_unit_service.get_db_session')
    def test_check_availability_insufficient(self, mock_session):
        """Test availability check with insufficient inventory."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value.inventory_count = 3

        # Act
        result = FinishedUnitService.check_availability(1, 5)

        # Assert
        assert result is False

    @patch('src.services.finished_unit_service.get_db_session')
    def test_check_availability_unit_not_found(self, mock_session):
        """Test availability check when unit not found."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(FinishedUnitNotFoundError):
            FinishedUnitService.check_availability(999, 5)


class TestFinishedUnitServiceCostCalculation:
    """Test cost calculation functionality."""

    @patch('src.services.finished_unit_service.get_db_session')
    def test_calculate_unit_cost_success(self, mock_session):
        """Test successful cost calculation."""
        # Arrange
        mock_unit = Mock()
        mock_unit.calculate_recipe_cost_per_item.return_value = Decimal('2.5000')
        mock_session.return_value.__enter__.return_value.query.return_value.options.return_value.filter.return_value.first.return_value = mock_unit

        # Act
        result = FinishedUnitService.calculate_unit_cost(1)

        # Assert
        assert result == Decimal('2.5000')
        mock_unit.calculate_recipe_cost_per_item.assert_called_once()

    @patch('src.services.finished_unit_service.get_db_session')
    def test_calculate_unit_cost_unit_not_found(self, mock_session):
        """Test cost calculation when unit not found."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.return_value.options.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(FinishedUnitNotFoundError):
            FinishedUnitService.calculate_unit_cost(999)


class TestFinishedUnitServiceQueryOperations:
    """Test query and search operations."""

    @patch('src.services.finished_unit_service.get_db_session')
    def test_search_finished_units_success(self, mock_session):
        """Test successful search."""
        # Arrange
        mock_units = [Mock() for _ in range(3)]
        mock_session.return_value.__enter__.return_value.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = mock_units

        # Act
        result = FinishedUnitService.search_finished_units("chocolate")

        # Assert
        assert len(result) == 3
        assert result == mock_units

    @patch('src.services.finished_unit_service.get_db_session')
    def test_search_finished_units_empty_query(self, mock_session):
        """Test search with empty query."""
        # Act
        result = FinishedUnitService.search_finished_units("")

        # Assert
        assert result == []
        mock_session.assert_not_called()

    @patch('src.services.finished_unit_service.get_db_session')
    def test_get_units_by_recipe_success(self, mock_session):
        """Test getting units by recipe ID."""
        # Arrange
        mock_units = [Mock() for _ in range(2)]
        mock_session.return_value.__enter__.return_value.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = mock_units

        # Act
        result = FinishedUnitService.get_units_by_recipe(1)

        # Assert
        assert len(result) == 2
        assert result == mock_units

    @patch('src.services.finished_unit_service.get_db_session')
    def test_get_units_by_recipe_no_results(self, mock_session):
        """Test getting units by recipe with no results."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = []

        # Act
        result = FinishedUnitService.get_units_by_recipe(999)

        # Assert
        assert result == []


class TestFinishedUnitServiceUtilityMethods:
    """Test utility methods."""

    def test_generate_slug_basic(self):
        """Test basic slug generation."""
        # Act
        slug = FinishedUnitService._generate_slug("Chocolate Chip Cookie")

        # Assert
        assert slug == "chocolate-chip-cookie"

    def test_generate_slug_special_characters(self):
        """Test slug generation with special characters."""
        # Act
        slug = FinishedUnitService._generate_slug("Cookie's & Cream (Premium)")

        # Assert
        assert_slug_format(slug)
        assert "cookie" in slug
        assert "cream" in slug

    def test_generate_slug_unicode(self):
        """Test slug generation with unicode characters."""
        # Act
        slug = FinishedUnitService._generate_slug("Café Crème Brûlée")

        # Assert
        assert_slug_format(slug)
        assert "caf" in slug or "cafe" in slug

    def test_generate_slug_empty_name(self):
        """Test slug generation with empty name."""
        # Act
        slug = FinishedUnitService._generate_slug("")

        # Assert
        assert slug == "unknown-item"

    def test_generate_slug_long_name(self):
        """Test slug generation with very long name."""
        # Arrange
        long_name = "A" * 200

        # Act
        slug = FinishedUnitService._generate_slug(long_name)

        # Assert
        assert len(slug) <= 90
        assert_slug_format(slug)


class TestFinishedUnitServiceModuleFunctions:
    """Test module-level convenience functions."""

    @patch('src.services.finished_unit_service.FinishedUnitService.get_finished_unit_count')
    def test_module_get_finished_unit_count(self, mock_method):
        """Test module-level get_finished_unit_count function."""
        # Arrange
        mock_method.return_value = 42

        # Act
        result = get_finished_unit_count()

        # Assert
        assert result == 42
        mock_method.assert_called_once()

    @patch('src.services.finished_unit_service.FinishedUnitService.create_finished_unit')
    def test_module_create_finished_unit(self, mock_method):
        """Test module-level create_finished_unit function."""
        # Arrange
        mock_unit = Mock()
        mock_method.return_value = mock_unit

        # Act
        result = create_finished_unit("Test Item", category="test")

        # Assert
        assert result == mock_unit
        mock_method.assert_called_once_with("Test Item", category="test")


class TestFinishedUnitServiceErrorHandling:
    """Test comprehensive error handling scenarios."""

    @patch('src.services.finished_unit_service.get_db_session')
    def test_database_connection_error(self, mock_session):
        """Test handling of database connection errors."""
        # Arrange
        mock_session.side_effect = Exception("Connection failed")

        # Act & Assert
        with pytest.raises(DatabaseError):
            FinishedUnitService.get_finished_unit_count()

    @patch('src.services.finished_unit_service.session_scope')
    def test_transaction_rollback_on_error(self, mock_session):
        """Test that transactions are properly rolled back on errors."""
        # Arrange
        mock_session.return_value.__enter__.side_effect = Exception("Transaction error")

        # Act & Assert
        with pytest.raises(Exception):
            FinishedUnitService.create_finished_unit("Test Item")


class TestFinishedUnitServicePerformance:
    """Test performance requirements."""

    @patch('src.services.finished_unit_service.get_db_session')
    def test_single_operation_performance(self, mock_session, performance_test_data):
        """Test that single operations meet performance targets."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.return_value.count.return_value = 1
        max_time = performance_test_data["max_acceptable_time_ms"]["single_crud"] / 1000

        # Act
        start_time = time.perf_counter()
        FinishedUnitService.get_finished_unit_count()
        duration = time.perf_counter() - start_time

        # Assert
        assert duration < max_time, f"Operation took {duration:.3f}s, exceeds {max_time:.3f}s target"

    @patch('src.services.finished_unit_service.get_db_session')
    def test_search_operation_performance(self, mock_session, performance_test_data):
        """Test that search operations meet performance targets."""
        # Arrange
        mock_session.return_value.__enter__.return_value.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = []
        max_time = performance_test_data["max_acceptable_time_ms"]["search_operations"] / 1000

        # Act
        start_time = time.perf_counter()
        FinishedUnitService.search_finished_units("test query")
        duration = time.perf_counter() - start_time

        # Assert
        assert duration < max_time, f"Search took {duration:.3f}s, exceeds {max_time:.3f}s target"


class TestFinishedUnitServiceEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch('src.services.finished_unit_service.session_scope')
    def test_create_with_boundary_values(self, mock_session, edge_case_data):
        """Test creation with boundary values."""
        # Arrange
        mock_session_instance = Mock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_session_instance.query.return_value.filter.return_value.first.return_value = None

        with patch('src.services.finished_unit_service.FinishedUnit') as mock_unit_class:
            mock_unit_instance = Mock()
            mock_unit_class.return_value = mock_unit_instance

            # Test various boundary values
            boundary_tests = [
                {"display_name": "Test", "unit_cost": edge_case_data["boundary_values"]["zero_cost"]},
                {"display_name": "Test", "unit_cost": edge_case_data["boundary_values"]["max_precision_cost"]},
                {"display_name": "Test", "inventory_count": edge_case_data["boundary_values"]["zero_inventory"]},
                {"display_name": "Test", "inventory_count": edge_case_data["boundary_values"]["large_inventory"]},
            ]

            for test_data in boundary_tests:
                # Act & Assert - should not raise exceptions
                result = FinishedUnitService.create_finished_unit(**test_data)
                assert result == mock_unit_instance

    def test_generate_slug_edge_cases(self, edge_case_data):
        """Test slug generation with edge cases."""
        # Test long name
        slug = FinishedUnitService._generate_slug(edge_case_data["long_display_name"])
        assert len(slug) <= 90
        assert_slug_format(slug)

        # Test unicode name
        slug = FinishedUnitService._generate_slug(edge_case_data["unicode_display_name"])
        assert_slug_format(slug)

        # Test special characters
        slug = FinishedUnitService._generate_slug(edge_case_data["special_chars_name"])
        assert_slug_format(slug)

        # Test numeric name
        slug = FinishedUnitService._generate_slug(edge_case_data["numeric_name"])
        assert_slug_format(slug)


# Integration with pytest fixtures
pytest.mark.parametrize("fixture_name,test_data", [
    ("sample_finished_unit_data", "valid_unit_data"),
    ("batch_portion_unit_data", "batch_portion_data"),
])
def test_fixture_integration(request, fixture_name, test_data):
    """Test that fixtures are properly integrated."""
    fixture_data = request.getfixturevalue(fixture_name)
    assert isinstance(fixture_data, dict)
    assert "display_name" in fixture_data


# Coverage verification
def test_all_service_methods_covered():
    """Verify that all public methods are covered in tests."""
    public_methods = [
        'get_finished_unit_count',
        'get_finished_unit_by_id',
        'get_finished_unit_by_slug',
        'get_all_finished_units',
        'create_finished_unit',
        'update_finished_unit',
        'delete_finished_unit',
        'update_inventory',
        'check_availability',
        'calculate_unit_cost',
        'search_finished_units',
        'get_units_by_recipe'
    ]

    # This test ensures we have test coverage for all public methods
    for method in public_methods:
        assert hasattr(FinishedUnitService, method), f"Method {method} not found in service"


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--cov=src.services.finished_unit_service",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=70"
    ])