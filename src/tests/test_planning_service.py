"""
Tests for F072 Planning Service - Recipe Decomposition & Aggregation.

Tests cover:
- Single atomic FG → recipe quantity mapping
- Bundle decomposition with quantity multiplication
- Recipe aggregation across multiple FGs
- Nested bundle decomposition (2-level, 3+ level)
- DAG patterns (same FG in multiple branches)
- Mixed atomic/bundle events
- Edge cases: circular references, empty events, missing recipes, zero quantities
"""

from unittest.mock import patch, PropertyMock

import pytest
from datetime import date

from src.services.planning_service import calculate_recipe_requirements
from src.services.event_service import CircularReferenceError
from src.services.exceptions import ValidationError
from src.models.event import Event
from src.models.event_finished_good import EventFinishedGood
from src.models.finished_good import FinishedGood
from src.models.finished_unit import FinishedUnit
from src.models.composition import Composition
from src.models.recipe import Recipe
# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def planning_event(test_db):
    """Create a test event for recipe requirement tests."""
    event = Event(
        name="Test Planning Event",
        event_date=date(2026, 12, 25),
        year=2026,
    )
    test_db.add(event)
    test_db.flush()
    return event


@pytest.fixture
def test_recipe(test_db):
    """Create a test recipe."""
    recipe = Recipe(name="Sugar Cookie Recipe", category="Cookies")
    test_db.add(recipe)
    test_db.flush()
    return recipe


@pytest.fixture
def test_finished_unit(test_db, test_recipe):
    """Create a FinishedUnit linked to a recipe."""
    fu = FinishedUnit(
        slug=f"sugar-cookie-{test_recipe.id}",
        display_name="Sugar Cookie",
        recipe_id=test_recipe.id,
    )
    test_db.add(fu)
    test_db.flush()
    return fu


@pytest.fixture
def atomic_finished_good(test_db, test_finished_unit):
    """Create a FinishedGood with a single FinishedUnit component (qty 1)."""
    fg = FinishedGood(
        slug="single-cookie-box",
        display_name="Single Cookie Box",
    )
    test_db.add(fg)
    test_db.flush()

    comp = Composition(
        assembly_id=fg.id,
        finished_unit_id=test_finished_unit.id,
        component_quantity=1.0,
    )
    test_db.add(comp)
    test_db.flush()

    return fg


@pytest.fixture
def second_recipe(test_db):
    """Create a second recipe."""
    recipe = Recipe(name="Chocolate Truffle Recipe", category="Candy")
    test_db.add(recipe)
    test_db.flush()
    return recipe


@pytest.fixture
def second_finished_unit(test_db, second_recipe):
    """Create a second FinishedUnit linked to second recipe."""
    fu = FinishedUnit(
        slug=f"chocolate-truffle-{second_recipe.id}",
        display_name="Chocolate Truffle",
        recipe_id=second_recipe.id,
    )
    test_db.add(fu)
    test_db.flush()
    return fu


@pytest.fixture
def bundle_finished_good(test_db, test_finished_unit, second_finished_unit):
    """Create a bundle FG containing 2 of each FinishedUnit."""
    fg = FinishedGood(
        slug="variety-box",
        display_name="Variety Box",
    )
    test_db.add(fg)
    test_db.flush()

    # Add 2 of first FU (sugar cookies)
    comp1 = Composition(
        assembly_id=fg.id,
        finished_unit_id=test_finished_unit.id,
        component_quantity=2.0,
    )
    test_db.add(comp1)

    # Add 2 of second FU (truffles)
    comp2 = Composition(
        assembly_id=fg.id,
        finished_unit_id=second_finished_unit.id,
        component_quantity=2.0,
    )
    test_db.add(comp2)
    test_db.flush()

    return fg


# ============================================================================
# T004: Tests for single atomic FG
# ============================================================================


class TestSingleAtomicFG:
    """Tests for User Story 1, Scenario 1: Single atomic FG."""

    def test_single_atomic_fg_returns_correct_recipe_quantity(
        self, test_db, planning_event, atomic_finished_good, test_recipe
    ):
        """
        Given an event with a single atomic FG (quantity 24)
        When recipe requirements are calculated
        Then the result contains one recipe with quantity 24
        """
        # Create EventFinishedGood with quantity 24
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=atomic_finished_good.id,
            quantity=24,
        )
        test_db.add(efg)
        test_db.flush()

        # Calculate requirements
        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # Verify
        assert len(result) == 1
        assert test_recipe in result
        assert result[test_recipe] == 24

    def test_atomic_fg_with_quantity_one(
        self, test_db, planning_event, atomic_finished_good, test_recipe
    ):
        """Quantity 1 should map directly to recipe quantity 1."""
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=atomic_finished_good.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        assert result[test_recipe] == 1


# ============================================================================
# T005: Tests for bundle decomposition
# ============================================================================


