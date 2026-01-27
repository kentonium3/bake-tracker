"""
Planning Tab - Event management for production planning.

Provides a focused interface for planning events, displaying plan_state,
expected_attendees, and supporting CRUD operations.

Feature 068: Event Management & Planning Data Model
Feature 069: Recipe Selection for Event Planning
Feature 070: Finished Goods Filtering for Event Planning
Feature 071: Finished Goods Quantity Specification
Feature 073: Batch Calculation User Decisions
"""

import customtkinter as ctk
from typing import Optional, Callable, List, Any, Tuple

from src.models import Event, PlanState
from src.services import event_service, recipe_service
from src.services.event_service import RemovedFGInfo
from src.services.database import session_scope
from src.utils.constants import (
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.data_table import DataTable
from src.ui.widgets.dialogs import show_confirmation
from src.ui.widgets.batch_options_frame import BatchOptionsFrame
from src.ui.components.recipe_selection_frame import RecipeSelectionFrame
from src.ui.components.fg_selection_frame import FGSelectionFrame
from src.services.planning_service import calculate_batch_options
from src.services.batch_decision_service import (
    save_batch_decision,
    get_batch_decisions,
    delete_batch_decisions,
    BatchDecisionInput,
)
from src.services.exceptions import ValidationError


class PlanningEventDataTable(DataTable):
    """
    Specialized data table for displaying planning events.

    Shows columns: Name, Date, Attendees, Plan State
    """

    def __init__(
        self,
        parent,
        select_callback: Optional[Callable[[Any], None]] = None,
        double_click_callback: Optional[Callable[[Any], None]] = None,
        height: int = 500,
    ):
        """
        Initialize planning event data table.

        Args:
            parent: Parent widget
            select_callback: Callback for row selection
            double_click_callback: Callback for row double-click
            height: Height of the table in pixels
        """
        columns = [
            ("Name", 250),
            ("Date", 120),
            ("Attendees", 100),
            ("Plan State", 140),
        ]
        super().__init__(
            parent,
            columns=columns,
            on_row_select=select_callback,
            on_row_double_click=double_click_callback,
            height=height,
        )

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract planning event-specific row values.

        Args:
            row_data: Event object

        Returns:
            List of formatted values for display
        """
        # Format date
        if row_data.event_date:
            date_str = row_data.event_date.strftime("%Y-%m-%d")
        else:
            date_str = "-"

        # Format attendees (display "-" for NULL)
        if row_data.expected_attendees is not None:
            attendees_str = str(row_data.expected_attendees)
        else:
            attendees_str = "-"

        # Format plan state (e.g., "in_production" -> "In Production")
        if row_data.plan_state:
            state_str = row_data.plan_state.value.replace("_", " ").title()
        else:
            state_str = "-"

        return [
            row_data.name or "",
            date_str,
            attendees_str,
            state_str,
        ]


class PlanningTab(ctk.CTkFrame):
    """
    Planning workspace tab for event management.

    Displays list of events with planning-related fields and provides
    CRUD actions for event management.
    """

    def __init__(
        self,
        parent,
        on_create_event: Optional[Callable] = None,
        on_edit_event: Optional[Callable[[Event], None]] = None,
        on_delete_event: Optional[Callable[[Event], None]] = None,
        **kwargs,
    ):
        """
        Initialize Planning tab.

        Args:
            parent: Parent widget
            on_create_event: Callback when Create button clicked
            on_edit_event: Callback when Edit button clicked (receives Event)
            on_delete_event: Callback when Delete button clicked (receives Event)
        """
        super().__init__(parent, **kwargs)

        self.selected_event: Optional[Event] = None
        self._selected_event_id: Optional[int] = None
        self._original_recipe_selection: List[int] = []
        # F070/F071: FG selection state with quantities
        self._original_fg_selection: List[Tuple[int, int]] = []
        # F073: Batch decision state
        self._confirmed_shortfalls: set = set()
        self._has_unsaved_batch_changes: bool = False

        # Store callbacks
        self._on_create_event = on_create_event
        self._on_edit_event = on_edit_event
        self._on_delete_event = on_delete_event

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Action buttons
        self.grid_rowconfigure(1, weight=1)  # Data table
        self.grid_rowconfigure(2, weight=0)  # Recipe selection frame
        self.grid_rowconfigure(3, weight=0)  # FG selection frame (F070)
        self.grid_rowconfigure(4, weight=0)  # Batch options frame (F073)
        self.grid_rowconfigure(5, weight=0)  # Status bar

        # Build UI
        self._create_action_buttons()
        self._create_data_table()
        self._create_recipe_selection_frame()
        self._create_fg_selection_frame()
        self._create_batch_options_frame()
        self._create_status_bar()

        # Layout widgets
        self._layout_widgets()

        # Grid the frame (consistent with other tabs)
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Load initial data
        self.refresh()

    def _create_action_buttons(self) -> None:
        """Create action buttons for CRUD operations."""
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")

        # Create button - always enabled
        self.create_button = ctk.CTkButton(
            self.button_frame,
            text="Create Event",
            command=self._on_create_click,
            width=140,
        )

        # Edit button - enabled when event selected
        self.edit_button = ctk.CTkButton(
            self.button_frame,
            text="Edit Event",
            command=self._on_edit_click,
            width=120,
            state="disabled",
        )

        # Delete button - enabled when event selected, styled red
        self.delete_button = ctk.CTkButton(
            self.button_frame,
            text="Delete Event",
            command=self._on_delete_click,
            width=120,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )

        # Refresh button
        self.refresh_button = ctk.CTkButton(
            self.button_frame,
            text="Refresh",
            command=self.refresh,
            width=100,
        )

    def _create_data_table(self) -> None:
        """Create the data table for displaying events."""
        self.data_table = PlanningEventDataTable(
            self,
            select_callback=self._on_row_select,
            double_click_callback=self._on_row_double_click,
        )

    def _create_recipe_selection_frame(self) -> None:
        """Create the recipe selection frame (initially hidden)."""
        self._recipe_selection_frame = RecipeSelectionFrame(
            self,
            on_save=self._on_recipe_selection_save,
            on_cancel=self._on_recipe_selection_cancel,
        )
        # Frame starts hidden - will be shown when event is selected

    def _create_fg_selection_frame(self) -> None:
        """Create the FG selection frame (initially hidden)."""
        self._fg_selection_frame = FGSelectionFrame(
            self,
            on_save=self._on_fg_selection_save,
            on_cancel=self._on_fg_selection_cancel,
        )
        # Frame starts hidden - will be shown when event is selected

    def _create_batch_options_frame(self) -> None:
        """Create the batch options frame (F073, initially hidden)."""
        # Create container frame for label, widget, and save button
        self._batch_options_container = ctk.CTkFrame(self)

        # Section label
        self._batch_options_label = ctk.CTkLabel(
            self._batch_options_container,
            text="Batch Options",
            font=ctk.CTkFont(weight="bold", size=16),
            anchor="w",
        )
        self._batch_options_label.pack(anchor="w", padx=10, pady=(10, 5))

        # BatchOptionsFrame widget
        self._batch_options_frame = BatchOptionsFrame(
            self._batch_options_container,
            on_selection_change=self._on_batch_selection_change,
            height=200,
        )
        self._batch_options_frame.pack(fill="x", padx=10, pady=5)

        # Save button
        self._save_batches_button = ctk.CTkButton(
            self._batch_options_container,
            text="Save Batch Decisions",
            command=self._save_batch_decisions,
            width=180,
        )
        self._save_batches_button.pack(anchor="e", padx=10, pady=10)
        # Frame starts hidden

    def _create_status_bar(self) -> None:
        """Create status bar for displaying feedback."""
        self.status_frame = ctk.CTkFrame(self, height=30)
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            anchor="w",
        )

    def _layout_widgets(self) -> None:
        """Position widgets using grid layout."""
        # Button frame at top
        self.button_frame.grid(
            row=0, column=0, sticky="ew",
            padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM)
        )
        self.create_button.pack(side="left", padx=PADDING_MEDIUM)
        self.edit_button.pack(side="left", padx=PADDING_MEDIUM)
        self.delete_button.pack(side="left", padx=PADDING_MEDIUM)
        self.refresh_button.pack(side="right", padx=PADDING_MEDIUM)

        # Data table takes remaining space
        self.data_table.grid(
            row=1, column=0, sticky="nsew",
            padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

        # Recipe selection frame - row 2 (initially not gridded, shown when event selected)
        # Note: _recipe_selection_frame.grid() is called in _show_recipe_selection()

        # FG selection frame - row 3 (initially not gridded, shown when event selected)
        # Note: _fg_selection_frame.grid() is called in _show_fg_selection()

        # Batch options frame - row 4 (F073, initially not gridded)
        # Note: _batch_options_container.grid() is called in _show_batch_options()

        # Status bar at bottom (row 5)
        self.status_frame.grid(
            row=5, column=0, sticky="ew",
            padx=PADDING_LARGE, pady=(0, PADDING_LARGE)
        )
        self.status_frame.grid_columnconfigure(0, weight=1)
        self.status_label.grid(
            row=0, column=0, sticky="w",
            padx=PADDING_MEDIUM, pady=5
        )

    def refresh(self) -> None:
        """Refresh the event list from database."""
        try:
            with session_scope() as session:
                events = event_service.get_events_for_planning(session)

                # Store data for display
                self.data_table.set_data(events)

                self._update_status(f"Loaded {len(events)} event(s)")

        except Exception as e:
            self._update_status(f"Error loading events: {e}", is_error=True)

        # Clear selection and hide recipe/FG/batch selection
        self.selected_event = None
        self._selected_event_id = None
        self._hide_recipe_selection()
        self._hide_fg_selection()
        self._hide_batch_options()
        self._update_button_states()

    def _on_row_select(self, event: Optional[Event]) -> None:
        """
        Handle row selection.

        Args:
            event: Selected Event object (None if deselected)
        """
        if event is not None:
            # Re-query to get attached object for session safety
            with session_scope() as session:
                self.selected_event = session.query(Event).filter(
                    Event.id == event.id
                ).first()
                # Detach from session for use in callbacks
                if self.selected_event:
                    session.expunge(self.selected_event)
        else:
            self.selected_event = None

        self._update_button_states()

        if self.selected_event:
            self._update_status(f"Selected: {self.selected_event.name}")
            self._selected_event_id = self.selected_event.id
            self._show_recipe_selection(self.selected_event.id)
            self._show_fg_selection(self.selected_event.id)
            self._show_batch_options(self.selected_event.id)
        else:
            self._update_status("Ready")
            self._selected_event_id = None
            self._hide_recipe_selection()
            self._hide_fg_selection()
            self._hide_batch_options()

    def _show_recipe_selection(self, event_id: int) -> None:
        """
        Show and populate recipe selection for an event.

        Args:
            event_id: ID of the selected event
        """
        try:
            with session_scope() as session:
                # Get event name
                event = event_service.get_event_by_id(event_id, session=session)
                event_name = event.name if event else ""

                # Get all recipes for selection (non-archived only)
                recipes = recipe_service.get_all_recipes(include_archived=False)

                # Get existing selections
                selected_ids = event_service.get_event_recipe_ids(session, event_id)

            # Populate frame
            self._recipe_selection_frame.populate_recipes(recipes, event_name)
            self._recipe_selection_frame.set_selected(selected_ids)

            # Store for cancel functionality
            self._original_recipe_selection = selected_ids.copy()

            # Show frame using grid
            self._recipe_selection_frame.grid(
                row=2, column=0, sticky="ew",
                padx=PADDING_LARGE, pady=PADDING_MEDIUM
            )

        except Exception as e:
            self._update_status(f"Error loading recipes: {e}", is_error=True)

    def _hide_recipe_selection(self) -> None:
        """Hide the recipe selection frame."""
        self._recipe_selection_frame.grid_forget()
        self._original_recipe_selection = []

    def _on_recipe_selection_save(self, selected_ids: List[int]) -> None:
        """
        Handle recipe selection save.

        F070: Also refreshes FG selection and shows notification for removed FGs.

        Args:
            selected_ids: List of selected recipe IDs
        """
        if self._selected_event_id is None:
            self._update_status("No event selected", is_error=True)
            return

        try:
            with session_scope() as session:
                count, removed_fgs = event_service.set_event_recipes(
                    session,
                    self._selected_event_id,
                    selected_ids,
                )
                session.commit()

            # Update original selection (for future cancel)
            self._original_recipe_selection = selected_ids.copy()

            # F070: Show notification for auto-removed FGs
            if removed_fgs:
                self._show_removed_fg_notification(removed_fgs)
            else:
                # Show success feedback
                self._update_status(f"Saved {count} recipe selection(s)")

            # F070: Refresh FG selection to show available FGs
            self._refresh_fg_selection()

        except Exception as e:
            # Show error but keep UI state
            self._update_status(f"Error saving: {e}", is_error=True)

    def _on_recipe_selection_cancel(self) -> None:
        """Handle recipe selection cancel - revert to last saved state."""
        self._recipe_selection_frame.set_selected(self._original_recipe_selection)
        self._update_status("Reverted to saved recipe selections")

    # =========================================================================
    # F070: Finished Good Selection
    # =========================================================================

    def _show_fg_selection(self, event_id: int) -> None:
        """
        Show and populate FG selection for an event.

        F071: Now loads quantities via get_event_fg_quantities().

        Args:
            event_id: ID of the selected event
        """
        try:
            with session_scope() as session:
                # Get event name
                event = event_service.get_event_by_id(event_id, session=session)
                event_name = event.name if event else ""

                # Get available FGs (filtered by selected recipes)
                available_fgs = event_service.get_available_finished_goods(
                    event_id, session
                )

                # F071: Get existing selections with quantities
                fg_quantities = event_service.get_event_fg_quantities(
                    session, event_id
                )

            # Populate frame
            self._fg_selection_frame.populate_finished_goods(available_fgs, event_name)

            # F071: Set quantities (converts from (FG, qty) to (fg_id, qty) tuples)
            qty_tuples = [(fg.id, qty) for fg, qty in fg_quantities]
            self._fg_selection_frame.set_selected_with_quantities(qty_tuples)

            # Store for cancel functionality
            self._original_fg_selection = qty_tuples.copy()

            # Show frame using grid
            self._fg_selection_frame.grid(
                row=3, column=0, sticky="ew",
                padx=PADDING_LARGE, pady=PADDING_MEDIUM
            )

        except Exception as e:
            self._update_status(f"Error loading finished goods: {e}", is_error=True)

    def _hide_fg_selection(self) -> None:
        """Hide the FG selection frame."""
        self._fg_selection_frame.grid_forget()
        self._original_fg_selection = []

    def _refresh_fg_selection(self) -> None:
        """Refresh FG selection after recipe change."""
        if self._selected_event_id is not None:
            self._show_fg_selection(self._selected_event_id)

    def _on_fg_selection_save(self, fg_quantities: List[Tuple[int, int]]) -> None:
        """
        Handle FG selection save with quantities.

        F071: Now saves quantities via set_event_fg_quantities().

        Args:
            fg_quantities: List of (fg_id, quantity) tuples
        """
        if self._selected_event_id is None:
            self._update_status("No event selected", is_error=True)
            return

        # F071: Check for validation errors before saving
        if self._fg_selection_frame.has_validation_errors():
            self._update_status(
                "Please fix invalid quantities before saving", is_error=True
            )
            return

        try:
            with session_scope() as session:
                count = event_service.set_event_fg_quantities(
                    session,
                    self._selected_event_id,
                    fg_quantities,
                )
                session.commit()

            # Update original selection (for future cancel)
            self._original_fg_selection = list(fg_quantities)

            # Show success feedback
            self._update_status(f"Saved {count} finished good(s)")

        except Exception as e:
            # Show error but keep UI state
            self._update_status(f"Error saving: {e}", is_error=True)

    def _on_fg_selection_cancel(self) -> None:
        """Handle FG selection cancel - revert to last saved state."""
        # F071: Use set_selected_with_quantities for quantities
        self._fg_selection_frame.set_selected_with_quantities(
            self._original_fg_selection
        )
        self._update_status("Reverted to saved FG selections")

    def _show_removed_fg_notification(self, removed_fgs: List[RemovedFGInfo]) -> None:
        """
        Show notification about auto-removed FG selections.

        Args:
            removed_fgs: List of RemovedFGInfo for removed FGs
        """
        if len(removed_fgs) == 1:
            fg = removed_fgs[0]
            missing = ", ".join(fg.missing_recipes)
            message = f"Removed '{fg.fg_name}' - requires: {missing}"
        else:
            names = ", ".join(fg.fg_name for fg in removed_fgs)
            message = f"Removed {len(removed_fgs)} FGs: {names}"

        # Show as error-style to draw attention (orange would be ideal but red is available)
        self._update_status(message, is_error=True)

    # =========================================================================
    # F073: Batch Options
    # =========================================================================

    def _show_batch_options(self, event_id: int) -> None:
        """
        Show and populate batch options for an event.

        Args:
            event_id: ID of the selected event
        """
        self._load_batch_options()

        # Show container using grid
        self._batch_options_container.grid(
            row=4, column=0, sticky="ew",
            padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

    def _hide_batch_options(self) -> None:
        """Hide the batch options frame."""
        self._batch_options_container.grid_forget()
        self._batch_options_frame.clear()
        self._confirmed_shortfalls.clear()
        self._has_unsaved_batch_changes = False

    def _load_batch_options(self) -> None:
        """Load batch options for the currently selected event."""
        if self._selected_event_id is None:
            self._batch_options_frame.clear()
            return

        try:
            # Calculate options from F073
            options_results = calculate_batch_options(self._selected_event_id)

            # Populate the widget
            self._batch_options_frame.populate(options_results)

            # Load existing decisions and pre-select
            self._load_existing_decisions()

            # Reset unsaved changes flag
            self._has_unsaved_batch_changes = False
            self._update_save_button_state()

        except Exception as e:
            self._update_status(f"Failed to load batch options: {e}", is_error=True)

    def _load_existing_decisions(self) -> None:
        """Load existing batch decisions and pre-select options."""
        if self._selected_event_id is None:
            return

        try:
            decisions = get_batch_decisions(self._selected_event_id)

            for decision in decisions:
                self._batch_options_frame.set_selection(
                    decision.finished_unit_id,
                    decision.batches,
                )

        except Exception as e:
            # Log but don't fail - just means no pre-selection
            print(f"Warning: Could not load existing decisions: {e}")

    def _on_batch_selection_change(self, fu_id: int, batches: int) -> None:
        """
        Handle batch selection change.

        Shows confirmation dialog if shortfall option selected.

        Args:
            fu_id: FinishedUnit ID
            batches: Number of batches selected
        """
        # Check if this is a shortfall selection
        selections = self._batch_options_frame.get_selection_with_shortfall_info()
        selection = next(
            (s for s in selections if s["finished_unit_id"] == fu_id), None
        )

        if selection and selection["is_shortfall"]:
            # Show confirmation dialog
            confirmed = show_confirmation(
                "Shortfall Warning",
                "This selection will produce fewer items than needed.\n\n"
                "You will be short. Do you want to proceed with this selection?",
                parent=self,
            )

            if not confirmed:
                # User cancelled - clear selection
                self._batch_options_frame.set_selection(fu_id, 0)
                return

            # Mark as confirmed for save
            self._confirmed_shortfalls.add(fu_id)
        else:
            # Not a shortfall, remove from confirmed set if present
            self._confirmed_shortfalls.discard(fu_id)

        # Mark as having unsaved changes
        self._has_unsaved_batch_changes = True
        self._update_save_button_state()

    def _update_save_button_state(self) -> None:
        """Update save button to indicate unsaved changes."""
        if self._has_unsaved_batch_changes:
            self._save_batches_button.configure(text="Save Batch Decisions *")
        else:
            self._save_batches_button.configure(text="Save Batch Decisions")

    def _save_batch_decisions(self) -> None:
        """Save all batch decisions for the current event."""
        if self._selected_event_id is None:
            return

        selections = self._batch_options_frame.get_selection_with_shortfall_info()

        if not selections:
            self._update_status("No batch selections to save.")
            return

        try:
            # Clear existing decisions first (replace pattern)
            delete_batch_decisions(self._selected_event_id)

            # Save each decision
            for selection in selections:
                is_shortfall = selection["is_shortfall"]
                fu_id = selection["finished_unit_id"]
                decision = BatchDecisionInput(
                    finished_unit_id=fu_id,
                    batches=selection["batches"],
                    is_shortfall=is_shortfall,
                    confirmed_shortfall=fu_id in self._confirmed_shortfalls if is_shortfall else False,
                )
                save_batch_decision(self._selected_event_id, decision)

            self._update_status("Batch decisions saved successfully.")

            # Reset unsaved indicator on success
            self._has_unsaved_batch_changes = False
            self._update_save_button_state()

        except ValidationError as e:
            self._update_status(f"Validation error: {e}", is_error=True)
        except Exception as e:
            self._update_status(f"Failed to save batch decisions: {e}", is_error=True)

    def _on_row_double_click(self, event: Event) -> None:
        """
        Handle row double-click (opens edit).

        Args:
            event: Double-clicked Event object
        """
        self._on_row_select(event)
        if self.selected_event and self._on_edit_event:
            self._on_edit_event(self.selected_event)

    def _update_button_states(self) -> None:
        """Update button enabled/disabled states based on selection."""
        has_selection = self.selected_event is not None

        self.edit_button.configure(state="normal" if has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")

    def _update_status(self, message: str, is_error: bool = False) -> None:
        """
        Update status bar message.

        Args:
            message: Status message to display
            is_error: If True, display in red color
        """
        color = "red" if is_error else ("gray60", "gray40")
        self.status_label.configure(text=message, text_color=color)

        # Auto-clear after delay (only for non-error messages)
        if message and not is_error:
            self.after(5000, lambda: self._clear_status_if_unchanged(message))

    def _clear_status_if_unchanged(self, original_message: str) -> None:
        """Clear status if it hasn't changed since scheduling the clear."""
        if self.status_label.cget("text") == original_message:
            self.status_label.configure(text="Ready", text_color=("gray60", "gray40"))

    def _on_create_click(self) -> None:
        """Handle Create button click."""
        if self._on_create_event:
            self._on_create_event()

    def _on_edit_click(self) -> None:
        """Handle Edit button click."""
        if self.selected_event and self._on_edit_event:
            self._on_edit_event(self.selected_event)

    def _on_delete_click(self) -> None:
        """Handle Delete button click."""
        if self.selected_event and self._on_delete_event:
            self._on_delete_event(self.selected_event)
