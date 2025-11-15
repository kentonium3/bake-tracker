"""
Unit tests for Composition Service.

Comprehensive test suite covering all composition relationship management
functionality including CRUD operations, hierarchy traversal, validation,
bulk operations, and polymorphic relationship handling.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from src.services.composition_service import (
    CompositionService,
    CompositionNotFoundError,
    InvalidComponentTypeError,
    CircularReferenceError,
    DuplicateCompositionError,
    IntegrityViolationError
)
from src.models import Composition, FinishedGood, FinishedUnit
from src.services.exceptions import ValidationError, DatabaseError

from ...fixtures.assembly_fixtures import (
    mock_assembly,
    mock_composition,
    component_validation_scenarios,
    assembly_hierarchy_test_data,
    circular_reference_test_data,
    assert_composition_integrity
)


class TestCompositionServiceCRUD:
    """Test CRUD operations for Composition relationships."""

    @patch('src.services.composition_service.session_scope')
    def test_create_composition_finished_unit_success(self, mock_session, mock_assembly):
        """Test successful creation of FinishedUnit composition."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_unit = Mock()
        mock_unit.id = 1

        # Mock queries for validation
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_assembly)))),  # Assembly exists
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_unit)))),      # Component exists
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=None))))           # No existing composition
        ]

        with patch.object(CompositionService, 'validate_component_exists', return_value=True):
            # Execute
            result = CompositionService.create_composition(1, "finished_unit", 1, 3)

            # Verify
            assert isinstance(result, Composition)
            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()

    @patch('src.services.composition_service.session_scope')
    def test_create_composition_finished_good_success(self, mock_session, mock_assembly):
        """Test successful creation of FinishedGood composition."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_component = Mock()
        mock_component.id = 2

        # Mock queries
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_assembly)))),    # Assembly exists
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_component)))),   # Component exists
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=None))))             # No existing composition
        ]

        with patch.object(CompositionService, 'validate_component_exists', return_value=True), \
             patch.object(CompositionService, 'validate_no_circular_reference', return_value=True):
            # Execute
            result = CompositionService.create_composition(1, "finished_good", 2, 1)

            # Verify
            assert isinstance(result, Composition)

    def test_create_composition_invalid_component_type(self):
        """Test creation with invalid component type."""
        # Execute & Verify
        with pytest.raises(InvalidComponentTypeError, match="Component type must be"):
            CompositionService.create_composition(1, "invalid_type", 1, 3)

    def test_create_composition_invalid_quantity(self):
        """Test creation with invalid quantity."""
        # Execute & Verify
        with pytest.raises(ValidationError, match="Quantity must be positive"):
            CompositionService.create_composition(1, "finished_unit", 1, 0)

        with pytest.raises(ValidationError, match="Quantity must be positive"):
            CompositionService.create_composition(1, "finished_unit", 1, -1)

    @patch('src.services.composition_service.session_scope')
    def test_create_composition_circular_reference(self, mock_session, mock_assembly):
        """Test creation that would create circular reference."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_component = Mock()
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_assembly)))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_component))))
        ]

        with patch.object(CompositionService, 'validate_component_exists', return_value=True), \
             patch.object(CompositionService, 'validate_no_circular_reference', return_value=False):
            # Execute & Verify
            with pytest.raises(CircularReferenceError, match="would create circular reference"):
                CompositionService.create_composition(1, "finished_good", 2, 1)

    @patch('src.services.composition_service.get_db_session')
    def test_get_composition_by_id_success(self, mock_session, mock_composition):
        """Test successful retrieval of composition by ID."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_composition

        # Execute
        result = CompositionService.get_composition_by_id(1)

        # Verify
        assert result == mock_composition

    @patch('src.services.composition_service.get_db_session')
    def test_get_composition_by_id_not_found(self, mock_session):
        """Test retrieval when composition not found."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None

        # Execute
        result = CompositionService.get_composition_by_id(999)

        # Verify
        assert result is None

    @patch('src.services.composition_service.session_scope')
    def test_update_composition_success(self, mock_session, mock_composition):
        """Test successful update of composition."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_composition

        # Execute
        result = CompositionService.update_composition(1, component_quantity=5, component_notes="Updated notes")

        # Verify
        assert result == mock_composition
        assert mock_composition.component_quantity == 5
        assert mock_composition.component_notes == "Updated notes"

    @patch('src.services.composition_service.session_scope')
    def test_update_composition_not_found(self, mock_session):
        """Test update when composition not found."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Execute & Verify
        with pytest.raises(CompositionNotFoundError, match="Composition ID 999 not found"):
            CompositionService.update_composition(999, component_quantity=5)

    @patch('src.services.composition_service.session_scope')
    def test_delete_composition_success(self, mock_session, mock_composition):
        """Test successful deletion of composition."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_composition

        # Execute
        result = CompositionService.delete_composition(1)

        # Verify
        assert result is True
        mock_db.delete.assert_called_once_with(mock_composition)

    @patch('src.services.composition_service.session_scope')
    def test_delete_composition_not_found(self, mock_session):
        """Test deletion when composition not found."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Execute
        result = CompositionService.delete_composition(999)

        # Verify
        assert result is False


