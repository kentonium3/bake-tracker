"""
Tests for FG availability and decomposition service methods (F070).

Tests cover:
- get_required_recipes (WP01)
- check_fg_availability, get_available_finished_goods, remove_invalid_fg_selections (WP02)
"""

import pytest
from src.services.event_service import (
    get_required_recipes,
    CircularReferenceError,
    MaxDepthExceededError,
    MAX_FG_NESTING_DEPTH,
)
from src.services.exceptions import ValidationError


class TestGetRequiredRecipes:
    """Tests for get_required_recipes decomposition algorithm."""

    def test_returns_empty_set_for_fg_with_no_recipe_components(
        self, test_db, fg_no_recipe_components
    ):
        """FG with only packaging components returns empty set."""
        result = get_required_recipes(fg_no_recipe_components.id, test_db)
        assert result == set()

    def test_returns_single_recipe_for_atomic_fg(
        self, test_db, atomic_fg_with_recipe
    ):
        """Atomic FG (single FinishedUnit) returns its recipe ID."""
        result = get_required_recipes(atomic_fg_with_recipe.id, test_db)
        assert len(result) == 1
        # Verify it's the expected recipe
        assert atomic_fg_with_recipe.expected_recipe_id in result

    def test_returns_multiple_recipes_for_simple_bundle(
        self, test_db, simple_bundle
    ):
        """Bundle with multiple FUs returns all recipe IDs."""
        result = get_required_recipes(simple_bundle.id, test_db)
        assert result == simple_bundle.expected_recipe_ids

    def test_returns_all_recipes_for_nested_bundle(
        self, test_db, nested_bundle
    ):
        """Nested bundle (bundle containing bundle) recursively decomposes."""
        result = get_required_recipes(nested_bundle.id, test_db)
        assert result == nested_bundle.expected_recipe_ids

    def test_returns_unique_recipes_no_duplicates(
        self, test_db, bundle_with_duplicate_recipes
    ):
        """Duplicate recipe references are deduplicated."""
        result = get_required_recipes(bundle_with_duplicate_recipes.id, test_db)
        # Result is a set, so duplicates are naturally removed
        assert len(result) == len(bundle_with_duplicate_recipes.expected_unique_recipes)

    def test_raises_for_nonexistent_fg(self, test_db):
        """Raises ValidationError for non-existent FG."""
        with pytest.raises(ValidationError, match="FinishedGood .* not found"):
            get_required_recipes(99999, test_db)

    def test_raises_for_circular_reference(self, test_db, circular_bundle):
        """Circular references raise CircularReferenceError."""
        with pytest.raises(CircularReferenceError):
            get_required_recipes(circular_bundle.id, test_db)

    def test_raises_for_deep_nesting(self, test_db, deeply_nested_bundle):
        """Deep nesting (>10 levels) raises MaxDepthExceededError."""
        with pytest.raises(MaxDepthExceededError) as exc_info:
            get_required_recipes(deeply_nested_bundle.id, test_db)
        assert exc_info.value.max_depth == MAX_FG_NESTING_DEPTH


# ============================================================================
# Fixtures (WP01)
# ============================================================================


@pytest.fixture
def test_recipe(test_db):
    """Create a test recipe."""
    from src.models.recipe import Recipe
    recipe = Recipe(name="Test Recipe", category="Test")
    test_db.add(recipe)
    test_db.flush()
    return recipe


@pytest.fixture
def test_recipes(test_db):
    """Create multiple test recipes."""
    from src.models.recipe import Recipe
    recipes = []
    for i in range(5):
        recipe = Recipe(name=f"Test Recipe {i+1}", category="Test")
        test_db.add(recipe)
        recipes.append(recipe)
    test_db.flush()
    return recipes


@pytest.fixture
def test_finished_unit(test_db, test_recipe):
    """Create a FinishedUnit linked to a recipe."""
    from src.models.finished_unit import FinishedUnit
    fu = FinishedUnit(
        slug=f"test-fu-{test_recipe.id}",
        display_name="Test Finished Unit",
        recipe_id=test_recipe.id,
    )
    test_db.add(fu)
    test_db.flush()
    return fu


@pytest.fixture
def fg_no_recipe_components(test_db):
    """FG with only packaging components (no recipes)."""
    from src.models.finished_good import FinishedGood
    fg = FinishedGood(
        slug="fg-no-recipes",
        display_name="FG No Recipes",
    )
    test_db.add(fg)
    test_db.flush()
    # Note: No compositions added - empty bundle
    return fg


