"""Tests for FinishedUnit yield_type service layer validation.

Feature 083 - Dual-Yield Support

Tests verify:
- VALID_YIELD_TYPES constant contains expected values
- validate_yield_type() returns errors for invalid values
- create_finished_unit() accepts and validates yield_type
- update_finished_unit() validates yield_type changes
- Backward compatibility: default yield_type is 'SERVING'
- propagate_yield_to_variants() syncs yield fields to variant FUs
"""

import pytest

from src.services import finished_unit_service
from src.services.finished_unit_service import (
    VALID_YIELD_TYPES,
    validate_yield_type,
    propagate_yield_to_variants,
)
from src.models.finished_unit import FinishedUnit
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


class TestPropagateYieldToVariants:
    """Test propagate_yield_to_variants function."""

    def _create_base_with_variant(self, session, base_yield_type="SERVING"):
        """Helper to create a base recipe with one variant, each having one FU."""
        base = Recipe(name="Base Cookie", slug="base-cookie", category="Cookies")
        session.add(base)
        session.flush()

        base_fu = FinishedUnit(
            recipe_id=base.id,
            slug="base-cookie-serving",
            display_name="Base Cookie",
            yield_type=base_yield_type,
            item_unit="cookie",
            items_per_batch=24,
        )
        session.add(base_fu)
        session.flush()

        variant = Recipe(
            name="Raspberry Cookie",
            slug="raspberry-cookie",
            category="Cookies",
            base_recipe_id=base.id,
            variant_name="Raspberry",
        )
        session.add(variant)
        session.flush()

        variant_fu = FinishedUnit(
            recipe_id=variant.id,
            slug="raspberry-cookie-serving",
            display_name="Raspberry Cookie",
            yield_type=base_yield_type,
            item_unit="cookie",
            items_per_batch=24,
        )
        session.add(variant_fu)
        session.commit()

        return base, base_fu, variant, variant_fu

    def test_propagate_yield_type_change(self, test_db):
        """Changing base yield_type propagates to variant."""
        session = test_db()
        base, base_fu, variant, variant_fu = self._create_base_with_variant(session)

        # Update base FU yield_type
        finished_unit_service.update_finished_unit(base_fu.id, yield_type="EA")

        # Propagate
        count = propagate_yield_to_variants(base.id)
        assert count == 1

        # Verify variant FU updated
        session.expire_all()
        updated_variant_fu = session.query(FinishedUnit).get(variant_fu.id)
        assert updated_variant_fu.yield_type == "EA"

    def test_propagate_items_per_batch_change(self, test_db):
        """Changing base items_per_batch propagates to variant."""
        session = test_db()
        base, base_fu, variant, variant_fu = self._create_base_with_variant(session)

        # Update base FU items_per_batch
        finished_unit_service.update_finished_unit(base_fu.id, items_per_batch=48)

        count = propagate_yield_to_variants(base.id)
        assert count == 1

        session.expire_all()
        updated_variant_fu = session.query(FinishedUnit).get(variant_fu.id)
        assert updated_variant_fu.items_per_batch == 48

    def test_propagate_no_variants_returns_zero(self, test_db):
        """No variants means nothing to propagate."""
        session = test_db()
        base = Recipe(name="Solo Recipe", slug="solo-recipe", category="Test")
        session.add(base)
        session.commit()

        count = propagate_yield_to_variants(base.id)
        assert count == 0

    def test_propagate_variant_recipe_returns_zero(self, test_db):
        """Calling propagate on a variant recipe (not base) returns zero."""
        session = test_db()
        base, base_fu, variant, variant_fu = self._create_base_with_variant(session)

        # Try propagating from the variant — should be a no-op
        count = propagate_yield_to_variants(variant.id)
        assert count == 0

    def test_propagate_multiple_variants(self, test_db):
        """Yield changes propagate to all variants."""
        session = test_db()
        base, base_fu, variant1, variant1_fu = self._create_base_with_variant(session)

        # Add a second variant
        variant2 = Recipe(
            name="Strawberry Cookie",
            slug="strawberry-cookie",
            category="Cookies",
            base_recipe_id=base.id,
            variant_name="Strawberry",
        )
        session.add(variant2)
        session.flush()

        variant2_fu = FinishedUnit(
            recipe_id=variant2.id,
            slug="strawberry-cookie-serving",
            display_name="Strawberry Cookie",
            yield_type="SERVING",
            item_unit="cookie",
            items_per_batch=24,
        )
        session.add(variant2_fu)
        session.commit()

        # Update base
        finished_unit_service.update_finished_unit(base_fu.id, yield_type="EA", items_per_batch=1)

        count = propagate_yield_to_variants(base.id)
        assert count == 2

        session.expire_all()
        for vfu_id in [variant1_fu.id, variant2_fu.id]:
            vfu = session.query(FinishedUnit).get(vfu_id)
            assert vfu.yield_type == "EA"
            assert vfu.items_per_batch == 1

    def test_propagate_skips_mismatched_fu_count(self, test_db):
        """Variant with different FU count is skipped (logged warning)."""
        session = test_db()
        base, base_fu, variant, variant_fu = self._create_base_with_variant(session)

        # Add extra FU to variant (creates mismatch)
        extra_fu = FinishedUnit(
            recipe_id=variant.id,
            slug="raspberry-cookie-extra",
            display_name="Raspberry Cookie Extra",
            yield_type="EA",
            item_unit="piece",
            items_per_batch=12,
        )
        session.add(extra_fu)
        session.commit()

        # Update base
        finished_unit_service.update_finished_unit(base_fu.id, yield_type="EA")

        # Should skip variant due to FU count mismatch
        count = propagate_yield_to_variants(base.id)
        assert count == 0

    def test_propagate_no_change_returns_zero(self, test_db):
        """If variant FUs already match base, count is zero."""
        session = test_db()
        base, base_fu, variant, variant_fu = self._create_base_with_variant(session)

        # No changes to base — variant already matches
        count = propagate_yield_to_variants(base.id)
        assert count == 0
