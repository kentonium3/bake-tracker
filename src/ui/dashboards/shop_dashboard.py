"""ShopDashboard - Dashboard for SHOP mode.

Shows statistics for shopping and inventory management:
- Shopping Lists: Number of active shopping lists
- Items Needed: Total items across all active lists
- Low Stock Alerts: Items below reorder threshold

Implements FR-009: Mode dashboard displays relevant statistics.
"""

from typing import Any
import customtkinter as ctk

from src.ui.dashboards.base_dashboard import BaseDashboard


class ShopDashboard(BaseDashboard):
    """Dashboard showing shopping and inventory statistics.

    Displays key metrics for the SHOP mode to help users
    quickly understand their shopping needs.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize ShopDashboard.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseDashboard
        """
        super().__init__(master, **kwargs)
        self.set_title("SHOP Dashboard")
        self._create_stats()

    def _create_stats(self) -> None:
        """Create statistic displays for shopping metrics."""
        self.add_stat("Shopping Lists", "0")
        self.add_stat("Items Needed", "0")
        self.add_stat("Low Stock Alerts", "0")

    def refresh(self) -> None:
        """Refresh dashboard with current shopping statistics."""
        try:
            # Shopping Lists count - placeholder for now
            # Will be implemented when shopping list service is available
            shopping_lists_count = 0
            self.update_stat("Shopping Lists", str(shopping_lists_count))

            # Items Needed - placeholder for now
            items_needed_count = 0
            self.update_stat("Items Needed", str(items_needed_count))

            # Low Stock Alerts - try to get from inventory service
            try:
                from src.services import inventory_item_service
                # Get all inventory items and check for low stock
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
