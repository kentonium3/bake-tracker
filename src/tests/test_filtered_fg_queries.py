"""
Tests for filtered FG query service functions (F100 WP01).

Tests cover:
- get_filtered_available_fgs (T003)
- get_available_recipe_categories_for_event (T004)
"""

import pytest
from datetime import date

from src.models.assembly_type import AssemblyType
from src.models.composition import Composition
from src.models.event import Event
from src.models.event_recipe import EventRecipe
from src.models.finished_good import FinishedGood
from src.models.finished_unit import FinishedUnit
from src.models.recipe import Recipe
from src.services.event_service import (
    get_filtered_available_fgs,
    get_available_recipe_categories_for_event,
    get_available_finished_goods,
    set_event_recipes,
)
from src.services.exceptions import ValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def planning_event(test_db):
    """Create a test event for filtered FG query tests."""
    event = Event(
        name="Filter Test Event",
        event_date=date(2026, 12, 25),
        year=2026,
    )
    test_db.add(event)
    test_db.flush()
    return event


@pytest.fixture
def cookie_recipe(test_db):
    """Create a cookie recipe with category 'Cookies'."""
    recipe = Recipe(name="Sugar Cookies", category="Cookies")
    test_db.add(recipe)
    test_db.flush()
    return recipe


@pytest.fixture
def cake_recipe(test_db):
    """Create a cake recipe with category 'Cakes'."""
    recipe = Recipe(name="Chocolate Cake", category="Cakes")
    test_db.add(recipe)
    test_db.flush()
    return recipe


@pytest.fixture
def bread_recipe(test_db):
    """Create a bread recipe with category 'Breads'."""
    recipe = Recipe(name="Sourdough Bread", category="Breads")
    test_db.add(recipe)
    test_db.flush()
    return recipe


@pytest.fixture
def cookie_fu_ea(test_db, cookie_recipe):
    """Create a cookie FinishedUnit with yield_type EA."""
    fu = FinishedUnit(
        slug="sugar-cookie-ea",
        display_name="Sugar Cookie (EA)",
        recipe_id=cookie_recipe.id,
        yield_type="EA",
    )
    test_db.add(fu)
    test_db.flush()
    return fu


@pytest.fixture
def cookie_fu_serving(test_db, cookie_recipe):
    """Create a cookie FinishedUnit with yield_type SERVING."""
    fu = FinishedUnit(
        slug="sugar-cookie-serving",
        display_name="Sugar Cookie (Serving)",
        recipe_id=cookie_recipe.id,
        yield_type="SERVING",
    )
    test_db.add(fu)
    test_db.flush()
    return fu


@pytest.fixture
def cake_fu_ea(test_db, cake_recipe):
    """Create a cake FinishedUnit with yield_type EA."""
    fu = FinishedUnit(
        slug="chocolate-cake-ea",
        display_name="Chocolate Cake (EA)",
        recipe_id=cake_recipe.id,
        yield_type="EA",
    )
    test_db.add(fu)
    test_db.flush()
    return fu


@pytest.fixture
def bread_fu_serving(test_db, bread_recipe):
    """Create a bread FinishedUnit with yield_type SERVING."""
    fu = FinishedUnit(
        slug="sourdough-bread-serving",
        display_name="Sourdough Bread (Serving)",
        recipe_id=bread_recipe.id,
        yield_type="SERVING",
    )
    test_db.add(fu)
    test_db.flush()
    return fu


@pytest.fixture
def bare_cookie_ea(test_db, cookie_fu_ea):
    """Create a BARE FG wrapping cookie FU (EA yield)."""
    fg = FinishedGood(
        slug="bare-cookie-ea",
        display_name="Bare Cookie EA",
        assembly_type=AssemblyType.BARE,
    )
    test_db.add(fg)
    test_db.flush()
    comp = Composition(
        assembly_id=fg.id,
        finished_unit_id=cookie_fu_ea.id,
        component_quantity=1.0,
    )
    test_db.add(comp)
    test_db.flush()
    return fg


