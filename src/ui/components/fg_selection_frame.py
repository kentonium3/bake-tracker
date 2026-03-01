"""
FGSelectionFrame - UI component for selecting finished goods.

Part of F070: Finished Goods Filtering for Event Planning.
Enhanced in F071: Finished Goods Quantity Specification.
Enhanced in F100/WP03: Filter-first with persistence.
"""

from typing import Callable, Dict, List, Optional, Set, Tuple

import customtkinter as ctk

from src.models.finished_good import FinishedGood
from src.services import event_service
from src.services.database import session_scope


class FGSelectionFrame(ctk.CTkFrame):
    """
    Frame for selecting finished goods from available list.

    Displays filter dropdowns (recipe category, item type, yield type),
    checkboxes for each available FG with quantity input fields,
    live count, and Save/Cancel buttons.

    Filter-first pattern: starts blank until at least one filter is applied.
    Selections and quantities persist across filter changes.
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

        # Track checkboxes and their variables (visible widgets only)
        self._checkbox_vars: Dict[int, ctk.BooleanVar] = {}  # fg_id -> BooleanVar
        self._checkboxes: Dict[int, ctk.CTkCheckBox] = {}  # fg_id -> checkbox widget
        self._fg_data: Dict[int, FinishedGood] = {}  # fg_id -> FG object

        # Track quantity inputs (F071) -- visible widgets only
        self._quantity_vars: Dict[int, ctk.StringVar] = {}  # fg_id -> StringVar
        self._quantity_entries: Dict[int, ctk.CTkEntry] = {}  # fg_id -> entry widget
        self._feedback_labels: Dict[int, ctk.CTkLabel] = {}  # fg_id -> feedback label

        # Event context
        self._event_name: str = ""
        self._event_id: Optional[int] = None

        # Filter state
        self._current_recipe_category: Optional[str] = None
        self._current_assembly_type: Optional[str] = None
        self._current_yield_type: Optional[str] = None

        # Selection persistence (survives filter changes)
        self._selected_fg_ids: Set[int] = set()
        self._fg_quantities: Dict[int, int] = {}  # fg_id -> int quantity

        # Flag to suppress trace callbacks during restore
        self._restoring: bool = False

        # Show-selected-only mode (T016)
        self._show_selected_only: bool = False

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
        self._count_label.pack(pady=(0, 5), padx=10, anchor="w")

        # Filter frame with three dropdowns
        self._filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._filter_frame.pack(fill="x", padx=10, pady=(0, 5))

        # Row 1: Recipe Category
        cat_row = ctk.CTkFrame(self._filter_frame, fg_color="transparent")
        cat_row.pack(fill="x", pady=2)
        ctk.CTkLabel(cat_row, text="Recipe Category:", width=120, anchor="w").pack(
            side="left"
        )
        self._recipe_cat_var = ctk.StringVar(value="")
        self._recipe_cat_dropdown = ctk.CTkComboBox(
            cat_row,
            variable=self._recipe_cat_var,
            values=[],
            command=self._on_filter_change,
            width=200,
            state="readonly",
        )
        self._recipe_cat_dropdown.pack(side="left", padx=5)

        # Row 2: Item Type
        type_row = ctk.CTkFrame(self._filter_frame, fg_color="transparent")
        type_row.pack(fill="x", pady=2)
        ctk.CTkLabel(type_row, text="Item Type:", width=120, anchor="w").pack(
            side="left"
        )
        self._item_type_var = ctk.StringVar(value="")
        self._item_type_dropdown = ctk.CTkComboBox(
            type_row,
            variable=self._item_type_var,
            values=["All Types", "Finished Units", "Assemblies"],
            command=self._on_filter_change,
            width=200,
            state="readonly",
        )
        self._item_type_dropdown.pack(side="left", padx=5)

        # Row 3: Yield Type
        yield_row = ctk.CTkFrame(self._filter_frame, fg_color="transparent")
        yield_row.pack(fill="x", pady=2)
        ctk.CTkLabel(yield_row, text="Yield Type:", width=120, anchor="w").pack(
            side="left"
        )
        self._yield_type_var = ctk.StringVar(value="")
        self._yield_type_dropdown = ctk.CTkComboBox(
            yield_row,
            variable=self._yield_type_var,
            values=["All Yields", "EA", "SERVING"],
            command=self._on_filter_change,
            width=200,
            state="readonly",
        )
        self._yield_type_dropdown.pack(side="left", padx=5)

        # Toggle frame for "Show All Selected" button (T016)
        self._toggle_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._toggle_frame.pack(fill="x", padx=10, pady=(0, 5))

        self._show_selected_button = ctk.CTkButton(
            self._toggle_frame,
            text="Show All Selected",
            width=150,
            command=self._toggle_show_selected,
        )
        self._show_selected_button.pack(side="left")

        self._selected_indicator = ctk.CTkLabel(
            self._toggle_frame,
            text="",
            font=ctk.CTkFont(size=11),
        )
        self._selected_indicator.pack(side="left", padx=10)

        # Scrollable frame for checkboxes
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            height=200,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Placeholder label (shown until filters are applied)
        self._placeholder_label = ctk.CTkLabel(
            self._scroll_frame,
            text="Select filters to see available finished goods",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=("gray50", "gray60"),
        )
        self._placeholder_label.pack(pady=40)

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

    def set_event(self, event_id: int, event_name: str = "") -> None:
        """
        Set the event context and populate filter options.

        Args:
            event_id: The event ID to set context for
            event_name: Event name for header display
        """
        self._event_id = event_id
        self._event_name = event_name

        # Update header
        if event_name:
            self._header_label.configure(text=f"Finished Goods for {event_name}")
        else:
            self._header_label.configure(text="Select Finished Goods")

        # Reset filter dropdowns
        self._recipe_cat_var.set("")
        self._item_type_var.set("")
        self._yield_type_var.set("")

        # Populate recipe category dropdown from service
        with session_scope() as session:
            categories = event_service.get_available_recipe_categories_for_event(
                event_id, session
            )
        cat_values = ["All Categories"] + categories
        self._recipe_cat_dropdown.configure(values=cat_values)

        # Show placeholder (blank start)
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        """Show placeholder text and clear visible FG widgets."""
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()
        self._checkbox_vars.clear()
        self._checkboxes.clear()
        self._fg_data.clear()
        self._quantity_vars.clear()
        self._quantity_entries.clear()
        self._feedback_labels.clear()

        self._placeholder_label = ctk.CTkLabel(
            self._scroll_frame,
            text="Select filters to see available finished goods",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=("gray50", "gray60"),
        )
        self._placeholder_label.pack(pady=40)
        self._update_count()
        self._update_save_button_state()

    def _on_filter_change(self, choice: str) -> None:
        """
        Handle any filter dropdown change.

        Reads all current filter values, queries the service layer,
        and re-renders the FG list with persistence restoration.

        Args:
            choice: The selected dropdown value (unused directly;
                    we read all vars for AND-combination)
        """
        # Exit show-selected mode if active (T018/FR-012)
        if self._show_selected_only:
            self._show_selected_only = False
            self._show_selected_button.configure(text="Show All Selected")
            self._selected_indicator.configure(text="")


        if self._event_id is None:
            return

        # Read current filter values
        recipe_cat = self._recipe_cat_var.get()
        item_type = self._item_type_var.get()
        yield_type = self._yield_type_var.get()

        # Check if at least one filter is set (FR-007)
        if not recipe_cat and not item_type and not yield_type:
            return  # Keep showing placeholder

        # Convert display values to service parameters
        cat_param = None if recipe_cat in ("", "All Categories") else recipe_cat
        type_param = None
        if item_type == "Finished Units":
            type_param = "bare"
        elif item_type == "Assemblies":
            type_param = "bundle"
        yield_param = None if yield_type in ("", "All Yields") else yield_type

        # Save current selections before re-render
        self._save_current_selections()

        # Query service
        with session_scope() as session:
            fgs = event_service.get_filtered_available_fgs(
                self._event_id,
                session,
                recipe_category=cat_param,
                assembly_type=type_param,
                yield_type=yield_param,
            )

        self._render_finished_goods(fgs)

    def _render_finished_goods(self, finished_goods: List[FinishedGood]) -> None:
        """
        Render FG rows in the scroll frame, restoring persisted selections.

        This replaces the direct rendering in populate_finished_goods() and
        is called after filter changes.

        Args:
            finished_goods: List of FinishedGood objects to display
        """
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
                text="No finished goods match the selected filters",
                font=ctk.CTkFont(size=12, slant="italic"),
            )
            empty_label.pack(pady=20)
            self._update_count()
            return

        # Set restoring flag to suppress trace callbacks during setup
        self._restoring = True

        try:
            # Configure grid columns for scroll frame
            self._scroll_frame.grid_columnconfigure(0, weight=1)  # Checkbox expands
            self._scroll_frame.grid_columnconfigure(1, weight=0)  # Entry fixed width
            self._scroll_frame.grid_columnconfigure(2, weight=0)  # Feedback fixed

            # Create row for each FG with checkbox, quantity entry, and feedback label
            for i, fg in enumerate(finished_goods):
                # Restore selection state from persistence
                var = ctk.BooleanVar(value=fg.id in self._selected_fg_ids)
                self._checkbox_vars[fg.id] = var
                self._fg_data[fg.id] = fg

                # Checkbox with persistence-aware toggle
                checkbox = ctk.CTkCheckBox(
                    self._scroll_frame,
                    text=fg.display_name,
                    variable=var,
                    command=lambda fid=fg.id: self._on_checkbox_toggle(fid),
                )
                checkbox.grid(row=i, column=0, sticky="w", pady=2, padx=5)
                self._checkboxes[fg.id] = checkbox

                # Quantity entry (F071) -- restore from persistence
                qty_var = ctk.StringVar(value="")
                if fg.id in self._fg_quantities:
                    qty_var.set(str(self._fg_quantities[fg.id]))
                self._quantity_vars[fg.id] = qty_var

                qty_entry = ctk.CTkEntry(
                    self._scroll_frame,
                    width=80,
                    textvariable=qty_var,
                    placeholder_text="Qty",
                )
                qty_entry.grid(row=i, column=1, padx=(10, 0), pady=2)
                self._quantity_entries[fg.id] = qty_entry

                # Bind validation and persistence on text change
                qty_var.trace_add(
                    "write",
                    lambda *args, fid=fg.id: self._on_quantity_change(fid),
                )

                # Feedback label for validation messages
                feedback_label = ctk.CTkLabel(
                    self._scroll_frame,
                    text="",
                    width=100,
                    anchor="w",
                )
                feedback_label.grid(row=i, column=2, padx=(5, 0), pady=2)
                self._feedback_labels[fg.id] = feedback_label
        finally:
            self._restoring = False

        # Update count display and save button state
        self._update_count()
        self._update_save_button_state()

    def populate_finished_goods(
        self,
        finished_goods: List[FinishedGood],
        event_name: str = "",
    ) -> None:
        """
        Populate the frame with finished goods (legacy method).

        Retained for backward compatibility with existing callers.

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

        # Clear persistence state for fresh populate
        self._selected_fg_ids.clear()
        self._fg_quantities.clear()

        self._render_finished_goods(finished_goods)

    def _on_checkbox_toggle(self, fg_id: int) -> None:
        """
        Handle checkbox toggle and update persistence.

        Args:
            fg_id: The finished good ID that was toggled
        """
        var = self._checkbox_vars.get(fg_id)
        if var:
            if var.get():
                self._selected_fg_ids.add(fg_id)
            else:
                self._selected_fg_ids.discard(fg_id)
        self._update_count()
        self._validate_quantity(fg_id)
        self._update_save_button_state()

    def _on_quantity_change(self, fg_id: int) -> None:
        """
        Handle quantity entry change and update persistence.

        Args:
            fg_id: The finished good ID whose quantity changed
        """
        if self._restoring:
            return

        qty_var = self._quantity_vars.get(fg_id)
        if qty_var:
            qty_text = qty_var.get().strip()
            try:
                qty = int(qty_text)
                if qty > 0:
                    self._fg_quantities[fg_id] = qty
            except (ValueError, TypeError):
                pass  # Keep existing quantity in persistence dict
        self._validate_quantity(fg_id)

    def _save_current_selections(self) -> None:
        """Save current UI state to persistence dicts."""
        for fg_id, var in self._checkbox_vars.items():
            if var.get():
                self._selected_fg_ids.add(fg_id)
                # Save quantity if valid
                qty_var = self._quantity_vars.get(fg_id)
                if qty_var:
                    qty_text = qty_var.get().strip()
                    try:
                        qty = int(qty_text)
                        if qty > 0:
                            self._fg_quantities[fg_id] = qty
                    except (ValueError, TypeError):
                        pass  # Keep existing quantity in dict
            else:
                self._selected_fg_ids.discard(fg_id)
                # Don't remove from _fg_quantities -- user might re-check later

    def set_selected(self, fg_ids: List[int]) -> None:
        """
        Set which FGs are selected (checkbox only, no quantities).

        Updates both persistence state and visible checkboxes.

        Args:
            fg_ids: List of FG IDs to mark as selected
        """
        # Update persistence
        self._selected_fg_ids = set(fg_ids)

        # Update visible checkboxes
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
        Set selected FGs with their quantities (F071/F100).

        Updates both persistence state and visible checkboxes/quantities.

        Args:
            fg_quantities: List of (fg_id, quantity) tuples
        """
        # Update persistence state
        self._selected_fg_ids.clear()
        self._fg_quantities.clear()
        for fg_id, qty in fg_quantities:
            self._selected_fg_ids.add(fg_id)
            self._fg_quantities[fg_id] = qty

        # Update visible checkboxes and quantities
        for fg_id, checkbox_var in self._checkbox_vars.items():
            if fg_id in self._selected_fg_ids:
                checkbox_var.set(True)
                if fg_id in self._quantity_vars:
                    self._quantity_vars[fg_id].set(
                        str(self._fg_quantities.get(fg_id, ""))
                    )
            else:
                checkbox_var.set(False)
                if fg_id in self._quantity_vars:
                    self._quantity_vars[fg_id].set("")
        self._update_count()
        self._update_save_button_state()

    def render_saved_selections(self) -> None:
        """
        Render saved selections on initial load (F102).

        Sets up the selected-only view state and renders saved FGs using
        the existing _render_selected_only() method. Called by PlanningTab
        after set_selected_with_quantities() when loading an event with
        existing selections.
        """
        if not self._selected_fg_ids:
            return

        # Enter selected-only mode (same state as _toggle_show_selected)
        self._show_selected_only = True
        self._show_selected_button.configure(text="Show Filtered View")

        # Set contextual indicator label
        count = len(self._selected_fg_ids)
        self._selected_indicator.configure(
            text=f"Saved plan selections ({count} items)"
        )

        # Render only selected FGs (queries DB and calls _render_finished_goods)
        self._render_selected_only()

    def get_selected(self) -> List[Tuple[int, int]]:
        """
        Get ALL selected FGs with their quantities (including hidden ones).

        Returns:
            List of (fg_id, quantity) tuples for FGs with valid quantities.
            Includes FGs selected in other filter views.
        """
        self._save_current_selections()
        return [
            (fg_id, self._fg_quantities.get(fg_id, 0))
            for fg_id in self._selected_fg_ids
            if self._fg_quantities.get(fg_id, 0) > 0
        ]

    def get_selected_ids(self) -> List[int]:
        """
        Get ALL selected FG IDs (including hidden ones).

        Returns:
            List of FG IDs that are currently selected across all filter views
        """
        self._save_current_selections()
        return list(self._selected_fg_ids)

    def has_validation_errors(self) -> bool:
        """
        Check if any checked FG has an invalid quantity.

        Checks both visible and persisted selections.

        Returns:
            True if any selected FG has empty, zero, negative, or non-integer quantity.
        """
        # Save current visible state first
        self._save_current_selections()

        # Check all persisted selections
        for fg_id in self._selected_fg_ids:
            qty = self._fg_quantities.get(fg_id, 0)
            if qty <= 0:
                return True

        # Also check visible items for in-progress edits
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

    def clear_selections(self) -> None:
        """Clear all FG selections and quantities (needed by WP04)."""
        self._selected_fg_ids.clear()
        self._fg_quantities.clear()
        for var in self._checkbox_vars.values():
            var.set(False)
        for qty_var in self._quantity_vars.values():
            qty_var.set("")
        self._update_count()
        self._update_save_button_state()

    def _validate_quantity(self, fg_id: int) -> None:
        """
        Validate quantity input and show spec-mandated error messages (T019).

        Messages match spec US6 exactly:
        - "Quantity required" for empty on checked FG
        - "Enter a valid number" for non-numeric
        - "Whole numbers only" for decimals
        - "Quantity must be positive" for negatives
        - "Quantity must be greater than zero" for zero

        Args:
            fg_id: The finished good ID to validate
        """
        qty_var = self._quantity_vars.get(fg_id)
        feedback_label = self._feedback_labels.get(fg_id)
        checkbox_var = self._checkbox_vars.get(fg_id)

        if qty_var is None or feedback_label is None:
            return

        qty_text = qty_var.get().strip()
        is_checked = checkbox_var.get() if checkbox_var else False

        # If not checked, no validation needed
        if not is_checked:
            feedback_label.configure(text="", text_color=("gray60", "gray40"))
            self._update_save_button_state()
            return

        # Empty quantity on checked item
        if not qty_text:
            feedback_label.configure(text="Quantity required", text_color="orange")
            self._update_save_button_state()
            return

        # Try parsing as float first to detect decimals
        try:
            value = float(qty_text)
        except ValueError:
            feedback_label.configure(text="Enter a valid number", text_color="orange")
            self._update_save_button_state()
            return

        # Check for decimal
        if value != int(value):
            feedback_label.configure(text="Whole numbers only", text_color="orange")
            self._update_save_button_state()
            return

        int_value = int(value)

        # Check for negative
        if int_value < 0:
            feedback_label.configure(text="Quantity must be positive", text_color="orange")
            self._update_save_button_state()
            return

        # Check for zero
        if int_value == 0:
            feedback_label.configure(
                text="Quantity must be greater than zero", text_color="orange"
            )
            self._update_save_button_state()
            return

        # Valid
        feedback_label.configure(text="", text_color=("gray60", "gray40"))
        self._fg_quantities[fg_id] = int_value
        self._update_save_button_state()

    def _update_count(self) -> None:
        """Update the count label with current selection (including hidden)."""
        visible_selected = sum(
            1 for var in self._checkbox_vars.values() if var.get()
        )
        total_visible = len(self._checkbox_vars)
        total_selected = len(self._selected_fg_ids)
        if total_selected > visible_selected:
            self._count_label.configure(
                text=f"{visible_selected} of {total_visible} shown "
                f"({total_selected} total selected)"
            )
        else:
            self._count_label.configure(
                text=f"{visible_selected} of {total_visible} selected"
            )

    def _reset_to_blank(self) -> None:
        """Reset the frame to blank state with placeholder (T015)."""
        # Clear rendered items
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()
        self._checkbox_vars.clear()
        self._checkboxes.clear()
        self._fg_data.clear()
        self._quantity_vars.clear()
        self._quantity_entries.clear()
        self._feedback_labels.clear()

        # Reset filter dropdowns
        self._recipe_cat_var.set("")
        self._item_type_var.set("")
        self._yield_type_var.set("")

        # Exit show-selected mode if active
        self._show_selected_only = False
        self._show_selected_button.configure(text="Show All Selected")
        self._selected_indicator.configure(text="")

        # Show placeholder
        self._placeholder_label = ctk.CTkLabel(
            self._scroll_frame,
            text="Select filters to see available finished goods",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=("gray50", "gray60"),
        )
        self._placeholder_label.pack(pady=40)

        # Reset count
        self._count_label.configure(text="0 of 0 selected")

    def _toggle_show_selected(self) -> None:
        """Toggle between filtered view and selected-only view (T017)."""
        self._save_current_selections()

        if self._show_selected_only:
            # Exit selected-only mode, restore filter view
            self._show_selected_only = False
            self._show_selected_button.configure(text="Show All Selected")
            self._selected_indicator.configure(text="")
            # Re-apply current filters
            self._on_filter_change("")
        else:
            # Enter selected-only mode
            if not self._selected_fg_ids:
                self._selected_indicator.configure(text="No items selected")
                return

            self._show_selected_only = True
            self._show_selected_button.configure(text="Show Filtered View")
            count = len(self._selected_fg_ids)
            self._selected_indicator.configure(text=f"Showing {count} selected items")

            # Render only selected FGs
            self._render_selected_only()

    def _render_selected_only(self) -> None:
        """Render only the currently selected FGs (T017)."""
        if self._event_id is None:
            return

        # Get FG objects for selected IDs
        with session_scope() as session:
            selected_fgs = (
                session.query(FinishedGood)
                .filter(FinishedGood.id.in_(self._selected_fg_ids))
                .all()
            )

        self._render_finished_goods(selected_fgs)

    def _update_save_button_state(self) -> None:
        """Enable/disable Save button based on validation state (T021)."""
        if not self._selected_fg_ids:
            self._save_button.configure(state="disabled")
            return

        if self.has_validation_errors():
            self._save_button.configure(state="disabled")
            return

        self._save_button.configure(state="normal")

    def _handle_save(self) -> None:
        """Handle Save button click."""
        if self._on_save:
            selected_with_quantities = self.get_selected()
            self._on_save(selected_with_quantities)

    def _handle_cancel(self) -> None:
        """Handle Cancel button click."""
        if self._on_cancel:
            self._on_cancel()
