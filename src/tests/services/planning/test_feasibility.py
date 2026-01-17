"""
Unit tests for feasibility service (Feature 039 WP04).

Tests cover:
- check_production_feasibility() for ingredient availability
- check_assembly_feasibility() for component availability
- Partial assembly calculations (minimum across components)
- FeasibilityStatus enum values are accurate
- Missing components are correctly reported

Per WP04 specification:
- If system shows "can_assemble", production yields are mathematically sufficient
- Partial assembly correctly calculates can_assemble count
"""

import pytest
from datetime import date
from decimal import Decimal

from src.services.planning import (
    check_production_feasibility,
    check_assembly_feasibility,
    check_single_assembly_feasibility,
    FeasibilityStatus,
    FeasibilityResult,
)
from src.models import (
    Event,
    EventProductionTarget,
    EventAssemblyTarget,
    Recipe,
    RecipeIngredient,
    FinishedUnit,
    FinishedGood,
    Composition,
    Ingredient,
    Product,
    InventoryItem,
)
from src.models.assembly_type import AssemblyType


class TestFeasibilityStatus:
    """Tests for FeasibilityStatus enum."""

    def test_enum_values(self):
        """Verify all expected enum values exist."""
        assert FeasibilityStatus.CAN_ASSEMBLE.value == "can_assemble"
        assert FeasibilityStatus.PARTIAL.value == "partial"
        assert FeasibilityStatus.CANNOT_ASSEMBLE.value == "cannot_assemble"
        assert FeasibilityStatus.AWAITING_PRODUCTION.value == "awaiting_production"


class TestFeasibilityResult:
    """Tests for FeasibilityResult dataclass."""

    def test_dataclass_fields(self):
        """Verify FeasibilityResult has all required fields."""
        result = FeasibilityResult(
            finished_good_id=1,
            finished_good_name="Test Bundle",
            target_quantity=10,
            can_assemble=5,
            status=FeasibilityStatus.PARTIAL,
            missing_components=[{"component_id": 1, "needed": 60, "available": 30}],
        )

        assert result.finished_good_id == 1
        assert result.finished_good_name == "Test Bundle"
        assert result.target_quantity == 10
        assert result.can_assemble == 5
        assert result.status == FeasibilityStatus.PARTIAL
        assert len(result.missing_components) == 1


class TestCheckProductionFeasibility:
    """Tests for check_production_feasibility() function."""

    @pytest.fixture
    def production_setup(self, test_db):
        """Create event with production targets and ingredients."""
        session = test_db()

        # Create event
        event = Event(
            name="Test Event 2025",
            event_date=date(2025, 12, 25),
            year=2025,
        )
        session.add(event)
        session.flush()

        # Create ingredient
        flour = Ingredient(
            display_name="All Purpose Flour",
            slug="all-purpose-flour",
            category="Flour",
            hierarchy_level=2,
        )
        session.add(flour)
        session.flush()

        # Create recipe
        cookie_recipe = Recipe(
            name="Chocolate Chip Cookies",
            category="Cookies",
        )
        session.add(cookie_recipe)
        session.flush()

        # Add recipe ingredient (needs 2 cups flour per batch)
        recipe_ing = RecipeIngredient(
            recipe_id=cookie_recipe.id,
            ingredient_id=flour.id,
            quantity=Decimal("2.0"),
            unit="cup",
        )
        session.add(recipe_ing)

        # Create production target (5 batches)
        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=cookie_recipe.id,
            target_batches=5,
        )
        session.add(target)
        session.commit()

        return {
            "event_id": event.id,
            "recipe_id": cookie_recipe.id,
            "flour_slug": flour.slug,
            "flour_id": flour.id,
        }

    def test_no_inventory_cannot_produce(self, test_db, production_setup):
        """Test with no inventory - production not feasible."""
        session = test_db()

        results = check_production_feasibility(
            production_setup["event_id"], session=session
        )

        assert len(results) == 1
        result = results[0]
        assert result["recipe_id"] == production_setup["recipe_id"]
        assert result["can_produce"] is False
        assert len(result["missing"]) > 0

    def test_with_sufficient_inventory(self, test_db, production_setup):
        """Test with sufficient inventory - production feasible."""
        session = test_db()

        # Create product for the ingredient
        flour = session.query(Ingredient).filter_by(slug=production_setup["flour_slug"]).first()
        product = Product(
            ingredient_id=flour.id,
            brand="Test Brand",
            package_size="5 lb bag",
            package_unit="cup",  # Use cups to match recipe
            package_unit_quantity=Decimal("20.0"),  # 20 cups per package
        )
        session.add(product)
        session.flush()

        # Add inventory (5 batches * 2 cups = 10 cups needed)
        # Add 20 cups worth (quantity in package_unit)
        inventory = InventoryItem(
            product_id=product.id,
            quantity=20.0,  # 20 cups
            unit_cost=0.25,  # $0.25 per cup
        )
        session.add(inventory)
        session.commit()

        results = check_production_feasibility(
            production_setup["event_id"], session=session
        )

        assert len(results) == 1
        result = results[0]
        assert result["can_produce"] is True
        assert result["missing"] == []

    def test_multiple_recipes(self, test_db, production_setup):
        """Test with multiple production targets."""
        session = test_db()

        # Add another recipe and target
        brownie_recipe = Recipe(
            name="Fudge Brownies",
            category="Brownies",
        )
        session.add(brownie_recipe)
        session.flush()

        target2 = EventProductionTarget(
            event_id=production_setup["event_id"],
            recipe_id=brownie_recipe.id,
            target_batches=3,
        )
        session.add(target2)
        session.commit()

        results = check_production_feasibility(
            production_setup["event_id"], session=session
        )

        assert len(results) == 2
        recipe_ids = {r["recipe_id"] for r in results}
        assert production_setup["recipe_id"] in recipe_ids
        assert brownie_recipe.id in recipe_ids