@pytest.fixture
def bare_cookie_serving(test_db, cookie_fu_serving):
    """Create a BARE FG wrapping cookie FU (SERVING yield)."""
    fg = FinishedGood(
        slug="bare-cookie-serving",
        display_name="Bare Cookie Serving",
        assembly_type=AssemblyType.BARE,
    )
    test_db.add(fg)
    test_db.flush()
    comp = Composition(
        assembly_id=fg.id,
        finished_unit_id=cookie_fu_serving.id,
        component_quantity=1.0,
    )
    test_db.add(comp)
    test_db.flush()
    return fg


@pytest.fixture
def bare_cake_ea(test_db, cake_fu_ea):
    """Create a BARE FG wrapping cake FU (EA yield)."""
    fg = FinishedGood(
        slug="bare-cake-ea",
        display_name="Bare Cake EA",
        assembly_type=AssemblyType.BARE,
    )
    test_db.add(fg)
    test_db.flush()
    comp = Composition(
        assembly_id=fg.id,
        finished_unit_id=cake_fu_ea.id,
        component_quantity=1.0,
    )
    test_db.add(comp)
    test_db.flush()
    return fg


@pytest.fixture
def bundle_cookie_cake(test_db, cookie_fu_ea, cake_fu_ea):
    """Create a BUNDLE FG containing cookie and cake FUs."""
    fg = FinishedGood(
        slug="bundle-cookie-cake",
        display_name="Cookie & Cake Bundle",
        assembly_type=AssemblyType.BUNDLE,
    )
    test_db.add(fg)
    test_db.flush()
    comp1 = Composition(
        assembly_id=fg.id,
        finished_unit_id=cookie_fu_ea.id,
        component_quantity=1.0,
        sort_order=0,
    )
    comp2 = Composition(
        assembly_id=fg.id,
        finished_unit_id=cake_fu_ea.id,
        component_quantity=1.0,
        sort_order=1,
    )
    test_db.add(comp1)
    test_db.add(comp2)
    test_db.flush()
    return fg


@pytest.fixture
def all_fgs_with_recipes_selected(
    test_db,
    planning_event,
    cookie_recipe,
    cake_recipe,
    bare_cookie_ea,
    bare_cookie_serving,
    bare_cake_ea,
    bundle_cookie_cake,
):
    """Select all recipes so all FGs are available."""
    set_event_recipes(
        test_db,
        planning_event.id,
        [cookie_recipe.id, cake_recipe.id],
    )
    test_db.flush()
    return {
        "bare_cookie_ea": bare_cookie_ea,
        "bare_cookie_serving": bare_cookie_serving,
        "bare_cake_ea": bare_cake_ea,
        "bundle_cookie_cake": bundle_cookie_cake,
    }


# ============================================================================
# T003: Tests for get_filtered_available_fgs
# ============================================================================