class TestCompositionServiceQueries:
    """Test assembly composition query operations."""

    @patch('src.services.composition_service.get_db_session')
    def test_get_assembly_components_ordered(self, mock_session):
        """Test getting assembly components in order."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_compositions = [Mock(), Mock()]
        mock_db.query.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = mock_compositions

        # Execute
        result = CompositionService.get_assembly_components(1, ordered=True)

        # Verify
        assert result == mock_compositions
        assert len(result) == 2

    @patch('src.services.composition_service.get_db_session')
    def test_get_assembly_components_unordered(self, mock_session):
        """Test getting assembly components without ordering."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_compositions = [Mock()]
        mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = mock_compositions

        # Execute
        result = CompositionService.get_assembly_components(1, ordered=False)

        # Verify
        assert result == mock_compositions

    @patch('src.services.composition_service.get_db_session')
    def test_get_component_usages_finished_unit(self, mock_session):
        """Test finding usages of a FinishedUnit component."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_usages = [Mock(), Mock()]
        mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = mock_usages

        # Execute
        result = CompositionService.get_component_usages("finished_unit", 1)

        # Verify
        assert result == mock_usages
        assert len(result) == 2

    @patch('src.services.composition_service.get_db_session')
    def test_get_component_usages_finished_good(self, mock_session):
        """Test finding usages of a FinishedGood component."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_usages = [Mock()]
        mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = mock_usages

        # Execute
        result = CompositionService.get_component_usages("finished_good", 2)

        # Verify
        assert result == mock_usages

    def test_get_component_usages_invalid_type(self):
        """Test getting usages with invalid component type."""
        # Execute & Verify
        with pytest.raises(InvalidComponentTypeError, match="Component type must be"):
            CompositionService.get_component_usages("invalid_type", 1)

    @patch('src.services.composition_service.get_db_session')
    def test_get_assembly_hierarchy(self, mock_session, mock_assembly):
        """Test building assembly hierarchy."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_assembly

        with patch.object(CompositionService, 'get_assembly_components') as mock_get_components:
            mock_get_components.return_value = []

            # Execute
            result = CompositionService.get_assembly_hierarchy(1, max_depth=3)

            # Verify
            assert result['assembly_id'] == mock_assembly.id
            assert result['max_depth'] == 3
            assert 'components' in result

    @patch('src.services.composition_service.get_db_session')
    def test_flatten_assembly_components(self, mock_session):
        """Test flattening assembly components."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        with patch.object(CompositionService, 'get_assembly_components') as mock_get_components:
            # Mock simple composition structure
            mock_unit = Mock()
            mock_unit.id = 1
            mock_unit.display_name = "Test Unit"
            mock_unit.slug = "test-unit"
            mock_unit.unit_cost = Decimal('2.00')
            mock_unit.inventory_count = 10

            mock_composition = Mock()
            mock_composition.component_quantity = 3
            mock_composition.finished_unit_component = mock_unit
            mock_composition.finished_good_component = None
            mock_composition.finished_unit_id = 1
            mock_composition.finished_good_id = None

            mock_get_components.return_value = [mock_composition]

            # Execute
            result = CompositionService.flatten_assembly_components(1)

            # Verify
            assert len(result) == 1
            assert result[0]['component_type'] == 'finished_unit'
            assert result[0]['total_quantity'] == 3
            assert result[0]['total_cost'] == 6.0  # 2.00 * 3


