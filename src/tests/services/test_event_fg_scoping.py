"""
Tests for Feature 103: Fix Plan Mode FG and Batch Scoping.

Tests cover:
- get_finished_units_for_event_recipes() - FUs returned for selected recipes
- get_fgs_for_selected_recipes() - FGs returned matching selected recipes
- remove_invalid_fg_selections() - stale EFG cleanup on recipe deselection
- decompose_event_to_fu_requirements() - batch decomposition scoped to selected recipes
"""

import pytest
from datetime import date

from src.models import (
    Event,
    EventRecipe,
    EventFinishedGood,
    FinishedGood,
    FinishedUnit,
    Composition,
    Recipe,
)
from src.models.assembly_type import AssemblyType
from src.models.finished_unit import YieldMode
from src.services.event_service import (
    get_finished_units_for_event_recipes,
    get_fgs_for_selected_recipes,
    remove_invalid_fg_selections,
)
from src.services.planning_service import decompose_event_to_fu_requirements


@pytest.fixture
def fg_scoping_data(test_db):
    """Create test data for FG scoping tests.

    Creates:
    - 3 recipes (Cookies, Bread, Scones categories)
    - 1 finished unit per recipe
    - 1 bare finished good per FU (linked via Composition)
    - 1 event
    - EventRecipe entries for all 3 recipes
    """
    session = test_db()

    # Create recipes
    recipe_cookies = Recipe(
        name="Test Cookies",
        category="Cookies",
    )
    recipe_bread = Recipe(
        name="Test Bread",
        category="Bread",
    )
    recipe_scones = Recipe(
        name="Test Scones",
        category="Scones",
    )
    session.add_all([recipe_cookies, recipe_bread, recipe_scones])
    session.flush()

    # Create finished units
    fu_cookies = FinishedUnit(
        slug="test-cookie",
        display_name="Test Cookie",
        recipe_id=recipe_cookies.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookie",
        yield_type="EA",
    )
    fu_bread = FinishedUnit(
        slug="test-bread-loaf",
        display_name="Test Bread Loaf",
        recipe_id=recipe_bread.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=2,
        item_unit="loaf",
        yield_type="EA",
    )
    fu_scones = FinishedUnit(
        slug="test-scone",
        display_name="Test Scone",
        recipe_id=recipe_scones.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=12,
        item_unit="scone",
        yield_type="SERVING",
    )
    session.add_all([fu_cookies, fu_bread, fu_scones])
    session.flush()

    # Create bare finished goods
    fg_cookies = FinishedGood(
        slug="test-cookie-fg",
        display_name="Test Cookie FG",
        assembly_type=AssemblyType.BARE,
    )
    fg_bread = FinishedGood(
        slug="test-bread-fg",
        display_name="Test Bread FG",
        assembly_type=AssemblyType.BARE,
    )
    fg_scones = FinishedGood(
        slug="test-scone-fg",
        display_name="Test Scone FG",
        assembly_type=AssemblyType.BARE,
    )
    session.add_all([fg_cookies, fg_bread, fg_scones])
    session.flush()

    # Link FGs to FUs via Composition
    comp_cookies = Composition(
        assembly_id=fg_cookies.id,
        finished_unit_id=fu_cookies.id,
        component_quantity=1,
    )
    comp_bread = Composition(
        assembly_id=fg_bread.id,
        finished_unit_id=fu_bread.id,
        component_quantity=1,
    )
    comp_scones = Composition(
        assembly_id=fg_scones.id,
        finished_unit_id=fu_scones.id,
        component_quantity=1,
    )
    session.add_all([comp_cookies, comp_bread, comp_scones])
    session.flush()

    # Create event
    event = Event(
        name="Test Event",
        event_date=date(2026, 4, 5),
        year=2026,
    )
    session.add(event)
    session.flush()

    # Select all 3 recipes for the event
    for recipe in [recipe_cookies, recipe_bread, recipe_scones]:
        er = EventRecipe(event_id=event.id, recipe_id=recipe.id)
        session.add(er)
    session.flush()

    session.commit()

    return {
        "session": session,
        "event": event,
        "recipes": {
            "cookies": recipe_cookies,
            "bread": recipe_bread,
            "scones": recipe_scones,
        },
        "fus": {
            "cookies": fu_cookies,
            "bread": fu_bread,
            "scones": fu_scones,
        },
        "fgs": {
            "cookies": fg_cookies,
            "bread": fg_bread,
            "scones": fg_scones,
        },
    }


class TestGetFinishedUnitsForEventRecipes:
    """Tests for get_finished_units_for_event_recipes()."""

    def test_returns_fus_for_all_selected_recipes(self, fg_scoping_data):
        """All 3 recipes selected -> 3 FUs returned."""
        d = fg_scoping_data
        fus = get_finished_units_for_event_recipes(d["event"].id, d["session"])
        assert len(fus) == 3
        fu_names = {fu.display_name for fu in fus}
        assert "Test Cookie" in fu_names
        assert "Test Bread Loaf" in fu_names
        assert "Test Scone" in fu_names

    def test_returns_empty_when_no_recipes_selected(self, fg_scoping_data):
        """No recipes selected -> empty list."""
        d = fg_scoping_data
        # Remove all event recipes
        d["session"].query(EventRecipe).filter_by(event_id=d["event"].id).delete()
        d["session"].flush()

        fus = get_finished_units_for_event_recipes(d["event"].id, d["session"])
        assert fus == []

    def test_category_filter(self, fg_scoping_data):
        """Category filter returns only matching FUs."""
        d = fg_scoping_data
        fus = get_finished_units_for_event_recipes(
            d["event"].id, d["session"], recipe_category="Cookies"
        )
        assert len(fus) == 1
        assert fus[0].display_name == "Test Cookie"

    def test_yield_type_filter(self, fg_scoping_data):
        """Yield type filter returns only matching FUs."""
        d = fg_scoping_data
        fus = get_finished_units_for_event_recipes(
            d["event"].id, d["session"], yield_type="SERVING"
        )
        assert len(fus) == 1
        assert fus[0].display_name == "Test Scone"

    def test_deselected_recipe_fu_not_returned(self, fg_scoping_data):
        """Deselecting a recipe removes its FU from results."""
        d = fg_scoping_data
        # Remove bread recipe from event
        d["session"].query(EventRecipe).filter_by(
            event_id=d["event"].id, recipe_id=d["recipes"]["bread"].id
        ).delete()
        d["session"].flush()

        fus = get_finished_units_for_event_recipes(d["event"].id, d["session"])
        assert len(fus) == 2
        fu_names = {fu.display_name for fu in fus}
        assert "Test Bread Loaf" not in fu_names


