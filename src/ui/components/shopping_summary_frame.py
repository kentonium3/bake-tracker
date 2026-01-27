"""
Shopping Summary Frame - Compact display of shopping list status.

Feature 076: Assembly Feasibility & Single-Screen Planning
"""

import customtkinter as ctk
from typing import Optional

from src.services.inventory_gap_service import GapAnalysisResult


class ShoppingSummaryFrame(ctk.CTkFrame):
    """
    Compact widget displaying shopping list summary.

    Shows count of items needing purchase vs items already sufficient.
    Designed for single-screen planning layout integration.
    """

    def __init__(
        self,
        parent,
        height: int = 50,
        **kwargs,
    ):
        """
        Initialize shopping summary frame.

        Args:
            parent: Parent widget
            height: Fixed height in pixels (default 50)
        """
        kwargs.setdefault("height", height)
        kwargs.setdefault("fg_color", ("gray90", "gray20"))
        kwargs.setdefault("corner_radius", 8)

        super().__init__(parent, **kwargs)

        self._purchase_count: int = 0
        self._sufficient_count: int = 0

        self._create_widgets()
        self._layout_widgets()

    def _create_widgets(self) -> None:
        """Create internal widgets."""
        self._label = ctk.CTkLabel(
            self,
            text="Shopping List",
            font=ctk.CTkFont(weight="bold", size=14),
            anchor="w",
        )

        self._purchase_label = ctk.CTkLabel(
            self,
            text="0 items to purchase",
            text_color="orange",
            anchor="w",
        )

        self._sufficient_label = ctk.CTkLabel(
            self,
            text="0 items sufficient",
            text_color="green",
            anchor="w",
        )

    def _layout_widgets(self) -> None:
        """Position widgets using grid layout."""
        self.grid_propagate(False)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        self._label.grid(row=0, column=0, padx=(10, 20), pady=5, sticky="w")
        self._purchase_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self._sufficient_label.grid(row=0, column=2, padx=10, pady=5, sticky="w")

    def update_summary(self, gap_result: Optional[GapAnalysisResult]) -> None:
        """
        Update the summary display with gap analysis results.

        Args:
            gap_result: Result from analyze_inventory_gaps(), or None to clear
        """
        if gap_result is None:
            self._purchase_count = 0
            self._sufficient_count = 0
        else:
            self._purchase_count = len(gap_result.purchase_items)
            self._sufficient_count = len(gap_result.sufficient_items)

        self._update_display()

    def _update_display(self) -> None:
        """Update label text based on current counts."""
        if self._purchase_count == 0:
            self._purchase_label.configure(
                text="No purchases needed",
                text_color="green",
            )
        elif self._purchase_count == 1:
            self._purchase_label.configure(
                text="1 item to purchase",
                text_color="orange",
            )
        else:
            self._purchase_label.configure(
                text=f"{self._purchase_count} items to purchase",
                text_color="orange",
            )

        if self._sufficient_count == 0:
            self._sufficient_label.configure(text="")
        elif self._sufficient_count == 1:
            self._sufficient_label.configure(
                text="1 item sufficient",
                text_color="green",
            )
        else:
            self._sufficient_label.configure(
                text=f"{self._sufficient_count} items sufficient",
                text_color="green",
            )

    def clear(self) -> None:
        """Clear the summary display."""
        self.update_summary(None)
