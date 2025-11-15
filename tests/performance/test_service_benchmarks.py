"""
Performance benchmarks for all service operations.

Validates performance targets across the complete system including FinishedUnit,
FinishedGood, Composition, and Migration services. Provides comprehensive
benchmarking for regression testing and optimization guidance.

Performance Targets (per specification):
- FinishedUnit CRUD operations: <2s
- FinishedUnit inventory queries: <200ms
- FinishedGood assembly creation: <30s
- FinishedGood component queries: <500ms
- Composition hierarchy traversal: <500ms for 5 levels
- Migration operations: Complete workflow timing with realistic data
- Memory usage: Acceptable bounds for desktop application
"""

import pytest
import logging
import time
import gc
import statistics
import sys
from decimal import Decimal
from typing import List, Dict, Any, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import tracemalloc

from src.services.finished_unit_service import FinishedUnitService
from src.services.finished_good_service import FinishedGoodService
from src.services.composition_service import CompositionService
from src.services.migration_service import MigrationService
from src.models import FinishedUnit, FinishedGood, AssemblyType
from src.database import get_db_session, session_scope

from ..fixtures.hierarchy_fixtures import HierarchyTestFixtures

logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """
    Performance measurement context manager with statistical analysis.

    Provides timing, memory tracking, and statistical analysis for
    performance benchmarks.
    """

    def __init__(self, name: str, target_ms: float = None, description: str = ""):
        self.name = name
        self.target_ms = target_ms
        self.description = description
        self.start_time = None
        self.end_time = None
        self.memory_start = None
        self.memory_peak = None

    def __enter__(self):
        # Force garbage collection for consistent measurements
        gc.collect()

        # Start memory monitoring
        if hasattr(tracemalloc, 'start'):
            tracemalloc.start()
            self.memory_start = tracemalloc.get_traced_memory()[0]

        # Start timing
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Stop timing
        self.end_time = time.perf_counter()

        # Stop memory monitoring
        if hasattr(tracemalloc, 'is_tracing') and tracemalloc.is_tracing():
            current_memory, self.memory_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.start_time is None or self.end_time is None:
            raise ValueError("Benchmark not properly started/stopped")
        return (self.end_time - self.start_time) * 1000

    @property
    def memory_used_mb(self) -> float:
        """Get memory usage in megabytes."""
        if self.memory_peak is None:
            return 0.0
        return (self.memory_peak - (self.memory_start or 0)) / 1024 / 1024

    def assert_within_target(self, description: str = ""):
        """Assert that performance is within target."""
        elapsed = self.elapsed_ms

        if self.target_ms:
            assert elapsed <= self.target_ms, (
                f"{self.name} {description} took {elapsed:.1f}ms "
                f"(target: <{self.target_ms}ms) - {self.description}"
            )

        logger.info(
            f"✓ {self.name} {description}: {elapsed:.1f}ms"
            f"{f' (target: <{self.target_ms}ms)' if self.target_ms else ''}"
            f"{f' - Memory: {self.memory_used_mb:.2f}MB' if self.memory_used_mb else ''}"
        )
        return elapsed

    def log_results(self, details: str = ""):
        """Log benchmark results."""
        elapsed = self.elapsed_ms
        logger.info(
            f"{self.name}: {elapsed:.1f}ms {details}"
            f"{f' - Memory: {self.memory_used_mb:.2f}MB' if self.memory_used_mb else ''}"
        )
        return elapsed


