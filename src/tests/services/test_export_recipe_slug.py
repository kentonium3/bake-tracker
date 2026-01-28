"""
Tests for Recipe Slug Export - Feature 080.

This module tests the recipe slug fields added to exports in Feature 080:
- T018: Verify all exports include recipe_slug fields
"""

import json
import tempfile
from datetime import date
from pathlib import Path

import pytest

from src.models.event import Event, EventProductionTarget
from src.models.finished_unit import FinishedUnit, YieldMode
from src.models.ingredient import Ingredient
from src.models.production_run import ProductionRun
from src.models.recipe import Recipe, RecipeComponent
from src.services.coordinated_export_service import export_complete
from src.services.database import session_scope


def _get_records(json_path: Path) -> list:
    """Helper to extract records from export JSON file.

    Export files have structure: {"entity_type": "...", "records": [...], "version": "..."}
    """
    data = json.loads(json_path.read_text())
    return data.get("records", [])


class TestRecipeSlugExport:
    """Tests for recipe slug fields in exports (Feature 080)."""

    def test_recipes_export_includes_slug(self, test_db):
        """Test recipes.json includes slug and previous_slug fields."""
        with session_scope() as session:
            # Create a recipe
            recipe = Recipe(
                name="Test Recipe",
                slug="test-recipe",
                previous_slug="old-test-recipe",
                category="Test Category",
            )
            session.add(recipe)
            session.commit()

        # Export
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            # Verify
            recipes_file = tmp_path / "recipes.json"
            assert recipes_file.exists()
            records = _get_records(recipes_file)

            assert len(records) >= 1
            recipe_data = next(r for r in records if r["name"] == "Test Recipe")
            assert "slug" in recipe_data
            assert recipe_data["slug"] == "test-recipe"
            assert "previous_slug" in recipe_data
            assert recipe_data["previous_slug"] == "old-test-recipe"

    def test_recipes_export_slug_after_name(self, test_db):
        """Test slug fields appear immediately after name in export."""
        with session_scope() as session:
            recipe = Recipe(
                name="Ordered Recipe",
                slug="ordered-recipe",
                category="Test",
            )
            session.add(recipe)
            session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            recipes_file = tmp_path / "recipes.json"
            records = _get_records(recipes_file)
            recipe_data = next(r for r in records if r["name"] == "Ordered Recipe")

            # Check key order (slug should come after name)
            keys = list(recipe_data.keys())
            name_idx = keys.index("name")
            slug_idx = keys.index("slug")
            assert slug_idx == name_idx + 1, "slug should immediately follow name"

    def test_finished_units_export_includes_recipe_slug(self, test_db):
        """Test finished_units.json includes recipe_slug field."""
        with session_scope() as session:
            # Create recipe and finished unit
            recipe = Recipe(
                name="Cookie Recipe",
                slug="cookie-recipe",
                category="Cookies",
            )
            session.add(recipe)
            session.flush()

            fu = FinishedUnit(
                display_name="Cookies",
                slug="cookies",
                recipe_id=recipe.id,
                category="Baked",
                yield_mode=YieldMode.DISCRETE_COUNT,
                items_per_batch=24,
                item_unit="cookie",
            )
            session.add(fu)
            session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            fu_file = tmp_path / "finished_units.json"
            assert fu_file.exists()
            records = _get_records(fu_file)

            fu_data = next(f for f in records if f["display_name"] == "Cookies")
            assert "recipe_slug" in fu_data
            assert fu_data["recipe_slug"] == "cookie-recipe"
            assert "recipe_name" in fu_data  # Backward compat
            assert fu_data["recipe_name"] == "Cookie Recipe"

    def test_events_export_includes_recipe_slug_in_targets(self, test_db):
        """Test events.json production targets include recipe_slug."""
        with session_scope() as session:
            # Create recipe
            recipe = Recipe(
                name="Pie Recipe",
                slug="pie-recipe",
                category="Pies",
            )
            session.add(recipe)
            session.flush()

            # Create event with production target
            event = Event(
                name="Holiday Event",
                event_date=date(2026, 12, 25),
                year=2026,
            )
            session.add(event)
            session.flush()

            target = EventProductionTarget(
                event_id=event.id,
                recipe_id=recipe.id,
                target_batches=5,
            )
            session.add(target)
            session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            events_file = tmp_path / "events.json"
            assert events_file.exists()
            records = _get_records(events_file)

            event_data = next(e for e in records if e["name"] == "Holiday Event")
            targets = event_data.get("production_targets", [])
            assert len(targets) >= 1

            target_data = targets[0]
            assert "recipe_slug" in target_data
            assert target_data["recipe_slug"] == "pie-recipe"
            assert "recipe_name" in target_data  # Backward compat
            assert target_data["recipe_name"] == "Pie Recipe"

    def test_production_runs_export_includes_recipe_slug(self, test_db):
        """Test production_runs.json includes recipe_slug field."""
        with session_scope() as session:
            # Create recipe
            recipe = Recipe(
                name="Bread Recipe",
                slug="bread-recipe",
                category="Breads",
            )
            session.add(recipe)
            session.flush()

            # Create finished unit for the recipe
            fu = FinishedUnit(
                display_name="Loaf",
                slug="loaf",
                recipe_id=recipe.id,
                category="Bread",
                yield_mode=YieldMode.DISCRETE_COUNT,
                items_per_batch=2,
                item_unit="loaf",
            )
            session.add(fu)
            session.flush()

            # Create production run
            run = ProductionRun(
                recipe_id=recipe.id,
                finished_unit_id=fu.id,
                num_batches=2,
                expected_yield=4,
                actual_yield=4,  # Required field
            )
            session.add(run)
            session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            runs_file = tmp_path / "production_runs.json"
            assert runs_file.exists()
            records = _get_records(runs_file)

            assert len(records) >= 1
            run_data = records[0]
            assert "recipe_slug" in run_data
            assert run_data["recipe_slug"] == "bread-recipe"
            assert "recipe_name" in run_data  # Backward compat
            assert run_data["recipe_name"] == "Bread Recipe"

    def test_recipe_components_include_slug(self, test_db):
        """Test recipe components include component_recipe_slug."""
        with session_scope() as session:
            # Create component and parent recipes
            component = Recipe(
                name="Dough",
                slug="dough",
                category="Base",
            )
            parent = Recipe(
                name="Bread",
                slug="bread",
                category="Bread",
            )
            session.add_all([component, parent])
            session.flush()

            # Link as component
            rc = RecipeComponent(
                recipe_id=parent.id,
                component_recipe_id=component.id,
                quantity=1.0,
            )
            session.add(rc)
            session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            recipes_file = tmp_path / "recipes.json"
            records = _get_records(recipes_file)

            # Find parent recipe
            parent_data = next(r for r in records if r["slug"] == "bread")
            components = parent_data.get("components", [])
            assert len(components) >= 1

            component_data = components[0]
            assert "component_recipe_slug" in component_data
            assert component_data["component_recipe_slug"] == "dough"
            assert "component_recipe_name" in component_data  # Backward compat
            assert component_data["component_recipe_name"] == "Dough"

    def test_recipe_with_null_previous_slug(self, test_db):
        """Test recipe with null previous_slug exports correctly."""
        with session_scope() as session:
            recipe = Recipe(
                name="New Recipe",
                slug="new-recipe",
                previous_slug=None,  # No previous slug
                category="Test",
            )
            session.add(recipe)
            session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            recipes_file = tmp_path / "recipes.json"
            records = _get_records(recipes_file)

            recipe_data = next(r for r in records if r["name"] == "New Recipe")
            assert "previous_slug" in recipe_data
            assert recipe_data["previous_slug"] is None
