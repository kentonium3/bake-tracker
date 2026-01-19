"""AssembleView - Assembly phase UI for Planning Workspace.

Displays assembly checklist with feasibility indicators.

Implements User Story 5: Assemble phase shows checklist with partial assembly support.
"""

from typing import Any, Optional
import customtkinter as ctk

from src.services.planning import (
    get_assembly_checklist,
    record_assembly_confirmation,
    check_assembly_feasibility,
    get_assembly_progress,
    FeasibilityStatus,
    FeasibilityResult,
    AssemblyProgress,
)


# Status colors for feasibility
STATUS_COLORS = {
    FeasibilityStatus.CAN_ASSEMBLE: ("#00AA00", "#00CC00"),  # Green
    FeasibilityStatus.PARTIAL: ("#CCAA00", "#FFD700"),  # Yellow
    FeasibilityStatus.AWAITING_PRODUCTION: ("#CC6600", "#FF8000"),  # Orange
    FeasibilityStatus.CANNOT_ASSEMBLE: ("#CC0000", "#FF3333"),  # Red
}

STATUS_LABELS = {
    FeasibilityStatus.CAN_ASSEMBLE: "Ready",
    FeasibilityStatus.PARTIAL: "Partial",
    FeasibilityStatus.AWAITING_PRODUCTION: "Awaiting Production",
    FeasibilityStatus.CANNOT_ASSEMBLE: "Not Available",
}


class AssemblyItemRow(ctk.CTkFrame):
    """Single row in the assembly checklist."""

    def __init__(self, parent: Any, item: dict, on_assemble: callable, **kwargs):
        """Initialize AssemblyItemRow.

        Args:
            parent: Parent widget
            item: Assembly item data from checklist
            on_assemble: Callback when assemble button clicked
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", ("gray92", "gray18"))
        kwargs.setdefault("corner_radius", 6)
        super().__init__(parent, **kwargs)

        self.item = item
        self.on_assemble = on_assemble

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the row UI."""
        self.grid_columnconfigure(1, weight=1)

        # Bundle name and target
        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.grid(row=0, column=0, sticky="w", padx=10, pady=8)

        name_label = ctk.CTkLabel(
            name_frame,
            text=self.item.get("finished_good_name", "Unknown"),
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        name_label.pack(anchor="w")

        target = self.item.get("target", 0)
        assembled = self.item.get("assembled", 0)
        available = self.item.get("available_to_assemble", 0)

        status_text = f"{assembled}/{target} assembled | {available} available"
        status_label = ctk.CTkLabel(
            name_frame,
            text=status_text,
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        status_label.pack(anchor="w")

        # Progress bar in middle
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=0, column=1, sticky="ew", padx=20, pady=8)
        progress_frame.grid_columnconfigure(0, weight=1)

        progress_percent = (assembled / target * 100) if target > 0 else 0
        bar_color = "#00AA00" if assembled >= target else "#3B8ED0"
        progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=12,
            progress_color=bar_color,
        )
        progress_bar.set(min(progress_percent / 100, 1.0))
        progress_bar.grid(row=0, column=0, sticky="ew")

        # Action button / status
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=0, column=2, padx=10, pady=8)

        if assembled >= target:
            # Complete - show checkmark
            complete_label = ctk.CTkLabel(
                action_frame,
                text="\u2713 Complete",
                text_color="#00AA00",
                font=ctk.CTkFont(weight="bold"),
            )
            complete_label.pack()
        elif available > 0:
            # Can assemble - show button
            assemble_btn = ctk.CTkButton(
                action_frame,
                text=f"Assemble ({available})",
                command=self._handle_assemble,
                width=120,
                height=28,
            )
            assemble_btn.pack()
        else:
            # Not available - show status
            status_label = ctk.CTkLabel(
                action_frame,
                text="Awaiting production",
                text_color="gray",
                font=ctk.CTkFont(size=12),
            )
            status_label.pack()

    def _handle_assemble(self) -> None:
        """Handle assemble button click."""
        self.on_assemble(self.item)