class TestCheckAssemblyFeasibility:
    """Tests for check_assembly_feasibility() function."""

    @pytest.fixture
    def assembly_setup(self, test_db):
        """Create event with assembly targets and FinishedUnit components."""
        session = test_db()

        # Create event
        event = Event(
            name="Assembly Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
        )
        session.add(event)
        session.flush()

        # Create recipes for finished units
        cookie_recipe = Recipe(
            name="Sugar Cookies",
            category="Cookies",
        )
        brownie_recipe = Recipe(
            name="Brownies",
            category="Brownies",
        )
        session.add_all([cookie_recipe, brownie_recipe])
        session.flush()

        # Create FinishedUnits
        cookie_unit = FinishedUnit(
            display_name="Sugar Cookie",
            slug="sugar-cookie",
            recipe_id=cookie_recipe.id,
            inventory_count=0,  # None produced yet
        )
        brownie_unit = FinishedUnit(
            display_name="Fudge Brownie",
            slug="fudge-brownie",
            recipe_id=brownie_recipe.id,
            inventory_count=0,
        )
        session.add_all([cookie_unit, brownie_unit])
        session.flush()

        # Create FinishedGood (bundle)
        gift_bag = FinishedGood(
            display_name="Holiday Gift Bag",
            slug="holiday-gift-bag",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=0,
        )
        session.add(gift_bag)
        session.flush()

        # Create Composition: 6 cookies, 3 brownies per bag
        comp_cookie = Composition.create_unit_composition(
            assembly_id=gift_bag.id,
            finished_unit_id=cookie_unit.id,
            quantity=6,
        )
        comp_brownie = Composition.create_unit_composition(
            assembly_id=gift_bag.id,
            finished_unit_id=brownie_unit.id,
            quantity=3,
        )
        session.add_all([comp_cookie, comp_brownie])

        # Create assembly target: 50 bags
        target = EventAssemblyTarget(
            event_id=event.id,
            finished_good_id=gift_bag.id,
            target_quantity=50,
        )
        session.add(target)
        session.commit()

        return {
            "event_id": event.id,
            "gift_bag_id": gift_bag.id,
            "cookie_unit_id": cookie_unit.id,
            "brownie_unit_id": brownie_unit.id,
        }

    def test_no_production_awaiting(self, test_db, assembly_setup):
        """Test with no production - status is AWAITING_PRODUCTION."""
        session = test_db()

        results = check_assembly_feasibility(
            assembly_setup["event_id"], session=session
        )

        assert len(results) == 1
        result = results[0]
        assert result.finished_good_id == assembly_setup["gift_bag_id"]
        assert result.target_quantity == 50
        assert result.can_assemble == 0
        assert result.status == FeasibilityStatus.AWAITING_PRODUCTION

    def test_full_production_can_assemble(self, test_db, assembly_setup):
        """Test with full production - status is CAN_ASSEMBLE."""
        session = test_db()

        # Add production: 50 bags need 300 cookies, 150 brownies
        cookie_unit = session.get(FinishedUnit, assembly_setup["cookie_unit_id"])
        brownie_unit = session.get(FinishedUnit, assembly_setup["brownie_unit_id"])
        cookie_unit.inventory_count = 300
        brownie_unit.inventory_count = 150
        session.commit()

        results = check_assembly_feasibility(
            assembly_setup["event_id"], session=session
        )

        assert len(results) == 1
        result = results[0]
        assert result.can_assemble == 50
        assert result.status == FeasibilityStatus.CAN_ASSEMBLE
        assert result.missing_components == []

    def test_partial_production(self, test_db, assembly_setup):
        """Test with partial production - status is PARTIAL."""
        session = test_db()

        # 50 bags need:
        # - 300 cookies (6 per bag)
        # - 150 brownies (3 per bag)
        # Give enough cookies for 50, but only brownies for 40
        cookie_unit = session.get(FinishedUnit, assembly_setup["cookie_unit_id"])
        brownie_unit = session.get(FinishedUnit, assembly_setup["brownie_unit_id"])
        cookie_unit.inventory_count = 300  # Enough for 50 bags
        brownie_unit.inventory_count = 120  # Only enough for 40 bags
        session.commit()

        results = check_assembly_feasibility(
            assembly_setup["event_id"], session=session
        )

        assert len(results) == 1
        result = results[0]
        # Minimum of (300/6=50, 120/3=40) = 40
        assert result.can_assemble == 40
        assert result.status == FeasibilityStatus.PARTIAL

    def test_multiple_bundles(self, test_db, assembly_setup):
        """Test with multiple assembly targets."""
        session = test_db()

        # Add another bundle
        another_bag = FinishedGood(
            display_name="Mini Gift Bag",
            slug="mini-gift-bag",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=0,
        )
        session.add(another_bag)
        session.flush()

        target2 = EventAssemblyTarget(
            event_id=assembly_setup["event_id"],
            finished_good_id=another_bag.id,
            target_quantity=20,
        )
        session.add(target2)
        session.commit()

        results = check_assembly_feasibility(
            assembly_setup["event_id"], session=session
        )

        assert len(results) == 2


