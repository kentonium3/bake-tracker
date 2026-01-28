"""
Tests for Recipe Slug Import Resolution - Feature 080.

This module tests the slug-based recipe resolution in imports:
- T019: Recipe import with slug support
- T020: _resolve_recipe() helper function
- T021: FinishedUnit import slug resolution
- T022: EventProductionTarget import slug resolution
- T023: ProductionRun import slug resolution
- T024: RecipeComponent import slug resolution
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
from src.services.coordinated_export_service import (
    _resolve_recipe,
    export_complete,
    import_complete,
)
from src.services.database import session_scope


class TestResolveRecipeHelper:
    """Tests for the _resolve_recipe() helper function (T020)."""

    def test_resolve_by_slug(self, test_db):
        """Test resolution by slug succeeds."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            result = _resolve_recipe("test-recipe", None, session, "test")
            assert result == recipe.id

    def test_resolve_by_previous_slug(self, test_db):
        """Test resolution falls back to previous_slug."""
        with session_scope() as session:
            recipe = Recipe(
                name="Renamed Recipe",
                slug="new-slug",
                previous_slug="old-slug",
                category="Test",
            )
            session.add(recipe)
            session.flush()

            # Using old slug should find via previous_slug
            result = _resolve_recipe("old-slug", None, session, "test")
            assert result == recipe.id

    def test_resolve_by_name_fallback(self, test_db):
        """Test resolution falls back to name."""
        with session_scope() as session:
            recipe = Recipe(name="Legacy Recipe", slug="legacy-recipe", category="Test")
            session.add(recipe)
            session.flush()

            # Using name only (no slug)
            result = _resolve_recipe(None, "Legacy Recipe", session, "test")
            assert result == recipe.id

    def test_resolve_by_name_when_slug_not_found(self, test_db):
        """Test name fallback when provided slug doesn't match."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            # Slug doesn't match, but name does
            result = _resolve_recipe("wrong-slug", "Test Recipe", session, "test")
            assert result == recipe.id

    def test_resolve_returns_none_when_not_found(self, test_db):
        """Test returns None when recipe not found."""
        with session_scope() as session:
            result = _resolve_recipe("nonexistent", "Also Not Found", session, "test")
            assert result is None

    def test_resolve_returns_none_when_no_identifiers(self, test_db):
        """Test returns None when neither slug nor name provided."""
        with session_scope() as session:
            result = _resolve_recipe(None, None, session, "test")
            assert result is None


class TestRecipeImportWithSlug:
    """Tests for recipe import with slug support (T019)."""

    def test_import_recipe_with_slug(self, test_db):
        """Test importing recipe with slug field."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create export data with slug
            recipes_data = {
                "version": "1.0",
                "entity_type": "recipes",
                "records": [
                    {
                        "name": "Test Recipe",
                        "slug": "test-recipe",
                        "previous_slug": "old-test-recipe",
                        "category": "Test",
                        "ingredients": [],
                        "components": [],
                    }
                ],
            }

            (tmp_path / "recipes.json").write_text(json.dumps(recipes_data))
            (tmp_path / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "files": [
                            {
                                "filename": "recipes.json",
                                "entity_type": "recipes",
                                "import_order": 4,
                            }
                        ],
                    }
                )
            )

            # Import
            import_complete(str(tmp_path))

            # Verify
            with session_scope() as session:
                recipe = session.query(Recipe).filter(Recipe.name == "Test Recipe").first()
                assert recipe is not None
                assert recipe.slug == "test-recipe"
                assert recipe.previous_slug == "old-test-recipe"

    def test_import_recipe_generates_slug_when_missing(self, test_db):
        """Test slug is generated for legacy imports without slug."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create export data WITHOUT slug (legacy format)
            recipes_data = {
                "version": "1.0",
                "entity_type": "recipes",
                "records": [
                    {
                        "name": "Legacy Recipe",
                        "category": "Test",
                        "ingredients": [],
                        "components": [],
                    }
                ],
            }

            (tmp_path / "recipes.json").write_text(json.dumps(recipes_data))
            (tmp_path / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "files": [
                            {
                                "filename": "recipes.json",
                                "entity_type": "recipes",
                                "import_order": 4,
                            }
                        ],
                    }
                )
            )

            # Import
            import_complete(str(tmp_path))

            # Verify slug was generated
            with session_scope() as session:
                recipe = session.query(Recipe).filter(Recipe.name == "Legacy Recipe").first()
                assert recipe is not None
                assert recipe.slug == "legacy-recipe"


class TestFinishedUnitImportWithSlug:
    """Tests for FinishedUnit import with slug resolution (T021)."""

    def test_import_finished_unit_by_recipe_slug(self, test_db):
        """Test FinishedUnit import resolves recipe by slug."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Include recipe in import (import_complete clears all data)
            recipes_data = {
                "version": "1.0",
                "entity_type": "recipes",
                "records": [
                    {
                        "name": "Cookie Recipe",
                        "slug": "cookie-recipe",
                        "category": "Cookies",
                        "ingredients": [],
                        "components": [],
                    }
                ],
            }

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [
                    {
                        "display_name": "Cookies",
                        "slug": "cookies",
                        "recipe_slug": "cookie-recipe",
                        "recipe_name": "Cookie Recipe",
                        "category": "Baked",
                        "yield_mode": "discrete_count",
                        "items_per_batch": 24,
                        "item_unit": "cookie",
                    }
                ],
            }

            (tmp_path / "recipes.json").write_text(json.dumps(recipes_data))
            (tmp_path / "finished_units.json").write_text(json.dumps(fu_data))
            (tmp_path / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "files": [
                            {
                                "filename": "recipes.json",
                                "entity_type": "recipes",
                                "import_order": 4,
                            },
                            {
                                "filename": "finished_units.json",
                                "entity_type": "finished_units",
                                "import_order": 5,
                            },
                        ],
                    }
                )
            )

            import_complete(str(tmp_path))

            with session_scope() as session:
                fu = session.query(FinishedUnit).filter(FinishedUnit.slug == "cookies").first()
                assert fu is not None
                assert fu.recipe.slug == "cookie-recipe"

    def test_import_finished_unit_by_previous_slug(self, test_db):
        """Test FinishedUnit import resolves via previous_slug fallback."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Recipe was renamed, has previous_slug
            recipes_data = {
                "version": "1.0",
                "entity_type": "recipes",
                "records": [
                    {
                        "name": "New Cookie Name",
                        "slug": "new-cookie-name",
                        "previous_slug": "old-cookie-slug",
                        "category": "Cookies",
                        "ingredients": [],
                        "components": [],
                    }
                ],
            }

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [
                    {
                        "display_name": "Cookies",
                        "slug": "cookies",
                        "recipe_slug": "old-cookie-slug",  # Old slug
                        "recipe_name": "Old Cookie Name",
                        "category": "Baked",
                        "yield_mode": "discrete_count",
                        "items_per_batch": 24,
                        "item_unit": "cookie",
                    }
                ],
            }

            (tmp_path / "recipes.json").write_text(json.dumps(recipes_data))
            (tmp_path / "finished_units.json").write_text(json.dumps(fu_data))
            (tmp_path / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "files": [
                            {
                                "filename": "recipes.json",
                                "entity_type": "recipes",
                                "import_order": 4,
                            },
                            {
                                "filename": "finished_units.json",
                                "entity_type": "finished_units",
                                "import_order": 5,
                            },
                        ],
                    }
                )
            )

            import_complete(str(tmp_path))

            with session_scope() as session:
                fu = session.query(FinishedUnit).filter(FinishedUnit.slug == "cookies").first()
                assert fu is not None
                assert fu.recipe.slug == "new-cookie-name"


class TestProductionRunImportWithSlug:
    """Tests for ProductionRun import with slug resolution (T023)."""

    def test_import_production_run_by_recipe_slug(self, test_db):
        """Test ProductionRun import resolves recipe by slug."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            recipes_data = {
                "version": "1.0",
                "entity_type": "recipes",
                "records": [
                    {
                        "name": "Bread Recipe",
                        "slug": "bread-recipe",
                        "category": "Breads",
                        "ingredients": [],
                        "components": [],
                    }
                ],
            }

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [
                    {
                        "display_name": "Loaf",
                        "slug": "loaf",
                        "recipe_slug": "bread-recipe",
                        "recipe_name": "Bread Recipe",
                        "category": "Bread",
                        "yield_mode": "discrete_count",
                        "items_per_batch": 2,
                        "item_unit": "loaf",
                    }
                ],
            }

            runs_data = {
                "version": "1.0",
                "entity_type": "production_runs",
                "records": [
                    {
                        "recipe_slug": "bread-recipe",
                        "recipe_name": "Bread Recipe",
                        "finished_unit_slug": "loaf",
                        "num_batches": 2,
                        "expected_yield": 4,
                        "actual_yield": 4,
                    }
                ],
            }

            (tmp_path / "recipes.json").write_text(json.dumps(recipes_data))
            (tmp_path / "finished_units.json").write_text(json.dumps(fu_data))
            (tmp_path / "production_runs.json").write_text(json.dumps(runs_data))
            (tmp_path / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "files": [
                            {
                                "filename": "recipes.json",
                                "entity_type": "recipes",
                                "import_order": 4,
                            },
                            {
                                "filename": "finished_units.json",
                                "entity_type": "finished_units",
                                "import_order": 5,
                            },
                            {
                                "filename": "production_runs.json",
                                "entity_type": "production_runs",
                                "import_order": 17,
                            },
                        ],
                    }
                )
            )

            import_complete(str(tmp_path))

            with session_scope() as session:
                run = session.query(ProductionRun).first()
                assert run is not None
                assert run.recipe.slug == "bread-recipe"