class TestBundleDecomposition:
    """Tests for User Story 1, Scenario 2: Bundle FG decomposition."""

    def test_bundle_decomposes_with_multiplied_quantities(
        self,
        test_db,
        planning_event,
        bundle_finished_good,
        test_recipe,
        second_recipe,
    ):
        """
        Given an event with a bundle FG (quantity 10) containing 2 atomic items each
        When recipe requirements are calculated
        Then the result shows 20 units needed for each component's recipe
        """
        # Create EventFinishedGood with bundle quantity 10
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=bundle_finished_good.id,
            quantity=10,
        )
        test_db.add(efg)
        test_db.flush()

        # Calculate requirements
        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # Verify: 10 bundles * 2 of each = 20 per recipe
        assert len(result) == 2
        assert result[test_recipe] == 20
        assert result[second_recipe] == 20

    def test_bundle_with_different_component_quantities(
        self, test_db, planning_event, test_finished_unit, second_finished_unit
    ):
        """Bundle with different quantities per component multiplies correctly."""
        # Create bundle: 3 of first, 5 of second
        fg = FinishedGood(slug="asymmetric-box", display_name="Asymmetric Box")
        test_db.add(fg)
        test_db.flush()

        comp1 = Composition(
            assembly_id=fg.id,
            finished_unit_id=test_finished_unit.id,
            component_quantity=3.0,
        )
        comp2 = Composition(
            assembly_id=fg.id,
            finished_unit_id=second_finished_unit.id,
            component_quantity=5.0,
        )
        test_db.add_all([comp1, comp2])
        test_db.flush()

        # Event with 4 of this bundle
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=fg.id,
            quantity=4,
        )
        test_db.add(efg)
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # First recipe: 4 * 3 = 12
        # Second recipe: 4 * 5 = 20
        recipe1 = test_finished_unit.recipe
        recipe2 = second_finished_unit.recipe
        assert result[recipe1] == 12
        assert result[recipe2] == 20


# ============================================================================
# T006: Tests for recipe aggregation
# ============================================================================


class TestRecipeAggregation:
    """Tests for User Story 1, Scenario 3: Recipe aggregation."""

    def test_recipe_quantities_aggregated_across_multiple_fgs(
        self, test_db, planning_event, test_recipe, test_finished_unit
    ):
        """
        Given an event with multiple FGs that share the same recipe
        When recipe requirements are calculated
        Then the quantities are summed for that recipe
        """
        # Create two FGs both using the same recipe
        fg1 = FinishedGood(slug="box-a", display_name="Box A")
        fg2 = FinishedGood(slug="box-b", display_name="Box B")
        test_db.add_all([fg1, fg2])
        test_db.flush()

        # Both contain the same FinishedUnit (same recipe)
        comp1 = Composition(
            assembly_id=fg1.id,
            finished_unit_id=test_finished_unit.id,
            component_quantity=1.0,
        )
        comp2 = Composition(
            assembly_id=fg2.id,
            finished_unit_id=test_finished_unit.id,
            component_quantity=1.0,
        )
        test_db.add_all([comp1, comp2])
        test_db.flush()

        # Event selects both: fg1 qty 10, fg2 qty 15
        efg1 = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=fg1.id,
            quantity=10,
        )
        efg2 = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=fg2.id,
            quantity=15,
        )
        test_db.add_all([efg1, efg2])
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # Should aggregate: 10 + 15 = 25
        assert len(result) == 1
        assert result[test_recipe] == 25

    def test_aggregation_with_different_multipliers(
        self, test_db, planning_event, test_recipe, test_finished_unit
    ):
        """Multiple FGs with different component quantities aggregate correctly."""
        # FG1: 2 of the FU per bundle
        # FG2: 5 of the FU per bundle
        fg1 = FinishedGood(slug="small-box", display_name="Small Box")
        fg2 = FinishedGood(slug="large-box", display_name="Large Box")
        test_db.add_all([fg1, fg2])
        test_db.flush()

        comp1 = Composition(
            assembly_id=fg1.id,
            finished_unit_id=test_finished_unit.id,
            component_quantity=2.0,
        )
        comp2 = Composition(
            assembly_id=fg2.id,
            finished_unit_id=test_finished_unit.id,
            component_quantity=5.0,
        )
        test_db.add_all([comp1, comp2])
        test_db.flush()

        # Event: 3 small boxes, 2 large boxes
        efg1 = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=fg1.id,
            quantity=3,
        )
        efg2 = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=fg2.id,
            quantity=2,
        )
        test_db.add_all([efg1, efg2])
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # (3 * 2) + (2 * 5) = 6 + 10 = 16
        assert result[test_recipe] == 16

    def test_multiple_recipes_with_aggregation(
        self,
        test_db,
        planning_event,
        test_recipe,
        second_recipe,
        test_finished_unit,
        second_finished_unit,
    ):
        """Event with multiple FGs using different recipes aggregates per-recipe."""
        # FG1: uses both recipes
        # FG2: uses only first recipe
        fg1 = FinishedGood(slug="combo-box", display_name="Combo Box")
        fg2 = FinishedGood(slug="cookie-box", display_name="Cookie Box")
        test_db.add_all([fg1, fg2])
        test_db.flush()

        # FG1: 2 cookies, 3 truffles
        comp1a = Composition(
            assembly_id=fg1.id,
            finished_unit_id=test_finished_unit.id,
            component_quantity=2.0,
        )
        comp1b = Composition(
            assembly_id=fg1.id,
            finished_unit_id=second_finished_unit.id,
            component_quantity=3.0,
        )
        # FG2: 4 cookies only
        comp2 = Composition(
            assembly_id=fg2.id,
            finished_unit_id=test_finished_unit.id,
            component_quantity=4.0,
        )
        test_db.add_all([comp1a, comp1b, comp2])
        test_db.flush()

        # Event: 5 combo boxes, 10 cookie boxes
        efg1 = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=fg1.id,
            quantity=5,
        )
        efg2 = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=fg2.id,
            quantity=10,
        )
        test_db.add_all([efg1, efg2])
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # Cookie recipe: (5 * 2) + (10 * 4) = 10 + 40 = 50
        # Truffle recipe: (5 * 3) = 15
        assert result[test_recipe] == 50
        assert result[second_recipe] == 15


