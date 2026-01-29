"""
Tests for Planning Tab FG Selection Integration.

F070 WP04: Tests the integration of FGSelectionFrame into the Planning Tab,
including wiring between recipe and FG selection.

F071 WP03: Updated to test quantity specification workflow.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import sys

from src.services.event_service import RemovedFGInfo


# Mock customtkinter before importing the module under test
@pytest.fixture(autouse=True)
def mock_ctk_module():
    """Mock customtkinter module to prevent GUI initialization."""
    mock_ctk = MagicMock()

    # Create a mock base class that doesn't require Tcl/Tk
    class MockCTkFrame:
        def __init__(self, *args, **kwargs):
            self._mock_widgets = {}

        def grid(self, *args, **kwargs):
            pass

        def grid_forget(self):
            pass

        def grid_columnconfigure(self, *args, **kwargs):
            pass

        def grid_rowconfigure(self, *args, **kwargs):
            pass

        def grid_propagate(self, *args, **kwargs):
            pass

        def columnconfigure(self, *args, **kwargs):
            pass

        def rowconfigure(self, *args, **kwargs):
            pass

        def pack(self, *args, **kwargs):
            pass

        def after(self, *args, **kwargs):
            pass

        def cget(self, name):
            return ""

        def configure(self, **kwargs):
            pass

        def winfo_children(self):
            return []

        def destroy(self):
            pass

    mock_ctk.CTkFrame = MockCTkFrame
    mock_ctk.CTkBaseClass = MockCTkFrame
    mock_ctk.CTkButton = MagicMock
    mock_ctk.CTkLabel = MagicMock
    mock_ctk.CTkScrollableFrame = MockCTkFrame
    mock_ctk.CTkCheckBox = MagicMock
    mock_ctk.CTkFont = MagicMock
    mock_ctk.BooleanVar = MagicMock

    modules_to_reset = [
        "customtkinter",
        "src.ui.planning_tab",
        "src.ui.widgets.data_table",
        "src.ui.widgets.batch_options_frame",
        "src.ui.components.shopping_summary_frame",
        "src.ui.components.fg_selection_frame",
        "src.ui.components.recipe_selection_frame",
    ]
    originals = {name: sys.modules.get(name) for name in modules_to_reset}
    for name in modules_to_reset:
        sys.modules.pop(name, None)

    with patch.dict(sys.modules, {"customtkinter": mock_ctk}):
        yield mock_ctk

    for name, module in originals.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


class TestPlanningTabFGIntegration:
    """Tests for FG selection integration in Planning Tab."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for PlanningTab."""
        with patch("src.ui.planning_tab.DataTable") as mock_dt:
            with patch("src.ui.planning_tab.RecipeSelectionFrame") as mock_rsf:
                with patch("src.ui.planning_tab.FGSelectionFrame") as mock_fgsf:
                    with patch("src.ui.planning_tab.session_scope") as mock_scope:
                        with patch("src.ui.planning_tab.event_service") as mock_es:
                            with patch("src.ui.planning_tab.recipe_service") as mock_rs:
                                # Setup default mocks
                                mock_dt.return_value = MagicMock()
                                mock_rsf.return_value = MagicMock()
                                mock_fgsf.return_value = MagicMock()
                                mock_es.get_events_for_planning.return_value = []

                                session = MagicMock()
                                mock_scope.return_value.__enter__ = MagicMock(
                                    return_value=session
                                )
                                mock_scope.return_value.__exit__ = MagicMock(
                                    return_value=False
                                )

                                yield {
                                    "data_table": mock_dt,
                                    "recipe_frame": mock_rsf,
                                    "fg_frame": mock_fgsf,
                                    "session_scope": mock_scope,
                                    "event_service": mock_es,
                                    "recipe_service": mock_rs,
                                    "session": session,
                                }

    def test_fg_selection_frame_created(self, mock_dependencies):
        """FGSelectionFrame is created during initialization."""
        from src.ui.planning_tab import PlanningTab

        parent = MagicMock()
        tab = PlanningTab(parent)

        # Verify FGSelectionFrame was instantiated
        mock_dependencies["fg_frame"].assert_called_once()
        assert hasattr(tab, "_fg_selection_frame")

    def test_fg_frame_hidden_on_refresh(self, mock_dependencies):
        """FG selection frame is hidden when tab is refreshed."""
        from src.ui.planning_tab import PlanningTab

        parent = MagicMock()
        tab = PlanningTab(parent)

        fg_frame_instance = mock_dependencies["fg_frame"].return_value
        fg_frame_instance.grid_forget.reset_mock()

        # Refresh should hide FG frame
        tab.refresh()

        fg_frame_instance.grid_forget.assert_called()

    def test_fg_frame_shown_on_event_select(self, mock_dependencies):
        """FG selection frame is shown when event is selected."""
        from src.ui.planning_tab import PlanningTab

        # Setup event service returns
        mock_event = MagicMock()
        mock_event.id = 1
        mock_event.name = "Test Event"

        mock_dependencies["event_service"].get_event_by_id.return_value = mock_event
        mock_dependencies["event_service"].get_available_finished_goods.return_value = (
            []
        )
        mock_dependencies["event_service"].get_event_finished_good_ids.return_value = []
        mock_dependencies["event_service"].get_event_recipe_ids.return_value = []
        mock_dependencies["recipe_service"].get_all_recipes.return_value = []

        parent = MagicMock()
        tab = PlanningTab(parent)

        fg_frame_instance = mock_dependencies["fg_frame"].return_value

        # Simulate row selection
        tab._on_row_select(mock_event)

        # FG frame should be shown via grid()
        fg_frame_instance.grid.assert_called()

    def test_recipe_save_refreshes_fg_frame(self, mock_dependencies):
        """Saving recipe selection refreshes the FG selection frame."""
        from src.ui.planning_tab import PlanningTab

        mock_dependencies["event_service"].set_event_recipes.return_value = (2, [])
        mock_dependencies["event_service"].get_event_by_id.return_value = MagicMock(
            name="Test"
        )
        mock_dependencies["event_service"].get_available_finished_goods.return_value = (
            []
        )
        mock_dependencies["event_service"].get_event_finished_good_ids.return_value = []

        parent = MagicMock()
        tab = PlanningTab(parent)
        tab._selected_event_id = 1

        fg_frame_instance = mock_dependencies["fg_frame"].return_value
        fg_frame_instance.populate_finished_goods.reset_mock()

        # Save recipe selection
        tab._on_recipe_selection_save([1, 2])

        # FG frame should be refreshed
        fg_frame_instance.populate_finished_goods.assert_called()

    def test_recipe_save_shows_removed_fg_notification(self, mock_dependencies):
        """Saving recipe selection shows notification for removed FGs."""
        from src.ui.planning_tab import PlanningTab

        # Setup removed FG
        removed_fg = RemovedFGInfo(
            fg_id=1, fg_name="Cookie Box", missing_recipes=["Sugar Cookies"]
        )
        mock_dependencies["event_service"].set_event_recipes.return_value = (
            1,
            [removed_fg],
        )
        mock_dependencies["event_service"].get_event_by_id.return_value = MagicMock(
            name="Test"
        )
        mock_dependencies["event_service"].get_available_finished_goods.return_value = (
            []
        )
        mock_dependencies["event_service"].get_event_finished_good_ids.return_value = []

        parent = MagicMock()
        tab = PlanningTab(parent)
        tab._selected_event_id = 1

        # Mock the status label
        tab.status_label = MagicMock()

        # Save recipe selection
        tab._on_recipe_selection_save([1])

        # Status should show removed FG notification
        call_args = tab.status_label.configure.call_args
        text = call_args[1].get("text", "")
        assert "Cookie Box" in text

    def test_fg_selection_save_calls_service(self, mock_dependencies):
        """FG selection save calls event_service.set_event_fg_quantities (F071)."""
        from src.ui.planning_tab import PlanningTab

        mock_dependencies["event_service"].set_event_fg_quantities.return_value = 3

        parent = MagicMock()
        tab = PlanningTab(parent)
        tab._selected_event_id = 1

        # Mock the status label
        tab.status_label = MagicMock()

        # Mock FGSelectionFrame to not have validation errors
        fg_frame_instance = mock_dependencies["fg_frame"].return_value
        fg_frame_instance.has_validation_errors.return_value = False

        # Save FG selection with quantities (F071 format)
        tab._on_fg_selection_save([(1, 10), (2, 20), (3, 30)])

        # Verify service was called with quantities
        mock_dependencies["event_service"].set_event_fg_quantities.assert_called_once()
        call_args = mock_dependencies[
            "event_service"
        ].set_event_fg_quantities.call_args
        assert call_args[0][1] == 1  # event_id
        assert call_args[0][2] == [(1, 10), (2, 20), (3, 30)]  # fg_quantities

    def test_fg_selection_cancel_reverts(self, mock_dependencies):
        """FG selection cancel reverts to original selection with quantities (F071)."""
        from src.ui.planning_tab import PlanningTab

        parent = MagicMock()
        tab = PlanningTab(parent)
        # F071: Original selection now includes quantities
        tab._original_fg_selection = [(1, 10), (2, 20)]

        # Mock the status label
        tab.status_label = MagicMock()

        fg_frame_instance = mock_dependencies["fg_frame"].return_value

        # Cancel
        tab._on_fg_selection_cancel()

        # Frame should be set to original selection with quantities
        fg_frame_instance.set_selected_with_quantities.assert_called_with(
            [(1, 10), (2, 20)]
        )

    def test_original_fg_selection_cleared_on_hide(self, mock_dependencies):
        """Original FG selection is cleared when frame is hidden."""
        from src.ui.planning_tab import PlanningTab

        parent = MagicMock()
        tab = PlanningTab(parent)
        tab._original_fg_selection = [1, 2, 3]

        # Hide FG frame
        tab._hide_fg_selection()

        assert tab._original_fg_selection == []


