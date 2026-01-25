"""
Unit tests for recipe yield primitives (Feature 063).

Tests cover:
- get_base_yield_structure: transparent yield access for base and variant recipes
- get_finished_units: access recipe's own FinishedUnits

These primitives enable Planning/Production services to work identically for
base and variant recipes without variant-specific logic.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models import Recipe, FinishedUnit
from src.models.finished_unit import YieldMode
from src.services import recipe_service
from src.services.exceptions import RecipeNotFound
from src.services import database


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def db_session():
    """
    Create a test database session.

    This fixture creates an in-memory database for each test,
    ensuring tests are isolated. It also patches the global
    session factory so services use the test database.
    """
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Create session factory with expire_on_commit=False
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    # Patch the global session factory
    original_get_session = database.get_session
    database._session_factory = Session

    def patched_get_session():
        return Session()

    database.get_session = patched_get_session

    # Create a session for the test
    session = Session()

    yield session

    # Cleanup
    session.close()
    database.get_session = original_get_session


@pytest.fixture
def base_recipe_with_fu(db_session):
    """Create a base recipe with a FinishedUnit."""
    recipe = Recipe(name="Plain Cookie", category="Cookies")
    db_session.add(recipe)
    db_session.flush()

    fu = FinishedUnit(
        recipe_id=recipe.id,
        slug="plain-cookie",
        display_name="Plain Cookie",
        items_per_batch=24,
        item_unit="cookie",
        yield_mode=YieldMode.DISCRETE_COUNT,
    )
    db_session.add(fu)
    db_session.flush()
    db_session.commit()
    return recipe, fu


@pytest.fixture
def variant_recipe(db_session, base_recipe_with_fu):
    """Create a variant recipe with FinishedUnit (yields copied from base)."""
    base, base_fu = base_recipe_with_fu
    variant = Recipe(
        name="Raspberry Cookie",
        category="Cookies",
        base_recipe_id=base.id,
        variant_name="Raspberry",
    )
    db_session.add(variant)
    db_session.flush()

    # Variant FinishedUnits should have yields copied from base
    variant_fu = FinishedUnit(
        recipe_id=variant.id,
        slug="raspberry-cookie",
        display_name="Raspberry Cookie",
        items_per_batch=base_fu.items_per_batch,  # Copied from base
        item_unit=base_fu.item_unit,  # Copied from base
        yield_mode=base_fu.yield_mode,
    )
    db_session.add(variant_fu)
    db_session.flush()
    db_session.commit()
    return variant, variant_fu


@pytest.fixture
def base_recipe_multiple_fu(db_session):
    """Create a base recipe with multiple FinishedUnits."""
    recipe = Recipe(name="Thumbprint Cookies", category="Cookies")
    db_session.add(recipe)
    db_session.flush()

    fu1 = FinishedUnit(
        recipe_id=recipe.id,
        slug="thumbprint-cookie",
        display_name="Thumbprint Cookie",
        items_per_batch=24,
        item_unit="cookie",
        yield_mode=YieldMode.DISCRETE_COUNT,
    )
    fu2 = FinishedUnit(
        recipe_id=recipe.id,
        slug="thumbprint-mini",
        display_name="Thumbprint Mini",
        items_per_batch=48,
        item_unit="mini",
        yield_mode=YieldMode.DISCRETE_COUNT,
    )
    db_session.add(fu1)
    db_session.add(fu2)
    db_session.flush()
    db_session.commit()
    return recipe, [fu1, fu2]


# ============================================================================
# Tests for get_base_yield_structure
# ============================================================================


class TestGetBaseYieldStructure:
    """Tests for the get_base_yield_structure primitive."""

    def test_base_recipe_returns_own_yields(self, db_session, base_recipe_with_fu):
        """Base recipe returns its own FinishedUnit yields."""
        recipe, fu = base_recipe_with_fu

        result = recipe_service.get_base_yield_structure(recipe.id, session=db_session)

        assert len(result) == 1
        assert result[0]["slug"] == "plain-cookie"
        assert result[0]["display_name"] == "Plain Cookie"
        assert result[0]["items_per_batch"] == 24
        assert result[0]["item_unit"] == "cookie"

    def test_variant_recipe_returns_base_yields(
        self, db_session, variant_recipe, base_recipe_with_fu
    ):
        """Variant recipe returns base recipe's yields, not its own NULL values."""
        variant, variant_fu = variant_recipe
        base, base_fu = base_recipe_with_fu

        result = recipe_service.get_base_yield_structure(
            variant.id, session=db_session
        )

        # Should return base recipe's yields
        assert len(result) == 1
        assert result[0]["items_per_batch"] == 24  # From base
        assert result[0]["item_unit"] == "cookie"  # From base
        assert result[0]["display_name"] == "Plain Cookie"  # Base's display_name

    def test_recipe_with_no_finished_units(self, db_session):
        """Recipe with no FinishedUnits returns empty list."""
        recipe = Recipe(name="No FU Recipe", category="Test")
        db_session.add(recipe)
        db_session.flush()
        db_session.commit()

        result = recipe_service.get_base_yield_structure(recipe.id, session=db_session)

        assert result == []

    def test_nonexistent_recipe_raises_error(self, db_session):
        """Non-existent recipe_id raises RecipeNotFound."""
        with pytest.raises(RecipeNotFound):
            recipe_service.get_base_yield_structure(99999, session=db_session)

    def test_multiple_finished_units(self, db_session, base_recipe_multiple_fu):
        """Recipe with multiple FinishedUnits returns all yields."""
        recipe, fus = base_recipe_multiple_fu

        result = recipe_service.get_base_yield_structure(recipe.id, session=db_session)

        assert len(result) == 2
        slugs = {r["slug"] for r in result}
        assert "thumbprint-cookie" in slugs
        assert "thumbprint-mini" in slugs

    def test_without_session_parameter(self, db_session, base_recipe_with_fu):
        """Function works without explicit session parameter (uses session_scope)."""
        recipe, fu = base_recipe_with_fu

        # Commit to ensure data is visible to new session
        db_session.commit()

        # Call without session - should create its own session_scope
        result = recipe_service.get_base_yield_structure(recipe.id)

        assert len(result) == 1
        assert result[0]["items_per_batch"] == 24


