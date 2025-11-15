"""
Test fixtures for complex hierarchy operations.

Provides realistic test data and helper methods for creating complex
assembly hierarchies used in integration testing.

Fixtures include:
- Realistic bakery product hierarchies
- Complex gift set scenarios
- Multi-level assembly structures
- Performance testing data sets
"""

import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.services.finished_good_service import FinishedGoodService
from src.services.finished_unit_service import FinishedUnitService
from src.models import FinishedGood, FinishedUnit, AssemblyType
from src.database import session_scope

logger = logging.getLogger(__name__)


class HierarchyTestFixtures:
    """
    Test fixtures for complex hierarchy testing.

    Provides methods to create realistic test data for bakery assembly
    hierarchies with proper relationships and data consistency.
    """

    def __init__(self):
        """Initialize fixtures with tracking for cleanup."""
        self.created_finished_units: List[int] = []
        self.created_finished_goods: List[int] = []

    def create_finished_unit(
        self,
        display_name: str,
        unit_cost: Decimal,
        slug: Optional[str] = None,
        description: str = "",
        inventory_count: int = 0,
        **kwargs
    ) -> FinishedUnit:
        """
        Create a FinishedUnit for testing with sensible defaults.

        Args:
            display_name: Name of the item
            unit_cost: Cost per unit
            slug: URL slug (auto-generated if not provided)
            description: Item description
            inventory_count: Available inventory
            **kwargs: Additional fields

        Returns:
            Created FinishedUnit instance
        """
        if slug is None:
            # Generate slug from display_name
            slug = display_name.lower().replace(' ', '-').replace('&', 'and')

        finished_unit_data = {
            'display_name': display_name,
            'slug': slug,
            'description': description or f"Test {display_name}",
            'unit_cost': unit_cost,
            'inventory_count': inventory_count,
            'production_notes': kwargs.get('production_notes', ''),
        }

        finished_unit = FinishedUnitService.create_finished_unit(**finished_unit_data)
        self.created_finished_units.append(finished_unit.id)

        logger.debug(f"Created test FinishedUnit: {display_name} (ID: {finished_unit.id})")
        return finished_unit

    def create_realistic_bakery_items(self) -> Dict[str, FinishedUnit]:
        """
        Create a set of realistic bakery items for testing.

        Returns:
            Dictionary mapping item names to FinishedUnit instances
        """
        items = {}

        # Cookies
        items['chocolate_chip_cookie'] = self.create_finished_unit(
            "Chocolate Chip Cookie", Decimal("2.50"), inventory_count=150,
            description="Fresh baked chocolate chip cookie with premium chocolate"
        )

        items['oatmeal_raisin_cookie'] = self.create_finished_unit(
            "Oatmeal Raisin Cookie", Decimal("2.25"), inventory_count=120,
            description="Wholesome oatmeal cookie with plump raisins"
        )

        items['sugar_cookie'] = self.create_finished_unit(
            "Sugar Cookie", Decimal("2.00"), inventory_count=180,
            description="Classic sugar cookie with vanilla flavor"
        )

        # Pastries
        items['croissant'] = self.create_finished_unit(
            "Butter Croissant", Decimal("3.50"), inventory_count=80,
            description="Flaky French butter croissant"
        )

        items['danish'] = self.create_finished_unit(
            "Fruit Danish", Decimal("4.00"), inventory_count=60,
            description="Danish pastry with seasonal fruit"
        )

        items['muffin'] = self.create_finished_unit(
            "Blueberry Muffin", Decimal("3.25"), inventory_count=100,
            description="Fresh blueberry muffin with streusel top"
        )

        # Premium items
        items['chocolate_truffle'] = self.create_finished_unit(
            "Dark Chocolate Truffle", Decimal("4.50"), inventory_count=40,
            description="Handcrafted dark chocolate truffle"
        )

        items['artisan_bread'] = self.create_finished_unit(
            "Artisan Sourdough Bread", Decimal("8.00"), inventory_count=25,
            description="Hand-crafted sourdough with natural starter"
        )

        items['specialty_cake_slice'] = self.create_finished_unit(
            "Specialty Cake Slice", Decimal("6.75"), inventory_count=30,
            description="Slice of our signature layered cake"
        )

        # Packaging materials
        items['gift_box_small'] = self.create_finished_unit(
            "Small Gift Box", Decimal("2.50"), inventory_count=200,
            description="Elegant small gift box with ribbon"
        )

        items['gift_box_large'] = self.create_finished_unit(
            "Large Gift Box", Decimal("5.00"), inventory_count=100,
            description="Premium large gift box for special occasions"
        )

        items['tissue_paper'] = self.create_finished_unit(
            "Decorative Tissue Paper", Decimal("0.75"), inventory_count=500,
            description="High-quality decorative tissue paper"
        )

        items['ribbon'] = self.create_finished_unit(
            "Satin Ribbon", Decimal("1.25"), inventory_count=300,
            description="Premium satin ribbon for gift wrapping"
        )

        logger.info(f"Created {len(items)} realistic bakery test items")
        return items

    def create_sample_gift_boxes(self, items: Dict[str, FinishedUnit]) -> Dict[str, FinishedGood]:
        """
        Create sample gift box assemblies using provided items.

        Args:
            items: Dictionary of FinishedUnit items to use as components

        Returns:
            Dictionary mapping gift box names to FinishedGood instances
        """
        gift_boxes = {}

        # Cookie Sampler Box
        gift_boxes['cookie_sampler'] = FinishedGoodService.create_finished_good(
            "Cookie Sampler Box",
            AssemblyType.GIFT_BOX,
            description="Assorted premium cookies in elegant gift box"
        )

        FinishedGoodService.add_component(
            gift_boxes['cookie_sampler'].id, "finished_unit",
            items['chocolate_chip_cookie'].id, 4
        )
        FinishedGoodService.add_component(
            gift_boxes['cookie_sampler'].id, "finished_unit",
            items['oatmeal_raisin_cookie'].id, 3
        )
        FinishedGoodService.add_component(
            gift_boxes['cookie_sampler'].id, "finished_unit",
            items['sugar_cookie'].id, 3
        )
        FinishedGoodService.add_component(
            gift_boxes['cookie_sampler'].id, "finished_unit",
            items['gift_box_small'].id, 1
        )

        # Pastry Variety Pack
        gift_boxes['pastry_variety'] = FinishedGoodService.create_finished_good(
            "Pastry Variety Pack",
            AssemblyType.VARIETY_PACK,
            description="Fresh pastries for the perfect morning"
        )

        FinishedGoodService.add_component(
            gift_boxes['pastry_variety'].id, "finished_unit",
            items['croissant'].id, 2
        )
        FinishedGoodService.add_component(
            gift_boxes['pastry_variety'].id, "finished_unit",
            items['danish'].id, 2
        )
        FinishedGoodService.add_component(
            gift_boxes['pastry_variety'].id, "finished_unit",
            items['muffin'].id, 2
        )
        FinishedGoodService.add_component(
            gift_boxes['pastry_variety'].id, "finished_unit",
            items['tissue_paper'].id, 3
        )

        # Premium Collection
        gift_boxes['premium_collection'] = FinishedGoodService.create_finished_good(
            "Premium Artisan Collection",
            AssemblyType.CUSTOM_ORDER,
            description="Curated selection of our finest artisan products"
        )

        FinishedGoodService.add_component(
            gift_boxes['premium_collection'].id, "finished_unit",
            items['chocolate_truffle'].id, 6
        )
        FinishedGoodService.add_component(
            gift_boxes['premium_collection'].id, "finished_unit",
            items['artisan_bread'].id, 1
        )
        FinishedGoodService.add_component(
            gift_boxes['premium_collection'].id, "finished_unit",
            items['specialty_cake_slice'].id, 2
        )
        FinishedGoodService.add_component(
            gift_boxes['premium_collection'].id, "finished_unit",
            items['gift_box_large'].id, 1
        )
        FinishedGoodService.add_component(
            gift_boxes['premium_collection'].id, "finished_unit",
            items['ribbon'].id, 2
        )

        # Track created assemblies for cleanup
        for assembly in gift_boxes.values():
            self.created_finished_goods.append(assembly.id)

        logger.info(f"Created {len(gift_boxes)} sample gift box assemblies")
        return gift_boxes

    def create_holiday_gift_hierarchy(self) -> Dict[str, Any]:
        """
        Create a complex holiday gift hierarchy for comprehensive testing.

        Creates a realistic 3-level hierarchy:
        Holiday Collection → Gift Boxes → Individual Items

        Returns:
            Dictionary with all created items and assemblies
        """
        # Create base items
        items = self.create_realistic_bakery_items()

        # Create intermediate gift boxes
        gift_boxes = self.create_sample_gift_boxes(items)

        # Create top-level holiday collection
        holiday_collection = FinishedGoodService.create_finished_good(
            "Ultimate Holiday Collection",
            AssemblyType.HOLIDAY_SET,
            description="The perfect holiday gift featuring our complete range of treats"
        )

        # Add gift boxes to holiday collection
        FinishedGoodService.add_component(
            holiday_collection.id, "finished_good",
            gift_boxes['cookie_sampler'].id, 1
        )
        FinishedGoodService.add_component(
            holiday_collection.id, "finished_good",
            gift_boxes['pastry_variety'].id, 1
        )
        FinishedGoodService.add_component(
            holiday_collection.id, "finished_good",
            gift_boxes['premium_collection'].id, 1
        )

        # Add some individual premium items
        FinishedGoodService.add_component(
            holiday_collection.id, "finished_unit",
            items['artisan_bread'].id, 1
        )
        FinishedGoodService.add_component(
            holiday_collection.id, "finished_unit",
            items['gift_box_large'].id, 1
        )

        self.created_finished_goods.append(holiday_collection.id)

        logger.info("Created complex holiday gift hierarchy for testing")

        return {
            'items': items,
            'gift_boxes': gift_boxes,
            'holiday_collection': holiday_collection,
            'hierarchy_levels': 3,
            'total_base_items': len(items),
            'total_assemblies': len(gift_boxes) + 1
        }

    def create_performance_test_hierarchy(self, depth: int = 5, breadth: int = 5) -> Dict[str, Any]:
        """
        Create a hierarchy optimized for performance testing.

        Args:
            depth: Maximum hierarchy depth
            breadth: Number of components per assembly level

        Returns:
            Dictionary with performance test data
        """
        assemblies = []
        all_items = []

        # Create base items
        for i in range(breadth * depth):
            item = self.create_finished_unit(
                f"Perf Test Item {i:03d}",
                Decimal(f"{(i % 10) + 1}.{(i % 100):02d}"),
                inventory_count=100 + (i % 50)
            )
            all_items.append(item)

        # Create hierarchy levels
        for level in range(depth):
            level_assemblies = []

            for assembly_idx in range(breadth):
                assembly = FinishedGoodService.create_finished_good(
                    f"Perf Assembly L{level}-A{assembly_idx}",
                    AssemblyType.BULK_PACK,
                    description=f"Performance test assembly at level {level}"
                )

                if level == 0:
                    # Bottom level: add base items
                    start_idx = assembly_idx * breadth
                    for item_idx in range(breadth):
                        if start_idx + item_idx < len(all_items):
                            FinishedGoodService.add_component(
                                assembly.id, "finished_unit",
                                all_items[start_idx + item_idx].id, item_idx + 1
                            )
                else:
                    # Higher levels: add assemblies from previous level
                    prev_level_assemblies = assemblies[level - 1]
                    for prev_assembly in prev_level_assemblies:
                        FinishedGoodService.add_component(
                            assembly.id, "finished_good",
                            prev_assembly.id, 1
                        )

                level_assemblies.append(assembly)
                self.created_finished_goods.append(assembly.id)

            assemblies.append(level_assemblies)

        # Create root assembly
        root_assembly = FinishedGoodService.create_finished_good(
            "Performance Test Root",
            AssemblyType.CUSTOM_ORDER,
            description="Root assembly for performance testing"
        )

        # Add top-level assemblies to root
        for assembly in assemblies[-1]:
            FinishedGoodService.add_component(root_assembly.id, "finished_good", assembly.id, 1)

        self.created_finished_goods.append(root_assembly.id)

        logger.info(f"Created performance test hierarchy: {depth} levels, {breadth} breadth")

        return {
            'root_assembly': root_assembly,
            'all_assemblies': assemblies,
            'all_items': all_items,
            'depth': depth,
            'breadth': breadth,
            'total_items': len(all_items),
            'total_assemblies': sum(len(level) for level in assemblies) + 1
        }

    def create_circular_reference_test_data(self) -> Dict[str, FinishedGood]:
        """
        Create assemblies specifically for circular reference testing.

        Returns:
            Dictionary with test assemblies for various circular reference scenarios
        """
        assemblies = {}

        # Create 6 assemblies for comprehensive circular reference testing
        for i, assembly_type in enumerate([
            AssemblyType.GIFT_BOX, AssemblyType.VARIETY_PACK, AssemblyType.HOLIDAY_SET,
            AssemblyType.BULK_PACK, AssemblyType.CUSTOM_ORDER, AssemblyType.GIFT_BOX
        ]):
            assembly = FinishedGoodService.create_finished_good(
                f"Circular Test Assembly {chr(65 + i)}",  # A, B, C, D, E, F
                assembly_type,
                description=f"Assembly for circular reference testing scenario {i+1}"
            )
            assemblies[chr(65 + i)] = assembly
            self.created_finished_goods.append(assembly.id)

        # Create some base items for valid components
        base_items = []
        for i in range(3):
            item = self.create_finished_unit(
                f"Circular Test Item {i+1}",
                Decimal(f"{i+1}.00"),
                inventory_count=50
            )
            base_items.append(item)

        logger.info("Created assemblies for circular reference testing")

        return {
            'assemblies': assemblies,
            'base_items': base_items
        }

    def cleanup(self):
        """
        Clean up all created test data.

        Removes all FinishedUnits and FinishedGoods created by this fixture
        instance in the correct dependency order.
        """
        try:
            with session_scope() as session:
                # Delete in dependency order: compositions first, then assemblies, then units
                from src.models import Composition

                # Delete compositions for all created assemblies
                if self.created_finished_goods:
                    session.query(Composition)\
                        .filter(Composition.assembly_id.in_(self.created_finished_goods))\
                        .delete(synchronize_session=False)

                # Delete finished goods
                if self.created_finished_goods:
                    session.query(FinishedGood)\
                        .filter(FinishedGood.id.in_(self.created_finished_goods))\
                        .delete(synchronize_session=False)

                # Delete finished units
                if self.created_finished_units:
                    session.query(FinishedUnit)\
                        .filter(FinishedUnit.id.in_(self.created_finished_units))\
                        .delete(synchronize_session=False)

                session.commit()

                logger.info(f"Cleaned up {len(self.created_finished_goods)} assemblies and {len(self.created_finished_units)} units")

        except Exception as e:
            logger.error(f"Error during test data cleanup: {e}")
            # Re-raise to ensure test failures are visible
            raise

        finally:
            # Reset tracking lists
            self.created_finished_units.clear()
            self.created_finished_goods.clear()


# Convenience functions for common test scenarios

def create_simple_hierarchy() -> Dict[str, Any]:
    """Create a simple 2-level hierarchy for basic testing."""
    fixtures = HierarchyTestFixtures()

    # Create base items
    item1 = fixtures.create_finished_unit("Simple Item 1", Decimal("5.00"), inventory_count=50)
    item2 = fixtures.create_finished_unit("Simple Item 2", Decimal("7.50"), inventory_count=30)

    # Create assembly
    assembly = FinishedGoodService.create_finished_good("Simple Assembly", AssemblyType.GIFT_BOX)
    FinishedGoodService.add_component(assembly.id, "finished_unit", item1.id, 2)
    FinishedGoodService.add_component(assembly.id, "finished_unit", item2.id, 1)

    fixtures.created_finished_goods.append(assembly.id)

    return {
        'fixtures': fixtures,
        'items': [item1, item2],
        'assembly': assembly
    }


def create_complex_nested_hierarchy() -> Dict[str, Any]:
    """Create a complex multi-level hierarchy for advanced testing."""
    fixtures = HierarchyTestFixtures()
    return fixtures.create_holiday_gift_hierarchy()