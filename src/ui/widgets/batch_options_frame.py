"""Widget for displaying and selecting batch options.

Feature 073: Batch Calculation User Decisions
Work Package: WP04 - UI Widget - BatchOptionsFrame

Provides a scrollable frame that displays batch options for each FinishedUnit
with radio button selection, shortfall warnings, and exact match highlights.
"""

from typing import Callable, Dict, List, Optional

import customtkinter as ctk

from src.services.planning_service import BatchOption, BatchOptionsResult


# Visual styling constants
SHORTFALL_COLOR = "#FF6B6B"  # Red for shortfall warning
EXACT_MATCH_COLOR = "#4CAF50"  # Green for exact match
SURPLUS_COLOR = "#888888"  # Gray for surplus (neutral)


class BatchOptionsFrame(ctk.CTkScrollableFrame):
    """
    Widget for displaying and selecting batch options.

    Displays batch options for each FinishedUnit with radio button selection.
    Shows shortfall warnings and exact match highlights.
    """

    def __init__(
        self,
        parent,
        on_selection_change: Optional[Callable[[int, int], None]] = None,
        **kwargs,
    ):
        """
        Initialize BatchOptionsFrame.

        Args:
            parent: Parent widget
            on_selection_change: Callback when user selects an option.
                                 Called with (finished_unit_id, batches)
            **kwargs: Additional arguments passed to CTkScrollableFrame
        """
        super().__init__(parent, **kwargs)

        self._selection_callback = on_selection_change
        self._option_vars: Dict[int, ctk.StringVar] = {}  # fu_id -> StringVar
        self._options_data: Dict[int, List[BatchOption]] = {}  # fu_id -> options
        self._fu_frames: Dict[int, ctk.CTkFrame] = {}  # fu_id -> frame

        # Configure grid
        self.columnconfigure(0, weight=1)

    def populate(self, options_results: List[BatchOptionsResult]) -> None:
        """
        Display batch options for all FUs.

        Args:
            options_results: List of BatchOptionsResult from calculate_batch_options()
        """
        # Clear existing content
        self.clear()

        # Create section for each FU
        for idx, result in enumerate(options_results):
            self._create_fu_section(result, idx)

    def clear(self) -> None:
        """Clear all displayed options."""
        for widget in self.winfo_children():
            widget.destroy()
        self._option_vars.clear()
        self._options_data.clear()
        self._fu_frames.clear()

    def _create_fu_section(self, result: BatchOptionsResult, row: int) -> None:
        """
        Create section for one FU with header and radio options.

        Args:
            result: BatchOptionsResult for this FU
            row: Grid row index
        """
        # Frame for this FU
        fu_frame = ctk.CTkFrame(self)
        fu_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        fu_frame.columnconfigure(0, weight=1)
        self._fu_frames[result.finished_unit_id] = fu_frame

        # Header: FU name
        header_text = f"{result.finished_unit_name}"
        header = ctk.CTkLabel(
            fu_frame,
            text=header_text,
            font=ctk.CTkFont(weight="bold", size=14),
            anchor="w",
        )
        header.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 0))

        # Subheader: quantity and yield info
        subheader_text = (
            f"Need {result.quantity_needed} {result.item_unit} "
            f"({result.yield_per_batch} per batch)"
        )
        subheader = ctk.CTkLabel(
            fu_frame,
            text=subheader_text,
            font=ctk.CTkFont(size=12),
            text_color="#888888",
            anchor="w",
        )
        subheader.grid(
            row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 5)
        )

        # Store data for this FU
        self._options_data[result.finished_unit_id] = result.options

        # Radio buttons for options
        var = ctk.StringVar(value="")
        self._option_vars[result.finished_unit_id] = var

        for opt_idx, option in enumerate(result.options):
            self._create_option_radio(
                fu_frame,
                result.finished_unit_id,
                option,
                var,
                result.item_unit,
                opt_idx + 2,  # Start at row 2 (after header and subheader)
            )

    def _create_option_radio(
        self,
        parent: ctk.CTkFrame,
        fu_id: int,
        option: BatchOption,
        var: ctk.StringVar,
        item_unit: str,
        row: int,
    ) -> None:
        """
        Create a radio button for one batch option.

        Args:
            parent: Parent frame
            fu_id: FinishedUnit ID for callback
            option: BatchOption to display
            var: StringVar for radio group
            item_unit: Unit name for display (e.g., "cookie")
            row: Grid row
        """
        # Format option text
        text = self._format_option_text(option, item_unit)

        # Determine text color based on option type
        if option.is_shortfall:
            text_color = SHORTFALL_COLOR
        elif option.is_exact_match:
            text_color = EXACT_MATCH_COLOR
        else:
            text_color = SURPLUS_COLOR

        # Create radio button
        radio = ctk.CTkRadioButton(
            parent,
            text=text,
            variable=var,
            value=str(option.batches),
            command=lambda: self._on_option_selected(fu_id),
            text_color=text_color,
        )
        radio.grid(row=row, column=0, sticky="w", padx=20, pady=2)

        # Add indicator icon
        if option.is_exact_match:
            indicator = ctk.CTkLabel(
                parent,
                text="✓",
                text_color=EXACT_MATCH_COLOR,
                font=ctk.CTkFont(size=14, weight="bold"),
            )
            indicator.grid(row=row, column=1, sticky="w", padx=5)
        elif option.is_shortfall:
            indicator = ctk.CTkLabel(
                parent,
                text="⚠",
                text_color=SHORTFALL_COLOR,
                font=ctk.CTkFont(size=14),
            )
            indicator.grid(row=row, column=1, sticky="w", padx=5)

    def _format_option_text(self, option: BatchOption, item_unit: str) -> str:
        """
        Format option for display in radio button.

        Args:
            option: BatchOption to format
            item_unit: Unit name (e.g., "cookie", "cake")

        Returns:
            Formatted string like "3 batches = 72 cookies (+22 extra)"
        """
        # Pluralize unit if needed
        unit = item_unit if option.total_yield == 1 else f"{item_unit}s"

        # Base text
        base = (
            f"{option.batches} batch{'es' if option.batches != 1 else ''} "
            f"= {option.total_yield} {unit}"
        )

        # Difference text
        if option.is_exact_match:
            diff_text = "(exact match)"
        elif option.is_shortfall:
            diff_text = f"({abs(option.difference)} short - SHORTFALL)"
        else:
            diff_text = f"(+{option.difference} extra)"

        return f"{base} {diff_text}"

    def _on_option_selected(self, fu_id: int) -> None:
        """
        Handle option selection change.

        Args:
            fu_id: FinishedUnit ID that was changed
        """
        if self._selection_callback is None:
            return

        var = self._option_vars.get(fu_id)
        if var is None:
            return

        value = var.get()
        if value:
            batches = int(value)
            self._selection_callback(fu_id, batches)

    def get_selections(self) -> Dict[int, int]:
        """
        Get current user selections.

        Returns:
            Dict mapping finished_unit_id -> selected batches.
            Only includes FUs where user has made a selection.
        """
        selections = {}
        for fu_id, var in self._option_vars.items():
            value = var.get()
            if value:
                selections[fu_id] = int(value)
        return selections

    def get_selection_with_shortfall_info(self) -> List[Dict]:
        """
        Get selections with shortfall information for validation.

        Returns:
            List of dicts with keys: finished_unit_id, batches, is_shortfall
        """
        results = []
        for fu_id, var in self._option_vars.items():
            value = var.get()
            if value:
                batches = int(value)
                options = self._options_data.get(fu_id, [])
                # Find the selected option to check shortfall
                is_shortfall = False
                for opt in options:
                    if opt.batches == batches:
                        is_shortfall = opt.is_shortfall
                        break
                results.append(
                    {
                        "finished_unit_id": fu_id,
                        "batches": batches,
                        "is_shortfall": is_shortfall,
                    }
                )
        return results

    def set_selection(self, fu_id: int, batches: int) -> None:
        """
        Set the selection for a FinishedUnit.

        Used when loading existing batch decisions.

        Args:
            fu_id: FinishedUnit ID
            batches: Number of batches to select
        """
        var = self._option_vars.get(fu_id)
        if var is not None:
            var.set(str(batches))


