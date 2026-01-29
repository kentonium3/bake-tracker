"""
Unit tests for batch calculation service (Feature 039).

Tests cover:
- calculate_batches() with various inputs including edge cases
- calculate_waste() for waste units and percentage
- create_batch_result() convenience function
- explode_bundle_requirements() with simple and nested bundles
- aggregate_by_recipe() grouping by recipe

Per WP02 specification:
- Batch calculations NEVER result in production shortfall
- total_yield always >= units_needed (100% accuracy)
"""

import pytest

from src.services.planning import (
    calculate_batches,
    calculate_waste,
    create_batch_result,
    explode_bundle_requirements,
    aggregate_by_recipe,
    RecipeBatchResult,
)
from src.models import (
    Recipe,
    FinishedUnit,
    FinishedGood,
    Composition,
)
from src.models.assembly_type import AssemblyType


class TestCalculateBatches:
    """Tests for calculate_batches() function."""

    def test_exact_fit_single_batch(self):
        """Test exact fit: 48 needed, 48 yield = 1 batch."""
        result = calculate_batches(48, 48)
        assert result == 1

    def test_exact_fit_multiple_batches(self):
        """Test exact fit with multiple batches: 96 needed, 48 yield = 2."""
        result = calculate_batches(96, 48)
        assert result == 2

    def test_round_up_one_extra(self):
        """Test round up: 49 needed, 48 yield = 2 batches."""
        result = calculate_batches(49, 48)
        assert result == 2

    def test_round_up_large_quantity(self):
        """Test large quantity: 300 needed, 48 yield = 7 batches (ceil(300/48))."""
        result = calculate_batches(300, 48)
        assert result == 7
        # Verify no shortfall
        total_yield = result * 48
        assert total_yield >= 300

    def test_edge_case_one_unit_needed(self):
        """Test edge: 1 needed, 48 yield = 1 batch."""
        result = calculate_batches(1, 48)
        assert result == 1

    def test_edge_case_zero_units_needed(self):
        """Test edge: 0 needed = 0 batches."""
        result = calculate_batches(0, 48)
        assert result == 0

    def test_small_yield_per_batch(self):
        """Test with small yield per batch."""
        result = calculate_batches(10, 3)
        assert result == 4  # ceil(10/3) = 4
        assert result * 3 >= 10

    def test_yield_equals_one(self):
        """Test with yield of 1 per batch."""
        result = calculate_batches(5, 1)
        assert result == 5

    def test_invalid_zero_yield_raises(self):
        """Test that zero yield raises ValueError."""
        with pytest.raises(ValueError, match="yield_per_batch must be greater than 0"):
            calculate_batches(10, 0)

    def test_invalid_negative_yield_raises(self):
        """Test that negative yield raises ValueError."""
        with pytest.raises(ValueError, match="yield_per_batch must be greater than 0"):
            calculate_batches(10, -1)

    def test_never_produces_shortfall(self):
        """Property test: result * yield_per_batch >= units_needed for all valid inputs."""
        test_cases = [
            (1, 1),
            (1, 100),
            (99, 100),
            (100, 100),
            (101, 100),
            (333, 48),
            (1000, 12),
        ]
        for units_needed, yield_per_batch in test_cases:
            batches = calculate_batches(units_needed, yield_per_batch)
            total_yield = batches * yield_per_batch
            assert total_yield >= units_needed, (
                f"Shortfall detected: {units_needed} needed, "
                f"{total_yield} produced ({batches} batches * {yield_per_batch})"
            )


