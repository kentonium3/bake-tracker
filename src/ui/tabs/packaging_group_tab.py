"""Packaging group tab with nested sub-tabs.

Feature 055: Groups Finished Units and Packages tabs under single
Packaging group in Catalog mode.

Note: The spec called for separate "Finished Units (Food Only)" and
"Finished Units (Bundles)" sub-tabs, but the current FinishedUnit model
doesn't have a clear bundle vs food distinction. This implementation uses
a single Finished Units tab for now. Filtering can be added when the model
supports it.
"""

import customtkinter as ctk
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.ui.finished_units_tab import FinishedUnitsTab
    from src.ui.packages_tab import PackagesTab


class PackagingGroupTab(ctk.CTkFrame):
    """Container for Finished Units and Packages tabs.

    Provides a nested tabview with:
    - Finished Units: View/manage finished units (yield types)
    - Packages: View/manage package definitions
    """

    def __init__(self, parent: Any, mode: Any = None):
        """Initialize PackagingGroupTab.

        Args:
            parent: Parent widget
            mode: Parent mode (for callbacks)
        """
        super().__init__(parent)
        self.mode = mode

        # Tab references
        self.finished_units_tab: "FinishedUnitsTab" = None
        self.packages_tab: "PackagesTab" = None

        self._create_tabview()

    def _create_tabview(self) -> None:
        """Create nested tabview with sub-tabs."""
        from src.ui.finished_units_tab import FinishedUnitsTab
        from src.ui.packages_tab import PackagesTab

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Add sub-tabs
        # Note: Future enhancement could split Finished Units into
        # "Food Only" and "Bundles" when model supports it
        finished_units_frame = self.tabview.add("Finished Units")
        finished_units_frame.grid_columnconfigure(0, weight=1)
        finished_units_frame.grid_rowconfigure(0, weight=1)
        self.finished_units_tab = FinishedUnitsTab(finished_units_frame)

        packages_frame = self.tabview.add("Packages")
        packages_frame.grid_columnconfigure(0, weight=1)
        packages_frame.grid_rowconfigure(0, weight=1)
        self.packages_tab = PackagesTab(packages_frame)

    def refresh(self) -> None:
        """Refresh all sub-tabs."""
        if self.finished_units_tab:
            self.finished_units_tab.refresh()
        if self.packages_tab:
            self.packages_tab.refresh()
