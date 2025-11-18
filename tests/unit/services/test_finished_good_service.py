"""
Unit tests for FinishedGood Service.

Comprehensive test suite covering all assembly management functionality including
CRUD operations, component management, hierarchy operations, cost calculations,
and business rule validation.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from src.services.finished_good_service import (
    FinishedGoodService,
    FinishedGoodNotFoundError,
    CircularReferenceError,
    InsufficientInventoryError,
    InvalidComponentError,
    AssemblyIntegrityError
)
from src.models import FinishedGood, FinishedUnit, Composition, AssemblyType
from src.services.exceptions import ValidationError, DatabaseError

from ...fixtures.assembly_fixtures import (
    mock_assembly,
    mock_gift_box,
    mock_variety_pack,
    sample_assembly_data,
    sample_component_specifications,
    cost_calculation_scenarios,
    business_rule_test_cases,
    inventory_management_scenarios,
    assert_assembly_fields,
    assert_cost_calculation
)


class TestFinishedGoodServiceCRUD:
    """Test CRUD operations for FinishedGood assemblies."""

    @patch('src.services.finished_good_service.get_db_session')
    def test_get_finished_good_by_id_success(self, mock_session, mock_assembly):
        """Test successful retrieval of FinishedGood by ID."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_assembly

        # Execute
        result = FinishedGoodService.get_finished_good_by_id(1)

        # Verify
        assert result == mock_assembly
        mock_db.query.assert_called_once_with(FinishedGood)

    @patch('src.services.finished_good_service.get_db_session')
    def test_get_finished_good_by_id_not_found(self, mock_session):
        """Test retrieval when FinishedGood not found."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None

        # Execute
        result = FinishedGoodService.get_finished_good_by_id(999)

        # Verify
        assert result is None

    @patch('src.services.finished_good_service.get_db_session')
    def test_get_finished_good_by_slug_success(self, mock_session, mock_assembly):
        """Test successful retrieval of FinishedGood by slug."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_assembly

        # Execute
        result = FinishedGoodService.get_finished_good_by_slug("test-assembly")

        # Verify
        assert result == mock_assembly
        mock_db.query.assert_called_once_with(FinishedGood)

    @patch('src.services.finished_good_service.get_db_session')
    def test_get_all_finished_goods(self, mock_session, mock_assembly, mock_gift_box):
        """Test retrieval of all FinishedGoods."""
        # Setup
        assemblies = [mock_assembly, mock_gift_box]
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.order_by.return_value.all.return_value = assemblies

        # Execute
        result = FinishedGoodService.get_all_finished_goods()

        # Verify
        assert result == assemblies
        assert len(result) == 2

    @patch('src.services.finished_good_service.session_scope')
    @patch('src.services.finished_good_service.FinishedGoodService._generate_slug')
    @patch('src.services.finished_good_service.validate_assembly_type_business_rules')
    def test_create_finished_good_success(self, mock_validate, mock_slug, mock_session, sample_assembly_data):
        """Test successful creation of FinishedGood assembly."""
        # Setup
        mock_slug.return_value = "premium-gift-box"
        mock_validate.return_value = (True, [])
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing slug

        # Execute
        result = FinishedGoodService.create_finished_good(**sample_assembly_data)

        # Verify
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        assert isinstance(result, FinishedGood)

    @patch('src.services.finished_good_service.session_scope')
    def test_create_finished_good_invalid_display_name(self, mock_session):
        """Test creation with invalid display name."""
        # Execute & Verify
        with pytest.raises(ValidationError, match="Display name is required"):
            FinishedGoodService.create_finished_good("", AssemblyType.GIFT_BOX)

        with pytest.raises(ValidationError, match="Display name is required"):
            FinishedGoodService.create_finished_good("   ", AssemblyType.GIFT_BOX)

    @patch('src.services.finished_good_service.session_scope')
    def test_create_finished_good_invalid_assembly_type(self, mock_session):
        """Test creation with invalid assembly type."""
        # Execute & Verify
        with pytest.raises(ValidationError, match="Assembly type must be a valid AssemblyType enum"):
            FinishedGoodService.create_finished_good("Test Assembly", "invalid_type")

    @patch('src.services.finished_good_service.session_scope')
    def test_update_finished_good_success(self, mock_session, mock_assembly):
        """Test successful update of FinishedGood."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_assembly

        updates = {"display_name": "Updated Assembly", "inventory_count": 10}

        # Execute
        result = FinishedGoodService.update_finished_good(1, **updates)

        # Verify
        assert result == mock_assembly
        assert mock_assembly.display_name == "Updated Assembly"
        assert mock_assembly.inventory_count == 10

    @patch('src.services.finished_good_service.session_scope')
    def test_update_finished_good_not_found(self, mock_session):
        """Test update when assembly not found."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Execute & Verify
        with pytest.raises(FinishedGoodNotFoundError, match="FinishedGood ID 999 not found"):
            FinishedGoodService.update_finished_good(999, display_name="Updated")

    @patch('src.services.finished_good_service.session_scope')
    def test_delete_finished_good_success(self, mock_session, mock_assembly):
        """Test successful deletion of FinishedGood."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_assembly
        mock_db.query.return_value.filter.return_value.count.return_value = 0  # No usage

        # Execute
        result = FinishedGoodService.delete_finished_good(1)

        # Verify
        assert result is True
        mock_db.delete.assert_called_once_with(mock_assembly)

    @patch('src.services.finished_good_service.session_scope')
    def test_delete_finished_good_not_found(self, mock_session):
        """Test deletion when assembly not found."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Execute
        result = FinishedGoodService.delete_finished_good(999)

        # Verify
        assert result is False