class TestCalculateWaste:
    """Tests for calculate_waste() function."""

    def test_zero_waste_exact_fit(self):
        """Test zero waste: 48 needed, 1 batch, 48 yield = (0, 0.0%)."""
        waste_units, waste_percent = calculate_waste(48, 1, 48)
        assert waste_units == 0
        assert waste_percent == 0.0

    def test_some_waste(self):
        """Test some waste: 49 needed, 2 batches, 48 yield."""
        waste_units, waste_percent = calculate_waste(49, 2, 48)
        # 2 * 48 = 96 total, 96 - 49 = 47 waste
        assert waste_units == 47
        # 47 / 96 * 100 = 48.958...%
        assert abs(waste_percent - 48.958333) < 0.01

    def test_nearly_full_waste(self):
        """Test high waste: 1 needed, 1 batch, 48 yield."""
        waste_units, waste_percent = calculate_waste(1, 1, 48)
        assert waste_units == 47
        # 47 / 48 * 100 = 97.916...%
        assert abs(waste_percent - 97.916666) < 0.01

    def test_zero_batches_zero_waste(self):
        """Test zero batches produces zero waste."""
        waste_units, waste_percent = calculate_waste(0, 0, 48)
        assert waste_units == 0
        assert waste_percent == 0.0

    def test_waste_never_exceeds_total(self):
        """Verify waste_units <= total_yield for all cases."""
        test_cases = [
            (1, 1, 48),
            (48, 1, 48),
            (49, 2, 48),
            (100, 3, 48),
        ]
        for units_needed, batches, yield_per_batch in test_cases:
            waste_units, _ = calculate_waste(units_needed, batches, yield_per_batch)
            total_yield = batches * yield_per_batch
            assert waste_units <= total_yield
            assert waste_units >= 0


class TestCreateBatchResult:
    """Tests for create_batch_result() convenience function."""

    def test_creates_complete_result(self):
        """Test that all fields are populated correctly."""
        result = create_batch_result(
            recipe_id=1,
            recipe_name="Chocolate Chip Cookies",
            units_needed=100,
            yield_per_batch=48,
        )

        assert isinstance(result, RecipeBatchResult)
        assert result.recipe_id == 1
        assert result.recipe_name == "Chocolate Chip Cookies"
        assert result.units_needed == 100
        assert result.batches == 3  # ceil(100/48)
        assert result.yield_per_batch == 48
        assert result.total_yield == 144  # 3 * 48
        assert result.waste_units == 44  # 144 - 100
        assert result.total_yield >= result.units_needed

    def test_exact_fit_result(self):
        """Test exact fit produces zero waste."""
        result = create_batch_result(
            recipe_id=2,
            recipe_name="Brownies",
            units_needed=24,
            yield_per_batch=24,
        )

        assert result.batches == 1
        assert result.total_yield == 24
        assert result.waste_units == 0
        assert result.waste_percent == 0.0


