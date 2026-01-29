"""Tests for batch calculation service (F073 WP02).

Tests the batch option calculation logic that generates floor/ceil
options for each FinishedUnit based on yield characteristics.
"""
from datetime import date

import pytest

from src.models.finished_unit import FinishedUnit, YieldMode
from src.models.finished_good import FinishedGood
from src.models.composition import Composition
from src.models.event import Event
from src.models.event_finished_good import EventFinishedGood
from src.models.recipe import Recipe
from src.services.planning_service import (
    BatchOption,
    BatchOptionsResult,
    calculate_batch_options_for_fu,
    calculate_batch_options,
)


class TestBatchOptionDataclass:
    """Tests for BatchOption dataclass."""

    def test_batch_option_creation(self):
        """BatchOption can be created with all fields."""
        opt = BatchOption(
            batches=2,
            total_yield=48,
            quantity_needed=50,
            difference=-2,
            is_shortfall=True,
            is_exact_match=False,
            yield_per_batch=24,
        )
        assert opt.batches == 2
        assert opt.total_yield == 48
        assert opt.quantity_needed == 50
        assert opt.difference == -2
        assert opt.is_shortfall is True
        assert opt.is_exact_match is False
        assert opt.yield_per_batch == 24


class TestBatchOptionsResultDataclass:
    """Tests for BatchOptionsResult dataclass."""

    def test_batch_options_result_creation(self):
        """BatchOptionsResult can be created with all fields."""
        result = BatchOptionsResult(
            finished_unit_id=1,
            finished_unit_name="Chocolate Chip Cookies",
            recipe_id=10,
            recipe_name="Chocolate Chip Cookie Recipe",
            quantity_needed=50,
            yield_per_batch=24,
            yield_mode="discrete_count",
            item_unit="cookie",
            options=[],
        )
        assert result.finished_unit_id == 1
        assert result.finished_unit_name == "Chocolate Chip Cookies"
        assert result.recipe_id == 10
        assert result.yield_mode == "discrete_count"