class FeasibilitySection(ctk.CTkFrame):
    """Section showing feasibility status for all bundles."""

    def __init__(self, parent: Any, results: list[FeasibilityResult], **kwargs):
        """Initialize FeasibilitySection.

        Args:
            parent: Parent widget
            results: Feasibility results from service
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", ("gray90", "gray20"))
        kwargs.setdefault("corner_radius", 8)
        super().__init__(parent, **kwargs)

        self._setup_ui(results)

    def _setup_ui(self, results: list[FeasibilityResult]) -> None:
        """Set up the section UI."""
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text="Assembly Feasibility",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        header.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        # Results
        for i, result in enumerate(results):
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.grid(row=i + 1, column=0, sticky="ew", padx=10, pady=2)
            row.grid_columnconfigure(1, weight=1)

            # Status indicator
            status_color = STATUS_COLORS.get(result.status, ("gray", "gray"))
            status_indicator = ctk.CTkLabel(
                row,
                text="\u25cf",  # Filled circle
                text_color=status_color,
                font=ctk.CTkFont(size=14),
            )
            status_indicator.grid(row=0, column=0, padx=(0, 5))

            # Bundle name
            name_label = ctk.CTkLabel(
                row,
                text=result.finished_good_name,
                anchor="w",
            )
            name_label.grid(row=0, column=1, sticky="ew")

            # Status label
            status_text = STATUS_LABELS.get(result.status, "Unknown")
            status_label = ctk.CTkLabel(
                row,
                text=status_text,
                text_color=status_color,
            )
            status_label.grid(row=0, column=2, padx=(10, 0))

            # Can assemble count
            count_label = ctk.CTkLabel(
                row,
                text=f"{result.can_assemble}/{result.target_quantity}",
                width=60,
            )
            count_label.grid(row=0, column=3, padx=(10, 0))

        # Padding at bottom
        spacer = ctk.CTkFrame(self, fg_color="transparent", height=10)
        spacer.grid(row=len(results) + 1, column=0)


class AssembleView(ctk.CTkFrame):
    """Assembly phase view for the Planning Workspace.

    Shows assembly checklist with feasibility indicators and
    supports partial assembly.
    """

    def __init__(self, parent: Any, event_id: Optional[int] = None, **kwargs):
        """Initialize AssembleView.

        Args:
            parent: Parent widget
            event_id: Event ID to show checklist for
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self.event_id = event_id
        self._checklist_items: list[dict] = []
        self._feasibility_results: list[FeasibilityResult] = []

        self._setup_ui()

        if event_id:
            self.after(100, self._load_checklist)

    def _setup_ui(self) -> None:
        """Set up the view UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header with title
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="Assembly Checklist",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        # Refresh button
        refresh_btn = ctk.CTkButton(
            header_frame,
            text="Refresh",
            command=self._load_checklist,
            width=100,
        )
        refresh_btn.grid(row=0, column=1)

        # Feasibility section
        self.feasibility_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.feasibility_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.feasibility_frame.grid_columnconfigure(0, weight=1)

        # Results container
        self.results_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.results_frame.grid(row=2, column=0, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

        # Placeholder message
        self.placeholder = ctk.CTkLabel(
            self.results_frame,
            text="No assembly targets. Calculate a plan first.",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        self.placeholder.grid(row=0, column=0, pady=50)

        # Scrollable checklist
        self.checklist_scroll = ctk.CTkScrollableFrame(
            self.results_frame,
            fg_color="transparent",
        )

    def _load_checklist(self) -> None:
        """Load assembly checklist from service."""
        if not self.event_id:
            return

        try:
            # Get checklist
            self._checklist_items = get_assembly_checklist(self.event_id)

            # Get feasibility
            self._feasibility_results = check_assembly_feasibility(self.event_id)

            self._display_checklist()
        except Exception as e:
            print(f"Error loading assembly checklist: {e}")
            self._show_empty_message("Error loading assembly checklist")

    def _display_checklist(self) -> None:
        """Display the assembly checklist."""
        if not self._checklist_items:
            self._show_empty_message("No assembly targets. Calculate a plan first.")
            return

        # Hide placeholder
        self.placeholder.grid_remove()

        # Clear and rebuild feasibility section
        for widget in self.feasibility_frame.winfo_children():
            widget.destroy()

        if self._feasibility_results:
            feasibility_section = FeasibilitySection(
                self.feasibility_frame,
                self._feasibility_results,
            )
            feasibility_section.grid(row=0, column=0, sticky="ew")

        # Clear existing checklist rows
        for widget in self.checklist_scroll.winfo_children():
            widget.destroy()

        # Show checklist
        self.checklist_scroll.grid(row=0, column=0, sticky="nsew")

        # Add section header
        section_header = ctk.CTkLabel(
            self.checklist_scroll,
            text="Assembly Items",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        )
        section_header.pack(fill="x", pady=(10, 5))

        # Add checklist rows
        for item in self._checklist_items:
            row = AssemblyItemRow(
                self.checklist_scroll,
                item,
                on_assemble=self._handle_assemble_item,
            )
            row.pack(fill="x", pady=3)

        # Summary
        complete_count = sum(
            1 for item in self._checklist_items if item.get("assembled", 0) >= item.get("target", 0)
        )
        summary = ctk.CTkLabel(
            self.checklist_scroll,
            text=f"{complete_count}/{len(self._checklist_items)} bundles complete",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        summary.pack(pady=(15, 10))

    def _show_empty_message(self, message: str) -> None:
        """Show empty state message.

        Args:
            message: Message to display
        """
        # Clear feasibility
        for widget in self.feasibility_frame.winfo_children():
            widget.destroy()

        self.checklist_scroll.grid_remove()
        self.placeholder.configure(text=message, text_color="gray")
        self.placeholder.grid()

    def _handle_assemble_item(self, item: dict) -> None:
        """Handle assemble button click for an item.

        Args:
            item: The checklist item to assemble
        """
        if not self.event_id:
            return

        finished_good_id = item.get("finished_good_id")
        available = item.get("available_to_assemble", 0)

        if not finished_good_id or available <= 0:
            return

        try:
            # Record assembly confirmation
            result = record_assembly_confirmation(
                self.event_id,
                finished_good_id,
                available,
            )
            if result:
                self._show_success(f"Assembled {available} {item.get('finished_good_name', '')}")
                self._load_checklist()  # Refresh
        except Exception as e:
            self._show_error(str(e))

    def _show_success(self, message: str) -> None:
        """Show success message.

        Args:
            message: Success message
        """
        print(f"Success: {message}")

    def _show_error(self, message: str) -> None:
        """Show error message.

        Args:
            message: Error message
        """
        print(f"Error: {message}")

    def set_event(self, event_id: int) -> None:
        """Set the event ID and reload.

        Args:
            event_id: Event database ID
        """
        self.event_id = event_id
        self._checklist_items = []
        self._feasibility_results = []
        self._load_checklist()

    def refresh(self) -> None:
        """Refresh the view."""
        self._load_checklist()
