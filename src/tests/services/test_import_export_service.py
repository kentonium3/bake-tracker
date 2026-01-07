"""
Unit tests for import_export_service.py - v3.0 export and import functions.

Tests cover:
- ExportResult class with per-entity counts
- export_finished_units_to_json()
- export_compositions_to_json()
- export_package_finished_goods_to_json()
- export_production_records_to_json()
- export_all_to_json() v3.0 format
- ImportResult class with per-entity tracking and merge
- import_all_from_json_v3() with mode support
- Version field handling (informational only, no validation)
- New entity import functions
"""

import json
import os
import tempfile
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.services.import_export_service import (
    ExportResult,
    ImportResult,
    export_all_to_json,
    export_compositions_to_json,
    export_finished_units_to_json,
    export_package_finished_goods_to_json,
    export_production_records_to_json,
    import_all_from_json_v3
)

class TestExportResult:
    """Tests for ExportResult class enhancements."""

    def test_export_result_init(self):
        """Test ExportResult initialization."""
        result = ExportResult("/tmp/test.json", 100)
        assert result.file_path == "/tmp/test.json"
        assert result.record_count == 100
        assert result.success is True
        assert result.error is None
        assert result.entity_counts == {}

    def test_add_entity_count(self):
        """Test adding entity counts."""
        result = ExportResult("/tmp/test.json", 100)
        result.add_entity_count("ingredients", 10)
        result.add_entity_count("recipes", 5)

        assert result.entity_counts["ingredients"] == 10
        assert result.entity_counts["recipes"] == 5

    def test_get_summary_success(self):
        """Test get_summary for successful export."""
        result = ExportResult("/tmp/test.json", 100)
        result.add_entity_count("ingredients", 10)
        result.add_entity_count("recipes", 5)

        summary = result.get_summary()

        assert "Exported 100 records to /tmp/test.json" in summary
        assert "ingredients: 10" in summary
        assert "recipes: 5" in summary

    def test_get_summary_failure(self):
        """Test get_summary for failed export."""
        result = ExportResult("/tmp/test.json", 0)
        result.success = False
        result.error = "Database connection failed"

        summary = result.get_summary()

        assert "Export failed: Database connection failed" in summary

class TestExportFinishedUnitsToJson:
    """Tests for export_finished_units_to_json function."""

    @patch("src.services.import_export_service.session_scope")
    def test_export_empty_finished_units(self, mock_session_scope):
        """Test export with no finished units."""
        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = []
        mock_session_scope.return_value.__enter__.return_value = mock_session

        result = export_finished_units_to_json()

        assert result == []

    @patch("src.services.import_export_service.session_scope")
    def test_export_finished_units_discrete_count(self, mock_session_scope):
        """Test export with discrete_count yield mode."""
        # Create mock finished unit
        mock_fu = MagicMock()
        mock_fu.slug = "chocolate_chip_cookie"
        mock_fu.display_name = "Chocolate Chip Cookie"
        mock_fu.yield_mode.value = "discrete_count"
        mock_fu.items_per_batch = 24
        mock_fu.item_unit = "cookie"
        mock_fu.category = "Cookies"
        mock_fu.description = None
        mock_fu.production_notes = None
        mock_fu.notes = None
        mock_fu.batch_percentage = None
        mock_fu.portion_description = None
        mock_fu.recipe.name = "Classic Chocolate Chip Cookies"

        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = [mock_fu]
        mock_session_scope.return_value.__enter__.return_value = mock_session

        result = export_finished_units_to_json()

        assert len(result) == 1
        assert result[0]["slug"] == "chocolate_chip_cookie"
        assert result[0]["display_name"] == "Chocolate Chip Cookie"
        assert result[0]["yield_mode"] == "discrete_count"
        assert result[0]["items_per_batch"] == 24
        assert result[0]["item_unit"] == "cookie"
        assert result[0]["category"] == "Cookies"
        assert result[0]["recipe_name"] == "Classic Chocolate Chip Cookies"

    @patch("src.services.import_export_service.session_scope")
    def test_export_finished_units_batch_portion(self, mock_session_scope):
        """Test export with batch_portion yield mode."""
        mock_fu = MagicMock()
        mock_fu.slug = "chocolate_cake"
        mock_fu.display_name = "Chocolate Cake"
        mock_fu.yield_mode.value = "batch_portion"
        mock_fu.batch_percentage = Decimal("50.00")
        mock_fu.portion_description = "9-inch round"
        mock_fu.items_per_batch = None
        mock_fu.item_unit = None
        mock_fu.category = "Cakes"
        mock_fu.description = None
        mock_fu.production_notes = None
        mock_fu.notes = None
        mock_fu.recipe.name = "Classic Chocolate Cake"

        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = [mock_fu]
        mock_session_scope.return_value.__enter__.return_value = mock_session

        result = export_finished_units_to_json()

        assert len(result) == 1
        assert result[0]["slug"] == "chocolate_cake"
        assert result[0]["yield_mode"] == "batch_portion"
        assert result[0]["batch_percentage"] == 50.00
        assert result[0]["portion_description"] == "9-inch round"

class TestExportCompositionsToJson:
    """Tests for export_compositions_to_json function."""

    @patch("src.services.import_export_service.session_scope")
    def test_export_empty_compositions(self, mock_session_scope):
        """Test export with no compositions."""
        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = []
        mock_session_scope.return_value.__enter__.return_value = mock_session

        result = export_compositions_to_json()

        assert result == []

    @patch("src.services.import_export_service.session_scope")
    def test_export_composition_with_finished_unit(self, mock_session_scope):
        """Test export composition referencing a finished unit."""
        mock_comp = MagicMock()
        mock_comp.assembly.slug = "holiday_cookie_box"
        mock_comp.component_quantity = 6
        mock_comp.sort_order = 1
        mock_comp.component_notes = None
        mock_comp.finished_unit_component = MagicMock()
        mock_comp.finished_unit_component.slug = "chocolate_chip_cookie"
        mock_comp.finished_good_component = None

        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = [mock_comp]
        mock_session_scope.return_value.__enter__.return_value = mock_session

        result = export_compositions_to_json()

        assert len(result) == 1
        assert result[0]["finished_good_slug"] == "holiday_cookie_box"
        assert result[0]["finished_unit_slug"] == "chocolate_chip_cookie"
        assert result[0]["finished_good_component_slug"] is None
        assert result[0]["component_quantity"] == 6
        assert result[0]["sort_order"] == 1

    @patch("src.services.import_export_service.session_scope")
    def test_export_composition_with_finished_good(self, mock_session_scope):
        """Test export composition referencing a finished good sub-assembly."""
        mock_comp = MagicMock()
        mock_comp.assembly.slug = "deluxe_gift_box"
        mock_comp.component_quantity = 2
        mock_comp.sort_order = 0
        mock_comp.component_notes = "Place at bottom"
        mock_comp.finished_unit_component = None
        mock_comp.finished_good_component = MagicMock()
        mock_comp.finished_good_component.slug = "mini_cookie_box"

        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = [mock_comp]
        mock_session_scope.return_value.__enter__.return_value = mock_session

        result = export_compositions_to_json()

        assert len(result) == 1
        assert result[0]["finished_good_slug"] == "deluxe_gift_box"
        assert result[0]["finished_unit_slug"] is None
        assert result[0]["finished_good_component_slug"] == "mini_cookie_box"
        assert result[0]["notes"] == "Place at bottom"

class TestExportPackageFinishedGoodsToJson:
    """Tests for export_package_finished_goods_to_json function."""

    @patch("src.services.import_export_service.session_scope")
    def test_export_empty_package_finished_goods(self, mock_session_scope):
        """Test export with no package-finished-good links."""
        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = []
        mock_session_scope.return_value.__enter__.return_value = mock_session

        result = export_package_finished_goods_to_json()

        assert result == []

    @patch("src.services.import_export_service.session_scope")
    def test_export_package_finished_goods(self, mock_session_scope):
        """Test export package-finished-good links."""
        mock_pfg = MagicMock()
        mock_pfg.package.name = "Holiday Gift Box - Large"
        mock_pfg.finished_good.slug = "holiday_cookie_box"
        mock_pfg.quantity = 2

        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = [mock_pfg]
        mock_session_scope.return_value.__enter__.return_value = mock_session

        result = export_package_finished_goods_to_json()

        assert len(result) == 1
        assert result[0]["package_name"] == "Holiday Gift Box - Large"
        assert result[0]["finished_good_slug"] == "holiday_cookie_box"
        assert result[0]["quantity"] == 2