# ============================================================================
# T007: Tests for 2-level nested bundles
# ============================================================================


class TestTwoLevelNestedBundles:
    """Tests for User Story 2, Scenario 1: 2-level nested bundle decomposition."""

    def test_2_level_nested_bundle_multiplies_correctly(self, test_db, planning_event):
        """
        Given a bundle containing another bundle (2-level nesting) with quantity 5
        When decomposed
        Then quantities are correctly multiplied through both levels.

        Structure:
          OuterBundle (qty 5 in event)
          └── InnerBundle (qty 3 per outer)
              └── FinishedUnit (qty 2 per inner) → Recipe

        Expected: 5 × 3 × 2 = 30
        """
        # Create Recipe
        recipe = Recipe(name="Nested Test Recipe", category="Test")
        test_db.add(recipe)
        test_db.flush()

        # Create FinishedUnit linked to Recipe
        fu = FinishedUnit(
            slug=f"nested-fu-{recipe.id}",
            display_name="Nested FU",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        # Create InnerBundle containing 2 of the FU
        inner_bundle = FinishedGood(slug="inner-bundle", display_name="Inner Bundle")
        test_db.add(inner_bundle)
        test_db.flush()

        inner_comp = Composition(
            assembly_id=inner_bundle.id,
            finished_unit_id=fu.id,
            component_quantity=2.0,
        )
        test_db.add(inner_comp)

        # Create OuterBundle containing 3 of InnerBundle
        outer_bundle = FinishedGood(slug="outer-bundle", display_name="Outer Bundle")
        test_db.add(outer_bundle)
        test_db.flush()

        outer_comp = Composition(
            assembly_id=outer_bundle.id,
            finished_good_id=inner_bundle.id,
            component_quantity=3.0,
        )
        test_db.add(outer_comp)
        test_db.flush()

        # Create Event with 5 of OuterBundle
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=outer_bundle.id,
            quantity=5,
        )
        test_db.add(efg)
        test_db.flush()

        # Execute
        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # Verify: 5 × 3 × 2 = 30
        assert len(result) == 1
        assert result[recipe] == 30

    def test_2_level_nested_with_multiple_recipes(self, test_db, planning_event):
        """
        Given a 2-level nested bundle with multiple recipes at the leaf level
        When decomposed
        Then all recipes are correctly aggregated.

        Structure:
          OuterBundle (qty 2 in event)
          └── InnerBundle (qty 4 per outer)
              ├── FU_A (qty 3 per inner) → RecipeA
              └── FU_B (qty 5 per inner) → RecipeB

        Expected: RecipeA = 2×4×3 = 24, RecipeB = 2×4×5 = 40
        """
        # Create two recipes
        recipe_a = Recipe(name="Recipe A", category="Test")
        recipe_b = Recipe(name="Recipe B", category="Test")
        test_db.add_all([recipe_a, recipe_b])
        test_db.flush()

        # Create FinishedUnits
        fu_a = FinishedUnit(
            slug=f"fu-a-{recipe_a.id}",
            display_name="FU A",
            recipe_id=recipe_a.id,
        )
        fu_b = FinishedUnit(
            slug=f"fu-b-{recipe_b.id}",
            display_name="FU B",
            recipe_id=recipe_b.id,
        )
        test_db.add_all([fu_a, fu_b])
        test_db.flush()

        # Create InnerBundle with both FUs
        inner_bundle = FinishedGood(slug="inner-multi", display_name="Inner Multi")
        test_db.add(inner_bundle)
        test_db.flush()

        comp_a = Composition(
            assembly_id=inner_bundle.id,
            finished_unit_id=fu_a.id,
            component_quantity=3.0,
        )
        comp_b = Composition(
            assembly_id=inner_bundle.id,
            finished_unit_id=fu_b.id,
            component_quantity=5.0,
        )
        test_db.add_all([comp_a, comp_b])

        # Create OuterBundle
        outer_bundle = FinishedGood(slug="outer-multi", display_name="Outer Multi")
        test_db.add(outer_bundle)
        test_db.flush()

        outer_comp = Composition(
            assembly_id=outer_bundle.id,
            finished_good_id=inner_bundle.id,
            component_quantity=4.0,
        )
        test_db.add(outer_comp)
        test_db.flush()

        # Event with qty 2
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=outer_bundle.id,
            quantity=2,
        )
        test_db.add(efg)
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # RecipeA: 2 × 4 × 3 = 24
        # RecipeB: 2 × 4 × 5 = 40
        assert len(result) == 2
        assert result[recipe_a] == 24
        assert result[recipe_b] == 40


