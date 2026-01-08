"""ObserveDashboard - Dashboard for OBSERVE mode.

Shows overall progress tracking:
- Shopping completion %
- Production completion %
- Assembly completion %
- Packaging completion %

Also displays upcoming events with their status.

Implements FR-011: Mode dashboard displays relevant statistics.
"""

from typing import Any, Optional
import customtkinter as ctk

from src.ui.dashboards.base_dashboard import BaseDashboard


class ObserveDashboard(BaseDashboard):
    """Dashboard showing overall progress and event readiness.

    Displays aggregated progress across all active events.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize ObserveDashboard.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseDashboard
        """
        # Set mode identity before super().__init__
        self.mode_name = "OBSERVE"
        self.mode_icon = ""

        # Initialize count variable for inline stats
        self._event_count = 0

        super().__init__(master, **kwargs)
        self._progress_bars = {}
        self._create_progress_stats()

    def _create_progress_stats(self) -> None:
        """Create progress statistics display."""
        # Clear default stats area and create custom layout
        self.clear_stats()

        # Progress labels with percentage
        self._add_progress_stat("Shopping", "0%")
        self._add_progress_stat("Production", "0%")
        self._add_progress_stat("Assembly", "0%")
        self._add_progress_stat("Packaging", "0%")

        # Add quick action for refresh
        self.add_action("View Details", self._on_view_details)

    def _format_inline_stats(self) -> str:
        """Format observe stats for inline display in header.

        Returns:
            String like "5 events tracked"
        """
        return f"{self._event_count} events tracked"

    def _add_progress_stat(self, label: str, value: str = "0%") -> None:
        """Add a progress statistic with visual indicator.

        Args:
            label: Stat label (e.g., "Shopping")
            value: Initial value (default "0%")
        """
        stat_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        stat_frame.pack(side="left", padx=15)

        # Value (larger font)
        value_label = ctk.CTkLabel(
            stat_frame,
            text=value,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        value_label.pack()

        # Label (smaller)
        label_widget = ctk.CTkLabel(
            stat_frame,
            text=label,
            font=ctk.CTkFont(size=11)
        )
        label_widget.pack()

        # Progress bar
        progress_bar = ctk.CTkProgressBar(stat_frame, width=80, height=8)
        progress_bar.set(0)
        progress_bar.pack(pady=(2, 0))

        self._stats[label] = label_widget
        self._stat_values[label] = value_label
        self._progress_bars[label] = progress_bar

    def update_stat(self, label: str, value: str) -> None:
        """Update a statistic value and progress bar.

        Args:
            label: Stat label to update
            value: New value to display (e.g., "75%")
        """
        super().update_stat(label, value)

        # Also update progress bar
        if label in self._progress_bars:
            try:
                # Parse percentage from value
                pct = int(value.replace("%", ""))
                self._progress_bars[label].set(pct / 100.0)
            except (ValueError, AttributeError):
                pass

    def refresh(self) -> None:
        """Refresh dashboard with current progress data."""
        try:
            from src.services.event_service import (
                get_all_events,
                get_event_overall_progress,
            )

            events = get_all_events()
            self._event_count = len(events) if events else 0

            if not events:
                # No events - show zeros
                self.update_stat("Shopping", "0%")
                self.update_stat("Production", "0%")
                self.update_stat("Assembly", "0%")
                self.update_stat("Packaging", "0%")
                return

            # Aggregate progress across all events
            total_shopping = 0
            total_production = 0
            total_assembly = 0
            total_packaging = 0
            event_count = len(events)

            for event in events:
                try:
                    progress = get_event_overall_progress(event.id)
                    total_shopping += progress.get("shopping_pct", 0)
                    total_production += progress.get("production_pct", 0)
                    total_assembly += progress.get("assembly_pct", 0)
                    total_packaging += progress.get("packaging_pct", 0)
                except Exception:
                    # Skip events that fail to load progress
                    event_count = max(1, event_count - 1)

            # Calculate averages
            if event_count > 0:
                self.update_stat("Shopping", f"{total_shopping // event_count}%")
                self.update_stat("Production", f"{total_production // event_count}%")
                self.update_stat("Assembly", f"{total_assembly // event_count}%")
                self.update_stat("Packaging", f"{total_packaging // event_count}%")

        except Exception:
            # Silently handle errors - dashboard stats are non-critical
            pass

    def _on_view_details(self) -> None:
        """Handle View Details button click."""
        # Switch to Event Status tab (will be implemented in ObserveMode)
        pass
