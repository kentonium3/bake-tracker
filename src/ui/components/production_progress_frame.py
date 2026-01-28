"""
Production Progress Frame - Display production progress status.

Feature 079: Production-Aware Planning Calculations
Work Package: WP05 - UI Progress Display

Provides a frame that displays production progress for all recipe targets
with remaining batches, overage indicators, and lock icons for recipes
that have production records.
"""

import customtkinter as ctk
from typing import List, Optional

from src.services.planning.progress import ProductionProgress


class ProductionProgressFrame(ctk.CTkFrame):
    """
    Widget displaying production progress status.

    Shows progress for each recipe target with remaining/overage indicators
    and lock icons for recipes with production records.
    """

    # Status color definitions
    COLOR_COMPLETE = "#2E7D32"  # Green
    COLOR_IN_PROGRESS = "#F57C00"  # Orange
    COLOR_OVERAGE = "#1565C0"  # Blue for overage (informational)
    COLOR_NOT_STARTED = "#757575"  # Gray
    COLOR_LOCKED = "#9E9E9E"  # Gray for locked indicator

    def __init__(
        self,
        parent,
        **kwargs,
    ):
        """
        Initialize production progress frame.

        Args:
            parent: Parent widget
        """
        super().__init__(parent, **kwargs)

        # State
        self._progress_list: List[ProductionProgress] = []

        # Build UI
        self._create_widgets()
        self._layout_widgets()

    def _create_widgets(self) -> None:
        """Create internal widgets."""
        # Header frame
        self._header_frame = ctk.CTkFrame(self, fg_color="transparent")

        # Section label
        self._title_label = ctk.CTkLabel(
            self._header_frame,
            text="Production Progress",
            font=ctk.CTkFont(weight="bold", size=16),
            anchor="w",
        )

        # Overall status label
        self._status_label = ctk.CTkLabel(
            self._header_frame,
            text="No targets",
            font=ctk.CTkFont(weight="bold", size=14),
            text_color=self.COLOR_NOT_STARTED,
            anchor="w",
        )

        # Count label
        self._count_label = ctk.CTkLabel(
            self._header_frame,
            text="0 of 0 recipes complete",
            anchor="w",
        )

        # Detail frame (scrollable) for per-recipe list
        self._detail_frame = ctk.CTkScrollableFrame(
            self,
            height=120,
            fg_color=("gray95", "gray15"),
        )

    def _layout_widgets(self) -> None:
        """Position widgets using grid layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Detail list

        # Header layout
        self._header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self._header_frame.grid_columnconfigure(1, weight=1)

        self._title_label.grid(row=0, column=0, padx=(0, 20), sticky="w")
        self._status_label.grid(row=0, column=1, sticky="w")
        self._count_label.grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky="w")

        # Detail list
        self._detail_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))

    def update_progress(self, progress_list: Optional[List[ProductionProgress]]) -> None:
        """
        Update the progress display with production progress data.

        Args:
            progress_list: List of ProductionProgress DTOs, or None to clear
        """
        self._progress_list = progress_list or []
        self._update_status_indicator()
        self._update_counts()
        self._update_detail_list()

    def _update_status_indicator(self) -> None:
        """Update the status label text and color."""
        if not self._progress_list:
            status_text = "No targets"
            status_color = self.COLOR_NOT_STARTED
        else:
            complete_count = sum(1 for p in self._progress_list if p.is_complete)
            total_count = len(self._progress_list)
            has_overage = any(p.overage_batches > 0 for p in self._progress_list)

            if complete_count == total_count:
                if has_overage:
                    status_text = "Complete (with overage)"
                    status_color = self.COLOR_OVERAGE
                else:
                    status_text = "All Complete"
                    status_color = self.COLOR_COMPLETE
            elif complete_count > 0:
                status_text = "In Progress"
                status_color = self.COLOR_IN_PROGRESS
            else:
                status_text = "Not Started"
                status_color = self.COLOR_NOT_STARTED

        self._status_label.configure(text=status_text, text_color=status_color)

    def _update_counts(self) -> None:
        """Update the count labels."""
        if not self._progress_list:
            self._count_label.configure(text="No production targets")
            return

        complete_count = sum(1 for p in self._progress_list if p.is_complete)
        total_count = len(self._progress_list)

        self._count_label.configure(
            text=f"{complete_count} of {total_count} recipes complete"
        )

    def _update_detail_list(self) -> None:
        """Update the per-recipe detail list."""
        # Clear existing detail widgets
        for widget in self._detail_frame.winfo_children():
            widget.destroy()

        if not self._progress_list:
            # Show placeholder
            placeholder = ctk.CTkLabel(
                self._detail_frame,
                text="No production targets to display",
                text_color=("gray60", "gray40"),
            )
            placeholder.pack(pady=10)
            return

        # Add row for each recipe
        for progress in self._progress_list:
            self._add_progress_row(progress)

    def _add_progress_row(self, progress: ProductionProgress) -> None:
        """Add a row for one recipe's progress."""
        row_frame = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        row_frame.pack(fill="x", padx=5, pady=2)
        row_frame.grid_columnconfigure(1, weight=1)

        # Lock icon if has production (completed_batches > 0)
        if progress.completed_batches > 0:
            lock_label = ctk.CTkLabel(
                row_frame,
                text="\U0001F512",  # Lock emoji
                font=ctk.CTkFont(size=12),
                text_color=self.COLOR_LOCKED,
                width=20,
            )
            lock_label.grid(row=0, column=0, padx=(0, 3))
            col_offset = 1
        else:
            col_offset = 0

        # Status icon
        if progress.is_complete:
            if progress.overage_batches > 0:
                icon = "\u2713"  # Checkmark
                icon_color = self.COLOR_OVERAGE
            else:
                icon = "\u2713"  # Checkmark
                icon_color = self.COLOR_COMPLETE
        elif progress.completed_batches > 0:
            icon = "\u25CF"  # Filled circle (in progress)
            icon_color = self.COLOR_IN_PROGRESS
        else:
            icon = "\u25CB"  # Empty circle (not started)
            icon_color = self.COLOR_NOT_STARTED

        icon_label = ctk.CTkLabel(
            row_frame,
            text=icon,
            font=ctk.CTkFont(size=14),
            text_color=icon_color,
            width=20,
        )
        icon_label.grid(row=0, column=col_offset, padx=(0, 5))

        # Recipe name
        name_label = ctk.CTkLabel(
            row_frame,
            text=progress.recipe_name,
            anchor="w",
        )
        name_label.grid(row=0, column=col_offset + 1, sticky="w")

        # Progress text: "X of Y (Z remaining)" or "X of Y (+N overage)"
        progress_text = self._format_progress_text(progress)
        progress_color = self._get_progress_color(progress)

        progress_label = ctk.CTkLabel(
            row_frame,
            text=progress_text,
            text_color=progress_color,
            anchor="e",
        )
        progress_label.grid(row=0, column=col_offset + 2, padx=(10, 0))

    def _format_progress_text(self, progress: ProductionProgress) -> str:
        """
        Format progress text according to WP05 requirements.

        T018: "X of Y (Z remaining)" format
        T019: "+N overage" when completed > target
        """
        base = f"{progress.completed_batches} of {progress.target_batches}"

        if progress.overage_batches > 0:
            # T019: Overage indicator
            return f"{base} (+{progress.overage_batches} overage)"
        elif progress.remaining_batches > 0:
            # T018: Remaining batches
            return f"{base} ({progress.remaining_batches} remaining)"
        else:
            # Complete with no overage
            return f"{base} (complete)"

    def _get_progress_color(self, progress: ProductionProgress) -> str:
        """Get the color for progress text based on status."""
        if progress.overage_batches > 0:
            return self.COLOR_OVERAGE
        elif progress.is_complete:
            return self.COLOR_COMPLETE
        elif progress.completed_batches > 0:
            return self.COLOR_IN_PROGRESS
        else:
            return ("gray60", "gray40")

    def clear(self) -> None:
        """Clear the progress display."""
        self.update_progress(None)

    def get_recipes_with_production(self) -> set:
        """
        Get set of recipe IDs that have production records.

        Used by planning_tab to determine which recipes are locked.

        Returns:
            Set of recipe_ids that have completed_batches > 0
        """
        return {
            p.recipe_id for p in self._progress_list if p.completed_batches > 0
        }
