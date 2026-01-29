"""Tests for yield_type export/import functionality.

Feature 083 - Dual-Yield Support

Tests verify:
- Export includes yield_type field in finished_units JSON
- Import reads yield_type with default='SERVING' for backward compatibility
- Import validates yield_type is 'EA' or 'SERVING'
- Round-trip test: export -> import preserves yield_type
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.models.finished_unit import FinishedUnit
from src.models.recipe import Recipe
from src.services.coordinated_export_service import (
    export_complete,
    import_complete,
)
from src.services.database import session_scope


class TestExportYieldType:
    """Test yield_type is included in exports."""

    def test_export_includes_yield_type(self, test_db):
        """Exported finished_units.json includes yield_type field."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = FinishedUnit(
                slug="test-fu",
                display_name="Test FU",
                recipe_id=recipe.id,
                item_unit="cookie",
                items_per_batch=24,
                yield_type="EA",
            )
            session.add(fu)
            session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            fu_file = tmp_path / "finished_units.json"
            assert fu_file.exists()

            with open(fu_file) as f:
                data = json.load(f)

            # Entity files have structure: {"version": "1.0", "entity_type": ..., "records": [...]}
            records = data.get("records", [])
            fu_record = next(r for r in records if r["slug"] == "test-fu")
            assert "yield_type" in fu_record
            assert fu_record["yield_type"] == "EA"

    def test_export_includes_serving_yield_type(self, test_db):
        """Exported finished_units.json includes SERVING yield_type."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = FinishedUnit(
                slug="test-fu-serving",
                display_name="Test FU Serving",
                recipe_id=recipe.id,
                item_unit="slice",
                items_per_batch=8,
                yield_type="SERVING",
            )
            session.add(fu)
            session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            fu_file = tmp_path / "finished_units.json"
            with open(fu_file) as f:
                data = json.load(f)

            records = data.get("records", [])
            fu_record = next(r for r in records if r["slug"] == "test-fu-serving")
            assert fu_record["yield_type"] == "SERVING"


class TestImportYieldType:
    """Test yield_type is read correctly during import."""

    def test_import_with_yield_type_ea(self, test_db):
        """Import correctly reads yield_type='EA' from JSON."""
        # Create recipe first
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.commit()

        # Create export with yield_type
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create minimal manifest
            manifest = {
                "version": "3.2",
                "files": [
                    {"entity_type": "finished_units", "filename": "finished_units.json", "import_order": 10}
                ]
            }
            with open(tmp_path / "manifest.json", "w") as f:
                json.dump(manifest, f)

            # Write finished_units.json with correct format
            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [{
                    "slug": "test-fu",
                    "display_name": "Test FU",
                    "recipe_slug": "test-recipe",
                    "yield_mode": "discrete_count",
                    "yield_type": "EA",
                    "items_per_batch": 1,
                    "item_unit": "cake",
                    "inventory_count": 0,
                }]
            }
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            # Import
            import_complete(tmp_path, clear_existing=False)

        # Verify
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(slug="test-fu").first()
            assert fu is not None
            assert fu.yield_type == "EA"

    def test_import_without_yield_type_defaults_to_serving(self, test_db):
        """Import without yield_type defaults to SERVING."""
        # Create recipe first
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.commit()

        # Create export WITHOUT yield_type (old format)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            manifest = {
                "version": "3.2",
                "files": [
                    {"entity_type": "finished_units", "filename": "finished_units.json", "import_order": 10}
                ]
            }
            with open(tmp_path / "manifest.json", "w") as f:
                json.dump(manifest, f)

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [{
                    "slug": "test-fu",
                    "display_name": "Test FU",
                    "recipe_slug": "test-recipe",
                    "yield_mode": "discrete_count",
                    # NO yield_type field - backward compat test
                    "items_per_batch": 24,
                    "item_unit": "cookie",
                    "inventory_count": 0,
                }]
            }
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            import_complete(tmp_path, clear_existing=False)

        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(slug="test-fu").first()
            assert fu is not None
            assert fu.yield_type == "SERVING"  # Default

    def test_import_with_invalid_yield_type_defaults_to_serving(self, test_db):
        """Import with invalid yield_type defaults to SERVING."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            manifest = {
                "version": "3.2",
                "files": [
                    {"entity_type": "finished_units", "filename": "finished_units.json", "import_order": 10}
                ]
            }
            with open(tmp_path / "manifest.json", "w") as f:
                json.dump(manifest, f)

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [{
                    "slug": "test-fu",
                    "display_name": "Test FU",
                    "recipe_slug": "test-recipe",
                    "yield_mode": "discrete_count",
                    "yield_type": "INVALID",  # Invalid value
                    "items_per_batch": 24,
                    "item_unit": "cookie",
                    "inventory_count": 0,
                }]
            }
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            import_complete(tmp_path, clear_existing=False)

        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(slug="test-fu").first()
            assert fu is not None
            assert fu.yield_type == "SERVING"  # Defaulted


