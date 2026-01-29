"""Tests for FinishedUnit yield_type service layer validation.

Feature 083 - Dual-Yield Support

Tests verify:
- VALID_YIELD_TYPES constant contains expected values
- validate_yield_type() returns errors for invalid values
- create_finished_unit() accepts and validates yield_type
- update_finished_unit() validates yield_type changes
- Backward compatibility: default yield_type is 'SERVING'
"""

import pytest

from src.services import finished_unit_service
from src.services.finished_unit_service import (
    VALID_YIELD_TYPES,
    validate_yield_type,
)
from src.models.recipe import Recipe
from src.services.database import session_scope


class TestValidateYieldType:
    """Test validate_yield_type function."""

    def test_valid_yield_types_constant(self):
        """VALID_YIELD_TYPES contains expected values."""
        assert VALID_YIELD_TYPES == {"EA", "SERVING"}

    def test_validate_ea_returns_empty_list(self):
        """'EA' is valid and returns no errors."""
        errors = validate_yield_type("EA")
        assert errors == []

    def test_validate_serving_returns_empty_list(self):
        """'SERVING' is valid and returns no errors."""
        errors = validate_yield_type("SERVING")
        assert errors == []

    def test_validate_empty_returns_error(self):
        """Empty string returns error."""
        errors = validate_yield_type("")
        assert len(errors) == 1
        assert "required" in errors[0]

    def test_validate_none_returns_error(self):
        """None returns error."""
        errors = validate_yield_type(None)
        assert len(errors) == 1
        assert "required" in errors[0]

    def test_validate_invalid_returns_error_with_value(self):
        """Invalid value returns error containing the bad value."""
        errors = validate_yield_type("INVALID")
        assert len(errors) == 1
        assert "INVALID" in errors[0]
        assert "EA" in errors[0]
        assert "SERVING" in errors[0]


class TestCreateFinishedUnitYieldType:
    """Test create_finished_unit with yield_type."""

    def test_create_with_default_yield_type(self, test_db):
        """FinishedUnit created without yield_type defaults to SERVING."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = finished_unit_service.create_finished_unit(
            display_name="Test Cookies",
            recipe_id=recipe.id,
            item_unit="cookie",
            items_per_batch=24,
        )

        assert fu.yield_type == "SERVING"

    def test_create_with_explicit_ea(self, test_db):
        """FinishedUnit can be created with yield_type='EA'."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = finished_unit_service.create_finished_unit(
            display_name="Test Cake",
            recipe_id=recipe.id,
            item_unit="cake",
            items_per_batch=1,
            yield_type="EA",
        )

        assert fu.yield_type == "EA"

    def test_create_with_explicit_serving(self, test_db):
        """FinishedUnit can be created with explicit yield_type='SERVING'."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = finished_unit_service.create_finished_unit(
            display_name="Test Cookie",
            recipe_id=recipe.id,
            item_unit="cookie",
            items_per_batch=24,
            yield_type="SERVING",
        )

        assert fu.yield_type == "SERVING"

    def test_create_with_invalid_yield_type_raises(self, test_db):
        """Creating with invalid yield_type raises ValueError."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        with pytest.raises(ValueError) as exc_info:
            finished_unit_service.create_finished_unit(
                display_name="Test",
                recipe_id=recipe.id,
                item_unit="item",
                items_per_batch=1,
                yield_type="INVALID",
            )

        assert "INVALID" in str(exc_info.value)
        assert "yield_type" in str(exc_info.value).lower()

    def test_create_with_empty_yield_type_raises(self, test_db):
        """Creating with empty yield_type raises ValueError."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        with pytest.raises(ValueError) as exc_info:
            finished_unit_service.create_finished_unit(
                display_name="Test",
                recipe_id=recipe.id,
                item_unit="item",
                items_per_batch=1,
                yield_type="",
            )

        assert "required" in str(exc_info.value).lower()


class TestUpdateFinishedUnitYieldType:
    """Test update_finished_unit with yield_type."""

    def test_update_yield_type_to_ea(self, test_db):
        """yield_type can be updated from SERVING to EA."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = finished_unit_service.create_finished_unit(
            display_name="Test",
            recipe_id=recipe.id,
            item_unit="item",
            items_per_batch=1,
            yield_type="SERVING",
        )
        fu_id = fu.id

        updated = finished_unit_service.update_finished_unit(
            fu_id,
            yield_type="EA",
        )

        assert updated.yield_type == "EA"

    def test_update_yield_type_to_serving(self, test_db):
        """yield_type can be updated from EA to SERVING."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = finished_unit_service.create_finished_unit(
            display_name="Test",
            recipe_id=recipe.id,
            item_unit="item",
            items_per_batch=1,
            yield_type="EA",
        )
        fu_id = fu.id

        updated = finished_unit_service.update_finished_unit(
            fu_id,
            yield_type="SERVING",
        )

        assert updated.yield_type == "SERVING"

    def test_update_other_fields_preserves_yield_type(self, test_db):
        """Updating other fields without yield_type preserves existing value."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = finished_unit_service.create_finished_unit(
            display_name="Test",
            recipe_id=recipe.id,
            item_unit="item",
            items_per_batch=1,
            yield_type="EA",
        )
        fu_id = fu.id

        updated = finished_unit_service.update_finished_unit(
            fu_id,
            display_name="Updated Name",
        )

        assert updated.yield_type == "EA"  # Preserved

    def test_update_with_invalid_yield_type_raises(self, test_db):
        """Updating with invalid yield_type raises ValueError."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = finished_unit_service.create_finished_unit(
            display_name="Test",
            recipe_id=recipe.id,
            item_unit="item",
            items_per_batch=1,
        )
        fu_id = fu.id

        with pytest.raises(ValueError) as exc_info:
            finished_unit_service.update_finished_unit(
                fu_id,
                yield_type="BOGUS",
            )

        assert "BOGUS" in str(exc_info.value)

    def test_update_with_empty_yield_type_raises(self, test_db):
        """Updating with empty yield_type raises ValueError."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = finished_unit_service.create_finished_unit(
            display_name="Test",
            recipe_id=recipe.id,
            item_unit="item",
            items_per_batch=1,
        )
        fu_id = fu.id

        with pytest.raises(ValueError) as exc_info:
            finished_unit_service.update_finished_unit(
                fu_id,
                yield_type="",
            )

        assert "required" in str(exc_info.value).lower()
