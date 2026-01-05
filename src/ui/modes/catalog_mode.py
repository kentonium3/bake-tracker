"""CatalogMode - Mode container for catalog management.

CATALOG mode contains 6 tabs for managing definitions:
- Ingredients: Base cooking ingredients
- Products: Branded products (bags, packages)
- Recipes: Recipe definitions with ingredients
- Finished Units: Single baked items (1 cookie, 1 brownie)
- Finished Goods: Multi-unit items (box of 12 cookies)
- Packages: Gift packaging definitions

Implements User Story 4: CATALOG Mode for Definitions (Priority P2)
"""

from typing import Any, TYPE_CHECKING
import customtkinter as ctk

from src.ui.base.base_mode import BaseMode
from src.ui.dashboards.catalog_dashboard import CatalogDashboard

if TYPE_CHECKING:
    from src.ui.ingredients_tab import IngredientsTab
    from src.ui.products_tab import ProductsTab
    from src.ui.recipes_tab import RecipesTab
    from src.ui.finished_units_tab import FinishedUnitsTab
    from src.ui.packages_tab import PackagesTab


class CatalogMode(BaseMode):
    """Mode container for catalog management.

    Provides access to all entity definition tabs with a dashboard
    showing entity counts.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize CatalogMode.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseMode
        """
        super().__init__(master, name="CATALOG", **kwargs)

        # Tab references
        self.ingredients_tab: "IngredientsTab" = None
        self.products_tab: "ProductsTab" = None
        self.recipes_tab: "RecipesTab" = None
        self.finished_units_tab: "FinishedUnitsTab" = None
        self.finished_goods_tab = None  # Placeholder
        self.packages_tab: "PackagesTab" = None

        # Set up dashboard and tabs
        self.setup_dashboard()
        self.setup_tabs()

    def setup_dashboard(self) -> None:
        """Set up the CATALOG dashboard with entity counts (FR-007)."""
        dashboard = CatalogDashboard(self)
        self.set_dashboard(dashboard)

    def setup_tabs(self) -> None:
        """Set up all 6 tabs for CATALOG mode (FR-018)."""
        from src.ui.ingredients_tab import IngredientsTab
        from src.ui.products_tab import ProductsTab
        from src.ui.recipes_tab import RecipesTab
        from src.ui.finished_units_tab import FinishedUnitsTab
        from src.ui.packages_tab import PackagesTab

        self.create_tabview()

        # Ingredients tab
        ingredients_frame = self.tabview.add("Ingredients")
        ingredients_frame.grid_columnconfigure(0, weight=1)
        ingredients_frame.grid_rowconfigure(0, weight=1)
        self.ingredients_tab = IngredientsTab(ingredients_frame)
        self._tab_widgets["Ingredients"] = self.ingredients_tab

        # Products tab
        products_frame = self.tabview.add("Products")
        products_frame.grid_columnconfigure(0, weight=1)
        products_frame.grid_rowconfigure(0, weight=1)
        self.products_tab = ProductsTab(products_frame)
        self._tab_widgets["Products"] = self.products_tab

        # Recipes tab
        recipes_frame = self.tabview.add("Recipes")
        recipes_frame.grid_columnconfigure(0, weight=1)
        recipes_frame.grid_rowconfigure(0, weight=1)
        self.recipes_tab = RecipesTab(recipes_frame)
        self._tab_widgets["Recipes"] = self.recipes_tab

        # Finished Units tab
        finished_units_frame = self.tabview.add("Finished Units")
        finished_units_frame.grid_columnconfigure(0, weight=1)
        finished_units_frame.grid_rowconfigure(0, weight=1)
        self.finished_units_tab = FinishedUnitsTab(finished_units_frame)
        self._tab_widgets["Finished Units"] = self.finished_units_tab

        # Finished Goods tab (placeholder for now)
        finished_goods_frame = self.tabview.add("Finished Goods")
        finished_goods_frame.grid_columnconfigure(0, weight=1)
        finished_goods_frame.grid_rowconfigure(0, weight=1)
        self._add_placeholder(finished_goods_frame, "Finished Goods", "Coming Soon")

        # Packages tab
        packages_frame = self.tabview.add("Packages")
        packages_frame.grid_columnconfigure(0, weight=1)
        packages_frame.grid_rowconfigure(0, weight=1)
        self.packages_tab = PackagesTab(packages_frame)
        self._tab_widgets["Packages"] = self.packages_tab

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
        # Lazy load data for all tabs on first activation
        if hasattr(self.ingredients_tab, 'refresh'):
            if not getattr(self.ingredients_tab, '_data_loaded', False):
                self.ingredients_tab._data_loaded = True
                self.after(10, self.ingredients_tab.refresh)

    def refresh_all_tabs(self) -> None:
        """Refresh all tabs in CATALOG mode."""
        if self.ingredients_tab:
            self.ingredients_tab.refresh()
        if self.products_tab:
            self.products_tab.refresh()
        if self.recipes_tab:
            self.recipes_tab.refresh()
        if self.finished_units_tab:
            self.finished_units_tab.refresh()
        if self.packages_tab:
            self.packages_tab.refresh()
