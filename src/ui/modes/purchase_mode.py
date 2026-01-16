"""PurchaseMode - Mode container for shopping and inventory management.

PURCHASE mode contains 3 tabs for managing purchases and inventory (F055 workflow order):
- Inventory: View and manage current inventory levels
- Purchases: Track purchases from suppliers
- Shopping Lists: Create and manage shopping lists

Implements User Story 6: PURCHASE Mode for Inventory Management (Priority P2)
"""

from typing import Any, TYPE_CHECKING
import customtkinter as ctk

from src.ui.base.base_mode import BaseMode
from src.ui.dashboards.purchase_dashboard import PurchaseDashboard
from src.ui.tabs.shopping_lists_tab import ShoppingListsTab
from src.ui.tabs.purchases_tab import PurchasesTab

if TYPE_CHECKING:
    from src.ui.inventory_tab import InventoryTab


class PurchaseMode(BaseMode):
    """Mode container for shopping and inventory management.

    Provides access to shopping lists, purchase tracking, and
    inventory management with a dashboard showing shopping stats.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize PurchaseMode.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseMode
        """
        super().__init__(master, name="PURCHASE", **kwargs)

        # Tab references
        self.shopping_lists_tab: ShoppingListsTab = None
        self.purchases_tab: PurchasesTab = None
        self.inventory_tab: "InventoryTab" = None

        # Set up dashboard and tabs
        self.setup_dashboard()
        self.setup_tabs()

    def setup_dashboard(self) -> None:
        """Set up the PURCHASE dashboard with shopping statistics (FR-009)."""
        dashboard = PurchaseDashboard(self)
        self.set_dashboard(dashboard)

    def setup_tabs(self) -> None:
        """Set up all 3 tabs for PURCHASE mode (F055 workflow order)."""
        from src.ui.inventory_tab import InventoryTab

        self.create_tabview()

        # Inventory tab - First: check what you have
        inventory_frame = self.tabview.add("Inventory")
        inventory_frame.grid_columnconfigure(0, weight=1)
        inventory_frame.grid_rowconfigure(0, weight=1)
        self.inventory_tab = InventoryTab(inventory_frame)
        self._tab_widgets["Inventory"] = self.inventory_tab

        # Purchases tab - Second: record purchases
        purchases_frame = self.tabview.add("Purchases")
        purchases_frame.grid_columnconfigure(0, weight=1)
        purchases_frame.grid_rowconfigure(0, weight=1)
        self.purchases_tab = PurchasesTab(purchases_frame)
        self.purchases_tab.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets["Purchases"] = self.purchases_tab

        # Shopping Lists tab - Third: plan what to buy
        shopping_lists_frame = self.tabview.add("Shopping Lists")
        shopping_lists_frame.grid_columnconfigure(0, weight=1)
        shopping_lists_frame.grid_rowconfigure(0, weight=1)
        self.shopping_lists_tab = ShoppingListsTab(shopping_lists_frame)
        self.shopping_lists_tab.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets["Shopping Lists"] = self.shopping_lists_tab

    def activate(self) -> None:
        """Called when PURCHASE mode becomes active."""
        super().activate()
        # Lazy load inventory data on first activation
        if self.inventory_tab:
            if not getattr(self.inventory_tab, '_data_loaded', False):
                self.inventory_tab._data_loaded = True
                self.after(10, self.inventory_tab.refresh)
        # Lazy load purchases data on first activation
        if self.purchases_tab:
            if not getattr(self.purchases_tab, '_data_loaded', False):
                self.after(20, self.purchases_tab.refresh)

    def refresh_all_tabs(self) -> None:
        """Refresh all tabs in PURCHASE mode."""
        # Shopping lists and purchases tabs have no data to refresh yet
        if self.shopping_lists_tab:
            self.shopping_lists_tab.refresh()
        if self.purchases_tab:
            self.purchases_tab.refresh()
        if self.inventory_tab:
            self.inventory_tab.refresh()