class TestExplodeBundleRequirements:
    """Tests for explode_bundle_requirements() function."""

    @pytest.fixture
    def simple_bundle_setup(self, test_db):
        """Create a simple bundle with two FinishedUnit components."""
        session = test_db()

        # Create recipes (F056: yield fields removed from Recipe model)
        cookie_recipe = Recipe(
            name="Chocolate Chip Cookies",
            category="Cookies",
        )
        brownie_recipe = Recipe(
            name="Fudge Brownies",
            category="Brownies",
        )
        session.add_all([cookie_recipe, brownie_recipe])
        session.flush()

        # Create FinishedUnits (F056: items_per_batch/item_unit hold yield data)
        cookie_unit = FinishedUnit(
            display_name="Chocolate Chip Cookie",
            slug="chocolate-chip-cookie",
            recipe_id=cookie_recipe.id,
            items_per_batch=48,  # Was Recipe.yield_quantity
            item_unit="cookies",  # Was Recipe.yield_unit
        )
        brownie_unit = FinishedUnit(
            display_name="Fudge Brownie",
            slug="fudge-brownie",
            recipe_id=brownie_recipe.id,
            items_per_batch=24,  # Was Recipe.yield_quantity
            item_unit="brownies",  # Was Recipe.yield_unit
        )
        session.add_all([cookie_unit, brownie_unit])
        session.flush()

        # Create FinishedGood (bundle)
        gift_bag = FinishedGood(
            display_name="Holiday Gift Bag",
            slug="holiday-gift-bag",
            assembly_type=AssemblyType.GIFT_BOX,
        )
        session.add(gift_bag)
        session.flush()

        # Create Composition entries using factory methods
        comp1 = Composition.create_unit_composition(
            assembly_id=gift_bag.id,
            finished_unit_id=cookie_unit.id,
            quantity=3,  # 3 cookies per bag
        )
        comp2 = Composition.create_unit_composition(
            assembly_id=gift_bag.id,
            finished_unit_id=brownie_unit.id,
            quantity=2,  # 2 brownies per bag
        )
        session.add_all([comp1, comp2])
        session.commit()

        return {
            "gift_bag_id": gift_bag.id,
            "cookie_unit_id": cookie_unit.id,
            "brownie_unit_id": brownie_unit.id,
            "cookie_recipe_id": cookie_recipe.id,
            "brownie_recipe_id": brownie_recipe.id,
        }

    @pytest.fixture
    def nested_bundle_setup(self, test_db, simple_bundle_setup):
        """Create a nested bundle containing the simple bundle."""
        session = test_db()

        # Create another FinishedGood that contains the first one
        mega_bundle = FinishedGood(
            display_name="Mega Holiday Bundle",
            slug="mega-holiday-bundle",
            assembly_type=AssemblyType.HOLIDAY_SET,
        )
        session.add(mega_bundle)
        session.flush()

        # Create a composition that references the nested FinishedGood
        comp = Composition.create_assembly_composition(
            assembly_id=mega_bundle.id,
            finished_good_id=simple_bundle_setup["gift_bag_id"],
            quantity=2,  # 2 gift bags per mega bundle
        )
        session.add(comp)
        session.commit()

        return {
            **simple_bundle_setup,
            "mega_bundle_id": mega_bundle.id,
        }

    def test_simple_bundle_explosion(self, test_db, simple_bundle_setup):
        """Test exploding a simple bundle with two components."""
        session = test_db()

        result = explode_bundle_requirements(
            simple_bundle_setup["gift_bag_id"],
            10,  # 10 gift bags
            session,
        )

        # 10 bags * 3 cookies = 30 cookies
        assert result[simple_bundle_setup["cookie_unit_id"]] == 30
        # 10 bags * 2 brownies = 20 brownies
        assert result[simple_bundle_setup["brownie_unit_id"]] == 20

    def test_nested_bundle_explosion(self, test_db, nested_bundle_setup):
        """Test exploding a nested bundle (bundle containing bundle)."""
        session = test_db()

        result = explode_bundle_requirements(
            nested_bundle_setup["mega_bundle_id"],
            5,  # 5 mega bundles
            session,
        )

        # 5 mega * 2 gift bags * 3 cookies = 30 cookies
        assert result[nested_bundle_setup["cookie_unit_id"]] == 30
        # 5 mega * 2 gift bags * 2 brownies = 20 brownies
        assert result[nested_bundle_setup["brownie_unit_id"]] == 20

    def test_nonexistent_bundle_returns_empty(self, test_db):
        """Test that nonexistent bundle returns empty dict."""
        session = test_db()

        result = explode_bundle_requirements(99999, 10, session)
        assert result == {}

    def test_zero_quantity_returns_zero_units(self, test_db, simple_bundle_setup):
        """Test that zero bundle quantity produces zero units."""
        session = test_db()

        result = explode_bundle_requirements(
            simple_bundle_setup["gift_bag_id"],
            0,
            session,
        )

        assert result.get(simple_bundle_setup["cookie_unit_id"], 0) == 0
        assert result.get(simple_bundle_setup["brownie_unit_id"], 0) == 0


