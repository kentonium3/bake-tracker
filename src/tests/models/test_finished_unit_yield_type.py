"""Tests for FinishedUnit yield_type field and constraints.

Feature 083 - Dual-Yield Support: Tests verify:
- yield_type column defaults to 'SERVING'
- yield_type accepts 'EA' value
- CHECK constraint rejects invalid yield_type values
- UNIQUE constraint allows same item_unit with different yield_types
- UNIQUE constraint rejects duplicate (recipe_id, item_unit, yield_type)
"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.finished_unit import FinishedUnit, YieldMode
from src.models.recipe import Recipe


class TestFinishedUnitYieldType:
    """Test yield_type field behavior."""

    def test_yield_type_default_is_serving(self, test_db):
        """FinishedUnit defaults to yield_type='SERVING'."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.flush()

        fu = FinishedUnit(
            slug="test-fu",
            display_name="Test Cookie",
            recipe_id=recipe.id,
            item_unit="cookie",
            items_per_batch=24,
            yield_mode=YieldMode.DISCRETE_COUNT,
        )
        session.add(fu)
        session.commit()

        assert fu.yield_type == "SERVING"

    def test_yield_type_accepts_ea(self, test_db):
        """FinishedUnit accepts yield_type='EA'."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.flush()

        fu = FinishedUnit(
            slug="test-fu",
            display_name="Test Cake",
            recipe_id=recipe.id,
            item_unit="cake",
            items_per_batch=1,
            yield_mode=YieldMode.DISCRETE_COUNT,
            yield_type="EA",
        )
        session.add(fu)
        session.commit()

        assert fu.yield_type == "EA"

    def test_yield_type_rejects_invalid_value(self, test_db):
        """FinishedUnit rejects invalid yield_type values via CHECK constraint."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.flush()

        fu = FinishedUnit(
            slug="test-fu",
            display_name="Test",
            recipe_id=recipe.id,
            item_unit="cookie",
            items_per_batch=24,
            yield_mode=YieldMode.DISCRETE_COUNT,
            yield_type="INVALID",
        )
        session.add(fu)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_unique_constraint_allows_different_yield_types(self, test_db):
        """Same item_unit can have both EA and SERVING yield types on same recipe."""
        session = test_db()

        recipe = Recipe(name="Cake Recipe", slug="cake-recipe", category="Cakes")
        session.add(recipe)
        session.flush()

        # Create EA yield (whole cake)
        fu_ea = FinishedUnit(
            slug="test-cake-ea",
            display_name="Small Cake (Whole)",
            recipe_id=recipe.id,
            item_unit="small cake",
            items_per_batch=1,
            yield_mode=YieldMode.DISCRETE_COUNT,
            yield_type="EA",
        )

        # Create SERVING yield (slices of same cake)
        fu_serving = FinishedUnit(
            slug="test-cake-serving",
            display_name="Small Cake (Slice)",
            recipe_id=recipe.id,
            item_unit="small cake",
            items_per_batch=8,
            yield_mode=YieldMode.DISCRETE_COUNT,
            yield_type="SERVING",
        )

        session.add_all([fu_ea, fu_serving])
        session.commit()

        # Both should be created successfully
        assert fu_ea.id is not None
        assert fu_serving.id is not None
        assert fu_ea.yield_type == "EA"
        assert fu_serving.yield_type == "SERVING"

    def test_unique_constraint_rejects_duplicate_yield_type(self, test_db):
        """Cannot have two FinishedUnits with same (recipe_id, item_unit, yield_type)."""
        session = test_db()

        recipe = Recipe(name="Cake Recipe", slug="cake-recipe", category="Cakes")
        session.add(recipe)
        session.flush()

        # Create first EA yield
        fu1 = FinishedUnit(
            slug="test-cake-1",
            display_name="Small Cake 1",
            recipe_id=recipe.id,
            item_unit="small cake",
            items_per_batch=1,
            yield_mode=YieldMode.DISCRETE_COUNT,
            yield_type="EA",
        )

        # Try to create second EA yield with same item_unit
        fu2 = FinishedUnit(
            slug="test-cake-2",
            display_name="Small Cake 2",
            recipe_id=recipe.id,
            item_unit="small cake",  # Same item_unit
            items_per_batch=1,
            yield_mode=YieldMode.DISCRETE_COUNT,
            yield_type="EA",  # Same yield_type - should fail!
        )

        session.add_all([fu1, fu2])

        with pytest.raises(IntegrityError):
            session.commit()

    def test_to_dict_includes_yield_type(self, test_db):
        """to_dict() includes yield_type field."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.flush()

        fu = FinishedUnit(
            slug="test-fu",
            display_name="Test Cookie",
            recipe_id=recipe.id,
            item_unit="cookie",
            items_per_batch=24,
            yield_mode=YieldMode.DISCRETE_COUNT,
            yield_type="SERVING",
        )
        session.add(fu)
        session.commit()

        result = fu.to_dict()

        assert "yield_type" in result
        assert result["yield_type"] == "SERVING"

    def test_to_dict_includes_ea_yield_type(self, test_db):
        """to_dict() includes yield_type='EA' correctly."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.flush()

        fu = FinishedUnit(
            slug="test-fu",
            display_name="Whole Cake",
            recipe_id=recipe.id,
            item_unit="cake",
            items_per_batch=1,
            yield_mode=YieldMode.DISCRETE_COUNT,
            yield_type="EA",
        )
        session.add(fu)
        session.commit()

        result = fu.to_dict()

        assert result["yield_type"] == "EA"