# ============================================================================
# T008: Tests for 3+ level nested bundles
# ============================================================================


class TestDeepNestedBundles:
    """Tests for User Story 2, Scenario 2: 3+ level nested bundle decomposition."""

    def test_3_level_nested_bundle_traverses_all_levels(self, test_db, planning_event):
        """
        Given a bundle with 3 levels of nesting
        When decomposed
        Then all levels are traversed and final atomic quantities are correct.

        Structure:
          Level1Bundle (qty 2 in event)
          └── Level2Bundle (qty 3 per L1)
              └── Level3Bundle (qty 4 per L2)
                  └── FinishedUnit (qty 5 per L3) → Recipe

        Expected: 2 × 3 × 4 × 5 = 120
        """
        # Create Recipe
        recipe = Recipe(name="Deep Nested Recipe", category="Test")
        test_db.add(recipe)
        test_db.flush()

        # Create FinishedUnit
        fu = FinishedUnit(
            slug=f"deep-fu-{recipe.id}",
            display_name="Deep FU",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        # Level 3 Bundle (innermost): contains FU with qty 5
        level3 = FinishedGood(slug="level-3-bundle", display_name="Level 3")
        test_db.add(level3)
        test_db.flush()
        comp3 = Composition(
            assembly_id=level3.id,
            finished_unit_id=fu.id,
            component_quantity=5.0,
        )
        test_db.add(comp3)

        # Level 2 Bundle: contains Level 3 with qty 4
        level2 = FinishedGood(slug="level-2-bundle", display_name="Level 2")
        test_db.add(level2)
        test_db.flush()
        comp2 = Composition(
            assembly_id=level2.id,
            finished_good_id=level3.id,
            component_quantity=4.0,
        )
        test_db.add(comp2)

        # Level 1 Bundle (outermost): contains Level 2 with qty 3
        level1 = FinishedGood(slug="level-1-bundle", display_name="Level 1")
        test_db.add(level1)
        test_db.flush()
        comp1 = Composition(
            assembly_id=level1.id,
            finished_good_id=level2.id,
            component_quantity=3.0,
        )
        test_db.add(comp1)
        test_db.flush()

        # Event with qty 2
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=level1.id,
            quantity=2,
        )
        test_db.add(efg)
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # 2 × 3 × 4 × 5 = 120
        assert len(result) == 1
        assert result[recipe] == 120

    def test_4_level_nested_bundle_with_branching(self, test_db, planning_event):
        """
        Given a 4-level nested structure with branching at middle levels
        When decomposed
        Then all paths are followed and quantities aggregate correctly.

        Structure:
          L1 (qty 1 in event)
          └── L2 (qty 2 per L1)
              ├── L3a (qty 3 per L2)
              │   └── FU → RecipeA (qty 1)
              └── L3b (qty 4 per L2)
                  └── L4 (qty 5 per L3b)
                      └── FU → RecipeB (qty 1)

        Expected: RecipeA = 1×2×3×1 = 6, RecipeB = 1×2×4×5×1 = 40
        """
        # Create recipes
        recipe_a = Recipe(name="Recipe A Deep", category="Test")
        recipe_b = Recipe(name="Recipe B Deep", category="Test")
        test_db.add_all([recipe_a, recipe_b])
        test_db.flush()

        # Create FUs
        fu_a = FinishedUnit(
            slug=f"fu-a-deep-{recipe_a.id}",
            display_name="FU A Deep",
            recipe_id=recipe_a.id,
        )
        fu_b = FinishedUnit(
            slug=f"fu-b-deep-{recipe_b.id}",
            display_name="FU B Deep",
            recipe_id=recipe_b.id,
        )
        test_db.add_all([fu_a, fu_b])
        test_db.flush()

        # L4: contains FU_B (qty 1)
        l4 = FinishedGood(slug="l4-bundle", display_name="L4")
        test_db.add(l4)
        test_db.flush()
        test_db.add(Composition(assembly_id=l4.id, finished_unit_id=fu_b.id, component_quantity=1.0))

        # L3b: contains L4 (qty 5)
        l3b = FinishedGood(slug="l3b-bundle", display_name="L3b")
        test_db.add(l3b)
        test_db.flush()
        test_db.add(Composition(assembly_id=l3b.id, finished_good_id=l4.id, component_quantity=5.0))

        # L3a: contains FU_A (qty 1)
        l3a = FinishedGood(slug="l3a-bundle", display_name="L3a")
        test_db.add(l3a)
        test_db.flush()
        test_db.add(Composition(assembly_id=l3a.id, finished_unit_id=fu_a.id, component_quantity=1.0))

        # L2: contains L3a (qty 3) and L3b (qty 4)
        l2 = FinishedGood(slug="l2-bundle", display_name="L2")
        test_db.add(l2)
        test_db.flush()
        test_db.add(Composition(assembly_id=l2.id, finished_good_id=l3a.id, component_quantity=3.0))
        test_db.add(Composition(assembly_id=l2.id, finished_good_id=l3b.id, component_quantity=4.0))

        # L1: contains L2 (qty 2)
        l1 = FinishedGood(slug="l1-bundle", display_name="L1")
        test_db.add(l1)
        test_db.flush()
        test_db.add(Composition(assembly_id=l1.id, finished_good_id=l2.id, component_quantity=2.0))
        test_db.flush()

        # Event with qty 1
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=l1.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # RecipeA: 1 × 2 × 3 × 1 = 6
        # RecipeB: 1 × 2 × 4 × 5 × 1 = 40
        assert len(result) == 2
        assert result[recipe_a] == 6
        assert result[recipe_b] == 40


