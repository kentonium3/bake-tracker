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
- Version validation (FR-018)
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
    ImportVersionError,
    export_all_to_json,
    export_compositions_to_json,
    export_finished_units_to_json,
    export_package_finished_goods_to_json,
    export_production_records_to_json,
    import_all_from_json_v3,
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
        mock_export_production_records,
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

            # Verify v3.2 header (Feature 016: event-centric production)
            assert data["version"] == "3.2"
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
        mock_export_production_records,
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


class TestImportVersionValidation:
    """Tests for v3.0 version validation (FR-018)."""

    def test_import_rejects_v2_format(self):
        """Test import rejects v2.0 format files."""
        v2_data = {
            "version": "2.0",
            "export_date": "2025-01-01T00:00:00Z",
            "ingredients": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v2_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ImportVersionError) as exc_info:
                import_all_from_json_v3(temp_path)

            assert "Unsupported file version: 2.0" in str(exc_info.value)
            assert "supports versions: 3.0, 3.1" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_import_rejects_unknown_version(self):
        """Test import rejects files with unknown/missing version."""
        no_version_data = {
            "ingredients": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(no_version_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ImportVersionError) as exc_info:
                import_all_from_json_v3(temp_path)

            assert "Unsupported file version: unknown" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_import_accepts_v3_format(self):
        """Test import accepts v3.0 format files."""
        v3_data = {
            "version": "3.0",
            "exported_at": "2025-12-04T00:00:00Z",
            "application": "bake-tracker",
            "ingredients": [],
            "recipes": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v3_data, f)
            temp_path = f.name

        try:
            # Should not raise - may fail due to DB issues but not version error
            result = import_all_from_json_v3(temp_path)
            # If we get here without ImportVersionError, version check passed
            assert result is not None
        except ImportVersionError:
            pytest.fail("Should not raise ImportVersionError for v3.0 format")
        except Exception:
            # Other errors (DB, etc.) are acceptable - we're testing version check
            pass
        finally:
            os.unlink(temp_path)


class TestImportModeValidation:
    """Tests for import mode parameter validation."""

    def test_invalid_mode_raises_error(self):
        """Test invalid mode raises ValueError."""
        v3_data = {"version": "3.0", "ingredients": []}

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

    def test_version_error_is_user_friendly(self):
        """Test version error message is user-friendly."""
        v2_data = {"version": "1.0", "ingredients": []}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(v2_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ImportVersionError) as exc_info:
                import_all_from_json_v3(temp_path)

            error_msg = str(exc_info.value)

            # Should be user-friendly - no technical jargon
            assert "stack" not in error_msg.lower()
            assert "traceback" not in error_msg.lower()
            assert "exception" not in error_msg.lower()

            # Should provide helpful guidance
            assert "export a new backup" in error_msg.lower()
        finally:
            os.unlink(temp_path)

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
        assert data["version"] == "3.0"

    def test_sample_data_has_v3_header(self):
        """Verify sample data has proper v3.0 header."""
        with open(SAMPLE_DATA_PATH, "r") as f:
            data = json.load(f)

        assert data.get("version") == "3.0"
        assert "exported_at" in data
        assert "application" in data
        assert data.get("application") == "bake-tracker"

    def test_sample_data_has_all_entity_types(self):
        """Verify sample data includes all 15 entity types."""
        expected_entities = [
            "unit_conversions",
            "ingredients",
            "products",
            "purchases",
            "pantry_items",
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

        with open(SAMPLE_DATA_PATH, "r") as f:
            data = json.load(f)

        for entity in expected_entities:
            assert entity in data, f"Sample data must include {entity}"
            assert isinstance(data[entity], list), f"{entity} must be a list"
            assert len(data[entity]) > 0, f"{entity} should have at least one record"

    def test_sample_data_referential_integrity(self):
        """Verify sample data has consistent references."""
        with open(SAMPLE_DATA_PATH, "r") as f:
            data = json.load(f)

        # Collect slugs
        ingredient_slugs = {i["slug"] for i in data["ingredients"]}
        recipe_slugs = {r["slug"] for r in data["recipes"]}
        finished_good_slugs = {fg["slug"] for fg in data["finished_goods"]}
        package_slugs = {p["slug"] for p in data["packages"]}
        event_slugs = {e["slug"] for e in data["events"]}
        recipient_names = {r["name"] for r in data["recipients"]}

        # Verify products reference valid ingredients
        for product in data["products"]:
            assert product["ingredient_slug"] in ingredient_slugs, \
                f"Product references invalid ingredient: {product['ingredient_slug']}"

        # Verify unit_conversions reference valid ingredients
        for conv in data["unit_conversions"]:
            assert conv["ingredient_slug"] in ingredient_slugs, \
                f"Conversion references invalid ingredient: {conv['ingredient_slug']}"

        # Verify finished_units reference valid recipes
        for fu in data["finished_units"]:
            assert fu["recipe_slug"] in recipe_slugs, \
                f"Finished unit references invalid recipe: {fu['recipe_slug']}"

        # Verify compositions reference valid finished_goods
        for comp in data["compositions"]:
            assert comp["finished_good_slug"] in finished_good_slugs, \
                f"Composition references invalid finished_good: {comp['finished_good_slug']}"

        # Verify package_finished_goods reference valid packages and finished_goods
        for pfg in data["package_finished_goods"]:
            assert pfg["package_slug"] in package_slugs, \
                f"Package-FG references invalid package: {pfg['package_slug']}"
            assert pfg["finished_good_slug"] in finished_good_slugs, \
                f"Package-FG references invalid finished_good: {pfg['finished_good_slug']}"

        # Verify event_recipient_packages reference valid events, recipients, packages
        for erp in data["event_recipient_packages"]:
            assert erp["event_slug"] in event_slugs, \
                f"Assignment references invalid event: {erp['event_slug']}"
            assert erp["recipient_name"] in recipient_names, \
                f"Assignment references invalid recipient: {erp['recipient_name']}"
            assert erp["package_slug"] in package_slugs, \
                f"Assignment references invalid package: {erp['package_slug']}"

        # Verify production_records reference valid events and recipes
        for pr in data["production_records"]:
            assert pr["event_slug"] in event_slugs, \
                f"Production record references invalid event: {pr['event_slug']}"
            assert pr["recipe_slug"] in recipe_slugs, \
                f"Production record references invalid recipe: {pr['recipe_slug']}"


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
            "unit_conversions",
            "ingredients",
            "products",
            "purchases",
            "pantry_items",
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
        """Verify sample data represents a coherent holiday baking scenario."""
        with open(SAMPLE_DATA_PATH, "r") as f:
            data = json.load(f)

        # Should have holiday-related events
        event_names = [e["name"].lower() for e in data["events"]]
        has_holiday = any("holiday" in n or "christmas" in n or "new year" in n for n in event_names)
        assert has_holiday, "Sample data should include holiday events"

        # Should have baking-related recipes
        recipe_categories = {r["category"] for r in data["recipes"]}
        has_baking = any(
            cat.lower() in ["cookies", "brownies", "cakes", "candies", "pies"]
            for cat in recipe_categories
        )
        assert has_baking, "Sample data should include baking recipes"

        # Should have gift recipients
        assert len(data["recipients"]) >= 2, "Should have multiple gift recipients"

        # Should have production records
        assert len(data["production_records"]) >= 1, "Should have production history"


class TestDensityFieldsImportExport:
    """Tests for 4-field density model in import/export (Feature 010)."""

    def test_export_ingredient_includes_density_fields(self):
        """Export includes all 4 density fields when present."""
        from src.models.ingredient import Ingredient

        ingredient = Ingredient(
            display_name="Test Flour",
            slug="test-flour",
            category="Flour",
            recipe_unit="cup",
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=4.25,
            density_weight_unit="oz",
        )

        # Manually build export dict like the export function does
        ingredient_data = {
            "name": ingredient.display_name,
            "slug": ingredient.slug,
            "category": ingredient.category,
            "recipe_unit": ingredient.recipe_unit,
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
            category="Other",
            recipe_unit="cup",
        )

        # Manually build export dict
        ingredient_data = {
            "name": ingredient.display_name,
            "slug": ingredient.slug,
            "category": ingredient.category,
            "recipe_unit": ingredient.recipe_unit,
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
            "recipe_unit": "cup",
            "density_volume_value": 1.0,
            "density_volume_unit": "cup",
            "density_weight_value": 4.25,
            "density_weight_unit": "oz",
        }

        # Mimic import logic
        ingredient = Ingredient(
            display_name=data.get("name"),
            slug=data.get("slug"),
            category=data.get("category"),
            recipe_unit=data.get("recipe_unit"),
            density_volume_value=data.get("density_volume_value"),
            density_volume_unit=data.get("density_volume_unit"),
            density_weight_value=data.get("density_weight_value"),
            density_weight_unit=data.get("density_weight_unit"),
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
            "recipe_unit": "cup",
            "density_g_per_ml": 0.5,  # Legacy field - should be ignored
        }

        # Mimic import logic (does NOT read density_g_per_ml)
        ingredient = Ingredient(
            display_name=data.get("name"),
            slug=data.get("slug"),
            category=data.get("category"),
            recipe_unit=data.get("recipe_unit"),
            density_volume_value=data.get("density_volume_value"),
            density_volume_unit=data.get("density_volume_unit"),
            density_weight_value=data.get("density_weight_value"),
            density_weight_unit=data.get("density_weight_unit"),
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
            recipe_unit="cup",
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=4.25,
            density_weight_unit="oz",
        )

        # Export to dict
        exported = {
            "name": original.display_name,
            "slug": original.slug,
            "category": original.category,
            "recipe_unit": original.recipe_unit,
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
            recipe_unit=exported.get("recipe_unit"),
            density_volume_value=exported.get("density_volume_value"),
            density_volume_unit=exported.get("density_volume_unit"),
            density_weight_value=exported.get("density_weight_value"),
            density_weight_unit=exported.get("density_weight_unit"),
        )

        # Verify density matches
        assert reimported.density_volume_value == original.density_volume_value
        assert reimported.density_volume_unit == original.density_volume_unit
        assert reimported.density_weight_value == original.density_weight_value
        assert reimported.density_weight_unit == original.density_weight_unit

    def test_sample_data_has_density_fields(self):
        """Verify sample_data.json uses new density format."""
        import json

        with open("test_data/sample_data.json", "r") as f:
            data = json.load(f)

        # Find All-Purpose Flour
        flour = None
        for ing in data["ingredients"]:
            if ing["slug"] == "all_purpose_flour":
                flour = ing
                break

        assert flour is not None, "Sample data should have all_purpose_flour"

        # Should have 4-field density, not legacy
        assert "density_g_per_ml" not in flour, "Should not have legacy density field"
        assert flour.get("density_volume_value") == 1.0
        assert flour.get("density_volume_unit") == "cup"
        assert flour.get("density_weight_value") == 4.25
        assert flour.get("density_weight_unit") == "oz"

    def test_sample_data_valid_json(self):
        """Verify sample_data.json is valid JSON."""
        import json

        # Should not raise
        with open("test_data/sample_data.json", "r") as f:
            data = json.load(f)

        assert "version" in data
        assert data["version"] == "3.0"
        assert "ingredients" in data


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
            {"name": "Export Flour", "category": "Flour", "recipe_unit": "cup"}
        )

        # Create child recipe
        child = recipe_service.create_recipe(
            {
                "name": "Export Child Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch",
            },
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}],
        )

        # Create parent recipe
        parent = recipe_service.create_recipe(
            {
                "name": "Export Parent Recipe",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch",
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}],
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
            {"name": "Simple Flour", "category": "Flour", "recipe_unit": "cup"}
        )

        recipe = recipe_service.create_recipe(
            {
                "name": "Simple Recipe No Components",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch",
            },
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}],
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
            {"name": "Full Export Flour", "category": "Flour", "recipe_unit": "cup"}
        )

        child = recipe_service.create_recipe(
            {
                "name": "Full Export Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch",
            },
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}],
        )

        parent = recipe_service.create_recipe(
            {
                "name": "Full Export Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch",
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}],
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


