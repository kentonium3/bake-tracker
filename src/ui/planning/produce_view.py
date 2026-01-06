"""ProduceView - Production phase UI for Planning Workspace.

Displays production progress with progress bars per recipe.

Implements User Story 4: Produce phase shows progress bars per recipe.
"""

from typing import Any, Optional
import customtkinter as ctk

from src.services.planning import (
    get_production_progress,
    get_overall_progress,
    ProductionProgress,
)


class ProgressRow(ctk.CTkFrame):
    """Single row showing progress for a recipe."""

    def __init__(
        self,
        parent: Any,
        progress: ProductionProgress,
        **kwargs
    ):
        """Initialize ProgressRow.

        Args:
            parent: Parent widget
            progress: Production progress data
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        # Configure grid columns
        self.grid_columnconfigure(0, weight=1)  # Recipe name
        self.grid_columnconfigure(1, weight=2)  # Progress bar
        self.grid_columnconfigure(2, weight=0)  # Progress text
        self.grid_columnconfigure(3, weight=0)  # Status icon

        # Recipe name
        name_label = ctk.CTkLabel(
            self,
            text=progress.recipe_name,
            anchor="w",
            font=ctk.CTkFont(size=14),
        )
        name_label.grid(row=0, column=0, sticky="ew", padx=(5, 10), pady=5)

        # Progress bar
        bar_value = min(progress.progress_percent / 100, 1.0)  # Cap at 100%
        bar_color = "#00AA00" if progress.is_complete else "#3B8ED0"
        progress_bar = ctk.CTkProgressBar(
            self,
            height=16,
            progress_color=bar_color,
        )
        progress_bar.set(bar_value)
        progress_bar.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # Progress text
        progress_text = f"{progress.completed_batches}/{progress.target_batches} " \
                        f"({progress.progress_percent:.0f}%)"
        text_label = ctk.CTkLabel(
            self,
            text=progress_text,
            anchor="e",
            width=100,
        )
        text_label.grid(row=0, column=2, padx=10, pady=5)

        # Status icon
        if progress.is_complete:
            status_icon = ctk.CTkLabel(
                self,
                text="\u2713",  # Checkmark
                text_color="#00AA00",
                font=ctk.CTkFont(size=18, weight="bold"),
                width=24,
            )
        elif progress.completed_batches > 0:
            status_icon = ctk.CTkLabel(
                self,
                text="\u25d0",  # Half circle
                text_color="#FFD700",
                font=ctk.CTkFont(size=18),
                width=24,
            )
        else:
            status_icon = ctk.CTkLabel(
                self,
                text="\u25cb",  # Empty circle
                text_color="gray",
                font=ctk.CTkFont(size=18),
                width=24,
            )
        status_icon.grid(row=0, column=3, padx=(5, 10), pady=5)


class OverallProgressBar(ctk.CTkFrame):
    """Overall progress display with large progress bar."""

    def __init__(
        self,
        parent: Any,
        percent: float,
        label: str = "Overall Production Progress",
        **kwargs
    ):
        """Initialize OverallProgressBar.

        Args:
            parent: Parent widget
            percent: Progress percentage
            label: Label text
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", ("gray90", "gray20"))
        kwargs.setdefault("corner_radius", 8)
        super().__init__(parent, **kwargs)

        self.grid_columnconfigure(0, weight=1)

        # Label
        label_widget = ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        label_widget.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        # Progress bar container
        bar_frame = ctk.CTkFrame(self, fg_color="transparent")
        bar_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(5, 15))
        bar_frame.grid_columnconfigure(0, weight=1)

        # Large progress bar
        bar_value = min(percent / 100, 1.0)
        bar_color = "#00AA00" if percent >= 100 else "#3B8ED0"
        progress_bar = ctk.CTkProgressBar(
            bar_frame,
            height=24,
            progress_color=bar_color,
        )
        progress_bar.set(bar_value)
        progress_bar.grid(row=0, column=0, sticky="ew")

        # Percentage text
        percent_label = ctk.CTkLabel(
            bar_frame,
            text=f"{percent:.0f}%",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=60,
        )
        percent_label.grid(row=0, column=1, padx=(10, 0))


