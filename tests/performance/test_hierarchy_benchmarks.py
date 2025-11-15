"""
Performance benchmarks for hierarchy operations.

Validates that hierarchy operations meet performance targets with varying
data sizes and complexity levels. Provides regression testing for performance
characteristics and optimization recommendations.

Performance Targets:
- Hierarchy traversal: <500ms for 5-level depth
- Circular reference validation: <200ms for large datasets
- Cost calculation: <400ms for complex nested assemblies
- Hierarchy flattening: <300ms for multi-level structures
- Cache operations: <50ms for cache hits
"""

import pytest
import logging
import time
import statistics
from decimal import Decimal
from typing import List, Dict, Any, Tuple
import gc
import sys

from src.services.finished_good_service import FinishedGoodService
from src.services.composition_service import CompositionService
from src.services.finished_unit_service import FinishedUnitService
from src.models import FinishedGood, FinishedUnit, AssemblyType
from src.database import get_db_session, session_scope

from ..fixtures.hierarchy_fixtures import HierarchyTestFixtures

logger = logging.getLogger(__name__)


class PerformanceTimer:
    """Context manager for measuring execution time."""

    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        gc.collect()  # Clean up before measurement
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.start_time is None or self.end_time is None:
            raise ValueError("Timer not properly started/stopped")
        return (self.end_time - self.start_time) * 1000

    def assert_within_target(self, target_ms: float, description: str = ""):
        """Assert that elapsed time is within target."""
        elapsed = self.elapsed_ms
        assert elapsed <= target_ms, (
            f"{self.name} {description} took {elapsed:.1f}ms "
            f"(target: <{target_ms}ms)"
        )
        logger.info(f"✓ {self.name} {description}: {elapsed:.1f}ms (target: <{target_ms}ms)")