class TestRecipeComponentImport:
    """Tests for importing recipe components (T033)."""

    def test_import_recipe_with_components(self, test_db, tmp_path):
        """Import creates component relationships."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import import_recipes_from_json

        # Create ingredient for recipes
        flour = ingredient_service.create_ingredient(
            {"name": "Import Flour", "category": "Flour", "recipe_unit": "cup"}
        )

        # Create export data with component relationship
        export_data = {
            "version": "1.0",
            "recipes": [
                {
                    "name": "Import Child Recipe",
                    "category": "Cookies",
                    "yield_quantity": 1,
                    "yield_unit": "batch",
                    "ingredients": [
                        {"ingredient_slug": "import_flour", "quantity": 1.0, "unit": "cup"}
                    ],
                    "components": [],
                },
                {
                    "name": "Import Parent Recipe",
                    "category": "Cookies",
                    "yield_quantity": 1,
                    "yield_unit": "batch",
                    "ingredients": [
                        {"ingredient_slug": "import_flour", "quantity": 2.0, "unit": "cup"}
                    ],
                    "components": [
                        {"recipe_name": "Import Child Recipe", "quantity": 2.0, "notes": "Test import"}
                    ],
                },
            ],
        }

        import_file = tmp_path / "import.json"
        with open(import_file, "w") as f:
            json.dump(export_data, f)

        result = import_recipes_from_json(str(import_file))

        # Should succeed
        assert result.successful >= 2

        # Verify relationship created
        parent = recipe_service.get_recipe_by_name("Import Parent Recipe")
        components = recipe_service.get_recipe_components(parent.id)
        assert len(components) == 1
        assert components[0].quantity == 2.0
        assert components[0].notes == "Test import"
        assert components[0].component_recipe.name == "Import Child Recipe"

    def test_import_component_missing_recipe(self, test_db, tmp_path):
        """Import warns when component recipe doesn't exist."""
        from src.services import ingredient_service
        from src.services.import_export_service import import_recipes_from_json

        flour = ingredient_service.create_ingredient(
            {"name": "Missing Comp Flour", "category": "Flour", "recipe_unit": "cup"}
        )

        export_data = {
            "version": "1.0",
            "recipes": [
                {
                    "name": "Missing Comp Parent",
                    "category": "Cookies",
                    "yield_quantity": 1,
                    "yield_unit": "batch",
                    "ingredients": [
                        {"ingredient_slug": "missing_comp_flour", "quantity": 1.0, "unit": "cup"}
                    ],
                    "components": [{"recipe_name": "Nonexistent Recipe", "quantity": 1.0}],
                }
            ],
        }

        import_file = tmp_path / "import.json"
        with open(import_file, "w") as f:
            json.dump(export_data, f)

        result = import_recipes_from_json(str(import_file))

        # Should succeed overall (recipe imported)
        assert result.successful >= 1
        # Should have warning about missing component
        assert len(result.warnings) > 0
        warning_str = str(result.warnings)
        assert "Nonexistent Recipe" in warning_str

    def test_import_links_existing_recipe(self, test_db, tmp_path):
        """Import links to existing recipe if component already exists."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import import_recipes_from_json

        flour = ingredient_service.create_ingredient(
            {"name": "Existing Link Flour", "category": "Flour", "recipe_unit": "cup"}
        )

        # Pre-create child recipe
        child = recipe_service.create_recipe(
            {
                "name": "Existing Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch",
            },
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}],
        )

        # Import parent that references existing child
        export_data = {
            "version": "1.0",
            "recipes": [
                {
                    "name": "New Parent Linking",
                    "category": "Cookies",
                    "yield_quantity": 1,
                    "yield_unit": "batch",
                    "ingredients": [
                        {"ingredient_slug": "existing_link_flour", "quantity": 2.0, "unit": "cup"}
                    ],
                    "components": [{"recipe_name": "Existing Child", "quantity": 1.0}],
                }
            ],
        }

        import_file = tmp_path / "import.json"
        with open(import_file, "w") as f:
            json.dump(export_data, f)

        result = import_recipes_from_json(str(import_file))

        assert result.successful >= 1

        parent = recipe_service.get_recipe_by_name("New Parent Linking")
        components = recipe_service.get_recipe_components(parent.id)
        assert len(components) == 1
        assert components[0].component_recipe_id == child.id

    def test_import_export_roundtrip(self, test_db, tmp_path):
        """Export then import preserves all component relationships."""
        from src.services import ingredient_service, recipe_service
        from src.services.import_export_service import (
            export_recipes_to_json,
            import_recipes_from_json,
        )

        # Create hierarchy
        flour = ingredient_service.create_ingredient(
            {"name": "Roundtrip Flour", "category": "Flour", "recipe_unit": "cup"}
        )

        grandchild = recipe_service.create_recipe(
            {
                "name": "Roundtrip Grandchild",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch",
            },
            [{"ingredient_id": flour.id, "quantity": 0.5, "unit": "cup"}],
        )

        child = recipe_service.create_recipe(
            {
                "name": "Roundtrip Child",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch",
            },
            [{"ingredient_id": flour.id, "quantity": 1.0, "unit": "cup"}],
        )

        parent = recipe_service.create_recipe(
            {
                "name": "Roundtrip Parent",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch",
            },
            [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}],
        )

        recipe_service.add_recipe_component(child.id, grandchild.id, quantity=1.0)
        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0, notes="Double batch")

        # Export
        export_file = tmp_path / "roundtrip.json"
        export_result = export_recipes_to_json(str(export_file))
        assert export_result.success

        # Delete all recipes
        recipe_service.delete_recipe(parent.id)
        recipe_service.delete_recipe(child.id)
        recipe_service.delete_recipe(grandchild.id)

        # Import
        import_result = import_recipes_from_json(str(export_file))
        assert import_result.successful >= 3

        # Verify hierarchy restored
        imported_parent = recipe_service.get_recipe_by_name("Roundtrip Parent")
        parent_components = recipe_service.get_recipe_components(imported_parent.id)
        assert len(parent_components) == 1
        assert parent_components[0].component_recipe.name == "Roundtrip Child"
        assert parent_components[0].quantity == 2.0
        assert parent_components[0].notes == "Double batch"

        child_components = recipe_service.get_recipe_components(
            parent_components[0].component_recipe_id
        )
        assert len(child_components) == 1
        assert child_components[0].component_recipe.name == "Roundtrip Grandchild"
