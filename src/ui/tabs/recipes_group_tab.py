"""Recipes group tab with nested sub-tabs.

Feature 055: Groups Recipes Catalog and Finished Units tabs under single
Recipes group in Catalog mode.

Feature 088: Added Finished Goods tab for managing package assemblies.
"""

import customtkinter as ctk
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.ui.recipes_tab import RecipesTab
    from src.ui.finished_units_tab import FinishedUnitsTab
    from src.ui.finished_goods_tab import FinishedGoodsTab


class RecipesGroupTab(ctk.CTkFrame):
    """Container for Recipes, Finished Units, and Finished Goods tabs.

    Provides a nested tabview with:
    - Recipes Catalog: View/manage recipe definitions
    - Finished Units: View/manage single baked items
    - Finished Goods: View/manage assembled packages (gift boxes, variety packs)
    """

    def __init__(self, parent: Any, mode: Any = None):
        """Initialize RecipesGroupTab.

        Args:
            parent: Parent widget
            mode: Parent mode (for callbacks)
        """
        super().__init__(parent)
        self.mode = mode

        # Tab references
        self.recipes_tab: "RecipesTab" = None
        self.finished_units_tab: "FinishedUnitsTab" = None
        self.finished_goods_tab: "FinishedGoodsTab" = None

        self._create_tabview()

    def _create_tabview(self) -> None:
        """Create nested tabview with sub-tabs."""
        from src.ui.recipes_tab import RecipesTab
        from src.ui.finished_units_tab import FinishedUnitsTab
        from src.ui.finished_goods_tab import FinishedGoodsTab

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Add sub-tabs
        recipes_frame = self.tabview.add("Recipes Catalog")
        recipes_frame.grid_columnconfigure(0, weight=1)
        recipes_frame.grid_rowconfigure(0, weight=1)
        self.recipes_tab = RecipesTab(recipes_frame)

        units_frame = self.tabview.add("Finished Units")
        units_frame.grid_columnconfigure(0, weight=1)
        units_frame.grid_rowconfigure(0, weight=1)
        self.finished_units_tab = FinishedUnitsTab(units_frame)

        # Feature 088: Add Finished Goods tab for assembled packages
        goods_frame = self.tabview.add("Finished Goods")
        goods_frame.grid_columnconfigure(0, weight=1)
        goods_frame.grid_rowconfigure(0, weight=1)
        self.finished_goods_tab = FinishedGoodsTab(goods_frame)

    def refresh(self) -> None:
        """Refresh all sub-tabs."""
        if self.recipes_tab:
            self.recipes_tab.refresh()
        if self.finished_units_tab:
            self.finished_units_tab.refresh()
        if self.finished_goods_tab:
            self.finished_goods_tab.refresh()
