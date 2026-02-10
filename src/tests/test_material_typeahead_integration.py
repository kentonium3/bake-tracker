"""
Tests for material type-ahead integration in the FG builder.

Tests the search callback wrapper without requiring full UI setup.
"""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest


def _make_mock_unit(unit_id, name, product_name, category_name, is_hidden=False):
    """Create a mock MaterialUnit with relationships for testing."""
    category = MagicMock()
    category.name = category_name

    subcategory = MagicMock()
    subcategory.category = category

    material = MagicMock()
    material.subcategory = subcategory

    product = MagicMock()
    product.name = product_name
    product.material = material
    product.is_hidden = is_hidden

    unit = MagicMock()
    unit.id = unit_id
    unit.name = name
    unit.material_product = product

    return unit


class TestMaterialSearchCallback:
    """Test the material search callback used by TypeAheadEntry."""

    @patch("src.services.material_unit_service.list_units")
    def test_returns_matching_results(self, mock_list_units):
        """Callback returns results matching query."""
        mock_list_units.return_value = [
            _make_mock_unit(1, "Red Satin Ribbon 1in", "Red Satin Ribbon", "Ribbons"),
            _make_mock_unit(2, "Blue Velvet Ribbon 1in", "Blue Velvet Ribbon", "Ribbons"),
        ]
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        results = FinishedGoodBuilderDialog._search_materials_for_typeahead(
            None, "red"
        )
        assert len(results) == 1
        assert results[0]["display_name"] == "Red Satin Ribbon 1in"
        assert results[0]["id"] == 1

    @patch("src.services.material_unit_service.list_units")
    def test_case_insensitive_matching(self, mock_list_units):
        """Search is case-insensitive."""
        mock_list_units.return_value = [
            _make_mock_unit(1, "Gold Foil Box", "Gold Foil Box", "Boxes"),
        ]
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        results = FinishedGoodBuilderDialog._search_materials_for_typeahead(
            None, "GOLD"
        )
        assert len(results) == 1

    @patch("src.services.material_unit_service.list_units")
    def test_skips_hidden_products(self, mock_list_units):
        """Hidden products are excluded from results."""
        mock_list_units.return_value = [
            _make_mock_unit(1, "Visible Item", "Visible", "Cat", is_hidden=False),
            _make_mock_unit(2, "Hidden Item", "Hidden", "Cat", is_hidden=True),
        ]
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        results = FinishedGoodBuilderDialog._search_materials_for_typeahead(
            None, "item"
        )
        assert len(results) == 1
        assert results[0]["display_name"] == "Visible Item"

    @patch("src.services.material_unit_service.list_units")
    def test_limits_to_10_results(self, mock_list_units):
        """Results capped at 10 items."""
        mock_list_units.return_value = [
            _make_mock_unit(i, f"Ribbon {i}", f"Ribbon {i}", "Ribbons")
            for i in range(20)
        ]
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        results = FinishedGoodBuilderDialog._search_materials_for_typeahead(
            None, "ribbon"
        )
        assert len(results) == 10

    @patch("src.services.material_unit_service.list_units")
    def test_handles_service_error(self, mock_list_units):
        """Returns empty list on service error."""
        mock_list_units.side_effect = RuntimeError("DB error")
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        results = FinishedGoodBuilderDialog._search_materials_for_typeahead(
            None, "ribbon"
        )
        assert results == []

    @patch("src.services.material_unit_service.list_units")
    def test_empty_results(self, mock_list_units):
        """Returns empty list when no matches."""
        mock_list_units.return_value = [
            _make_mock_unit(1, "Red Ribbon", "Red Ribbon", "Ribbons"),
        ]
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        results = FinishedGoodBuilderDialog._search_materials_for_typeahead(
            None, "xyz"
        )
        assert results == []

    @patch("src.services.material_unit_service.list_units")
    def test_result_has_required_keys(self, mock_list_units):
        """Results have id, display_name, name, category_name, product_name."""
        mock_list_units.return_value = [
            _make_mock_unit(42, "Gold Box 6in", "Gold Box", "Boxes"),
        ]
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        results = FinishedGoodBuilderDialog._search_materials_for_typeahead(
            None, "gold"
        )
        item = results[0]
        assert item["id"] == 42
        assert item["display_name"] == "Gold Box 6in"
        assert item["name"] == "Gold Box 6in"
        assert item["category_name"] == "Boxes"
        assert item["product_name"] == "Gold Box"

    @patch("src.services.material_unit_service.list_units")
    def test_skips_units_without_product(self, mock_list_units):
        """Units with no product are excluded."""
        unit_no_product = MagicMock()
        unit_no_product.id = 1
        unit_no_product.name = "Orphan Unit"
        unit_no_product.material_product = None

        mock_list_units.return_value = [unit_no_product]
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        results = FinishedGoodBuilderDialog._search_materials_for_typeahead(
            None, "orphan"
        )
        assert results == []


class TestMaterialSelectionCallback:
    """Test the material selection callback behavior."""

    def test_adds_to_selections(self):
        """Selection callback adds material to _material_selections dict."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        builder = MagicMock(spec=FinishedGoodBuilderDialog)
        builder._material_selections = {}
        builder._has_changes = False
        builder._query_material_items = MagicMock(return_value=[])
        builder._render_material_items = MagicMock()

        item = {"id": 42, "name": "Gold Box 6in", "display_name": "Gold Box 6in"}
        FinishedGoodBuilderDialog._on_typeahead_material_selected(builder, item)

        assert 42 in builder._material_selections
        assert builder._material_selections[42]["name"] == "Gold Box 6in"
        assert builder._material_selections[42]["quantity"] == 1
        assert builder._has_changes is True

    def test_does_not_overwrite_existing_selection(self):
        """Selection callback doesn't overwrite existing selection (keeps quantity)."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        builder = MagicMock(spec=FinishedGoodBuilderDialog)
        builder._material_selections = {
            42: {"id": 42, "name": "Gold Box 6in", "quantity": 5}
        }
        builder._has_changes = False
        builder._query_material_items = MagicMock(return_value=[])
        builder._render_material_items = MagicMock()

        item = {"id": 42, "name": "Gold Box 6in", "display_name": "Gold Box 6in"}
        FinishedGoodBuilderDialog._on_typeahead_material_selected(builder, item)

        # Quantity should remain 5 (not overwritten to 1)
        assert builder._material_selections[42]["quantity"] == 5

    def test_re_renders_material_list(self):
        """Selection callback triggers re-render of material list."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        builder = MagicMock(spec=FinishedGoodBuilderDialog)
        builder._material_selections = {}
        builder._has_changes = False
        builder._query_material_items = MagicMock(return_value=[{"id": 1, "name": "X"}])
        builder._render_material_items = MagicMock()

        item = {"id": 1, "name": "X", "display_name": "X"}
        FinishedGoodBuilderDialog._on_typeahead_material_selected(builder, item)

        builder._query_material_items.assert_called_once()
        builder._render_material_items.assert_called_once()
