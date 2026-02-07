"""Tests for the FinishedGoodBuilderDialog: shell, navigation, food selection, materials."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def ctk_root():
    """Create a CTk root window for dialog testing."""
    import customtkinter as ctk

    if os.environ.get("BAKE_TRACKER_UI_TESTS") != "1":
        if sys.platform != "win32" and not (
            os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        ):
            pytest.skip(
                "UI tests require a display; set BAKE_TRACKER_UI_TESTS=1 to force"
            )

    try:
        root = ctk.CTk()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"CTk unavailable in this environment: {exc}")
    root.withdraw()
    yield root
    root.destroy()


def _make_mock_fg(fg_id, display_name, assembly_type_value, components=None):
    """Create a mock FinishedGood with the given attributes."""
    from src.models.assembly_type import AssemblyType

    fg = MagicMock()
    fg.id = fg_id
    fg.display_name = display_name
    fg.assembly_type = AssemblyType(assembly_type_value)
    fg.components = components or []
    return fg


def _make_mock_fu(fu_id, display_name, category=None):
    """Create a mock FinishedUnit."""
    fu = MagicMock()
    fu.id = fu_id
    fu.display_name = display_name
    fu.category = category
    return fu


def _make_mock_composition(finished_unit_id=None, finished_good_id=None, fu_category=None):
    """Create a mock Composition object."""
    comp = MagicMock()
    comp.finished_unit_id = finished_unit_id
    comp.finished_good_id = finished_good_id
    comp.packaging_product_id = None
    comp.material_unit_id = None
    if finished_unit_id:
        comp.finished_unit_component = MagicMock()
        comp.finished_unit_component.category = fu_category
    else:
        comp.finished_unit_component = None
    return comp


def _make_mock_material_unit(unit_id, name, product_name, category_name,
                             is_hidden=False):
    """Create a mock MaterialUnit with full relationship chain."""
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


@pytest.fixture
def mock_services():
    """Mock the service calls used by the builder dialog."""
    with patch(
        "src.ui.builders.finished_good_builder.finished_good_service"
    ) as mock_fg_svc, patch(
        "src.ui.builders.finished_good_builder.finished_unit_service"
    ) as mock_fu_svc, patch(
        "src.ui.builders.finished_good_builder.material_catalog_service"
    ) as mock_mat_cat_svc, patch(
        "src.ui.builders.finished_good_builder.material_unit_service"
    ) as mock_mat_unit_svc:
        # Default: no items
        mock_fg_svc.get_all_finished_goods.return_value = []
        mock_fu_svc.get_all_finished_units.return_value = []
        mock_mat_cat_svc.list_categories.return_value = []
        mock_mat_unit_svc.list_units.return_value = []
        yield mock_fg_svc, mock_fu_svc, mock_mat_cat_svc, mock_mat_unit_svc


class TestDialogCreation:
    """Tests for dialog construction (T005, T006)."""

    def test_dialog_creates_in_create_mode(self, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_LOCKED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        assert dialog.step1.state == STATE_ACTIVE
        assert dialog.step2.state == STATE_LOCKED
        assert dialog.step3.state == STATE_LOCKED
        assert dialog.result is None
        assert not dialog._is_edit_mode
        dialog.destroy()

    def test_dialog_creates_in_edit_mode(self, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        fg = MagicMock()
        fg.display_name = "Test Gift Box"
        dialog = FinishedGoodBuilderDialog(ctk_root, finished_good=fg)
        assert dialog._is_edit_mode
        assert dialog.name_entry.get() == "Test Gift Box"
        dialog.destroy()

    def test_three_accordion_steps_exist(self, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import AccordionStep

        dialog = FinishedGoodBuilderDialog(ctk_root)
        assert isinstance(dialog.step1, AccordionStep)
        assert isinstance(dialog.step2, AccordionStep)
        assert isinstance(dialog.step3, AccordionStep)
        assert dialog.step1.step_number == 1
        assert dialog.step2.step_number == 2
        assert dialog.step3.step_number == 3
        dialog.destroy()

    def test_scroll_frame_exists(self, ctk_root, mock_services):
        import customtkinter as ctk

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        assert isinstance(dialog.scroll_frame, ctk.CTkScrollableFrame)
        dialog.destroy()


class TestStepNavigation:
    """Tests for step navigation logic (T007)."""

    def test_advance_to_step_2(self, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_COMPLETED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog.advance_to_step(2, "3 items selected")
        assert dialog.step1.state == STATE_COMPLETED
        assert dialog.step2.state == STATE_ACTIVE
        assert dialog._step_completed[1] is True
        dialog.destroy()

    def test_advance_to_step_3(self, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_COMPLETED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog.advance_to_step(2, "3 items")
        dialog.advance_to_step(3, "2 materials")
        assert dialog.step1.state == STATE_COMPLETED
        assert dialog.step2.state == STATE_COMPLETED
        assert dialog.step3.state == STATE_ACTIVE
        dialog.destroy()

    def test_mutual_exclusion(self, ctk_root, mock_services):
        """Only one step should be expanded at a time."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        assert dialog.step1.is_expanded
        assert not dialog.step2.is_expanded

        dialog.advance_to_step(2, "done")
        assert not dialog.step1.is_expanded
        assert dialog.step2.is_expanded
        assert not dialog.step3.is_expanded
        dialog.destroy()

    def test_change_button_goes_back(self, ctk_root, mock_services):
        """Clicking Change on step 1 from step 2 should expand step 1."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog.advance_to_step(2, "3 items")
        dialog.advance_to_step(3, "2 materials")

        dialog._on_step_change(1)
        assert dialog.step1.state == STATE_ACTIVE
        assert dialog.step1.is_expanded
        assert not dialog.step2.is_expanded
        assert not dialog.step3.is_expanded
        dialog.destroy()

    def test_get_current_step(self, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        assert dialog._get_current_step() == 1

        dialog.advance_to_step(2, "done")
        assert dialog._get_current_step() == 2
        dialog.destroy()


class TestDialogControls:
    """Tests for Cancel, Start Over, and name entry (T008)."""

    def test_start_over_resets_all(self, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_LOCKED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog.name_entry.insert(0, "Test Name")
        dialog._food_selections["finished_unit:1"] = {
            "type": "finished_unit", "id": 1, "display_name": "Test", "quantity": 2
        }
        dialog._material_selections[5] = {
            "id": 5, "name": "Red Ribbon", "quantity": 3
        }
        dialog.advance_to_step(2, "3 items")
        dialog.advance_to_step(3, "2 materials")

        dialog._on_start_over()

        assert dialog.step1.state == STATE_ACTIVE
        assert dialog.step2.state == STATE_LOCKED
        assert dialog.step3.state == STATE_LOCKED
        assert dialog.name_entry.get() == ""
        assert len(dialog.food_selections) == 0
        assert len(dialog.material_selections) == 0
        assert not dialog._has_changes
        dialog.destroy()

    def test_cancel_with_no_changes_closes(self, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._has_changes = False
        dialog._on_cancel()
        assert dialog.result is None

    @patch("src.ui.builders.finished_good_builder.show_confirmation")
    def test_cancel_with_changes_prompts(self, mock_confirm, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        mock_confirm.return_value = False
        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._has_changes = True
        dialog._on_cancel()
        mock_confirm.assert_called_once()
        assert dialog.winfo_exists()
        dialog.destroy()

    @patch("src.ui.builders.finished_good_builder.show_confirmation")
    def test_cancel_with_changes_confirmed_closes(self, mock_confirm, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        mock_confirm.return_value = True
        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._has_changes = True
        dialog._on_cancel()
        mock_confirm.assert_called_once()
        assert dialog.result is None

    def test_name_change_sets_has_changes(self, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        assert not dialog._has_changes
        dialog._on_name_change()
        assert dialog._has_changes
        dialog.destroy()

    def test_advance_sets_has_changes(self, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._has_changes = False
        dialog.advance_to_step(2, "done")
        assert dialog._has_changes
        dialog.destroy()


class TestFoodQuery:
    """Tests for food item querying and filtering (T011)."""

    def test_food_query_bare_only(self, ctk_root, mock_services):
        """Bare Items Only filter returns only BARE FinishedGoods."""
        mock_fg_svc, mock_fu_svc, _, _ = mock_services
        bare_comp = _make_mock_composition(finished_unit_id=10, fu_category="Cookies")
        mock_fg_svc.get_all_finished_goods.return_value = [
            _make_mock_fg(1, "Cookie Box", "bare", components=[bare_comp]),
            _make_mock_fg(2, "Gift Set", "gift_box"),
        ]
        mock_fu_svc.get_all_finished_units.return_value = [
            _make_mock_fu(10, "Chocolate Cookie", "Cookies"),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._food_type_var.set("Bare Items Only")
        items = dialog._query_food_items()

        assert len(items) == 1
        assert items[0]["display_name"] == "Cookie Box"
        assert items[0]["comp_type"] == "finished_unit"
        assert items[0]["comp_id"] == 10
        dialog.destroy()

    def test_food_query_include_assemblies(self, ctk_root, mock_services):
        """All filter returns both BARE and non-BARE items."""
        mock_fg_svc, mock_fu_svc, _, _ = mock_services
        bare_comp = _make_mock_composition(finished_unit_id=10, fu_category="Cookies")
        mock_fg_svc.get_all_finished_goods.return_value = [
            _make_mock_fg(1, "Cookie Box", "bare", components=[bare_comp]),
            _make_mock_fg(2, "Gift Set", "gift_box"),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._food_type_var.set("All")
        dialog._food_category_var.set("All Categories")
        items = dialog._query_food_items()

        assert len(items) == 2
        dialog.destroy()

    def test_food_query_category_filter(self, ctk_root, mock_services):
        """Category filter narrows results to matching category."""
        mock_fg_svc, mock_fu_svc, _, _ = mock_services
        cookie_comp = _make_mock_composition(finished_unit_id=10, fu_category="Cookies")
        cake_comp = _make_mock_composition(finished_unit_id=11, fu_category="Cakes")
        mock_fg_svc.get_all_finished_goods.return_value = [
            _make_mock_fg(1, "Cookie Box", "bare", components=[cookie_comp]),
            _make_mock_fg(2, "Cake Box", "bare", components=[cake_comp]),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._food_category_var.set("Cookies")
        items = dialog._query_food_items()

        assert len(items) == 1
        assert items[0]["display_name"] == "Cookie Box"
        dialog.destroy()

    def test_food_query_search_filter(self, ctk_root, mock_services):
        """Search filter matches display_name case-insensitively."""
        mock_fg_svc, *_ = mock_services
        mock_fg_svc.get_all_finished_goods.return_value = [
            _make_mock_fg(1, "Chocolate Chip Cookies", "gift_box"),
            _make_mock_fg(2, "Vanilla Cake Set", "gift_box"),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._food_category_var.set("All Categories")
        dialog._food_search_var.set("choco")
        items = dialog._query_food_items()

        assert len(items) == 1
        assert items[0]["display_name"] == "Chocolate Chip Cookies"
        dialog.destroy()

    def test_assembly_fg_uses_finished_good_comp_type(self, ctk_root, mock_services):
        """Non-BARE FinishedGood should use finished_good as comp_type."""
        mock_fg_svc, *_ = mock_services
        mock_fg_svc.get_all_finished_goods.return_value = [
            _make_mock_fg(5, "Holiday Gift Box", "gift_box"),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        items = dialog._query_food_items()

        assert len(items) == 1
        assert items[0]["comp_type"] == "finished_good"
        assert items[0]["comp_id"] == 5
        dialog.destroy()


class TestFoodSelectionState:
    """Tests for food selection state management (T013)."""

    def test_food_selection_persists_across_filter(self, ctk_root, mock_services):
        """Selections persist when filter changes."""
        mock_fg_svc, *_ = mock_services
        mock_fg_svc.get_all_finished_goods.return_value = [
            _make_mock_fg(1, "Item A", "gift_box"),
            _make_mock_fg(2, "Item B", "gift_box"),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        # Manually add a selection
        dialog._food_selections["finished_good:1"] = {
            "type": "finished_good", "id": 1, "display_name": "Item A", "quantity": 3,
        }

        # Re-render (simulates filter change)
        dialog._on_food_filter_changed()

        # Selection should still be there
        assert "finished_good:1" in dialog._food_selections
        assert dialog._food_selections["finished_good:1"]["quantity"] == 3
        dialog.destroy()

    def test_food_selection_restored_in_rendered_list(self, ctk_root, mock_services):
        """When list re-renders, previously selected items show as checked."""
        mock_fg_svc, *_ = mock_services
        mock_fg_svc.get_all_finished_goods.return_value = [
            _make_mock_fg(1, "Item A", "gift_box"),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._food_selections["finished_good:1"] = {
            "type": "finished_good", "id": 1, "display_name": "Item A", "quantity": 2,
        }

        dialog._on_food_filter_changed()

        # Check that the checkbox var was set to selected
        key = "finished_good:1"
        assert key in dialog._food_check_vars
        assert dialog._food_check_vars[key].get() == "1"
        dialog.destroy()


class TestFoodValidation:
    """Tests for food selection validation (T014)."""

    def test_food_validation_requires_one_item(self, ctk_root, mock_services):
        """Continue should be blocked with no selections."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._on_food_continue()

        # Should show error, not advance
        assert dialog._food_error_label.cget("text") != ""
        assert dialog.step1.state != "completed"
        dialog.destroy()

    def test_food_continue_advances_to_step_2(self, ctk_root, mock_services):
        """Valid food selections should advance to step 2."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_COMPLETED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._food_selections["finished_good:1"] = {
            "type": "finished_good", "id": 1, "display_name": "Item A", "quantity": 2,
        }

        dialog._on_food_continue()

        assert dialog.step1.state == STATE_COMPLETED
        assert dialog.step2.state == STATE_ACTIVE
        dialog.destroy()

    def test_food_continue_summary_count(self, ctk_root, mock_services):
        """Summary should show correct item count."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._food_selections["finished_good:1"] = {
            "type": "finished_good", "id": 1, "display_name": "A", "quantity": 1,
        }
        dialog._food_selections["finished_good:2"] = {
            "type": "finished_good", "id": 2, "display_name": "B", "quantity": 1,
        }

        dialog._on_food_continue()

        # Step 1 should show "2 items selected"
        assert "2 items" in dialog.step1._summary_label.cget("text")
        dialog.destroy()

    def test_parse_quantity_valid(self, ctk_root, mock_services):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        assert FinishedGoodBuilderDialog._parse_quantity("5") == 5
        assert FinishedGoodBuilderDialog._parse_quantity("999") == 999
        assert FinishedGoodBuilderDialog._parse_quantity("0") == 1
        assert FinishedGoodBuilderDialog._parse_quantity("-1") == 1
        assert FinishedGoodBuilderDialog._parse_quantity("1000") == 999
        assert FinishedGoodBuilderDialog._parse_quantity("") == 1
        assert FinishedGoodBuilderDialog._parse_quantity("abc") == 1