# ============================================================================
# Tests for get_finished_units
# ============================================================================


class TestGetFinishedUnits:
    """Tests for the get_finished_units primitive."""

    def test_base_recipe_returns_own_finished_units(
        self, db_session, base_recipe_with_fu
    ):
        """Base recipe returns its own FinishedUnits with yield values."""
        recipe, fu = base_recipe_with_fu

        result = recipe_service.get_finished_units(recipe.id, session=db_session)

        assert len(result) == 1
        assert result[0]["id"] == fu.id
        assert result[0]["slug"] == "plain-cookie"
        assert result[0]["display_name"] == "Plain Cookie"
        assert result[0]["items_per_batch"] == 24
        assert result[0]["item_unit"] == "cookie"
        assert result[0]["yield_mode"] == "discrete_count"

    def test_variant_recipe_returns_own_finished_units_with_copied_yields(
        self, db_session, variant_recipe, base_recipe_with_fu
    ):
        """Variant recipe returns its own FinishedUnits with yields copied from base."""
        variant, variant_fu = variant_recipe
        base, base_fu = base_recipe_with_fu

        result = recipe_service.get_finished_units(variant.id, session=db_session)

        assert len(result) == 1
        assert result[0]["display_name"] == "Raspberry Cookie"
        assert result[0]["items_per_batch"] == base_fu.items_per_batch  # Copied from base
        assert result[0]["item_unit"] == base_fu.item_unit  # Copied from base

    def test_recipe_with_no_finished_units(self, db_session):
        """Recipe with no FinishedUnits returns empty list."""
        recipe = Recipe(name="No FU Recipe", category="Test")
        db_session.add(recipe)
        db_session.flush()
        db_session.commit()

        result = recipe_service.get_finished_units(recipe.id, session=db_session)

        assert result == []

    def test_nonexistent_recipe_raises_error(self, db_session):
        """Non-existent recipe_id raises RecipeNotFound."""
        with pytest.raises(RecipeNotFound):
            recipe_service.get_finished_units(99999, session=db_session)

    def test_does_not_resolve_to_base(self, db_session, variant_recipe):
        """get_finished_units returns variant's FUs, NOT base's FUs."""
        variant, variant_fu = variant_recipe

        result = recipe_service.get_finished_units(variant.id, session=db_session)

        # Should return variant's own FinishedUnit, not base's
        assert len(result) == 1
        assert result[0]["display_name"] == "Raspberry Cookie"  # Variant's name
        assert result[0]["slug"] == "raspberry-cookie"  # Variant's slug

    def test_without_session_parameter(self, db_session, base_recipe_with_fu):
        """Function works without explicit session parameter (uses session_scope)."""
        recipe, fu = base_recipe_with_fu
        db_session.commit()

        # Call without session
        result = recipe_service.get_finished_units(recipe.id)

        assert len(result) == 1
        assert result[0]["display_name"] == "Plain Cookie"


# ============================================================================
# Integration Tests: Using Both Primitives Together
# ============================================================================


class TestPrimitivesIntegration:
    """Test using both primitives together as intended."""

    def test_display_variant_with_base_yield(self, db_session, variant_recipe, base_recipe_with_fu):
        """
        Integration test: Display variant's name with base's yield.

        This is the intended usage pattern from the spec:
        - get_finished_units(variant_id) -> variant's display_name
        - get_base_yield_structure(variant_id) -> base's yield values
        """
        variant, _ = variant_recipe
        base, _ = base_recipe_with_fu

        # Get variant's FinishedUnits for display_name
        variant_fus = recipe_service.get_finished_units(variant.id, session=db_session)

        # Get base yields (resolved through primitive)
        base_yields = recipe_service.get_base_yield_structure(
            variant.id, session=db_session
        )

        # Build display string as UI would
        # Note: In real usage, variant might have different number of FUs than base
        assert len(variant_fus) >= 1
        assert len(base_yields) >= 1

        variant_display = variant_fus[0]["display_name"]
        base_yield = base_yields[0]["items_per_batch"]
        base_unit = base_yields[0]["item_unit"]

        display_string = f"{variant_display}: {base_yield} {base_unit}s per batch"

        assert display_string == "Raspberry Cookie: 24 cookies per batch"

    def test_base_recipe_same_result_both_primitives(
        self, db_session, base_recipe_with_fu
    ):
        """
        For base recipes, both primitives return similar yield data.

        This ensures consistent behavior for non-variant recipes.
        """
        recipe, fu = base_recipe_with_fu

        fus = recipe_service.get_finished_units(recipe.id, session=db_session)
        yields = recipe_service.get_base_yield_structure(recipe.id, session=db_session)

        # Both should have same yield values for base recipe
        assert fus[0]["items_per_batch"] == yields[0]["items_per_batch"]
        assert fus[0]["item_unit"] == yields[0]["item_unit"]
