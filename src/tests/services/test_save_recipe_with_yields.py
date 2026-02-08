"""Tests for save_recipe_with_yields() orchestration function.

WP02 - F098: Auto-Generation of FinishedGoods

Tests verify:
- Atomic creation of recipe + yield types in single transaction
- Atomic update of recipe + yield types in single transaction
- Yield type reconciliation (add new, update existing, delete removed)
- Transaction rollback on failure (no partial state)
"""

import pytest

from src.services.recipe_service import save_recipe_with_yields
from src.services import finished_unit_service, recipe_service
from src.models.recipe import Recipe
from src.models.finished_unit import FinishedUnit
from src.services.database import session_scope
from src.services.exceptions import ValidationError


class TestSaveRecipeWithYieldsCreate:
    """Test save_recipe_with_yields for new recipe creation."""

    def test_creates_recipe_and_yield_type(self, test_db):
        """Recipe and FU are created atomically."""
        test_db()

        recipe_data = {"name": "Test Cake", "category": "Cakes"}
        yield_types = [
            {
                "id": None,
                "display_name": "Test Cake",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]

        recipe = save_recipe_with_yields(recipe_data, yield_types)

        assert recipe.id is not None
        assert recipe.name == "Test Cake"

        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 1
        assert fus[0].display_name == "Test Cake"
        assert fus[0].yield_type == "EA"

    def test_creates_multiple_yield_types(self, test_db):
        """Multiple yield types (EA + SERVING) created for same recipe."""
        test_db()

        recipe_data = {"name": "Chocolate Chip Cookies", "category": "Cookies"}
        yield_types = [
            {
                "id": None,
                "display_name": "Chocolate Chip Cookies",
                "yield_type": "EA",
                "items_per_batch": 24.0,
                "item_unit": "cookie",
            },
            {
                "id": None,
                "display_name": "Chocolate Chip Cookies",
                "yield_type": "SERVING",
                "items_per_batch": 12.0,
                "item_unit": "serving",
            },
        ]

        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 2

        yield_types_found = {fu.yield_type for fu in fus}
        assert yield_types_found == {"EA", "SERVING"}

    def test_creates_recipe_with_no_yield_types(self, test_db):
        """Recipe created with empty yield types list."""
        test_db()

        recipe_data = {"name": "Simple Recipe", "category": "Other"}
        recipe = save_recipe_with_yields(recipe_data, [])

        assert recipe.id is not None
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 0

    def test_create_with_session_parameter(self, test_db):
        """save_recipe_with_yields respects provided session."""
        test_db()

        recipe_data = {"name": "Session Test", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Session Test",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]

        with session_scope() as sess:
            recipe = save_recipe_with_yields(
                recipe_data, yield_types, session=sess
            )
            assert recipe in sess

            # FU should also be queryable in the same session
            fus = sess.query(FinishedUnit).filter_by(recipe_id=recipe.id).all()
            assert len(fus) == 1


class TestSaveRecipeWithYieldsUpdate:
    """Test save_recipe_with_yields for recipe updates."""

    def _create_recipe_with_fu(self, test_db):
        """Helper to create a recipe with one FU."""
        session = test_db()
        recipe_data = {"name": "Base Recipe", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Base Unit",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        return recipe, fus[0]

    def test_update_recipe_name(self, test_db):
        """Recipe name update with existing yield types preserved."""
        recipe, fu = self._create_recipe_with_fu(test_db)

        updated_data = {"name": "Updated Recipe", "category": "Test"}
        yield_types = [
            {
                "id": fu.id,
                "display_name": "Base Unit",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]

        result = save_recipe_with_yields(
            updated_data, yield_types, recipe_id=recipe.id
        )
        assert result.name == "Updated Recipe"

        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 1
        assert fus[0].id == fu.id


class TestYieldReconciliation:
    """Test yield type reconciliation (add, update, delete)."""

    def _create_recipe_with_fus(self, test_db, count=2):
        """Helper to create a recipe with multiple FUs."""
        test_db()
        recipe_data = {"name": "Multi-FU Recipe", "category": "Test"}
        yield_types = []
        for i in range(count):
            yield_types.append({
                "id": None,
                "display_name": f"Unit {i+1}",
                "yield_type": "EA",
                "items_per_batch": float(i + 1),
            })
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        return recipe, fus

    def test_add_new_yield_type(self, test_db):
        """Adding a new yield type to existing recipe."""
        recipe, fus = self._create_recipe_with_fus(test_db, count=1)
        fu_id = fus[0].id

        yield_types = [
            {
                "id": fu_id,
                "display_name": "Unit 1",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
            {
                "id": None,
                "display_name": "New Unit",
                "yield_type": "SERVING",
                "items_per_batch": 8.0,
            },
        ]

        save_recipe_with_yields(
            {"name": "Multi-FU Recipe", "category": "Test"},
            yield_types,
            recipe_id=recipe.id,
        )

        updated_fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(updated_fus) == 2

    def test_update_existing_yield_type(self, test_db):
        """Updating an existing yield type's name."""
        recipe, fus = self._create_recipe_with_fus(test_db, count=1)
        fu_id = fus[0].id

        yield_types = [
            {
                "id": fu_id,
                "display_name": "Renamed Unit",
                "yield_type": "EA",
                "items_per_batch": 5.0,
            },
        ]

        save_recipe_with_yields(
            {"name": "Multi-FU Recipe", "category": "Test"},
            yield_types,
            recipe_id=recipe.id,
        )

        updated_fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(updated_fus) == 1
        assert updated_fus[0].display_name == "Renamed Unit"
        assert updated_fus[0].items_per_batch == 5.0

    def test_remove_yield_type(self, test_db):
        """Removing a yield type deletes the FU."""
        recipe, fus = self._create_recipe_with_fus(test_db, count=2)
        keep_fu_id = fus[0].id

        # Only keep one FU
        yield_types = [
            {
                "id": keep_fu_id,
                "display_name": "Unit 1",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]

        save_recipe_with_yields(
            {"name": "Multi-FU Recipe", "category": "Test"},
            yield_types,
            recipe_id=recipe.id,
        )

        updated_fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(updated_fus) == 1
        assert updated_fus[0].id == keep_fu_id

    def test_mixed_operations(self, test_db):
        """Add one, update one, remove one in same call."""
        recipe, fus = self._create_recipe_with_fus(test_db, count=2)
        keep_fu_id = fus[0].id
        # fus[1] will be removed

        yield_types = [
            {
                "id": keep_fu_id,
                "display_name": "Updated Unit 1",
                "yield_type": "EA",
                "items_per_batch": 10.0,
            },
            {
                "id": None,
                "display_name": "Brand New Unit",
                "yield_type": "SERVING",
                "items_per_batch": 4.0,
            },
        ]

        save_recipe_with_yields(
            {"name": "Multi-FU Recipe", "category": "Test"},
            yield_types,
            recipe_id=recipe.id,
        )

        updated_fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(updated_fus) == 2

        names = {fu.display_name for fu in updated_fus}
        assert "Updated Unit 1" in names
        assert "Brand New Unit" in names


class TestTransactionRollback:
    """Test that failures roll back the entire operation."""

    def test_invalid_recipe_data_no_partial_state(self, test_db):
        """Invalid recipe data prevents any creation."""
        test_db()

        # Missing required 'category'
        recipe_data = {"name": "Bad Recipe"}
        yield_types = [
            {
                "id": None,
                "display_name": "Should Not Exist",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]

        with pytest.raises(ValidationError):
            save_recipe_with_yields(recipe_data, yield_types)

        # Verify no recipes were created
        with session_scope() as sess:
            count = sess.query(Recipe).filter_by(name="Bad Recipe").count()
            assert count == 0

    def test_invalid_yield_type_rolls_back_recipe(self, test_db):
        """Invalid yield type data rolls back the recipe creation too."""
        test_db()

        recipe_data = {"name": "Rollback Test", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "",  # Invalid: empty display name
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]

        with pytest.raises((ValidationError, ValueError)):
            save_recipe_with_yields(recipe_data, yield_types)

        # Verify no recipes were created
        with session_scope() as sess:
            count = sess.query(Recipe).filter_by(name="Rollback Test").count()
            assert count == 0
