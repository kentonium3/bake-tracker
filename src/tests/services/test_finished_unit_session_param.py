"""Tests for FinishedUnit service session parameter support.

WP01 - F098: Auto-Generation of FinishedGoods

Tests verify:
- create_finished_unit() uses provided session (no new session_scope)
- update_finished_unit() uses provided session
- delete_finished_unit() uses provided session
- Module-level convenience functions forward session parameter
- Objects remain attached to the provided session
"""

import pytest

from src.services import finished_unit_service
from src.services.finished_unit_service import (
    FinishedUnitService,
    ReferencedUnitError,
)
from src.models.finished_unit import FinishedUnit
from src.models.recipe import Recipe
from src.models.composition import Composition
from src.models.finished_good import FinishedGood
from src.models.assembly_type import AssemblyType
from src.services.database import session_scope


class TestCreateFinishedUnitWithSession:
    """Test create_finished_unit with explicit session parameter."""

    def test_create_with_session_uses_provided_session(self, test_db):
        """When session is provided, FU is created within that session."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        with session_scope() as sess:
            fu = FinishedUnitService.create_finished_unit(
                display_name="Test Unit",
                recipe_id=recipe.id,
                session=sess,
            )
            # Object should be in the same session
            assert fu in sess
            assert fu.id is not None
            assert fu.display_name == "Test Unit"

            # Verify we can query it in the same session
            found = sess.query(FinishedUnit).filter_by(id=fu.id).first()
            assert found is not None
            assert found.display_name == "Test Unit"

    def test_create_with_session_module_level(self, test_db):
        """Module-level create_finished_unit forwards session parameter."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        with session_scope() as sess:
            fu = finished_unit_service.create_finished_unit(
                display_name="Module Level Unit",
                recipe_id=recipe.id,
                session=sess,
            )
            assert fu in sess
            assert fu.display_name == "Module Level Unit"

    def test_create_without_session_still_works(self, test_db):
        """Default session=None preserves backward-compatible behavior."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = FinishedUnitService.create_finished_unit(
            display_name="No Session Unit",
            recipe_id=recipe.id,
        )
        assert fu.id is not None
        assert fu.display_name == "No Session Unit"

    def test_create_with_session_and_kwargs(self, test_db):
        """Session parameter works alongside other keyword arguments."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        with session_scope() as sess:
            fu = FinishedUnitService.create_finished_unit(
                display_name="Full Unit",
                recipe_id=recipe.id,
                session=sess,
                yield_type="EA",
                items_per_batch=12,
                item_unit="cookie",
            )
            assert fu in sess
            assert fu.yield_type == "EA"
            assert fu.items_per_batch == 12
            assert fu.item_unit == "cookie"


class TestUpdateFinishedUnitWithSession:
    """Test update_finished_unit with explicit session parameter."""

    def test_update_with_session_uses_provided_session(self, test_db):
        """When session is provided, update executes within that session."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = FinishedUnitService.create_finished_unit(
            display_name="Original Name",
            recipe_id=recipe.id,
        )
        fu_id = fu.id

        with session_scope() as sess:
            updated = FinishedUnitService.update_finished_unit(
                fu_id,
                session=sess,
                display_name="Updated Name",
            )
            assert updated in sess
            assert updated.display_name == "Updated Name"

            # Verify within the same session
            found = sess.query(FinishedUnit).filter_by(id=fu_id).first()
            assert found.display_name == "Updated Name"

    def test_update_with_session_module_level(self, test_db):
        """Module-level update_finished_unit forwards session parameter."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = FinishedUnitService.create_finished_unit(
            display_name="Original",
            recipe_id=recipe.id,
        )
        fu_id = fu.id

        with session_scope() as sess:
            updated = finished_unit_service.update_finished_unit(
                fu_id,
                session=sess,
                display_name="Module Updated",
            )
            assert updated in sess
            assert updated.display_name == "Module Updated"

    def test_update_without_session_still_works(self, test_db):
        """Default session=None preserves backward-compatible behavior."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = FinishedUnitService.create_finished_unit(
            display_name="Original",
            recipe_id=recipe.id,
        )
        fu_id = fu.id

        updated = FinishedUnitService.update_finished_unit(
            fu_id,
            display_name="Updated No Session",
        )
        assert updated.display_name == "Updated No Session"


class TestDeleteFinishedUnitWithSession:
    """Test delete_finished_unit with explicit session parameter."""

    def test_delete_with_session_uses_provided_session(self, test_db):
        """When session is provided, delete executes within that session."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = FinishedUnitService.create_finished_unit(
            display_name="To Delete",
            recipe_id=recipe.id,
        )
        fu_id = fu.id

        with session_scope() as sess:
            result = FinishedUnitService.delete_finished_unit(
                fu_id,
                session=sess,
            )
            assert result is True

            # Should be gone within this session
            found = sess.query(FinishedUnit).filter_by(id=fu_id).first()
            assert found is None

    def test_delete_with_session_module_level(self, test_db):
        """Module-level delete_finished_unit forwards session parameter."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = FinishedUnitService.create_finished_unit(
            display_name="To Delete Module",
            recipe_id=recipe.id,
        )
        fu_id = fu.id

        with session_scope() as sess:
            result = finished_unit_service.delete_finished_unit(
                fu_id,
                session=sess,
            )
            assert result is True

    def test_delete_not_found_with_session(self, test_db):
        """Delete returns False for nonexistent ID even with session."""
        test_db()

        with session_scope() as sess:
            result = FinishedUnitService.delete_finished_unit(
                99999,
                session=sess,
            )
            assert result is False

    def test_delete_without_session_still_works(self, test_db):
        """Default session=None preserves backward-compatible behavior."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = FinishedUnitService.create_finished_unit(
            display_name="To Delete No Session",
            recipe_id=recipe.id,
        )
        fu_id = fu.id

        result = FinishedUnitService.delete_finished_unit(fu_id)
        assert result is True

    def test_delete_with_session_checks_composition_refs(self, test_db):
        """Delete with session still checks composition references."""
        session = test_db()

        recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
        session.add(recipe)
        session.commit()

        fu = FinishedUnitService.create_finished_unit(
            display_name="Referenced Unit",
            recipe_id=recipe.id,
        )
        fu_id = fu.id

        # Create a FinishedGood and Composition referencing this FU
        fg = FinishedGood(
            display_name="Test FG",
            slug="test-fg",
            assembly_type=AssemblyType.BARE,
        )
        session.add(fg)
        session.flush()

        comp = Composition(
            assembly_id=fg.id,
            finished_unit_id=fu_id,
            component_quantity=1,
        )
        session.add(comp)
        session.commit()

        with session_scope() as sess:
            with pytest.raises(ReferencedUnitError):
                FinishedUnitService.delete_finished_unit(fu_id, session=sess)