# ============================================================================
# T009: Tests for DAG patterns (same FG in multiple branches)
# ============================================================================


class TestDAGPatterns:
    """Tests for DAG patterns where the same FG appears in multiple branches."""

    def test_dag_pattern_same_fu_multiple_branches_allowed(self, test_db, planning_event):
        """
        Given a bundle structure where the same FinishedUnit appears in multiple branches (DAG)
        When decomposed
        Then no circular reference error is raised and quantities aggregate correctly.

        Structure:
          MainBundle (qty 1 in event)
          ├── BranchA (qty 2)
          │   └── SharedFU (qty 3) → Recipe
          └── BranchB (qty 4)
              └── SharedFU (qty 5) → Recipe (SAME FU!)

        Expected: (2 × 3) + (4 × 5) = 6 + 20 = 26
        """
        # Create Recipe
        recipe = Recipe(name="Shared Recipe", category="Test")
        test_db.add(recipe)
        test_db.flush()

        # Create SharedFU used in both branches
        shared_fu = FinishedUnit(
            slug=f"shared-fu-{recipe.id}",
            display_name="Shared FU",
            recipe_id=recipe.id,
        )
        test_db.add(shared_fu)
        test_db.flush()

        # Create BranchA containing SharedFU (qty 3)
        branch_a = FinishedGood(slug="branch-a", display_name="Branch A")
        test_db.add(branch_a)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=branch_a.id,
                finished_unit_id=shared_fu.id,
                component_quantity=3.0,
            )
        )

        # Create BranchB containing SharedFU (qty 5)
        branch_b = FinishedGood(slug="branch-b", display_name="Branch B")
        test_db.add(branch_b)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=branch_b.id,
                finished_unit_id=shared_fu.id,
                component_quantity=5.0,
            )
        )

        # Create MainBundle containing BranchA (qty 2) and BranchB (qty 4)
        main_bundle = FinishedGood(slug="main-bundle-dag", display_name="Main Bundle DAG")
        test_db.add(main_bundle)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=main_bundle.id,
                finished_good_id=branch_a.id,
                component_quantity=2.0,
            )
        )
        test_db.add(
            Composition(
                assembly_id=main_bundle.id,
                finished_good_id=branch_b.id,
                component_quantity=4.0,
            )
        )
        test_db.flush()

        # Event with qty 1
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=main_bundle.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        # Should NOT raise CircularReferenceError
        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # Should aggregate: (2×3) + (4×5) = 26
        assert len(result) == 1
        assert result[recipe] == 26

    def test_dag_pattern_same_bundle_multiple_branches(self, test_db, planning_event):
        """
        Given a structure where the same inner bundle appears in multiple branches
        When decomposed
        Then path-based detection allows this DAG pattern.

        Structure:
          Root (qty 1 in event)
          ├── PathA (qty 2)
          │   └── SharedBundle (qty 1)
          │       └── FU (qty 3) → Recipe
          └── PathB (qty 3)
              └── SharedBundle (qty 1) (SAME BUNDLE!)
                  └── FU (qty 3) → Recipe

        Expected: (2×1×3) + (3×1×3) = 6 + 9 = 15
        """
        # Create Recipe and FU
        recipe = Recipe(name="DAG Bundle Recipe", category="Test")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug=f"dag-fu-{recipe.id}",
            display_name="DAG FU",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        # SharedBundle containing FU (qty 3)
        shared_bundle = FinishedGood(slug="shared-bundle", display_name="Shared Bundle")
        test_db.add(shared_bundle)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=shared_bundle.id,
                finished_unit_id=fu.id,
                component_quantity=3.0,
            )
        )

        # PathA containing SharedBundle (qty 1)
        path_a = FinishedGood(slug="path-a", display_name="Path A")
        test_db.add(path_a)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=path_a.id,
                finished_good_id=shared_bundle.id,
                component_quantity=1.0,
            )
        )

        # PathB containing SharedBundle (qty 1)
        path_b = FinishedGood(slug="path-b", display_name="Path B")
        test_db.add(path_b)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=path_b.id,
                finished_good_id=shared_bundle.id,
                component_quantity=1.0,
            )
        )

        # Root containing PathA (qty 2) and PathB (qty 3)
        root = FinishedGood(slug="dag-root", display_name="DAG Root")
        test_db.add(root)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=root.id,
                finished_good_id=path_a.id,
                component_quantity=2.0,
            )
        )
        test_db.add(
            Composition(
                assembly_id=root.id,
                finished_good_id=path_b.id,
                component_quantity=3.0,
            )
        )
        test_db.flush()

        # Event with qty 1
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=root.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        # Should NOT raise CircularReferenceError - this is DAG, not circular
        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # (2×1×3) + (3×1×3) = 6 + 9 = 15
        assert len(result) == 1
        assert result[recipe] == 15


# ============================================================================
# T010: Tests for mixed atomic/bundle events
# ============================================================================