class TestPartialAssemblyCalculation:
    """Tests for partial assembly calculation logic."""

    @pytest.fixture
    def multi_component_setup(self, test_db):
        """Create bundle with three components for partial testing."""
        session = test_db()

        # Create recipes (F056: yield fields removed from Recipe model)
        cookie_recipe = Recipe(name="Cookies", category="Cookies")
        brownie_recipe = Recipe(name="Brownies", category="Brownies")
        truffle_recipe = Recipe(name="Truffles", category="Candy")
        session.add_all([cookie_recipe, brownie_recipe, truffle_recipe])
        session.flush()

        # Create FinishedUnits
        cookie = FinishedUnit(
            display_name="Cookie",
            slug="cookie",
            recipe_id=cookie_recipe.id,
            inventory_count=0,
        )
        brownie = FinishedUnit(
            display_name="Brownie",
            slug="brownie",
            recipe_id=brownie_recipe.id,
            inventory_count=0,
        )
        truffle = FinishedUnit(
            display_name="Truffle",
            slug="truffle",
            recipe_id=truffle_recipe.id,
            inventory_count=0,
        )
        session.add_all([cookie, brownie, truffle])
        session.flush()

        # Create bundle with composition:
        # 4 cookies, 2 brownies, 3 truffles per bag
        bundle = FinishedGood(
            display_name="Deluxe Bag",
            slug="deluxe-bag",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=0,
        )
        session.add(bundle)
        session.flush()

        comp1 = Composition.create_unit_composition(bundle.id, cookie.id, 4)
        comp2 = Composition.create_unit_composition(bundle.id, brownie.id, 2)
        comp3 = Composition.create_unit_composition(bundle.id, truffle.id, 3)
        session.add_all([comp1, comp2, comp3])
        session.commit()

        return {
            "bundle_id": bundle.id,
            "cookie_id": cookie.id,
            "brownie_id": brownie.id,
            "truffle_id": truffle.id,
        }

    def test_minimum_across_all_components(self, test_db, multi_component_setup):
        """Verify can_assemble equals minimum across all components."""
        session = test_db()

        # Target: 100 bags
        # Needs: 400 cookies (4*100), 200 brownies (2*100), 300 truffles (3*100)
        # Give: 400 cookies (100), 160 brownies (80), 150 truffles (50)
        # Minimum: 50 bags
        cookie = session.get(FinishedUnit, multi_component_setup["cookie_id"])
        brownie = session.get(FinishedUnit, multi_component_setup["brownie_id"])
        truffle = session.get(FinishedUnit, multi_component_setup["truffle_id"])

        cookie.inventory_count = 400  # 100 bags worth
        brownie.inventory_count = 160  # 80 bags worth
        truffle.inventory_count = 150  # 50 bags worth
        session.commit()

        result = check_single_assembly_feasibility(
            multi_component_setup["bundle_id"],
            100,
            session=session,
        )

        assert result.can_assemble == 50
        assert result.status == FeasibilityStatus.PARTIAL

    def test_all_components_equal(self, test_db, multi_component_setup):
        """Test when all components support same number."""
        session = test_db()

        # Give exactly enough for 25 bags of each
        cookie = session.get(FinishedUnit, multi_component_setup["cookie_id"])
        brownie = session.get(FinishedUnit, multi_component_setup["brownie_id"])
        truffle = session.get(FinishedUnit, multi_component_setup["truffle_id"])

        cookie.inventory_count = 100  # 25 bags (100/4)
        brownie.inventory_count = 50   # 25 bags (50/2)
        truffle.inventory_count = 75   # 25 bags (75/3)
        session.commit()

        result = check_single_assembly_feasibility(
            multi_component_setup["bundle_id"],
            50,  # Target 50 bags
            session=session,
        )

        assert result.can_assemble == 25
        assert result.status == FeasibilityStatus.PARTIAL

    def test_zero_of_one_component(self, test_db, multi_component_setup):
        """Test when one component has zero inventory."""
        session = test_db()

        cookie = session.get(FinishedUnit, multi_component_setup["cookie_id"])
        brownie = session.get(FinishedUnit, multi_component_setup["brownie_id"])
        truffle = session.get(FinishedUnit, multi_component_setup["truffle_id"])

        cookie.inventory_count = 200  # 50 bags worth
        brownie.inventory_count = 0    # Zero!
        truffle.inventory_count = 150  # 50 bags worth
        session.commit()

        result = check_single_assembly_feasibility(
            multi_component_setup["bundle_id"],
            50,
            session=session,
        )

        assert result.can_assemble == 0
        assert result.status == FeasibilityStatus.AWAITING_PRODUCTION

    def test_excess_inventory_capped_at_target(self, test_db, multi_component_setup):
        """Test that can_assemble is capped at target quantity."""
        session = test_db()

        # Give way more than needed
        cookie = session.get(FinishedUnit, multi_component_setup["cookie_id"])
        brownie = session.get(FinishedUnit, multi_component_setup["brownie_id"])
        truffle = session.get(FinishedUnit, multi_component_setup["truffle_id"])

        cookie.inventory_count = 1000  # 250 bags worth
        brownie.inventory_count = 1000  # 500 bags worth
        truffle.inventory_count = 1000  # 333 bags worth
        session.commit()

        result = check_single_assembly_feasibility(
            multi_component_setup["bundle_id"],
            50,  # Only targeting 50
            session=session,
        )

        # Should be capped at target, not minimum of inventory
        assert result.can_assemble == 50
        assert result.status == FeasibilityStatus.CAN_ASSEMBLE