class TestAggregateByRecipe:
    """Tests for aggregate_by_recipe() function."""

    @pytest.fixture
    def multi_unit_setup(self, test_db):
        """Create multiple FinishedUnits sharing recipes."""
        session = test_db()

        # Create recipes (F056: yield fields removed from Recipe model)
        cookie_recipe = Recipe(
            name="Sugar Cookies",
            category="Cookies",
        )
        brownie_recipe = Recipe(
            name="Walnut Brownies",
            category="Brownies",
        )
        session.add_all([cookie_recipe, brownie_recipe])
        session.flush()

        # Create multiple FinishedUnits - some sharing recipes
        # F056: items_per_batch holds yield data (was Recipe.yield_quantity)
        # F083: Multiple sizes can share same item_unit and yield_type
        large_cookie = FinishedUnit(
            display_name="Large Sugar Cookie",
            slug="large-sugar-cookie",
            recipe_id=cookie_recipe.id,
            items_per_batch=36,  # From Recipe's former yield_quantity
            item_unit="large cookie",  # Unique item_unit for this yield
        )
        small_cookie = FinishedUnit(
            display_name="Small Sugar Cookie",
            slug="small-sugar-cookie",
            recipe_id=cookie_recipe.id,  # Same recipe!
            items_per_batch=36,
            item_unit="small cookie",  # Different item_unit to satisfy unique constraint
        )
        brownie = FinishedUnit(
            display_name="Walnut Brownie",
            slug="walnut-brownie",
            recipe_id=brownie_recipe.id,
            items_per_batch=16,  # From Recipe's former yield_quantity
            item_unit="brownies",
        )
        session.add_all([large_cookie, small_cookie, brownie])
        session.commit()

        return {
            "cookie_recipe_id": cookie_recipe.id,
            "brownie_recipe_id": brownie_recipe.id,
            "large_cookie_id": large_cookie.id,
            "small_cookie_id": small_cookie.id,
            "brownie_id": brownie.id,
        }

    def test_aggregates_same_recipe(self, test_db, multi_unit_setup):
        """Test that units with same recipe are aggregated."""
        session = test_db()

        unit_quantities = {
            multi_unit_setup["large_cookie_id"]: 50,
            multi_unit_setup["small_cookie_id"]: 30,
        }

        results = aggregate_by_recipe(unit_quantities, session)

        assert len(results) == 1  # Both use same recipe
        result = results[0]
        assert result.recipe_id == multi_unit_setup["cookie_recipe_id"]
        assert result.units_needed == 80  # 50 + 30
        assert result.batches == 3  # ceil(80/36)
        assert result.total_yield >= 80

    def test_multiple_recipes(self, test_db, multi_unit_setup):
        """Test multiple units with different recipes."""
        session = test_db()

        unit_quantities = {
            multi_unit_setup["large_cookie_id"]: 50,
            multi_unit_setup["brownie_id"]: 20,
        }

        results = aggregate_by_recipe(unit_quantities, session)

        assert len(results) == 2

        # Find results by recipe
        results_by_recipe = {r.recipe_id: r for r in results}

        cookie_result = results_by_recipe[multi_unit_setup["cookie_recipe_id"]]
        assert cookie_result.units_needed == 50
        assert cookie_result.batches == 2  # ceil(50/36)

        brownie_result = results_by_recipe[multi_unit_setup["brownie_recipe_id"]]
        assert brownie_result.units_needed == 20
        assert brownie_result.batches == 2  # ceil(20/16)

    def test_empty_input_returns_empty(self, test_db):
        """Test that empty unit_quantities returns empty list."""
        session = test_db()

        results = aggregate_by_recipe({}, session)
        assert results == []

    def test_all_results_no_shortfall(self, test_db, multi_unit_setup):
        """Verify all results have total_yield >= units_needed."""
        session = test_db()

        unit_quantities = {
            multi_unit_setup["large_cookie_id"]: 100,
            multi_unit_setup["small_cookie_id"]: 77,
            multi_unit_setup["brownie_id"]: 33,
        }

        results = aggregate_by_recipe(unit_quantities, session)

        for result in results:
            assert result.total_yield >= result.units_needed, (
                f"Shortfall in {result.recipe_name}: "
                f"{result.total_yield} produced < {result.units_needed} needed"
            )


class TestRecipeBatchResultDataclass:
    """Tests for RecipeBatchResult dataclass structure."""

    def test_dataclass_fields(self):
        """Test that RecipeBatchResult has all required fields."""
        result = RecipeBatchResult(
            recipe_id=1,
            recipe_name="Test Recipe",
            units_needed=100,
            batches=3,
            yield_per_batch=48,
            total_yield=144,
            waste_units=44,
            waste_percent=30.56,
        )

        assert result.recipe_id == 1
        assert result.recipe_name == "Test Recipe"
        assert result.units_needed == 100
        assert result.batches == 3
        assert result.yield_per_batch == 48
        assert result.total_yield == 144
        assert result.waste_units == 44
        assert result.waste_percent == 30.56

    def test_dataclass_equality(self):
        """Test dataclass equality comparison."""
        result1 = RecipeBatchResult(1, "Recipe", 100, 3, 48, 144, 44, 30.56)
        result2 = RecipeBatchResult(1, "Recipe", 100, 3, 48, 144, 44, 30.56)
        assert result1 == result2