@pytest.fixture
def atomic_fg_with_recipe(test_db, test_finished_unit):
    """FG with single FinishedUnit component."""
    from src.models.finished_good import FinishedGood
    from src.models.composition import Composition

    fg = FinishedGood(
        slug="atomic-fg",
        display_name="Atomic FG",
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

    # Store expected recipe for assertion
    fg.expected_recipe_id = test_finished_unit.recipe_id
    return fg


@pytest.fixture
def simple_bundle(test_db, test_recipes):
    """Bundle with multiple FinishedUnit components."""
    from src.models.finished_good import FinishedGood
    from src.models.finished_unit import FinishedUnit
    from src.models.composition import Composition

    fg = FinishedGood(
        slug="simple-bundle",
        display_name="Simple Bundle",
    )
    test_db.add(fg)
    test_db.flush()

    expected_recipe_ids = set()
    for i, recipe in enumerate(test_recipes[:3]):
        fu = FinishedUnit(
            slug=f"fu-{recipe.id}",
            display_name=f"FU {recipe.id}",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        comp = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu.id,
            component_quantity=1.0,
        )
        test_db.add(comp)
        expected_recipe_ids.add(recipe.id)

    test_db.flush()
    fg.expected_recipe_ids = expected_recipe_ids
    return fg


@pytest.fixture
def nested_bundle(test_db, test_recipes):
    """Nested bundle (bundle containing another bundle)."""
    from src.models.finished_good import FinishedGood
    from src.models.finished_unit import FinishedUnit
    from src.models.composition import Composition

    # Inner bundle with 2 recipes
    inner_fg = FinishedGood(
        slug="inner-bundle",
        display_name="Inner Bundle",
    )
    test_db.add(inner_fg)
    test_db.flush()

    expected_recipe_ids = set()
    for recipe in test_recipes[:2]:
        fu = FinishedUnit(
            slug=f"inner-fu-{recipe.id}",
            display_name=f"Inner FU {recipe.id}",
            recipe_id=recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        comp = Composition(
            assembly_id=inner_fg.id,
            finished_unit_id=fu.id,
            component_quantity=1.0,
        )
        test_db.add(comp)
        expected_recipe_ids.add(recipe.id)

    # Outer bundle containing inner bundle + 1 more recipe
    outer_fg = FinishedGood(
        slug="outer-bundle",
        display_name="Outer Bundle",
    )
    test_db.add(outer_fg)
    test_db.flush()

    # Add inner bundle as component
    comp_inner = Composition(
        assembly_id=outer_fg.id,
        finished_good_id=inner_fg.id,
        component_quantity=1.0,
    )
    test_db.add(comp_inner)

    # Add one more FU directly
    extra_fu = FinishedUnit(
        slug=f"extra-fu-{test_recipes[2].id}",
        display_name="Extra FU",
        recipe_id=test_recipes[2].id,
    )
    test_db.add(extra_fu)
    test_db.flush()

    comp_extra = Composition(
        assembly_id=outer_fg.id,
        finished_unit_id=extra_fu.id,
        component_quantity=1.0,
    )
    test_db.add(comp_extra)
    expected_recipe_ids.add(test_recipes[2].id)

    test_db.flush()
    outer_fg.expected_recipe_ids = expected_recipe_ids
    return outer_fg


@pytest.fixture
def bundle_with_duplicate_recipes(test_db, test_recipe):
    """Bundle where multiple FUs use the same recipe."""
    from src.models.finished_good import FinishedGood
    from src.models.finished_unit import FinishedUnit
    from src.models.composition import Composition

    fg = FinishedGood(
        slug="duplicate-recipe-bundle",
        display_name="Duplicate Recipe Bundle",
    )
    test_db.add(fg)
    test_db.flush()

    # Add two FUs with same recipe
    for i in range(2):
        fu = FinishedUnit(
            slug=f"dup-fu-{i}",
            display_name=f"Dup FU {i}",
            recipe_id=test_recipe.id,
        )
        test_db.add(fu)
        test_db.flush()

        comp = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu.id,
            component_quantity=1.0,
        )
        test_db.add(comp)

    test_db.flush()
    fg.expected_unique_recipes = {test_recipe.id}
    return fg


@pytest.fixture
def circular_bundle(test_db):
    """Bundle with circular reference (A contains B, B contains A)."""
    from src.models.finished_good import FinishedGood
    from src.models.composition import Composition

    # Create two bundles
    fg_a = FinishedGood(slug="circular-a", display_name="Circular A")
    fg_b = FinishedGood(slug="circular-b", display_name="Circular B")
    test_db.add(fg_a)
    test_db.add(fg_b)
    test_db.flush()

    # A contains B
    comp_a = Composition(
        assembly_id=fg_a.id,
        finished_good_id=fg_b.id,
        component_quantity=1.0,
    )
    test_db.add(comp_a)

    # B contains A (creates cycle)
    comp_b = Composition(
        assembly_id=fg_b.id,
        finished_good_id=fg_a.id,
        component_quantity=1.0,
    )
    test_db.add(comp_b)
    test_db.flush()

    return fg_a


@pytest.fixture
def deeply_nested_bundle(test_db, test_recipe):
    """Bundle nested 12 levels deep (exceeds max 10)."""
    from src.models.finished_good import FinishedGood
    from src.models.finished_unit import FinishedUnit
    from src.models.composition import Composition

    # Create leaf FU
    leaf_fu = FinishedUnit(
        slug="deep-leaf-fu",
        display_name="Deep Leaf FU",
        recipe_id=test_recipe.id,
    )
    test_db.add(leaf_fu)
    test_db.flush()

    # Create 12 levels of nesting
    prev_fg = None
    for level in range(12):
        fg = FinishedGood(
            slug=f"deep-level-{level}",
            display_name=f"Deep Level {level}",
        )
        test_db.add(fg)
        test_db.flush()

        if prev_fg is None:
            # First level contains the leaf FU
            comp = Composition(
                assembly_id=fg.id,
                finished_unit_id=leaf_fu.id,
                component_quantity=1.0,
            )
        else:
            # Subsequent levels contain previous bundle
            comp = Composition(
                assembly_id=fg.id,
                finished_good_id=prev_fg.id,
                component_quantity=1.0,
            )
        test_db.add(comp)
        prev_fg = fg

    test_db.flush()
    return prev_fg  # Return outermost bundle