class TestServicePerformanceBenchmarks:
    """Performance benchmarks for all service operations."""

    @pytest.fixture(autouse=True)
    def setup_performance_environment(self):
        """Set up clean performance testing environment."""
        # Clear caches
        CompositionService.clear_hierarchy_cache()

        # Force garbage collection
        gc.collect()

        yield

        # Cleanup after test
        with session_scope() as session:
            from src.models import Composition
            session.query(Composition).delete()
            session.query(FinishedGood).delete()
            session.query(FinishedUnit).delete()
            session.commit()

    def test_finished_unit_crud_performance(self):
        """
        Benchmark FinishedUnit CRUD operations.

        Target: <2s for complete CRUD operations
        Tests: Create, Read, Update, Delete operations with batch processing
        """
        logger.info("Benchmarking FinishedUnit CRUD Performance")

        # Benchmark individual operations
        measurements = {}

        # Test 1: Single item creation performance
        with PerformanceBenchmark("FinishedUnit Create", 100, "single item") as bench:
            test_item = FinishedUnitService.create_finished_unit(
                display_name="Performance Test Item",
                slug="performance-test-item",
                unit_cost=Decimal("5.00"),
                inventory_count=100,
                description="Created for performance testing"
            )
        measurements['create_single'] = bench.assert_within_target("single item creation")

        # Test 2: Single item retrieval performance
        with PerformanceBenchmark("FinishedUnit Read", 50, "single item retrieval") as bench:
            retrieved_item = FinishedUnitService.get_finished_unit_by_id(test_item.id)
        bench.assert_within_target("single item retrieval")
        assert retrieved_item.id == test_item.id

        # Test 3: Single item update performance
        with PerformanceBenchmark("FinishedUnit Update", 100, "single item update") as bench:
            updated_item = FinishedUnitService.update_finished_unit(
                test_item.id,
                unit_cost=Decimal("5.50"),
                inventory_count=95
            )
        measurements['update_single'] = bench.assert_within_target("single item update")

        # Test 4: Bulk creation performance
        bulk_items = []
        with PerformanceBenchmark("FinishedUnit Bulk Create", 1000, "50 items") as bench:
            for i in range(50):
                item = FinishedUnitService.create_finished_unit(
                    display_name=f"Bulk Test Item {i:02d}",
                    slug=f"bulk-test-item-{i:02d}",
                    unit_cost=Decimal(f"{i+1}.00"),
                    inventory_count=100 + i
                )
                bulk_items.append(item)
        measurements['create_bulk'] = bench.assert_within_target("bulk creation (50 items)")

        # Test 5: Bulk retrieval performance
        with PerformanceBenchmark("FinishedUnit Bulk Read", 500, "all items query") as bench:
            all_items = FinishedUnitService.get_all_finished_units()
        measurements['read_bulk'] = bench.assert_within_target("bulk retrieval")
        assert len(all_items) >= 51  # Original + 50 bulk items

        # Test 6: Search performance
        with PerformanceBenchmark("FinishedUnit Search", 300, "search query") as bench:
            search_results = FinishedUnitService.search_finished_units("bulk")
        measurements['search'] = bench.assert_within_target("search operation")
        assert len(search_results) >= 50

        # Test 7: Single item deletion performance
        with PerformanceBenchmark("FinishedUnit Delete", 100, "single item deletion") as bench:
            success = FinishedUnitService.delete_finished_unit(test_item.id)
        measurements['delete_single'] = bench.assert_within_target("single item deletion")
        assert success is True

        # Overall CRUD cycle time validation
        total_crud_time = (
            measurements['create_single'] + measurements['update_single'] + measurements['delete_single']
        )
        assert total_crud_time < 2000, f"Complete CRUD cycle took {total_crud_time:.1f}ms (target: <2000ms)"

        logger.info(f"✓ FinishedUnit CRUD performance validated - Total cycle: {total_crud_time:.1f}ms")

    def test_finished_unit_inventory_queries_performance(self):
        """
        Benchmark FinishedUnit inventory query operations.

        Target: <200ms for inventory queries
        Tests: Inventory filtering, low stock alerts, availability checks
        """
        logger.info("Benchmarking FinishedUnit Inventory Query Performance")

        # Create test dataset with varied inventory levels
        test_items = []
        for i in range(100):
            item = FinishedUnitService.create_finished_unit(
                display_name=f"Inventory Test Item {i:03d}",
                slug=f"inventory-test-item-{i:03d}",
                unit_cost=Decimal(f"{(i % 10) + 1}.00"),
                inventory_count=i * 2  # Varied inventory: 0, 2, 4, ..., 198
            )
            test_items.append(item)

        # Test 1: All items query performance
        with PerformanceBenchmark("Inventory Query All", 200, "all items") as bench:
            all_items = FinishedUnitService.get_all_finished_units()
        bench.assert_within_target("all items query")
        assert len(all_items) >= 100

        # Test 2: Low inventory filtering performance
        with PerformanceBenchmark("Inventory Query Low Stock", 200, "low stock filter") as bench:
            # Filter for items with inventory < 20
            low_stock_items = [item for item in all_items if item.inventory_count < 20]
        bench.assert_within_target("low stock filtering")
        assert len(low_stock_items) >= 10

        # Test 3: Search with inventory considerations
        with PerformanceBenchmark("Inventory Search Query", 200, "search with inventory") as bench:
            search_results = FinishedUnitService.search_finished_units("inventory")
        bench.assert_within_target("inventory search")
        assert len(search_results) >= 50

        # Test 4: Repeated queries performance (caching effects)
        query_times = []
        for i in range(10):
            with PerformanceBenchmark(f"Inventory Query {i+1}", 150) as bench:
                items = FinishedUnitService.get_all_finished_units()
            query_times.append(bench.elapsed_ms)

        # Analyze query consistency
        avg_query_time = statistics.mean(query_times)
        max_query_time = max(query_times)

        assert avg_query_time < 200, f"Average query time {avg_query_time:.1f}ms exceeds target"
        assert max_query_time < 300, f"Maximum query time {max_query_time:.1f}ms too high"

        logger.info(f"✓ Inventory query performance: Avg {avg_query_time:.1f}ms, Max {max_query_time:.1f}ms")

    def test_finished_good_assembly_creation_performance(self):
        """
        Benchmark FinishedGood assembly creation operations.

        Target: <30s for assembly creation
        Tests: Simple assemblies, complex assemblies, bulk assembly creation
        """
        logger.info("Benchmarking FinishedGood Assembly Creation Performance")

        # Create component items for assemblies
        components = []
        for i in range(20):
            component = FinishedUnitService.create_finished_unit(
                display_name=f"Assembly Component {i:02d}",
                slug=f"assembly-component-{i:02d}",
                unit_cost=Decimal(f"{i+1}.50"),
                inventory_count=200
            )
            components.append(component)

        # Test 1: Simple assembly creation (few components)
        with PerformanceBenchmark("Simple Assembly Creation", 5000, "5 components") as bench:
            simple_assembly = FinishedGoodService.create_finished_good(
                display_name="Simple Test Assembly",
                assembly_type=AssemblyType.GIFT_BOX,
                description="Assembly with few components"
            )

            # Add 5 components
            for i in range(5):
                FinishedGoodService.add_component(
                    simple_assembly.id, "finished_unit", components[i].id, i + 1
                )
        bench.assert_within_target("simple assembly (5 components)")

        # Test 2: Complex assembly creation (many components)
        with PerformanceBenchmark("Complex Assembly Creation", 20000, "20 components") as bench:
            complex_assembly = FinishedGoodService.create_finished_good(
                display_name="Complex Test Assembly",
                assembly_type=AssemblyType.VARIETY_PACK,
                description="Assembly with many components"
            )

            # Add all 20 components
            for i, component in enumerate(components):
                FinishedGoodService.add_component(
                    complex_assembly.id, "finished_unit", component.id, i + 1
                )
        bench.assert_within_target("complex assembly (20 components)")

        # Test 3: Nested assembly creation
        with PerformanceBenchmark("Nested Assembly Creation", 15000, "nested structure") as bench:
            # Create intermediate assembly
            intermediate = FinishedGoodService.create_finished_good(
                display_name="Intermediate Assembly",
                assembly_type=AssemblyType.BULK_PACK
            )

            # Add components to intermediate
            for i in range(5):
                FinishedGoodService.add_component(
                    intermediate.id, "finished_unit", components[i + 10].id, 2
                )

            # Create parent assembly
            parent_assembly = FinishedGoodService.create_finished_good(
                display_name="Parent Assembly",
                assembly_type=AssemblyType.HOLIDAY_SET
            )

            # Add intermediate assembly and some individual components
            FinishedGoodService.add_component(parent_assembly.id, "finished_good", intermediate.id, 1)
            FinishedGoodService.add_component(parent_assembly.id, "finished_good", simple_assembly.id, 1)
            FinishedGoodService.add_component(parent_assembly.id, "finished_unit", components[0].id, 3)
        bench.assert_within_target("nested assembly creation")

        # Test 4: Bulk assembly creation performance
        bulk_assemblies = []
        with PerformanceBenchmark("Bulk Assembly Creation", 30000, "10 assemblies") as bench:
            for i in range(10):
                assembly = FinishedGoodService.create_finished_good(
                    display_name=f"Bulk Assembly {i:02d}",
                    assembly_type=AssemblyType.CUSTOM_ORDER
                )

                # Add 3-5 components to each
                component_count = (i % 3) + 3  # 3, 4, or 5 components
                for j in range(component_count):
                    component_idx = (i * 2 + j) % len(components)
                    FinishedGoodService.add_component(
                        assembly.id, "finished_unit", components[component_idx].id, j + 1
                    )

                bulk_assemblies.append(assembly)
        bench.assert_within_target("bulk assembly creation (10 assemblies)")

        # Validate all assemblies were created successfully
        assert len(bulk_assemblies) == 10

        # Test assembly retrieval performance
        with PerformanceBenchmark("Assembly Retrieval", 500, "all assemblies") as bench:
            all_assemblies = FinishedGoodService.get_all_finished_goods()
        bench.assert_within_target("assembly retrieval")
        assert len(all_assemblies) >= 13  # simple + complex + nested + 10 bulk

        logger.info("✓ FinishedGood assembly creation performance validated")

    def test_finished_good_component_queries_performance(self):
        """
        Benchmark FinishedGood component query operations.

        Target: <500ms for component queries
        Tests: Component listing, assembly search, relationship queries
        """
        logger.info("Benchmarking FinishedGood Component Query Performance")

        # Create test assemblies with known structure
        fixtures = HierarchyTestFixtures()
        hierarchy_data = fixtures.create_holiday_gift_hierarchy()

        holiday_collection = hierarchy_data['holiday_collection']
        gift_boxes = hierarchy_data['gift_boxes']

        # Test 1: Component listing performance
        with PerformanceBenchmark("Component Query", 500, "assembly components") as bench:
            components = CompositionService.get_assembly_components(holiday_collection.id)
        bench.assert_within_target("component listing")
        assert len(components) > 0

        # Test 2: Hierarchy query performance
        with PerformanceBenchmark("Hierarchy Query", 500, "full hierarchy") as bench:
            hierarchy = CompositionService.get_assembly_hierarchy(holiday_collection.id)
        bench.assert_within_target("hierarchy query")
        assert hierarchy['assembly_id'] == holiday_collection.id

        # Test 3: Flattened components query performance
        with PerformanceBenchmark("Flattened Components", 500, "bill of materials") as bench:
            flattened = CompositionService.flatten_assembly_components(holiday_collection.id)
        bench.assert_within_target("flattened components")
        assert len(flattened) > 0

        # Test 4: Cost calculation query performance
        with PerformanceBenchmark("Cost Calculation", 400, "assembly costs") as bench:
            costs = CompositionService.calculate_assembly_component_costs(holiday_collection.id)
        bench.assert_within_target("cost calculation")
        assert costs['total_assembly_cost'] > 0

        # Test 5: Inventory requirements query performance
        with PerformanceBenchmark("Inventory Requirements", 300, "production requirements") as bench:
            requirements = CompositionService.calculate_required_inventory(holiday_collection.id, 5)
        bench.assert_within_target("inventory requirements")
        assert requirements['assembly_quantity'] == 5

        # Test 6: Assembly statistics query performance
        with PerformanceBenchmark("Assembly Statistics", 200, "assembly stats") as bench:
            stats = CompositionService.get_assembly_statistics(holiday_collection.id)
        bench.assert_within_target("assembly statistics")
        assert stats['assembly_id'] == holiday_collection.id

        # Test 7: Multiple assembly queries (batch performance)
        all_assemblies = list(gift_boxes.values())[:3]  # Test with first 3 assemblies
        query_times = []

        for assembly in all_assemblies:
            with PerformanceBenchmark("Batch Component Query", 300) as bench:
                components = CompositionService.get_assembly_components(assembly.id)
                hierarchy = CompositionService.get_assembly_hierarchy(assembly.id)
                costs = CompositionService.calculate_assembly_component_costs(assembly.id)
            query_times.append(bench.elapsed_ms)

        avg_batch_time = statistics.mean(query_times)
        assert avg_batch_time < 500, f"Average batch query time {avg_batch_time:.1f}ms exceeds target"

        logger.info(f"✓ Component query performance: Average batch time {avg_batch_time:.1f}ms")

        # Cleanup
        fixtures.cleanup()

    def test_composition_hierarchy_traversal_performance(self):
        """
        Benchmark Composition service hierarchy traversal operations.

        Target: <500ms for 5-level hierarchy traversal
        Tests: Deep hierarchies, wide hierarchies, complex traversal patterns
        """
        logger.info("Benchmarking Composition Hierarchy Traversal Performance")

        fixtures = HierarchyTestFixtures()

        # Test 1: Deep hierarchy performance (5 levels)
        deep_hierarchy = fixtures.create_performance_test_hierarchy(depth=5, breadth=3)
        root_assembly = deep_hierarchy['root_assembly']

        with PerformanceBenchmark("Deep Hierarchy Traversal", 500, "5-level depth") as bench:
            hierarchy = CompositionService.get_assembly_hierarchy(root_assembly.id)
        bench.assert_within_target("5-level hierarchy traversal")

        # Test 2: Wide hierarchy performance (many components)
        wide_hierarchy = fixtures.create_performance_test_hierarchy(depth=3, breadth=8)
        wide_root = wide_hierarchy['root_assembly']

        with PerformanceBenchmark("Wide Hierarchy Traversal", 500, "wide structure") as bench:
            wide_hierarchy_result = CompositionService.get_assembly_hierarchy(wide_root.id)
        bench.assert_within_target("wide hierarchy traversal")

        # Test 3: Flattening performance with complex hierarchy
        with PerformanceBenchmark("Hierarchy Flattening", 400, "complex flattening") as bench:
            flattened = CompositionService.flatten_assembly_components(root_assembly.id)
        bench.assert_within_target("complex hierarchy flattening")
        assert len(flattened) > 0

        # Test 4: Circular reference validation performance
        test_assembly = FinishedGoodService.create_finished_good(
            display_name="Circular Test Assembly",
            assembly_type=AssemblyType.BULK_PACK
        )
        fixtures.created_finished_goods.append(test_assembly.id)

        with PerformanceBenchmark("Circular Reference Check", 200, "validation") as bench:
            is_valid = CompositionService.validate_no_circular_reference(
                root_assembly.id, test_assembly.id
            )
        bench.assert_within_target("circular reference validation")
        assert is_valid is True

        # Test 5: Cache performance analysis
        CompositionService.clear_hierarchy_cache()

        # First call (cache miss)
        with PerformanceBenchmark("Hierarchy Cache Miss", 500) as bench_miss:
            hierarchy_1 = CompositionService.get_assembly_hierarchy(root_assembly.id)

        # Second call (cache hit)
        with PerformanceBenchmark("Hierarchy Cache Hit", 50) as bench_hit:
            hierarchy_2 = CompositionService.get_assembly_hierarchy(root_assembly.id)

        bench_miss.log_results("(cache miss)")
        bench_hit.assert_within_target("(cache hit)")

        # Verify cache effectiveness
        speedup_ratio = bench_miss.elapsed_ms / bench_hit.elapsed_ms
        assert speedup_ratio >= 2.0, f"Cache speedup ratio {speedup_ratio:.1f}x insufficient"

        # Test 6: Statistics calculation performance
        with PerformanceBenchmark("Hierarchy Statistics", 200, "statistics generation") as bench:
            stats = CompositionService.get_assembly_statistics(root_assembly.id)
        bench.assert_within_target("statistics generation")
        assert stats['hierarchy_depth'] <= 5

        logger.info("✓ Hierarchy traversal performance validated")

        # Cleanup
        fixtures.cleanup()

    def test_migration_operations_performance(self):
        """
        Benchmark migration service operations.

        Tests: Migration validation, backup operations, data transformation
        """
        logger.info("Benchmarking Migration Operations Performance")

        # Create realistic dataset for migration testing
        test_items = []
        for i in range(100):
            item = FinishedUnitService.create_finished_unit(
                display_name=f"Migration Test Item {i:03d}",
                slug=f"migration-test-item-{i:03d}",
                unit_cost=Decimal(f"{(i % 50) + 1}.00"),
                inventory_count=100 + i,
                production_notes=f"Test item {i} for migration validation"
            )
            test_items.append(item)

        # Test 1: Pre-migration validation performance
        with PerformanceBenchmark("Migration Validation", 2000, "pre-migration check") as bench:
            validation_result = MigrationService.validate_pre_migration()
        bench.assert_within_target("pre-migration validation")
        assert validation_result['status'] == 'success'
        assert validation_result['total_finished_units'] >= 100

        # Test 2: Migration backup performance (if implemented)
        # Note: This would test backup creation performance
        # Implementation depends on specific backup strategy

        # Test 3: Post-migration validation performance
        with PerformanceBenchmark("Post-Migration Validation", 2000, "data integrity check") as bench:
            # Simulate post-migration validation
            all_items = FinishedUnitService.get_all_finished_units()
            for item in all_items[:10]:  # Sample validation
                retrieved = FinishedUnitService.get_finished_unit_by_id(item.id)
                assert retrieved is not None
        bench.assert_within_target("post-migration validation")

        logger.info("✓ Migration operations performance validated")

    def test_concurrent_operations_performance(self):
        """
        Benchmark service performance under concurrent load.

        Tests: Multiple simultaneous operations, thread safety, resource contention
        """
        logger.info("Benchmarking Concurrent Operations Performance")

        # Create shared test data
        base_items = []
        for i in range(20):
            item = FinishedUnitService.create_finished_unit(
                display_name=f"Concurrent Test Item {i:02d}",
                slug=f"concurrent-test-item-{i:02d}",
                unit_cost=Decimal(f"{i+1}.00"),
                inventory_count=100
            )
            base_items.append(item)

        test_assembly = FinishedGoodService.create_finished_good(
            display_name="Concurrent Test Assembly",
            assembly_type=AssemblyType.VARIETY_PACK
        )

        # Add some components
        for i in range(5):
            FinishedGoodService.add_component(test_assembly.id, "finished_unit", base_items[i].id, i+1)

        def concurrent_operations():
            """Function to run concurrent operations."""
            operations_times = []

            # Mix of read operations that might happen simultaneously
            start_time = time.perf_counter()

            # Operation 1: Get all items
            all_items = FinishedUnitService.get_all_finished_units()

            # Operation 2: Search items
            search_results = FinishedUnitService.search_finished_units("concurrent")

            # Operation 3: Get assembly hierarchy
            hierarchy = CompositionService.get_assembly_hierarchy(test_assembly.id)

            # Operation 4: Calculate costs
            costs = CompositionService.calculate_assembly_component_costs(test_assembly.id)

            # Operation 5: Get assembly components
            components = CompositionService.get_assembly_components(test_assembly.id)

            end_time = time.perf_counter()

            return (end_time - start_time) * 1000, {
                'items_found': len(all_items),
                'search_results': len(search_results),
                'hierarchy_components': len(hierarchy['components']),
                'total_cost': costs['total_assembly_cost'],
                'component_count': len(components)
            }

        # Test concurrent execution
        with PerformanceBenchmark("Concurrent Operations", 3000, "5 threads") as bench:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(concurrent_operations) for _ in range(5)]
                results = [future.result() for future in as_completed(futures)]

        bench.assert_within_target("concurrent operations (5 threads)")

        # Analyze results
        operation_times = [result[0] for result in results]
        avg_operation_time = statistics.mean(operation_times)
        max_operation_time = max(operation_times)

        assert avg_operation_time < 2000, f"Average concurrent operation time {avg_operation_time:.1f}ms too high"
        assert max_operation_time < 3000, f"Maximum concurrent operation time {max_operation_time:.1f}ms too high"

        # Verify all operations returned consistent results
        operation_data = [result[1] for result in results]
        items_counts = [data['items_found'] for data in operation_data]
        assert len(set(items_counts)) == 1, "Inconsistent results across concurrent operations"

        logger.info(f"✓ Concurrent performance: Avg {avg_operation_time:.1f}ms, Max {max_operation_time:.1f}ms")

    def test_memory_usage_validation(self):
        """
        Validate memory usage under various operations.

        Tests: Memory consumption, memory leaks, garbage collection effectiveness
        """
        logger.info("Benchmarking Memory Usage")

        if not hasattr(tracemalloc, 'start'):
            pytest.skip("Memory tracking not available")

        # Test 1: Memory usage during bulk operations
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]

        # Create large dataset
        bulk_items = []
        for i in range(200):
            item = FinishedUnitService.create_finished_unit(
                display_name=f"Memory Test Item {i:03d}",
                slug=f"memory-test-item-{i:03d}",
                unit_cost=Decimal(f"{i+1}.00"),
                inventory_count=100
            )
            bulk_items.append(item)

        after_creation_memory = tracemalloc.get_traced_memory()[0]
        creation_memory_mb = (after_creation_memory - initial_memory) / 1024 / 1024

        # Test 2: Memory usage during hierarchy operations
        assembly = FinishedGoodService.create_finished_good(
            display_name="Memory Test Assembly",
            assembly_type=AssemblyType.BULK_PACK
        )

        # Add many components
        for i in range(50):
            FinishedGoodService.add_component(assembly.id, "finished_unit", bulk_items[i].id, 1)

        # Perform memory-intensive operations
        hierarchy = CompositionService.get_assembly_hierarchy(assembly.id)
        flattened = CompositionService.flatten_assembly_components(assembly.id)
        costs = CompositionService.calculate_assembly_component_costs(assembly.id)

        final_memory = tracemalloc.get_traced_memory()[0]
        total_memory_mb = (final_memory - initial_memory) / 1024 / 1024

        tracemalloc.stop()

        # Memory usage should be reasonable for desktop application
        assert creation_memory_mb < 10, f"Item creation used {creation_memory_mb:.2f}MB (too high)"
        assert total_memory_mb < 20, f"Total memory usage {total_memory_mb:.2f}MB (too high)"

        logger.info(f"✓ Memory usage validated - Creation: {creation_memory_mb:.2f}MB, Total: {total_memory_mb:.2f}MB")

    def test_performance_regression_baseline(self):
        """
        Establish performance baseline for regression testing.

        Creates comprehensive performance profile for future comparison.
        """
        logger.info("Establishing Performance Regression Baseline")

        # Create standardized test dataset
        fixtures = HierarchyTestFixtures()
        hierarchy_data = fixtures.create_holiday_gift_hierarchy()
        holiday_collection = hierarchy_data['holiday_collection']

        # Clear caches for consistent measurements
        CompositionService.clear_hierarchy_cache()

        # Comprehensive performance baseline measurements
        baseline_metrics = {}

        # 1. FinishedUnit operations baseline
        with PerformanceBenchmark("Baseline FinishedUnit CRUD") as bench:
            item = FinishedUnitService.create_finished_unit(
                display_name="Baseline Test Item",
                unit_cost=Decimal("10.00"),
                inventory_count=100
            )
            retrieved = FinishedUnitService.get_finished_unit_by_id(item.id)
            updated = FinishedUnitService.update_finished_unit(item.id, unit_cost=Decimal("11.00"))
            deleted = FinishedUnitService.delete_finished_unit(item.id)
        baseline_metrics['finished_unit_crud_ms'] = bench.log_results()

        # 2. FinishedGood operations baseline
        with PerformanceBenchmark("Baseline FinishedGood Operations") as bench:
            assembly = FinishedGoodService.create_finished_good(
                display_name="Baseline Assembly",
                assembly_type=AssemblyType.GIFT_BOX
            )
            retrieved_assembly = FinishedGoodService.get_finished_good_by_id(assembly.id)
        baseline_metrics['finished_good_ops_ms'] = bench.log_results()

        # 3. Composition operations baseline
        with PerformanceBenchmark("Baseline Composition Operations") as bench:
            hierarchy = CompositionService.get_assembly_hierarchy(holiday_collection.id)
            flattened = CompositionService.flatten_assembly_components(holiday_collection.id)
            costs = CompositionService.calculate_assembly_component_costs(holiday_collection.id)
            stats = CompositionService.get_assembly_statistics(holiday_collection.id)
        baseline_metrics['composition_ops_ms'] = bench.log_results()

        # 4. Search and query operations baseline
        with PerformanceBenchmark("Baseline Search Operations") as bench:
            all_units = FinishedUnitService.get_all_finished_units()
            all_goods = FinishedGoodService.get_all_finished_goods()
            search_results = FinishedUnitService.search_finished_units("test")
        baseline_metrics['search_ops_ms'] = bench.log_results()

        # 5. Cache performance baseline
        CompositionService.clear_hierarchy_cache()
        with PerformanceBenchmark("Baseline Cache Miss") as bench:
            CompositionService.get_assembly_hierarchy(holiday_collection.id)
        baseline_metrics['cache_miss_ms'] = bench.log_results()

        with PerformanceBenchmark("Baseline Cache Hit") as bench:
            CompositionService.get_assembly_hierarchy(holiday_collection.id)
        baseline_metrics['cache_hit_ms'] = bench.log_results()

        # Validate all measurements are within expected ranges
        assert baseline_metrics['finished_unit_crud_ms'] < 1000
        assert baseline_metrics['finished_good_ops_ms'] < 500
        assert baseline_metrics['composition_ops_ms'] < 1000
        assert baseline_metrics['search_ops_ms'] < 500
        assert baseline_metrics['cache_miss_ms'] < 500
        assert baseline_metrics['cache_hit_ms'] < 100

        # Log comprehensive baseline for future regression testing
        logger.info("=== PERFORMANCE BASELINE ESTABLISHED ===")
        for metric, value in baseline_metrics.items():
            logger.info(f"  {metric}: {value:.2f}ms")
        logger.info("==========================================")

        # Cleanup
        fixtures.cleanup()

        return baseline_metrics