class TestCalculateBatchOptionsForFU:
    """Tests for calculate_batch_options_for_fu()."""

    def test_exact_division_returns_one_option(self, test_db):
        """When quantity exactly divisible by yield, only one option returned."""
        # Setup: Recipe and FU with yield 24/batch
        recipe = Recipe(name="Cookie Recipe", category="Cookies")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        # Need 48 cookies - exactly 2 batches
        options = calculate_batch_options_for_fu(fu, 48)

        assert len(options) == 1
        assert options[0].batches == 2
        assert options[0].total_yield == 48
        assert options[0].is_exact_match is True
        assert options[0].is_shortfall is False
        assert options[0].difference == 0

    def test_floor_ceil_options_with_shortfall(self, test_db):
        """Non-exact division returns floor (shortfall) and ceil options."""
        recipe = Recipe(name="Cookie Recipe", category="Cookies")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        # Need 50 cookies - floor=2 (48, shortfall), ceil=3 (72, surplus)
        options = calculate_batch_options_for_fu(fu, 50)

        assert len(options) == 2

        # Floor option
        floor_opt = options[0]
        assert floor_opt.batches == 2
        assert floor_opt.total_yield == 48
        assert floor_opt.difference == -2
        assert floor_opt.is_shortfall is True
        assert floor_opt.is_exact_match is False

        # Ceil option
        ceil_opt = options[1]
        assert ceil_opt.batches == 3
        assert ceil_opt.total_yield == 72
        assert ceil_opt.difference == 22
        assert ceil_opt.is_shortfall is False
        assert ceil_opt.is_exact_match is False

    def test_zero_quantity_returns_empty(self, test_db):
        """Zero quantity needed returns empty list."""
        recipe = Recipe(name="Cookie Recipe", category="Cookies")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        options = calculate_batch_options_for_fu(fu, 0)
        assert options == []

    def test_negative_quantity_returns_empty(self, test_db):
        """Negative quantity returns empty list."""
        recipe = Recipe(name="Cookie Recipe", category="Cookies")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        options = calculate_batch_options_for_fu(fu, -5)
        assert options == []

    def test_batch_portion_mode_yield_is_one(self, test_db):
        """BATCH_PORTION mode treats each batch as one portion."""
        recipe = Recipe(name="Cake Recipe", category="Cakes")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug="cake",
            display_name="Cake",
            yield_mode=YieldMode.BATCH_PORTION,
            batch_percentage=100,  # 100% = 1 cake per batch
            items_per_batch=None,  # Not used for BATCH_PORTION
            item_unit="cake",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        # Need 3 cakes - exactly 3 batches (1 cake per batch)
        options = calculate_batch_options_for_fu(fu, 3)

        assert len(options) == 1  # Exact match
        assert options[0].batches == 3
        assert options[0].yield_per_batch == 1
        assert options[0].total_yield == 3
        assert options[0].is_exact_match is True

    def test_floor_zero_only_returns_ceil(self, test_db):
        """When floor rounds to 0, only ceil option returned."""
        recipe = Recipe(name="Cookie Recipe", category="Cookies")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        # Need 5 cookies - floor=0 (skipped), ceil=1 (24)
        options = calculate_batch_options_for_fu(fu, 5)

        assert len(options) == 1
        assert options[0].batches == 1
        assert options[0].total_yield == 24
        assert options[0].is_shortfall is False  # Ceil never shortfalls

    def test_zero_yield_returns_empty(self):
        """Zero items_per_batch returns empty list (tested without DB due to CHECK constraint)."""
        # Note: Database has CHECK constraint preventing items_per_batch=0
        # This tests the calculation logic directly with a mock-like object
        from unittest.mock import Mock

        fu = Mock()
        fu.calculate_batches_needed.return_value = 0  # Simulates zero/invalid yield
        fu.items_per_batch = 0
        fu.yield_mode = YieldMode.DISCRETE_COUNT

        # When calculate_batches_needed returns 0, we should get empty options
        options = calculate_batch_options_for_fu(fu, 50)
        assert options == []

    def test_none_yield_returns_empty(self, test_db):
        """None items_per_batch returns empty list."""
        recipe = Recipe(name="Cookie Recipe", category="Cookies")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=None,  # Invalid for DISCRETE_COUNT
            item_unit="cookie",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        options = calculate_batch_options_for_fu(fu, 50)
        assert options == []

    def test_large_quantity_calculation(self, test_db):
        """Large quantities calculate correctly."""
        recipe = Recipe(name="Cookie Recipe", category="Cookies")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        # Need 1000 cookies - floor=41 (984), ceil=42 (1008)
        options = calculate_batch_options_for_fu(fu, 1000)

        assert len(options) == 2
        assert options[0].batches == 41
        assert options[0].total_yield == 984
        assert options[0].is_shortfall is True
        assert options[1].batches == 42
        assert options[1].total_yield == 1008