class TestCompositionServiceValidation:
    """Test validation operations."""

    @patch('src.services.composition_service.get_db_session')
    def test_validate_no_circular_reference_safe(self, mock_session):
        """Test validation when no circular reference exists."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock empty results (no cycles)
        mock_db.query.return_value.filter.return_value.all.return_value = []

        # Execute
        result = CompositionService.validate_no_circular_reference(1, 2, mock_db)

        # Verify
        assert result is True

    @patch('src.services.composition_service.get_db_session')
    def test_validate_no_circular_reference_detected(self, mock_session):
        """Test detection of circular reference."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock composition that creates circular reference
        mock_composition = Mock()
        mock_composition.finished_good_id = 1  # Points back to original
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_composition]

        # Execute
        result = CompositionService.validate_no_circular_reference(1, 2, mock_db)

        # Verify
        assert result is False

    @patch('src.services.composition_service.get_db_session')
    def test_validate_component_exists_finished_unit(self, mock_session):
        """Test validation of FinishedUnit component existence."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_unit = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_unit

        # Execute
        result = CompositionService.validate_component_exists("finished_unit", 1, mock_db)

        # Verify
        assert result is True

    @patch('src.services.composition_service.get_db_session')
    def test_validate_component_exists_not_found(self, mock_session):
        """Test validation when component doesn't exist."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Execute
        result = CompositionService.validate_component_exists("finished_unit", 999, mock_db)

        # Verify
        assert result is False

    @patch('src.services.composition_service.get_db_session')
    def test_check_composition_integrity(self, mock_session):
        """Test composition integrity checking."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock valid composition
        mock_composition = Mock()
        mock_composition.id = 1
        mock_composition.finished_unit_id = 1
        mock_composition.finished_good_id = None
        mock_composition.component_quantity = 3
        mock_composition.finished_unit_component = Mock()
        mock_composition.finished_good_component = None

        with patch.object(CompositionService, 'get_assembly_components') as mock_get_components, \
             patch.object(CompositionService, 'validate_no_circular_reference', return_value=True):
            mock_get_components.return_value = [mock_composition]

            # Execute
            result = CompositionService.check_composition_integrity(1)

            # Verify
            assert result['is_valid'] is True
            assert result['issues_count'] == 0


class TestCompositionServiceBulkOperations:
    """Test bulk operations."""

    @patch('src.services.composition_service.session_scope')
    def test_bulk_create_compositions_success(self, mock_session):
        """Test successful bulk creation of compositions."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock assembly and component existence
        mock_assembly = Mock()
        mock_unit = Mock()

        def mock_query_side_effect(*args):
            if args[0] == FinishedGood:
                return Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_assembly))))
            elif args[0] == FinishedUnit:
                return Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_unit))))

        mock_db.query.side_effect = mock_query_side_effect

        compositions_specs = [
            {"assembly_id": 1, "component_type": "finished_unit", "component_id": 1, "quantity": 2},
            {"assembly_id": 1, "component_type": "finished_unit", "component_id": 2, "quantity": 3}
        ]

        with patch.object(CompositionService, 'validate_component_exists', return_value=True):
            # Execute
            result = CompositionService.bulk_create_compositions(compositions_specs)

            # Verify
            assert len(result) == 2
            assert mock_db.add.call_count == 2

    def test_bulk_create_compositions_empty(self):
        """Test bulk creation with empty list."""
        # Execute
        result = CompositionService.bulk_create_compositions([])

        # Verify
        assert result == []

    @patch('src.services.composition_service.session_scope')
    def test_reorder_assembly_components_success(self, mock_session):
        """Test successful reordering of assembly components."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_comp1 = Mock()
        mock_comp1.id = 1
        mock_comp1.sort_order = 0

        mock_comp2 = Mock()
        mock_comp2.id = 2
        mock_comp2.sort_order = 1

        compositions = [mock_comp1, mock_comp2]
        mock_db.query.return_value.filter.return_value.all.return_value = compositions

        # Execute
        result = CompositionService.reorder_assembly_components(1, [2, 1])

        # Verify
        assert result is True
        assert mock_comp1.sort_order == 1  # Moved to position 1
        assert mock_comp2.sort_order == 0  # Moved to position 0

    @patch('src.services.composition_service.session_scope')
    def test_reorder_assembly_components_invalid_id(self, mock_session):
        """Test reordering with invalid composition ID."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_comp = Mock()
        mock_comp.id = 1
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_comp]

        # Execute & Verify
        with pytest.raises(ValidationError, match="Composition ID 999 not found"):
            CompositionService.reorder_assembly_components(1, [999])

    @patch('src.services.composition_service.session_scope')
    def test_copy_assembly_composition_success(self, mock_session):
        """Test successful copying of assembly composition."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock assemblies
        source_assembly = Mock()
        target_assembly = Mock()

        def assembly_query_side_effect(assembly_id):
            if assembly_id == 1:
                return Mock(filter=Mock(return_value=Mock(first=Mock(return_value=source_assembly))))
            else:
                return Mock(filter=Mock(return_value=Mock(first=Mock(return_value=target_assembly))))

        mock_db.query.return_value.filter.side_effect = assembly_query_side_effect

        # Mock source compositions
        mock_composition = Mock()
        mock_composition.component_quantity = 3
        mock_composition.component_notes = "Test notes"
        mock_composition.sort_order = 0
        mock_composition.finished_unit_id = 1
        mock_composition.finished_good_id = None

        with patch.object(CompositionService, 'get_assembly_components') as mock_get_components, \
             patch.object(CompositionService, 'validate_no_circular_reference', return_value=True):
            mock_get_components.return_value = [mock_composition]

            # Execute
            result = CompositionService.copy_assembly_composition(1, 2)

            # Verify
            assert result is True
            mock_db.add.assert_called_once()


class TestCompositionServiceCalculations:
    """Test cost and quantity calculations."""

    @patch('src.services.composition_service.get_db_session')
    def test_calculate_assembly_component_costs(self, mock_session):
        """Test calculation of component costs."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock composition with FinishedUnit
        mock_unit = Mock()
        mock_unit.id = 1
        mock_unit.display_name = "Test Unit"
        mock_unit.unit_cost = Decimal('2.50')

        mock_composition = Mock()
        mock_composition.id = 1
        mock_composition.component_quantity = 4
        mock_composition.finished_unit_component = mock_unit
        mock_composition.finished_good_component = None

        with patch.object(CompositionService, 'get_assembly_components') as mock_get_components:
            mock_get_components.return_value = [mock_composition]

            # Execute
            result = CompositionService.calculate_assembly_component_costs(1)

            # Verify
            assert result['total_finished_unit_cost'] == 10.0  # 2.50 * 4
            assert result['total_assembly_cost'] == 10.0
            assert len(result['finished_unit_costs']) == 1

    @patch('src.services.composition_service.CompositionService.flatten_assembly_components')
    def test_calculate_required_inventory(self, mock_flatten):
        """Test calculation of required inventory."""
        # Setup
        mock_flatten.return_value = [
            {
                'component_type': 'finished_unit',
                'component_id': 1,
                'display_name': 'Test Unit',
                'total_quantity': 3,
                'inventory_count': 10
            },
            {
                'component_type': 'finished_unit',
                'component_id': 2,
                'display_name': 'Another Unit',
                'total_quantity': 2,
                'inventory_count': 3
            }
        ]

        # Execute
        result = CompositionService.calculate_required_inventory(1, 5)

        # Verify
        assert result['assembly_quantity'] == 5
        assert result['availability_status'] == 'insufficient'  # Second component short
        assert len(result['finished_unit_requirements']) == 2

        unit1_req = result['finished_unit_requirements'][0]
        assert unit1_req['required_quantity'] == 15  # 3 * 5
        assert unit1_req['shortage'] == 5  # 15 - 10

        unit2_req = result['finished_unit_requirements'][1]
        assert unit2_req['required_quantity'] == 10  # 2 * 5
        assert unit2_req['shortage'] == 7   # 10 - 3