class TestRemovedFGNotification:
    """Tests for the removed FG notification display."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for PlanningTab."""
        with patch("src.ui.planning_tab.DataTable") as mock_dt:
            with patch("src.ui.planning_tab.RecipeSelectionFrame") as mock_rsf:
                with patch("src.ui.planning_tab.FGSelectionFrame") as mock_fgsf:
                    with patch("src.ui.planning_tab.session_scope") as mock_scope:
                        with patch("src.ui.planning_tab.event_service") as mock_es:
                            with patch("src.ui.planning_tab.recipe_service"):
                                mock_dt.return_value = MagicMock()
                                mock_rsf.return_value = MagicMock()
                                mock_fgsf.return_value = MagicMock()
                                mock_es.get_events_for_planning.return_value = []

                                session = MagicMock()
                                mock_scope.return_value.__enter__ = MagicMock(
                                    return_value=session
                                )
                                mock_scope.return_value.__exit__ = MagicMock(
                                    return_value=False
                                )

                                yield

    def test_single_fg_notification_format(self, mock_dependencies):
        """Single removed FG shows name and missing recipes."""
        from src.ui.planning_tab import PlanningTab

        parent = MagicMock()
        tab = PlanningTab(parent)
        tab.status_label = MagicMock()

        removed_fg = RemovedFGInfo(
            fg_id=1, fg_name="Holiday Box", missing_recipes=["Gingerbread", "Fruitcake"]
        )

        tab._show_removed_fg_notification([removed_fg])

        call_args = tab.status_label.configure.call_args
        text = call_args[1].get("text", "")
        assert "Holiday Box" in text
        assert "Gingerbread" in text
        assert "Fruitcake" in text

    def test_multiple_fg_notification_format(self, mock_dependencies):
        """Multiple removed FGs show count and names."""
        from src.ui.planning_tab import PlanningTab

        parent = MagicMock()
        tab = PlanningTab(parent)
        tab.status_label = MagicMock()

        removed_fgs = [
            RemovedFGInfo(fg_id=1, fg_name="Box A", missing_recipes=["R1"]),
            RemovedFGInfo(fg_id=2, fg_name="Box B", missing_recipes=["R2"]),
        ]

        tab._show_removed_fg_notification(removed_fgs)

        call_args = tab.status_label.configure.call_args
        text = call_args[1].get("text", "")
        assert "2 FGs" in text
        assert "Box A" in text
        assert "Box B" in text