class TestCheckSingleAssemblyFeasibility:
    """Tests for check_single_assembly_feasibility convenience function."""

    @pytest.fixture
    def simple_bundle(self, test_db):
        """Create a simple bundle for testing."""
        session = test_db()

        recipe = Recipe(name="Cookies", category="Cookies")
        session.add(recipe)
        session.flush()

        unit = FinishedUnit(
            display_name="Cookie",
            slug="cookie",
            recipe_id=recipe.id,
            inventory_count=100,
        )
        session.add(unit)
        session.flush()

        bundle = FinishedGood(
            display_name="Cookie Box",
            slug="cookie-box",
            assembly_type=AssemblyType.GIFT_BOX,
        )
        session.add(bundle)
        session.flush()

        comp = Composition.create_unit_composition(bundle.id, unit.id, 5)
        session.add(comp)
        session.commit()

        return {"bundle_id": bundle.id, "unit_id": unit.id}

    def test_returns_feasibility_result(self, test_db, simple_bundle):
        """Verify function returns FeasibilityResult."""
        session = test_db()

        result = check_single_assembly_feasibility(
            simple_bundle["bundle_id"],
            10,
            session=session,
        )

        assert isinstance(result, FeasibilityResult)
        assert result.finished_good_id == simple_bundle["bundle_id"]
        assert result.target_quantity == 10

    def test_feasible_assembly(self, test_db, simple_bundle):
        """Test when assembly is fully feasible."""
        session = test_db()

        # 100 cookies / 5 per box = 20 boxes possible
        result = check_single_assembly_feasibility(
            simple_bundle["bundle_id"],
            20,  # Target 20, exactly achievable
            session=session,
        )

        assert result.can_assemble == 20
        assert result.status == FeasibilityStatus.CAN_ASSEMBLE

    def test_nonexistent_bundle(self, test_db):
        """Test with nonexistent bundle ID."""
        session = test_db()

        result = check_single_assembly_feasibility(
            99999,  # Doesn't exist
            10,
            session=session,
        )

        # Should handle gracefully - either return 0 or error
        assert result.can_assemble == 0


