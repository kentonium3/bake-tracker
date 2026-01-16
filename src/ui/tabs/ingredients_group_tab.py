"""Ingredients group tab with nested sub-tabs.

Feature 055: Groups Ingredient Catalog and Food Products tabs under single
Ingredients group in Catalog mode.
"""

import customtkinter as ctk
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.ui.ingredients_tab import IngredientsTab
    from src.ui.products_tab import ProductsTab


class IngredientsGroupTab(ctk.CTkFrame):
    """Container for Ingredients and Products tabs.

    Provides a nested tabview with:
    - Ingredient Catalog: View/manage ingredient definitions
    - Food Products: View/manage products linked to ingredients
    """

    def __init__(self, parent: Any, mode: Any = None):
        """Initialize IngredientsGroupTab.

        Args:
            parent: Parent widget
            mode: Parent mode (for callbacks)
        """
        super().__init__(parent)
        self.mode = mode

        # Tab references
        self.ingredients_tab: "IngredientsTab" = None
        self.products_tab: "ProductsTab" = None

        self._create_tabview()

    def _create_tabview(self) -> None:
        """Create nested tabview with sub-tabs."""
        from src.ui.ingredients_tab import IngredientsTab
        from src.ui.products_tab import ProductsTab

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Add sub-tabs
        ingredient_frame = self.tabview.add("Ingredient Catalog")
        ingredient_frame.grid_columnconfigure(0, weight=1)
        ingredient_frame.grid_rowconfigure(0, weight=1)
        self.ingredients_tab = IngredientsTab(ingredient_frame)

        product_frame = self.tabview.add("Food Products")
        product_frame.grid_columnconfigure(0, weight=1)
        product_frame.grid_rowconfigure(0, weight=1)
        self.products_tab = ProductsTab(product_frame)

    def refresh(self) -> None:
        """Refresh all sub-tabs."""
        if self.ingredients_tab:
            self.ingredients_tab.refresh()
        if self.products_tab:
            self.products_tab.refresh()