class TestEventProductionTargetImportWithSlug:
    """Tests for EventProductionTarget import with slug resolution (T022)."""

    def test_import_event_with_production_target_by_slug(self, test_db):
        """Test Event import resolves production target recipe by slug."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            recipes_data = {
                "version": "1.0",
                "entity_type": "recipes",
                "records": [
                    {
                        "name": "Pie Recipe",
                        "slug": "pie-recipe",
                        "category": "Pies",
                        "ingredients": [],
                        "components": [],
                    }
                ],
            }

            events_data = {
                "version": "1.0",
                "entity_type": "events",
                "records": [
                    {
                        "name": "Holiday Event",
                        "event_date": "2026-12-25",
                        "year": 2026,
                        "production_targets": [
                            {
                                "recipe_slug": "pie-recipe",
                                "recipe_name": "Pie Recipe",
                                "target_batches": 5,
                            }
                        ],
                        "assembly_targets": [],
                    }
                ],
            }

            (tmp_path / "recipes.json").write_text(json.dumps(recipes_data))
            (tmp_path / "events.json").write_text(json.dumps(events_data))
            (tmp_path / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "files": [
                            {
                                "filename": "recipes.json",
                                "entity_type": "recipes",
                                "import_order": 4,
                            },
                            {
                                "filename": "events.json",
                                "entity_type": "events",
                                "import_order": 16,
                            },
                        ],
                    }
                )
            )

            import_complete(str(tmp_path))

            with session_scope() as session:
                event = session.query(Event).filter(Event.name == "Holiday Event").first()
                assert event is not None
                assert len(event.production_targets) == 1
                assert event.production_targets[0].recipe.slug == "pie-recipe"
                assert event.production_targets[0].target_batches == 5


class TestRecipeComponentImportWithSlug:
    """Tests for RecipeComponent import with slug resolution (T024)."""

    def test_import_recipe_component_by_slug(self, test_db):
        """Test RecipeComponent import resolves component by slug."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Import both component and parent recipes
            recipes_data = {
                "version": "1.0",
                "entity_type": "recipes",
                "records": [
                    # Component recipe first
                    {
                        "name": "Dough",
                        "slug": "dough",
                        "category": "Base",
                        "ingredients": [],
                        "components": [],
                    },
                    # Parent recipe with component reference
                    {
                        "name": "Bread",
                        "slug": "bread",
                        "category": "Bread",
                        "ingredients": [],
                        "components": [
                            {
                                "component_recipe_slug": "dough",
                                "component_recipe_name": "Dough",
                                "quantity": 1.0,
                            }
                        ],
                    },
                ],
            }

            (tmp_path / "recipes.json").write_text(json.dumps(recipes_data))
            (tmp_path / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "files": [
                            {
                                "filename": "recipes.json",
                                "entity_type": "recipes",
                                "import_order": 4,
                            }
                        ],
                    }
                )
            )

            import_complete(str(tmp_path))

            with session_scope() as session:
                parent = session.query(Recipe).filter(Recipe.slug == "bread").first()
                assert parent is not None
                assert len(parent.recipe_components) == 1
                assert parent.recipe_components[0].component_recipe.slug == "dough"


