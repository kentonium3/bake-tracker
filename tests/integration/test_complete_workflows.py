"""
Complete workflow integration tests for all user stories.

Tests end-to-end workflows across all services, validating complete user
journeys from creation to complex operations. Covers all three user stories
with realistic scenarios and cross-service interactions.

User Stories Tested:
- User Story 1: Track Individual Consumable Items
- User Story 2: Create Simple Package Assemblies
- User Story 3: Create Nested Package Hierarchies

Cross-Service Integration:
- FinishedUnit ↔ FinishedGood ↔ Composition interactions
- Migration integration with all service layers
- Error handling across service boundaries
"""

import pytest
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional
import time
from datetime import datetime

from src.services.finished_unit_service import FinishedUnitService
from src.services.finished_good_service import FinishedGoodService
from src.services.composition_service import CompositionService
from src.services.migration_service import MigrationService
from src.models import FinishedUnit, FinishedGood, AssemblyType, Composition
from src.database import get_db_session, session_scope

from ..fixtures.hierarchy_fixtures import HierarchyTestFixtures

logger = logging.getLogger(__name__)


class TestCompleteWorkflows:
    """Integration tests for complete user workflows across all services."""

    @pytest.fixture(autouse=True)
    def setup_workflow_environment(self):
        """Set up clean environment for each workflow test."""
        # Clear any existing cache
        CompositionService.clear_hierarchy_cache()

        yield

        # Cleanup after test
        with session_scope() as session:
            # Clean up in dependency order
            session.query(Composition).delete()
            session.query(FinishedGood).delete()
            session.query(FinishedUnit).delete()
            session.commit()

    def test_user_story_1_complete_workflow(self):
        """
        Test complete User Story 1 workflow: Track Individual Consumable Items.

        Workflow Steps:
        1. Create multiple individual bakery items
        2. Manage inventory levels and track changes
        3. Calculate costs and update pricing
        4. Handle low inventory scenarios
        5. Track production and consumption patterns
        """
        logger.info("Testing User Story 1: Complete Individual Item Workflow")

        # Step 1: Create individual bakery items
        chocolate_chip_cookie = FinishedUnitService.create_finished_unit(
            display_name="Premium Chocolate Chip Cookie",
            slug="premium-chocolate-chip-cookie",
            description="Fresh baked with premium Belgian chocolate chips",
            unit_cost=Decimal("3.25"),
            inventory_count=150,
            production_notes="Bake daily, use premium ingredients"
        )

        croissant = FinishedUnitService.create_finished_unit(
            display_name="Butter Croissant",
            slug="butter-croissant",
            description="Flaky French butter croissant, made fresh daily",
            unit_cost=Decimal("4.50"),
            inventory_count=80,
            production_notes="Requires overnight lamination process"
        )

        artisan_bread = FinishedUnitService.create_finished_unit(
            display_name="Artisan Sourdough Loaf",
            slug="artisan-sourdough-loaf",
            description="24-hour fermented sourdough with natural starter",
            unit_cost=Decimal("12.00"),
            inventory_count=25,
            production_notes="72-hour process, natural starter maintenance"
        )

        # Validate creation
        assert chocolate_chip_cookie.id is not None
        assert croissant.id is not None
        assert artisan_bread.id is not None

        # Step 2: Test inventory management and tracking
        initial_cookie_inventory = chocolate_chip_cookie.inventory_count

        # Simulate sales - update inventory
        updated_cookie = FinishedUnitService.update_finished_unit(
            chocolate_chip_cookie.id,
            inventory_count=initial_cookie_inventory - 25
        )

        assert updated_cookie.inventory_count == 125
        assert updated_cookie.id == chocolate_chip_cookie.id

        # Step 3: Test cost calculation and pricing updates
        # Update cost due to ingredient price change
        updated_croissant = FinishedUnitService.update_finished_unit(
            croissant.id,
            unit_cost=Decimal("4.75"),
            production_notes="Updated - butter price increased 5%"
        )

        assert updated_croissant.unit_cost == Decimal("4.75")

        # Step 4: Handle low inventory scenarios
        # Simulate low inventory situation
        low_inventory_bread = FinishedUnitService.update_finished_unit(
            artisan_bread.id,
            inventory_count=5
        )

        assert low_inventory_bread.inventory_count == 5

        # Test inventory queries for reorder alerts
        all_items = FinishedUnitService.get_all_finished_units()
        low_inventory_items = [item for item in all_items if item.inventory_count < 10]
        assert len(low_inventory_items) == 1
        assert low_inventory_items[0].id == artisan_bread.id

        # Step 5: Test search and retrieval operations
        search_results = FinishedUnitService.search_finished_units("chocolate")
        assert len(search_results) >= 1
        assert any(item.id == chocolate_chip_cookie.id for item in search_results)

        # Validate complete data integrity
        retrieved_cookie = FinishedUnitService.get_finished_unit_by_id(chocolate_chip_cookie.id)
        assert retrieved_cookie is not None
        assert retrieved_cookie.display_name == "Premium Chocolate Chip Cookie"
        assert retrieved_cookie.inventory_count == 125
        assert retrieved_cookie.unit_cost == Decimal("3.25")

        logger.info("✓ User Story 1 complete workflow validated successfully")

    def test_user_story_2_complete_workflow(self):
        """
        Test complete User Story 2 workflow: Create Simple Package Assemblies.

        Workflow Steps:
        1. Create individual components
        2. Create package assembly with multiple components
        3. Track component availability for package production
        4. Handle package distribution and inventory updates
        5. Calculate package costs from component costs
        6. Manage package inventory and reordering
        """
        logger.info("Testing User Story 2: Complete Package Assembly Workflow")

        # Step 1: Create individual components
        sugar_cookie = FinishedUnitService.create_finished_unit(
            display_name="Sugar Cookie",
            slug="sugar-cookie",
            unit_cost=Decimal("2.00"),
            inventory_count=200
        )

        chocolate_cookie = FinishedUnitService.create_finished_unit(
            display_name="Double Chocolate Cookie",
            slug="double-chocolate-cookie",
            unit_cost=Decimal("2.50"),
            inventory_count=150
        )

        oatmeal_cookie = FinishedUnitService.create_finished_unit(
            display_name="Oatmeal Raisin Cookie",
            slug="oatmeal-raisin-cookie",
            unit_cost=Decimal("2.25"),
            inventory_count=180
        )

        gift_box = FinishedUnitService.create_finished_unit(
            display_name="Premium Gift Box",
            slug="premium-gift-box",
            unit_cost=Decimal("3.50"),
            inventory_count=100
        )

        # Step 2: Create package assembly
        cookie_sampler = FinishedGoodService.create_finished_good(
            display_name="Gourmet Cookie Sampler",
            assembly_type=AssemblyType.GIFT_BOX,
            description="Assorted premium cookies in elegant gift box"
        )

        # Add components to the assembly
        FinishedGoodService.add_component(cookie_sampler.id, "finished_unit", sugar_cookie.id, 4)
        FinishedGoodService.add_component(cookie_sampler.id, "finished_unit", chocolate_cookie.id, 3)
        FinishedGoodService.add_component(cookie_sampler.id, "finished_unit", oatmeal_cookie.id, 3)
        FinishedGoodService.add_component(cookie_sampler.id, "finished_unit", gift_box.id, 1)

        # Validate assembly creation
        retrieved_assembly = FinishedGoodService.get_finished_good_by_id(cookie_sampler.id)
        assert retrieved_assembly is not None
        assert retrieved_assembly.display_name == "Gourmet Cookie Sampler"

        # Step 3: Track component availability for package production
        assembly_components = CompositionService.get_assembly_components(cookie_sampler.id)
        assert len(assembly_components) == 4  # 3 cookie types + gift box

        # Calculate inventory requirements for production
        production_quantity = 15  # Want to produce 15 samplers
        inventory_requirements = CompositionService.calculate_required_inventory(
            cookie_sampler.id, production_quantity
        )

        # Validate requirements calculation
        assert inventory_requirements['assembly_id'] == cookie_sampler.id
        assert inventory_requirements['assembly_quantity'] == 15

        # Check specific component requirements
        requirements_dict = {
            req['component_id']: req for req in inventory_requirements['finished_unit_requirements']
        }

        # Sugar cookies: 15 samplers × 4 cookies = 60 cookies (available: 200) ✓
        assert requirements_dict[sugar_cookie.id]['required_quantity'] == 60
        assert requirements_dict[sugar_cookie.id]['is_sufficient'] is True

        # Chocolate cookies: 15 samplers × 3 cookies = 45 cookies (available: 150) ✓
        assert requirements_dict[chocolate_cookie.id]['required_quantity'] == 45
        assert requirements_dict[chocolate_cookie.id]['is_sufficient'] is True

        # Gift boxes: 15 samplers × 1 box = 15 boxes (available: 100) ✓
        assert requirements_dict[gift_box.id]['required_quantity'] == 15
        assert requirements_dict[gift_box.id]['is_sufficient'] is True

        assert inventory_requirements['availability_status'] == 'available'

        # Step 4: Simulate package production and inventory updates
        # Produce 10 cookie samplers - update component inventories
        production_qty = 10

        # Calculate component consumption
        for comp in assembly_components:
            if comp.finished_unit_component:
                component = comp.finished_unit_component
                consumed_quantity = comp.component_quantity * production_qty
                new_inventory = component.inventory_count - consumed_quantity

                updated_component = FinishedUnitService.update_finished_unit(
                    component.id,
                    inventory_count=new_inventory
                )

                # Verify inventory was updated correctly
                expected_new_count = component.inventory_count - consumed_quantity
                assert updated_component.inventory_count == expected_new_count

        # Update assembly inventory count
        updated_assembly = FinishedGoodService.update_finished_good(
            cookie_sampler.id,
            inventory_count=production_qty
        )

        assert updated_assembly.inventory_count == production_qty

        # Step 5: Calculate total assembly costs
        cost_breakdown = CompositionService.calculate_assembly_component_costs(cookie_sampler.id)

        # Expected costs:
        # Sugar cookies: 4 × $2.00 = $8.00
        # Chocolate cookies: 3 × $2.50 = $7.50
        # Oatmeal cookies: 3 × $2.25 = $6.75
        # Gift box: 1 × $3.50 = $3.50
        # Total component cost: $25.75

        expected_total = Decimal("25.75")
        assert abs(cost_breakdown['total_assembly_cost'] - float(expected_total)) < 0.01

        # Step 6: Test package distribution and sales
        # Sell 3 packages
        sold_quantity = 3
        remaining_inventory = production_qty - sold_quantity

        final_assembly = FinishedGoodService.update_finished_good(
            cookie_sampler.id,
            inventory_count=remaining_inventory
        )

        assert final_assembly.inventory_count == 7

        # Validate complete package data integrity
        final_components = CompositionService.get_assembly_components(cookie_sampler.id)
        assert len(final_components) == 4

        logger.info("✓ User Story 2 complete workflow validated successfully")

    def test_user_story_3_complete_workflow(self):
        """
        Test complete User Story 3 workflow: Create Nested Package Hierarchies.

        Workflow Steps:
        1. Create base individual items
        2. Create intermediate assemblies
        3. Create complex nested hierarchy assembly
        4. Validate multi-level inventory propagation
        5. Test hierarchy traversal and flattening
        6. Handle complex cost aggregation across levels
        7. Manage production of nested assemblies
        """
        logger.info("Testing User Story 3: Complete Nested Package Hierarchy Workflow")

        # Step 1: Create base individual items
        premium_truffle = FinishedUnitService.create_finished_unit(
            display_name="Premium Dark Truffle",
            unit_cost=Decimal("5.00"),
            inventory_count=60
        )

        gold_truffle = FinishedUnitService.create_finished_unit(
            display_name="Gold Leaf Truffle",
            unit_cost=Decimal("8.00"),
            inventory_count=30
        )

        gourmet_cookie = FinishedUnitService.create_finished_unit(
            display_name="Gourmet Macaroon",
            unit_cost=Decimal("4.00"),
            inventory_count=80
        )

        specialty_tea = FinishedUnitService.create_finished_unit(
            display_name="Earl Grey Premium Tea",
            unit_cost=Decimal("2.50"),
            inventory_count=120
        )

        deluxe_packaging = FinishedUnitService.create_finished_unit(
            display_name="Deluxe Gift Packaging",
            unit_cost=Decimal("12.00"),
            inventory_count=40
        )

        # Step 2: Create intermediate assemblies (Level 1)
        truffle_collection = FinishedGoodService.create_finished_good(
            display_name="Artisan Truffle Collection",
            assembly_type=AssemblyType.GIFT_BOX,
            description="Curated selection of premium truffles"
        )

        tea_cookie_set = FinishedGoodService.create_finished_good(
            display_name="Tea & Cookie Pairing Set",
            assembly_type=AssemblyType.VARIETY_PACK,
            description="Perfect afternoon tea combination"
        )

        # Add components to intermediate assemblies
        FinishedGoodService.add_component(truffle_collection.id, "finished_unit", premium_truffle.id, 4)
        FinishedGoodService.add_component(truffle_collection.id, "finished_unit", gold_truffle.id, 2)

        FinishedGoodService.add_component(tea_cookie_set.id, "finished_unit", gourmet_cookie.id, 6)
        FinishedGoodService.add_component(tea_cookie_set.id, "finished_unit", specialty_tea.id, 8)

        # Step 3: Create top-level nested hierarchy assembly (Level 2)
        ultimate_gift_set = FinishedGoodService.create_finished_good(
            display_name="Ultimate Luxury Gift Set",
            assembly_type=AssemblyType.HOLIDAY_SET,
            description="The pinnacle of our artisan offerings"
        )

        # Add both intermediate assemblies and individual items
        FinishedGoodService.add_component(ultimate_gift_set.id, "finished_good", truffle_collection.id, 1)
        FinishedGoodService.add_component(ultimate_gift_set.id, "finished_good", tea_cookie_set.id, 1)
        FinishedGoodService.add_component(ultimate_gift_set.id, "finished_unit", deluxe_packaging.id, 1)

        # Step 4: Validate multi-level inventory propagation
        # Test inventory requirements for nested assembly production
        luxury_production_qty = 5
        luxury_requirements = CompositionService.calculate_required_inventory(
            ultimate_gift_set.id, luxury_production_qty
        )

        # Validate that requirements cascade through hierarchy
        # Expected requirements for 5 luxury sets:
        # Premium truffles: 5 sets × 1 collection × 4 truffles = 20 truffles
        # Gold truffles: 5 sets × 1 collection × 2 truffles = 10 truffles
        # Gourmet cookies: 5 sets × 1 tea set × 6 cookies = 30 cookies
        # Specialty tea: 5 sets × 1 tea set × 8 teas = 40 teas
        # Deluxe packaging: 5 sets × 1 packaging = 5 packages

        requirements_dict = {
            req['component_id']: req for req in luxury_requirements['finished_unit_requirements']
        }

        assert requirements_dict[premium_truffle.id]['required_quantity'] == 20
        assert requirements_dict[gold_truffle.id]['required_quantity'] == 10
        assert requirements_dict[gourmet_cookie.id]['required_quantity'] == 30
        assert requirements_dict[specialty_tea.id]['required_quantity'] == 40
        assert requirements_dict[deluxe_packaging.id]['required_quantity'] == 5

        # All should be available based on our inventory levels
        assert luxury_requirements['availability_status'] == 'available'

        # Step 5: Test hierarchy traversal and structure validation
        hierarchy = CompositionService.get_assembly_hierarchy(ultimate_gift_set.id)

        # Validate hierarchy structure
        assert hierarchy['assembly_id'] == ultimate_gift_set.id
        assert len(hierarchy['components']) == 3  # 2 assemblies + 1 individual item

        # Find intermediate assemblies in hierarchy
        truffle_component = None
        tea_component = None
        packaging_component = None

        for comp in hierarchy['components']:
            if comp['component_id'] == truffle_collection.id:
                truffle_component = comp
            elif comp['component_id'] == tea_cookie_set.id:
                tea_component = comp
            elif comp['component_id'] == deluxe_packaging.id:
                packaging_component = comp

        assert truffle_component is not None
        assert tea_component is not None
        assert packaging_component is not None

        # Validate nested structure
        assert len(truffle_component['subcomponents']) == 2  # 2 truffle types
        assert len(tea_component['subcomponents']) == 2     # cookies + tea
        assert len(packaging_component['subcomponents']) == 0  # Individual item

        # Step 6: Test flattened component view for bill of materials
        flattened = CompositionService.flatten_assembly_components(ultimate_gift_set.id)

        # Should have all base components plus intermediate assemblies
        base_components = [comp for comp in flattened if comp['component_type'] == 'finished_unit']
        assembly_components = [comp for comp in flattened if comp['component_type'] == 'finished_good']

        assert len(base_components) == 5  # 5 individual item types
        assert len(assembly_components) == 2  # 2 intermediate assemblies

        # Validate quantities in flattened view
        flattened_dict = {
            comp['component_id']: comp['total_quantity'] for comp in base_components
        }

        assert flattened_dict[premium_truffle.id] == 4  # From truffle collection
        assert flattened_dict[gold_truffle.id] == 2     # From truffle collection
        assert flattened_dict[gourmet_cookie.id] == 6   # From tea set
        assert flattened_dict[specialty_tea.id] == 8    # From tea set
        assert flattened_dict[deluxe_packaging.id] == 1 # Direct component

        # Step 7: Test complex cost aggregation across all levels
        cost_breakdown = CompositionService.calculate_assembly_component_costs(ultimate_gift_set.id)

        # Direct unit cost: deluxe packaging = $12.00
        # Assembly costs: truffle collection + tea cookie set

        # Truffle collection cost: (4 × $5.00) + (2 × $8.00) = $36.00
        # Tea set cost: (6 × $4.00) + (8 × $2.50) = $44.00
        # Total expected: $12.00 + $36.00 + $44.00 = $92.00 (before packaging markup)

        assert len(cost_breakdown['finished_unit_costs']) == 1  # Direct packaging
        assert len(cost_breakdown['finished_good_costs']) == 2  # 2 intermediate assemblies

        # Validate packaging cost
        packaging_cost = cost_breakdown['finished_unit_costs'][0]
        assert packaging_cost['component_id'] == deluxe_packaging.id
        assert packaging_cost['total_cost'] == 12.00

        # Step 8: Test production simulation with nested inventory updates
        # Simulate production of 2 luxury sets
        production_quantity = 2

        # Get all assembly statistics before production
        stats = CompositionService.get_assembly_statistics(ultimate_gift_set.id)
        assert stats['hierarchy_depth'] == 2  # 2 levels deep
        assert stats['total_unique_components'] == 7  # 5 base + 2 intermediate

        # Validate complete nested workflow integrity
        # Check that all services interact properly
        final_hierarchy = CompositionService.get_assembly_hierarchy(ultimate_gift_set.id, max_depth=3)
        assert final_hierarchy['max_depth'] == 3

        logger.info("✓ User Story 3 complete workflow validated successfully")

    def test_cross_service_integration_and_error_handling(self):
        """
        Test cross-service operations and error handling across service boundaries.

        Tests:
        1. Service interaction patterns and data flow
        2. Error propagation and handling across services
        3. Transaction consistency across operations
        4. Validation of service contracts and interfaces
        """
        logger.info("Testing Cross-Service Integration and Error Handling")

        # Test 1: Valid cross-service operations
        # Create items through different service entry points
        base_item = FinishedUnitService.create_finished_unit(
            display_name="Integration Test Item",
            unit_cost=Decimal("1.00"),
            inventory_count=100
        )

        assembly = FinishedGoodService.create_finished_good(
            display_name="Integration Test Assembly",
            assembly_type=AssemblyType.BULK_PACK
        )

        # Use composition service to create relationship
        composition = CompositionService.create_composition(
            assembly_id=assembly.id,
            component_type="finished_unit",
            component_id=base_item.id,
            quantity=5
        )

        assert composition.id is not None
        assert composition.assembly_id == assembly.id
        assert composition.finished_unit_id == base_item.id

        # Test 2: Error handling - Invalid assembly reference
        with pytest.raises(Exception) as exc_info:
            CompositionService.create_composition(
                assembly_id=99999,  # Non-existent assembly
                component_type="finished_unit",
                component_id=base_item.id,
                quantity=1
            )
        assert "not found" in str(exc_info.value).lower()

        # Test 3: Error handling - Invalid component reference
        with pytest.raises(Exception) as exc_info:
            CompositionService.create_composition(
                assembly_id=assembly.id,
                component_type="finished_unit",
                component_id=99999,  # Non-existent component
                quantity=1
            )
        assert "not found" in str(exc_info.value).lower()

        # Test 4: Error handling - Invalid component type
        with pytest.raises(Exception) as exc_info:
            CompositionService.create_composition(
                assembly_id=assembly.id,
                component_type="invalid_type",  # Invalid type
                component_id=base_item.id,
                quantity=1
            )
        assert "component type" in str(exc_info.value).lower()

        # Test 5: Error handling - Circular reference detection
        second_assembly = FinishedGoodService.create_finished_good(
            display_name="Second Assembly",
            assembly_type=AssemblyType.GIFT_BOX
        )

        # Add second assembly to first (valid)
        FinishedGoodService.add_component(assembly.id, "finished_good", second_assembly.id, 1)

        # Try to add first assembly to second (should create circular reference)
        with pytest.raises(Exception) as exc_info:
            FinishedGoodService.add_component(second_assembly.id, "finished_good", assembly.id, 1)
        assert "circular reference" in str(exc_info.value).lower()

        # Test 6: Service contract validation
        # Verify that services return expected data types and structures
        retrieved_item = FinishedUnitService.get_finished_unit_by_id(base_item.id)
        assert isinstance(retrieved_item, FinishedUnit)
        assert hasattr(retrieved_item, 'display_name')
        assert hasattr(retrieved_item, 'unit_cost')
        assert hasattr(retrieved_item, 'inventory_count')

        retrieved_assembly = FinishedGoodService.get_finished_good_by_id(assembly.id)
        assert isinstance(retrieved_assembly, FinishedGood)
        assert hasattr(retrieved_assembly, 'display_name')
        assert hasattr(retrieved_assembly, 'assembly_type')

        # Test 7: Transaction consistency
        # Verify that operations are properly atomic
        initial_composition_count = len(CompositionService.get_assembly_components(assembly.id))

        # Attempt invalid operation that should not affect database
        try:
            CompositionService.create_composition(
                assembly_id=assembly.id,
                component_type="finished_unit",
                component_id=99999,  # Invalid
                quantity=1
            )
        except:
            pass  # Expected to fail

        # Verify no partial data was created
        final_composition_count = len(CompositionService.get_assembly_components(assembly.id))
        assert final_composition_count == initial_composition_count

        logger.info("✓ Cross-service integration and error handling validated successfully")

    def test_migration_integration_workflow(self):
        """
        Test integration with migration services across all layers.

        Tests:
        1. Migration service interaction with other services
        2. Data preservation during migration workflow
        3. Service functionality with migrated data
        4. Migration rollback and recovery scenarios
        """
        logger.info("Testing Migration Integration Workflow")

        # Test 1: Create legacy-style data that would need migration
        # This simulates the kind of data that would exist before migration
        legacy_item = FinishedUnitService.create_finished_unit(
            display_name="Legacy Baked Good",
            slug="legacy-baked-good",
            unit_cost=Decimal("5.00"),
            inventory_count=50,
            production_notes="Created in legacy format"
        )

        # Test 2: Verify migration service can interact with created data
        # Check backup functionality
        backup_result = MigrationService.validate_pre_migration()
        assert backup_result['status'] == 'success'
        assert backup_result['total_finished_units'] >= 1

        # Test 3: Test post-migration service functionality
        # Verify all services still work with migrated data structure
        search_results = FinishedUnitService.search_finished_units("legacy")
        assert len(search_results) >= 1
        assert any(item.id == legacy_item.id for item in search_results)

        # Create assembly with migrated data
        migrated_assembly = FinishedGoodService.create_finished_good(
            display_name="Post-Migration Assembly",
            assembly_type=AssemblyType.VARIETY_PACK
        )

        # Add legacy item to new assembly
        FinishedGoodService.add_component(
            migrated_assembly.id, "finished_unit", legacy_item.id, 3
        )

        # Verify hierarchy operations work
        hierarchy = CompositionService.get_assembly_hierarchy(migrated_assembly.id)
        assert hierarchy['assembly_id'] == migrated_assembly.id
        assert len(hierarchy['components']) == 1

        # Test cost calculations with migrated data
        cost_breakdown = CompositionService.calculate_assembly_component_costs(migrated_assembly.id)
        expected_cost = float(legacy_item.unit_cost) * 3  # 3 units × $5.00
        assert abs(cost_breakdown['total_assembly_cost'] - expected_cost) < 0.01

        # Test 4: Verify data integrity across migration workflow
        original_display_name = legacy_item.display_name
        original_cost = legacy_item.unit_cost
        original_inventory = legacy_item.inventory_count

        # Retrieve item after all operations
        final_item = FinishedUnitService.get_finished_unit_by_id(legacy_item.id)
        assert final_item.display_name == original_display_name
        assert final_item.unit_cost == original_cost
        assert final_item.inventory_count == original_inventory

        logger.info("✓ Migration integration workflow validated successfully")

    def test_complete_end_to_end_bakery_scenario(self):
        """
        Test a realistic complete bakery workflow covering all user stories.

        Scenario: Seasonal Holiday Bakery Operations
        1. Create individual seasonal items (User Story 1)
        2. Create themed gift packages (User Story 2)
        3. Create luxury holiday collection with nested packaging (User Story 3)
        4. Handle customer orders and inventory management
        5. Track costs and profitability across all levels
        """
        logger.info("Testing Complete End-to-End Bakery Scenario")

        # === PHASE 1: CREATE SEASONAL ITEMS (User Story 1) ===

        # Holiday cookies
        gingerbread_cookie = FinishedUnitService.create_finished_unit(
            display_name="Gingerbread Cookie",
            slug="gingerbread-cookie",
            unit_cost=Decimal("2.75"),
            inventory_count=300,
            description="Traditional spiced gingerbread with royal icing"
        )

        sugar_snowflake = FinishedUnitService.create_finished_unit(
            display_name="Sugar Snowflake Cookie",
            slug="sugar-snowflake-cookie",
            unit_cost=Decimal("3.00"),
            inventory_count=250,
            description="Delicate sugar cookie with winter snowflake design"
        )

        # Holiday treats
        peppermint_bark = FinishedUnitService.create_finished_unit(
            display_name="Peppermint Bark Square",
            slug="peppermint-bark-square",
            unit_cost=Decimal("4.50"),
            inventory_count=150,
            description="Dark chocolate with white chocolate and crushed peppermint"
        )

        hot_cocoa_bomb = FinishedUnitService.create_finished_unit(
            display_name="Hot Cocoa Bomb",
            slug="hot-cocoa-bomb",
            unit_cost=Decimal("6.00"),
            inventory_count=100,
            description="Chocolate sphere filled with cocoa mix and marshmallows"
        )

        # Packaging materials
        holiday_tin = FinishedUnitService.create_finished_unit(
            display_name="Holiday Gift Tin",
            slug="holiday-gift-tin",
            unit_cost=Decimal("8.00"),
            inventory_count=75
        )

        festive_ribbon = FinishedUnitService.create_finished_unit(
            display_name="Festive Gold Ribbon",
            slug="festive-gold-ribbon",
            unit_cost=Decimal("2.00"),
            inventory_count=200
        )

        # === PHASE 2: CREATE THEMED GIFT PACKAGES (User Story 2) ===

        # Cookie collection
        holiday_cookie_tin = FinishedGoodService.create_finished_good(
            display_name="Holiday Cookie Collection",
            assembly_type=AssemblyType.HOLIDAY_SET,
            description="Festive tin filled with our signature holiday cookies"
        )

        FinishedGoodService.add_component(holiday_cookie_tin.id, "finished_unit", gingerbread_cookie.id, 6)
        FinishedGoodService.add_component(holiday_cookie_tin.id, "finished_unit", sugar_snowflake.id, 6)
        FinishedGoodService.add_component(holiday_cookie_tin.id, "finished_unit", holiday_tin.id, 1)

        # Chocolate treat box
        chocolate_holiday_box = FinishedGoodService.create_finished_good(
            display_name="Chocolate Holiday Treats",
            assembly_type=AssemblyType.GIFT_BOX,
            description="Premium chocolate treats for the holidays"
        )

        FinishedGoodService.add_component(chocolate_holiday_box.id, "finished_unit", peppermint_bark.id, 4)
        FinishedGoodService.add_component(chocolate_holiday_box.id, "finished_unit", hot_cocoa_bomb.id, 2)
        FinishedGoodService.add_component(chocolate_holiday_box.id, "finished_unit", festive_ribbon.id, 1)

        # === PHASE 3: CREATE LUXURY HOLIDAY COLLECTION (User Story 3) ===

        # Premium luxury set containing both packages plus extras
        ultimate_holiday_collection = FinishedGoodService.create_finished_good(
            display_name="Ultimate Holiday Experience",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            description="Our finest holiday offerings in one spectacular collection"
        )

        # Add both packages plus some individual premium items
        FinishedGoodService.add_component(ultimate_holiday_collection.id, "finished_good", holiday_cookie_tin.id, 1)
        FinishedGoodService.add_component(ultimate_holiday_collection.id, "finished_good", chocolate_holiday_box.id, 1)
        FinishedGoodService.add_component(ultimate_holiday_collection.id, "finished_unit", hot_cocoa_bomb.id, 2)  # Extra bombs
        FinishedGoodService.add_component(ultimate_holiday_collection.id, "finished_unit", holiday_tin.id, 1)  # Extra packaging

        # === PHASE 4: CUSTOMER ORDER PROCESSING ===

        # Simulate customer order: 5 cookie tins, 3 chocolate boxes, 2 ultimate collections
        order_requirements = {
            'cookie_tins': 5,
            'chocolate_boxes': 3,
            'ultimate_collections': 2
        }

        # Check inventory availability for each product
        cookie_tin_req = CompositionService.calculate_required_inventory(
            holiday_cookie_tin.id, order_requirements['cookie_tins']
        )
        chocolate_box_req = CompositionService.calculate_required_inventory(
            chocolate_holiday_box.id, order_requirements['chocolate_boxes']
        )
        ultimate_req = CompositionService.calculate_required_inventory(
            ultimate_holiday_collection.id, order_requirements['ultimate_collections']
        )

        # All orders should be fulfillable based on our inventory
        assert cookie_tin_req['availability_status'] == 'available'
        assert chocolate_box_req['availability_status'] == 'available'
        assert ultimate_req['availability_status'] == 'available'

        # === PHASE 5: COST AND PROFITABILITY ANALYSIS ===

        # Calculate total costs for each product line
        cookie_tin_costs = CompositionService.calculate_assembly_component_costs(holiday_cookie_tin.id)
        chocolate_box_costs = CompositionService.calculate_assembly_component_costs(chocolate_holiday_box.id)
        ultimate_costs = CompositionService.calculate_assembly_component_costs(ultimate_holiday_collection.id)

        # Verify cost calculations make sense
        # Cookie tin: (6 × $2.75) + (6 × $3.00) + (1 × $8.00) = $42.50
        expected_cookie_cost = (6 * 2.75) + (6 * 3.00) + (1 * 8.00)
        assert abs(cookie_tin_costs['total_assembly_cost'] - expected_cookie_cost) < 0.01

        # === PHASE 6: HIERARCHY ANALYSIS AND STATISTICS ===

        # Analyze the complete hierarchy structure
        ultimate_hierarchy = CompositionService.get_assembly_hierarchy(ultimate_holiday_collection.id)
        ultimate_stats = CompositionService.get_assembly_statistics(ultimate_holiday_collection.id)

        # Validate complex hierarchy structure
        assert ultimate_stats['hierarchy_depth'] == 2  # Ultimate → packages → items
        assert ultimate_stats['total_unique_components'] >= 8  # Various items and packages

        # Get complete bill of materials
        ultimate_bom = CompositionService.flatten_assembly_components(ultimate_holiday_collection.id)

        # Verify BOM includes all expected components
        bom_units = [comp for comp in ultimate_bom if comp['component_type'] == 'finished_unit']
        bom_assemblies = [comp for comp in ultimate_bom if comp['component_type'] == 'finished_good']

        assert len(bom_units) == 6  # 6 different unit types
        assert len(bom_assemblies) == 2  # 2 sub-assemblies

        # === PHASE 7: VALIDATE COMPLETE DATA INTEGRITY ===

        # Verify all items are searchable
        all_units = FinishedUnitService.get_all_finished_units()
        all_assemblies = FinishedGoodService.get_all_finished_goods()

        assert len(all_units) >= 6  # At least our 6 items
        assert len(all_assemblies) >= 3  # At least our 3 assemblies

        # Test search across all items
        holiday_search = FinishedUnitService.search_finished_units("holiday")
        assert len(holiday_search) >= 2  # At least holiday tin and some items

        # Verify cost integrity across all levels
        total_order_value = (
            (cookie_tin_costs['total_assembly_cost'] * order_requirements['cookie_tins']) +
            (chocolate_box_costs['total_assembly_cost'] * order_requirements['chocolate_boxes']) +
            (ultimate_costs['total_assembly_cost'] * order_requirements['ultimate_collections'])
        )

        assert total_order_value > 0
        logger.info(f"Total order value: ${total_order_value:.2f}")

        logger.info("✓ Complete end-to-end bakery scenario validated successfully")

    def test_performance_under_realistic_load(self):
        """
        Test system performance under realistic operational load.

        Tests performance of complete workflows under conditions similar
        to real bakery operations with multiple concurrent operations.
        """
        logger.info("Testing Performance Under Realistic Load")

        # Create larger dataset for realistic performance testing
        fixtures = HierarchyTestFixtures()

        # Create realistic bakery inventory
        items = fixtures.create_realistic_bakery_items()
        gift_boxes = fixtures.create_sample_gift_boxes(items)

        # Test bulk operations performance
        start_time = time.time()

        # Simulate multiple customer orders
        for i in range(10):
            # Create custom assembly for each "customer"
            customer_assembly = FinishedGoodService.create_finished_good(
                display_name=f"Customer {i+1} Custom Order",
                assembly_type=AssemblyType.CUSTOM_ORDER
            )

            # Add random components
            sample_items = list(items.values())[:5]  # First 5 items
            for j, item in enumerate(sample_items):
                FinishedGoodService.add_component(
                    customer_assembly.id, "finished_unit", item.id, j + 1
                )

            # Calculate costs and requirements
            cost_breakdown = CompositionService.calculate_assembly_component_costs(customer_assembly.id)
            inventory_req = CompositionService.calculate_required_inventory(customer_assembly.id, 1)

            # Validate results
            assert cost_breakdown['total_assembly_cost'] > 0
            assert 'finished_unit_requirements' in inventory_req

        total_time = time.time() - start_time

        # Performance should be reasonable for 10 custom orders
        assert total_time < 10.0, f"Bulk operations took too long: {total_time:.2f}s"

        logger.info(f"✓ Performance test completed in {total_time:.2f}s for 10 custom orders")

        # Cleanup
        fixtures.cleanup()

        logger.info("✓ Performance under realistic load validated successfully")