class TestFinishedGoodServiceComponents:
    """Test component management operations."""

    @patch('src.services.finished_good_service.session_scope')
    @patch('src.services.finished_good_service.FinishedGoodService.validate_no_circular_references')
    def test_add_component_finished_unit_success(self, mock_validate, mock_session, mock_assembly):
        """Test successful addition of FinishedUnit component."""
        # Setup
        mock_validate.return_value = True
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_unit = Mock()
        mock_unit.id = 1

        # Mock queries
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_assembly)))),  # Assembly query
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_unit)))),      # Component query
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=None))))           # Existing composition query
        ]

        # Execute
        result = FinishedGoodService.add_component(1, "finished_unit", 1, 3)

        # Verify
        assert result is True
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @patch('src.services.finished_good_service.session_scope')
    def test_add_component_invalid_type(self, mock_session):
        """Test adding component with invalid type."""
        # Execute & Verify
        with pytest.raises(ValidationError, match="Component type must be"):
            FinishedGoodService.add_component(1, "invalid_type", 1, 3)

    @patch('src.services.finished_good_service.session_scope')
    def test_add_component_invalid_quantity(self, mock_session):
        """Test adding component with invalid quantity."""
        # Execute & Verify
        with pytest.raises(ValidationError, match="Quantity must be positive"):
            FinishedGoodService.add_component(1, "finished_unit", 1, 0)

        with pytest.raises(ValidationError, match="Quantity must be positive"):
            FinishedGoodService.add_component(1, "finished_unit", 1, -1)

    @patch('src.services.finished_good_service.session_scope')
    @patch('src.services.finished_good_service.FinishedGoodService.validate_no_circular_references')
    def test_add_component_duplicate_detection(self, mock_validate, mock_session, mock_assembly):
        """Test duplicate component detection when adding same component twice."""
        # Setup
        mock_validate.return_value = True
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_assembly

        # Mock existing composition for this component
        existing_composition = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_composition

        # Execute & Verify - should raise ValidationError for duplicate component
        with pytest.raises(ValidationError, match="Component already exists in assembly"):
            FinishedGoodService.add_component(1, "finished_unit", 1, 3)

    @patch('src.services.finished_good_service.session_scope')
    def test_remove_component_success(self, mock_session, mock_assembly):
        """Test successful removal of component."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_composition = Mock()
        mock_composition.id = 1

        # Mock queries
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_assembly)))),     # Assembly query
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_composition))))   # Composition query
        ]

        # Execute
        result = FinishedGoodService.remove_component(1, 1)

        # Verify
        assert result is True
        mock_db.delete.assert_called_once_with(mock_composition)

    @patch('src.services.finished_good_service.session_scope')
    def test_remove_component_not_found(self, mock_session, mock_assembly):
        """Test remove component returning False when composition not found."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock queries - assembly exists but composition does not
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_assembly)))),     # Assembly query
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=None))))               # Composition not found
        ]

        # Execute
        result = FinishedGoodService.remove_component(1, 1)

        # Verify
        assert result is False
        mock_db.delete.assert_not_called()

    @patch('src.services.finished_good_service.session_scope')
    def test_update_component_quantity_success(self, mock_session):
        """Test successful update of component quantity."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_composition = Mock()
        mock_composition.id = 1
        mock_composition.assembly_id = 1

        mock_db.query.return_value.filter.return_value.first.return_value = mock_composition

        # Execute
        result = FinishedGoodService.update_component_quantity(1, 5)

        # Verify
        assert result is True
        assert mock_composition.component_quantity == 5

    @patch('src.services.finished_good_service.session_scope')
    def test_update_component_quantity_invalid_value(self, mock_session):
        """Test update component quantity with invalid value (≤ 0)."""
        # Execute & Verify - zero quantity
        with pytest.raises(ValidationError, match="Quantity must be positive"):
            FinishedGoodService.update_component_quantity(1, 0)

        # Execute & Verify - negative quantity
        with pytest.raises(ValidationError, match="Quantity must be positive"):
            FinishedGoodService.update_component_quantity(1, -1)


class TestFinishedGoodServiceHierarchy:
    """Test hierarchy and composition operations."""

    @patch('src.services.finished_good_service.get_db_session')
    def test_get_all_components_flattened(self, mock_session, mock_assembly):
        """Test getting flattened component list."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_assembly

        with patch.object(FinishedGoodService, '_get_flattened_components') as mock_flatten:
            mock_flatten.return_value = [{"component_type": "finished_unit", "total_quantity": 5}]

            # Execute
            result = FinishedGoodService.get_all_components(1, flatten=True)

            # Verify
            mock_flatten.assert_called_once_with(1, mock_db)
            assert len(result) == 1

    @patch('src.services.finished_good_service.get_db_session')
    def test_calculate_total_cost(self, mock_session, mock_assembly):
        """Test total cost calculation."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_assembly

        mock_assembly.calculate_component_cost.return_value = Decimal('25.50')

        # Execute
        result = FinishedGoodService.calculate_total_cost(1)

        # Verify
        assert result == Decimal('25.50')
        mock_assembly.calculate_component_cost.assert_called_once()

    @patch('src.services.finished_good_service.get_db_session')
    def test_check_assembly_availability(self, mock_session, mock_assembly):
        """Test assembly availability checking."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_assembly

        availability_result = {'can_assemble': True, 'missing_components': []}
        mock_assembly.can_assemble.return_value = availability_result

        # Execute
        result = FinishedGoodService.check_assembly_availability(1, 2)

        # Verify
        assert result == availability_result
        mock_assembly.can_assemble.assert_called_once_with(2)