class TestMaterialQuery:
    """Tests for material item querying and filtering (T017)."""

    def test_material_query_all(self, ctk_root, mock_services):
        """All MaterialUnits returned with no filter."""
        _, _, mock_mat_cat_svc, mock_mat_unit_svc = mock_services
        mock_mat_unit_svc.list_units.return_value = [
            _make_mock_material_unit(1, "6in Red Ribbon", "Red Satin", "Ribbons"),
            _make_mock_material_unit(2, "Small Gold Box", "Gold Box", "Boxes"),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._mat_category_var.set("All Categories")
        dialog._mat_search_var.set("")
        items = dialog._query_material_items()

        assert len(items) == 2
        assert items[0]["name"] == "6in Red Ribbon"
        assert items[1]["name"] == "Small Gold Box"
        dialog.destroy()

    def test_material_query_category_filter(self, ctk_root, mock_services):
        """MaterialCategory filter narrows results."""
        _, _, mock_mat_cat_svc, mock_mat_unit_svc = mock_services
        mock_mat_unit_svc.list_units.return_value = [
            _make_mock_material_unit(1, "6in Red Ribbon", "Red Satin", "Ribbons"),
            _make_mock_material_unit(2, "Small Gold Box", "Gold Box", "Boxes"),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._mat_category_var.set("Ribbons")
        items = dialog._query_material_items()

        assert len(items) == 1
        assert items[0]["name"] == "6in Red Ribbon"
        assert items[0]["category_name"] == "Ribbons"
        dialog.destroy()

    def test_material_query_search(self, ctk_root, mock_services):
        """Name search filters MaterialUnits case-insensitively."""
        _, _, _, mock_mat_unit_svc = mock_services
        mock_mat_unit_svc.list_units.return_value = [
            _make_mock_material_unit(1, "6in Red Ribbon", "Red Satin", "Ribbons"),
            _make_mock_material_unit(2, "Small Gold Box", "Gold Box", "Boxes"),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._mat_category_var.set("All Categories")
        dialog._mat_search_var.set("gold")
        items = dialog._query_material_items()

        assert len(items) == 1
        assert items[0]["name"] == "Small Gold Box"
        dialog.destroy()

    def test_material_query_hidden_excluded(self, ctk_root, mock_services):
        """Hidden MaterialProducts are excluded."""
        _, _, _, mock_mat_unit_svc = mock_services
        mock_mat_unit_svc.list_units.return_value = [
            _make_mock_material_unit(1, "Visible Unit", "Prod A", "Cat A"),
            _make_mock_material_unit(
                2, "Hidden Unit", "Prod B", "Cat A", is_hidden=True
            ),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        items = dialog._query_material_items()

        assert len(items) == 1
        assert items[0]["name"] == "Visible Unit"
        dialog.destroy()


class TestMaterialSelectionState:
    """Tests for material selection state management (T018, T019)."""

    def test_material_selection_persists_across_filter(self, ctk_root, mock_services):
        """Material selections persist when filter changes."""
        _, _, _, mock_mat_unit_svc = mock_services
        mock_mat_unit_svc.list_units.return_value = [
            _make_mock_material_unit(1, "Red Ribbon", "Red Satin", "Ribbons"),
            _make_mock_material_unit(2, "Gold Box", "Gold Box", "Boxes"),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        # Manually add a selection
        dialog._material_selections[1] = {
            "id": 1, "name": "Red Ribbon", "quantity": 5,
        }

        # Re-render (simulates filter change)
        dialog._on_material_filter_changed()

        assert 1 in dialog._material_selections
        assert dialog._material_selections[1]["quantity"] == 5
        dialog.destroy()

    def test_materials_skip_advances_to_step_3(self, ctk_root, mock_services):
        """Skip clears material selections and advances to step 3."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_COMPLETED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog.advance_to_step(2, "3 items")
        # Add accidental selection
        dialog._material_selections[1] = {
            "id": 1, "name": "Ribbon", "quantity": 2,
        }

        dialog._on_materials_skip()

        assert len(dialog._material_selections) == 0
        assert dialog.step2.state == STATE_COMPLETED
        assert dialog.step3.state == STATE_ACTIVE
        assert "No materials" in dialog.step2._summary_label.cget("text")
        dialog.destroy()

    def test_materials_continue_with_selections(self, ctk_root, mock_services):
        """Continue with selections advances to step 3 with correct summary."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_COMPLETED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog.advance_to_step(2, "3 items")
        dialog._material_selections[1] = {
            "id": 1, "name": "Ribbon", "quantity": 2,
        }
        dialog._material_selections[2] = {
            "id": 2, "name": "Box", "quantity": 1,
        }

        dialog._on_materials_continue()

        assert dialog.step2.state == STATE_COMPLETED
        assert dialog.step3.state == STATE_ACTIVE
        assert "2 materials" in dialog.step2._summary_label.cget("text")
        assert len(dialog._material_selections) == 2
        dialog.destroy()

    def test_materials_continue_empty_same_as_skip(self, ctk_root, mock_services):
        """Continue with no selections behaves like Skip."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_COMPLETED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog.advance_to_step(2, "3 items")

        dialog._on_materials_continue()

        assert dialog.step2.state == STATE_COMPLETED
        assert dialog.step3.state == STATE_ACTIVE
        assert "No materials" in dialog.step2._summary_label.cget("text")
        dialog.destroy()

    def test_material_selection_restored_in_rendered_list(
        self, ctk_root, mock_services
    ):
        """When material list re-renders, previously selected items show checked."""
        _, _, _, mock_mat_unit_svc = mock_services
        mock_mat_unit_svc.list_units.return_value = [
            _make_mock_material_unit(1, "Red Ribbon", "Red Satin", "Ribbons"),
        ]

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._material_selections[1] = {
            "id": 1, "name": "Red Ribbon", "quantity": 3,
        }

        dialog._on_material_filter_changed()

        assert 1 in dialog._mat_check_vars
        assert dialog._mat_check_vars[1].get() == "1"
        dialog.destroy()