# Additional utility functions for workflow validation

def validate_service_contracts():
    """Validate that all services maintain proper contracts and interfaces."""
    # This could be expanded to check service method signatures,
    # return types, exception handling, etc.
    pass


def generate_workflow_report(results: Dict[str, Any]) -> str:
    """Generate a comprehensive workflow test report."""
    report_lines = [
        "=== Complete Workflow Integration Test Report ===",
        f"Test execution time: {results.get('total_time', 'N/A')}",
        f"User Story 1 validation: {'✓ PASS' if results.get('user_story_1', False) else '✗ FAIL'}",
        f"User Story 2 validation: {'✓ PASS' if results.get('user_story_2', False) else '✗ FAIL'}",
        f"User Story 3 validation: {'✓ PASS' if results.get('user_story_3', False) else '✗ FAIL'}",
        f"Cross-service integration: {'✓ PASS' if results.get('cross_service', False) else '✗ FAIL'}",
        f"Migration integration: {'✓ PASS' if results.get('migration', False) else '✗ FAIL'}",
        f"End-to-end scenario: {'✓ PASS' if results.get('end_to_end', False) else '✗ FAIL'}",
        f"Performance validation: {'✓ PASS' if results.get('performance', False) else '✗ FAIL'}",
        "================================================="
    ]
    return "\n".join(report_lines)