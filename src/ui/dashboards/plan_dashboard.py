"""PlanDashboard - Dashboard for PLAN mode.

Shows upcoming events and planning stats:
- Upcoming events count
- Next event date
- Events needing attention

Implements FR-008: Mode dashboard displays relevant statistics.
"""

from typing import Any
import customtkinter as ctk

from src.ui.dashboards.base_dashboard import BaseDashboard


class PlanDashboard(BaseDashboard):
    """Dashboard showing upcoming events and planning stats.

    Displays event counts and highlights events needing attention.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize PlanDashboard.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseDashboard
        """
        # Set mode identity before super().__init__
        self.mode_name = "PLAN"
        self.mode_icon = ""

        # Initialize count variables for inline stats
        self._event_count = 0
        self._package_count = 0

        super().__init__(master, **kwargs)
        self._create_stats()

    def _create_stats(self) -> None:
        """Create statistic displays for planning data."""
        self.add_stat("Upcoming Events", "0")
        self.add_stat("Next Event", "N/A")
        self.add_stat("Need Attention", "0")

    def _format_inline_stats(self) -> str:
        """Format plan stats for inline display in header.

        Returns:
            String like "5 events - 12 packages"
        """
        return f"{self._event_count} events - {self._package_count} packages"

    def refresh(self) -> None:
        """Refresh dashboard with current event data."""
        try:
            from src.services.event_service import get_all_events
            from src.services.package_service import get_all_packages
            from datetime import date

            events = get_all_events()
            self._event_count = len(events) if events else 0

            # Get package count for inline stats
            try:
                packages = get_all_packages()
                self._package_count = len(packages) if packages else 0
            except Exception:
                self._package_count = 0

            if not events:
                self.update_stat("Upcoming Events", "0")
                self.update_stat("Next Event", "N/A")
                self.update_stat("Need Attention", "0")
                return

            # Filter upcoming events (event_date >= today)
            today = date.today()
            upcoming = [e for e in events if e.event_date and e.event_date >= today]

            self.update_stat("Upcoming Events", str(len(upcoming)))

            # Find next event
            if upcoming:
                upcoming_sorted = sorted(upcoming, key=lambda e: e.event_date)
                next_event = upcoming_sorted[0]
                days_until = (next_event.event_date - today).days
                if days_until == 0:
                    next_text = "Today"
                elif days_until == 1:
                    next_text = "Tomorrow"
                else:
                    next_text = f"In {days_until} days"
                self.update_stat("Next Event", next_text)
            else:
                self.update_stat("Next Event", "N/A")

            # Events needing attention (placeholder logic - events without targets)
            # For now, just count events happening soon (within 7 days)
            attention_count = len([e for e in upcoming
                                   if e.event_date and (e.event_date - today).days <= 7])
            self.update_stat("Need Attention", str(attention_count))

        except Exception:
            # Silently handle errors - dashboard stats are non-critical
            pass
