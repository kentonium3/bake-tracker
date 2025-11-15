"""
Integration tests for complex hierarchy operations.

Tests User Story 3: Create Nested Package Hierarchies with realistic
multi-level assembly scenarios, circular reference prevention, and
performance validation.

Test Coverage:
- Complex nested assembly creation (FinishedGoods containing other FinishedGoods)
- Hierarchy traversal with realistic multi-level structures
- Circular reference prevention with various invalid scenarios
- Cost calculation aggregation across multiple hierarchy levels
- Inventory propagation through nested assemblies
- Cache performance and invalidation
"""

import pytest
import logging
from decimal import Decimal
from typing import List, Dict, Any
import time

from src.services.finished_good_service import FinishedGoodService
from src.services.composition_service import CompositionService
from src.services.finished_unit_service import FinishedUnitService
from src.models import FinishedGood, FinishedUnit, AssemblyType
from src.database import get_db_session, session_scope

from ..fixtures.hierarchy_fixtures import HierarchyTestFixtures

logger = logging.getLogger(__name__)


class TestComplexHierarchyOperations:
    """Integration tests for complex assembly hierarchy operations."""

    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Set up test data for each test."""
        self.fixtures = HierarchyTestFixtures()

        # Clear cache before each test
        CompositionService.clear_hierarchy_cache()

        yield

        # Cleanup after test
        with session_scope() as session:
            # Clean up test data in dependency order
            session.query(Composition).delete()
            session.query(FinishedGood).delete()
            session.query(FinishedUnit).delete()
            session.commit()

    def test_create_deluxe_gift_set_hierarchy(self):
        """
        Test creating a complex deluxe gift set with nested assemblies.

        User Story 3 Scenario:
        - Deluxe Holiday Set containing:
          - Holiday Cookie Assortment (assembly containing individual cookies)
          - Gourmet Truffle Collection (assembly containing individual truffles)
          - Individual premium chocolate bar
          - Custom gift box and ribbon
        """
        # Create individual FinishedUnits (base components)
        chocolate_chip_cookie = self.fixtures.create_finished_unit(
            "Chocolate Chip Cookie", Decimal("2.50"), inventory_count=100
        )
        sugar_cookie = self.fixtures.create_finished_unit(
            "Sugar Cookie", Decimal("2.00"), inventory_count=100
        )
        snickerdoodle = self.fixtures.create_finished_unit(
            "Snickerdoodle", Decimal("2.25"), inventory_count=100
        )

        dark_truffle = self.fixtures.create_finished_unit(
            "Dark Chocolate Truffle", Decimal("3.00"), inventory_count=50
        )
        milk_truffle = self.fixtures.create_finished_unit(
            "Milk Chocolate Truffle", Decimal("2.75"), inventory_count=50
        )
        white_truffle = self.fixtures.create_finished_unit(
            "White Chocolate Truffle", Decimal("2.90"), inventory_count=50
        )

        premium_bar = self.fixtures.create_finished_unit(
            "Premium Chocolate Bar", Decimal("8.00"), inventory_count=25
        )
        gift_box = self.fixtures.create_finished_unit(
            "Deluxe Gift Box", Decimal("5.00"), inventory_count=30
        )
        ribbon = self.fixtures.create_finished_unit(
            "Satin Ribbon", Decimal("1.50"), inventory_count=100
        )

        # Create intermediate assemblies
        cookie_assortment = FinishedGoodService.create_finished_good(
            "Holiday Cookie Assortment",
            AssemblyType.VARIETY_PACK,
            description="Assorted holiday cookies"
        )

        truffle_collection = FinishedGoodService.create_finished_good(
            "Gourmet Truffle Collection",
            AssemblyType.GIFT_BOX,
            description="Premium truffle selection"
        )

        # Add components to intermediate assemblies
        FinishedGoodService.add_component(cookie_assortment.id, "finished_unit", chocolate_chip_cookie.id, 4)
        FinishedGoodService.add_component(cookie_assortment.id, "finished_unit", sugar_cookie.id, 3)
        FinishedGoodService.add_component(cookie_assortment.id, "finished_unit", snickerdoodle.id, 3)

        FinishedGoodService.add_component(truffle_collection.id, "finished_unit", dark_truffle.id, 2)
        FinishedGoodService.add_component(truffle_collection.id, "finished_unit", milk_truffle.id, 2)
        FinishedGoodService.add_component(truffle_collection.id, "finished_unit", white_truffle.id, 2)

        # Create top-level deluxe gift set
        deluxe_set = FinishedGoodService.create_finished_good(
            "Deluxe Holiday Gift Set",
            AssemblyType.HOLIDAY_SET,
            description="Premium holiday gift collection"
        )

        # Add components to deluxe set (mix of assemblies and individual items)
        FinishedGoodService.add_component(deluxe_set.id, "finished_good", cookie_assortment.id, 1)
        FinishedGoodService.add_component(deluxe_set.id, "finished_good", truffle_collection.id, 1)
        FinishedGoodService.add_component(deluxe_set.id, "finished_unit", premium_bar.id, 1)
        FinishedGoodService.add_component(deluxe_set.id, "finished_unit", gift_box.id, 1)
        FinishedGoodService.add_component(deluxe_set.id, "finished_unit", ribbon.id, 2)

        # Test hierarchy traversal
        hierarchy = CompositionService.get_assembly_hierarchy(deluxe_set.id)

        # Verify structure
        assert hierarchy['assembly_id'] == deluxe_set.id
        assert hierarchy['assembly_name'] == "Deluxe Holiday Gift Set"
        assert len(hierarchy['components']) == 5

        # Find the cookie assortment component
        cookie_component = None
        truffle_component = None
        for comp in hierarchy['components']:
            if comp['component_id'] == cookie_assortment.id:
                cookie_component = comp
            elif comp['component_id'] == truffle_collection.id:
                truffle_component = comp

        assert cookie_component is not None
        assert truffle_component is not None

        # Verify nested structure
        assert len(cookie_component['subcomponents']) == 3  # 3 cookie types
        assert len(truffle_component['subcomponents']) == 3  # 3 truffle types

        # Test flattened component view
        flattened = CompositionService.flatten_assembly_components(deluxe_set.id)

        # Should have all individual components
        expected_components = {
            f"finished_unit_{chocolate_chip_cookie.id}": 4,
            f"finished_unit_{sugar_cookie.id}": 3,
            f"finished_unit_{snickerdoodle.id}": 3,
            f"finished_unit_{dark_truffle.id}": 2,
            f"finished_unit_{milk_truffle.id}": 2,
            f"finished_unit_{white_truffle.id}": 2,
            f"finished_unit_{premium_bar.id}": 1,
            f"finished_unit_{gift_box.id}": 1,
            f"finished_unit_{ribbon.id}": 2,
            f"finished_good_{cookie_assortment.id}": 1,
            f"finished_good_{truffle_collection.id}": 1
        }

        flattened_dict = {
            f"{comp['component_type']}_{comp['component_id']}": comp['total_quantity']
            for comp in flattened
        }

        for key, expected_qty in expected_components.items():
            assert key in flattened_dict, f"Missing component: {key}"
            assert flattened_dict[key] == expected_qty, f"Wrong quantity for {key}: {flattened_dict[key]} != {expected_qty}"

        logger.info("Successfully created and validated complex deluxe gift set hierarchy")

    def test_circular_reference_prevention_scenarios(self):
        """
        Test comprehensive circular reference prevention in various scenarios.

        Scenarios tested:
        - Direct circular reference (A contains B, B contains A)
        - Indirect circular reference (A contains B, B contains C, C contains A)
        - Self-reference (A contains A)
        - Complex multi-level circular references
        """
        # Create assemblies for testing
        assembly_a = FinishedGoodService.create_finished_good("Assembly A", AssemblyType.GIFT_BOX)
        assembly_b = FinishedGoodService.create_finished_good("Assembly B", AssemblyType.VARIETY_PACK)
        assembly_c = FinishedGoodService.create_finished_good("Assembly C", AssemblyType.CUSTOM_ORDER)
        assembly_d = FinishedGoodService.create_finished_good("Assembly D", AssemblyType.BULK_PACK)

        # Test 1: Direct circular reference
        # A contains B (valid)
        FinishedGoodService.add_component(assembly_a.id, "finished_good", assembly_b.id, 1)

        # B contains A (should fail - circular reference)
        with pytest.raises(Exception) as exc_info:
            FinishedGoodService.add_component(assembly_b.id, "finished_good", assembly_a.id, 1)
        assert "circular reference" in str(exc_info.value).lower()

        # Test 2: Self-reference
        # A contains A (should fail)
        with pytest.raises(Exception) as exc_info:
            FinishedGoodService.add_component(assembly_a.id, "finished_good", assembly_a.id, 1)
        assert "circular reference" in str(exc_info.value).lower()

        # Test 3: Indirect circular reference (3-level)
        # Current: A → B
        # Add: B → C (valid)
        FinishedGoodService.add_component(assembly_b.id, "finished_good", assembly_c.id, 1)

        # Add: C → A (should fail - creates cycle A → B → C → A)
        with pytest.raises(Exception) as exc_info:
            FinishedGoodService.add_component(assembly_c.id, "finished_good", assembly_a.id, 1)
        assert "circular reference" in str(exc_info.value).lower()

        # Test 4: Valid multi-level hierarchy
        # C → D should be valid (no cycle)
        FinishedGoodService.add_component(assembly_c.id, "finished_good", assembly_d.id, 1)

        # Verify hierarchy depth
        hierarchy = CompositionService.get_assembly_hierarchy(assembly_a.id)
        assert hierarchy['components'][0]['subcomponents'][0]['subcomponents'][0]['component_id'] == assembly_d.id

        logger.info("Successfully validated comprehensive circular reference prevention")

    def test_cost_aggregation_multi_level(self):
        """
        Test cost calculation aggregation across multiple hierarchy levels.

        Validates that costs are correctly calculated and propagated through
        complex nested assembly structures.
        """
        # Create base items with known costs
        base_item_1 = self.fixtures.create_finished_unit("Base Item 1", Decimal("10.00"))
        base_item_2 = self.fixtures.create_finished_unit("Base Item 2", Decimal("15.00"))
        base_item_3 = self.fixtures.create_finished_unit("Base Item 3", Decimal("20.00"))

        # Create mid-level assembly
        mid_assembly = FinishedGoodService.create_finished_good("Mid Assembly", AssemblyType.GIFT_BOX)
        FinishedGoodService.add_component(mid_assembly.id, "finished_unit", base_item_1.id, 2)  # 2 × $10 = $20
        FinishedGoodService.add_component(mid_assembly.id, "finished_unit", base_item_2.id, 1)  # 1 × $15 = $15
        # Mid assembly total = $35 + packaging markup

        # Create top-level assembly
        top_assembly = FinishedGoodService.create_finished_good("Top Assembly", AssemblyType.HOLIDAY_SET)
        FinishedGoodService.add_component(top_assembly.id, "finished_good", mid_assembly.id, 1)
        FinishedGoodService.add_component(top_assembly.id, "finished_unit", base_item_3.id, 1)  # 1 × $20 = $20

        # Calculate costs
        cost_breakdown = CompositionService.calculate_assembly_component_costs(top_assembly.id)

        # Verify cost structure
        assert len(cost_breakdown['finished_unit_costs']) == 1  # Only base_item_3 directly
        assert len(cost_breakdown['finished_good_costs']) == 1  # Mid assembly

        # Verify specific costs
        unit_cost = cost_breakdown['finished_unit_costs'][0]
        assert unit_cost['component_id'] == base_item_3.id
        assert unit_cost['total_cost'] == 20.00

        good_cost = cost_breakdown['finished_good_costs'][0]
        assert good_cost['component_id'] == mid_assembly.id

        # Test flattened cost view
        flattened = CompositionService.flatten_assembly_components(top_assembly.id)

        # Find costs in flattened view
        total_base_cost = 0
        for comp in flattened:
            if comp['component_type'] == 'finished_unit':
                total_base_cost += comp['total_cost']

        # Should include: 2×$10 + 1×$15 + 1×$20 = $65 from base units
        assert total_base_cost == 65.00

        logger.info("Successfully validated multi-level cost aggregation")

    def test_inventory_propagation_nested_assemblies(self):
        """
        Test inventory availability calculation through nested assemblies.

        Validates that inventory requirements are correctly calculated
        considering all levels of the hierarchy.
        """
        # Create items with specific inventory levels
        item_a = self.fixtures.create_finished_unit("Item A", Decimal("5.00"), inventory_count=100)
        item_b = self.fixtures.create_finished_unit("Item B", Decimal("3.00"), inventory_count=50)
        item_c = self.fixtures.create_finished_unit("Item C", Decimal("7.00"), inventory_count=20)
        item_d = self.fixtures.create_finished_unit("Item D", Decimal("2.00"), inventory_count=10)

        # Create nested assembly structure
        sub_assembly = FinishedGoodService.create_finished_good("Sub Assembly", AssemblyType.VARIETY_PACK)
        FinishedGoodService.add_component(sub_assembly.id, "finished_unit", item_c.id, 2)  # Requires 2 × Item C
        FinishedGoodService.add_component(sub_assembly.id, "finished_unit", item_d.id, 5)  # Requires 5 × Item D

        main_assembly = FinishedGoodService.create_finished_good("Main Assembly", AssemblyType.GIFT_BOX)
        FinishedGoodService.add_component(main_assembly.id, "finished_unit", item_a.id, 3)    # Requires 3 × Item A
        FinishedGoodService.add_component(main_assembly.id, "finished_unit", item_b.id, 2)    # Requires 2 × Item B
        FinishedGoodService.add_component(main_assembly.id, "finished_good", sub_assembly.id, 1)  # Requires 1 × Sub Assembly

        # Test inventory requirements for different production quantities

        # Test 1: Small quantity (5 assemblies) - should be available
        requirements_5 = CompositionService.calculate_required_inventory(main_assembly.id, 5)

        expected_requirements_5 = {
            item_a.id: {'required': 15, 'available': 100, 'sufficient': True},   # 5 × 3 = 15
            item_b.id: {'required': 10, 'available': 50, 'sufficient': True},    # 5 × 2 = 10
            item_c.id: {'required': 10, 'available': 20, 'sufficient': True},    # 5 × 1 × 2 = 10
            item_d.id: {'required': 25, 'available': 10, 'sufficient': False},   # 5 × 1 × 5 = 25 > 10 available
        }

        assert requirements_5['availability_status'] == 'insufficient'  # Due to Item D shortage

        # Verify individual requirements
        for req in requirements_5['finished_unit_requirements']:
            item_id = req['component_id']
            if item_id in expected_requirements_5:
                expected = expected_requirements_5[item_id]
                assert req['required_quantity'] == expected['required']
                assert req['available_quantity'] == expected['available']
                assert req['is_sufficient'] == expected['sufficient']

        # Test 2: Smaller quantity (2 assemblies) - should be available
        requirements_2 = CompositionService.calculate_required_inventory(main_assembly.id, 2)

        # Item D: 2 × 1 × 5 = 10 (exactly available)
        assert requirements_2['availability_status'] == 'available'

        logger.info("Successfully validated inventory propagation through nested assemblies")

    def test_hierarchy_depth_limiting(self):
        """
        Test that hierarchy operations respect the 5-level depth limit.

        Creates a deep hierarchy and validates depth limiting behavior.
        """
        assemblies = []

        # Create 6 assemblies to test depth limiting
        for i in range(6):
            assembly = FinishedGoodService.create_finished_good(
                f"Assembly Level {i}",
                AssemblyType.CUSTOM_ORDER
            )
            assemblies.append(assembly)

        # Create base item
        base_item = self.fixtures.create_finished_unit("Base Item", Decimal("1.00"))

        # Chain assemblies: 0 → 1 → 2 → 3 → 4 → 5 → base_item
        for i in range(5):
            FinishedGoodService.add_component(assemblies[i].id, "finished_good", assemblies[i + 1].id, 1)

        # Add base item to deepest assembly
        FinishedGoodService.add_component(assemblies[5].id, "finished_unit", base_item.id, 1)

        # Test hierarchy traversal with default max depth (5)
        hierarchy = CompositionService.get_assembly_hierarchy(assemblies[0].id)

        # Navigate to maximum depth
        current_level = hierarchy['components'][0]  # Level 1
        depth = 1

        while 'subcomponents' in current_level and current_level['subcomponents']:
            if isinstance(current_level['subcomponents'], dict) and 'max_depth_reached' in current_level['subcomponents']:
                break
            if isinstance(current_level['subcomponents'], list) and len(current_level['subcomponents']) > 0:
                current_level = current_level['subcomponents'][0]
                depth += 1
            else:
                break

        # Should stop before reaching the deepest level due to depth limit
        assert depth <= 5, f"Hierarchy depth exceeded limit: {depth}"

        # Test with custom max depth
        shallow_hierarchy = CompositionService.get_assembly_hierarchy(assemblies[0].id, max_depth=3)

        # Verify it stops at level 3
        level_3 = shallow_hierarchy['components'][0]['subcomponents'][0]['subcomponents'][0]
        assert 'max_depth_reached' in level_3 or len(level_3.get('subcomponents', [])) == 0

        logger.info("Successfully validated hierarchy depth limiting")

    def test_performance_targets_complex_hierarchies(self):
        """
        Test that hierarchy operations meet performance targets with complex structures.

        Creates realistic complex hierarchies and validates performance requirements:
        - Hierarchy traversal: <500ms for 5-level depth
        - Component flattening: <400ms
        - Circular reference validation: <200ms
        """
        # Create complex hierarchy with multiple branches
        root_assembly = FinishedGoodService.create_finished_good("Performance Test Root", AssemblyType.HOLIDAY_SET)

        # Create multiple sub-assemblies with various components
        sub_assemblies = []
        for i in range(5):
            sub_assembly = FinishedGoodService.create_finished_good(f"Sub Assembly {i}", AssemblyType.GIFT_BOX)

            # Add multiple components to each sub-assembly
            for j in range(8):
                item = self.fixtures.create_finished_unit(f"Item {i}-{j}", Decimal(f"{i+j+1}.00"))
                FinishedGoodService.add_component(sub_assembly.id, "finished_unit", item.id, j+1)

            sub_assemblies.append(sub_assembly)
            FinishedGoodService.add_component(root_assembly.id, "finished_good", sub_assembly.id, 1)

        # Performance test 1: Hierarchy traversal
        start_time = time.time()
        hierarchy = CompositionService.get_assembly_hierarchy(root_assembly.id)
        hierarchy_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        assert hierarchy_time < 500, f"Hierarchy traversal took {hierarchy_time:.1f}ms (target: <500ms)"

        # Performance test 2: Component flattening
        start_time = time.time()
        flattened = CompositionService.flatten_assembly_components(root_assembly.id)
        flatten_time = (time.time() - start_time) * 1000

        assert flatten_time < 400, f"Component flattening took {flatten_time:.1f}ms (target: <400ms)"

        # Performance test 3: Circular reference validation
        test_assembly = FinishedGoodService.create_finished_good("Test Assembly", AssemblyType.BULK_PACK)

        start_time = time.time()
        is_valid = CompositionService.validate_no_circular_reference(root_assembly.id, test_assembly.id)
        validation_time = (time.time() - start_time) * 1000

        assert validation_time < 200, f"Circular reference validation took {validation_time:.1f}ms (target: <200ms)"
        assert is_valid is True

        # Verify hierarchy structure is correct
        assert len(hierarchy['components']) == 5
        total_flattened_items = sum(1 for comp in flattened if comp['component_type'] == 'finished_unit')
        assert total_flattened_items == 40  # 5 sub-assemblies × 8 items each

        logger.info(f"Performance validation passed - Hierarchy: {hierarchy_time:.1f}ms, Flatten: {flatten_time:.1f}ms, Validation: {validation_time:.1f}ms")

    def test_cache_performance_and_invalidation(self):
        """
        Test hierarchy cache performance and proper invalidation.

        Validates that caching improves performance and cache is properly
        invalidated when compositions are modified.
        """
        # Create test assembly
        assembly = FinishedGoodService.create_finished_good("Cache Test Assembly", AssemblyType.GIFT_BOX)

        # Add some components
        for i in range(5):
            item = self.fixtures.create_finished_unit(f"Cache Item {i}", Decimal(f"{i+1}.00"))
            FinishedGoodService.add_component(assembly.id, "finished_unit", item.id, i+1)

        # Clear cache and get initial stats
        CompositionService.clear_hierarchy_cache()
        initial_stats = CompositionService.get_cache_statistics()
        assert initial_stats['cache_size'] == 0

        # First call - should populate cache
        start_time = time.time()
        hierarchy_1 = CompositionService.get_assembly_hierarchy(assembly.id)
        first_call_time = time.time() - start_time

        # Verify cache was populated
        stats_after_first = CompositionService.get_cache_statistics()
        assert stats_after_first['cache_size'] == 1

        # Second call - should use cache (much faster)
        start_time = time.time()
        hierarchy_2 = CompositionService.get_assembly_hierarchy(assembly.id)
        cached_call_time = time.time() - start_time

        # Verify cache hit
        assert hierarchy_1 == hierarchy_2
        assert cached_call_time < first_call_time * 0.5  # Should be significantly faster

        # Add new component - should invalidate cache
        new_item = self.fixtures.create_finished_unit("New Cache Item", Decimal("10.00"))
        FinishedGoodService.add_component(assembly.id, "finished_unit", new_item.id, 1)

        # Verify hierarchy includes new component
        hierarchy_3 = CompositionService.get_assembly_hierarchy(assembly.id)
        assert len(hierarchy_3['components']) == 6  # Original 5 + new 1

        # Test explicit cache clearing
        CompositionService.clear_hierarchy_cache(assembly.id)
        stats_after_clear = CompositionService.get_cache_statistics()
        assert stats_after_clear['cache_size'] == 0

        logger.info(f"Cache performance validated - Initial: {first_call_time*1000:.1f}ms, Cached: {cached_call_time*1000:.1f}ms")

    def test_user_story_acceptance_scenarios(self):
        """
        Test all User Story 3 acceptance scenarios end-to-end.

        User Story 3: Create Nested Package Hierarchies
        - Create deluxe gift set with packages containing both units and other packages
        - Track multi-level composition including packages within packages
        - Inventory changes propagate correctly through all hierarchy levels
        """
        # Scenario 1: Create deluxe gift set with nested packages
        # Individual items
        cookie = self.fixtures.create_finished_unit("Gourmet Cookie", Decimal("3.00"), inventory_count=50)
        truffle = self.fixtures.create_finished_unit("Chocolate Truffle", Decimal("4.00"), inventory_count=30)
        tea_bag = self.fixtures.create_finished_unit("Premium Tea Bag", Decimal("1.50"), inventory_count=100)

        # Intermediate packages
        cookie_pack = FinishedGoodService.create_finished_good("Cookie 3-Pack", AssemblyType.VARIETY_PACK)
        FinishedGoodService.add_component(cookie_pack.id, "finished_unit", cookie.id, 3)

        truffle_box = FinishedGoodService.create_finished_good("Truffle Gift Box", AssemblyType.GIFT_BOX)
        FinishedGoodService.add_component(truffle_box.id, "finished_unit", truffle.id, 6)

        tea_sampler = FinishedGoodService.create_finished_good("Tea Sampler", AssemblyType.VARIETY_PACK)
        FinishedGoodService.add_component(tea_sampler.id, "finished_unit", tea_bag.id, 10)

        # Deluxe gift set containing packages and individual items
        deluxe_set = FinishedGoodService.create_finished_good("Deluxe Tea & Treats Set", AssemblyType.HOLIDAY_SET)
        FinishedGoodService.add_component(deluxe_set.id, "finished_good", cookie_pack.id, 1)
        FinishedGoodService.add_component(deluxe_set.id, "finished_good", truffle_box.id, 1)
        FinishedGoodService.add_component(deluxe_set.id, "finished_good", tea_sampler.id, 1)
        FinishedGoodService.add_component(deluxe_set.id, "finished_unit", truffle.id, 2)  # Additional individual truffles

        # Scenario validation: Multi-level composition tracking
        hierarchy = CompositionService.get_assembly_hierarchy(deluxe_set.id)

        # Verify structure contains both packages and individual items
        components = hierarchy['components']
        package_components = [c for c in components if c['component_type'] == 'finished_good']
        individual_components = [c for c in components if c['component_type'] == 'finished_unit']

        assert len(package_components) == 3  # cookie_pack, truffle_box, tea_sampler
        assert len(individual_components) == 1  # direct truffles

        # Verify nested structure exists
        for package_comp in package_components:
            assert len(package_comp['subcomponents']) > 0  # Each package should have subcomponents

        # Scenario validation: Inventory propagation through all levels
        requirements = CompositionService.calculate_required_inventory(deluxe_set.id, 5)  # 5 deluxe sets

        # Expected requirements:
        # - Cookies: 5 sets × 1 pack × 3 cookies = 15 cookies (available: 50) ✓
        # - Truffles: 5 sets × (1 box × 6 + 2 individual) = 40 truffles (available: 30) ✗
        # - Tea bags: 5 sets × 1 sampler × 10 bags = 50 bags (available: 100) ✓

        assert requirements['availability_status'] == 'insufficient'  # Due to truffle shortage

        # Find truffle requirement
        truffle_req = None
        for req in requirements['finished_unit_requirements']:
            if req['component_id'] == truffle.id:
                truffle_req = req
                break

        assert truffle_req is not None
        assert truffle_req['required_quantity'] == 40
        assert truffle_req['available_quantity'] == 30
        assert truffle_req['shortage'] == 10
        assert truffle_req['is_sufficient'] is False

        # Scenario validation: Correct cost aggregation
        cost_breakdown = CompositionService.calculate_assembly_component_costs(deluxe_set.id)

        # Should include costs from both package assemblies and individual items
        assert len(cost_breakdown['finished_good_costs']) == 3  # 3 packages
        assert len(cost_breakdown['finished_unit_costs']) == 1   # 1 direct truffle component

        # Test flattened view for complete bill of materials
        flattened = CompositionService.flatten_assembly_components(deluxe_set.id)

        # Verify all base components are included with correct quantities
        base_components = {comp['component_id']: comp['total_quantity']
                          for comp in flattened if comp['component_type'] == 'finished_unit'}

        assert base_components[cookie.id] == 3      # 1 pack × 3 cookies
        assert base_components[truffle.id] == 8     # 1 box × 6 + 2 individual
        assert base_components[tea_bag.id] == 10    # 1 sampler × 10 bags

        logger.info("Successfully validated all User Story 3 acceptance scenarios")

# Additional helper methods for complex scenarios could be added here
# such as performance stress tests, edge case validations, etc.