class TestCompositionServiceQueryUtilities:
    """Test query utility methods."""

    @patch('src.services.composition_service.get_db_session')
    def test_search_compositions_by_component(self, mock_session):
        """Test searching compositions by component name."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_compositions = [Mock(), Mock()]
        mock_db.query.return_value.options.return_value.outerjoin.return_value.outerjoin.return_value.filter.return_value.all.return_value = mock_compositions

        # Execute
        result = CompositionService.search_compositions_by_component("chocolate")

        # Verify
        assert result == mock_compositions

    @patch('src.services.composition_service.get_db_session')
    def test_search_compositions_empty_query(self, mock_session):
        """Test search with empty query."""
        # Execute
        result = CompositionService.search_compositions_by_component("")

        # Verify
        assert result == []

    @patch('src.services.composition_service.get_db_session')
    def test_get_assembly_statistics(self, mock_session):
        """Test getting assembly statistics."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock direct components
        mock_unit_comp = Mock()
        mock_unit_comp.finished_unit_id = 1
        mock_unit_comp.finished_good_id = None

        mock_good_comp = Mock()
        mock_good_comp.finished_unit_id = None
        mock_good_comp.finished_good_id = 2

        direct_components = [mock_unit_comp, mock_good_comp]

        with patch.object(CompositionService, 'get_assembly_components') as mock_get_components, \
             patch.object(CompositionService, 'flatten_assembly_components') as mock_flatten, \
             patch.object(CompositionService, 'calculate_assembly_component_costs') as mock_costs:

            mock_get_components.return_value = direct_components
            mock_flatten.return_value = [
                {'component_type': 'finished_unit'},
                {'component_type': 'finished_unit'},
                {'component_type': 'finished_good'}
            ]
            mock_costs.return_value = {'total_assembly_cost': 25.0}

            # Mock hierarchy depth calculation
            mock_db.query.return_value.filter.return_value.all.return_value = []

            # Execute
            result = CompositionService.get_assembly_statistics(1)

            # Verify
            assert result['direct_components_count'] == 2
            assert result['direct_finished_units'] == 1
            assert result['direct_finished_goods'] == 1
            assert result['total_unique_components'] == 3
            assert result['total_cost'] == 25.0