class ProduceView(ctk.CTkFrame):
    """Production phase view for the Planning Workspace.

    Shows production progress with progress bars per recipe.
    """

    def __init__(
        self,
        parent: Any,
        event_id: Optional[int] = None,
        **kwargs
    ):
        """Initialize ProduceView.

        Args:
            parent: Parent widget
            event_id: Event ID to show progress for
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self.event_id = event_id
        self._progress_items: list[ProductionProgress] = []

        self._setup_ui()

        if event_id:
            self.after(100, self._load_progress)

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
            text="Production Progress",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        # Refresh button
        refresh_btn = ctk.CTkButton(
            header_frame,
            text="Refresh",
            command=self._load_progress,
            width=100,
        )
        refresh_btn.grid(row=0, column=1)

        # Overall progress section
        self.overall_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.overall_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.overall_frame.grid_columnconfigure(0, weight=1)

        # Results container
        self.results_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.results_frame.grid(row=2, column=0, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

        # Placeholder message
        self.placeholder = ctk.CTkLabel(
            self.results_frame,
            text="No production targets. Calculate a plan first.",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        self.placeholder.grid(row=0, column=0, pady=50)

        # Scrollable progress list
        self.progress_scroll = ctk.CTkScrollableFrame(
            self.results_frame,
            fg_color="transparent",
        )

    def _load_progress(self) -> None:
        """Load production progress from service."""
        if not self.event_id:
            return

        try:
            # Get per-recipe progress
            self._progress_items = get_production_progress(self.event_id)

            # Get overall progress
            overall = get_overall_progress(self.event_id)

            self._display_progress(overall)
        except Exception as e:
            print(f"Error loading production progress: {e}")
            self._show_empty_message("Error loading production progress")

    def _display_progress(self, overall: dict) -> None:
        """Display production progress.

        Args:
            overall: Overall progress data from service
        """
        if not self._progress_items:
            self._show_empty_message("No production targets. Calculate a plan first.")
            return

        # Hide placeholder
        self.placeholder.grid_remove()

        # Clear and rebuild overall progress
        for widget in self.overall_frame.winfo_children():
            widget.destroy()

        overall_percent = overall.get("production_percent", 0)
        overall_bar = OverallProgressBar(
            self.overall_frame,
            percent=overall_percent,
        )
        overall_bar.grid(row=0, column=0, sticky="ew")

        # Clear existing progress rows
        for widget in self.progress_scroll.winfo_children():
            widget.destroy()

        # Show progress list
        self.progress_scroll.grid(row=0, column=0, sticky="nsew")

        # Add section header
        section_header = ctk.CTkLabel(
            self.progress_scroll,
            text="Per-Recipe Progress",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        )
        section_header.pack(fill="x", pady=(10, 5))

        # Add progress rows
        for progress in self._progress_items:
            row = ProgressRow(self.progress_scroll, progress)
            row.pack(fill="x", pady=2)

        # Summary
        complete_count = sum(1 for p in self._progress_items if p.is_complete)
        summary = ctk.CTkLabel(
            self.progress_scroll,
            text=f"{complete_count}/{len(self._progress_items)} recipes complete",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        summary.pack(pady=(15, 10))

    def _show_empty_message(self, message: str) -> None:
        """Show empty state message.

        Args:
            message: Message to display
        """
        # Clear overall
        for widget in self.overall_frame.winfo_children():
            widget.destroy()

        self.progress_scroll.grid_remove()
        self.placeholder.configure(text=message, text_color="gray")
        self.placeholder.grid()

    def set_event(self, event_id: int) -> None:
        """Set the event ID and reload.

        Args:
            event_id: Event database ID
        """
        self.event_id = event_id
        self._progress_items = []
        self._load_progress()

    def refresh(self) -> None:
        """Refresh the view."""
        self._load_progress()