class TestMissingComponentsStructure:
    """Tests for missing_components list structure."""

    @pytest.fixture
    def missing_component_setup(self, test_db):
        """Create bundle with insufficient inventory."""
        session = test_db()

        recipe = Recipe(name="Cookies", category="Cookies")
        session.add(recipe)
        session.flush()

        unit = FinishedUnit(
            display_name="Chocolate Cookie",
            slug="chocolate-cookie",
            recipe_id=recipe.id,
            inventory_count=10,  # Only 10 available
        )
        session.add(unit)
        session.flush()

        bundle = FinishedGood(
            display_name="Cookie Gift Box",
            slug="cookie-gift-box",
            assembly_type=AssemblyType.GIFT_BOX,
        )
        session.add(bundle)
        session.flush()

        comp = Composition.create_unit_composition(bundle.id, unit.id, 5)
        session.add(comp)
        session.commit()

        return {"bundle_id": bundle.id, "unit_id": unit.id}

    def test_missing_components_populated(self, test_db, missing_component_setup):
        """Verify missing_components contains required fields."""
        session = test_db()

        # Need 10 boxes * 5 cookies = 50 cookies, only have 10
        result = check_single_assembly_feasibility(
            missing_component_setup["bundle_id"],
            10,
            session=session,
        )

        assert len(result.missing_components) > 0

        # Check structure of missing component
        missing = result.missing_components[0]
        assert "component_type" in missing
        assert "component_id" in missing
        assert "needed" in missing
        assert "available" in missing

    def test_no_missing_when_feasible(self, test_db, missing_component_setup):
        """Verify missing_components is empty when fully feasible."""
        session = test_db()

        # Only need 2 boxes = 10 cookies, we have 10
        result = check_single_assembly_feasibility(
            missing_component_setup["bundle_id"],
            2,
            session=session,
        )

        assert result.missing_components == []
        assert result.status == FeasibilityStatus.CAN_ASSEMBLE