# Performance analysis utilities

def generate_performance_report(measurements: Dict[str, float]) -> str:
    """Generate comprehensive performance analysis report."""

    report = [
        "=== SERVICE PERFORMANCE BENCHMARK REPORT ===",
        "",
        f"Execution timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "PERFORMANCE TARGETS:",
        "- FinishedUnit CRUD: <2000ms",
        "- FinishedUnit inventory queries: <200ms",
        "- FinishedGood assembly creation: <30000ms",
        "- FinishedGood component queries: <500ms",
        "- Composition hierarchy traversal: <500ms (5 levels)",
        "",
        "MEASURED PERFORMANCE:",
    ]

    for metric, value in sorted(measurements.items()):
        status = "✓ PASS" if value < 1000 else "⚠ REVIEW"  # Generic threshold
        report.append(f"  {metric}: {value:.2f}ms {status}")

    report.extend([
        "",
        "=== END REPORT ===",
        ""
    ])

    return "\n".join(report)


def analyze_performance_trends(baseline: Dict[str, float], current: Dict[str, float]) -> Dict[str, Any]:
    """Analyze performance trends between baseline and current measurements."""

    analysis = {
        'total_metrics': len(baseline),
        'improved': [],
        'degraded': [],
        'stable': [],
        'new_metrics': [],
        'overall_trend': 'stable'
    }

    for metric, baseline_value in baseline.items():
        if metric in current:
            current_value = current[metric]
            change_percent = ((current_value - baseline_value) / baseline_value) * 100

            if change_percent < -5:  # >5% improvement
                analysis['improved'].append((metric, change_percent))
            elif change_percent > 10:  # >10% degradation
                analysis['degraded'].append((metric, change_percent))
            else:
                analysis['stable'].append((metric, change_percent))

    # Check for new metrics
    for metric in current:
        if metric not in baseline:
            analysis['new_metrics'].append(metric)

    # Determine overall trend
    if len(analysis['degraded']) > len(analysis['improved']):
        analysis['overall_trend'] = 'degrading'
    elif len(analysis['improved']) > len(analysis['degraded']):
        analysis['overall_trend'] = 'improving'

    return analysis