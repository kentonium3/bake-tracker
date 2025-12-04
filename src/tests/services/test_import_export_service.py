"""
Unit tests for import_export_service.py - v3.0 export functions.

Tests cover:
- ExportResult class with per-entity counts
- export_finished_units_to_json()
- export_compositions_to_json()
- export_package_finished_goods_to_json()
- export_production_records_to_json()
- export_all_to_json() v3.0 format
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
    export_all_to_json,
    export_compositions_to_json,
    export_finished_units_to_json,
    export_package_finished_goods_to_json,
    export_production_records_to_json,
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

            # Verify v3.0 header
            assert data["version"] == "3.0"
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
