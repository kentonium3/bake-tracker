"""Integration tests for 083 migration script."""
import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class Test083Migration:
    """Test the yield_type migration workflow."""

    def test_migration_script_adds_yield_type_wrapped_format(self):
        """Migration script adds yield_type to wrapped format records."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create export in wrapped format (current format)
            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [
                    {
                        "slug": "test-fu-1",
                        "display_name": "Test FU 1",
                        "recipe_slug": "test-recipe",
                        "yield_mode": "discrete_count",
                        # NO yield_type
                        "items_per_batch": 24,
                        "item_unit": "cookie",
                        "inventory_count": 0,
                    },
                    {
                        "slug": "test-fu-2",
                        "display_name": "Test FU 2",
                        "recipe_slug": "test-recipe",
                        "yield_mode": "discrete_count",
                        # NO yield_type
                        "items_per_batch": 1,
                        "item_unit": "cake",
                        "inventory_count": 0,
                    },
                ],
            }
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            # Run migration script
            result = subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Script failed: {result.stderr}"
            assert "Transformed 2 records" in result.stdout

            # Verify transformation
            with open(tmp_path / "finished_units.json") as f:
                transformed = json.load(f)

            # Should preserve wrapped structure
            assert "records" in transformed
            assert "version" in transformed
            assert transformed["entity_type"] == "finished_units"

            for record in transformed["records"]:
                assert "yield_type" in record
                assert record["yield_type"] == "SERVING"

    def test_migration_script_adds_yield_type_list_format(self):
        """Migration script adds yield_type to legacy list format records."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create export in legacy list format
            fu_data = [
                {
                    "slug": "test-fu-1",
                    "display_name": "Test FU 1",
                    "recipe_slug": "test-recipe",
                    "yield_mode": "discrete_count",
                    "items_per_batch": 24,
                    "item_unit": "cookie",
                    "inventory_count": 0,
                },
            ]
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            # Run migration script
            result = subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Script failed: {result.stderr}"
            assert "Transformed 1 records" in result.stdout

            # Verify transformation preserves list format
            with open(tmp_path / "finished_units.json") as f:
                transformed = json.load(f)

            assert isinstance(transformed, list)
            assert transformed[0]["yield_type"] == "SERVING"

    def test_migration_script_is_idempotent(self):
        """Running migration script twice doesn't duplicate yield_type."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [
                    {
                        "slug": "test-fu",
                        "display_name": "Test FU",
                        "recipe_slug": "test-recipe",
                        "yield_mode": "discrete_count",
                        "items_per_batch": 24,
                        "item_unit": "cookie",
                        "inventory_count": 0,
                    }
                ],
            }
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            # Run twice
            subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
            )
            result = subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
                text=True,
            )

            assert "already had yield_type" in result.stdout

            # Verify single yield_type value
            with open(tmp_path / "finished_units.json") as f:
                transformed = json.load(f)

            assert transformed["records"][0]["yield_type"] == "SERVING"

    def test_migration_script_creates_backup(self):
        """Migration script creates backup before modifying."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [
                    {
                        "slug": "test-fu",
                        "display_name": "Test FU",
                        "recipe_slug": "test-recipe",
                        "yield_mode": "discrete_count",
                        "items_per_batch": 24,
                        "item_unit": "cookie",
                        "inventory_count": 0,
                    }
                ],
            }
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            # Run migration
            result = subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0

            # Check backup was created
            backup_files = list(tmp_path.glob("finished_units.json.backup.*"))
            assert len(backup_files) == 1

            # Verify backup has original content (no yield_type)
            with open(backup_files[0]) as f:
                backup_data = json.load(f)
            assert "yield_type" not in backup_data["records"][0]

    def test_migration_script_handles_missing_file(self):
        """Migration script handles missing finished_units.json gracefully."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Don't create finished_units.json

            # Run migration
            result = subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            assert "skipped" in result.stdout.lower() or "not found" in result.stdout.lower()

    def test_migration_script_handles_invalid_directory(self):
        """Migration script errors on non-existent directory."""
        result = subprocess.run(
            ["python", "scripts/migrate_add_yield_type.py", "/nonexistent/path"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "not a directory" in result.stderr or "not a directory" in result.stdout

    def test_migration_script_preserves_existing_yield_type(self):
        """Migration script preserves existing yield_type values (e.g., EA)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [
                    {
                        "slug": "test-fu-serving",
                        "display_name": "Serving Item",
                        "yield_mode": "discrete_count",
                        "items_per_batch": 24,
                        "item_unit": "cookie",
                        # Already has yield_type
                        "yield_type": "SERVING",
                    },
                    {
                        "slug": "test-fu-ea",
                        "display_name": "EA Item",
                        "yield_mode": "discrete_count",
                        "items_per_batch": 1,
                        "item_unit": "cake",
                        # Already has EA
                        "yield_type": "EA",
                    },
                    {
                        "slug": "test-fu-new",
                        "display_name": "New Item",
                        "yield_mode": "discrete_count",
                        "items_per_batch": 12,
                        "item_unit": "muffin",
                        # No yield_type - should get SERVING
                    },
                ],
            }
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            # Run migration
            result = subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            assert "Transformed 1 records" in result.stdout
            assert "2 already had yield_type" in result.stdout

            # Verify values preserved
            with open(tmp_path / "finished_units.json") as f:
                transformed = json.load(f)

            records = {r["slug"]: r for r in transformed["records"]}
            assert records["test-fu-serving"]["yield_type"] == "SERVING"
            assert records["test-fu-ea"]["yield_type"] == "EA"  # Preserved!
            assert records["test-fu-new"]["yield_type"] == "SERVING"  # Added

    def test_migration_script_preserves_all_fields(self):
        """Migration script preserves all existing fields."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            fu_data = {
                "version": "1.0",
                "entity_type": "finished_units",
                "records": [
                    {
                        "uuid": "test-uuid-123",
                        "slug": "test-fu",
                        "display_name": "Test Cookies",
                        "recipe_slug": "test-recipe",
                        "recipe_name": "Test Recipe",
                        "category": "Cookies",
                        "yield_mode": "discrete_count",
                        "items_per_batch": 24,
                        "item_unit": "cookie",
                        "batch_percentage": None,
                        "portion_description": None,
                        "inventory_count": 5,
                        "description": "Delicious cookies",
                        "notes": "Make extra for tasting",
                    }
                ],
            }
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            # Run migration
            subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
            )

            # Verify all fields preserved
            with open(tmp_path / "finished_units.json") as f:
                transformed = json.load(f)

            record = transformed["records"][0]
            assert record["uuid"] == "test-uuid-123"
            assert record["slug"] == "test-fu"
            assert record["display_name"] == "Test Cookies"
            assert record["recipe_slug"] == "test-recipe"
            assert record["recipe_name"] == "Test Recipe"
            assert record["category"] == "Cookies"
            assert record["yield_mode"] == "discrete_count"
            assert record["items_per_batch"] == 24
            assert record["item_unit"] == "cookie"
            assert record["inventory_count"] == 5
            assert record["description"] == "Delicious cookies"
            assert record["notes"] == "Make extra for tasting"
            # And yield_type was added
            assert record["yield_type"] == "SERVING"