class TestRoundTripWithSlugs:
    """Tests for export/import round-trip with slug fields.

    Note: Full round-trip testing requires both export (WP03) and import (WP04)
    changes. This test validates import behavior with manually created export data.
    """

    def test_import_with_complete_slug_data(self, test_db):
        """Test import preserves slug fields when provided in export data."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Simulate export data that would be created by WP03 export changes
            recipes_data = {
                "version": "1.0",
                "entity_type": "recipes",
                "records": [
                    {
                        "name": "Round Trip Recipe",
                        "slug": "round-trip-recipe",
                        "previous_slug": "old-round-trip",
                        "category": "Test",
                        "ingredients": [],
                        "components": [],
                    }
                ],
            }

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [
                    {
                        "display_name": "Test Unit",
                        "slug": "test-unit",
                        "recipe_slug": "round-trip-recipe",
                        "recipe_name": "Round Trip Recipe",
                        "category": "Test",
                        "yield_mode": "discrete_count",
                        "items_per_batch": 10,
                        "item_unit": "unit",
                    }
                ],
            }

            (tmp_path / "recipes.json").write_text(json.dumps(recipes_data))
            (tmp_path / "finished_units.json").write_text(json.dumps(fu_data))
            (tmp_path / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "files": [
                            {
                                "filename": "recipes.json",
                                "entity_type": "recipes",
                                "import_order": 4,
                            },
                            {
                                "filename": "finished_units.json",
                                "entity_type": "finished_units",
                                "import_order": 5,
                            },
                        ],
                    }
                )
            )

            import_complete(str(tmp_path))

            # Verify slugs preserved
            with session_scope() as session:
                recipe = (
                    session.query(Recipe)
                    .filter(Recipe.name == "Round Trip Recipe")
                    .first()
                )
                assert recipe is not None
                assert recipe.slug == "round-trip-recipe"
                assert recipe.previous_slug == "old-round-trip"

                fu = session.query(FinishedUnit).filter(FinishedUnit.slug == "test-unit").first()
                assert fu is not None
                assert fu.recipe.slug == "round-trip-recipe"


class TestLegacyImportBackwardCompatibility:
    """Tests for backward compatibility with legacy imports without slug fields."""

    def test_legacy_import_without_slug_uses_name_fallback(self, test_db):
        """Test import without recipe_slug field falls back to name."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Recipe import with slug
            recipes_data = {
                "version": "1.0",
                "entity_type": "recipes",
                "records": [
                    {
                        "name": "Legacy Name Recipe",
                        "slug": "legacy-name-recipe",
                        "category": "Test",
                        "ingredients": [],
                        "components": [],
                    }
                ],
            }

            # FinishedUnit with only recipe_name (no recipe_slug)
            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [
                    {
                        "display_name": "Legacy Unit",
                        "slug": "legacy-unit",
                        "recipe_name": "Legacy Name Recipe",  # No recipe_slug
                        "category": "Test",
                        "yield_mode": "discrete_count",
                        "items_per_batch": 5,
                        "item_unit": "unit",
                    }
                ],
            }

            (tmp_path / "recipes.json").write_text(json.dumps(recipes_data))
            (tmp_path / "finished_units.json").write_text(json.dumps(fu_data))
            (tmp_path / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "files": [
                            {
                                "filename": "recipes.json",
                                "entity_type": "recipes",
                                "import_order": 4,
                            },
                            {
                                "filename": "finished_units.json",
                                "entity_type": "finished_units",
                                "import_order": 5,
                            },
                        ],
                    }
                )
            )

            import_complete(str(tmp_path))

            with session_scope() as session:
                fu = session.query(FinishedUnit).filter(FinishedUnit.slug == "legacy-unit").first()
                assert fu is not None
                assert fu.recipe.name == "Legacy Name Recipe"
