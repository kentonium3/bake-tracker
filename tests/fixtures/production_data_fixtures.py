"""
Production data fixtures for migration testing.

Provides realistic production-scale datasets for testing migration workflows
with representative data volumes, relationships, and edge cases that would
occur in actual bakery operations.

Data Scenarios:
- Large volume FinishedGood datasets (1000+ records)
- Complex Recipe relationships and dependencies
- PantryConsumption patterns and inventory tracking
- ProductionRun history and yield data
- Edge cases and data quality issues
"""

import logging
import random
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from src.services.finished_unit_service import FinishedUnitService
from src.services.finished_good_service import FinishedGoodService
from src.services.composition_service import CompositionService
from src.models import FinishedUnit, FinishedGood, AssemblyType
from src.database import session_scope

logger = logging.getLogger(__name__)


class ProductionDataFixtures:
    """
    Production-scale data fixtures for migration and performance testing.

    Generates realistic datasets that represent actual bakery operations
    with appropriate data volumes, relationships, and edge cases.
    """

    def __init__(self):
        """Initialize fixtures with tracking for cleanup."""
        self.created_finished_units: List[int] = []
        self.created_finished_goods: List[int] = []
        self.data_characteristics = {}

    def create_large_finished_unit_dataset(self, count: int = 1000) -> Dict[str, Any]:
        """
        Create a large dataset of FinishedUnits for migration testing.

        Args:
            count: Number of FinishedUnits to create (default: 1000)

        Returns:
            Dictionary with created items and dataset characteristics
        """
        logger.info(f"Creating large FinishedUnit dataset with {count} items")

        # Define realistic bakery product categories
        product_categories = [
            {
                'name': 'cookies',
                'items': [
                    'Chocolate Chip Cookie', 'Sugar Cookie', 'Oatmeal Raisin Cookie',
                    'Snickerdoodle', 'Peanut Butter Cookie', 'Double Chocolate Cookie',
                    'Gingerbread Cookie', 'Molasses Cookie', 'White Chocolate Macadamia'
                ],
                'cost_range': (Decimal('1.50'), Decimal('4.00')),
                'inventory_range': (50, 300)
            },
            {
                'name': 'pastries',
                'items': [
                    'Croissant', 'Danish', 'Eclair', 'Cream Puff', 'Turnover',
                    'Scone', 'Muffin', 'Donut', 'Bear Claw', 'Cinnamon Roll'
                ],
                'cost_range': (Decimal('2.50'), Decimal('6.00')),
                'inventory_range': (20, 150)
            },
            {
                'name': 'breads',
                'items': [
                    'Sourdough Loaf', 'White Bread', 'Wheat Bread', 'Rye Bread',
                    'French Baguette', 'Focaccia', 'Ciabatta', 'Pumpernickel',
                    'Multigrain Loaf', 'Artisan Roll'
                ],
                'cost_range': (Decimal('4.00'), Decimal('15.00')),
                'inventory_range': (10, 80)
            },
            {
                'name': 'desserts',
                'items': [
                    'Chocolate Cake Slice', 'Cheesecake Slice', 'Pie Slice',
                    'Brownie', 'Cupcake', 'Tart', 'Truffle', 'Macaroon',
                    'Tiramisu', 'Mousse Cup'
                ],
                'cost_range': (Decimal('3.00'), Decimal('8.00')),
                'inventory_range': (15, 100)
            },
            {
                'name': 'seasonal',
                'items': [
                    'Holiday Cookie', 'Easter Bread', 'Pumpkin Pie',
                    'Valentine Cupcake', 'Christmas Cake', 'Halloween Treat',
                    'Summer Fruit Tart', 'Spring Roll', 'Winter Warmer'
                ],
                'cost_range': (Decimal('2.00'), Decimal('10.00')),
                'inventory_range': (5, 200)
            }
        ]

        created_items = []
        category_distribution = {}

        # Create items distributed across categories
        items_per_category = count // len(product_categories)
        remainder = count % len(product_categories)

        for cat_index, category in enumerate(product_categories):
            category_count = items_per_category + (1 if cat_index < remainder else 0)
            category_items = []

            for i in range(category_count):
                # Select random item from category
                base_name = random.choice(category['items'])

                # Add variation to create unique items
                variations = ['', 'Premium', 'Organic', 'Gluten-Free', 'Vegan', 'Mini', 'Large']
                variation = random.choice(variations)
                display_name = f"{variation} {base_name}".strip()

                # Generate realistic cost within category range
                min_cost, max_cost = category['cost_range']
                cost_decimal = Decimal(str(random.uniform(float(min_cost), float(max_cost))))
                unit_cost = round(cost_decimal, 2)

                # Generate realistic inventory within category range
                min_inv, max_inv = category['inventory_range']
                inventory_count = random.randint(min_inv, max_inv)

                # Create slug from display name
                slug = display_name.lower().replace(' ', '-').replace('&', 'and')

                # Add uniqueness to slug if needed
                slug = f"{slug}-{i:04d}"

                # Create production notes based on category
                production_notes = self._generate_production_notes(category['name'], base_name)

                # Create the FinishedUnit
                item = FinishedUnitService.create_finished_unit(
                    display_name=display_name,
                    slug=slug,
                    description=f"{category['name'].title()} product: {display_name}",
                    unit_cost=unit_cost,
                    inventory_count=inventory_count,
                    production_notes=production_notes
                )

                created_items.append(item)
                category_items.append(item)
                self.created_finished_units.append(item.id)

            category_distribution[category['name']] = len(category_items)

        # Generate dataset characteristics
        total_cost = sum(item.unit_cost for item in created_items)
        total_inventory = sum(item.inventory_count for item in created_items)
        avg_cost = total_cost / len(created_items)

        dataset_info = {
            'items': created_items,
            'total_count': len(created_items),
            'category_distribution': category_distribution,
            'total_cost': float(total_cost),
            'total_inventory': total_inventory,
            'average_cost': float(avg_cost),
            'cost_range': {
                'min': float(min(item.unit_cost for item in created_items)),
                'max': float(max(item.unit_cost for item in created_items))
            },
            'inventory_range': {
                'min': min(item.inventory_count for item in created_items),
                'max': max(item.inventory_count for item in created_items)
            }
        }

        logger.info(f"Created {len(created_items)} FinishedUnits across {len(product_categories)} categories")
        logger.info(f"Total cost: ${total_cost:.2f}, Avg cost: ${avg_cost:.2f}")
        logger.info(f"Total inventory: {total_inventory} units")

        return dataset_info

    def create_complex_assembly_relationships(self, base_items: List[FinishedUnit], assembly_count: int = 200) -> Dict[str, Any]:
        """
        Create complex assembly relationships using the base items.

        Args:
            base_items: List of FinishedUnit items to use as components
            assembly_count: Number of assemblies to create

        Returns:
            Dictionary with created assemblies and relationship data
        """
        logger.info(f"Creating {assembly_count} complex assemblies from {len(base_items)} base items")

        if len(base_items) < 10:
            raise ValueError("Need at least 10 base items to create complex relationships")

        # Define assembly patterns based on bakery business logic
        assembly_patterns = [
            {
                'type': AssemblyType.GIFT_BOX,
                'name_patterns': ['Gift Box', 'Present Box', 'Holiday Box', 'Special Box'],
                'component_count_range': (3, 8),
                'description': 'Elegant gift box with assorted treats'
            },
            {
                'type': AssemblyType.VARIETY_PACK,
                'name_patterns': ['Variety Pack', 'Sampler Pack', 'Assortment', 'Mixed Pack'],
                'component_count_range': (4, 12),
                'description': 'Variety pack with diverse selection'
            },
            {
                'type': AssemblyType.HOLIDAY_SET,
                'name_patterns': ['Holiday Set', 'Seasonal Set', 'Festival Set', 'Celebration Set'],
                'component_count_range': (3, 10),
                'description': 'Special holiday-themed collection'
            },
            {
                'type': AssemblyType.BULK_PACK,
                'name_patterns': ['Bulk Pack', 'Family Pack', 'Large Pack', 'Value Pack'],
                'component_count_range': (1, 20),
                'description': 'Bulk packaging for large quantities'
            },
            {
                'type': AssemblyType.CUSTOM_ORDER,
                'name_patterns': ['Custom Order', 'Special Request', 'Bespoke Set', 'Tailored Pack'],
                'component_count_range': (1, 15),
                'description': 'Custom-configured package'
            }
        ]

        created_assemblies = []
        relationship_stats = {
            'total_compositions': 0,
            'nested_assemblies': 0,
            'component_usage': {},
            'assembly_types': {}
        }

        # Create simple assemblies first
        simple_assemblies = []
        for i in range(int(assembly_count * 0.7)):  # 70% simple assemblies
            pattern = random.choice(assembly_patterns)

            # Generate assembly name
            base_name = random.choice(pattern['name_patterns'])
            display_name = f"{base_name} {i+1:03d}"

            # Create assembly
            assembly = FinishedGoodService.create_finished_good(
                display_name=display_name,
                assembly_type=pattern['type'],
                description=pattern['description']
            )

            # Add random components
            component_count = random.randint(*pattern['component_count_range'])
            selected_components = random.sample(base_items, min(component_count, len(base_items)))

            for component in selected_components:
                quantity = random.randint(1, 5)
                FinishedGoodService.add_component(
                    assembly.id, "finished_unit", component.id, quantity
                )

                # Track usage statistics
                relationship_stats['component_usage'][component.id] = \
                    relationship_stats['component_usage'].get(component.id, 0) + 1

            simple_assemblies.append(assembly)
            created_assemblies.append(assembly)
            self.created_finished_goods.append(assembly.id)

            # Track assembly type statistics
            type_name = pattern['type'].value
            relationship_stats['assembly_types'][type_name] = \
                relationship_stats['assembly_types'].get(type_name, 0) + 1

            relationship_stats['total_compositions'] += component_count

        # Create nested assemblies (30% of total)
        nested_count = assembly_count - len(simple_assemblies)
        for i in range(nested_count):
            pattern = random.choice(assembly_patterns)

            display_name = f"Nested {pattern['name_patterns'][0]} {i+1:03d}"

            # Create nested assembly
            nested_assembly = FinishedGoodService.create_finished_good(
                display_name=display_name,
                assembly_type=pattern['type'],
                description=f"Nested {pattern['description']}"
            )

            # Add some individual components
            individual_count = random.randint(1, 3)
            individual_components = random.sample(base_items, min(individual_count, len(base_items)))

            for component in individual_components:
                quantity = random.randint(1, 3)
                FinishedGoodService.add_component(
                    nested_assembly.id, "finished_unit", component.id, quantity
                )

            # Add 1-2 other assemblies as components (creating hierarchy)
            if simple_assemblies:
                assembly_component_count = random.randint(1, min(2, len(simple_assemblies)))
                assembly_components = random.sample(simple_assemblies, assembly_component_count)

                for assembly_component in assembly_components:
                    # Validate no circular reference before adding
                    if CompositionService.validate_no_circular_reference(
                        nested_assembly.id, assembly_component.id
                    ):
                        FinishedGoodService.add_component(
                            nested_assembly.id, "finished_good", assembly_component.id, 1
                        )
                        relationship_stats['nested_assemblies'] += 1

            created_assemblies.append(nested_assembly)
            self.created_finished_goods.append(nested_assembly.id)

            # Track statistics
            type_name = pattern['type'].value
            relationship_stats['assembly_types'][type_name] = \
                relationship_stats['assembly_types'].get(type_name, 0) + 1

        logger.info(f"Created {len(created_assemblies)} assemblies with {relationship_stats['total_compositions']} total compositions")
        logger.info(f"Nested assemblies: {relationship_stats['nested_assemblies']}")

        return {
            'assemblies': created_assemblies,
            'simple_assemblies': simple_assemblies,
            'nested_assemblies': created_assemblies[len(simple_assemblies):],
            'relationship_statistics': relationship_stats
        }

    def create_edge_case_scenarios(self) -> Dict[str, Any]:
        """
        Create edge cases and data quality scenarios for migration testing.

        Returns:
            Dictionary with edge case items and scenarios
        """
        logger.info("Creating edge case scenarios for migration testing")

        edge_cases = {}

        # Edge case 1: Items with zero inventory
        zero_inventory_items = []
        for i in range(5):
            item = FinishedUnitService.create_finished_unit(
                display_name=f"Zero Inventory Item {i+1}",
                slug=f"zero-inventory-item-{i+1}",
                unit_cost=Decimal("5.00"),
                inventory_count=0,
                description="Item with zero inventory for testing"
            )
            zero_inventory_items.append(item)
            self.created_finished_units.append(item.id)

        edge_cases['zero_inventory'] = zero_inventory_items

        # Edge case 2: Items with very high costs
        high_cost_items = []
        for i in range(3):
            item = FinishedUnitService.create_finished_unit(
                display_name=f"Luxury Item {i+1}",
                slug=f"luxury-item-{i+1}",
                unit_cost=Decimal("999.99"),
                inventory_count=1,
                description="High-cost luxury item for edge case testing"
            )
            high_cost_items.append(item)
            self.created_finished_units.append(item.id)

        edge_cases['high_cost'] = high_cost_items

        # Edge case 3: Items with very low costs
        low_cost_items = []
        for i in range(3):
            item = FinishedUnitService.create_finished_unit(
                display_name=f"Promotional Item {i+1}",
                slug=f"promotional-item-{i+1}",
                unit_cost=Decimal("0.01"),
                inventory_count=1000,
                description="Very low cost promotional item"
            )
            low_cost_items.append(item)
            self.created_finished_units.append(item.id)

        edge_cases['low_cost'] = low_cost_items

        # Edge case 4: Items with special characters in names
        special_char_items = []
        special_names = [
            "Café au Lait Cake",
            "Piñata Cookie",
            "Naïve Pastry",
            "Résumé Bread",
            "Jalapeño & Cheese Roll"
        ]

        for i, name in enumerate(special_names):
            # Create safe slug from name with special characters
            slug = name.lower()
            slug = slug.replace('&', 'and').replace(' ', '-')
            slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
            slug = f"{slug}-{i+1}"

            item = FinishedUnitService.create_finished_unit(
                display_name=name,
                slug=slug,
                unit_cost=Decimal("3.50"),
                inventory_count=50,
                description=f"Item with special characters: {name}"
            )
            special_char_items.append(item)
            self.created_finished_units.append(item.id)

        edge_cases['special_characters'] = special_char_items

        # Edge case 5: Long descriptions and notes
        long_content_items = []
        long_description = "This is an extremely long description that tests the handling of large text fields in the database migration process. " * 10
        long_notes = "These are very detailed production notes that include step-by-step instructions, ingredient sourcing information, quality control checkpoints, and historical context. " * 5

        item = FinishedUnitService.create_finished_unit(
            display_name="Long Content Test Item",
            slug="long-content-test-item",
            unit_cost=Decimal("7.50"),
            inventory_count=25,
            description=long_description[:500],  # Truncate if too long
            production_notes=long_notes[:1000]   # Truncate if too long
        )
        long_content_items.append(item)
        self.created_finished_units.append(item.id)

        edge_cases['long_content'] = long_content_items

        logger.info(f"Created edge case scenarios: {len(edge_cases)} categories")

        return edge_cases

    def create_migration_stress_dataset(self, item_count: int = 5000) -> Dict[str, Any]:
        """
        Create a large dataset specifically for migration stress testing.

        Args:
            item_count: Number of items to create for stress testing

        Returns:
            Dataset information and performance characteristics
        """
        logger.info(f"Creating migration stress dataset with {item_count} items")

        # Create large base dataset
        start_time = datetime.now()

        base_dataset = self.create_large_finished_unit_dataset(item_count)

        creation_time = datetime.now() - start_time

        # Create assemblies using subset of items for performance
        assembly_items = base_dataset['items'][:500]  # Use subset for assemblies
        assembly_dataset = self.create_complex_assembly_relationships(
            assembly_items, assembly_count=100
        )

        # Create edge cases
        edge_cases = self.create_edge_case_scenarios()

        total_time = datetime.now() - start_time

        stress_dataset = {
            'base_dataset': base_dataset,
            'assembly_dataset': assembly_dataset,
            'edge_cases': edge_cases,
            'performance_metrics': {
                'creation_time_seconds': creation_time.total_seconds(),
                'total_time_seconds': total_time.total_seconds(),
                'items_per_second': item_count / total_time.total_seconds(),
                'total_items': len(base_dataset['items']),
                'total_assemblies': len(assembly_dataset['assemblies']),
                'total_relationships': assembly_dataset['relationship_statistics']['total_compositions']
            }
        }

        logger.info(f"Stress dataset created in {total_time.total_seconds():.2f} seconds")
        logger.info(f"Rate: {stress_dataset['performance_metrics']['items_per_second']:.1f} items/second")

        return stress_dataset

    def _generate_production_notes(self, category: str, item_name: str) -> str:
        """Generate realistic production notes based on category and item."""

        category_notes = {
            'cookies': [
                "Bake at 350°F for 12-15 minutes until golden brown",
                "Cream butter and sugar thoroughly before adding dry ingredients",
                "Chill dough for 30 minutes before baking for best results",
                "Store in airtight container, consume within 7 days"
            ],
            'pastries': [
                "Requires overnight lamination process for flaky layers",
                "Proof in warm environment for 45-60 minutes",
                "Egg wash before baking for golden finish",
                "Best served fresh, can be frozen for up to 30 days"
            ],
            'breads': [
                "Knead dough for 10-12 minutes until smooth and elastic",
                "First rise: 1.5 hours, second rise: 45 minutes",
                "Score top before baking to prevent cracking",
                "Cool completely before slicing to maintain texture"
            ],
            'desserts': [
                "Temperature control critical for proper texture",
                "Garnish just before serving to maintain appearance",
                "Store refrigerated, bring to room temperature before serving",
                "Use high-quality ingredients for optimal flavor"
            ],
            'seasonal': [
                "Available only during specific seasonal periods",
                "May require special ordering or advance notice",
                "Ingredients subject to seasonal availability",
                "Popular during holiday periods - increase production"
            ]
        }

        base_notes = random.choice(category_notes.get(category, ["Standard production procedures apply"]))

        # Add item-specific notes
        if 'chocolate' in item_name.lower():
            base_notes += " | Use premium Belgian chocolate for best results"
        elif 'organic' in item_name.lower():
            base_notes += " | Certified organic ingredients only"
        elif 'gluten-free' in item_name.lower():
            base_notes += " | Dedicated gluten-free prep area required"

        return base_notes

    def generate_migration_report(self) -> str:
        """Generate comprehensive report of created test data."""

        total_units = len(self.created_finished_units)
        total_goods = len(self.created_finished_goods)

        report_lines = [
            "=== PRODUCTION DATA FIXTURES REPORT ===",
            "",
            f"Created {total_units} FinishedUnit items",
            f"Created {total_goods} FinishedGood assemblies",
            f"Total database records: {total_units + total_goods}",
            "",
            "Dataset suitable for:",
            "- Large-scale migration testing",
            "- Performance benchmarking",
            "- Edge case validation",
            "- Data integrity verification",
            "",
            "=== END REPORT ===",
            ""
        ]

        return "\n".join(report_lines)

    def cleanup(self):
        """Clean up all created test data."""
        try:
            with session_scope() as session:
                from src.models import Composition

                # Delete in dependency order
                if self.created_finished_goods:
                    session.query(Composition)\
                        .filter(Composition.assembly_id.in_(self.created_finished_goods))\
                        .delete(synchronize_session=False)

                if self.created_finished_goods:
                    session.query(FinishedGood)\
                        .filter(FinishedGood.id.in_(self.created_finished_goods))\
                        .delete(synchronize_session=False)

                if self.created_finished_units:
                    session.query(FinishedUnit)\
                        .filter(FinishedUnit.id.in_(self.created_finished_units))\
                        .delete(synchronize_session=False)

                session.commit()

                logger.info(f"Cleaned up {len(self.created_finished_goods)} assemblies and {len(self.created_finished_units)} units")

        except Exception as e:
            logger.error(f"Error during production data cleanup: {e}")
            raise

        finally:
            self.created_finished_units.clear()
            self.created_finished_goods.clear()


# Convenience functions for common production scenarios

def create_small_production_dataset() -> Dict[str, Any]:
    """Create small production dataset for quick testing."""
    fixtures = ProductionDataFixtures()
    dataset = fixtures.create_large_finished_unit_dataset(100)
    return {
        'fixtures': fixtures,
        'dataset': dataset
    }


def create_medium_production_dataset() -> Dict[str, Any]:
    """Create medium production dataset for comprehensive testing."""
    fixtures = ProductionDataFixtures()
    dataset = fixtures.create_large_finished_unit_dataset(1000)
    return {
        'fixtures': fixtures,
        'dataset': dataset
    }


def create_stress_test_dataset() -> Dict[str, Any]:
    """Create large production dataset for stress testing."""
    fixtures = ProductionDataFixtures()
    dataset = fixtures.create_migration_stress_dataset(5000)
    return {
        'fixtures': fixtures,
        'dataset': dataset
    }