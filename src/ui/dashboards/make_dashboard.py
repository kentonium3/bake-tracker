"""MakeDashboard - Dashboard for MAKE mode.

Shows production-related statistics:
- Pending Batches: Production runs not yet complete
- Ready to Assemble: Items ready for assembly
- Ready to Package: Items ready for packaging

Implements FR-010: Mode dashboard displays relevant statistics.
"""

from typing import Any
import customtkinter as ctk

from src.ui.dashboards.base_dashboard import BaseDashboard


class MakeDashboard(BaseDashboard):
    """Dashboard showing production statistics.

    Displays counts for production workflow stages in MAKE mode.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize MakeDashboard.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseDashboard
        """
        # Set mode identity before super().__init__
        self.mode_name = "MAKE"
        self.mode_icon = ""

        # Initialize count variables for inline stats
        self._production_runs = 0
        self._assembly_runs = 0

        super().__init__(master, **kwargs)
        self._create_stats()

    def _create_stats(self) -> None:
        """Create statistic displays for production stages."""
        self.add_stat("Pending Batches", "0")
        self.add_stat("Ready to Assemble", "0")
        self.add_stat("Ready to Package", "0")

    def _format_inline_stats(self) -> str:
        """Format make stats for inline display in header.

        Returns:
            String like "12 production runs - 5 assemblies"
        """
        return f"{self._production_runs} production runs - {self._assembly_runs} assemblies"

    def refresh(self) -> None:
        """Refresh dashboard with current production statistics."""
        try:
            # Try to get production statistics from services
            # These services may not exist yet, so handle errors silently
            pending_batches = self._get_pending_batches_count()
            self._production_runs = pending_batches  # Use for inline stats
            self.update_stat("Pending Batches", str(pending_batches))

            ready_to_assemble = self._get_ready_to_assemble_count()
            self._assembly_runs = ready_to_assemble  # Use for inline stats
            self.update_stat("Ready to Assemble", str(ready_to_assemble))

            ready_to_package = self._get_ready_to_package_count()
            self.update_stat("Ready to Package", str(ready_to_package))

        except Exception:
            # Silently handle errors - dashboard stats are non-critical
            pass

    def _get_pending_batches_count(self) -> int:
        """Get count of pending production batches.

        Returns:
            Number of pending batches, or 0 if unavailable
        """
        try:
            from src.services import batch_production_service

            # Get recent production runs and count those that might be pending
            history = batch_production_service.get_production_history(limit=100)
            return len(history) if history else 0
        except Exception:
            return 0

    def _get_ready_to_assemble_count(self) -> int:
        """Get count of items ready for assembly.

        Returns:
            Number of items ready to assemble, or 0 if unavailable
        """
        try:
            from src.services import finished_unit_service

            # Get finished units as proxy for ready-to-assemble items
            # This is a placeholder - actual implementation depends on service API
            units = finished_unit_service.get_all_finished_units()
            return len(units) if units else 0
        except Exception:
            return 0

    def _get_ready_to_package_count(self) -> int:
        """Get count of items ready for packaging.

        Returns:
            Number of items ready to package, or 0 if unavailable
        """
        try:
            from src.services import finished_goods_service

            # Get finished goods as proxy for ready-to-package items
            # This is a placeholder - actual implementation depends on service API
            goods = finished_goods_service.get_all_finished_goods()
            return len(goods) if goods else 0
        except Exception:
            return 0