class TestGetFgsForSelectedRecipes:
    """Tests for get_fgs_for_selected_recipes()."""

    def test_returns_fg_objects(self, fg_scoping_data):
        """Returns FinishedGood objects, not FinishedUnits."""
        d = fg_scoping_data
        fgs = get_fgs_for_selected_recipes(d["event"].id, d["session"])
        assert len(fgs) == 3
        assert all(isinstance(fg, FinishedGood) for fg in fgs)

    def test_category_filter(self, fg_scoping_data):
        """Category filter works through FG wrapper."""
        d = fg_scoping_data
        fgs = get_fgs_for_selected_recipes(
            d["event"].id, d["session"], recipe_category="Bread"
        )
        assert len(fgs) == 1
        assert fgs[0].display_name == "Test Bread FG"

    def test_item_type_filter_bare(self, fg_scoping_data):
        """Item type filter for Finished Units returns bare FGs."""
        d = fg_scoping_data
        fgs = get_fgs_for_selected_recipes(
            d["event"].id, d["session"], item_type="Finished Units"
        )
        assert len(fgs) == 3  # All are bare
        assert all(fg.assembly_type == AssemblyType.BARE for fg in fgs)

    def test_item_type_filter_assemblies(self, fg_scoping_data):
        """Item type filter for Assemblies returns empty (no bundles in test data)."""
        d = fg_scoping_data
        fgs = get_fgs_for_selected_recipes(
            d["event"].id, d["session"], item_type="Assemblies"
        )
        assert fgs == []


class TestRemoveInvalidFgSelections:
    """Tests for remove_invalid_fg_selections() cleanup."""

    def test_removes_fg_when_recipe_deselected(self, fg_scoping_data):
        """Deselecting a recipe removes its EventFinishedGood."""
        d = fg_scoping_data
        # Save an EFG for cookies
        efg = EventFinishedGood(
            event_id=d["event"].id,
            finished_good_id=d["fgs"]["cookies"].id,
            quantity=5,
        )
        d["session"].add(efg)
        d["session"].flush()

        # Deselect cookies recipe
        d["session"].query(EventRecipe).filter_by(
            event_id=d["event"].id, recipe_id=d["recipes"]["cookies"].id
        ).delete()
        d["session"].flush()

        removed = remove_invalid_fg_selections(d["event"].id, d["session"])
        assert len(removed) == 1
        assert removed[0].fg_name == "Test Cookie FG"

        # Verify EFG is deleted
        remaining = (
            d["session"]
            .query(EventFinishedGood)
            .filter_by(event_id=d["event"].id)
            .all()
        )
        assert len(remaining) == 0

    def test_keeps_fg_when_recipe_still_selected(self, fg_scoping_data):
        """EFG preserved when its recipe is still selected."""
        d = fg_scoping_data
        efg = EventFinishedGood(
            event_id=d["event"].id,
            finished_good_id=d["fgs"]["cookies"].id,
            quantity=5,
        )
        d["session"].add(efg)
        d["session"].flush()

        removed = remove_invalid_fg_selections(d["event"].id, d["session"])
        assert len(removed) == 0

        remaining = (
            d["session"]
            .query(EventFinishedGood)
            .filter_by(event_id=d["event"].id)
            .all()
        )
        assert len(remaining) == 1


class TestBatchDecompositionScoping:
    """Tests for recipe-scoped batch decomposition."""

    def test_excludes_deselected_recipe_from_batch(self, fg_scoping_data):
        """Stale EFG for deselected recipe excluded from batch decomposition."""
        d = fg_scoping_data
        # Save EFG for cookies
        efg = EventFinishedGood(
            event_id=d["event"].id,
            finished_good_id=d["fgs"]["cookies"].id,
            quantity=5,
        )
        d["session"].add(efg)
        d["session"].flush()

        # Deselect cookies recipe (but leave EFG -- simulating stale record)
        d["session"].query(EventRecipe).filter_by(
            event_id=d["event"].id, recipe_id=d["recipes"]["cookies"].id
        ).delete()
        d["session"].flush()

        # Batch decomposition should exclude the stale EFG
        requirements = decompose_event_to_fu_requirements(
            d["event"].id, session=d["session"]
        )
        assert len(requirements) == 0

    def test_includes_selected_recipe_in_batch(self, fg_scoping_data):
        """Valid EFG for selected recipe included in batch decomposition."""
        d = fg_scoping_data
        efg = EventFinishedGood(
            event_id=d["event"].id,
            finished_good_id=d["fgs"]["cookies"].id,
            quantity=5,
        )
        d["session"].add(efg)
        d["session"].flush()

        requirements = decompose_event_to_fu_requirements(
            d["event"].id, session=d["session"]
        )
        assert len(requirements) == 1
        assert requirements[0].recipe.name == "Test Cookies"
        assert requirements[0].quantity_needed == 5