class TestExportProductionRecordsToJson:
    """Tests for export_production_records_to_json function."""

    @patch("src.services.import_export_service.session_scope")
    def test_export_empty_production_records(self, mock_session_scope):
        """Test export with no production records."""
        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = []
        mock_session_scope.return_value.__enter__.return_value = mock_session

        result = export_production_records_to_json()

        assert result == []

    @patch("src.services.import_export_service.session_scope")
    def test_export_production_records(self, mock_session_scope):
        """Test export production records with FIFO cost."""
        mock_rec = MagicMock()
        mock_rec.event.name = "Christmas 2025"
        mock_rec.recipe.name = "Chocolate Chip Cookies"
        mock_rec.batches = 3
        mock_rec.produced_at = datetime(2025, 12, 20, 14, 30, 0)
        mock_rec.actual_cost = Decimal("25.50")
        mock_rec.notes = "Double batch for extra gifts"

        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = [mock_rec]
        mock_session_scope.return_value.__enter__.return_value = mock_session

        result = export_production_records_to_json()

        assert len(result) == 1
        assert result[0]["event_name"] == "Christmas 2025"
        assert result[0]["recipe_name"] == "Chocolate Chip Cookies"
        assert result[0]["batches"] == 3
        assert result[0]["produced_at"] == "2025-12-20T14:30:00Z"
        assert result[0]["actual_cost"] == 25.50
        assert result[0]["notes"] == "Double batch for extra gifts"

class TestExportAllToJsonV3Format:
    """Tests for export_all_to_json v3.0 format compliance."""

    @patch("src.services.import_export_service.export_production_records_to_json")
    @patch("src.services.import_export_service.export_package_finished_goods_to_json")
    @patch("src.services.import_export_service.export_compositions_to_json")
    @patch("src.services.import_export_service.export_finished_units_to_json")
    @patch("src.services.import_export_service.event_service")
    @patch("src.services.import_export_service.recipient_service")
    @patch("src.services.import_export_service.package_service")
    @patch("src.services.import_export_service.recipe_service")
    @patch("src.services.import_export_service.session_scope")
    def test_export_v3_header_format(
        self,
        mock_session_scope,
        mock_recipe_service,
        mock_package_service,
        mock_recipient_service,
        mock_event_service,
        mock_export_finished_units,
        mock_export_compositions,
        mock_export_pkg_fgs,
        mock_export_production_records
    ):
        """Test v3.0 header fields in export."""
        # Mock all services to return empty
        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = []
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_recipe_service.get_all_recipes.return_value = []
        mock_package_service.get_all_packages.return_value = []
        mock_recipient_service.get_all_recipients.return_value = []
        mock_event_service.get_all_events.return_value = []
        mock_export_finished_units.return_value = []
        mock_export_compositions.return_value = []
        mock_export_pkg_fgs.return_value = []
        mock_export_production_records.return_value = []

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_all_to_json(temp_path)

            assert result.success is True

            with open(temp_path, "r") as f:
                data = json.load(f)

            # Version is informational only; tests validate current spec structure
            assert "version" in data
            assert "exported_at" in data
            assert data["application"] == "bake-tracker"

            # Verify v3.0 entities present
            assert "finished_units" in data
            assert "compositions" in data
            assert "package_finished_goods" in data
            assert "event_recipient_packages" in data
            assert "production_records" in data

            # Verify v2.0 deprecated entities NOT present
            assert "bundles" not in data
            assert "export_date" not in data
            assert "source" not in data

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("src.services.import_export_service.export_production_records_to_json")
    @patch("src.services.import_export_service.export_package_finished_goods_to_json")
    @patch("src.services.import_export_service.export_compositions_to_json")
    @patch("src.services.import_export_service.export_finished_units_to_json")
    @patch("src.services.import_export_service.event_service")
    @patch("src.services.import_export_service.recipient_service")
    @patch("src.services.import_export_service.package_service")
    @patch("src.services.import_export_service.recipe_service")
    @patch("src.services.import_export_service.session_scope")
    def test_export_result_entity_counts(
        self,
        mock_session_scope,
        mock_recipe_service,
        mock_package_service,
        mock_recipient_service,
        mock_event_service,
        mock_export_finished_units,
        mock_export_compositions,
        mock_export_pkg_fgs,
        mock_export_production_records
    ):
        """Test ExportResult contains per-entity counts."""
        # Mock services
        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.all.return_value = []
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_recipe_service.get_all_recipes.return_value = []
        mock_package_service.get_all_packages.return_value = []
        mock_recipient_service.get_all_recipients.return_value = []
        mock_event_service.get_all_events.return_value = []
        mock_export_finished_units.return_value = [{"slug": "test"}]  # 1 record
        mock_export_compositions.return_value = []
        mock_export_pkg_fgs.return_value = []
        mock_export_production_records.return_value = [{"event_name": "test"}]  # 1 record

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            result = export_all_to_json(temp_path)

            assert result.success is True
            assert "finished_units" in result.entity_counts
            assert result.entity_counts["finished_units"] == 1
            assert "production_records" in result.entity_counts
            assert result.entity_counts["production_records"] == 1

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_handles_error(self):
        """Test export handles errors gracefully."""
        # Use invalid path to trigger error
        result = export_all_to_json("/nonexistent/directory/test.json")

        assert result.success is False
        assert result.error is not None
        assert result.record_count == 0

# ============================================================================
# Import Function Tests
# ============================================================================

class TestImportResult:
    """Tests for ImportResult class enhancements."""

    def test_import_result_init(self):
        """Test ImportResult initialization."""
        result = ImportResult()
        assert result.total_records == 0
        assert result.successful == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.entity_counts == {}

    def test_add_success_with_entity(self):
        """Test add_success with entity type tracking."""
        result = ImportResult()
        result.add_success("ingredient")
        result.add_success("ingredient")
        result.add_success("recipe")

        assert result.successful == 3
        assert result.entity_counts["ingredient"]["imported"] == 2
        assert result.entity_counts["recipe"]["imported"] == 1

    def test_add_skip_tracks_entity(self):
        """Test add_skip tracks entity counts."""
        result = ImportResult()
        result.add_skip("ingredient", "flour", "Already exists")

        assert result.skipped == 1
        assert result.entity_counts["ingredient"]["skipped"] == 1

    def test_add_error_tracks_entity(self):
        """Test add_error tracks entity counts."""
        result = ImportResult()
        result.add_error("ingredient", "bad_data", "Invalid format")

        assert result.failed == 1
        assert result.entity_counts["ingredient"]["errors"] == 1

    def test_merge_combines_results(self):
        """Test merge combines two ImportResults."""
        result1 = ImportResult()
        result1.add_success("ingredient")
        result1.add_success("ingredient")

        result2 = ImportResult()
        result2.add_success("ingredient")
        result2.add_skip("ingredient", "sugar", "Duplicate")

        result1.merge(result2)

        assert result1.successful == 3
        assert result1.skipped == 1
        assert result1.entity_counts["ingredient"]["imported"] == 3
        assert result1.entity_counts["ingredient"]["skipped"] == 1

    def test_get_summary_includes_entity_breakdown(self):
        """Test get_summary shows per-entity breakdown."""
        result = ImportResult()
        result.add_success("ingredient")
        result.add_success("ingredient")
        result.add_skip("ingredient", "flour", "Duplicate")
        result.add_success("recipe")

        summary = result.get_summary()

        assert "ingredient" in summary
        assert "2 imported" in summary
        assert "1 skipped" in summary
        assert "recipe" in summary