class TestCalculateBatchOptions:
    """Tests for calculate_batch_options() event-level function."""

    def test_returns_results_for_all_fus(self, test_db):
        """Returns BatchOptionsResult for each FU in event."""
        # Setup recipes
        recipe1 = Recipe(name="Cookie Recipe", category="Cookies")
        recipe2 = Recipe(name="Cake Recipe", category="Cakes")
        test_db.add_all([recipe1, recipe2])
        test_db.flush()

        # Setup FUs
        fu1 = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
            recipe_id=recipe1.id,
        )
        fu2 = FinishedUnit(
            slug="cake",
            display_name="Cake",
            yield_mode=YieldMode.BATCH_PORTION,
            batch_percentage=100,
            item_unit="cake",
            recipe_id=recipe2.id,
        )
        test_db.add_all([fu1, fu2])
        test_db.flush()

        # Setup FGs (atomic, one FU each)
        fg1 = FinishedGood(
            slug="cookies-fg",
            display_name="Cookies FG",
        )
        fg2 = FinishedGood(
            slug="cake-fg",
            display_name="Cake FG",
        )
        test_db.add_all([fg1, fg2])
        test_db.flush()

        # Add FU components to FGs
        comp1 = Composition(
            assembly_id=fg1.id,
            finished_unit_id=fu1.id,
            component_quantity=1,
        )
        comp2 = Composition(
            assembly_id=fg2.id,
            finished_unit_id=fu2.id,
            component_quantity=1,
        )
        test_db.add_all([comp1, comp2])
        test_db.flush()

        # Setup event with both FGs
        event = Event(name="Holiday Party", event_date=date(2024, 12, 25), year=2024)
        test_db.add(event)
        test_db.flush()

        efg1 = EventFinishedGood(
            event_id=event.id,
            finished_good_id=fg1.id,
            quantity=50,
        )
        efg2 = EventFinishedGood(
            event_id=event.id,
            finished_good_id=fg2.id,
            quantity=3,
        )
        test_db.add_all([efg1, efg2])
        test_db.flush()

        # Calculate batch options
        results = calculate_batch_options(event.id, session=test_db)

        assert len(results) == 2

        # Check first result (cookies)
        cookies_result = next(r for r in results if r.finished_unit_id == fu1.id)
        assert cookies_result.finished_unit_name == "Cookies"
        assert cookies_result.recipe_name == "Cookie Recipe"
        assert cookies_result.quantity_needed == 50
        assert cookies_result.yield_per_batch == 24
        assert cookies_result.yield_mode == "discrete_count"
        assert len(cookies_result.options) == 2  # Floor and ceil

        # Check second result (cake)
        cake_result = next(r for r in results if r.finished_unit_id == fu2.id)
        assert cake_result.finished_unit_name == "Cake"
        assert cake_result.recipe_name == "Cake Recipe"
        assert cake_result.quantity_needed == 3
        assert cake_result.yield_per_batch == 1  # BATCH_PORTION
        assert len(cake_result.options) == 1  # Exact match

    def test_empty_event_returns_empty_list(self, test_db):
        """Event with no FGs returns empty list."""
        event = Event(name="Empty Event", event_date=date(2024, 12, 25), year=2024)
        test_db.add(event)
        test_db.flush()

        results = calculate_batch_options(event.id, session=test_db)
        assert results == []

    def test_uses_f072_decomposition_for_bundles(self, test_db):
        """Verifies F072 decomposition is used for bundle expansion."""
        # Setup recipe and FU
        recipe = Recipe(name="Cookie Recipe", category="Cookies")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug="cookies",
            display_name="Cookies",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="cookie",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        # Setup atomic FG
        atomic_fg = FinishedGood(
            slug="cookies-fg",
            display_name="Cookies FG",
        )
        test_db.add(atomic_fg)
        test_db.flush()

        atomic_comp = Composition(
            assembly_id=atomic_fg.id,
            finished_unit_id=fu.id,
            component_quantity=1,
        )
        test_db.add(atomic_comp)
        test_db.flush()

        # Setup bundle FG containing atomic FG with quantity 2
        bundle_fg = FinishedGood(
            slug="cookie-bundle",
            display_name="Cookie Bundle",
        )
        test_db.add(bundle_fg)
        test_db.flush()

        bundle_comp = Composition(
            assembly_id=bundle_fg.id,
            finished_good_id=atomic_fg.id,
            component_quantity=2,  # Bundle contains 2 atomic FGs
        )
        test_db.add(bundle_comp)
        test_db.flush()

        # Setup event with bundle quantity 3
        event = Event(name="Party", event_date=date(2024, 12, 25), year=2024)
        test_db.add(event)
        test_db.flush()

        efg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=bundle_fg.id,
            quantity=3,  # 3 bundles * 2 atomic = 6 FUs needed
        )
        test_db.add(efg)
        test_db.flush()

        # Calculate batch options
        results = calculate_batch_options(event.id, session=test_db)

        assert len(results) == 1
        result = results[0]
        assert result.quantity_needed == 6  # 3 bundles * 2 = 6 cookies
        assert result.finished_unit_name == "Cookies"

    def test_session_parameter_passed_through(self, test_db):
        """Session parameter correctly passed to F072 decomposition."""
        # This test verifies no session errors when using passed session
        event = Event(name="Test Event", event_date=date(2024, 12, 25), year=2024)
        test_db.add(event)
        test_db.flush()

        # Should not raise any session-related errors
        results = calculate_batch_options(event.id, session=test_db)
        assert results == []  # Empty event, but no errors


