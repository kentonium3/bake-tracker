"""CatalogMode - Mode container for catalog management.

Feature 055: CATALOG mode restructured into 3 logical groups:
- Ingredients: Ingredient Catalog, Food Products
- Materials: Material Catalog, Material Units, Material Products
- Recipes: Recipes Catalog, Finished Units

Feature 086: Removed Packaging group (Finished Units was redundant with Recipes,
Packages will be refactored into MAKE or Delivery mode).

Implements User Story 4: CATALOG Mode for Definitions (Priority P2)
"""

from typing import Any, TYPE_CHECKING
import customtkinter as ctk

from src.ui.base.base_mode import BaseMode
from src.ui.dashboards.catalog_dashboard import CatalogDashboard

if TYPE_CHECKING:
    from src.ui.tabs.ingredients_group_tab import IngredientsGroupTab
    from src.ui.tabs.recipes_group_tab import RecipesGroupTab
    from src.ui.materials_tab import MaterialsTab


class CatalogMode(BaseMode):
    """Mode container for catalog management.

    Feature 055: Restructured into 3 logical groups with nested tabs:
    - Ingredients group: Ingredient Catalog, Food Products
    - Materials: Material Catalog, Material Units, Material Products
    - Recipes group: Recipes Catalog, Finished Units
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize CatalogMode.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseMode
        """
        super().__init__(master, name="CATALOG", **kwargs)

        # Group tab references (Feature 055)
        self.ingredients_group: "IngredientsGroupTab" = None
        self.materials_tab: "MaterialsTab" = None
        self.recipes_group: "RecipesGroupTab" = None

        # Set up dashboard and tabs
        self.setup_dashboard()
        self.setup_tabs()

    def setup_dashboard(self) -> None:
        """Set up the CATALOG dashboard with entity counts (FR-007)."""
        dashboard = CatalogDashboard(self)
        self.set_dashboard(dashboard)

    def setup_tabs(self) -> None:
        """Set up 3 group tabs for CATALOG mode (Feature 055, updated F086)."""
        from src.ui.tabs.ingredients_group_tab import IngredientsGroupTab
        from src.ui.tabs.recipes_group_tab import RecipesGroupTab
        from src.ui.materials_tab import MaterialsTab

        self.create_tabview()

        # Ingredients group (Ingredient Catalog + Food Products)
        ingredients_frame = self.tabview.add("Ingredients")
        ingredients_frame.grid_columnconfigure(0, weight=1)
        ingredients_frame.grid_rowconfigure(0, weight=1)
        self.ingredients_group = IngredientsGroupTab(ingredients_frame, mode=self)
        self.ingredients_group.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets["Ingredients"] = self.ingredients_group

        # Materials tab (existing - already has internal sub-tabs)
        materials_frame = self.tabview.add("Materials")
        materials_frame.grid_columnconfigure(0, weight=1)
        materials_frame.grid_rowconfigure(0, weight=1)
        self.materials_tab = MaterialsTab(materials_frame)
        self._tab_widgets["Materials"] = self.materials_tab

        # Recipes group (Recipes Catalog + Finished Units)
        recipes_frame = self.tabview.add("Recipes")
        recipes_frame.grid_columnconfigure(0, weight=1)
        recipes_frame.grid_rowconfigure(0, weight=1)
        self.recipes_group = RecipesGroupTab(recipes_frame, mode=self)
        self.recipes_group.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets["Recipes"] = self.recipes_group

    def _add_placeholder(self, frame: ctk.CTkFrame, title: str, message: str) -> None:
        """Add a placeholder message to a frame.

        Args:
            frame: Frame to add placeholder to
            title: Placeholder title
            message: Placeholder message
        """
        label = ctk.CTkLabel(
            frame,
            text=f"{title}\n\n{message}",
            font=ctk.CTkFont(size=20),
        )
        label.grid(row=0, column=0, padx=20, pady=20)

    def activate(self) -> None:
        """Called when CATALOG mode becomes active."""
        super().activate()
        # Feature 055: Lazy load data for group tabs on first activation
        if self.ingredients_group:
            if not getattr(self.ingredients_group, "_data_loaded", False):
                self.ingredients_group._data_loaded = True
                self.after(10, self.ingredients_group.refresh)
        if self.materials_tab:
            if not getattr(self.materials_tab, "_data_loaded", False):
                self.materials_tab._data_loaded = True
                self.after(20, self.materials_tab.refresh)
        if self.recipes_group:
            if not getattr(self.recipes_group, "_data_loaded", False):
                self.recipes_group._data_loaded = True
                self.after(30, self.recipes_group.refresh)

    def refresh_all_tabs(self) -> None:
        """Refresh all group tabs in CATALOG mode (Feature 055)."""
        if self.ingredients_group:
            self.ingredients_group.refresh()
        if self.materials_tab:
            self.materials_tab.refresh()
        if self.recipes_group:
            self.recipes_group.refresh()
