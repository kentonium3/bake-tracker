"""Packaging group tab with nested sub-tabs.

Feature 055: Groups Finished Goods and Packages tabs under single
Packaging group in Catalog mode.

Note: The spec called for separate "Finished Goods (Food Only)" and
"Finished Goods (Bundles)" sub-tabs, but the current FinishedGood model
doesn't have a clear bundle vs food distinction. This implementation uses
a single Finished Goods tab for now. Filtering can be added when the model
supports it.
"""

import customtkinter as ctk
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.ui.finished_goods_tab import FinishedGoodsTab
    from src.ui.packages_tab import PackagesTab


class PackagingGroupTab(ctk.CTkFrame):
    """Container for Finished Goods and Packages tabs.

    Provides a nested tabview with:
    - Finished Goods: View/manage assembled packages
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
        self.finished_goods_tab: "FinishedGoodsTab" = None
        self.packages_tab: "PackagesTab" = None

        self._create_tabview()

    def _create_tabview(self) -> None:
        """Create nested tabview with sub-tabs."""
        from src.ui.finished_goods_tab import FinishedGoodsTab
        from src.ui.packages_tab import PackagesTab

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Add sub-tabs
        # Note: Future enhancement could split Finished Goods into
        # "Food Only" and "Bundles" when model supports it
        finished_goods_frame = self.tabview.add("Finished Goods")
        finished_goods_frame.grid_columnconfigure(0, weight=1)
        finished_goods_frame.grid_rowconfigure(0, weight=1)
        self.finished_goods_tab = FinishedGoodsTab(finished_goods_frame)

        packages_frame = self.tabview.add("Packages")
        packages_frame.grid_columnconfigure(0, weight=1)
        packages_frame.grid_rowconfigure(0, weight=1)
        self.packages_tab = PackagesTab(packages_frame)

    def refresh(self) -> None:
        """Refresh all sub-tabs."""
        if self.finished_goods_tab:
            self.finished_goods_tab.refresh()
        if self.packages_tab:
            self.packages_tab.refresh()