class TestMixedAtomicAndBundleEvents:
    """Tests for events containing both atomic FGs and bundle FGs."""

    def test_mixed_atomic_and_bundle_fgs_process_correctly(self, test_db, planning_event):
        """
        Given a mix of atomic FGs and bundles in the same event
        When decomposed
        Then atomic FGs pass through unchanged while bundles are expanded.

        Structure:
          Event contains:
          - AtomicFG (qty 10) → direct FinishedUnit → RecipeA
          - BundleFG (qty 5)
            └── FinishedUnit (qty 2) → RecipeB

        Expected: RecipeA = 10, RecipeB = 10 (5 × 2)
        """
        # Create recipes
        recipe_a = Recipe(name="Atomic Recipe", category="Test")
        recipe_b = Recipe(name="Bundle Recipe", category="Test")
        test_db.add_all([recipe_a, recipe_b])
        test_db.flush()

        # Create FUs
        fu_a = FinishedUnit(
            slug=f"fu-atomic-{recipe_a.id}",
            display_name="FU Atomic",
            recipe_id=recipe_a.id,
        )
        fu_b = FinishedUnit(
            slug=f"fu-bundle-{recipe_b.id}",
            display_name="FU Bundle",
            recipe_id=recipe_b.id,
        )
        test_db.add_all([fu_a, fu_b])
        test_db.flush()

        # Create Atomic FG (single FU component with qty 1)
        atomic_fg = FinishedGood(slug="atomic-fg", display_name="Atomic FG")
        test_db.add(atomic_fg)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=atomic_fg.id,
                finished_unit_id=fu_a.id,
                component_quantity=1.0,
            )
        )

        # Create Bundle FG (FU component with qty 2)
        bundle_fg = FinishedGood(slug="bundle-fg-mixed", display_name="Bundle FG")
        test_db.add(bundle_fg)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=bundle_fg.id,
                finished_unit_id=fu_b.id,
                component_quantity=2.0,
            )
        )
        test_db.flush()

        # Event has: atomic (qty 10), bundle (qty 5)
        efg_atomic = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=atomic_fg.id,
            quantity=10,
        )
        efg_bundle = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=bundle_fg.id,
            quantity=5,
        )
        test_db.add_all([efg_atomic, efg_bundle])
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # Atomic: 10 × 1 = 10
        # Bundle: 5 × 2 = 10
        assert len(result) == 2
        assert result[recipe_a] == 10
        assert result[recipe_b] == 10

    def test_mixed_atomic_bundle_and_nested_in_same_event(self, test_db, planning_event):
        """
        Given an event with atomic, simple bundle, and nested bundle FGs
        When decomposed
        Then all types process correctly with proper aggregation.

        Structure:
          Event contains:
          - AtomicFG (qty 3) → FU → RecipeA
          - SimpleBundleFG (qty 2)
            └── FU (qty 4) → RecipeA (same recipe!)
          - NestedBundleFG (qty 1)
            └── InnerBundle (qty 2)
                └── FU (qty 3) → RecipeB

        Expected: RecipeA = (3×1) + (2×4) = 11, RecipeB = 1×2×3 = 6
        """
        # Create recipes
        recipe_a = Recipe(name="Shared Recipe Mixed", category="Test")
        recipe_b = Recipe(name="Nested Only Recipe", category="Test")
        test_db.add_all([recipe_a, recipe_b])
        test_db.flush()

        # Create FUs
        fu_a = FinishedUnit(
            slug=f"fu-shared-{recipe_a.id}",
            display_name="FU Shared",
            recipe_id=recipe_a.id,
        )
        fu_b = FinishedUnit(
            slug=f"fu-nested-{recipe_b.id}",
            display_name="FU Nested",
            recipe_id=recipe_b.id,
        )
        test_db.add_all([fu_a, fu_b])
        test_db.flush()

        # AtomicFG: single FU_A with qty 1
        atomic_fg = FinishedGood(slug="atomic-mixed", display_name="Atomic Mixed")
        test_db.add(atomic_fg)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=atomic_fg.id,
                finished_unit_id=fu_a.id,
                component_quantity=1.0,
            )
        )

        # SimpleBundleFG: FU_A with qty 4
        simple_bundle = FinishedGood(slug="simple-bundle", display_name="Simple Bundle")
        test_db.add(simple_bundle)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=simple_bundle.id,
                finished_unit_id=fu_a.id,
                component_quantity=4.0,
            )
        )

        # InnerBundle: FU_B with qty 3
        inner_bundle = FinishedGood(slug="inner-nested", display_name="Inner Nested")
        test_db.add(inner_bundle)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=inner_bundle.id,
                finished_unit_id=fu_b.id,
                component_quantity=3.0,
            )
        )

        # NestedBundleFG: InnerBundle with qty 2
        nested_bundle = FinishedGood(slug="nested-bundle", display_name="Nested Bundle")
        test_db.add(nested_bundle)
        test_db.flush()
        test_db.add(
            Composition(
                assembly_id=nested_bundle.id,
                finished_good_id=inner_bundle.id,
                component_quantity=2.0,
            )
        )
        test_db.flush()

        # Event: atomic (qty 3), simple bundle (qty 2), nested bundle (qty 1)
        test_db.add_all(
            [
                EventFinishedGood(
                    event_id=planning_event.id,
                    finished_good_id=atomic_fg.id,
                    quantity=3,
                ),
                EventFinishedGood(
                    event_id=planning_event.id,
                    finished_good_id=simple_bundle.id,
                    quantity=2,
                ),
                EventFinishedGood(
                    event_id=planning_event.id,
                    finished_good_id=nested_bundle.id,
                    quantity=1,
                ),
            ]
        )
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # RecipeA: (3×1) + (2×4) = 3 + 8 = 11
        # RecipeB: 1×2×3 = 6
        assert len(result) == 2
        assert result[recipe_a] == 11
        assert result[recipe_b] == 6