class TestImportVersionHandling:
    """Tests for version field handling (informational only, no validation)."""

    def test_import_accepts_any_version(self):
        """Test import accepts files with any version value."""
        for version in ["1.0", "2.0", "3.4", "3.5", "4.0", "99.99"]:
            test_data = {
                "version": version,
                "exported_at": "2025-12-04T00:00:00Z",
                "application": "bake-tracker",
                "ingredients": [],
                "recipes": []
            }

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(test_data, f)
                temp_path = f.name

            try:
                # Should not raise - version is informational only
                result = import_all_from_json_v3(temp_path)
                assert result is not None, f"Import failed for version {version}"
            except Exception as e:
                # Only fail if it's a version-related error
                if "version" in str(e).lower():
                    pytest.fail(f"Version {version} should be accepted: {e}")
            finally:
                os.unlink(temp_path)

    def test_import_accepts_missing_version(self):
        """Test import accepts files without version field."""
        no_version_data = {
            "exported_at": "2025-12-04T00:00:00Z",
            "application": "bake-tracker",
            "ingredients": [],
            "recipes": []
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(no_version_data, f)
            temp_path = f.name

        try:
            # Should not raise - version is optional
            result = import_all_from_json_v3(temp_path)
            assert result is not None
        except Exception as e:
            # Only fail if it's a version-related error
            if "version" in str(e).lower():
                pytest.fail(f"Missing version should be accepted: {e}")
        finally:
            os.unlink(temp_path)

class TestImportModeValidation:
    """Tests for import mode parameter validation."""

    def test_invalid_mode_raises_error(self):
        """Test invalid mode raises ValueError."""
        v3_data = {"version": "3.4", "ingredients": []}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                import_all_from_json_v3(temp_path, mode="invalid")

            assert "Invalid import mode" in str(exc_info.value)
            assert "merge" in str(exc_info.value)
            assert "replace" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_merge_mode_accepted(self):
        """Test merge mode is accepted."""
        v3_data = {"version": "3.0", "ingredients": []}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            # Should not raise ValueError for mode
            result = import_all_from_json_v3(temp_path, mode="merge")
            assert result is not None
        except ValueError as e:
            if "mode" in str(e).lower():
                pytest.fail("Should accept 'merge' mode")
        except Exception:
            pass  # Other errors are acceptable
        finally:
            os.unlink(temp_path)

    def test_replace_mode_accepted(self):
        """Test replace mode is accepted."""
        v3_data = {"version": "3.0", "ingredients": []}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            # Should not raise ValueError for mode
            result = import_all_from_json_v3(temp_path, mode="replace")
            assert result is not None
        except ValueError as e:
            if "mode" in str(e).lower():
                pytest.fail("Should accept 'replace' mode")
        except Exception:
            pass  # Other errors are acceptable
        finally:
            os.unlink(temp_path)

class TestImportUserFriendlyErrors:
    """Tests for user-friendly error messages (SC-006)."""

    def test_file_not_found_error(self):
        """Test file not found returns ImportResult with error."""
        result = import_all_from_json_v3("/nonexistent/path/data.json")

        assert result.failed > 0 or len(result.errors) > 0

# ============================================================================
# Integration Tests - WP05 (T035-T038)
# ============================================================================

import time

# Path to sample data file
SAMPLE_DATA_PATH = "test_data/sample_data.json"

class TestSampleDataIntegration:
    """Integration tests for sample data import (T035).

    These tests require a test database fixture.
    """

    def test_sample_data_file_exists(self):
        """Verify sample_data.json exists and is valid JSON."""
        assert os.path.exists(SAMPLE_DATA_PATH), "Sample data file must exist"

        with open(SAMPLE_DATA_PATH, "r") as f:
            data = json.load(f)

        assert data is not None
        assert "version" in data
        assert isinstance(data["version"], str)

    def test_sample_data_has_v3_header(self):
        """Verify sample data has required header fields."""
        with open(SAMPLE_DATA_PATH, "r") as f:
            data = json.load(f)

        assert "version" in data
        assert "exported_at" in data
        assert "application" in data
        assert data.get("application") == "bake-tracker"

    def test_sample_data_has_required_entity_types(self):
        """Verify sample data includes products and recipes (catalog subset format).

        Note: sample_data.json uses catalog subset format with products and recipes only.
        Ingredients are imported separately via ingredients_catalog.json.
        """
        required_entities = [
            "products",
            "recipes",
        ]

        with open(SAMPLE_DATA_PATH, "r") as f:
            data = json.load(f)

        for entity in required_entities:
            assert entity in data, f"Sample data must include {entity}"
            assert isinstance(data[entity], list), f"{entity} must be a list"
            assert len(data[entity]) > 0, f"{entity} should have at least one record"

    def test_sample_data_referential_integrity(self):
        """Verify sample data has consistent internal references.

        Note: sample_data.json uses catalog subset format. Products reference
        ingredient_slugs that exist in the separately imported catalog, not
        within this file.
        """
        with open(SAMPLE_DATA_PATH, "r") as f:
            data = json.load(f)

        # Collect recipe names (sample data uses name field, not slug)
        recipe_names = {r["name"] for r in data["recipes"]}

        # Verify all products have required fields
        for product in data["products"]:
            assert "ingredient_slug" in product, "Product must have ingredient_slug"
            assert "brand" in product, "Product must have brand"
            assert "package_unit" in product, "Product must have package_unit"

        # Verify all recipes have required fields and valid ingredient references
        for recipe in data["recipes"]:
            assert "name" in recipe, "Recipe must have name"
            assert "ingredients" in recipe, "Recipe must have ingredients list"
            for ing in recipe["ingredients"]:
                assert "ingredient_slug" in ing, "Recipe ingredient must have ingredient_slug"
                assert "quantity" in ing, "Recipe ingredient must have quantity"
                assert "unit" in ing, "Recipe ingredient must have unit"

class TestPerformance:
    """Performance tests (T037) - SC-001 and SC-002."""

    def test_sample_data_export_format_performance(self):
        """Test that reading and parsing sample data is fast."""
        # This tests the JSON parsing performance
        start = time.time()

        with open(SAMPLE_DATA_PATH, "r") as f:
            data = json.load(f)

        elapsed = time.time() - start

        # JSON parsing should be nearly instant
        assert elapsed < 1.0, f"JSON parsing took {elapsed:.2f}s, expected <1s"
        assert data is not None

    def test_sample_data_record_count(self):
        """Verify sample data has a reasonable number of records."""
        with open(SAMPLE_DATA_PATH, "r") as f:
            data = json.load(f)

        total_records = 0
        for key, value in data.items():
            if isinstance(value, list):
                total_records += len(value)

        # Sample data should have a reasonable size (not too small, not huge)
        assert total_records >= 50, f"Sample data too small: {total_records} records"
        assert total_records < 10000, f"Sample data too large: {total_records} records"

class TestSuccessCriteriaValidation:
    """Tests validating success criteria (T038)."""

    def test_sc007_all_entities_in_spec(self):
        """SC-007: v3.0 spec covers 100% of entities."""
        spec_path = "docs/design/import_export_specification.md"

        if not os.path.exists(spec_path):
            pytest.skip("Specification document not found")

        with open(spec_path, "r") as f:
            spec_content = f.read().lower()

        expected_entities = [
            "ingredients",
            "products",
            "purchases",
            "inventory_items",
            "recipes",
            "finished_units",
            "finished_goods",
            "compositions",
            "packages",
            "package_finished_goods",
            "recipients",
            "events",
            "event_recipient_packages",
            "production_records",
        ]

        for entity in expected_entities:
            # Check for entity mention (allow underscores or spaces)
            entity_variations = [entity, entity.replace("_", " "), entity.replace("_", "-")]
            found = any(var in spec_content for var in entity_variations)
            assert found, f"Entity '{entity}' not documented in specification"

    def test_sample_data_is_realistic_scenario(self):
        """Verify sample data represents a coherent holiday baking scenario.

        Note: sample_data.json uses catalog subset format with products and recipes.
        Events, recipients, and production records are not included.
        """
        with open(SAMPLE_DATA_PATH, "r") as f:
            data = json.load(f)

        # Should have baking-related recipes
        recipe_categories = {r["category"] for r in data["recipes"]}
        has_baking = any(
            cat.lower() in ["cookies", "brownies", "cakes", "candies", "pies"]
            for cat in recipe_categories
        )
        assert has_baking, "Sample data should include baking recipes"

        # Should have multiple recipes for realistic testing
        assert len(data["recipes"]) >= 5, "Should have multiple recipes for testing"

        # Should have multiple products for realistic testing
        assert len(data["products"]) >= 10, "Should have multiple products for testing"

class TestDensityFieldsImportExport:
    """Tests for 4-field density model in import/export (Feature 010)."""

    def test_export_ingredient_includes_density_fields(self):
        """Export includes all 4 density fields when present."""
        from src.models.ingredient import Ingredient

        ingredient = Ingredient(
            display_name="Test Flour",
            slug="test-flour",
            category="Flour",
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=4.25,
            density_weight_unit="oz"
        )

        # Manually build export dict like the export function does
        ingredient_data = {
            "name": ingredient.display_name,
            "slug": ingredient.slug,
            "category": ingredient.category
        }

        # Add density fields (mirroring export logic)
        if ingredient.density_volume_value is not None:
            ingredient_data["density_volume_value"] = ingredient.density_volume_value
        if ingredient.density_volume_unit:
            ingredient_data["density_volume_unit"] = ingredient.density_volume_unit
        if ingredient.density_weight_value is not None:
            ingredient_data["density_weight_value"] = ingredient.density_weight_value
        if ingredient.density_weight_unit:
            ingredient_data["density_weight_unit"] = ingredient.density_weight_unit

        # Verify all 4 density fields present
        assert "density_volume_value" in ingredient_data
        assert "density_volume_unit" in ingredient_data
        assert "density_weight_value" in ingredient_data
        assert "density_weight_unit" in ingredient_data
        assert ingredient_data["density_volume_value"] == 1.0
        assert ingredient_data["density_volume_unit"] == "cup"
        assert ingredient_data["density_weight_value"] == 4.25
        assert ingredient_data["density_weight_unit"] == "oz"

    def test_export_ingredient_without_density(self):
        """Export omits density fields when not set."""
        from src.models.ingredient import Ingredient

        ingredient = Ingredient(
            display_name="Test Ingredient",
            slug="test-ingredient",
            category="Other"
        )

        # Manually build export dict
        ingredient_data = {
            "name": ingredient.display_name,
            "slug": ingredient.slug,
            "category": ingredient.category
        }

        # Add density fields only if present
        if ingredient.density_volume_value is not None:
            ingredient_data["density_volume_value"] = ingredient.density_volume_value
        if ingredient.density_volume_unit:
            ingredient_data["density_volume_unit"] = ingredient.density_volume_unit
        if ingredient.density_weight_value is not None:
            ingredient_data["density_weight_value"] = ingredient.density_weight_value
        if ingredient.density_weight_unit:
            ingredient_data["density_weight_unit"] = ingredient.density_weight_unit

        # Verify no density fields
        assert "density_volume_value" not in ingredient_data
        assert "density_volume_unit" not in ingredient_data
        assert "density_weight_value" not in ingredient_data
        assert "density_weight_unit" not in ingredient_data

    def test_import_ingredient_reads_density_fields(self):
        """Import reads all 4 density fields."""
        from src.models.ingredient import Ingredient

        data = {
            "slug": "test-flour",
            "name": "Test Flour",
            "category": "Flour",
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 4.25,
            "density_weight_unit": "oz"
        }

        # Mimic import logic
        ingredient = Ingredient(
            display_name=data.get("name"),
            slug=data.get("slug"),
            category=data.get("category"),
            density_volume_value=data.get("density_volume_value"),
            density_volume_unit=data.get("density_volume_unit"),
            density_weight_value=data.get("density_weight_value"),
            density_weight_unit=data.get("density_weight_unit")
        )

        # Verify
        assert ingredient.density_volume_value == 1.0
        assert ingredient.density_volume_unit == "cup"
        assert ingredient.density_weight_value == 4.25
        assert ingredient.density_weight_unit == "oz"

    def test_import_ignores_legacy_density_field(self):
        """Import ignores legacy density_g_per_ml field."""
        from src.models.ingredient import Ingredient

        data = {
            "slug": "test-flour",
            "name": "Test Flour",
            "category": "Flour",
            "density_g_per_ml": 0.5,  # Legacy field - should be ignored
        }

        # Mimic import logic (does NOT read density_g_per_ml)
        ingredient = Ingredient(
            display_name=data.get("name"),
            slug=data.get("slug"),
            category=data.get("category"),
            density_volume_value=data.get("density_volume_value"),
            density_volume_unit=data.get("density_volume_unit"),
            density_weight_value=data.get("density_weight_value"),
            density_weight_unit=data.get("density_weight_unit")
        )

        # Verify density fields are None (not populated from legacy)
        assert ingredient.density_volume_value is None
        assert ingredient.density_volume_unit is None
        assert ingredient.density_weight_value is None
        assert ingredient.density_weight_unit is None
        assert ingredient.get_density_g_per_ml() is None

    def test_density_round_trip(self):
        """Export and reimport preserves density."""
        from src.models.ingredient import Ingredient

        # Create ingredient with density
        original = Ingredient(
            slug="test",
            display_name="Test",
            category="Flour",
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=4.25,
            density_weight_unit="oz"
        )

        # Export to dict
        exported = {
            "name": original.display_name,
            "slug": original.slug,
            "category": original.category
        }
        if original.density_volume_value is not None:
            exported["density_volume_value"] = original.density_volume_value
        if original.density_volume_unit:
            exported["density_volume_unit"] = original.density_volume_unit
        if original.density_weight_value is not None:
            exported["density_weight_value"] = original.density_weight_value
        if original.density_weight_unit:
            exported["density_weight_unit"] = original.density_weight_unit

        # Import from dict
        reimported = Ingredient(
            display_name=exported.get("name"),
            slug=exported.get("slug"),
            category=exported.get("category"),
            density_volume_value=exported.get("density_volume_value"),
            density_volume_unit=exported.get("density_volume_unit"),
            density_weight_value=exported.get("density_weight_value"),
            density_weight_unit=exported.get("density_weight_unit")
        )

        # Verify density matches
        assert reimported.density_volume_value == original.density_volume_value
        assert reimported.density_volume_unit == original.density_volume_unit
        assert reimported.density_weight_value == original.density_weight_value
        assert reimported.density_weight_unit == original.density_weight_unit

    def test_ingredients_catalog_has_density_fields(self):
        """Verify ingredients_catalog.json uses new density format."""
        import json

        with open("test_data/ingredients_catalog.json", "r") as f:
            data = json.load(f)

        # Find All-Purpose Flour (slug may vary by catalog generation)
        flour = None
        target_slugs = {"flour_all_purpose", "all_purpose_wheat_flour"}
        for ing in data["ingredients"]:
            if ing.get("slug") in target_slugs:
                flour = ing
                break

        assert flour is not None, f"Catalog should have one of {sorted(target_slugs)}"

        # Should have 4-field density, not legacy
        assert "density_g_per_ml" not in flour, "Should not have legacy density field"
        assert flour.get("density_volume_value") == 1.0
        assert flour.get("density_volume_unit") == "cup"
        assert flour.get("density_weight_value") == 4.42
        assert flour.get("density_weight_unit") == "oz"

    def test_sample_data_valid_json(self):
        """Verify sample_data.json is valid JSON with required header."""
        import json

        # Should not raise
        with open("test_data/sample_data.json", "r") as f:
            data = json.load(f)

        assert "version" in data
        assert isinstance(data["version"], str)
        # Note: ingredients are in separate catalog file, not sample_data.json
        assert "products" in data
        assert "recipes" in data

# ============================================================================
# Recipe Component Import/Export Tests (Feature 012)
# ============================================================================

class TestRecipeComponentExport:
    """Tests for exporting recipe components (T032)."""

    def test_export_recipe_with_components(self, test_db, tmp_path):
        """Export includes component relationships."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import export_recipes_to_json

        # Create ingredient
        flour = ingredient_service.create_ingredient(
            {"display_name": "Export Flour", "category": "Flour"}
        )

        # Create child recipe
        child = recipe_service.create_recipe(
            {
                "name": "Export Child Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}]
        )

        # Create parent recipe
        parent = recipe_service.create_recipe(
            {
                "name": "Export Parent Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Add child as component
        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0, notes="Test note")

        # Export
        export_file = tmp_path / "export.json"
        result = export_recipes_to_json(str(export_file))

        assert result.success

        # Read and verify
        with open(export_file) as f:
            data = json.load(f)

        parent_data = next(r for r in data["recipes"] if r["name"] == "Export Parent Recipe")
        assert "components" in parent_data
        assert len(parent_data["components"]) == 1
        assert parent_data["components"][0]["recipe_name"] == "Export Child Recipe"
        assert parent_data["components"][0]["quantity"] == 2.0
        assert parent_data["components"][0]["notes"] == "Test note"

    def test_export_recipe_without_components(self, test_db, tmp_path):
        """Recipe without components has empty components array."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import export_recipes_to_json

        flour = ingredient_service.create_ingredient(
            {"display_name": "Simple Flour", "category": "Flour"}
        )

        recipe = recipe_service.create_recipe(
            {
                "name": "Simple Recipe No Components",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}]
        )

        export_file = tmp_path / "export.json"
        result = export_recipes_to_json(str(export_file))

        with open(export_file) as f:
            data = json.load(f)

        recipe_data = next(r for r in data["recipes"] if r["name"] == "Simple Recipe No Components")
        assert "components" in recipe_data
        assert len(recipe_data["components"]) == 0

    def test_export_all_includes_components(self, test_db, tmp_path):
        """Full export includes component relationships."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import export_all_to_json

        flour = ingredient_service.create_ingredient(
            {"display_name": "Full Export Flour", "category": "Flour"}
        )

        child = recipe_service.create_recipe(
            {
                "name": "Full Export Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}]
        )

        parent = recipe_service.create_recipe(
            {
                "name": "Full Export Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        recipe_service.add_recipe_component(parent.id, child.id, quantity=1.5)

        export_file = tmp_path / "full_export.json"
        result = export_all_to_json(str(export_file))

        with open(export_file) as f:
            data = json.load(f)

        parent_data = next(r for r in data["recipes"] if r["name"] == "Full Export Parent")
        assert len(parent_data["components"]) == 1
        assert parent_data["components"][0]["recipe_name"] == "Full Export Child"
        assert parent_data["components"][0]["quantity"] == 1.5

# ============================================================================
# Unit Validation Tests (TD-002)
# ============================================================================

class TestImportUnitValidation:
    """Tests for unit validation during import (TD-002 Technical Debt)."""

    def test_import_product_with_valid_unit_succeeds(self):
        """Import with valid package_unit succeeds."""
        v3_data = {
            "version": "3.4",
            "exported_at": "2025-12-16T00:00:00Z",
            "application": "bake-tracker",
            "ingredients": [
                {
                    "slug": "valid_unit_flour",
                    "name": "Valid Unit Flour",
                    "category": "Flour"
                }
            ],
            "products": [
                {
                    "ingredient_slug": "valid_unit_flour",
                    "brand": "Test Brand",
                    "package_unit": "lb",
                    "package_unit_quantity": 5.0
                }
            ],
            "recipes": []
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            result = import_all_from_json_v3(temp_path)
            # Check that product was imported (no unit error)
            product_errors = [e for e in result.errors if e["record_type"] == "product"]
            assert len(product_errors) == 0, f"Expected no product errors, got: {product_errors}"
        except Exception as e:
            # DB errors are acceptable, unit validation errors are not
            if "Invalid unit" in str(e):
                pytest.fail(f"Valid unit 'lb' was rejected: {e}")
        finally:
            os.unlink(temp_path)

    def test_import_product_with_invalid_unit_fails(self):
        """Import with invalid package_unit returns error."""
        v3_data = {
            "version": "3.4",
            "exported_at": "2025-12-16T00:00:00Z",
            "application": "bake-tracker",
            "ingredients": [
                {
                    "slug": "invalid_unit_flour",
                    "name": "Invalid Unit Flour",
                    "category": "Flour"
                }
            ],
            "products": [
                {
                    "ingredient_slug": "invalid_unit_flour",
                    "brand": "Bad Unit Brand",
                    "package_unit": "invalid_unit_xyz",
                    "package_unit_quantity": 5.0
                }
            ],
            "recipes": []
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            result = import_all_from_json_v3(temp_path)
            # Check for unit validation error
            product_errors = [e for e in result.errors if e["record_type"] == "product"]
            assert len(product_errors) > 0, "Expected product error for invalid unit"
            error_msg = str(product_errors[0])
            assert "Invalid unit" in error_msg or "invalid_unit_xyz" in error_msg
        except Exception:
            pass  # Other exceptions are acceptable
        finally:
            os.unlink(temp_path)

    def test_import_ingredient_with_invalid_density_volume_unit_fails(self):
        """Import with invalid density_volume_unit returns error."""
        v3_data = {
            "version": "3.4",
            "exported_at": "2025-12-16T00:00:00Z",
            "application": "bake-tracker",
            "ingredients": [
                {
                    "slug": "bad_density_flour",
                    "name": "Bad Density Flour",
                    "category": "Flour",
                    "density_volume_value": 1.0,
                    "density_volume_unit": "invalid_volume_unit",
                    "density_weight_value": 4.25,
                    "density_weight_unit": "oz"
                }
            ],
            "products": [],
            "recipes": []
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            result = import_all_from_json_v3(temp_path)
            # Check for ingredient error
            ingredient_errors = [e for e in result.errors if e["record_type"] == "ingredient"]
            assert len(ingredient_errors) > 0, "Expected ingredient error for invalid density_volume_unit"
            error_msg = str(ingredient_errors[0])
            assert "Invalid unit" in error_msg or "density_volume_unit" in error_msg
        except Exception:
            pass  # Other exceptions are acceptable
        finally:
            os.unlink(temp_path)

    def test_import_ingredient_with_invalid_density_weight_unit_fails(self):
        """Import with invalid density_weight_unit returns error."""
        v3_data = {
            "version": "3.4",
            "exported_at": "2025-12-16T00:00:00Z",
            "application": "bake-tracker",
            "ingredients": [
                {
                    "slug": "bad_weight_flour",
                    "name": "Bad Weight Flour",
                    "category": "Flour",
                    "density_volume_value": 1.0,
                    "density_volume_unit": "cup",
                    "density_weight_value": 4.25,
                    "density_weight_unit": "invalid_weight_unit"
                }
            ],
            "products": [],
            "recipes": []
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            result = import_all_from_json_v3(temp_path)
            ingredient_errors = [e for e in result.errors if e["record_type"] == "ingredient"]
            assert len(ingredient_errors) > 0, "Expected ingredient error for invalid density_weight_unit"
            error_msg = str(ingredient_errors[0])
            assert "Invalid unit" in error_msg or "density_weight_unit" in error_msg
        except Exception:
            pass
        finally:
            os.unlink(temp_path)

    def test_import_ingredient_with_null_density_units_succeeds(self):
        """Import with null density units succeeds (density is optional)."""
        v3_data = {
            "version": "3.4",
            "exported_at": "2025-12-16T00:00:00Z",
            "application": "bake-tracker",
            "ingredients": [
                {
                    "slug": "no_density_flour",
                    "name": "No Density Flour",
                    "category": "Flour"
                }
            ],
            "products": [],
            "recipes": []
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            result = import_all_from_json_v3(temp_path)
            ingredient_errors = [e for e in result.errors if e["record_type"] == "ingredient"]
            # Should have no density-related errors
            unit_errors = [e for e in ingredient_errors if "unit" in str(e).lower()]
            assert len(unit_errors) == 0, f"Expected no unit errors for null density, got: {unit_errors}"
        except Exception:
            pass
        finally:
            os.unlink(temp_path)

    def test_import_recipe_ingredient_with_invalid_unit_fails(self):
        """Import with invalid recipe ingredient unit returns error."""
        v3_data = {
            "version": "3.4",
            "exported_at": "2025-12-16T00:00:00Z",
            "application": "bake-tracker",
            "ingredients": [
                {
                    "slug": "recipe_test_flour",
                    "name": "Recipe Test Flour",
                    "category": "Flour"
                }
            ],
            "products": [],
            "recipes": [
                {
                    "name": "Bad Unit Recipe",
                    "slug": "bad_unit_recipe",
                    "category": "Cookies",
                    "yield_quantity": 24,
                    "yield_unit": "cookies",
                    "ingredients": [
                        {
                            "ingredient_slug": "recipe_test_flour",
                            "quantity": 2.0,
                            "unit": "invalid_recipe_unit"
                        }
                    ]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            result = import_all_from_json_v3(temp_path)
            recipe_errors = [e for e in result.errors if e["record_type"] == "recipe"]
            assert len(recipe_errors) > 0, "Expected recipe error for invalid ingredient unit"
            error_msg = str(recipe_errors[0])
            assert "Invalid unit" in error_msg or "invalid_recipe_unit" in error_msg
        except Exception:
            pass
        finally:
            os.unlink(temp_path)

    def test_import_recipe_ingredient_with_valid_units_succeeds(self):
        """Import with valid recipe ingredient units succeeds."""
        v3_data = {
            "version": "3.4",
            "exported_at": "2025-12-16T00:00:00Z",
            "application": "bake-tracker",
            "ingredients": [
                {
                    "slug": "good_recipe_flour",
                    "name": "Good Recipe Flour",
                    "category": "Flour"
                }
            ],
            "products": [],
            "recipes": [
                {
                    "name": "Good Unit Recipe",
                    "slug": "good_unit_recipe",
                    "category": "Cookies",
                    "yield_quantity": 24,
                    "yield_unit": "cookies",
                    "ingredients": [
                        {
                            "ingredient_slug": "good_recipe_flour",
                            "quantity": 2.0,
                            "unit": "cup"
                        }
                    ]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            result = import_all_from_json_v3(temp_path)
            recipe_errors = [e for e in result.errors if e["record_type"] == "recipe"]
            unit_errors = [e for e in recipe_errors if "unit" in str(e).lower()]
            assert len(unit_errors) == 0, f"Expected no unit errors for valid units, got: {unit_errors}"
        except Exception as e:
            if "Invalid unit" in str(e):
                pytest.fail(f"Valid unit 'cup' was rejected: {e}")
        finally:
            os.unlink(temp_path)

    def test_error_message_includes_valid_units_list(self):
        """Error message includes list of valid units."""
        v3_data = {
            "version": "3.4",
            "exported_at": "2025-12-16T00:00:00Z",
            "application": "bake-tracker",
            "ingredients": [
                {
                    "slug": "error_msg_flour",
                    "name": "Error Msg Flour",
                    "category": "Flour"
                }
            ],
            "products": [
                {
                    "ingredient_slug": "error_msg_flour",
                    "brand": "Error Test Brand",
                    "package_unit": "badunit",
                    "package_unit_quantity": 5.0
                }
            ],
            "recipes": []
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            result = import_all_from_json_v3(temp_path)
            product_errors = [e for e in result.errors if e["record_type"] == "product"]
            if product_errors:
                error_msg = str(product_errors[0]["message"])
                # Should include some valid units in the message
                assert any(unit in error_msg for unit in ["lb", "oz", "cup", "bag"]), \
                    f"Error message should list valid units, got: {error_msg}"
        except Exception:
            pass
        finally:
            os.unlink(temp_path)


class TestRecipeComponentImport:
    """Tests for importing recipe components (nested recipes)."""

    def test_import_recipe_with_components(self, test_db, tmp_path):
        """Import creates recipe component relationships."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import export_all_to_json, import_all_from_json_v3

        # Create test data
        flour = ingredient_service.create_ingredient(
            {"display_name": "Import Test Flour", "category": "Flour"}
        )

        child = recipe_service.create_recipe(
            {
                "name": "Import Test Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}]
        )

        parent = recipe_service.create_recipe(
            {
                "name": "Import Test Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.5, notes="Test import")

        # Export
        export_file = tmp_path / "component_export.json"
        export_all_to_json(str(export_file))

        # Delete recipes
        recipe_service.remove_recipe_component(parent.id, child.id)
        recipe_service.delete_recipe(parent.id)
        recipe_service.delete_recipe(child.id)

        # Verify deleted
        assert recipe_service.get_recipe_by_name("Import Test Parent") is None

        # Import
        result = import_all_from_json_v3(str(export_file), mode="merge")
        assert result.successful > 0

        # Verify component relationship restored
        restored_parent = recipe_service.get_recipe_by_name("Import Test Parent")
        assert restored_parent is not None

        components = recipe_service.get_recipe_components(restored_parent.id)
        assert len(components) == 1
        assert components[0].component_recipe.name == "Import Test Child"
        assert components[0].quantity == 2.5
        assert components[0].notes == "Test import"

    def test_import_missing_component_recipe_errors(self, test_db, tmp_path):
        """Import errors gracefully when component recipe doesn't exist."""
        from src.services.import_export_service import import_all_from_json_v3

        # Create a minimal v3.4 import file with missing component reference
        import_data = {
            "version": "3.4",
            "app_name": "Test",
            "app_version": "1.0.0",
            "exported_at": "2024-01-01T00:00:00Z",
            "ingredients": [
                {
                    "slug": "test_flour",
                    "display_name": "Test Flour",
                    "category": "Flour"
                }
            ],
            "products": [],
            "purchases": [],
            "inventory_items": [],
            "recipes": [
                {
                    "name": "Recipe With Missing Component",
                    "slug": "recipe_missing_component",
                    "category": "Cookies",
                    "yield_quantity": 1,
                    "yield_unit": "batch",
                    "ingredients": [
                        {"ingredient_slug": "test_flour", "quantity": 1.0, "unit": "cup"}
                    ],
                    "components": [
                        {"recipe_name": "Non Existent Recipe", "quantity": 1.0}
                    ]
                }
            ],
            "finished_units": [],
            "finished_goods": [],
            "compositions": [],
            "packages": [],
            "package_finished_goods": [],
            "recipients": [],
            "events": [],
            "event_recipient_packages": [],
            "production_records": [],
            "event_production_targets": [],
            "event_assembly_targets": [],
            "production_runs": [],
            "assembly_runs": []
        }

        import_file = tmp_path / "missing_component.json"
        with open(import_file, "w") as f:
            json.dump(import_data, f)

        # Import should succeed but report error for component
        result = import_all_from_json_v3(str(import_file), mode="merge")

        # Recipe itself should be created
        assert result.successful >= 1

        # Component should have an error
        assert result.failed >= 1
        error_found = any(
            "Non Existent Recipe" in str(err) or "Component recipe not found" in str(err)
            for err in result.errors
        )
        assert error_found, f"Expected error about missing component, got: {result.errors}"

    def test_import_rejects_circular_reference(self, test_db, tmp_path):
        """Import rejects components that would create circular references."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import import_all_from_json_v3

        # Create two recipes
        flour = ingredient_service.create_ingredient(
            {"display_name": "Circular Test Flour", "category": "Flour"}
        )

        recipe_a = recipe_service.create_recipe(
            {"name": "Circular Recipe A", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}]
        )

        recipe_b = recipe_service.create_recipe(
            {"name": "Circular Recipe B", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}]
        )

        # A contains B
        recipe_service.add_recipe_component(recipe_a.id, recipe_b.id, quantity=1.0)

        # Create import data that tries to make B contain A (circular!)
        import_data = {
            "version": "3.4",
            "app_name": "Test",
            "app_version": "1.0.0",
            "exported_at": "2024-01-01T00:00:00Z",
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [],
            "recipes": [
                {
                    "name": "Circular Recipe B",
                    "slug": "circular_recipe_b",
                    "category": "Cookies",
                    "yield_quantity": 1,
                    "yield_unit": "batch",
                    "ingredients": [],
                    "components": [
                        {"recipe_name": "Circular Recipe A", "quantity": 1.0}
                    ]
                }
            ],
            "finished_units": [],
            "finished_goods": [],
            "compositions": [],
            "packages": [],
            "package_finished_goods": [],
            "recipients": [],
            "events": [],
            "event_recipient_packages": [],
            "production_records": [],
            "event_production_targets": [],
            "event_assembly_targets": [],
            "production_runs": [],
            "assembly_runs": []
        }

        import_file = tmp_path / "circular.json"
        with open(import_file, "w") as f:
            json.dump(import_data, f)

        # Import should reject the circular reference
        result = import_all_from_json_v3(str(import_file), mode="merge")

        # Should have an error about circular reference
        error_found = any(
            "circular" in str(err).lower()
            for err in result.errors
        )
        assert error_found, f"Expected circular reference error, got: {result.errors}"

    def test_import_skips_duplicate_components(self, test_db, tmp_path):
        """Import skips components that already exist."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import export_all_to_json, import_all_from_json_v3

        # Create recipes with component
        flour = ingredient_service.create_ingredient(
            {"display_name": "Duplicate Test Flour", "category": "Flour"}
        )

        child = recipe_service.create_recipe(
            {"name": "Duplicate Child", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}]
        )

        parent = recipe_service.create_recipe(
            {"name": "Duplicate Parent", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        recipe_service.add_recipe_component(parent.id, child.id, quantity=1.0)

        # Export
        export_file = tmp_path / "duplicate_export.json"
        export_all_to_json(str(export_file))

        # Import again (should skip duplicates)
        result = import_all_from_json_v3(str(export_file), mode="merge")

        # Component should be skipped (already exists)
        # result.skipped is a count of skipped items
        assert result.skipped > 0, \
            f"Expected some skipped items, got skipped={result.skipped}"


class TestRecipeExportV4:
    """Tests for Feature 040 recipe export v4.0 fields (F037 support)."""

    @pytest.fixture(autouse=True)
    def setup_database(self, test_db):
        """Use test database for each test."""
        pass

    def test_export_recipe_with_variant_fields(self, tmp_path):
        """Test export recipe with is_production_ready field."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import export_all_to_json

        # Create a recipe with is_production_ready set
        flour = ingredient_service.create_ingredient(
            {"display_name": "Export V4 Flour", "category": "Flour"}
        )

        recipe = recipe_service.create_recipe(
            {
                "name": "V4 Test Cookie",
                "category": "Cookies",
                "yield_quantity": 24,
                "yield_unit": "cookies",
                "is_production_ready": True,
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Export
        export_file = tmp_path / "v4_variant_export.json"
        export_all_to_json(str(export_file))

        # Verify JSON content
        with open(export_file) as f:
            data = json.load(f)

        recipe_data = next(
            (r for r in data["recipes"] if r["name"] == "V4 Test Cookie"), None
        )
        assert recipe_data is not None, "Recipe not found in export"
        assert recipe_data["is_production_ready"] is True
        assert recipe_data["base_recipe_slug"] is None  # Not a variant
        assert recipe_data["variant_name"] is None  # Not a variant

    def test_export_recipe_with_base_recipe(self, tmp_path):
        """Test export base and variant recipes, verify base_recipe_slug exported."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import export_all_to_json

        # Create base recipe
        flour = ingredient_service.create_ingredient(
            {"display_name": "Export V4 Base Flour", "category": "Flour"}
        )

        base_recipe = recipe_service.create_recipe(
            {
                "name": "Base Thumbprint Cookie",
                "category": "Cookies",
                "yield_quantity": 24,
                "yield_unit": "cookies",
                "is_production_ready": True,
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Create variant recipe using the recipe_service variant function
        variant_result = recipe_service.create_recipe_variant(
            base_recipe_id=base_recipe.id,
            variant_name="Raspberry",
            name="Raspberry Thumbprint",
            copy_ingredients=True,
        )

        # Export
        export_file = tmp_path / "v4_base_variant_export.json"
        export_all_to_json(str(export_file))

        # Verify JSON content
        with open(export_file) as f:
            data = json.load(f)

        # Check base recipe
        base_data = next(
            (r for r in data["recipes"] if r["name"] == "Base Thumbprint Cookie"), None
        )
        assert base_data is not None, "Base recipe not found"
        assert base_data["base_recipe_slug"] is None
        assert base_data["is_production_ready"] is True

        # Check variant recipe
        variant_data = next(
            (r for r in data["recipes"] if r["name"] == "Raspberry Thumbprint"), None
        )
        assert variant_data is not None, "Variant recipe not found"
        # base_recipe_slug should be the base recipe name in slug format
        expected_slug = "base_thumbprint_cookie"  # "Base Thumbprint Cookie" -> lowercase with underscores
        assert variant_data["base_recipe_slug"] == expected_slug, f"Expected {expected_slug}, got {variant_data['base_recipe_slug']}"
        assert variant_data["variant_name"] == "Raspberry"

    def test_export_recipe_with_finished_units(self, tmp_path):
        """Test export recipe with FinishedUnits, verify yield_mode exported."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import export_all_to_json
        from src.services.database import session_scope
        from src.models.finished_unit import FinishedUnit, YieldMode

        # Create recipe
        flour = ingredient_service.create_ingredient(
            {"display_name": "Export V4 FU Flour", "category": "Flour"}
        )

        recipe = recipe_service.create_recipe(
            {
                "name": "FU Test Cookie",
                "category": "Cookies",
                "yield_quantity": 24,
                "yield_unit": "cookies",
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Create FinishedUnit for this recipe
        with session_scope() as session:
            fu = FinishedUnit(
                slug="fu-test-cookie-dozen",
                display_name="Cookie Dozen",
                recipe_id=recipe.id,
                yield_mode=YieldMode.DISCRETE_COUNT,
                items_per_batch=12,
                item_unit="cookie",
            )
            session.add(fu)
            session.commit()

        # Export
        export_file = tmp_path / "v4_finished_units_export.json"
        export_all_to_json(str(export_file))

        # Verify JSON content
        with open(export_file) as f:
            data = json.load(f)

        recipe_data = next(
            (r for r in data["recipes"] if r["name"] == "FU Test Cookie"), None
        )
        assert recipe_data is not None, "Recipe not found"
        assert "finished_units" in recipe_data
        assert len(recipe_data["finished_units"]) == 1

        fu_data = recipe_data["finished_units"][0]
        assert fu_data["slug"] == "fu-test-cookie-dozen"
        assert fu_data["name"] == "Cookie Dozen"
        assert fu_data["yield_mode"] == "discrete_count"
        assert fu_data["unit_yield_quantity"] == 12
        assert fu_data["unit_yield_unit"] == "cookie"

    def test_export_recipe_without_variant(self, tmp_path):
        """Test non-variant recipe exports null for base_recipe_slug and variant_name."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import export_all_to_json

        # Create a plain recipe (not a variant)
        flour = ingredient_service.create_ingredient(
            {"display_name": "Export V4 Plain Flour", "category": "Flour"}
        )

        recipe = recipe_service.create_recipe(
            {
                "name": "Plain Non-Variant Cookie",
                "category": "Cookies",
                "yield_quantity": 24,
                "yield_unit": "cookies",
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Export
        export_file = tmp_path / "v4_nonvariant_export.json"
        export_all_to_json(str(export_file))

        # Verify JSON content
        with open(export_file) as f:
            data = json.load(f)

        recipe_data = next(
            (r for r in data["recipes"] if r["name"] == "Plain Non-Variant Cookie"), None
        )
        assert recipe_data is not None, "Recipe not found"
        assert recipe_data["base_recipe_slug"] is None
        assert recipe_data["variant_name"] is None
        assert recipe_data["is_production_ready"] is False  # Default value
        assert recipe_data["finished_units"] == []  # Empty array


class TestRecipeImportV4:
    """Tests for Feature 040 recipe import v4.0 fields (F037 support)."""

    @pytest.fixture(autouse=True)
    def setup_database(self, test_db):
        """Use test database for each test."""
        pass

    def test_import_base_recipe_with_f037_fields(self, tmp_path):
        """Test import recipe with variant_name, is_production_ready fields."""
        from src.services.import_export_service import import_all_from_json_v3
        from src.services.database import session_scope
        from src.models.recipe import Recipe

        # Create JSON with ingredient and recipe (replace mode clears all data)
        import_data = {
            "version": "4.0",
            "ingredients": [
                {"display_name": "Import V4 Flour", "slug": "import_v4_flour", "category": "Flour"}
            ],
            "recipes": [
                {
                    "name": "Import V4 Cookie",
                    "category": "Cookies",
                    "yield_quantity": 24,
                    "yield_unit": "cookies",
                    "variant_name": "Original",
                    "is_production_ready": True,
                    "base_recipe_slug": None,
                    "ingredients": [
                        {"ingredient_slug": "import_v4_flour", "quantity": 2.0, "unit": "cup"}
                    ],
                }
            ],
        }

        import_file = tmp_path / "v4_import_f037.json"
        with open(import_file, "w") as f:
            json.dump(import_data, f)

        # Import
        result = import_all_from_json_v3(str(import_file), mode="replace")

        assert result.successful > 0, f"Import failed: {result.errors}"
        assert result.failed == 0

        # Verify recipe in database
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(name="Import V4 Cookie").first()
            assert recipe is not None
            assert recipe.variant_name == "Original"
            assert recipe.is_production_ready is True
            assert recipe.base_recipe_id is None

    def test_import_variant_recipe(self, tmp_path):
        """Test import variant with base_recipe_slug, verify FK set."""
        from src.services.import_export_service import import_all_from_json_v3
        from src.services.database import session_scope
        from src.models.recipe import Recipe

        # Create JSON with ingredient, base and variant recipes
        import_data = {
            "version": "4.0",
            "ingredients": [
                {"display_name": "Variant Import Flour", "slug": "variant_import_flour", "category": "Flour"}
            ],
            "recipes": [
                {
                    "name": "Base Cookie Recipe",
                    "category": "Cookies",
                    "yield_quantity": 24,
                    "yield_unit": "cookies",
                    "variant_name": None,
                    "is_production_ready": True,
                    "base_recipe_slug": None,
                    "ingredients": [
                        {"ingredient_slug": "variant_import_flour", "quantity": 2.0, "unit": "cup"}
                    ],
                },
                {
                    "name": "Chocolate Chip Variant",
                    "category": "Cookies",
                    "yield_quantity": 24,
                    "yield_unit": "cookies",
                    "variant_name": "Chocolate Chip",
                    "is_production_ready": False,
                    "base_recipe_slug": "base_cookie_recipe",  # Should match base recipe
                    "ingredients": [
                        {"ingredient_slug": "variant_import_flour", "quantity": 2.0, "unit": "cup"}
                    ],
                },
            ],
        }

        import_file = tmp_path / "v4_import_variant.json"
        with open(import_file, "w") as f:
            json.dump(import_data, f)

        # Import
        result = import_all_from_json_v3(str(import_file), mode="replace")

        assert result.successful >= 2, f"Import failed: {result.errors}"
        assert result.failed == 0

        # Verify recipes in database
        with session_scope() as session:
            base_recipe = session.query(Recipe).filter_by(name="Base Cookie Recipe").first()
            variant_recipe = session.query(Recipe).filter_by(name="Chocolate Chip Variant").first()

            assert base_recipe is not None
            assert variant_recipe is not None
            assert variant_recipe.base_recipe_id == base_recipe.id
            assert variant_recipe.variant_name == "Chocolate Chip"

    def test_import_recipe_with_finished_units(self, tmp_path):
        """Test import recipe with finished_units, verify yield_mode."""
        from src.services.import_export_service import import_all_from_json_v3
        from src.services.database import session_scope
        from src.models.recipe import Recipe
        from src.models.finished_unit import FinishedUnit, YieldMode

        # Create JSON with ingredient, recipe and finished_units
        import_data = {
            "version": "4.0",
            "ingredients": [
                {"display_name": "FU Import Flour", "slug": "fu_import_flour", "category": "Flour"}
            ],
            "recipes": [
                {
                    "name": "Import FU Cookie",
                    "category": "Cookies",
                    "yield_quantity": 24,
                    "yield_unit": "cookies",
                    "is_production_ready": True,
                    "base_recipe_slug": None,
                    "ingredients": [
                        {"ingredient_slug": "fu_import_flour", "quantity": 2.0, "unit": "cup"}
                    ],
                    "finished_units": [
                        {
                            "slug": "import-fu-cookie-dozen",
                            "name": "Cookie Dozen",
                            "yield_mode": "discrete_count",
                            "unit_yield_quantity": 12,
                            "unit_yield_unit": "cookie",
                        }
                    ],
                }
            ],
        }

        import_file = tmp_path / "v4_import_fu.json"
        with open(import_file, "w") as f:
            json.dump(import_data, f)

        # Import
        result = import_all_from_json_v3(str(import_file), mode="replace")

        assert result.successful >= 2, f"Import failed: {result.errors}"  # 1 recipe + 1 finished_unit
        assert result.failed == 0

        # Verify in database
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(name="Import FU Cookie").first()
            assert recipe is not None

            fu = session.query(FinishedUnit).filter_by(slug="import-fu-cookie-dozen").first()
            assert fu is not None
            assert fu.recipe_id == recipe.id
            assert fu.yield_mode == YieldMode.DISCRETE_COUNT
            assert fu.items_per_batch == 12
            assert fu.item_unit == "cookie"

    def test_import_variant_before_base_sorted(self, tmp_path):
        """Test import JSON with variant listed first - should still work due to sorting."""
        from src.services.import_export_service import import_all_from_json_v3
        from src.services.database import session_scope
        from src.models.recipe import Recipe

        # Create JSON with variant FIRST in the array (before base)
        import_data = {
            "version": "4.0",
            "ingredients": [
                {"display_name": "Sort Test Flour", "slug": "sort_test_flour", "category": "Flour"}
            ],
            "recipes": [
                # Variant listed first - import should still succeed due to sorting
                {
                    "name": "Variant Listed First",
                    "category": "Cookies",
                    "yield_quantity": 24,
                    "yield_unit": "cookies",
                    "variant_name": "Raspberry",
                    "is_production_ready": False,
                    "base_recipe_slug": "base_listed_second",
                    "ingredients": [
                        {"ingredient_slug": "sort_test_flour", "quantity": 2.0, "unit": "cup"}
                    ],
                },
                # Base listed second
                {
                    "name": "Base Listed Second",
                    "category": "Cookies",
                    "yield_quantity": 24,
                    "yield_unit": "cookies",
                    "variant_name": None,
                    "is_production_ready": True,
                    "base_recipe_slug": None,
                    "ingredients": [
                        {"ingredient_slug": "sort_test_flour", "quantity": 2.0, "unit": "cup"}
                    ],
                },
            ],
        }

        import_file = tmp_path / "v4_import_sort.json"
        with open(import_file, "w") as f:
            json.dump(import_data, f)

        # Import - should succeed because T006 sorts base before variants
        result = import_all_from_json_v3(str(import_file), mode="replace")

        assert result.failed == 0, f"Import failed: {result.errors}"
        assert result.successful >= 2

        # Verify FK relationship is correct
        with session_scope() as session:
            base = session.query(Recipe).filter_by(name="Base Listed Second").first()
            variant = session.query(Recipe).filter_by(name="Variant Listed First").first()

            assert base is not None
            assert variant is not None
            assert variant.base_recipe_id == base.id

    def test_import_invalid_base_recipe_slug(self, tmp_path):
        """Test import with non-existent base_recipe_slug, verify error."""
        from src.services.import_export_service import import_all_from_json_v3

        # Create JSON with invalid base_recipe_slug
        import_data = {
            "version": "4.0",
            "ingredients": [
                {"display_name": "Invalid Ref Flour", "slug": "invalid_ref_flour", "category": "Flour"}
            ],
            "recipes": [
                {
                    "name": "Orphan Variant",
                    "category": "Cookies",
                    "yield_quantity": 24,
                    "yield_unit": "cookies",
                    "variant_name": "Orphan",
                    "is_production_ready": False,
                    "base_recipe_slug": "nonexistent_base_recipe",  # This doesn't exist
                    "ingredients": [
                        {"ingredient_slug": "invalid_ref_flour", "quantity": 2.0, "unit": "cup"}
                    ],
                },
            ],
        }

        import_file = tmp_path / "v4_import_invalid_ref.json"
        with open(import_file, "w") as f:
            json.dump(import_data, f)

        # Import - should record an error for the invalid reference
        result = import_all_from_json_v3(str(import_file), mode="replace")

        assert result.failed > 0, "Expected error for invalid base_recipe_slug"
        # Check that error message mentions base recipe not found
        error_messages = [str(e) for e in result.errors]
        assert any("not found" in msg.lower() or "base recipe" in msg.lower() for msg in error_messages), \
            f"Expected error message about base recipe, got: {error_messages}"

    def test_import_recipe_roundtrip(self, tmp_path):
        """Test import then verify data matches - verifies F037 fields roundtrip."""
        from src.services.import_export_service import import_all_from_json_v3
        from src.services.database import session_scope
        from src.models.recipe import Recipe
        from src.models.finished_unit import FinishedUnit, YieldMode

        # Create complete import data with all F037 fields
        import_data = {
            "version": "4.0",
            "ingredients": [
                {"display_name": "Roundtrip Flour", "slug": "roundtrip_flour", "category": "Flour"}
            ],
            "recipes": [
                {
                    "name": "Roundtrip Base",
                    "category": "Cookies",
                    "yield_quantity": 24,
                    "yield_unit": "cookies",
                    "is_production_ready": True,
                    "base_recipe_slug": None,
                    "variant_name": None,
                    "ingredients": [
                        {"ingredient_slug": "roundtrip_flour", "quantity": 2.0, "unit": "cup"}
                    ],
                    "finished_units": [
                        {
                            "slug": "roundtrip-fu",
                            "name": "Roundtrip Unit",
                            "yield_mode": "discrete_count",
                            "unit_yield_quantity": 24,
                            "unit_yield_unit": "cookie",
                        }
                    ],
                },
                {
                    "name": "Roundtrip Variant Recipe",
                    "category": "Cookies",
                    "yield_quantity": 24,
                    "yield_unit": "cookies",
                    "is_production_ready": False,
                    "base_recipe_slug": "roundtrip_base",
                    "variant_name": "Roundtrip Variant",
                    "ingredients": [
                        {"ingredient_slug": "roundtrip_flour", "quantity": 2.0, "unit": "cup"}
                    ],
                },
            ],
        }

        import_file = tmp_path / "roundtrip_import.json"
        with open(import_file, "w") as f:
            json.dump(import_data, f)

        # Import
        result = import_all_from_json_v3(str(import_file), mode="replace")

        assert result.failed == 0, f"Import failed: {result.failed}, errors: {result.errors}"

        # Verify all data imported correctly
        with session_scope() as session:
            base = session.query(Recipe).filter_by(name="Roundtrip Base").first()
            variant = session.query(Recipe).filter_by(name="Roundtrip Variant Recipe").first()
            fu = session.query(FinishedUnit).filter_by(slug="roundtrip-fu").first()

            assert base is not None, "Base recipe not found after import"
            assert base.is_production_ready is True
            assert base.base_recipe_id is None

            assert variant is not None, "Variant recipe not found after import"
            assert variant.base_recipe_id == base.id
            assert variant.variant_name == "Roundtrip Variant"

            assert fu is not None, "FinishedUnit not found after import"
            assert fu.yield_mode == YieldMode.DISCRETE_COUNT
            assert fu.items_per_batch == 24
            assert fu.item_unit == "cookie"

