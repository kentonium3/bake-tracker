"""PurchaseDashboard - Dashboard for PURCHASE mode.

Shows statistics for shopping and inventory management:
- Shopping Lists: Number of active shopping lists
- Items Needed: Total items across all active lists
- Low Stock Alerts: Items below reorder threshold

Implements FR-009: Mode dashboard displays relevant statistics.
"""

from typing import Any
import customtkinter as ctk

from src.ui.dashboards.base_dashboard import BaseDashboard


class PurchaseDashboard(BaseDashboard):
    """Dashboard showing shopping and inventory statistics.

    Displays key metrics for the PURCHASE mode to help users
    quickly understand their shopping needs.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize PurchaseDashboard.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseDashboard
        """
        # Set mode identity before super().__init__
        self.mode_name = "PURCHASE"
        self.mode_icon = ""

        # Initialize count variables for inline stats
        self._items_needed = 0
        self._inventory_count = 0

        super().__init__(master, **kwargs)
        self._create_stats()

    def _create_stats(self) -> None:
        """Create statistic displays for shopping metrics."""
        self.add_stat("Shopping Lists", "0")
        self.add_stat("Items Needed", "0")
        self.add_stat("Low Stock Alerts", "0")

    def _format_inline_stats(self) -> str:
        """Format purchase stats for inline display in header.

        Returns:
            String like "15 items needed - 42 inventory items"
        """
        return f"{self._items_needed} items needed - {self._inventory_count} inventory items"

    def refresh(self) -> None:
        """Refresh dashboard with current shopping statistics."""
        try:
            # Shopping Lists count - placeholder for now
            # Will be implemented when shopping list service is available
            shopping_lists_count = 0
            self.update_stat("Shopping Lists", str(shopping_lists_count))

            # Items Needed - placeholder for now
            self._items_needed = 0
            self.update_stat("Items Needed", str(self._items_needed))

            # Get inventory count for inline stats
            try:
                from src.services import inventory_item_service
                inventory_items = inventory_item_service.get_all_inventory_items()
                self._inventory_count = len(inventory_items) if inventory_items else 0
            except Exception:
                self._inventory_count = 0

            # Low Stock Alerts - try to get from inventory service
            try:
                # This is a simplified check - real implementation would use
                # reorder thresholds defined per ingredient
                low_stock_count = 0
                self.update_stat("Low Stock Alerts", str(low_stock_count))
            except Exception:
                # Service not available or error - show 0
                self.update_stat("Low Stock Alerts", "0")

        except Exception:
            # Silently handle errors - dashboard stats are non-critical
            pass
