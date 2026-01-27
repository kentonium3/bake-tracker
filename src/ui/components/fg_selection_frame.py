"""
FGSelectionFrame - UI component for selecting finished goods.

Part of F070: Finished Goods Filtering for Event Planning.
Enhanced in F071: Finished Goods Quantity Specification.
"""

from typing import Callable, Dict, List, Optional, Tuple

import customtkinter as ctk

from src.models.finished_good import FinishedGood


class FGSelectionFrame(ctk.CTkFrame):
    """
    Frame for selecting finished goods from available list.

    Displays checkboxes for each available FG with quantity input fields,
    live count, and Save/Cancel buttons.
    """

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        on_save: Optional[Callable[[List[Tuple[int, int]]], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """
        Initialize FG selection frame.

        Args:
            parent: Parent widget
            on_save: Callback when Save clicked, receives list of (fg_id, quantity) tuples
            on_cancel: Callback when Cancel clicked
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(parent, **kwargs)

        self._on_save = on_save
        self._on_cancel = on_cancel

        # Track checkboxes and their variables
        self._checkbox_vars: Dict[int, ctk.BooleanVar] = {}  # fg_id -> BooleanVar
        self._checkboxes: Dict[int, ctk.CTkCheckBox] = {}  # fg_id -> checkbox widget
        self._fg_data: Dict[int, FinishedGood] = {}  # fg_id -> FG object

        # Track quantity inputs (F071)
        self._quantity_vars: Dict[int, ctk.StringVar] = {}  # fg_id -> StringVar
        self._quantity_entries: Dict[int, ctk.CTkEntry] = {}  # fg_id -> entry widget
        self._feedback_labels: Dict[int, ctk.CTkLabel] = {}  # fg_id -> feedback label

        # Event name for header
        self._event_name: str = ""

        # Build UI
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the UI components."""
        # Header label
        self._header_label = ctk.CTkLabel(
            self,
            text="Select Finished Goods",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self._header_label.pack(pady=(10, 5), padx=10, anchor="w")

        # Count label
        self._count_label = ctk.CTkLabel(
            self,
            text="0 of 0 selected",
            font=ctk.CTkFont(size=12),
        )
        self._count_label.pack(pady=(0, 10), padx=10, anchor="w")

        # Scrollable frame for checkboxes
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            height=200,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Button frame
        self._button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._button_frame.pack(fill="x", padx=10, pady=10)

        self._cancel_button = ctk.CTkButton(
            self._button_frame,
            text="Cancel",
            width=80,
            command=self._handle_cancel,
        )
        self._cancel_button.pack(side="right", padx=(5, 0))

        self._save_button = ctk.CTkButton(
            self._button_frame,
            text="Save",
            width=80,
            command=self._handle_save,
        )
        self._save_button.pack(side="right")

    def populate_finished_goods(
        self,
        finished_goods: List[FinishedGood],
        event_name: str = "",
    ) -> None:
        """
        Populate the frame with finished goods.

        Args:
            finished_goods: List of available FinishedGood objects to display
            event_name: Name of the event (for header display)
        """
        self._event_name = event_name

        # Update header
        if event_name:
            self._header_label.configure(text=f"Finished Goods for {event_name}")
        else:
            self._header_label.configure(text="Select Finished Goods")

        # Clear existing widgets
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()
        self._checkbox_vars.clear()
        self._checkboxes.clear()
        self._fg_data.clear()
        self._quantity_vars.clear()
        self._quantity_entries.clear()
        self._feedback_labels.clear()

        # Handle empty list
        if not finished_goods:
            empty_label = ctk.CTkLabel(
                self._scroll_frame,
                text="No finished goods available",
                font=ctk.CTkFont(size=12, slant="italic"),
            )
            empty_label.pack(pady=20)
            self._update_count()
            return

        # Configure grid columns for scroll frame
        self._scroll_frame.grid_columnconfigure(0, weight=1)  # Checkbox expands
        self._scroll_frame.grid_columnconfigure(1, weight=0)  # Entry fixed width
        self._scroll_frame.grid_columnconfigure(2, weight=0)  # Feedback fixed width

        # Create row for each FG with checkbox, quantity entry, and feedback label
        for i, fg in enumerate(finished_goods):
            # Checkbox variable
            var = ctk.BooleanVar(value=False)
            self._checkbox_vars[fg.id] = var
            self._fg_data[fg.id] = fg

            # Checkbox
            checkbox = ctk.CTkCheckBox(
                self._scroll_frame,
                text=fg.display_name,
                variable=var,
                command=self._update_count,
            )
            checkbox.grid(row=i, column=0, sticky="w", pady=2, padx=5)
            self._checkboxes[fg.id] = checkbox

            # Quantity entry (F071)
            qty_var = ctk.StringVar(value="")
            self._quantity_vars[fg.id] = qty_var
            qty_entry = ctk.CTkEntry(
                self._scroll_frame,
                width=80,
                textvariable=qty_var,
                placeholder_text="Qty",
            )
            qty_entry.grid(row=i, column=1, padx=(10, 0), pady=2)
            self._quantity_entries[fg.id] = qty_entry

            # Bind validation on text change
            qty_var.trace_add("write", lambda *args, fid=fg.id: self._validate_quantity(fid))

            # Feedback label for validation messages
            feedback_label = ctk.CTkLabel(
                self._scroll_frame,
                text="",
                width=100,
                anchor="w",
            )
            feedback_label.grid(row=i, column=2, padx=(5, 0), pady=2)
            self._feedback_labels[fg.id] = feedback_label

        # Update count display
        self._update_count()

    def set_selected(self, fg_ids: List[int]) -> None:
        """
        Set which FGs are selected (checkbox only, no quantities).

        Args:
            fg_ids: List of FG IDs to mark as selected
        """
        selected_set = set(fg_ids)
        for fg_id, var in self._checkbox_vars.items():
            var.set(fg_id in selected_set)
            # Clear quantities for unselected items
            if fg_id not in selected_set and fg_id in self._quantity_vars:
                self._quantity_vars[fg_id].set("")
        self._update_count()

    def set_selected_with_quantities(
        self, fg_quantities: List[Tuple[int, int]]
    ) -> None:
        """
        Set selected FGs with their quantities (F071).

        Args:
            fg_quantities: List of (fg_id, quantity) tuples
        """
        # Create lookup for quantities
        qty_lookup = {fg_id: qty for fg_id, qty in fg_quantities}

        for fg_id, checkbox_var in self._checkbox_vars.items():
            if fg_id in qty_lookup:
                # Check the checkbox and set quantity
                checkbox_var.set(True)
                if fg_id in self._quantity_vars:
                    self._quantity_vars[fg_id].set(str(qty_lookup[fg_id]))
            else:
                # Uncheck and clear quantity
                checkbox_var.set(False)
                if fg_id in self._quantity_vars:
                    self._quantity_vars[fg_id].set("")

        self._update_count()

    def get_selected(self) -> List[Tuple[int, int]]:
        """
        Get selected FGs with their quantities (F071).

        Returns:
            List of (fg_id, quantity) tuples for FGs with valid quantities.
            FGs with checked checkbox but empty or invalid quantities are excluded.
        """
        result = []
        for fg_id, checkbox_var in self._checkbox_vars.items():
            # Only include if checkbox is checked
            if not checkbox_var.get():
                continue

            # Get quantity value
            qty_var = self._quantity_vars.get(fg_id)
            if qty_var is None:
                continue

            qty_text = qty_var.get().strip()

            # Skip empty quantities
            if not qty_text:
                continue

            # Skip invalid quantities
            try:
                qty = int(qty_text)
                if qty > 0:
                    result.append((fg_id, qty))
            except ValueError:
                continue  # Skip invalid entries

        return result

    def get_selected_ids(self) -> List[int]:
        """
        Get list of selected FG IDs (checkbox only, ignores quantity validation).

        This is a backward-compatible method for callers that only need IDs.

        Returns:
            List of FG IDs that are currently checked
        """
        return [fg_id for fg_id, var in self._checkbox_vars.items() if var.get()]

    def has_validation_errors(self) -> bool:
        """
        Check if any checked FG has an invalid quantity.

        Returns:
            True if any checked FG has empty, zero, negative, or non-integer quantity.
        """
        for fg_id, checkbox_var in self._checkbox_vars.items():
            if not checkbox_var.get():
                continue

            qty_var = self._quantity_vars.get(fg_id)
            if qty_var is None:
                return True

            qty_text = qty_var.get().strip()
            if not qty_text:
                return True  # Checked but no quantity

            try:
                qty = int(qty_text)
                if qty <= 0:
                    return True
            except ValueError:
                return True

        return False

    def _validate_quantity(self, fg_id: int) -> None:
        """
        Validate quantity input and show feedback (F071).

        Args:
            fg_id: The finished good ID to validate
        """
        qty_var = self._quantity_vars.get(fg_id)
        feedback_label = self._feedback_labels.get(fg_id)

        if qty_var is None or feedback_label is None:
            return

        qty_text = qty_var.get().strip()

        # Empty is valid (FG not selected or quantity not yet entered)
        if not qty_text:
            feedback_label.configure(text="", text_color=("gray60", "gray40"))
            return

        try:
            qty = int(qty_text)
            if qty <= 0:
                feedback_label.configure(text="Must be > 0", text_color="orange")
            else:
                # Valid - clear feedback
                feedback_label.configure(text="", text_color=("gray60", "gray40"))
        except ValueError:
            feedback_label.configure(text="Integer only", text_color="orange")

    def _update_count(self) -> None:
        """Update the count label with current selection."""
        selected_count = sum(1 for var in self._checkbox_vars.values() if var.get())
        total_count = len(self._checkbox_vars)
        self._count_label.configure(text=f"{selected_count} of {total_count} selected")

    def _handle_save(self) -> None:
        """Handle Save button click."""
        if self._on_save:
            selected_with_quantities = self.get_selected()
            self._on_save(selected_with_quantities)

    def _handle_cancel(self) -> None:
        """Handle Cancel button click."""
        if self._on_cancel:
            self._on_cancel()