class TestFilteredAvailableFGs:
    """Tests for get_filtered_available_fgs."""

    def test_no_filters_returns_all_available(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """No filters applied returns same as get_available_finished_goods."""
        fgs = all_fgs_with_recipes_selected
        result = get_filtered_available_fgs(planning_event.id, test_db)
        unfiltered = get_available_finished_goods(planning_event.id, test_db)

        assert len(result) == len(unfiltered)
        result_ids = {fg.id for fg in result}
        unfiltered_ids = {fg.id for fg in unfiltered}
        assert result_ids == unfiltered_ids

    def test_filter_by_recipe_category(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """Filter by recipe_category='Cookies' returns only cookie-recipe FGs."""
        fgs = all_fgs_with_recipes_selected
        result = get_filtered_available_fgs(
            planning_event.id, test_db, recipe_category="Cookies"
        )
        result_ids = {fg.id for fg in result}

        # bare_cookie_ea, bare_cookie_serving, and bundle_cookie_cake all
        # contain cookie recipe components
        assert fgs["bare_cookie_ea"].id in result_ids
        assert fgs["bare_cookie_serving"].id in result_ids
        assert fgs["bundle_cookie_cake"].id in result_ids
        # bare_cake_ea does NOT have cookie recipe
        assert fgs["bare_cake_ea"].id not in result_ids

    def test_filter_by_assembly_type_bare(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """Filter by assembly_type='bare' returns only BARE FGs."""
        fgs = all_fgs_with_recipes_selected
        result = get_filtered_available_fgs(
            planning_event.id, test_db, assembly_type="bare"
        )
        result_ids = {fg.id for fg in result}

        assert fgs["bare_cookie_ea"].id in result_ids
        assert fgs["bare_cookie_serving"].id in result_ids
        assert fgs["bare_cake_ea"].id in result_ids
        assert fgs["bundle_cookie_cake"].id not in result_ids

    def test_filter_by_assembly_type_bundle(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """Filter by assembly_type='bundle' returns only BUNDLE FGs."""
        fgs = all_fgs_with_recipes_selected
        result = get_filtered_available_fgs(
            planning_event.id, test_db, assembly_type="bundle"
        )
        result_ids = {fg.id for fg in result}

        assert fgs["bundle_cookie_cake"].id in result_ids
        assert fgs["bare_cookie_ea"].id not in result_ids
        assert fgs["bare_cookie_serving"].id not in result_ids
        assert fgs["bare_cake_ea"].id not in result_ids

    def test_filter_by_yield_type_ea(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """Filter by yield_type='EA' returns only BARE FGs with EA yield."""
        fgs = all_fgs_with_recipes_selected
        result = get_filtered_available_fgs(
            planning_event.id, test_db, yield_type="EA"
        )
        result_ids = {fg.id for fg in result}

        assert fgs["bare_cookie_ea"].id in result_ids
        assert fgs["bare_cake_ea"].id in result_ids
        # SERVING yield excluded
        assert fgs["bare_cookie_serving"].id not in result_ids
        # BUNDLEs excluded when yield_type is specified
        assert fgs["bundle_cookie_cake"].id not in result_ids

    def test_filter_by_yield_type_excludes_bundles(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """Yield type filter always excludes BUNDLE FGs."""
        fgs = all_fgs_with_recipes_selected
        for yt in ("EA", "SERVING"):
            result = get_filtered_available_fgs(
                planning_event.id, test_db, yield_type=yt
            )
            result_ids = {fg.id for fg in result}
            assert fgs["bundle_cookie_cake"].id not in result_ids

    def test_combined_category_and_type(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """Combined recipe_category + assembly_type applies AND logic."""
        fgs = all_fgs_with_recipes_selected
        result = get_filtered_available_fgs(
            planning_event.id,
            test_db,
            recipe_category="Cookies",
            assembly_type="bare",
        )
        result_ids = {fg.id for fg in result}

        # Only bare cookie FGs
        assert fgs["bare_cookie_ea"].id in result_ids
        assert fgs["bare_cookie_serving"].id in result_ids
        # Bundle excluded by assembly_type
        assert fgs["bundle_cookie_cake"].id not in result_ids
        # Cake excluded by category
        assert fgs["bare_cake_ea"].id not in result_ids

    def test_all_three_filters(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """All three filters applied with AND logic, yield_type excludes BUNDLEs."""
        fgs = all_fgs_with_recipes_selected
        result = get_filtered_available_fgs(
            planning_event.id,
            test_db,
            recipe_category="Cookies",
            assembly_type="bare",
            yield_type="EA",
        )
        result_ids = {fg.id for fg in result}

        # Only bare cookie EA
        assert result_ids == {fgs["bare_cookie_ea"].id}

    def test_no_matches_returns_empty(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """Filters that match nothing return empty list."""
        result = get_filtered_available_fgs(
            planning_event.id,
            test_db,
            recipe_category="Nonexistent Category",
        )
        assert result == []

    def test_no_recipes_selected_returns_empty(
        self, test_db, planning_event, bare_cookie_ea, cookie_recipe
    ):
        """Event with no recipe selections returns empty list."""
        # Don't select any recipes
        result = get_filtered_available_fgs(planning_event.id, test_db)
        assert result == []

    def test_filter_category_cakes_only(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """Filter by recipe_category='Cakes' returns only cake-recipe FGs."""
        fgs = all_fgs_with_recipes_selected
        result = get_filtered_available_fgs(
            planning_event.id, test_db, recipe_category="Cakes"
        )
        result_ids = {fg.id for fg in result}

        assert fgs["bare_cake_ea"].id in result_ids
        # Bundle has cake component too
        assert fgs["bundle_cookie_cake"].id in result_ids
        # Cookie-only FGs excluded
        assert fgs["bare_cookie_ea"].id not in result_ids
        assert fgs["bare_cookie_serving"].id not in result_ids

    def test_yield_type_serving(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """Filter by yield_type='SERVING' returns only BARE SERVING FGs."""
        fgs = all_fgs_with_recipes_selected
        result = get_filtered_available_fgs(
            planning_event.id, test_db, yield_type="SERVING"
        )
        result_ids = {fg.id for fg in result}

        assert fgs["bare_cookie_serving"].id in result_ids
        assert fgs["bare_cookie_ea"].id not in result_ids
        assert fgs["bare_cake_ea"].id not in result_ids
        assert fgs["bundle_cookie_cake"].id not in result_ids

    def test_raises_for_nonexistent_event(self, test_db):
        """Raises ValidationError for non-existent event."""
        with pytest.raises(ValidationError, match="Event .* not found"):
            get_filtered_available_fgs(99999, test_db)


# ============================================================================
# T004: Tests for get_available_recipe_categories_for_event
# ============================================================================


class TestAvailableRecipeCategoriesForEvent:
    """Tests for get_available_recipe_categories_for_event."""

    def test_returns_distinct_categories(
        self,
        test_db,
        planning_event,
        cookie_recipe,
        bare_cookie_ea,
        bare_cookie_serving,
    ):
        """Multiple FGs from same category return category once."""
        set_event_recipes(test_db, planning_event.id, [cookie_recipe.id])
        test_db.flush()

        result = get_available_recipe_categories_for_event(
            planning_event.id, test_db
        )
        assert result.count("Cookies") == 1

    def test_returns_sorted(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """Categories returned in alphabetical order."""
        result = get_available_recipe_categories_for_event(
            planning_event.id, test_db
        )
        assert result == sorted(result)

    def test_no_available_fgs_returns_empty(self, test_db, planning_event):
        """Event with no available FGs returns empty list."""
        result = get_available_recipe_categories_for_event(
            planning_event.id, test_db
        )
        assert result == []

    def test_multiple_categories(
        self, test_db, planning_event, all_fgs_with_recipes_selected
    ):
        """FGs from different categories all represented."""
        result = get_available_recipe_categories_for_event(
            planning_event.id, test_db
        )
        assert "Cookies" in result
        assert "Cakes" in result
        assert len(result) == 2

    def test_raises_for_nonexistent_event(self, test_db):
        """Raises ValidationError for non-existent event."""
        with pytest.raises(ValidationError, match="Event .* not found"):
            get_available_recipe_categories_for_event(99999, test_db)

    def test_with_three_categories(
        self,
        test_db,
        planning_event,
        cookie_recipe,
        cake_recipe,
        bread_recipe,
        bare_cookie_ea,
        bare_cake_ea,
        bread_fu_serving,
    ):
        """Three different categories all returned sorted."""
        # Create a BARE FG for bread
        bread_fg = FinishedGood(
            slug="bare-bread-serving",
            display_name="Bare Bread Serving",
            assembly_type=AssemblyType.BARE,
        )
        test_db.add(bread_fg)
        test_db.flush()
        comp = Composition(
            assembly_id=bread_fg.id,
            finished_unit_id=bread_fu_serving.id,
            component_quantity=1.0,
        )
        test_db.add(comp)
        test_db.flush()

        # Select all three recipes
        set_event_recipes(
            test_db,
            planning_event.id,
            [cookie_recipe.id, cake_recipe.id, bread_recipe.id],
        )
        test_db.flush()

        result = get_available_recipe_categories_for_event(
            planning_event.id, test_db
        )
        assert result == ["Breads", "Cakes", "Cookies"]