class TestFinishedGoodServiceProduction:
    """Test assembly production operations."""

    @patch('src.services.finished_good_service.session_scope')
    @patch('src.services.finished_good_service.FinishedGoodService.check_assembly_availability')
    @patch('src.services.finished_good_service.finished_unit_service')
    def test_create_assembly_from_inventory_success(self, mock_unit_service, mock_availability, mock_session, mock_assembly):
        """Test successful assembly creation from inventory."""
        # Setup
        mock_availability.return_value = {'can_assemble': True}
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_assembly

        # Mock compositions
        mock_composition = Mock()
        mock_composition.component_quantity = 2
        mock_composition.finished_unit_id = 1
        mock_composition.finished_unit_component = Mock()
        mock_composition.finished_good_component = None
        mock_assembly.components = [mock_composition]

        # Execute
        result = FinishedGoodService.create_assembly_from_inventory(1, 3)

        # Verify
        assert result is True
        mock_unit_service.update_inventory.assert_called_once_with(1, -6)  # 2 * 3
        mock_assembly.update_inventory.assert_called_once_with(3)

    @patch('src.services.finished_good_service.session_scope')
    @patch('src.services.finished_good_service.FinishedGoodService.check_assembly_availability')
    def test_create_assembly_insufficient_inventory(self, mock_availability, mock_session):
        """Test assembly creation with insufficient inventory."""
        # Setup
        mock_availability.return_value = {
            'can_assemble': False,
            'missing_components': ['Unit 1: need 6, have 3']
        }

        # Execute & Verify
        with pytest.raises(InsufficientInventoryError, match="Cannot create 3 assemblies"):
            FinishedGoodService.create_assembly_from_inventory(1, 3)

    @patch('src.services.finished_good_service.session_scope')
    @patch('src.services.finished_good_service.finished_unit_service')
    def test_disassemble_into_components_success(self, mock_unit_service, mock_session, mock_assembly):
        """Test successful disassembly into components."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_assembly

        mock_assembly.inventory_count = 5

        # Mock compositions
        mock_composition = Mock()
        mock_composition.component_quantity = 2
        mock_composition.finished_unit_id = 1
        mock_composition.finished_unit_component = Mock()
        mock_composition.finished_good_component = None
        mock_assembly.components = [mock_composition]

        # Execute
        result = FinishedGoodService.disassemble_into_components(1, 2)

        # Verify
        assert result is True
        mock_unit_service.update_inventory.assert_called_once_with(1, 4)  # 2 * 2
        mock_assembly.update_inventory.assert_called_once_with(-2)


class TestFinishedGoodServiceValidation:
    """Test validation and business rule operations."""

    @patch('src.services.finished_good_service.get_db_session')
    def test_validate_no_circular_references_safe(self, mock_session):
        """Test circular reference validation when safe."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []  # No circular references

        # Execute
        result = FinishedGoodService.validate_no_circular_references(1, 2)

        # Verify
        assert result is True

    @patch('src.services.finished_good_service.get_db_session')
    def test_validate_no_circular_references_detected(self, mock_session):
        """Test circular reference detection."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock compositions that create circular reference
        mock_composition = Mock()
        mock_composition.finished_good_id = 1  # Points back to original assembly
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_composition]

        # Execute
        result = FinishedGoodService.validate_no_circular_references(1, 2)

        # Verify
        assert result is False


class TestFinishedGoodServiceQueries:
    """Test search and query operations."""

    @patch('src.services.finished_good_service.get_db_session')
    def test_search_finished_goods(self, mock_session, mock_assembly, mock_gift_box):
        """Test search functionality."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_gift_box]

        # Execute
        result = FinishedGoodService.search_finished_goods("gift")

        # Verify
        assert len(result) == 1
        assert result[0] == mock_gift_box

    @patch('src.services.finished_good_service.get_db_session')
    def test_search_finished_goods_empty_query(self, mock_session):
        """Test search with empty query."""
        # Execute
        result = FinishedGoodService.search_finished_goods("")

        # Verify
        assert result == []

    @patch('src.services.finished_good_service.get_db_session')
    def test_get_assemblies_by_type(self, mock_session, mock_gift_box):
        """Test filtering assemblies by type."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_gift_box]

        # Execute
        result = FinishedGoodService.get_assemblies_by_type(AssemblyType.GIFT_BOX)

        # Verify
        assert len(result) == 1
        assert result[0] == mock_gift_box


class TestFinishedGoodServiceBusinessRules:
    """Test assembly type business rules and metadata."""

    @patch('src.services.finished_good_service.get_db_session')
    @patch('src.services.finished_good_service.validate_assembly_type_business_rules')
    def test_validate_assembly_business_rules(self, mock_validate, mock_session, mock_assembly):
        """Test business rule validation for assembly."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_assembly

        mock_assembly.components = [Mock(), Mock(), Mock()]  # 3 components
        mock_assembly.assembly_type = AssemblyType.GIFT_BOX
        mock_validate.return_value = (True, [])

        # Execute
        result = FinishedGoodService.validate_assembly_business_rules(1)

        # Verify
        assert result['is_valid'] is True
        assert result['component_count'] == 3
        assert result['assembly_type'] == 'gift_box'

    @patch('src.services.finished_good_service.get_db_session')
    @patch('src.services.finished_good_service.calculate_packaging_cost')
    @patch('src.services.finished_good_service.get_suggested_retail_price')
    def test_calculate_suggested_pricing(self, mock_price, mock_packaging, mock_session, mock_assembly):
        """Test pricing calculation functionality."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_assembly

        mock_assembly.total_cost = Decimal('25.00')
        mock_assembly.assembly_type = AssemblyType.GIFT_BOX

        mock_packaging.return_value = Decimal('3.75')
        mock_price.return_value = Decimal('31.25')

        with patch.object(FinishedGoodService, 'calculate_total_cost', return_value=Decimal('21.25')):
            # Execute
            result = FinishedGoodService.calculate_suggested_pricing(1)

            # Verify
            assert result['total_cost'] == 25.0
            assert result['suggested_retail_price'] == 31.25


class TestFinishedGoodServiceUtilities:
    """Test utility methods."""

    def test_generate_slug(self):
        """Test slug generation."""
        # Execute & Verify
        assert FinishedGoodService._generate_slug("Test Assembly") == "test-assembly"
        assert FinishedGoodService._generate_slug("Holiday Gift Box!") == "holiday-gift-box"
        assert FinishedGoodService._generate_slug("Special Characters @#$%") == "special-characters"

    def test_generate_slug_empty(self):
        """Test slug generation with empty input."""
        # Execute & Verify
        assert FinishedGoodService._generate_slug("") == "unknown-assembly"
        assert FinishedGoodService._generate_slug(None) == "unknown-assembly"

    def test_get_assembly_type_recommendations(self):
        """Test getting assembly type recommendations."""
        # Execute
        result = FinishedGoodService.get_assembly_type_recommendations(AssemblyType.GIFT_BOX)

        # Verify
        assert result['assembly_type'] == 'gift_box'
        assert result['display_name'] == 'Gift Box'
        assert 'component_limits' in result
        assert 'business_rules' in result
        assert result['is_seasonal'] is False

    @patch('src.services.finished_good_service.session_scope')
    @patch('src.services.finished_good_service.validate_assembly_type_business_rules')
    def test_create_finished_good_duplicate_slug_handling(self, mock_validate, mock_session):
        """Test duplicate slug handling during create."""
        # Setup - mock business rules validation to pass
        mock_validate.return_value = (True, [])

        # Setup - mock session that returns existing assembly on first check
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        existing_assembly = MagicMock()
        existing_assembly.slug = "test-assembly"

        # First call finds existing slug, second call finds nothing (unique slug generated)
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            existing_assembly,  # First slug exists
            None  # Retry with unique suffix succeeds
        ]

        # Execute
        result = FinishedGoodService.create_finished_good("Test Assembly", AssemblyType.GIFT_BOX)

        # Verify - should generate unique slug and create assembly
        assert mock_db.query.return_value.filter.return_value.first.call_count == 2
        mock_db.add.assert_called_once()
        assert result.display_name == "Test Assembly"


class TestFinishedGoodServiceEdgeCases:
    """Test edge cases and error conditions."""

    @patch('src.services.finished_good_service.get_db_session')
    def test_database_error_handling(self, mock_session):
        """Test database error handling."""
        # Setup
        mock_session.side_effect = Exception("Database connection failed")

        # Execute & Verify
        with pytest.raises(DatabaseError, match="Failed to retrieve FinishedGood"):
            FinishedGoodService.get_finished_good_by_id(1)

    def test_assembly_business_rules_validation(self, business_rule_test_cases):
        """Test business rule validation for different assembly types."""
        for assembly_type, test_cases in business_rule_test_cases.items():
            # Test valid cases
            for valid_case in test_cases['valid_cases']:
                is_valid, errors = assembly_type.validate_component_count(valid_case['component_count'])
                assert is_valid, f"Should be valid for {assembly_type}: {valid_case}"

                is_valid, errors = assembly_type.validate_cost_constraints(Decimal(str(valid_case['total_cost'])))
                assert is_valid, f"Cost should be valid for {assembly_type}: {valid_case}"

            # Test invalid cases
            for invalid_case in test_cases['invalid_cases']:
                is_valid, errors = assembly_type.validate_component_count(invalid_case['component_count'])
                if 'component' in invalid_case['error']:
                    assert not is_valid, f"Should be invalid for {assembly_type}: {invalid_case}"

                is_valid, errors = assembly_type.validate_cost_constraints(Decimal(str(invalid_case['total_cost'])))
                if 'cost' in invalid_case['error']:
                    assert not is_valid, f"Cost should be invalid for {assembly_type}: {invalid_case}"


class TestFinishedGoodServiceIntegration:
    """Integration-style tests for complex workflows."""

    @patch('src.services.finished_good_service.session_scope')
    @patch('src.services.finished_good_service.FinishedGoodService._generate_slug')
    @patch('src.services.finished_good_service.validate_assembly_type_business_rules')
    @patch('src.services.finished_good_service.calculate_packaging_cost')
    def test_create_assembly_with_components_workflow(self, mock_packaging, mock_validate, mock_slug, mock_session):
        """Test complete workflow of creating assembly with components."""
        # Setup
        mock_slug.return_value = "test-workflow"
        mock_validate.return_value = (True, [])
        mock_packaging.return_value = Decimal('2.50')

        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # No existing slug
            Mock(unit_cost=Decimal('2.00')),  # Component 1
            Mock(unit_cost=Decimal('3.00'))   # Component 2
        ]

        components = [
            {"component_type": "finished_unit", "component_id": 1, "quantity": 3},
            {"component_type": "finished_unit", "component_id": 2, "quantity": 2}
        ]

        # Execute
        result = FinishedGoodService.create_finished_good(
            display_name="Test Workflow Assembly",
            assembly_type=AssemblyType.GIFT_BOX,
            components=components
        )

        # Verify
        mock_validate.assert_called_once()
        mock_packaging.assert_called_once()
        assert isinstance(result, FinishedGood)