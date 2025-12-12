"""
EventCard widget for displaying event progress summary.

Feature 018 - Event Production Dashboard
"""

import customtkinter as ctk
from typing import Dict, Any, Callable, Optional

from src.utils.constants import STATUS_COLORS, PADDING_MEDIUM, PADDING_LARGE


class EventCard(ctk.CTkFrame):
    """
    Expandable card showing event progress summary.

    Collapsed view: Event name, date, overall progress bar, fulfillment counts
    Expanded view: Individual target progress bars, quick action buttons
    """

    def __init__(
        self,
        parent,
        event_data: Dict[str, Any],
        callbacks: Optional[Dict[str, Callable]] = None,
        **kwargs,
    ):
        """
        Initialize EventCard.

        Args:
            parent: Parent widget
            event_data: Dict with event_id, event_name, event_date,
                       production_progress, assembly_progress, overall_progress
            callbacks: Dict of callback functions:
                       - on_record_production(event_id)
                       - on_record_assembly(event_id)
                       - on_shopping_list(event_id)
                       - on_event_detail(event_id)
                       - on_fulfillment_click(event_id, status)
        """
        super().__init__(parent, **kwargs)

        self.event_data = event_data
        self.callbacks = callbacks or {}
        self._is_expanded = False

        # Configure card appearance
        self.configure(corner_radius=8, border_width=1, border_color="gray50")

        self._create_widgets()

    def _create_widgets(self):
        """Create all widget components."""
        self._create_collapsed_view()
        self._create_expanded_view()

        # Initially hide expanded view
        self.detail_frame.pack_forget()

    def _create_collapsed_view(self):
        """Create the collapsed summary view."""
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        # Row 1: Event name and date with expand button
        row1 = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        row1.pack(fill="x")

        # Expand/collapse indicator
        self.expand_btn = ctk.CTkButton(
            row1,
            text="\u25b6",  # Right-pointing triangle
            width=30,
            height=30,
            command=self.toggle_expanded,
            fg_color="transparent",
            hover_color="gray30",
        )
        self.expand_btn.pack(side="left", padx=(0, PADDING_MEDIUM))

        # Event name
        ctk.CTkLabel(
            row1,
            text=self.event_data["event_name"],
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        # Event date
        event_date = self.event_data["event_date"]
        date_str = event_date.strftime("%b %d, %Y") if event_date else "No date"
        ctk.CTkLabel(row1, text=f" | {date_str}", text_color="gray60").pack(side="left")

        # Row 2: Overall progress bar
        self._create_overall_progress_row()

        # Row 3: Fulfillment status counts
        self._create_fulfillment_row()

    def _create_overall_progress_row(self):
        """Create overall progress indicator row."""
        row2 = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        row2.pack(fill="x", pady=(PADDING_MEDIUM, 0))

        overall = self.event_data.get("overall_progress", {})

        # Production progress
        prod_count = overall.get("production_targets_count", 0)
        prod_complete = overall.get("production_complete_count", 0)

        # Assembly progress
        asm_count = overall.get("assembly_targets_count", 0)
        asm_complete = overall.get("assembly_complete_count", 0)

        # Combined progress
        total_targets = prod_count + asm_count
        total_complete = prod_complete + asm_complete

        if total_targets > 0:
            progress_pct = (total_complete / total_targets) * 100
        else:
            progress_pct = 0

        # Progress bar
        self.overall_progress = ctk.CTkProgressBar(row2, width=200)
        self.overall_progress.set(min(progress_pct / 100, 1.0))
        self.overall_progress.configure(progress_color=self._get_status_color(progress_pct))
        self.overall_progress.pack(side="left", padx=(40, PADDING_MEDIUM))

        # Progress text
        status_text = self._get_status_text(progress_pct)
        label_text = (
            f"{total_complete}/{total_targets} targets ({progress_pct:.0f}%) - " f"{status_text}"
        )

        if total_targets == 0:
            label_text = "No targets set"

        ctk.CTkLabel(row2, text=label_text, text_color=self._get_status_color(progress_pct)).pack(
            side="left"
        )

    def _create_fulfillment_row(self):
        """Create fulfillment status counts row."""
        row3 = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        row3.pack(fill="x", pady=(PADDING_MEDIUM, 0))

        overall = self.event_data.get("overall_progress", {})

        pending = overall.get("packages_pending", 0)
        ready = overall.get("packages_ready", 0)
        delivered = overall.get("packages_delivered", 0)
        total = overall.get("packages_total", 0)

        if total == 0:
            ctk.CTkLabel(row3, text="No packages assigned", text_color="gray60", padx=40).pack(
                side="left"
            )
            return

        # Create clickable labels for each status
        fulfillment_frame = ctk.CTkFrame(row3, fg_color="transparent")
        fulfillment_frame.pack(side="left", padx=40)

        # Helper to create clickable status label
        def make_status_label(text, status):
            btn = ctk.CTkButton(
                fulfillment_frame,
                text=text,
                fg_color="transparent",
                hover_color="gray30",
                text_color="gray70",
                command=lambda: self._on_fulfillment_click(status),
            )
            btn.pack(side="left", padx=(0, PADDING_MEDIUM))

        make_status_label(f"{pending} pending", "pending")
        make_status_label(f"{ready} ready", "ready")
        make_status_label(f"{delivered} delivered", "delivered")

    def _on_fulfillment_click(self, status: str):
        """Handle click on fulfillment status."""
        callback = self.callbacks.get("on_fulfillment_click")
        if callback:
            callback(self.event_data["event_id"], status)

    def _create_expanded_view(self):
        """Create the expanded detail view."""
        self.detail_frame = ctk.CTkFrame(self, fg_color="transparent")

        # Production targets section
        self._create_production_section()

        # Assembly targets section
        self._create_assembly_section()

        # Quick actions row
        self._create_quick_actions()

    def _create_production_section(self):
        """Create production targets progress section."""
        production_progress = self.event_data.get("production_progress", [])

        if not production_progress:
            return

        # Section header
        ctk.CTkLabel(
            self.detail_frame,
            text="Recipe Production:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_MEDIUM, 5))

        # Progress bars for each target
        for item in production_progress:
            row = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
            row.pack(fill="x", padx=PADDING_LARGE, pady=2)

            # Recipe name
            ctk.CTkLabel(row, text=item["recipe_name"], width=150, anchor="w").pack(
                side="left", padx=5
            )

            # Progress bar
            progress_pct = item.get("progress_pct", 0)
            progress_bar = ctk.CTkProgressBar(row, width=150)
            progress_bar.set(min(progress_pct / 100, 1.0))
            progress_bar.configure(progress_color=self._get_status_color(progress_pct))
            progress_bar.pack(side="left", padx=5)

            # Progress text
            produced = item.get("produced_batches", 0)
            target = item.get("target_batches", 0)
            label_text = f"{produced}/{target} ({progress_pct:.0f}%)"
            ctk.CTkLabel(
                row, text=label_text, text_color=self._get_status_color(progress_pct)
            ).pack(side="left", padx=5)

    def _create_assembly_section(self):
        """Create assembly targets progress section."""
        assembly_progress = self.event_data.get("assembly_progress", [])

        if not assembly_progress:
            return

        # Section header
        ctk.CTkLabel(
            self.detail_frame,
            text="Finished Good Assembly:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_MEDIUM, 5))

        # Progress bars for each target
        for item in assembly_progress:
            row = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
            row.pack(fill="x", padx=PADDING_LARGE, pady=2)

            # Finished good name
            ctk.CTkLabel(row, text=item["finished_good_name"], width=150, anchor="w").pack(
                side="left", padx=5
            )

            # Progress bar
            progress_pct = item.get("progress_pct", 0)
            progress_bar = ctk.CTkProgressBar(row, width=150)
            progress_bar.set(min(progress_pct / 100, 1.0))
            progress_bar.configure(progress_color=self._get_status_color(progress_pct))
            progress_bar.pack(side="left", padx=5)

            # Progress text
            assembled = item.get("assembled_quantity", 0)
            target = item.get("target_quantity", 0)
            label_text = f"{assembled}/{target} ({progress_pct:.0f}%)"
            ctk.CTkLabel(
                row, text=label_text, text_color=self._get_status_color(progress_pct)
            ).pack(side="left", padx=5)

    def _create_quick_actions(self):
        """Create quick action buttons row."""
        actions_frame = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        actions_frame.pack(fill="x", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

        event_id = self.event_data["event_id"]

        # Record Production button
        if "on_record_production" in self.callbacks:
            ctk.CTkButton(
                actions_frame,
                text="Record Production",
                width=130,
                command=lambda: self.callbacks["on_record_production"](event_id),
            ).pack(side="left", padx=(0, PADDING_MEDIUM))

        # Record Assembly button
        if "on_record_assembly" in self.callbacks:
            ctk.CTkButton(
                actions_frame,
                text="Record Assembly",
                width=130,
                command=lambda: self.callbacks["on_record_assembly"](event_id),
            ).pack(side="left", padx=(0, PADDING_MEDIUM))

        # Shopping List button
        if "on_shopping_list" in self.callbacks:
            ctk.CTkButton(
                actions_frame,
                text="Shopping List",
                width=100,
                command=lambda: self.callbacks["on_shopping_list"](event_id),
            ).pack(side="left", padx=(0, PADDING_MEDIUM))

        # Event Detail button
        if "on_event_detail" in self.callbacks:
            ctk.CTkButton(
                actions_frame,
                text="Event Detail",
                width=100,
                command=lambda: self.callbacks["on_event_detail"](event_id),
            ).pack(side="left")

    def toggle_expanded(self):
        """Toggle between collapsed and expanded views."""
        self._is_expanded = not self._is_expanded

        if self._is_expanded:
            # Show expanded view
            self.detail_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM))
            self.expand_btn.configure(text="\u25bc")  # Down-pointing triangle
        else:
            # Hide expanded view
            self.detail_frame.pack_forget()
            self.expand_btn.configure(text="\u25b6")  # Right-pointing triangle

    def _get_status_color(self, progress_pct: float) -> str:
        """
        Get color for progress percentage.

        Args:
            progress_pct: Progress as percentage (0-100+)

        Returns:
            Hex color string from STATUS_COLORS
        """
        if progress_pct == 0:
            return STATUS_COLORS.get("not_started", "#808080")
        elif progress_pct < 100:
            return STATUS_COLORS.get("in_progress", "#FFA500")
        elif progress_pct == 100:
            return STATUS_COLORS.get("complete", "#28A745")
        else:
            return STATUS_COLORS.get("exceeded", "#20B2AA")

    def _get_status_text(self, progress_pct: float) -> str:
        """Get status text for progress percentage."""
        if progress_pct == 0:
            return "Not Started"
        elif progress_pct < 100:
            return "In Progress"
        elif progress_pct == 100:
            return "Complete"
        else:
            return "Exceeded"