# Quick manual test script
if __name__ == "__main__":
    from src.services.planning_service import BatchOption, BatchOptionsResult

    # Sample data
    test_results = [
        BatchOptionsResult(
            finished_unit_id=1,
            finished_unit_name="Sugar Cookies",
            recipe_id=1,
            recipe_name="Sugar Cookie Recipe",
            quantity_needed=50,
            yield_per_batch=24,
            yield_mode="discrete_count",
            item_unit="cookie",
            options=[
                BatchOption(
                    batches=2,
                    total_yield=48,
                    quantity_needed=50,
                    difference=-2,
                    is_shortfall=True,
                    is_exact_match=False,
                    yield_per_batch=24,
                ),
                BatchOption(
                    batches=3,
                    total_yield=72,
                    quantity_needed=50,
                    difference=22,
                    is_shortfall=False,
                    is_exact_match=False,
                    yield_per_batch=24,
                ),
            ],
        ),
        BatchOptionsResult(
            finished_unit_id=2,
            finished_unit_name="Chocolate Cake",
            recipe_id=2,
            recipe_name="Chocolate Cake Recipe",
            quantity_needed=3,
            yield_per_batch=1,
            yield_mode="batch_portion",
            item_unit="cake",
            options=[
                BatchOption(
                    batches=3,
                    total_yield=3,
                    quantity_needed=3,
                    difference=0,
                    is_shortfall=False,
                    is_exact_match=True,
                    yield_per_batch=1,
                ),
            ],
        ),
    ]

    def on_change(fu_id, batches):
        print(f"Selection changed: FU {fu_id} = {batches} batches")

    root = ctk.CTk()
    root.geometry("500x400")
    root.title("BatchOptionsFrame Test")

    frame = BatchOptionsFrame(root, on_selection_change=on_change)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    frame.populate(test_results)

    root.mainloop()