class TestHierarchyPerformanceBenchmarks:
    """Performance benchmarks for hierarchy operations."""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up clean test environment for each benchmark."""
        # Clear cache before each test
        CompositionService.clear_hierarchy_cache()

        # Force garbage collection for consistent measurements
        gc.collect()

        yield

        # Cleanup after test
        with session_scope() as session:
            from src.models import Composition
            session.query(Composition).delete()
            session.query(FinishedGood).delete()
            session.query(FinishedUnit).delete()
            session.commit()

    def test_hierarchy_traversal_performance_by_depth(self):
        """
        Benchmark hierarchy traversal performance with varying depths.

        Target: <500ms for 5-level depth
        Tests depths 1-5 to identify performance scaling characteristics.
        """
        fixtures = HierarchyTestFixtures()

        # Test different depths
        depth_results = {}

        for depth in range(1, 6):
            # Create hierarchy with specified depth
            hierarchy_data = fixtures.create_performance_test_hierarchy(depth=depth, breadth=3)
            root_assembly = hierarchy_data['root_assembly']

            # Benchmark hierarchy traversal
            with PerformanceTimer(f"Hierarchy traversal depth {depth}") as timer:
                hierarchy = CompositionService.get_assembly_hierarchy(root_assembly.id)

            depth_results[depth] = timer.elapsed_ms

            # Validate structure
            assert hierarchy['assembly_id'] == root_assembly.id

            # Performance assertion - scale based on depth
            max_time_ms = min(500, 100 * depth)  # Allow more time for deeper hierarchies, max 500ms
            timer.assert_within_target(max_time_ms, f"for depth {depth}")

        # Check that performance doesn't degrade exponentially
        if len(depth_results) >= 3:
            # Compare depth 3 vs depth 5
            depth3_time = depth_results[3]
            depth5_time = depth_results[5]

            # Depth 5 should not be more than 3x slower than depth 3
            assert depth5_time <= depth3_time * 3.0, (
                f"Performance degrades too much with depth: "
                f"depth 3: {depth3_time:.1f}ms, depth 5: {depth5_time:.1f}ms"
            )

        logger.info(f"Hierarchy traversal scaling: {depth_results}")

    def test_circular_reference_validation_large_datasets(self):
        """
        Benchmark circular reference validation with large datasets.

        Target: <200ms for large datasets
        Tests validation performance with varying hierarchy complexity.
        """
        fixtures = HierarchyTestFixtures()

        # Create complex hierarchy for testing
        hierarchy_data = fixtures.create_performance_test_hierarchy(depth=4, breadth=4)
        root_assembly = hierarchy_data['root_assembly']

        # Create test assembly to validate against
        test_assembly = FinishedGoodService.create_finished_good(
            "Circular Reference Test Assembly",
            AssemblyType.BULK_PACK
        )
        fixtures.created_finished_goods.append(test_assembly.id)

        # Benchmark multiple validation calls
        validation_times = []

        for i in range(10):  # Multiple runs for statistical reliability
            with PerformanceTimer(f"Circular reference validation run {i+1}") as timer:
                is_valid = CompositionService.validate_no_circular_reference(
                    root_assembly.id, test_assembly.id
                )

            validation_times.append(timer.elapsed_ms)
            assert is_valid is True  # Should be valid

        # Statistical analysis
        avg_time = statistics.mean(validation_times)
        max_time = max(validation_times)

        # Performance assertions
        assert avg_time <= 200, f"Average validation time {avg_time:.1f}ms exceeds target 200ms"
        assert max_time <= 300, f"Maximum validation time {max_time:.1f}ms too high"

        logger.info(f"Circular reference validation - Avg: {avg_time:.1f}ms, Max: {max_time:.1f}ms")

    def test_cost_calculation_complex_assemblies(self):
        """
        Benchmark cost calculation for complex nested assemblies.

        Target: <400ms for complex nested assemblies
        Tests cost aggregation across multiple hierarchy levels.
        """
        fixtures = HierarchyTestFixtures()

        # Create complex hierarchy with realistic cost structure
        hierarchy_data = fixtures.create_holiday_gift_hierarchy()
        holiday_collection = hierarchy_data['holiday_collection']

        # Benchmark cost calculation
        with PerformanceTimer("Complex assembly cost calculation") as timer:
            cost_breakdown = CompositionService.calculate_assembly_component_costs(
                holiday_collection.id
            )

        timer.assert_within_target(400, "for complex assembly")

        # Validate results structure
        assert 'total_assembly_cost' in cost_breakdown
        assert 'finished_unit_costs' in cost_breakdown
        assert 'finished_good_costs' in cost_breakdown
        assert cost_breakdown['total_assembly_cost'] > 0

        logger.info(f"Cost calculation completed: {len(cost_breakdown['finished_unit_costs'])} units, "
                   f"{len(cost_breakdown['finished_good_costs'])} assemblies")

    def test_hierarchy_flattening_performance(self):
        """
        Benchmark hierarchy flattening operations.

        Target: <300ms for multi-level structures
        Tests bill-of-materials generation performance.
        """
        fixtures = HierarchyTestFixtures()

        # Create multi-level hierarchy
        hierarchy_data = fixtures.create_performance_test_hierarchy(depth=4, breadth=5)
        root_assembly = hierarchy_data['root_assembly']

        # Benchmark flattening operation
        with PerformanceTimer("Hierarchy flattening") as timer:
            flattened = CompositionService.flatten_assembly_components(root_assembly.id)

        timer.assert_within_target(300, "for multi-level structure")

        # Validate results
        assert len(flattened) > 0
        assert all('component_id' in comp for comp in flattened)
        assert all('total_quantity' in comp for comp in flattened)
        assert all('total_cost' in comp for comp in flattened)

        logger.info(f"Flattened hierarchy: {len(flattened)} unique components")

    def test_cache_performance_and_hit_rates(self):
        """
        Benchmark cache operations and measure hit rates.

        Target: <50ms for cache hits
        Tests cache effectiveness and performance impact.
        """
        fixtures = HierarchyTestFixtures()

        # Create test hierarchy
        hierarchy_data = fixtures.create_holiday_gift_hierarchy()
        holiday_collection = hierarchy_data['holiday_collection']

        # Clear cache and get baseline stats
        CompositionService.clear_hierarchy_cache()
        initial_stats = CompositionService.get_cache_statistics()
        assert initial_stats['cache_size'] == 0

        # First call - cache miss
        with PerformanceTimer("First call (cache miss)") as timer_miss:
            hierarchy_1 = CompositionService.get_assembly_hierarchy(holiday_collection.id)

        # Verify cache population
        stats_after_first = CompositionService.get_cache_statistics()
        assert stats_after_first['cache_size'] == 1

        # Second call - cache hit
        with PerformanceTimer("Second call (cache hit)") as timer_hit:
            hierarchy_2 = CompositionService.get_assembly_hierarchy(holiday_collection.id)

        # Validate cache hit
        assert hierarchy_1 == hierarchy_2
        timer_hit.assert_within_target(50, "for cache hit")

        # Cache hit should be significantly faster
        speedup_ratio = timer_miss.elapsed_ms / timer_hit.elapsed_ms
        assert speedup_ratio >= 2.0, f"Cache speedup ratio {speedup_ratio:.1f}x is too low"

        # Test multiple cache hits for consistency
        cache_hit_times = []
        for i in range(5):
            with PerformanceTimer(f"Cache hit {i+1}") as timer:
                CompositionService.get_assembly_hierarchy(holiday_collection.id)
            cache_hit_times.append(timer.elapsed_ms)

        avg_cache_time = statistics.mean(cache_hit_times)
        assert avg_cache_time <= 50, f"Average cache hit time {avg_cache_time:.1f}ms exceeds target"

        logger.info(f"Cache performance - Miss: {timer_miss.elapsed_ms:.1f}ms, "
                   f"Hit: {timer_hit.elapsed_ms:.1f}ms, Speedup: {speedup_ratio:.1f}x")

    def test_bulk_operations_performance(self):
        """
        Benchmark bulk operations on compositions.

        Target: <1s for up to 100 compositions
        Tests batch creation and management performance.
        """
        fixtures = HierarchyTestFixtures()

        # Create base items
        base_items = []
        for i in range(50):
            item = fixtures.create_finished_unit(
                f"Bulk Test Item {i:02d}",
                Decimal(f"{i+1}.00"),
                inventory_count=100
            )
            base_items.append(item)

        # Create assembly for bulk operations
        assembly = FinishedGoodService.create_finished_good(
            "Bulk Operations Test Assembly",
            AssemblyType.BULK_PACK
        )
        fixtures.created_finished_goods.append(assembly.id)

        # Prepare bulk composition data
        compositions_data = []
        for i, item in enumerate(base_items):
            compositions_data.append({
                'assembly_id': assembly.id,
                'component_type': 'finished_unit',
                'component_id': item.id,
                'quantity': i + 1,
                'notes': f'Bulk test component {i+1}',
                'sort_order': i
            })

        # Benchmark bulk creation
        with PerformanceTimer("Bulk composition creation") as timer:
            created_compositions = CompositionService.bulk_create_compositions(compositions_data)

        timer.assert_within_target(1000, f"for {len(compositions_data)} compositions")

        # Validate results
        assert len(created_compositions) == len(compositions_data)

        # Benchmark bulk retrieval
        with PerformanceTimer("Bulk composition retrieval") as timer:
            retrieved_compositions = CompositionService.get_assembly_components(assembly.id)

        timer.assert_within_target(200, "for bulk retrieval")
        assert len(retrieved_compositions) == len(compositions_data)

        logger.info(f"Bulk operations: created {len(created_compositions)} compositions")

    def test_memory_usage_large_hierarchies(self):
        """
        Monitor memory usage during large hierarchy operations.

        Validates that memory usage remains reasonable for realistic scenarios.
        """
        if not hasattr(sys, 'getsizeof'):
            pytest.skip("Memory monitoring not available")

        fixtures = HierarchyTestFixtures()

        # Get baseline memory
        gc.collect()

        # Create large hierarchy
        hierarchy_data = fixtures.create_performance_test_hierarchy(depth=5, breadth=6)
        root_assembly = hierarchy_data['root_assembly']

        # Measure memory usage of hierarchy operations
        gc.collect()

        # Test hierarchy traversal memory
        hierarchy = CompositionService.get_assembly_hierarchy(root_assembly.id)
        hierarchy_size = sys.getsizeof(hierarchy)

        # Test flattened components memory
        flattened = CompositionService.flatten_assembly_components(root_assembly.id)
        flattened_size = sum(sys.getsizeof(comp) for comp in flattened)

        # Memory usage should be reasonable (rough guidelines)
        assert hierarchy_size < 1024 * 1024, f"Hierarchy size {hierarchy_size} bytes too large"
        assert flattened_size < 512 * 1024, f"Flattened size {flattened_size} bytes too large"

        logger.info(f"Memory usage - Hierarchy: {hierarchy_size} bytes, "
                   f"Flattened: {flattened_size} bytes")

    def test_concurrent_operations_performance(self):
        """
        Test performance under concurrent access scenarios.

        Simulates multiple operations happening simultaneously to identify
        potential bottlenecks in real-world usage.
        """
        fixtures = HierarchyTestFixtures()

        # Create test hierarchy
        hierarchy_data = fixtures.create_holiday_gift_hierarchy()
        holiday_collection = hierarchy_data['holiday_collection']

        # Clear cache to start fresh
        CompositionService.clear_hierarchy_cache()

        # Simulate concurrent read operations
        operation_times = []

        for i in range(10):
            # Mix of operations that might happen concurrently
            operations = [
                lambda: CompositionService.get_assembly_hierarchy(holiday_collection.id),
                lambda: CompositionService.flatten_assembly_components(holiday_collection.id),
                lambda: CompositionService.calculate_assembly_component_costs(holiday_collection.id),
                lambda: CompositionService.get_assembly_statistics(holiday_collection.id)
            ]

            with PerformanceTimer(f"Concurrent simulation {i+1}") as timer:
                for op in operations:
                    op()

            operation_times.append(timer.elapsed_ms)

        # Analyze performance consistency
        avg_time = statistics.mean(operation_times)
        std_dev = statistics.stdev(operation_times) if len(operation_times) > 1 else 0
        max_time = max(operation_times)

        # Performance should be consistent
        assert avg_time <= 2000, f"Average concurrent operations time {avg_time:.1f}ms too high"
        assert max_time <= 3000, f"Maximum concurrent operations time {max_time:.1f}ms too high"
        assert std_dev <= avg_time * 0.5, f"Performance too inconsistent (std dev: {std_dev:.1f}ms)"

        logger.info(f"Concurrent performance - Avg: {avg_time:.1f}ms, "
                   f"Max: {max_time:.1f}ms, Std Dev: {std_dev:.1f}ms")

    def test_performance_regression_baseline(self):
        """
        Establish performance baseline for regression testing.

        Creates standardized test scenario and records performance metrics
        for future comparison.
        """
        fixtures = HierarchyTestFixtures()

        # Create standardized test hierarchy
        hierarchy_data = fixtures.create_holiday_gift_hierarchy()
        holiday_collection = hierarchy_data['holiday_collection']

        # Clear cache for consistent measurements
        CompositionService.clear_hierarchy_cache()

        # Measure key operations
        measurements = {}

        # 1. Hierarchy traversal
        with PerformanceTimer("Baseline hierarchy traversal") as timer:
            CompositionService.get_assembly_hierarchy(holiday_collection.id)
        measurements['hierarchy_traversal_ms'] = timer.elapsed_ms

        # 2. Component flattening
        with PerformanceTimer("Baseline component flattening") as timer:
            CompositionService.flatten_assembly_components(holiday_collection.id)
        measurements['component_flattening_ms'] = timer.elapsed_ms

        # 3. Cost calculation
        with PerformanceTimer("Baseline cost calculation") as timer:
            CompositionService.calculate_assembly_component_costs(holiday_collection.id)
        measurements['cost_calculation_ms'] = timer.elapsed_ms

        # 4. Cache hit performance
        with PerformanceTimer("Baseline cache hit") as timer:
            CompositionService.get_assembly_hierarchy(holiday_collection.id)  # Should be cached
        measurements['cache_hit_ms'] = timer.elapsed_ms

        # 5. Statistics generation
        with PerformanceTimer("Baseline statistics") as timer:
            CompositionService.get_assembly_statistics(holiday_collection.id)
        measurements['statistics_ms'] = timer.elapsed_ms

        # Validate all measurements are within acceptable ranges
        assert measurements['hierarchy_traversal_ms'] <= 500
        assert measurements['component_flattening_ms'] <= 300
        assert measurements['cost_calculation_ms'] <= 400
        assert measurements['cache_hit_ms'] <= 50
        assert measurements['statistics_ms'] <= 200

        # Log baseline metrics for regression comparison
        logger.info("Performance baseline established:")
        for metric, value in measurements.items():
            logger.info(f"  {metric}: {value:.1f}ms")

        return measurements


# Performance analysis utilities

def analyze_performance_trends(measurements: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    Analyze performance trends across multiple measurement sets.

    Args:
        measurements: List of measurement dictionaries

    Returns:
        Analysis results with trends and recommendations
    """
    if not measurements:
        return {'error': 'No measurements provided'}

    analysis = {
        'sample_size': len(measurements),
        'metrics': {},
        'recommendations': []
    }

    # Analyze each metric
    metric_names = set()
    for measurement in measurements:
        metric_names.update(measurement.keys())

    for metric in metric_names:
        values = [m.get(metric, 0) for m in measurements if metric in m]
        if values:
            analysis['metrics'][metric] = {
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                'min': min(values),
                'max': max(values),
                'coefficient_of_variation': statistics.stdev(values) / statistics.mean(values) if len(values) > 1 and statistics.mean(values) > 0 else 0
            }

    # Generate recommendations
    for metric, stats in analysis['metrics'].items():
        cv = stats['coefficient_of_variation']
        if cv > 0.3:  # High variability
            analysis['recommendations'].append(
                f"{metric} shows high variability (CV: {cv:.2f}) - investigate inconsistent performance"
            )

        if stats['max'] > stats['mean'] * 2:  # Outliers
            analysis['recommendations'].append(
                f"{metric} has significant outliers (max: {stats['max']:.1f}ms, mean: {stats['mean']:.1f}ms)"
            )

    return analysis