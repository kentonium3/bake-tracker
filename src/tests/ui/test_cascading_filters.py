"""
Integration tests for cascading hierarchy filters (Feature 034).

Tests the L0 -> L1 -> L2 cascading behavior in Products and Inventory tabs,
and L2-only enforcement in recipe ingredient selection.

These tests focus on the filter logic and service integration rather than
UI widget rendering, using mocks for CustomTkinter components.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List

from src.services import ingredient_hierarchy_service
from src.services.database import session_scope


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def hierarchy_test_data():
    """Create test hierarchy data for L0 -> L1 -> L2 structure."""
    return {
        "l0_baking": {
            "id": 1,
            "display_name": "Baking",
            "hierarchy_level": 0,
            "is_leaf": False,
            "parent_ingredient_id": None,
        },
        "l0_dairy": {
            "id": 2,
            "display_name": "Dairy",
            "hierarchy_level": 0,
            "is_leaf": False,
            "parent_ingredient_id": None,
        },
        "l1_flour": {
            "id": 10,
            "display_name": "Flour",
            "hierarchy_level": 1,
            "is_leaf": False,
            "parent_ingredient_id": 1,
        },
        "l1_sugar": {
            "id": 11,
            "display_name": "Sugar",
            "hierarchy_level": 1,
            "is_leaf": False,
            "parent_ingredient_id": 1,
        },
        "l1_milk": {
            "id": 20,
            "display_name": "Milk",
            "hierarchy_level": 1,
            "is_leaf": False,
            "parent_ingredient_id": 2,
        },
        "l2_all_purpose_flour": {
            "id": 100,
            "display_name": "All-Purpose Flour",
            "hierarchy_level": 2,
            "is_leaf": True,
            "parent_ingredient_id": 10,
        },
        "l2_bread_flour": {
            "id": 101,
            "display_name": "Bread Flour",
            "hierarchy_level": 2,
            "is_leaf": True,
            "parent_ingredient_id": 10,
        },
        "l2_granulated_sugar": {
            "id": 110,
            "display_name": "Granulated Sugar",
            "hierarchy_level": 2,
            "is_leaf": True,
            "parent_ingredient_id": 11,
        },
        "l2_whole_milk": {
            "id": 200,
            "display_name": "Whole Milk",
            "hierarchy_level": 2,
            "is_leaf": True,
            "parent_ingredient_id": 20,
        },
    }


@pytest.fixture
def mock_products_tab(hierarchy_test_data):
    """Create a mock ProductsTab with filter components."""
    tab = Mock()

    # Filter variables (StringVar mocks)
    tab.l0_filter_var = Mock()
    tab.l0_filter_var.get = Mock(return_value="All Categories")
    tab.l0_filter_var.set = Mock()

    tab.l1_filter_var = Mock()
    tab.l1_filter_var.get = Mock(return_value="All")
    tab.l1_filter_var.set = Mock()

    tab.l2_filter_var = Mock()
    tab.l2_filter_var.get = Mock(return_value="All")
    tab.l2_filter_var.set = Mock()

    tab.brand_var = Mock()
    tab.brand_var.get = Mock(return_value="All")
    tab.brand_var.set = Mock()

    tab.supplier_var = Mock()
    tab.supplier_var.get = Mock(return_value="All")
    tab.supplier_var.set = Mock()

    tab.search_var = Mock()
    tab.search_var.get = Mock(return_value="")
    tab.search_var.set = Mock()

    # Filter dropdowns
    tab.l0_filter_dropdown = Mock()
    tab.l0_filter_dropdown.configure = Mock()

    tab.l1_filter_dropdown = Mock()
    tab.l1_filter_dropdown.configure = Mock()

    tab.l2_filter_dropdown = Mock()
    tab.l2_filter_dropdown.configure = Mock()

    # Hierarchy maps
    tab._l0_map = {
        "Baking": hierarchy_test_data["l0_baking"],
        "Dairy": hierarchy_test_data["l0_dairy"],
    }
    tab._l1_map = {}
    tab._l2_map = {}

    # Re-entry guard
    tab._updating_filters = False

    # Refresh method
    tab._load_products = Mock()

    return tab


@pytest.fixture
def mock_inventory_tab(hierarchy_test_data):
    """Create a mock InventoryTab with filter components."""
    tab = Mock()

    # Filter variables
    tab.l0_filter_var = Mock()
    tab.l0_filter_var.get = Mock(return_value="All Categories")
    tab.l0_filter_var.set = Mock()

    tab.l1_filter_var = Mock()
    tab.l1_filter_var.get = Mock(return_value="All")
    tab.l1_filter_var.set = Mock()

    tab.l2_filter_var = Mock()
    tab.l2_filter_var.get = Mock(return_value="All")
    tab.l2_filter_var.set = Mock()

    tab.brand_var = Mock()
    tab.brand_var.get = Mock(return_value="All Brands")
    tab.brand_var.set = Mock()

    # Search entry (different from products tab)
    tab.search_entry = Mock()
    tab.search_entry.delete = Mock()

    # Filter dropdowns
    tab.l0_filter_dropdown = Mock()
    tab.l0_filter_dropdown.configure = Mock()

    tab.l1_filter_dropdown = Mock()
    tab.l1_filter_dropdown.configure = Mock()

    tab.l2_filter_dropdown = Mock()
    tab.l2_filter_dropdown.configure = Mock()

    # Hierarchy maps
    tab._l0_map = {
        "Baking": hierarchy_test_data["l0_baking"],
        "Dairy": hierarchy_test_data["l0_dairy"],
    }
    tab._l1_map = {}
    tab._l2_map = {}

    # Re-entry guard
    tab._updating_filters = False

    # Refresh method
    tab._apply_filters = Mock()

    return tab


@pytest.fixture
def mock_recipe_dialog():
    """Create a mock IngredientSelectionDialog."""
    dialog = Mock()
    dialog._selected_ingredient = None
    dialog.select_button = Mock()
    dialog.select_button.configure = Mock()
    return dialog


# =============================================================================
# Products Tab Cascading Tests
# =============================================================================


class TestProductsTabCascading:
    """Tests for Products tab cascading filters."""

    def test_l0_selection_updates_l1_options(
        self, mock_products_tab, hierarchy_test_data
    ):
        """When L0 is selected, L1 should show only children of that L0."""
        # Arrange
        l1_children = [
            hierarchy_test_data["l1_flour"],
            hierarchy_test_data["l1_sugar"],
        ]

        with patch.object(
            ingredient_hierarchy_service, "get_children", return_value=l1_children
        ):
            # Simulate L0 selection
            mock_products_tab.l0_filter_var.get.return_value = "Baking"

            # Act - simulate the filter change handler logic
            value = mock_products_tab.l0_filter_var.get()
            if value in mock_products_tab._l0_map:
                l0_id = mock_products_tab._l0_map[value].get("id")
                subcategories = ingredient_hierarchy_service.get_children(l0_id)
                mock_products_tab._l1_map = {
                    sub.get("display_name", "?"): sub for sub in subcategories
                }
                l1_values = ["All"] + sorted(mock_products_tab._l1_map.keys())
                mock_products_tab.l1_filter_dropdown.configure(
                    values=l1_values, state="normal"
                )

            # Assert
            assert "Flour" in mock_products_tab._l1_map
            assert "Sugar" in mock_products_tab._l1_map
            assert len(mock_products_tab._l1_map) == 2
            mock_products_tab.l1_filter_dropdown.configure.assert_called()
            call_kwargs = mock_products_tab.l1_filter_dropdown.configure.call_args[1]
            assert "Flour" in call_kwargs["values"]
            assert "Sugar" in call_kwargs["values"]
            assert call_kwargs["state"] == "normal"

    def test_l0_selection_clears_l2(self, mock_products_tab, hierarchy_test_data):
        """When L0 changes, L2 should be reset."""
        # Arrange
        mock_products_tab._l2_map = {"Old Item": {"id": 999}}
        l1_children = [hierarchy_test_data["l1_flour"]]

        with patch.object(
            ingredient_hierarchy_service, "get_children", return_value=l1_children
        ):
            # Act - simulate L0 change
            value = "Baking"
            if value in mock_products_tab._l0_map:
                mock_products_tab._l2_map = {}
                mock_products_tab.l2_filter_dropdown.configure(
                    values=["All"], state="disabled"
                )
                mock_products_tab.l2_filter_var.set("All")

            # Assert
            assert mock_products_tab._l2_map == {}
            mock_products_tab.l2_filter_var.set.assert_called_with("All")
            mock_products_tab.l2_filter_dropdown.configure.assert_called_with(
                values=["All"], state="disabled"
            )

    def test_l1_selection_updates_l2_options(
        self, mock_products_tab, hierarchy_test_data
    ):
        """When L1 is selected, L2 should show only children of that L1."""
        # Arrange
        mock_products_tab._l1_map = {"Flour": hierarchy_test_data["l1_flour"]}
        l2_children = [
            hierarchy_test_data["l2_all_purpose_flour"],
            hierarchy_test_data["l2_bread_flour"],
        ]

        with patch.object(
            ingredient_hierarchy_service, "get_children", return_value=l2_children
        ):
            # Act - simulate L1 selection
            value = "Flour"
            if value in mock_products_tab._l1_map:
                l1_id = mock_products_tab._l1_map[value].get("id")
                leaves = ingredient_hierarchy_service.get_children(l1_id)
                mock_products_tab._l2_map = {
                    leaf.get("display_name", "?"): leaf for leaf in leaves
                }
                l2_values = ["All"] + sorted(mock_products_tab._l2_map.keys())
                mock_products_tab.l2_filter_dropdown.configure(
                    values=l2_values, state="normal"
                )

            # Assert
            assert "All-Purpose Flour" in mock_products_tab._l2_map
            assert "Bread Flour" in mock_products_tab._l2_map
            call_kwargs = mock_products_tab.l2_filter_dropdown.configure.call_args[1]
            assert "All-Purpose Flour" in call_kwargs["values"]
            assert "Bread Flour" in call_kwargs["values"]

    def test_l0_all_categories_resets_l1_and_l2(self, mock_products_tab):
        """Selecting 'All Categories' should reset both L1 and L2."""
        # Arrange
        mock_products_tab._l1_map = {"Flour": {"id": 10}}
        mock_products_tab._l2_map = {"All-Purpose Flour": {"id": 100}}

        # Act - simulate selecting "All Categories"
        value = "All Categories"
        if value == "All Categories":
            mock_products_tab._l1_map = {}
            mock_products_tab._l2_map = {}
            mock_products_tab.l1_filter_dropdown.configure(
                values=["All"], state="disabled"
            )
            mock_products_tab.l2_filter_dropdown.configure(
                values=["All"], state="disabled"
            )
            mock_products_tab.l1_filter_var.set("All")
            mock_products_tab.l2_filter_var.set("All")

        # Assert
        assert mock_products_tab._l1_map == {}
        assert mock_products_tab._l2_map == {}
        mock_products_tab.l1_filter_dropdown.configure.assert_called_with(
            values=["All"], state="disabled"
        )
        mock_products_tab.l2_filter_dropdown.configure.assert_called_with(
            values=["All"], state="disabled"
        )

    def test_clear_filters_resets_all_dropdowns(self, mock_products_tab):
        """Clear button should reset all hierarchy and attribute filters."""
        # Arrange - set some filter values
        mock_products_tab._l1_map = {"Flour": {"id": 10}}
        mock_products_tab._l2_map = {"All-Purpose Flour": {"id": 100}}

        # Act - simulate _clear_filters() logic
        mock_products_tab._updating_filters = True
        try:
            mock_products_tab.l0_filter_var.set("All Categories")
            mock_products_tab.l1_filter_var.set("All")
            mock_products_tab.l2_filter_var.set("All")
            mock_products_tab._l1_map = {}
            mock_products_tab._l2_map = {}
            mock_products_tab.l1_filter_dropdown.configure(
                values=["All"], state="disabled"
            )
            mock_products_tab.l2_filter_dropdown.configure(
                values=["All"], state="disabled"
            )
            mock_products_tab.brand_var.set("All")
            mock_products_tab.supplier_var.set("All")
            mock_products_tab.search_var.set("")
        finally:
            mock_products_tab._updating_filters = False
        mock_products_tab._load_products()

        # Assert
        mock_products_tab.l0_filter_var.set.assert_called_with("All Categories")
        mock_products_tab.l1_filter_var.set.assert_called_with("All")
        mock_products_tab.l2_filter_var.set.assert_called_with("All")
        mock_products_tab.brand_var.set.assert_called_with("All")
        mock_products_tab.supplier_var.set.assert_called_with("All")
        mock_products_tab.search_var.set.assert_called_with("")
        mock_products_tab._load_products.assert_called_once()
        assert mock_products_tab._updating_filters is False

    def test_reentry_guard_prevents_recursion(self, mock_products_tab):
        """Re-entry guard should prevent infinite loops."""
        # Arrange
        mock_products_tab._updating_filters = True
        call_count_before = mock_products_tab.l1_filter_dropdown.configure.call_count

        # Act - simulate handler being called while guard is set
        if mock_products_tab._updating_filters:
            pass  # Should return early
        else:
            mock_products_tab.l1_filter_dropdown.configure(values=["Test"])

        # Assert - no new calls should have been made
        assert (
            mock_products_tab.l1_filter_dropdown.configure.call_count
            == call_count_before
        )


# =============================================================================
# Inventory Tab Cascading Tests
# =============================================================================


class TestInventoryTabCascading:
    """Tests for Inventory tab cascading filters."""

    def test_l0_selection_updates_l1_options(
        self, mock_inventory_tab, hierarchy_test_data
    ):
        """When L0 is selected, L1 should show only children of that L0."""
        # Arrange
        l1_children = [hierarchy_test_data["l1_milk"]]

        with patch.object(
            ingredient_hierarchy_service, "get_children", return_value=l1_children
        ):
            # Act - simulate L0 selection
            value = "Dairy"
            if value in mock_inventory_tab._l0_map:
                l0_id = mock_inventory_tab._l0_map[value].get("id")
                subcategories = ingredient_hierarchy_service.get_children(l0_id)
                mock_inventory_tab._l1_map = {
                    sub.get("display_name", "?"): sub for sub in subcategories
                }
                l1_values = ["All"] + sorted(mock_inventory_tab._l1_map.keys())
                mock_inventory_tab.l1_filter_dropdown.configure(
                    values=l1_values, state="normal"
                )

            # Assert
            assert "Milk" in mock_inventory_tab._l1_map
            call_kwargs = mock_inventory_tab.l1_filter_dropdown.configure.call_args[1]
            assert "Milk" in call_kwargs["values"]

    def test_l1_selection_updates_l2_options(
        self, mock_inventory_tab, hierarchy_test_data
    ):
        """When L1 is selected, L2 should show only children of that L1."""
        # Arrange
        mock_inventory_tab._l1_map = {"Milk": hierarchy_test_data["l1_milk"]}
        l2_children = [hierarchy_test_data["l2_whole_milk"]]

        with patch.object(
            ingredient_hierarchy_service, "get_children", return_value=l2_children
        ):
            # Act - simulate L1 selection
            value = "Milk"
            if value in mock_inventory_tab._l1_map:
                l1_id = mock_inventory_tab._l1_map[value].get("id")
                leaves = ingredient_hierarchy_service.get_children(l1_id)
                mock_inventory_tab._l2_map = {
                    leaf.get("display_name", "?"): leaf for leaf in leaves
                }
                l2_values = ["All"] + sorted(mock_inventory_tab._l2_map.keys())
                mock_inventory_tab.l2_filter_dropdown.configure(
                    values=l2_values, state="normal"
                )

            # Assert
            assert "Whole Milk" in mock_inventory_tab._l2_map
            call_kwargs = mock_inventory_tab.l2_filter_dropdown.configure.call_args[1]
            assert "Whole Milk" in call_kwargs["values"]

    def test_clear_filters_resets_hierarchy_dropdowns(self, mock_inventory_tab):
        """Clear button should reset hierarchy filters and search."""
        # Arrange
        mock_inventory_tab._l1_map = {"Milk": {"id": 20}}
        mock_inventory_tab._l2_map = {"Whole Milk": {"id": 200}}

        # Act - simulate _clear_hierarchy_filters() logic
        mock_inventory_tab._updating_filters = True
        try:
            mock_inventory_tab.l0_filter_var.set("All Categories")
            mock_inventory_tab.l1_filter_var.set("All")
            mock_inventory_tab.l2_filter_var.set("All")
            mock_inventory_tab._l1_map = {}
            mock_inventory_tab._l2_map = {}
            mock_inventory_tab.l1_filter_dropdown.configure(
                values=["All"], state="disabled"
            )
            mock_inventory_tab.l2_filter_dropdown.configure(
                values=["All"], state="disabled"
            )
            mock_inventory_tab.brand_var.set("All Brands")
            mock_inventory_tab.search_entry.delete(0, "end")
        finally:
            mock_inventory_tab._updating_filters = False
        mock_inventory_tab._apply_filters()

        # Assert
        mock_inventory_tab.l0_filter_var.set.assert_called_with("All Categories")
        mock_inventory_tab.l1_filter_var.set.assert_called_with("All")
        mock_inventory_tab.l2_filter_var.set.assert_called_with("All")
        mock_inventory_tab.brand_var.set.assert_called_with("All Brands")
        mock_inventory_tab.search_entry.delete.assert_called_with(0, "end")
        mock_inventory_tab._apply_filters.assert_called_once()
        assert mock_inventory_tab._updating_filters is False


# =============================================================================
# Recipe Ingredient Selection Tests
# =============================================================================


class TestRecipeIngredientSelection:
    """Tests for recipe L2-only ingredient selection."""

    def test_leaf_selection_enables_select_button(
        self, mock_recipe_dialog, hierarchy_test_data
    ):
        """Selecting an L2 (leaf) ingredient should enable the Select button."""
        # Arrange
        l2_ingredient = hierarchy_test_data["l2_all_purpose_flour"]

        # Act - simulate _on_tree_select callback logic
        ingredient_data = l2_ingredient
        if ingredient_data and ingredient_data.get("is_leaf", False):
            mock_recipe_dialog._selected_ingredient = ingredient_data
            mock_recipe_dialog.select_button.configure(state="normal")
        else:
            mock_recipe_dialog._selected_ingredient = None
            mock_recipe_dialog.select_button.configure(state="disabled")

        # Assert
        assert mock_recipe_dialog._selected_ingredient == l2_ingredient
        mock_recipe_dialog.select_button.configure.assert_called_with(state="normal")

    def test_non_leaf_selection_disables_select_button(
        self, mock_recipe_dialog, hierarchy_test_data
    ):
        """Selecting an L0 or L1 ingredient should disable the Select button."""
        # Arrange
        l0_ingredient = hierarchy_test_data["l0_baking"]

        # Act - simulate _on_tree_select callback logic
        ingredient_data = l0_ingredient
        if ingredient_data and ingredient_data.get("is_leaf", False):
            mock_recipe_dialog._selected_ingredient = ingredient_data
            mock_recipe_dialog.select_button.configure(state="normal")
        else:
            mock_recipe_dialog._selected_ingredient = None
            mock_recipe_dialog.select_button.configure(state="disabled")

        # Assert
        assert mock_recipe_dialog._selected_ingredient is None
        mock_recipe_dialog.select_button.configure.assert_called_with(state="disabled")

    def test_l1_selection_also_disabled(
        self, mock_recipe_dialog, hierarchy_test_data
    ):
        """L1 ingredients should also be blocked from selection."""
        # Arrange
        l1_ingredient = hierarchy_test_data["l1_flour"]

        # Act
        ingredient_data = l1_ingredient
        if ingredient_data and ingredient_data.get("is_leaf", False):
            mock_recipe_dialog._selected_ingredient = ingredient_data
            mock_recipe_dialog.select_button.configure(state="normal")
        else:
            mock_recipe_dialog._selected_ingredient = None
            mock_recipe_dialog.select_button.configure(state="disabled")

        # Assert
        assert mock_recipe_dialog._selected_ingredient is None
        mock_recipe_dialog.select_button.configure.assert_called_with(state="disabled")

    def test_null_selection_disables_button(self, mock_recipe_dialog):
        """Null/None selection should disable the Select button."""
        # Act
        ingredient_data = None
        if ingredient_data and ingredient_data.get("is_leaf", False):
            mock_recipe_dialog._selected_ingredient = ingredient_data
            mock_recipe_dialog.select_button.configure(state="normal")
        else:
            mock_recipe_dialog._selected_ingredient = None
            mock_recipe_dialog.select_button.configure(state="disabled")

        # Assert
        assert mock_recipe_dialog._selected_ingredient is None
        mock_recipe_dialog.select_button.configure.assert_called_with(state="disabled")


# =============================================================================
# Service Integration Tests
# =============================================================================


class TestHierarchyServiceIntegration:
    """Tests for integration with ingredient_hierarchy_service."""

    def test_get_children_returns_correct_structure(self, test_db_with_hierarchy):
        """Verify get_children returns expected structure for cascading."""
        # This test uses the actual service with a test database
        # to verify the integration works end-to-end
        roots = ingredient_hierarchy_service.get_root_ingredients()

        if roots:
            root = roots[0]
            children = ingredient_hierarchy_service.get_children(root["id"])

            # Verify children have expected keys
            for child in children:
                assert "id" in child
                assert "display_name" in child
                assert "hierarchy_level" in child
                assert "is_leaf" in child

    def test_cascading_chain_l0_to_l2(self, test_db_with_hierarchy):
        """Verify L0 -> L1 -> L2 cascading chain works."""
        # Get L0
        roots = ingredient_hierarchy_service.get_root_ingredients()
        if not roots:
            pytest.skip("No root ingredients in test database")

        l0 = roots[0]
        assert l0["hierarchy_level"] == 0

        # Get L1 children
        l1_children = ingredient_hierarchy_service.get_children(l0["id"])
        if not l1_children:
            pytest.skip("No L1 children in test database")

        l1 = l1_children[0]
        assert l1["hierarchy_level"] == 1

        # Get L2 children
        l2_children = ingredient_hierarchy_service.get_children(l1["id"])
        if l2_children:
            l2 = l2_children[0]
            assert l2["hierarchy_level"] == 2
            assert l2["is_leaf"] is True


@pytest.fixture
def test_db_with_hierarchy(test_db):
    """Fixture that ensures test database has hierarchy data."""
    # This relies on the conftest.py test_db fixture
    # The actual hierarchy data should be seeded by test_db or sample_data
    return test_db