class TestBatchCalculationIntegration:
    """Integration tests for full batch calculation workflow."""

    def test_multiple_fus_same_recipe_preserved(self, test_db):
        """Multiple FUs from same recipe are preserved separately."""
        # Setup one recipe with two FUs (different yields)
        # F083: Multiple sizes can share same item_unit and yield_type
        recipe = Recipe(name="Cake Recipe", category="Cakes")
        test_db.add(recipe)
        test_db.flush()

        fu_large = FinishedUnit(
            slug="large-cake",
            display_name="Large Cake",
            yield_mode=YieldMode.BATCH_PORTION,
            batch_percentage=100,  # 1 cake per batch
            item_unit="large cake",  # Unique item_unit for this yield
            recipe_id=recipe.id,
        )
        fu_small = FinishedUnit(
            slug="small-cake",
            display_name="Small Cake",
            yield_mode=YieldMode.BATCH_PORTION,
            batch_percentage=25,  # 4 small cakes per batch
            item_unit="small cake",  # Different item_unit to satisfy unique constraint
            recipe_id=recipe.id,
        )
        test_db.add_all([fu_large, fu_small])
        test_db.flush()

        # Setup atomic FGs
        fg_large = FinishedGood(slug="large-cake-fg", display_name="Large Cake FG")
        fg_small = FinishedGood(slug="small-cake-fg", display_name="Small Cake FG")
        test_db.add_all([fg_large, fg_small])
        test_db.flush()

        comp_large = Composition(assembly_id=fg_large.id, finished_unit_id=fu_large.id, component_quantity=1)
        comp_small = Composition(assembly_id=fg_small.id, finished_unit_id=fu_small.id, component_quantity=1)
        test_db.add_all([comp_large, comp_small])
        test_db.flush()

        # Event with both FUs
        event = Event(name="Wedding", event_date=date(2024, 6, 15), year=2024)
        test_db.add(event)
        test_db.flush()

        efg_large = EventFinishedGood(event_id=event.id, finished_good_id=fg_large.id, quantity=2)
        efg_small = EventFinishedGood(event_id=event.id, finished_good_id=fg_small.id, quantity=10)
        test_db.add_all([efg_large, efg_small])
        test_db.flush()

        results = calculate_batch_options(event.id, session=test_db)

        assert len(results) == 2

        large_result = next(r for r in results if r.finished_unit_id == fu_large.id)
        small_result = next(r for r in results if r.finished_unit_id == fu_small.id)

        # Large cakes: 2 needed, 1 per batch = exactly 2 batches
        assert large_result.quantity_needed == 2
        assert len(large_result.options) == 1
        assert large_result.options[0].batches == 2

        # Small cakes: 10 needed, batch_percentage=25 means 4 cakes use 1 batch
        # calculate_batches_needed with BATCH_PORTION: quantity * (percentage/100)
        # 10 * 0.25 = 2.5 batches needed
        assert small_result.quantity_needed == 10
        assert len(small_result.options) == 2
        assert small_result.options[0].batches == 2  # floor
        assert small_result.options[1].batches == 3  # ceil
