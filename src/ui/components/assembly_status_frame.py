"""
Assembly Status Frame - Display assembly feasibility status.

Feature 076: Assembly Feasibility & Single-Screen Planning
"""

import customtkinter as ctk
from typing import Optional

from src.services.assembly_feasibility_service import (
    AssemblyFeasibilityResult,
    FGFeasibilityStatus,
)


class AssemblyStatusFrame(ctk.CTkFrame):
    """
    Widget displaying assembly feasibility status.

    Shows overall status indicator, FG counts, and per-FG details.
    Prominent display for single-screen planning integration.
    """

    # Status color definitions
    COLOR_READY = "#2E7D32"  # Green
    COLOR_PARTIAL = "#F57C00"  # Orange
    COLOR_CANNOT = "#C62828"  # Red
    COLOR_AWAITING = "#757575"  # Gray

    def __init__(
        self,
        parent,
        **kwargs,
    ):
        """
        Initialize assembly status frame.

        Args:
            parent: Parent widget
        """
        super().__init__(parent, **kwargs)

        # State
        self._result: Optional[AssemblyFeasibilityResult] = None

        # Build UI
        self._create_widgets()
        self._layout_widgets()

    def _create_widgets(self) -> None:
        """Create internal widgets."""
        # Header frame for status indicator
        self._header_frame = ctk.CTkFrame(self, fg_color="transparent")

        # Section label
        self._title_label = ctk.CTkLabel(
            self._header_frame,
            text="Assembly Status",
            font=ctk.CTkFont(weight="bold", size=16),
            anchor="w",
        )

        # Status indicator label (will be colored)
        self._status_label = ctk.CTkLabel(
            self._header_frame,
            text="Awaiting Decisions",
            font=ctk.CTkFont(weight="bold", size=14),
            text_color=self.COLOR_AWAITING,
            anchor="w",
        )

        # FG count label
        self._count_label = ctk.CTkLabel(
            self._header_frame,
            text="0 of 0 finished goods ready",
            anchor="w",
        )

        # Decision coverage label
        self._coverage_label = ctk.CTkLabel(
            self._header_frame,
            text="Decisions: 0 of 0",
            anchor="w",
            text_color=("gray60", "gray40"),
        )

        # Detail frame (scrollable) for per-FG list
        self._detail_frame = ctk.CTkScrollableFrame(
            self,
            height=100,
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
        self._coverage_label.grid(row=1, column=2, pady=(5, 0), sticky="e")

        # Detail list
        self._detail_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))

    def update_status(self, result: Optional[AssemblyFeasibilityResult]) -> None:
        """
        Update the status display with feasibility results.

        Args:
            result: Result from calculate_assembly_feasibility(), or None to clear
        """
        self._result = result
        self._update_status_indicator()
        self._update_counts()
        self._update_detail_list()

    def _update_status_indicator(self) -> None:
        """Update the status label text and color."""
        if self._result is None:
            status_text = "Awaiting Decisions"
            status_color = self.COLOR_AWAITING
        elif self._result.decided_count == 0:
            status_text = "Awaiting Decisions"
            status_color = self.COLOR_AWAITING
        elif self._result.overall_feasible:
            status_text = "Ready to Assemble"
            status_color = self.COLOR_READY
        else:
            # Check severity
            feasible_count = sum(
                1 for fg in self._result.finished_goods if fg.can_assemble
            )

            if feasible_count == 0:
                status_text = "Cannot Assemble"
                status_color = self.COLOR_CANNOT
            else:
                status_text = "Shortfalls Detected"
                status_color = self.COLOR_PARTIAL

        self._status_label.configure(text=status_text, text_color=status_color)

    def _update_counts(self) -> None:
        """Update the count labels."""
        if self._result is None:
            self._count_label.configure(text="0 of 0 finished goods ready")
            self._coverage_label.configure(text="Decisions: 0 of 0")
            return

        # FG readiness count
        feasible_count = sum(
            1 for fg in self._result.finished_goods if fg.can_assemble
        )
        total_fg_count = len(self._result.finished_goods)

        if total_fg_count == 0:
            self._count_label.configure(text="No finished goods selected")
        else:
            self._count_label.configure(
                text=f"{feasible_count} of {total_fg_count} finished goods ready"
            )

        # Decision coverage
        self._coverage_label.configure(
            text=f"Decisions: {self._result.decided_count} of {self._result.total_fu_count}"
        )

    def _update_detail_list(self) -> None:
        """Update the per-FG detail list."""
        # Clear existing detail widgets
        for widget in self._detail_frame.winfo_children():
            widget.destroy()

        if self._result is None or not self._result.finished_goods:
            # Show placeholder
            placeholder = ctk.CTkLabel(
                self._detail_frame,
                text="No finished goods to display",
                text_color=("gray60", "gray40"),
            )
            placeholder.pack(pady=10)
            return

        # Add row for each FG
        for fg in self._result.finished_goods:
            self._add_fg_row(fg)

    def _add_fg_row(self, fg: FGFeasibilityStatus) -> None:
        """Add a row for one finished good."""
        row_frame = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        row_frame.pack(fill="x", padx=5, pady=2)
        row_frame.grid_columnconfigure(1, weight=1)

        # Status icon
        if fg.can_assemble:
            icon = "✓"
            icon_color = self.COLOR_READY
        else:
            icon = "✗"
            icon_color = self.COLOR_CANNOT

        icon_label = ctk.CTkLabel(
            row_frame,
            text=icon,
            font=ctk.CTkFont(size=14),
            text_color=icon_color,
            width=20,
        )
        icon_label.grid(row=0, column=0, padx=(0, 5))

        # FG name
        name_label = ctk.CTkLabel(
            row_frame,
            text=fg.finished_good_name,
            anchor="w",
        )
        name_label.grid(row=0, column=1, sticky="w")

        # Quantity info
        if fg.can_assemble:
            qty_text = f"Need {fg.quantity_needed}"
            qty_color = ("gray60", "gray40")
        else:
            qty_text = f"Need {fg.quantity_needed}, short {fg.shortfall}"
            qty_color = self.COLOR_CANNOT

        qty_label = ctk.CTkLabel(
            row_frame,
            text=qty_text,
            text_color=qty_color,
            anchor="e",
        )
        qty_label.grid(row=0, column=2, padx=(10, 0))

    def clear(self) -> None:
        """Clear the status display."""
        self.update_status(None)