class TestCompositionServiceEdgeCases:
    """Test edge cases and error conditions."""

    @patch('src.services.composition_service.get_db_session')
    def test_database_error_handling(self, mock_session):
        """Test database error handling."""
        # Setup
        mock_session.side_effect = Exception("Database connection failed")

        # Execute & Verify
        with pytest.raises(DatabaseError, match="Failed to retrieve composition"):
            CompositionService.get_composition_by_id(1)

    def test_component_validation_scenarios(self, component_validation_scenarios):
        """Test various component validation scenarios."""
        for scenario in component_validation_scenarios:
            component_type = scenario['component_type']
            should_succeed = scenario['should_succeed']

            if should_succeed:
                # Test should pass basic validation
                assert component_type in ["finished_unit", "finished_good"]
            else:
                # Test should fail validation
                if component_type not in ["finished_unit", "finished_good"]:
                    with pytest.raises(InvalidComponentTypeError):
                        CompositionService.create_composition(1, component_type, 1, 1)

    @patch('src.services.composition_service.session_scope')
    def test_duplicate_composition_error(self, mock_session):
        """Test creation of duplicate composition."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_assembly = Mock()
        mock_unit = Mock()
        mock_existing_composition = Mock()

        # Mock queries - assembly exists, component exists, composition already exists
        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_assembly)))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_unit)))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_existing_composition))))
        ]

        with patch.object(CompositionService, 'validate_component_exists', return_value=True):
            # Execute & Verify
            with pytest.raises(DuplicateCompositionError, match="already exists"):
                CompositionService.create_composition(1, "finished_unit", 1, 3)


class TestCompositionServiceIntegration:
    """Integration-style tests for complex workflows."""

    @patch('src.services.composition_service.session_scope')
    def test_complete_assembly_composition_workflow(self, mock_session):
        """Test complete workflow of assembly composition management."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock successful validations and database operations
        mock_assembly = Mock()
        mock_unit1 = Mock()
        mock_unit2 = Mock()

        mock_db.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_assembly)))),  # Assembly 1
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_unit1)))),      # Unit 1
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=None)))),           # No existing comp 1
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_assembly)))),  # Assembly 2
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=mock_unit2)))),      # Unit 2
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=None))))           # No existing comp 2
        ]

        with patch.object(CompositionService, 'validate_component_exists', return_value=True):
            # Execute - Create multiple compositions
            result1 = CompositionService.create_composition(1, "finished_unit", 1, 3)
            result2 = CompositionService.create_composition(1, "finished_unit", 2, 2)

            # Verify
            assert isinstance(result1, Composition)
            assert isinstance(result2, Composition)
            assert mock_db.add.call_count == 2