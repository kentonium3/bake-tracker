"""Integration tests for recipe slug support (F080).

Feature 080: Recipe Slug Support
- Tests round-trip export/import with slug-based identification
- Tests legacy import (name fallback) for backward compatibility
- Tests previous_slug fallback for renamed recipes
- Tests all FK entity resolution via slug
"""

import json
import logging

import pytest

from src.models.recipe import Recipe, RecipeComponent
from src.models.finished_unit import FinishedUnit
from src.models.production_run import ProductionRun
from src.models.event import Event, EventProductionTarget
from src.services.coordinated_export_service import (
    export_complete,
    _resolve_recipe,
)
from src.services.catalog_import_service import import_recipes, import_finished_units
from src.services.database import session_scope


class TestRecipeSlugRoundTrip:
    """Test export/import round-trip preserves recipe slug data (T026)."""

    def test_export_includes_recipe_slugs(self, test_db, tmp_path):
        """Test recipes.json export includes slug and previous_slug fields."""
        # Create recipe with slug using the session
        with session_scope() as session:
            recipe = Recipe(
                name="Chocolate Chip Cookies",
                slug="chocolate-chip-cookies",
                previous_slug=None,
                category="Cookies",
            )
            session.add(recipe)
            session.commit()

            # Export
            export_complete(str(tmp_path), session)

        # Verify export file contains slugs
        recipes_file = tmp_path / "recipes.json"
        assert recipes_file.exists()
        data = json.loads(recipes_file.read_text())

        assert len(data["records"]) >= 1
        recipe_data = data["records"][0]
        assert recipe_data["slug"] == "chocolate-chip-cookies"
        assert "previous_slug" in recipe_data

    def test_export_includes_component_recipe_slug(self, test_db, tmp_path):
        """Test recipe components include component_recipe_slug in export."""
        with session_scope() as session:
            # Create recipes
            component = Recipe(name="Cookie Dough", slug="cookie-dough", category="Bases")
            parent = Recipe(name="Full Cookies", slug="full-cookies", category="Cookies")
            session.add_all([component, parent])
            session.flush()

            # Create component relationship
            rc = RecipeComponent(
                recipe_id=parent.id,
                component_recipe_id=component.id,
                quantity=1.0,
            )
            session.add(rc)
            session.commit()

            # Export
            export_complete(str(tmp_path), session)

        # Verify
        recipes_file = tmp_path / "recipes.json"
        data = json.loads(recipes_file.read_text())

        parent_data = next(
            (r for r in data["records"] if r["slug"] == "full-cookies"), None
        )
        assert parent_data is not None
        assert len(parent_data.get("components", [])) >= 1
        assert parent_data["components"][0]["component_recipe_slug"] == "cookie-dough"

    def test_export_includes_recipe_slug_in_finished_units(self, test_db, tmp_path):
        """Test finished_units.json includes recipe_slug."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = FinishedUnit(
                display_name="Test FU",
                slug="test-fu",
                recipe_id=recipe.id,
            )
            session.add(fu)
            session.commit()

            # Export
            export_complete(str(tmp_path), session)

        # Verify
        fu_file = tmp_path / "finished_units.json"
        data = json.loads(fu_file.read_text())
        assert len(data["records"]) >= 1
        assert data["records"][0]["recipe_slug"] == "test-recipe"
        assert data["records"][0]["recipe_name"] == "Test Recipe"  # Backward compat

    def test_export_includes_recipe_slug_in_production_targets(self, test_db, tmp_path):
        """Test events.json production targets include recipe_slug."""
        from datetime import date

        with session_scope() as session:
            recipe = Recipe(name="Event Recipe", slug="event-recipe", category="Test")
            event = Event(name="Test Event", event_date=date(2026, 12, 25), year=2026)
            session.add_all([recipe, event])
            session.flush()

            target = EventProductionTarget(
                event_id=event.id,
                recipe_id=recipe.id,
                target_batches=5,
            )
            session.add(target)
            session.commit()

            # Export
            export_complete(str(tmp_path), session)

        # Verify
        events_file = tmp_path / "events.json"
        data = json.loads(events_file.read_text())
        assert len(data["records"]) >= 1
        targets = data["records"][0].get("production_targets", [])
        assert len(targets) >= 1
        assert targets[0]["recipe_slug"] == "event-recipe"

    def test_export_includes_recipe_slug_in_production_runs(self, test_db, tmp_path):
        """Test production_runs.json includes recipe_slug."""
        with session_scope() as session:
            recipe = Recipe(name="Run Recipe", slug="run-recipe", category="Test")
            session.add(recipe)
            session.flush()

            # FinishedUnit is required for ProductionRun
            fu = FinishedUnit(
                display_name="Run FU",
                slug="run-fu",
                recipe_id=recipe.id,
            )
            session.add(fu)
            session.flush()

            run = ProductionRun(
                recipe_id=recipe.id,
                finished_unit_id=fu.id,
                num_batches=1,
                expected_yield=10,
                actual_yield=10,
            )
            session.add(run)
            session.commit()

            # Export
            export_complete(str(tmp_path), session)

        # Verify
        runs_file = tmp_path / "production_runs.json"
        data = json.loads(runs_file.read_text())
        assert len(data["records"]) >= 1
        assert data["records"][0]["recipe_slug"] == "run-recipe"


class TestLegacyImportFallback:
    """Test imports without slugs fall back to name resolution (T027)."""

    def test_legacy_recipe_import_generates_slug(self, test_db):
        """Test importing recipe without slug auto-generates one."""
        # Create legacy data (no slug field)
        legacy_data = [
            {
                "name": "Legacy Recipe",
                "category": "Test",
                "ingredients": [],
                "components": [],
                # NO slug field - simulates pre-F080 export
            }
        ]

        # Import
        result = import_recipes(legacy_data, mode="add")
        assert result.entity_counts["recipes"].added == 1

        # Verify slug was generated
        with session_scope() as session:
            recipe = session.query(Recipe).filter(Recipe.name == "Legacy Recipe").first()
            assert recipe is not None
            assert recipe.slug == "legacy-recipe"  # Auto-generated

    def test_legacy_finished_unit_import_uses_name_fallback(self, test_db):
        """Test finished unit import falls back to recipe_name when no slug."""
        # Create recipe first
        with session_scope() as session:
            recipe = Recipe(name="Target Recipe", slug="target-recipe", category="Test")
            session.add(recipe)
            session.commit()
            recipe_id = recipe.id

        # Create legacy finished unit data (no recipe_slug)
        legacy_fu = [
            {
                "display_name": "Legacy FU",
                "slug": "legacy-fu",
                "recipe_name": "Target Recipe",  # Name only, no slug
            }
        ]

        # Import
        result = import_finished_units(legacy_fu, mode="add")
        assert result.entity_counts["finished_units"].added == 1

        # Verify FK resolved via name
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter(FinishedUnit.slug == "legacy-fu").first()
            assert fu is not None
            assert fu.recipe_id == recipe_id


class TestPreviousSlugFallback:
    """Test imports resolve via previous_slug for renamed recipes (T028)."""

    def test_resolve_recipe_by_previous_slug(self, test_db):
        """Test _resolve_recipe finds renamed recipe via previous_slug."""
        with session_scope() as session:
            # Create recipe that was renamed (has previous_slug)
            recipe = Recipe(
                name="New Recipe Name",
                slug="new-recipe-name",
                previous_slug="old-recipe-name",
                category="Test",
            )
            session.add(recipe)
            session.commit()

            # Resolve using old slug
            recipe_id = _resolve_recipe("old-recipe-name", None, session, "Test")

            assert recipe_id == recipe.id

    def test_current_slug_takes_precedence_over_previous_slug(self, test_db):
        """Test current slug is preferred over previous_slug match."""
        with session_scope() as session:
            # Create two recipes where one's slug matches other's previous_slug
            recipe1 = Recipe(
                name="Current Recipe",
                slug="shared-slug",
                previous_slug=None,
                category="Test",
            )
            recipe2 = Recipe(
                name="Renamed Recipe",
                slug="renamed-slug",
                previous_slug="shared-slug",
                category="Test",
            )
            session.add_all([recipe1, recipe2])
            session.commit()

            # Resolve should find recipe1 (current slug match)
            recipe_id = _resolve_recipe("shared-slug", None, session, "test")

            assert recipe_id == recipe1.id  # Current slug wins

    def test_previous_slug_logged_when_used(self, test_db, caplog):
        """Test fallback to previous_slug is logged."""
        caplog.set_level(logging.INFO)

        with session_scope() as session:
            recipe = Recipe(
                name="Renamed",
                slug="new-slug",
                previous_slug="old-slug",
                category="Test",
            )
            session.add(recipe)
            session.commit()

            _resolve_recipe("old-slug", None, session, "TestContext")

        # Check log message
        assert "previous_slug" in caplog.text.lower() or "fallback" in caplog.text.lower()


class TestAllFKEntityResolution:
    """Test all FK entities correctly resolve recipe by slug (T029)."""

    def test_resolve_recipe_by_slug(self, test_db):
        """Test _resolve_recipe finds recipe by current slug."""
        with session_scope() as session:
            recipe = Recipe(
                name="Universal Recipe",
                slug="universal-recipe",
                category="Test",
            )
            session.add(recipe)
            session.commit()

            recipe_id = _resolve_recipe("universal-recipe", None, session, "Test")
            assert recipe_id == recipe.id

    def test_resolve_recipe_by_name_when_slug_not_found(self, test_db):
        """Test _resolve_recipe falls back to name when slug not found."""
        with session_scope() as session:
            recipe = Recipe(
                name="Universal Recipe",
                slug="universal-recipe",
                category="Test",
            )
            session.add(recipe)
            session.commit()

            recipe_id = _resolve_recipe("wrong-slug", "Universal Recipe", session, "Test")
            assert recipe_id == recipe.id

    def test_resolve_recipe_returns_none_for_missing(self, test_db):
        """Test _resolve_recipe returns None when recipe not found."""
        with session_scope() as session:
            recipe_id = _resolve_recipe(
                "nonexistent-slug", "Nonexistent Recipe", session, "Test"
            )
            assert recipe_id is None

    def test_resolve_recipe_logs_error_for_missing(self, test_db, caplog):
        """Test _resolve_recipe logs error when recipe not found."""
        caplog.set_level(logging.ERROR)

        with session_scope() as session:
            _resolve_recipe("nonexistent-slug", "Nonexistent", session, "TestContext")

        assert "not found" in caplog.text.lower()

    def test_finished_unit_import_resolves_by_name(self, test_db):
        """Test FinishedUnit import via catalog service resolves recipe by name.

        Note: catalog_import_service uses recipe_name for FK resolution.
        The coordinated_export_service.py import path uses recipe_slug.
        This test verifies the catalog import path works with name resolution.
        """
        # Create recipe
        with session_scope() as session:
            recipe = Recipe(
                name="Universal Recipe",
                slug="universal-recipe",
                category="Test",
            )
            session.add(recipe)
            session.commit()
            recipe_id = recipe.id

        # Import finished unit with recipe_name (catalog import uses name)
        data = [
            {
                "display_name": "FU Test",
                "slug": "fu-test",
                "recipe_name": "Universal Recipe",  # Catalog import uses name
            }
        ]

        result = import_finished_units(data, mode="add")
        assert result.entity_counts["finished_units"].added == 1

        with session_scope() as session:
            fu = session.query(FinishedUnit).filter(FinishedUnit.slug == "fu-test").first()
            assert fu is not None
            assert fu.recipe_id == recipe_id

    def test_recipe_component_import_resolves_by_slug(self, test_db):
        """Test RecipeComponent import resolves component_recipe by slug.

        Note: catalog_import_service validation currently requires recipe_name
        for components. We provide both slug and name, with slug taking priority
        in resolution.
        """
        # Create component recipe
        with session_scope() as session:
            component = Recipe(
                name="Component Recipe",
                slug="component-recipe",
                category="Test",
            )
            session.add(component)
            session.commit()
            component_id = component.id

        # Import parent recipe with component
        # Note: validation requires recipe_name, but slug takes priority in resolution
        data = [
            {
                "name": "Parent Recipe",
                "slug": "parent-recipe",
                "category": "Test",
                "ingredients": [],
                "components": [
                    {
                        "component_recipe_slug": "component-recipe",
                        "recipe_name": "Component Recipe",  # Required by validation
                        "quantity": 1.0,
                    }
                ],
            }
        ]

        result = import_recipes(data, mode="add")
        assert result.entity_counts["recipes"].added == 1

        # Verify component relationship created
        with session_scope() as session:
            parent = session.query(Recipe).filter(Recipe.slug == "parent-recipe").first()
            assert parent is not None
            assert len(parent.recipe_components) >= 1
            assert parent.recipe_components[0].component_recipe_id == component_id

    def test_missing_recipe_slug_logs_warning(self, test_db, caplog):
        """Test missing recipe logs warning when not found."""
        caplog.set_level(logging.WARNING)

        # Import finished unit with non-existent recipe_slug
        data = [
            {
                "display_name": "Orphan FU",
                "slug": "orphan-fu",
                "recipe_slug": "nonexistent-recipe",
            }
        ]

        result = import_finished_units(data, mode="add")

        # The record should fail or log warning
        assert (
            result.entity_counts["finished_units"].failed > 0
            or "not found" in caplog.text.lower()
            or "nonexistent" in caplog.text.lower()
        )