class TestExportImportRoundTrip:
    """Test full export/import cycle preserves yield_type."""

    def test_round_trip_preserves_yield_type(self, test_db):
        """Export -> import preserves yield_type values."""
        # Create test data with both EA and SERVING
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu_ea = FinishedUnit(
                slug="test-fu-ea",
                display_name="Test (EA)",
                recipe_id=recipe.id,
                item_unit="cake",
                items_per_batch=1,
                yield_type="EA",
            )
            fu_serving = FinishedUnit(
                slug="test-fu-serving",
                display_name="Test (Serving)",
                recipe_id=recipe.id,
                item_unit="slice",  # Different item_unit to avoid constraint issues
                items_per_batch=8,
                yield_type="SERVING",
            )
            session.add_all([fu_ea, fu_serving])
            session.commit()

        # Export
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            # Import with clear_existing=True (full replace mode)
            # This will clear existing data and import from export
            import_complete(tmp_path, clear_existing=True)

        # Verify
        with session_scope() as session:
            fu_ea = session.query(FinishedUnit).filter_by(slug="test-fu-ea").first()
            fu_serving = session.query(FinishedUnit).filter_by(slug="test-fu-serving").first()

            assert fu_ea is not None
            assert fu_ea.yield_type == "EA"

            assert fu_serving is not None
            assert fu_serving.yield_type == "SERVING"


class TestImportDuplicateHandling:
    """Test duplicate handling during import."""

    def test_import_skips_duplicate_slug(self, test_db):
        """Import skips finished_unit with duplicate slug."""
        # Create recipe and existing finished_unit
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            # Create existing FU
            existing_fu = FinishedUnit(
                slug="existing-fu",
                display_name="Existing FU",
                recipe_id=recipe.id,
                item_unit="cookie",
                items_per_batch=24,
                yield_type="SERVING",
            )
            session.add(existing_fu)
            session.commit()

        # Try to import FU with same slug
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            manifest = {
                "version": "3.2",
                "files": [
                    {"entity_type": "finished_units", "filename": "finished_units.json", "import_order": 10}
                ]
            }
            with open(tmp_path / "manifest.json", "w") as f:
                json.dump(manifest, f)

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [{
                    "slug": "existing-fu",  # Same slug - should be skipped
                    "display_name": "Different Name",
                    "recipe_slug": "test-recipe",
                    "yield_mode": "discrete_count",
                    "yield_type": "SERVING",
                    "items_per_batch": 12,
                    "item_unit": "cookie",
                    "inventory_count": 0,
                }]
            }
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            # Import should skip the duplicate slug
            import_complete(tmp_path, clear_existing=False)

        # Verify only original exists (not overwritten)
        with session_scope() as session:
            all_fus = session.query(FinishedUnit).all()
            assert len(all_fus) == 1
            assert all_fus[0].slug == "existing-fu"
            assert all_fus[0].display_name == "Existing FU"  # Original, not imported

    def test_import_allows_same_unit_and_yield_type_different_slug(self, test_db):
        """Import allows multiple finished_units with same (item_unit, yield_type) but different slugs."""
        # Create recipe and existing finished_unit
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            existing_fu = FinishedUnit(
                slug="large-cookie",
                display_name="Large Cookie",
                recipe_id=recipe.id,
                item_unit="cookie",
                items_per_batch=24,
                yield_type="SERVING",
            )
            session.add(existing_fu)
            session.commit()

        # Import FU with same (item_unit, yield_type) but different slug
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            manifest = {
                "version": "3.2",
                "files": [
                    {"entity_type": "finished_units", "filename": "finished_units.json", "import_order": 10}
                ]
            }
            with open(tmp_path / "manifest.json", "w") as f:
                json.dump(manifest, f)

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [{
                    "slug": "small-cookie",  # Different slug
                    "display_name": "Small Cookie",
                    "recipe_slug": "test-recipe",
                    "yield_mode": "discrete_count",
                    "yield_type": "SERVING",  # Same yield_type
                    "items_per_batch": 12,
                    "item_unit": "cookie",  # Same item_unit
                    "inventory_count": 0,
                }]
            }
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            import_complete(tmp_path, clear_existing=False)

        # Verify both exist
        with session_scope() as session:
            all_fus = session.query(FinishedUnit).all()
            assert len(all_fus) == 2
            slugs = {fu.slug for fu in all_fus}
            assert "large-cookie" in slugs
            assert "small-cookie" in slugs

    def test_import_allows_different_yield_types_same_item_unit(self, test_db):
        """Import allows same item_unit with different yield_type."""
        # Create recipe and existing finished_unit with EA
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            existing_fu = FinishedUnit(
                slug="cake-ea",
                display_name="Whole Cake",
                recipe_id=recipe.id,
                item_unit="cake",
                items_per_batch=1,
                yield_type="EA",
            )
            session.add(existing_fu)
            session.commit()

        # Import FU with same item_unit but SERVING yield_type
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            manifest = {
                "version": "3.2",
                "files": [
                    {"entity_type": "finished_units", "filename": "finished_units.json", "import_order": 10}
                ]
            }
            with open(tmp_path / "manifest.json", "w") as f:
                json.dump(manifest, f)

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [{
                    "slug": "cake-serving",
                    "display_name": "Cake Slices",
                    "recipe_slug": "test-recipe",
                    "yield_mode": "discrete_count",
                    "yield_type": "SERVING",  # Different yield_type
                    "items_per_batch": 8,
                    "item_unit": "cake",  # Same item_unit
                    "inventory_count": 0,
                }]
            }
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            import_complete(tmp_path, clear_existing=False)

        # Verify both exist
        with session_scope() as session:
            all_fus = session.query(FinishedUnit).all()
            assert len(all_fus) == 2

            slugs = {fu.slug for fu in all_fus}
            assert "cake-ea" in slugs
            assert "cake-serving" in slugs