# ============================================================================
# T011: Tests for circular reference detection
# ============================================================================


class TestCircularReferenceDetection:
    """Tests for User Story 3, Scenario 1: Circular reference detection."""

    def test_indirect_circular_reference_raises_error(self, test_db, planning_event):
        """
        Given a bundle that references itself indirectly (A → B → A)
        When decomposition is attempted
        Then a CircularReferenceError is raised.
        """
        # Create two bundles
        bundle_a = FinishedGood(slug="circular-a", display_name="Bundle A")
        bundle_b = FinishedGood(slug="circular-b", display_name="Bundle B")
        test_db.add_all([bundle_a, bundle_b])
        test_db.flush()

        # Create circular structure: A → B → A
        # BundleA contains BundleB
        comp_a_to_b = Composition(
            assembly_id=bundle_a.id,
            finished_good_id=bundle_b.id,
            component_quantity=1.0,
        )
        test_db.add(comp_a_to_b)
        test_db.flush()

        # BundleB contains BundleA (creates cycle)
        # Note: The DB check constraint ck_composition_no_self_reference only prevents
        # direct self-reference (assembly_id != finished_good_id), not indirect cycles
        comp_b_to_a = Composition(
            assembly_id=bundle_b.id,
            finished_good_id=bundle_a.id,
            component_quantity=1.0,
        )
        test_db.add(comp_b_to_a)
        test_db.flush()

        # Refresh to ensure relationships are loaded
        test_db.expire_all()

        # Create event with bundle_a
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=bundle_a.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        # Should raise CircularReferenceError
        with pytest.raises(CircularReferenceError) as exc_info:
            calculate_recipe_requirements(planning_event.id, session=test_db)

        # Verify one of the bundle IDs is in the error path
        assert bundle_a.id in exc_info.value.path or bundle_b.id in exc_info.value.path

    def test_3_bundle_circular_chain_raises_error(self, test_db, planning_event):
        """
        Given a longer circular chain (A → B → C → A)
        When decomposition is attempted
        Then a CircularReferenceError is raised.
        """
        # Create three bundles
        bundle_a = FinishedGood(slug="chain-a", display_name="Chain A")
        bundle_b = FinishedGood(slug="chain-b", display_name="Chain B")
        bundle_c = FinishedGood(slug="chain-c", display_name="Chain C")
        test_db.add_all([bundle_a, bundle_b, bundle_c])
        test_db.flush()

        # A → B
        test_db.add(
            Composition(
                assembly_id=bundle_a.id,
                finished_good_id=bundle_b.id,
                component_quantity=1.0,
            )
        )
        # B → C
        test_db.add(
            Composition(
                assembly_id=bundle_b.id,
                finished_good_id=bundle_c.id,
                component_quantity=1.0,
            )
        )
        # C → A (completes cycle) - indirect reference, not blocked by DB constraint
        test_db.add(
            Composition(
                assembly_id=bundle_c.id,
                finished_good_id=bundle_a.id,
                component_quantity=1.0,
            )
        )
        test_db.flush()

        # Refresh to ensure relationships are loaded
        test_db.expire_all()

        # Create event
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=bundle_a.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        with pytest.raises(CircularReferenceError):
            calculate_recipe_requirements(planning_event.id, session=test_db)


# ============================================================================
# T012: Tests for empty event handling
# ============================================================================


class TestEmptyEventHandling:
    """Tests for User Story 3, Scenario 3: Empty event handling."""

    def test_empty_event_returns_empty_dict(self, test_db):
        """
        Given an event with no FG selections
        When recipe requirements are calculated
        Then an empty dictionary is returned (not an error).
        """
        # Create event with no EventFinishedGoods
        event = Event(
            name="Empty Event",
            event_date=date(2026, 12, 25),
            year=2026,
        )
        test_db.add(event)
        test_db.flush()

        result = calculate_recipe_requirements(event.id, session=test_db)

        assert result == {}
        assert isinstance(result, dict)

    def test_nonexistent_event_raises_validation_error(self, test_db):
        """
        Given an event ID that doesn't exist
        When recipe requirements are requested
        Then a ValidationError is raised.
        """
        nonexistent_id = 99999

        with pytest.raises(ValidationError) as exc_info:
            calculate_recipe_requirements(nonexistent_id, session=test_db)

        # Verify error message mentions the event
        assert "99999" in str(exc_info.value) or "not found" in str(exc_info.value).lower()


# ============================================================================
# T013: Tests for missing recipe validation
# ============================================================================


