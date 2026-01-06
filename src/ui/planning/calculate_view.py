"""CalculateView - Calculate phase UI for Planning Workspace.

Displays batch calculations for an event and allows recalculation.

Implements User Story 1: Calculate phase shows batch counts and waste.
"""

from typing import Any, Callable, Optional
import customtkinter as ctk

from src.services.planning import (
    calculate_plan,
    get_plan_summary,
    PlanningError,
    EventNotConfiguredError,
)


# Waste percentage color thresholds
WASTE_COLORS = {
    "low": ("#00AA00", "#00CC00"),  # Green: <5%
    "medium": ("#CCAA00", "#FFD700"),  # Yellow: 5-15%
    "high": ("#CC6600", "#FF8000"),  # Orange: >15%
}


def _get_waste_color(waste_percent: float) -> str:
    """Get color for waste percentage.

    Args:
        waste_percent: Waste as percentage

    Returns:
        Color tuple (light, dark) for the waste level
    """
    if waste_percent < 5:
        return WASTE_COLORS["low"]
    elif waste_percent < 15:
        return WASTE_COLORS["medium"]
    else:
        return WASTE_COLORS["high"]


class RecipeBatchRow(ctk.CTkFrame):
    """Single row in the batch results table."""

    def __init__(
        self,
        parent: Any,
        recipe_name: str,
        units_needed: int,
        batches: int,
        yield_per_batch: int,
        total_yield: int,
        waste_units: int,
        waste_percent: float,
        **kwargs
    ):
        """Initialize RecipeBatchRow.

        Args:
            parent: Parent widget
            recipe_name: Name of the recipe
            units_needed: Units required
            batches: Number of batches needed
            yield_per_batch: Yield per batch
            total_yield: Total yield from all batches
            waste_units: Number of waste units
            waste_percent: Waste as percentage
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        # Configure grid columns
        self.grid_columnconfigure(0, weight=2)  # Recipe name
        self.grid_columnconfigure(1, weight=1)  # Units needed
        self.grid_columnconfigure(2, weight=1)  # Batches
        self.grid_columnconfigure(3, weight=1)  # Total yield
        self.grid_columnconfigure(4, weight=1)  # Waste

        # Recipe name
        name_label = ctk.CTkLabel(
            self,
            text=recipe_name,
            anchor="w",
        )
        name_label.grid(row=0, column=0, sticky="ew", padx=5, pady=3)

        # Units needed
        units_label = ctk.CTkLabel(
            self,
            text=str(units_needed),
            anchor="e",
        )
        units_label.grid(row=0, column=1, sticky="ew", padx=5, pady=3)

        # Batches
        batches_label = ctk.CTkLabel(
            self,
            text=str(batches),
            anchor="e",
        )
        batches_label.grid(row=0, column=2, sticky="ew", padx=5, pady=3)

        # Total yield
        yield_label = ctk.CTkLabel(
            self,
            text=str(total_yield),
            anchor="e",
        )
        yield_label.grid(row=0, column=3, sticky="ew", padx=5, pady=3)

        # Waste with color coding
        waste_text = f"{waste_units} ({waste_percent:.1f}%)"
        waste_color = _get_waste_color(waste_percent)
        waste_label = ctk.CTkLabel(
            self,
            text=waste_text,
            anchor="e",
            text_color=waste_color,
        )
        waste_label.grid(row=0, column=4, sticky="ew", padx=5, pady=3)


class TableHeader(ctk.CTkFrame):
    """Header row for the batch results table."""

    def __init__(self, parent: Any, **kwargs):
        """Initialize TableHeader."""
        kwargs.setdefault("fg_color", ("gray80", "gray30"))
        super().__init__(parent, **kwargs)

        # Configure grid columns (match RecipeBatchRow)
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_columnconfigure(4, weight=1)

        headers = ["Recipe", "Units Needed", "Batches", "Total Yield", "Waste"]
        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                self,
                text=header,
                font=ctk.CTkFont(weight="bold"),
                anchor="w" if i == 0 else "e",
            )
            label.grid(row=0, column=i, sticky="ew", padx=5, pady=5)


class CalculateView(ctk.CTkFrame):
    """Calculate phase view for the Planning Workspace.

    Shows batch calculation results and allows recalculation.
    """

    def __init__(
        self,
        parent: Any,
        event_id: Optional[int] = None,
        on_calculated: Optional[Callable] = None,
        **kwargs
    ):
        """Initialize CalculateView.

        Args:
            parent: Parent widget
            event_id: Event ID to calculate for
            on_calculated: Callback when calculation completes
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self.event_id = event_id
        self.on_calculated = on_calculated
        self._plan_data: dict = {}

        self._setup_ui()

        if event_id:
            self.after(100, self._load_existing_plan)

    def _setup_ui(self) -> None:
        """Set up the view UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header with title and calculate button
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="Calculate Requirements",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        self.calculate_btn = ctk.CTkButton(
            header_frame,
            text="Calculate Plan",
            command=self._on_calculate_click,
            width=140,
            height=36,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.calculate_btn.grid(row=0, column=1, padx=(10, 0))

        # Info text
        info_text = ctk.CTkLabel(
            self,
            text="Calculate batch requirements based on event targets. "
                 "Batches always round up to ensure sufficient production.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            wraplength=600,
            justify="left",
        )
        info_text.grid(row=1, column=0, sticky="w", pady=(0, 15))

        # Results container
        self.results_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.results_frame.grid(row=2, column=0, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(1, weight=1)

        # Placeholder message
        self.placeholder = ctk.CTkLabel(
            self.results_frame,
            text="Click 'Calculate Plan' to generate batch requirements",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        self.placeholder.grid(row=0, column=0, pady=50)

        # Table header (hidden initially)
        self.table_header = TableHeader(self.results_frame)

        # Scrollable results table
        self.table_scroll = ctk.CTkScrollableFrame(
            self.results_frame,
            fg_color="transparent",
        )

        # Summary section (hidden initially)
        self.summary_frame = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        self.summary_label = ctk.CTkLabel(
            self.summary_frame,
            text="",
            font=ctk.CTkFont(size=14),
        )
        self.summary_label.pack(pady=10)

    def _on_calculate_click(self) -> None:
        """Handle calculate button click."""
        if not self.event_id:
            self._show_error("No event selected")
            return

        self.calculate_btn.configure(state="disabled", text="Calculating...")

        try:
            self._plan_data = calculate_plan(self.event_id, force_recalculate=True)
            self._display_results(self._plan_data)
            if self.on_calculated:
                self.on_calculated()
        except EventNotConfiguredError:
            self._show_error("Event needs output mode configured before planning")
        except PlanningError as e:
            self._show_error(str(e))
        except Exception as e:
            self._show_error(f"Unexpected error: {e}")
        finally:
            self.calculate_btn.configure(state="normal", text="Calculate Plan")

    def _load_existing_plan(self) -> None:
        """Load existing plan data if available."""
        if not self.event_id:
            return

        try:
            summary = get_plan_summary(self.event_id)
            if summary and summary.plan_id:
                # There's an existing plan - load its data
                self._plan_data = calculate_plan(self.event_id, force_recalculate=False)
                self._display_results(self._plan_data)
        except PlanningError:
            # No plan yet, that's ok
            pass
        except Exception as e:
            print(f"Error loading plan: {e}")

    def _display_results(self, plan_data: dict) -> None:
        """Display calculation results.

        Args:
            plan_data: Plan data from calculate_plan
        """
        # Hide placeholder
        self.placeholder.grid_remove()

        # Show table header
        self.table_header.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        # Clear existing rows
        for widget in self.table_scroll.winfo_children():
            widget.destroy()

        # Show table
        self.table_scroll.grid(row=1, column=0, sticky="nsew")

        # Add rows for each recipe batch
        recipe_batches = plan_data.get("recipe_batches", [])
        total_waste = 0
        total_yield = 0

        for batch in recipe_batches:
            row = RecipeBatchRow(
                self.table_scroll,
                recipe_name=batch.get("recipe_name", "Unknown"),
                units_needed=batch.get("units_needed", 0),
                batches=batch.get("batches", 0),
                yield_per_batch=batch.get("yield_per_batch", 0),
                total_yield=batch.get("total_yield", 0),
                waste_units=batch.get("waste_units", 0),
                waste_percent=batch.get("waste_percent", 0),
            )
            row.pack(fill="x", pady=1)

            total_waste += batch.get("waste_units", 0)
            total_yield += batch.get("total_yield", 0)

        # Show summary
        self.summary_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        avg_waste = (total_waste / total_yield * 100) if total_yield > 0 else 0
        self.summary_label.configure(
            text=f"Total: {len(recipe_batches)} recipes | "
                 f"Average waste: {avg_waste:.1f}%"
        )

    def _show_error(self, message: str) -> None:
        """Show error message.

        Args:
            message: Error message
        """
        # Clear results
        self.table_header.grid_remove()
        self.table_scroll.grid_remove()
        self.summary_frame.grid_remove()

        # Show error in placeholder area
        self.placeholder.configure(
            text=f"Error: {message}",
            text_color=("#CC0000", "#FF3333"),
        )
        self.placeholder.grid()

    def set_event(self, event_id: int) -> None:
        """Set the event ID and reload.

        Args:
            event_id: Event database ID
        """
        self.event_id = event_id
        self._plan_data = {}
        # Reset to placeholder
        self.placeholder.configure(
            text="Click 'Calculate Plan' to generate batch requirements",
            text_color="gray",
        )
        self.placeholder.grid()
        self.table_header.grid_remove()
        self.table_scroll.grid_remove()
        self.summary_frame.grid_remove()
        # Try to load existing plan
        self._load_existing_plan()

    def refresh(self) -> None:
        """Refresh the view."""
        if self.event_id and self._plan_data:
            self._display_results(self._plan_data)