class TestMissingRecipeValidation:
    """Tests for User Story 3, Scenario 2: Missing recipe validation."""

    def test_finished_unit_without_recipe_raises_validation_error(
        self, test_db, planning_event
    ):
        """
        Given a FinishedGood that contains a FinishedUnit without a linked recipe
        When recipe mapping is attempted
        Then a ValidationError is raised with a clear message.

        Note: The schema requires recipe_id to be NOT NULL with ondelete=CASCADE,
        so a FinishedUnit cannot exist in the DB without a valid recipe in normal
        operation. We use mocking to test the defensive code path that handles
        fu.recipe being None (e.g., data corruption, manual DB edits).
        """
        # Create recipe and FU (valid state initially)
        recipe = Recipe(name="Test Recipe", category="Test")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug="fu-with-recipe",
            display_name="FU With Recipe",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        # Create FG containing this FU
        fg = FinishedGood(slug="test-fg-missing-recipe", display_name="Test FG")
        test_db.add(fg)
        test_db.flush()

        comp = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu.id,
            component_quantity=1.0,
        )
        test_db.add(comp)
        test_db.flush()

        # Create event
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=fg.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        # Mock the recipe relationship to return None
        # This simulates data corruption where recipe_id points to a deleted recipe
        with patch.object(
            FinishedUnit, "recipe", new_callable=PropertyMock, return_value=None
        ):
            with pytest.raises(ValidationError) as exc_info:
                calculate_recipe_requirements(planning_event.id, session=test_db)

            # Verify error message is clear about the missing recipe
            error_msg = str(exc_info.value).lower()
            assert "no recipe" in error_msg


# ============================================================================
# T014: Tests for zero-quantity component handling
# ============================================================================


class TestZeroQuantityHandling:
    """Tests for edge case: zero-quantity components are skipped."""

    def test_zero_effective_quantity_from_small_multiplier_skipped(
        self, test_db, planning_event
    ):
        """
        Given a bundle with component that results in effective_qty = 0
        When decomposed with a multiplier that makes effective_qty < 1
        Then the component is skipped.

        Note: The DB has a CHECK constraint requiring component_quantity > 0,
        so we test the zero-quantity code path by having effective_qty round to 0
        due to the int() conversion: int(0.4 * 1) = 0.
        """
        # Create two recipes
        recipe_included = Recipe(name="Included Recipe", category="Test")
        recipe_excluded = Recipe(name="Excluded Recipe", category="Test")
        test_db.add_all([recipe_included, recipe_excluded])
        test_db.flush()

        # Create FUs
        fu_included = FinishedUnit(
            slug=f"fu-included-{recipe_included.id}",
            display_name="FU Included",
            recipe_id=recipe_included.id,
        )
        fu_excluded = FinishedUnit(
            slug=f"fu-excluded-{recipe_excluded.id}",
            display_name="FU Excluded",
            recipe_id=recipe_excluded.id,
        )
        test_db.add_all([fu_included, fu_excluded])
        test_db.flush()

        # Create bundle
        bundle = FinishedGood(slug="effective-zero-bundle", display_name="Effective Zero Bundle")
        test_db.add(bundle)
        test_db.flush()

        # Add normal component (qty 2) - will be 2*1 = 2
        comp_normal = Composition(
            assembly_id=bundle.id,
            finished_unit_id=fu_included.id,
            component_quantity=2.0,
        )
        test_db.add(comp_normal)

        # Add component with 0.4 qty - will be int(0.4*1) = 0, should be skipped
        comp_fractional = Composition(
            assembly_id=bundle.id,
            finished_unit_id=fu_excluded.id,
            component_quantity=0.4,
        )
        test_db.add(comp_fractional)
        test_db.flush()

        # Create event with qty 1
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=bundle.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # Only recipe_included should be in result (qty = 1 * 2 = 2)
        # recipe_excluded should be skipped due to effective_qty = int(0.4) = 0
        assert recipe_included in result
        assert result[recipe_included] == 2
        assert recipe_excluded not in result

    def test_small_fractional_quantity_that_rounds_to_zero_skipped(
        self, test_db, planning_event
    ):
        """
        Given a component with small fractional quantity that rounds to zero
        When decomposed with a small multiplier
        Then the component is skipped.

        Example: component_quantity=0.1, multiplier=1 → effective_qty = int(0.1) = 0
        """
        # Create recipe and FU
        recipe = Recipe(name="Fractional Recipe", category="Test")
        test_db.add(recipe)
        test_db.flush()

        fu = FinishedUnit(
            slug=f"fractional-fu-{recipe.id}",
            display_name="Fractional FU",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        # Create bundle
        bundle = FinishedGood(slug="fractional-bundle", display_name="Fractional Bundle")
        test_db.add(bundle)
        test_db.flush()

        # Add fractional component (0.3) - this is valid per constraint (> 0)
        comp = Composition(
            assembly_id=bundle.id,
            finished_unit_id=fu.id,
            component_quantity=0.3,
        )
        test_db.add(comp)
        test_db.flush()

        # Create event with qty 1
        # effective_qty = int(0.3 * 1) = 0 → should be skipped
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=bundle.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        result = calculate_recipe_requirements(planning_event.id, session=test_db)

        # Recipe should NOT be in result because effective quantity rounds to 0
        assert recipe not in result or result.get(recipe, 0) == 0
