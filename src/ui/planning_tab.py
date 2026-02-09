"""
Planning Tab - Event management for production planning.

Provides a focused interface for planning events, displaying plan_state,
expected_attendees, and supporting CRUD operations.

Feature 068: Event Management & Planning Data Model
Feature 069: Recipe Selection for Event Planning
Feature 070: Finished Goods Filtering for Event Planning
Feature 071: Finished Goods Quantity Specification
Feature 073: Batch Calculation User Decisions
Feature 076: Assembly Feasibility & Single-Screen Planning
Feature 078: Plan Snapshots & Amendments
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
from src.ui.widgets.dialogs import show_confirmation
from src.ui.widgets import DataTable
from src.ui.widgets.batch_options_frame import BatchOptionsFrame
from src.ui.components.recipe_selection_frame import RecipeSelectionFrame
from src.ui.components.fg_selection_frame import FGSelectionFrame
from src.ui.components.shopping_summary_frame import ShoppingSummaryFrame
from src.ui.components.assembly_status_frame import AssemblyStatusFrame
from src.ui.components.production_progress_frame import ProductionProgressFrame
from src.services.planning_service import calculate_batch_options
from src.services.inventory_gap_service import analyze_inventory_gaps
from src.services.assembly_feasibility_service import calculate_assembly_feasibility
from src.services.batch_decision_service import (
    save_batch_decision,
    get_batch_decisions,
    delete_batch_decisions,
    BatchDecisionInput,
)
from src.services.exceptions import ValidationError, PlanStateError, ServiceError
from src.ui.utils.error_handler import handle_error
from src.services.plan_state_service import (
    get_plan_state,
    lock_plan,
    start_production,
    complete_production,
)
from tkinter import messagebox


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

        # Configure grid (planning-focused layout)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Event selector header (compact)
        self.grid_rowconfigure(
            1, weight=1
        )  # Planning sections container (scrollable, takes almost all space)
        self.grid_rowconfigure(2, weight=0)  # Status bar

        # Build UI
        self._create_event_selector()  # New: compact dropdown-based event selector
        self._create_planning_container()  # New: scrollable container for all planning sections
        self._create_recipe_selection_frame()
        self._create_clear_buttons_frame()
        self._create_fg_selection_frame()
        self._create_batch_options_frame()
        self._create_plan_state_frame()  # F077
        self._create_shopping_summary_frame()
        self._create_assembly_status_frame()
        self._create_production_progress_frame()  # F079
        self._create_status_bar()

        # Layout widgets
        self._layout_widgets()

        # Grid the frame (consistent with other tabs)
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Load initial data
        self.refresh()

    def _create_event_selector(self) -> None:
        """Create compact event selector header (replaces table)."""
        self.selector_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.selector_frame.grid_columnconfigure(1, weight=1)  # Event display expands

        # Left side: Create Event button
        self.create_button = ctk.CTkButton(
            self.selector_frame,
            text="Create Event",
            command=self._on_create_click,
            width=120,
        )

        # Center: Event dropdown and info display
        self.event_selector_container = ctk.CTkFrame(self.selector_frame)

        # Dropdown label
        ctk.CTkLabel(
            self.event_selector_container,
            text="Event:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", padx=(10, 5))

        # Event dropdown
        self._event_var = ctk.StringVar(value="Select an event...")
        self.event_dropdown = ctk.CTkOptionMenu(
            self.event_selector_container,
            variable=self._event_var,
            values=["No events available"],
            command=self._on_event_dropdown_change,
            width=300,
        )
        self.event_dropdown.pack(side="left", padx=5)

        # Event details display (date, attendees, state)
        self.event_details_label = ctk.CTkLabel(
            self.event_selector_container,
            text="",
            text_color="gray",
        )
        self.event_details_label.pack(side="left", padx=10)

        # Right side: Edit and Delete buttons
        self.edit_button = ctk.CTkButton(
            self.selector_frame,
            text="Edit",
            command=self._on_edit_click,
            width=80,
            state="disabled",
        )

        self.delete_button = ctk.CTkButton(
            self.selector_frame,
            text="Delete",
            command=self._on_delete_click,
            width=80,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )

        # Store event mapping (name -> event object)
        self._event_map = {}

    def _create_planning_container(self) -> None:
        """Create scrollable container for all planning sections."""
        self._planning_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
        )
        # Container starts empty - sections will pack into it when event selected

    def _create_recipe_selection_frame(self) -> None:
        """Create the recipe selection frame (initially hidden)."""
        self._recipe_selection_frame = RecipeSelectionFrame(
            self._planning_container,
            on_save=self._on_recipe_selection_save,
            on_cancel=self._on_recipe_selection_cancel,
        )
        # Frame starts hidden - will be shown when event is selected

    def _create_clear_buttons_frame(self) -> None:
        """Create the clear buttons frame (T013/T014, initially hidden)."""
        self._clear_buttons_frame = ctk.CTkFrame(
            self._planning_container, fg_color="transparent"
        )

        self._clear_all_button = ctk.CTkButton(
            self._clear_buttons_frame,
            text="Clear All",
            width=100,
            fg_color="gray40",
            hover_color="gray30",
            command=self._handle_clear_all,
        )
        self._clear_all_button.pack(side="left", padx=5)

        self._clear_fgs_button = ctk.CTkButton(
            self._clear_buttons_frame,
            text="Clear Finished Goods",
            width=150,
            fg_color="gray40",
            hover_color="gray30",
            command=self._handle_clear_fgs,
        )
        self._clear_fgs_button.pack(side="left", padx=5)
        # Frame starts hidden - will be shown when event is selected

    def _create_fg_selection_frame(self) -> None:
        """Create the FG selection frame (initially hidden)."""
        self._fg_selection_frame = FGSelectionFrame(
            self._planning_container,
            on_save=self._on_fg_selection_save,
            on_cancel=self._on_fg_selection_cancel,
        )
        # Frame starts hidden - will be shown when event is selected

    def _create_batch_options_frame(self) -> None:
        """Create the batch options frame (F073, initially hidden)."""
        # Create container frame for label, widget, and save button
        self._batch_options_container = ctk.CTkFrame(self._planning_container)

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

    def _create_plan_state_frame(self) -> None:
        """Create the plan state controls frame (F077) and amendment controls (F078)."""
        self._plan_state_frame = ctk.CTkFrame(self._planning_container)

        # State label (shows current state)
        self._state_label = ctk.CTkLabel(
            self._plan_state_frame,
            text="Plan State: --",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self._state_label.pack(side="left", padx=(10, 20), pady=8)

        # Transition buttons (created but visibility controlled by state)
        self._lock_btn = ctk.CTkButton(
            self._plan_state_frame,
            text="Lock Plan",
            command=self._on_lock_plan,
            width=120,
        )
        self._lock_btn.pack(side="left", padx=5, pady=8)

        self._start_production_btn = ctk.CTkButton(
            self._plan_state_frame,
            text="Start Production",
            command=self._on_start_production,
            width=140,
        )
        self._start_production_btn.pack(side="left", padx=5, pady=8)

        self._complete_btn = ctk.CTkButton(
            self._plan_state_frame,
            text="Complete Production",
            command=self._on_complete_production,
            width=160,
        )
        self._complete_btn.pack(side="left", padx=5, pady=8)

        # F078: Amendment controls container (only visible in IN_PRODUCTION)
        self._amendment_controls_frame = ctk.CTkFrame(self._planning_container)

        # Amendment header
        amendment_header = ctk.CTkFrame(self._amendment_controls_frame)
        amendment_header.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            amendment_header,
            text="Plan Amendments",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=5)

        # Amendment buttons
        amendment_buttons = ctk.CTkFrame(self._amendment_controls_frame)
        amendment_buttons.pack(fill="x", padx=5, pady=5)

        self._drop_fg_btn = ctk.CTkButton(
            amendment_buttons,
            text="Drop FG",
            command=self._on_drop_fg_click,
            width=100,
        )
        self._drop_fg_btn.pack(side="left", padx=5)

        self._add_fg_btn = ctk.CTkButton(
            amendment_buttons,
            text="Add FG",
            command=self._on_add_fg_click,
            width=100,
        )
        self._add_fg_btn.pack(side="left", padx=5)

        self._modify_batch_btn = ctk.CTkButton(
            amendment_buttons,
            text="Modify Batch",
            command=self._on_modify_batch_click,
            width=120,
        )
        self._modify_batch_btn.pack(side="left", padx=5)

        # F078: Amendment history panel
        self._amendment_history_frame = ctk.CTkScrollableFrame(
            self._amendment_controls_frame,
            height=150,
        )
        self._amendment_history_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            self._amendment_history_frame,
            text="Amendment History",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=5, pady=5)

        self._history_content = ctk.CTkFrame(self._amendment_history_frame)
        self._history_content.pack(fill="x")

        # F078: Comparison view (T023-T025)
        self._comparison_visible = False
        self._show_comparison_btn = ctk.CTkButton(
            amendment_header,
            text="Show Comparison",
            command=self._toggle_comparison_view,
            width=130,
        )
        self._show_comparison_btn.pack(side="right", padx=5)

        self._comparison_frame = ctk.CTkScrollableFrame(
            self._amendment_controls_frame,
            height=200,
        )
        # Don't pack initially - shown on demand

        # Frame starts hidden

    def _create_shopping_summary_frame(self) -> None:
        """Create the shopping summary frame (F076)."""
        self._shopping_summary_frame = ShoppingSummaryFrame(self._planning_container)
        # Frame starts hidden - shown when event selected

    def _create_assembly_status_frame(self) -> None:
        """Create the assembly status frame (F076)."""
        self._assembly_status_frame = AssemblyStatusFrame(self._planning_container)
        # Frame starts hidden - shown when event selected

    def _create_production_progress_frame(self) -> None:
        """Create the production progress frame (F079)."""
        self._production_progress_frame = ProductionProgressFrame(self._planning_container)
        # Frame starts hidden - shown when event selected

    def _create_status_bar(self) -> None:
        """Create status bar for displaying feedback."""
        self.status_frame = ctk.CTkFrame(self, height=30)
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            anchor="w",
        )

    def _layout_widgets(self) -> None:
        """Position widgets using planning-focused layout."""
        # Compact event selector at top
        self.selector_frame.grid(
            row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE
        )
        self.create_button.grid(row=0, column=0, sticky="w", padx=(0, PADDING_MEDIUM))
        self.event_selector_container.grid(row=0, column=1, sticky="ew", padx=PADDING_MEDIUM)
        self.edit_button.grid(row=0, column=2, sticky="e", padx=PADDING_MEDIUM)
        self.delete_button.grid(row=0, column=3, sticky="e")

        # Planning sections scrollable container (takes almost all screen space)
        self._planning_container.grid(
            row=1, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

        # Planning sections now pack into _planning_container when shown:
        # - Recipe selection frame: packed in _show_recipe_selection()
        # - FG selection frame: packed in _show_fg_selection()
        # - Batch options frame: packed in _show_batch_options()
        # - Plan state controls: packed in _show_plan_state_controls()
        # - Amendment controls: packed in _show_amendment_controls()
        # - Shopping summary: packed in _show_shopping_summary()
        # - Assembly status: packed in _show_assembly_status()
        # - Production progress: packed in _show_production_progress()

        # Status bar at bottom
        self.status_frame.grid(
            row=2, column=0, sticky="ew", padx=PADDING_LARGE, pady=(0, PADDING_LARGE)
        )
        self.status_frame.grid_columnconfigure(0, weight=1)
        self.status_label.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

    def refresh(self) -> None:
        """Refresh the event dropdown from database."""
        try:
            with session_scope() as session:
                events = event_service.get_events_for_planning(session)

                # Filter to incomplete events (Draft, Locked, In Production - not Completed)
                from src.models import PlanState

                incomplete_events = [e for e in events if e.plan_state != PlanState.COMPLETED]

                # If no incomplete events, show last 5 events
                if not incomplete_events:
                    display_events = events[:5] if len(events) > 5 else events
                else:
                    display_events = incomplete_events

                # Build dropdown options and event map
                if display_events:
                    event_names = [e.name for e in display_events]
                    self._event_map = {e.name: e for e in display_events}
                    self.event_dropdown.configure(values=event_names)

                    # If we had a previously selected event, try to keep it selected
                    if self.selected_event and self.selected_event.name in event_names:
                        self._event_var.set(self.selected_event.name)
                    else:
                        # Select first event by default
                        self._event_var.set(event_names[0])
                        self._on_event_dropdown_change(event_names[0])
                else:
                    # No events available
                    self.event_dropdown.configure(values=["No events available"])
                    self._event_var.set("No events available")
                    self._event_map = {}
                    self._clear_selection()

                self._update_status(f"Loaded {len(display_events)} event(s)")

        except ServiceError as e:
            handle_error(e, parent=self, operation="Load events", show_dialog=False)
            self._update_status("Error loading events", is_error=True)
            self._clear_selection()
        except Exception as e:
            handle_error(e, parent=self, operation="Load events", show_dialog=False)
            self._update_status("Error loading events", is_error=True)
            self._clear_selection()

    @staticmethod
    def _safe_pack_forget(widget) -> None:
        """Hide a widget regardless of pack/grid layout (test-friendly)."""
        if hasattr(widget, "pack_forget"):
            widget.pack_forget()
        elif hasattr(widget, "grid_forget"):
            widget.grid_forget()

    def _clear_selection(self) -> None:
        """Clear event selection and hide all planning panels."""
        self.selected_event = None
        self._selected_event_id = None
        self.event_details_label.configure(text="")
        self._hide_recipe_selection()
        self._hide_clear_buttons()
        self._hide_fg_selection()
        self._hide_batch_options()
        self._hide_plan_state_controls()
        self._hide_shopping_summary()
        self._hide_assembly_status()
        self._hide_production_progress()
        self._update_button_states()

    def _on_event_dropdown_change(self, event_name: str) -> None:
        """
        Handle event dropdown selection change.

        Args:
            event_name: Selected event name from dropdown
        """
        if event_name == "No events available" or event_name not in self._event_map:
            self._clear_selection()
            return

        # Get the selected event
        event = self._event_map[event_name]

        # Re-query to get attached object for session safety
        with session_scope() as session:
            self.selected_event = session.query(Event).filter(Event.id == event.id).first()
            if self.selected_event:
                session.expunge(self.selected_event)

        if not self.selected_event:
            self._clear_selection()
            return

        # Update UI
        self._selected_event_id = self.selected_event.id
        self._update_event_details_display()
        self._update_button_states()

        # Show planning sections
        self._show_recipe_selection(self.selected_event.id)
        self._show_clear_buttons()
        self._show_fg_selection(self.selected_event.id)
        self._show_batch_options(self.selected_event.id)
        self._show_plan_state_controls()
        self._show_shopping_summary()
        self._show_assembly_status()
        self._show_production_progress()

        self._update_status(f"Selected: {self.selected_event.name}")

    def _update_event_details_display(self) -> None:
        """Update the event details label with date, attendees, and state."""
        if not self.selected_event:
            self.event_details_label.configure(text="")
            return

        details = []

        # Date
        if self.selected_event.event_date:
            details.append(self.selected_event.event_date.strftime("%Y-%m-%d"))

        # Attendees
        if self.selected_event.expected_attendees:
            details.append(f"{self.selected_event.expected_attendees} attendees")

        # Plan state
        if self.selected_event.plan_state:
            state_str = self.selected_event.plan_state.value.replace("_", " ").title()
            details.append(f"[{state_str}]")

        self.event_details_label.configure(text=" • ".join(details) if details else "")

    def _show_recipe_selection(self, event_id: int) -> None:
        """
        Show recipe selection for an event with filter-first pattern.

        Populates the category dropdown and restores existing selections,
        but does NOT auto-load all recipes. The user selects a category
        to see available recipes.

        Args:
            event_id: ID of the selected event
        """
        try:
            with session_scope() as session:
                # Get event name for header
                event = event_service.get_event_by_id(event_id, session=session)
                event_name = event.name if event else ""

                # Get existing selections
                selected_ids = event_service.get_event_recipe_ids(session, event_id)

            # Update header with event name
            if event_name:
                self._recipe_selection_frame._header_label.configure(
                    text=f"Recipe Selection for {event_name}"
                )
            else:
                self._recipe_selection_frame._header_label.configure(
                    text="Recipe Selection"
                )
            self._recipe_selection_frame._event_name = event_name

            # Load category dropdown options
            self._recipe_selection_frame.populate_categories()

            # Restore existing selections into persistence set
            self._recipe_selection_frame.set_selected(selected_ids)

            # Store for cancel functionality
            self._original_recipe_selection = selected_ids.copy()

            # Show frame using pack (starts blank; user selects category)
            self._recipe_selection_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        except ServiceError as e:
            handle_error(e, parent=self, operation="Load recipes", show_dialog=False)
            self._update_status("Error loading recipes", is_error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Load recipes", show_dialog=False)
            self._update_status("Error loading recipes", is_error=True)

    def _hide_recipe_selection(self) -> None:
        """Hide the recipe selection frame."""
        self._safe_pack_forget(self._recipe_selection_frame)
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

            # F076: Cascade updates to shopping and assembly
            self._update_shopping_summary()
            self._update_assembly_status()

        except PlanStateError as e:
            # F077: User-friendly message for state violations
            self._update_status(
                f"Cannot save: {e.attempted_action} not allowed "
                f"(plan is {e.current_state.value})",
                is_error=True,
            )
        except ServiceError as e:
            handle_error(e, parent=self, operation="Save", show_dialog=False)
            self._update_status("Error saving", is_error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Save", show_dialog=False)
            self._update_status("Error saving", is_error=True)

    def _on_recipe_selection_cancel(self) -> None:
        """Handle recipe selection cancel - revert to last saved state."""
        self._recipe_selection_frame.set_selected(self._original_recipe_selection)
        self._update_status("Reverted to saved recipe selections")

    # =========================================================================
    # F100/WP04: Clear Buttons
    # =========================================================================

    def _show_clear_buttons(self) -> None:
        """Show the clear buttons frame."""
        self._clear_buttons_frame.pack(
            fill="x", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM)
        )

    def _hide_clear_buttons(self) -> None:
        """Hide the clear buttons frame."""
        self._safe_pack_forget(self._clear_buttons_frame)

    def _handle_clear_all(self) -> None:
        """Handle Clear All button - reset entire plan (T013)."""
        confirmed = messagebox.askyesno(
            "Clear All",
            "Clear all recipes and finished goods?\n\n"
            "This resets the entire plan to blank.",
        )
        if not confirmed:
            return

        # Clear recipe selections
        self._recipe_selection_frame.clear_selections()

        # Clear FG selections
        self._fg_selection_frame.clear_selections()

        # Return FG frame to blank state
        self._fg_selection_frame._reset_to_blank()

        self._update_status("Cleared all selections")

    def _handle_clear_fgs(self) -> None:
        """Handle Clear FGs button - reset only FG selections (T014)."""
        confirmed = messagebox.askyesno(
            "Clear Finished Goods",
            "Clear all finished good selections?\n\n"
            "Recipe selections will remain.",
        )
        if not confirmed:
            return

        # Clear only FG selections
        self._fg_selection_frame.clear_selections()

        # Reset FG frame to blank (recipes stay)
        self._fg_selection_frame._reset_to_blank()

        self._update_status("Cleared finished good selections")

    # =========================================================================
    # F070: Finished Good Selection
    # =========================================================================

    def _show_fg_selection(self, event_id: int) -> None:
        """
        Show and populate FG selection for an event.

        F100/WP03: Filter-first blank start. Sets event context on the frame
        to populate filter dropdowns. Does NOT auto-populate FGs -- the frame
        starts blank until the user selects at least one filter.

        F071: Loads existing selections with quantities and restores them
        in the persistence layer so they appear when the user filters.

        Args:
            event_id: ID of the selected event
        """
        try:
            with session_scope() as session:
                # Get event name
                event = event_service.get_event_by_id(event_id, session=session)
                event_name = event.name if event else ""

                # F071: Get existing selections with quantities
                fg_quantities = event_service.get_event_fg_quantities(session, event_id)

            # Set event context and populate filter dropdowns (blank start)
            self._fg_selection_frame.set_event(event_id, event_name)

            # F071: Restore existing selections in persistence layer
            qty_tuples = [(fg.id, qty) for fg, qty in fg_quantities]
            self._fg_selection_frame.set_selected_with_quantities(qty_tuples)

            # Store for cancel functionality
            self._original_fg_selection = qty_tuples.copy()

            # Show frame using pack
            self._fg_selection_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        except ServiceError as e:
            handle_error(e, parent=self, operation="Load finished goods", show_dialog=False)
            self._update_status("Error loading finished goods", is_error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Load finished goods", show_dialog=False)
            self._update_status("Error loading finished goods", is_error=True)

    def _hide_fg_selection(self) -> None:
        """Hide the FG selection frame."""
        self._safe_pack_forget(self._fg_selection_frame)
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
            self._update_status("Please fix invalid quantities before saving", is_error=True)
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

            # F076: Reload batch options and update downstream panels
            self._load_batch_options()
            self._update_shopping_summary()
            self._update_assembly_status()

        except PlanStateError as e:
            # F077: User-friendly message for state violations
            self._update_status(
                f"Cannot save: {e.attempted_action} not allowed "
                f"(plan is {e.current_state.value})",
                is_error=True,
            )
        except ServiceError as e:
            handle_error(e, parent=self, operation="Save", show_dialog=False)
            self._update_status("Error saving", is_error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Save", show_dialog=False)
            self._update_status("Error saving", is_error=True)

    def _on_fg_selection_cancel(self) -> None:
        """Handle FG selection cancel - revert to last saved state."""
        # F071: Use set_selected_with_quantities for quantities
        self._fg_selection_frame.set_selected_with_quantities(self._original_fg_selection)
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

        # Show container using pack (fallback for mock frames)
        if hasattr(self._batch_options_container, "pack"):
            self._batch_options_container.pack(
                fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
            )
        else:
            self._batch_options_container.grid()

    def _hide_batch_options(self) -> None:
        """Hide the batch options frame."""
        if hasattr(self._batch_options_container, "pack_forget"):
            self._batch_options_container.pack_forget()
        else:
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

        except ServiceError as e:
            handle_error(e, parent=self, operation="Load batch options", show_dialog=False)
            self._update_status("Failed to load batch options", is_error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Load batch options", show_dialog=False)
            self._update_status("Failed to load batch options", is_error=True)

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

        except ServiceError as e:
            # Log but don't fail - just means no pre-selection
            handle_error(e, parent=self, operation="Load existing decisions", show_dialog=False)
        except Exception as e:
            # Log but don't fail - just means no pre-selection
            handle_error(e, parent=self, operation="Load existing decisions", show_dialog=False)

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
        selection = next((s for s in selections if s["finished_unit_id"] == fu_id), None)

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

    # =========================================================================
    # F076: Shopping Summary & Assembly Status
    # =========================================================================

    def _update_shopping_summary(self) -> None:
        """Update the shopping summary panel with current gap analysis."""
        if self._selected_event_id is None:
            self._shopping_summary_frame.clear()
            return

        try:
            gap_result = analyze_inventory_gaps(self._selected_event_id)
            self._shopping_summary_frame.update_summary(gap_result)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Update shopping summary", show_dialog=False)
            self._shopping_summary_frame.clear()
        except Exception as e:
            handle_error(e, parent=self, operation="Update shopping summary", show_dialog=False)
            self._shopping_summary_frame.clear()

    def _update_assembly_status(self) -> None:
        """Update the assembly status panel with current feasibility."""
        if self._selected_event_id is None:
            self._assembly_status_frame.clear()
            return

        try:
            feasibility = calculate_assembly_feasibility(self._selected_event_id)
            self._assembly_status_frame.update_status(feasibility)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Update assembly status", show_dialog=False)
            self._assembly_status_frame.clear()
        except Exception as e:
            handle_error(e, parent=self, operation="Update assembly status", show_dialog=False)
            self._assembly_status_frame.clear()

    def _show_plan_state_controls(self) -> None:
        """Show and update plan state controls frame (F077)."""
        if self._selected_event_id is None:
            return

        try:
            state = get_plan_state(self._selected_event_id)
            self._update_plan_state_buttons(state)
            self._plan_state_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Show plan state controls", show_dialog=False)
        except Exception as e:
            handle_error(e, parent=self, operation="Show plan state controls", show_dialog=False)

    def _hide_plan_state_controls(self) -> None:
        """Hide the plan state controls frame (F077)."""
        self._safe_pack_forget(self._plan_state_frame)
        self._state_label.configure(text="Plan State: --")

    def _update_plan_state_buttons(self, state: PlanState) -> None:
        """Update button visibility and state based on current plan state (F077/F078).

        Args:
            state: Current PlanState of the selected event
        """
        # Handle None/invalid state
        if state is None:
            self._state_label.configure(text="Plan State: --")
            self._lock_btn.pack_forget()
            self._start_production_btn.pack_forget()
            self._complete_btn.pack_forget()
            self._hide_amendment_controls()
            return

        # Hide all buttons first
        self._lock_btn.pack_forget()
        self._start_production_btn.pack_forget()
        self._complete_btn.pack_forget()

        # Update state label with human-readable name
        state_display = {
            PlanState.DRAFT: "Draft",
            PlanState.LOCKED: "Locked",
            PlanState.IN_PRODUCTION: "In Production",
            PlanState.COMPLETED: "Completed",
        }
        display_name = state_display.get(state, str(state))
        self._state_label.configure(text=f"Plan State: {display_name}")

        # Show appropriate button based on state
        if state == PlanState.DRAFT:
            self._lock_btn.pack(side="left", padx=5, pady=8)
            self._hide_amendment_controls()
        elif state == PlanState.LOCKED:
            self._start_production_btn.pack(side="left", padx=5, pady=8)
            self._hide_amendment_controls()
        elif state == PlanState.IN_PRODUCTION:
            self._complete_btn.pack(side="left", padx=5, pady=8)
            self._show_amendment_controls()
        else:
            # COMPLETED: no buttons or amendment controls shown
            self._hide_amendment_controls()

    def _refresh_plan_state_display(self) -> None:
        """Refresh the plan state display after a transition (F077)."""
        if self._selected_event_id is None:
            return

        try:
            state = get_plan_state(self._selected_event_id)
            self._update_plan_state_buttons(state)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Refresh plan state", show_dialog=False)
        except Exception as e:
            handle_error(e, parent=self, operation="Refresh plan state", show_dialog=False)

    def _on_lock_plan(self) -> None:
        """Handle Lock Plan button click (F077)."""
        if self._selected_event_id is None:
            return

        try:
            lock_plan(self._selected_event_id)
            self._update_status("Plan locked successfully")
            self._refresh_plan_state_display()
            # Refresh other panels that may be affected
            self._update_shopping_summary()
            self._update_assembly_status()
            self._update_production_progress()  # F079
        except PlanStateError as e:
            handle_error(e, parent=self, operation="Lock plan")
            self._update_status(f"Cannot lock plan: {e}", is_error=True)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Lock plan")
            self._update_status("Error", is_error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Lock plan")
            self._update_status("Error", is_error=True)

    def _on_start_production(self) -> None:
        """Handle Start Production button click (F077)."""
        if self._selected_event_id is None:
            return

        try:
            start_production(self._selected_event_id)
            self._update_status("Production started")
            self._refresh_plan_state_display()
            self._update_shopping_summary()
            self._update_assembly_status()
            self._update_production_progress()  # F079
        except PlanStateError as e:
            handle_error(e, parent=self, operation="Start production")
            self._update_status(f"Cannot start production: {e}", is_error=True)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Start production")
            self._update_status("Error", is_error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Start production")
            self._update_status("Error", is_error=True)

    def _on_complete_production(self) -> None:
        """Handle Complete Production button click (F077)."""
        if self._selected_event_id is None:
            return

        # Confirm completion (this is a significant action)
        if not messagebox.askyesno(
            "Complete Production",
            "Are you sure you want to mark production as complete?\n\n"
            "This will make the plan read-only. No further changes will be allowed.",
        ):
            return

        try:
            complete_production(self._selected_event_id)
            self._update_status("Production completed")
            self._refresh_plan_state_display()
            self._update_shopping_summary()
            self._update_assembly_status()
            self._update_production_progress()  # F079
        except PlanStateError as e:
            handle_error(e, parent=self, operation="Complete production")
            self._update_status(f"Cannot complete production: {e}", is_error=True)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Complete production")
            self._update_status("Error", is_error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Complete production")
            self._update_status("Error", is_error=True)

    def _show_shopping_summary(self) -> None:
        """Show and update shopping summary frame."""
        self._update_shopping_summary()
        self._shopping_summary_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    def _hide_shopping_summary(self) -> None:
        """Hide the shopping summary frame."""
        self._safe_pack_forget(self._shopping_summary_frame)
        self._shopping_summary_frame.clear()

    def _show_assembly_status(self) -> None:
        """Show and update assembly status frame."""
        self._update_assembly_status()
        self._assembly_status_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    def _hide_assembly_status(self) -> None:
        """Hide the assembly status frame."""
        self._safe_pack_forget(self._assembly_status_frame)
        self._assembly_status_frame.clear()

    # =========================================================================
    # F079: Production Progress Display
    # =========================================================================

    def _show_production_progress(self) -> None:
        """Show and update production progress frame (F079)."""
        self._update_production_progress()
        self._production_progress_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    def _hide_production_progress(self) -> None:
        """Hide the production progress frame (F079)."""
        self._safe_pack_forget(self._production_progress_frame)
        self._production_progress_frame.clear()

    def _update_production_progress(self) -> None:
        """Update the production progress panel with current progress (F079)."""
        if self._selected_event_id is None:
            self._production_progress_frame.clear()
            return

        try:
            from src.services.planning.progress import get_production_progress

            progress_list = get_production_progress(self._selected_event_id)
            self._production_progress_frame.update_progress(progress_list)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Update production progress", show_dialog=False)
            self._production_progress_frame.clear()
        except Exception as e:
            handle_error(e, parent=self, operation="Update production progress", show_dialog=False)
            self._production_progress_frame.clear()

    def _has_production_for_recipe(self, recipe_id: int) -> bool:
        """
        Check if recipe has production records for the current event (F079/T020).

        Used to determine if amendment controls should be disabled.

        Args:
            recipe_id: Recipe ID to check

        Returns:
            True if recipe has production records, False otherwise
        """
        if self._selected_event_id is None:
            return False

        recipes_with_production = self._production_progress_frame.get_recipes_with_production()
        return recipe_id in recipes_with_production

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
                    confirmed_shortfall=(
                        fu_id in self._confirmed_shortfalls if is_shortfall else False
                    ),
                )
                save_batch_decision(self._selected_event_id, decision)

            self._update_status("Batch decisions saved successfully.")

            # Reset unsaved indicator on success
            self._has_unsaved_batch_changes = False
            self._update_save_button_state()

            # F076: Update shopping and assembly status
            self._update_shopping_summary()
            self._update_assembly_status()

        except PlanStateError as e:
            # F077: User-friendly message for state violations
            self._update_status(
                f"Cannot save: {e.attempted_action} not allowed "
                f"(plan is {e.current_state.value})",
                is_error=True,
            )
        except ValidationError as e:
            handle_error(e, parent=self, operation="Save batch decisions", show_dialog=False)
            self._update_status("Validation error", is_error=True)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Save batch decisions", show_dialog=False)
            self._update_status("Failed to save batch decisions", is_error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Save batch decisions", show_dialog=False)
            self._update_status("Failed to save batch decisions", is_error=True)

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

    # =========================================================================
    # F078: Amendment Controls
    # =========================================================================

    def _show_amendment_controls(self) -> None:
        """Show amendment controls frame and refresh history (F078)."""
        self._amendment_controls_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)
        self._refresh_amendment_history()

    def _hide_amendment_controls(self) -> None:
        """Hide the amendment controls frame (F078)."""
        self._safe_pack_forget(self._amendment_controls_frame)
        # Clear history content
        for widget in self._history_content.winfo_children():
            widget.destroy()

    def _refresh_amendment_history(self) -> None:
        """Refresh the amendment history display (F078)."""
        # Clear existing
        for widget in self._history_content.winfo_children():
            widget.destroy()

        if not self._selected_event_id:
            return

        try:
            from src.services import plan_amendment_service

            amendments = plan_amendment_service.get_amendments(self._selected_event_id)

            if not amendments:
                ctk.CTkLabel(
                    self._history_content,
                    text="No amendments recorded.",
                    text_color="gray",
                ).pack(anchor="w", padx=10, pady=5)
                return

            for amendment in amendments:
                frame = ctk.CTkFrame(self._history_content)
                frame.pack(fill="x", padx=5, pady=2)

                # Type and summary
                type_text = amendment.amendment_type.value.upper().replace("_", " ")
                summary = self._format_amendment_summary(amendment)

                ctk.CTkLabel(
                    frame,
                    text=f"[{type_text}] {summary}",
                    font=ctk.CTkFont(weight="bold"),
                ).pack(anchor="w", padx=5)

                # Reason
                ctk.CTkLabel(
                    frame,
                    text=f"Reason: {amendment.reason}",
                    text_color="gray",
                ).pack(anchor="w", padx=15)

                # Timestamp
                timestamp = amendment.created_at.strftime("%Y-%m-%d %H:%M")
                ctk.CTkLabel(
                    frame,
                    text=timestamp,
                    text_color="gray",
                    font=ctk.CTkFont(size=10),
                ).pack(anchor="w", padx=15)

        except ServiceError as e:
            handle_error(e, parent=self, operation="Refresh amendment history", show_dialog=False)
            ctk.CTkLabel(
                self._history_content,
                text="Error loading history.",
                text_color="red",
            ).pack(anchor="w", padx=10, pady=5)
        except Exception as e:
            handle_error(e, parent=self, operation="Refresh amendment history", show_dialog=False)
            ctk.CTkLabel(
                self._history_content,
                text=f"Error loading history: {e}",
                text_color="red",
            ).pack(anchor="w", padx=10, pady=5)

    def _format_amendment_summary(self, amendment) -> str:
        """Format amendment data as readable summary (F078)."""
        data = amendment.amendment_data
        if amendment.amendment_type.value == "drop_fg":
            return f"Dropped {data.get('fg_name', 'Unknown')} (was qty {data.get('original_quantity', '?')})"
        elif amendment.amendment_type.value == "add_fg":
            return f"Added {data.get('fg_name', 'Unknown')} (qty {data.get('quantity', '?')})"
        elif amendment.amendment_type.value == "modify_batch":
            return f"{data.get('recipe_name', 'Unknown')}: {data.get('old_batches', '?')} -> {data.get('new_batches', '?')} batches"
        return "Unknown amendment"

    # =========================================================================
    # F078: Comparison View (T023-T025)
    # =========================================================================

    def _toggle_comparison_view(self) -> None:
        """Toggle comparison view visibility (F078)."""
        if self._comparison_visible:
            self._safe_pack_forget(self._comparison_frame)
            self._show_comparison_btn.configure(text="Show Comparison")
            self._comparison_visible = False
        else:
            self._refresh_comparison_view()
            self._comparison_frame.pack(fill="x", padx=5, pady=5)
            self._show_comparison_btn.configure(text="Hide Comparison")
            self._comparison_visible = True

    def _refresh_comparison_view(self) -> None:
        """Refresh the comparison view with current data (F078)."""
        # Clear existing
        for widget in self._comparison_frame.winfo_children():
            widget.destroy()

        if not self._selected_event_id:
            return

        try:
            from src.services import plan_snapshot_service

            comparison = plan_snapshot_service.get_plan_comparison(self._selected_event_id)

            if not comparison.has_snapshot:
                ctk.CTkLabel(
                    self._comparison_frame,
                    text="No snapshot available (production not started)",
                    text_color="gray",
                ).pack(pady=10)
                return

            # Header
            header_text = f"Plan Comparison ({comparison.total_changes} changes)"
            ctk.CTkLabel(
                self._comparison_frame,
                text=header_text,
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(anchor="w", padx=5, pady=5)

            # FG comparison section
            if comparison.finished_goods:
                self._render_fg_comparison(comparison.finished_goods)

            # Batch comparison section
            if comparison.batch_decisions:
                self._render_batch_comparison(comparison.batch_decisions)

            if not comparison.has_changes:
                ctk.CTkLabel(
                    self._comparison_frame,
                    text="No changes from original plan.",
                    text_color="gray",
                ).pack(pady=5)

        except ServiceError as e:
            handle_error(e, parent=self, operation="Refresh comparison view", show_dialog=False)
            ctk.CTkLabel(
                self._comparison_frame,
                text="Error loading comparison.",
                text_color="red",
            ).pack(anchor="w", padx=10, pady=5)
        except Exception as e:
            handle_error(e, parent=self, operation="Refresh comparison view", show_dialog=False)
            ctk.CTkLabel(
                self._comparison_frame,
                text=f"Error loading comparison: {e}",
                text_color="red",
            ).pack(anchor="w", padx=10, pady=5)

    def _render_fg_comparison(self, fg_items: list) -> None:
        """Render finished goods comparison section (F078/T024)."""
        section = ctk.CTkFrame(self._comparison_frame)
        section.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(section, text="Finished Goods", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w"
        )

        for item in fg_items:
            row = ctk.CTkFrame(section, fg_color="transparent")
            row.pack(fill="x", pady=1)

            # Status indicator and color
            if item.status == "dropped":
                indicator = "[-]"
                color = "#ff6b6b"  # Red
                text = f"{item.fg_name}: was {item.original_quantity}"
            elif item.status == "added":
                indicator = "[+]"
                color = "#51cf66"  # Green
                text = f"{item.fg_name}: now {item.current_quantity}"
            elif item.status == "modified":
                indicator = "[~]"
                color = "#fcc419"  # Yellow
                text = f"{item.fg_name}: {item.original_quantity} -> {item.current_quantity}"
            else:
                indicator = "[ ]"
                color = "gray"
                text = f"{item.fg_name}: {item.current_quantity}"

            ctk.CTkLabel(row, text=f"{indicator} {text}", text_color=color).pack(
                anchor="w", padx=10
            )

    def _render_batch_comparison(self, batch_items: list) -> None:
        """Render batch decisions comparison section (F078/T025)."""
        section = ctk.CTkFrame(self._comparison_frame)
        section.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(section, text="Batch Decisions", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w"
        )

        for item in batch_items:
            row = ctk.CTkFrame(section, fg_color="transparent")
            row.pack(fill="x", pady=1)

            if item.status == "modified":
                indicator = "[~]"
                color = "#fcc419"  # Yellow
                text = (
                    f"{item.recipe_name}: {item.original_batches} -> {item.current_batches} batches"
                )
            elif item.status == "dropped":
                indicator = "[-]"
                color = "#ff6b6b"  # Red
                text = f"{item.recipe_name}: was {item.original_batches} batches"
            elif item.status == "added":
                indicator = "[+]"
                color = "#51cf66"  # Green
                text = f"{item.recipe_name}: now {item.current_batches} batches"
            else:
                indicator = "[ ]"
                color = "gray"
                text = f"{item.recipe_name}: {item.current_batches} batches"

            ctk.CTkLabel(row, text=f"{indicator} {text}", text_color=color).pack(
                anchor="w", padx=10
            )

    def _on_drop_fg_click(self) -> None:
        """Handle Drop FG button click (F078)."""
        if not self._selected_event_id:
            return

        from src.models import EventFinishedGood

        with session_scope() as session:
            event_fgs = (
                session.query(EventFinishedGood)
                .filter(EventFinishedGood.event_id == self._selected_event_id)
                .all()
            )

            if not event_fgs:
                messagebox.showinfo("No Finished Goods", "No finished goods in plan to drop.")
                return

            fg_options = {
                f"{efg.finished_good.display_name} (qty: {efg.quantity})": efg.finished_good_id
                for efg in event_fgs
            }

        dialog = DropFGDialog(self, fg_options)
        result = dialog.get_result()

        if result:
            fg_id, reason = result
            try:
                from src.services import plan_amendment_service

                plan_amendment_service.drop_finished_good(self._selected_event_id, fg_id, reason)
                self._refresh_fg_selection()
                self._refresh_amendment_history()
                self._update_shopping_summary()
                self._update_assembly_status()
                self._update_production_progress()  # F079: Refresh progress
                self._update_status("Finished good dropped successfully")
            except ServiceError as e:
                handle_error(e, parent=self, operation="Drop finished good")
            except Exception as e:
                handle_error(e, parent=self, operation="Drop finished good")

    def _on_add_fg_click(self) -> None:
        """Handle Add FG button click (F078)."""
        if not self._selected_event_id:
            return

        from src.models import FinishedGood, EventFinishedGood

        with session_scope() as session:
            # Get IDs already in plan
            existing_ids = set(
                efg.finished_good_id
                for efg in session.query(EventFinishedGood)
                .filter(EventFinishedGood.event_id == self._selected_event_id)
                .all()
            )

            # Get available FGs
            query = session.query(FinishedGood)
            if existing_ids:
                query = query.filter(~FinishedGood.id.in_(existing_ids))
            available_fgs = query.all()

            if not available_fgs:
                messagebox.showinfo(
                    "No Available FGs", "All finished goods are already in the plan."
                )
                return

            fg_options = {fg.display_name: fg.id for fg in available_fgs}

        dialog = AddFGDialog(self, fg_options)
        result = dialog.get_result()

        if result:
            fg_id, quantity, reason = result
            try:
                from src.services import plan_amendment_service

                plan_amendment_service.add_finished_good(
                    self._selected_event_id, fg_id, quantity, reason
                )
                self._refresh_fg_selection()
                self._refresh_amendment_history()
                self._update_shopping_summary()
                self._update_assembly_status()
                self._update_production_progress()  # F079: Refresh progress
                self._update_status("Finished good added successfully")
            except ServiceError as e:
                handle_error(e, parent=self, operation="Add finished good")
            except Exception as e:
                handle_error(e, parent=self, operation="Add finished good")

    def _on_modify_batch_click(self) -> None:
        """Handle Modify Batch button click (F078).

        F079/T021: Filters out recipes with production records (locked).
        """
        if not self._selected_event_id:
            return

        from src.models import BatchDecision

        # F079: Get recipes with production to filter out locked ones
        recipes_with_production = self._production_progress_frame.get_recipes_with_production()

        with session_scope() as session:
            batch_decisions = (
                session.query(BatchDecision)
                .filter(BatchDecision.event_id == self._selected_event_id)
                .all()
            )

            if not batch_decisions:
                messagebox.showinfo("No Batch Decisions", "No batch decisions to modify.")
                return

            # F079/T021: Filter out recipes with production (locked)
            # Format: "Recipe Name (current: X batches)" or "(LOCKED)" indicator
            recipe_options = {}
            locked_count = 0
            for bd in batch_decisions:
                if bd.recipe_id in recipes_with_production:
                    # Skip locked recipes - they have production
                    locked_count += 1
                else:
                    recipe_options[f"{bd.recipe.name} (current: {bd.batches} batches)"] = (
                        bd.recipe_id,
                        bd.batches,
                    )

            if not recipe_options:
                if locked_count > 0:
                    messagebox.showinfo(
                        "All Recipes Locked",
                        f"All {locked_count} recipe(s) have production records "
                        "and cannot be modified.\n\n"
                        "Recipes with production are locked to protect "
                        "in-progress batches.",
                    )
                else:
                    messagebox.showinfo("No Batch Decisions", "No batch decisions to modify.")
                return

        dialog = ModifyBatchDialog(self, recipe_options)
        result = dialog.get_result()

        if result:
            recipe_id, new_batches, reason = result
            try:
                from src.services import plan_amendment_service

                plan_amendment_service.modify_batch_decision(
                    self._selected_event_id, recipe_id, new_batches, reason
                )
                self._load_batch_options()
                self._refresh_amendment_history()
                self._update_shopping_summary()
                self._update_assembly_status()
                self._update_production_progress()  # F079: Refresh progress
                self._update_status("Batch count modified successfully")
            except ServiceError as e:
                handle_error(e, parent=self, operation="Modify batch decision")
            except Exception as e:
                handle_error(e, parent=self, operation="Modify batch decision")


# =============================================================================
# F078: Amendment Dialog Classes
# =============================================================================


class DropFGDialog(ctk.CTkToplevel):
    """Dialog for dropping a finished good (F078)."""

    def __init__(self, parent, fg_options: dict):
        super().__init__(parent)
        self.title("Drop Finished Good")
        self.geometry("400x280")
        self.fg_options = fg_options
        self.result = None

        self.transient(parent)
        self.grab_set()

        # FG selection
        ctk.CTkLabel(self, text="Select Finished Good:").pack(pady=(15, 5))
        self.fg_var = ctk.StringVar()
        options = list(fg_options.keys())
        if options:
            self.fg_var.set(options[0])
        self.fg_dropdown = ctk.CTkOptionMenu(self, variable=self.fg_var, values=options, width=350)
        self.fg_dropdown.pack(pady=5)

        # Reason entry
        ctk.CTkLabel(self, text="Reason (required):").pack(pady=(15, 5))
        self.reason_entry = ctk.CTkTextbox(self, height=80, width=350)
        self.reason_entry.pack(pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Drop", command=self._on_confirm, fg_color="darkred").pack(
            side="left", padx=10
        )
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=10)

        self.wait_window()

    def _on_confirm(self):
        reason = self.reason_entry.get("1.0", "end-1c").strip()
        if not reason:
            messagebox.showerror("Error", "Reason is required.")
            return

        selected = self.fg_var.get()
        if not selected:
            messagebox.showerror("Error", "Select a finished good.")
            return

        self.result = (self.fg_options[selected], reason)
        self.destroy()

    def get_result(self):
        return self.result


class AddFGDialog(ctk.CTkToplevel):
    """Dialog for adding a finished good (F078)."""

    def __init__(self, parent, fg_options: dict):
        super().__init__(parent)
        self.title("Add Finished Good")
        self.geometry("400x340")
        self.fg_options = fg_options
        self.result = None

        self.transient(parent)
        self.grab_set()

        # FG selection
        ctk.CTkLabel(self, text="Select Finished Good:").pack(pady=(15, 5))
        self.fg_var = ctk.StringVar()
        options = list(fg_options.keys())
        if options:
            self.fg_var.set(options[0])
        self.fg_dropdown = ctk.CTkOptionMenu(self, variable=self.fg_var, values=options, width=350)
        self.fg_dropdown.pack(pady=5)

        # Quantity entry
        ctk.CTkLabel(self, text="Quantity:").pack(pady=(15, 5))
        self.qty_entry = ctk.CTkEntry(self, width=100)
        self.qty_entry.insert(0, "1")
        self.qty_entry.pack(pady=5)

        # Reason entry
        ctk.CTkLabel(self, text="Reason (required):").pack(pady=(15, 5))
        self.reason_entry = ctk.CTkTextbox(self, height=80, width=350)
        self.reason_entry.pack(pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Add", command=self._on_confirm).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=10)

        self.wait_window()

    def _on_confirm(self):
        reason = self.reason_entry.get("1.0", "end-1c").strip()
        if not reason:
            messagebox.showerror("Error", "Reason is required.")
            return

        selected = self.fg_var.get()
        if not selected:
            messagebox.showerror("Error", "Select a finished good.")
            return

        try:
            quantity = int(self.qty_entry.get())
            if quantity <= 0:
                raise ValueError("Must be positive")
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a positive integer.")
            return

        self.result = (self.fg_options[selected], quantity, reason)
        self.destroy()

    def get_result(self):
        return self.result


class ModifyBatchDialog(ctk.CTkToplevel):
    """Dialog for modifying batch decision (F078)."""

    def __init__(self, parent, recipe_options: dict):
        super().__init__(parent)
        self.title("Modify Batch Count")
        self.geometry("400x340")
        self.recipe_options = recipe_options
        self.result = None

        self.transient(parent)
        self.grab_set()

        # Recipe selection
        ctk.CTkLabel(self, text="Select Recipe:").pack(pady=(15, 5))
        self.recipe_var = ctk.StringVar()
        options = list(recipe_options.keys())
        if options:
            self.recipe_var.set(options[0])
        self.recipe_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.recipe_var,
            values=options,
            width=350,
            command=self._on_recipe_change,
        )
        self.recipe_dropdown.pack(pady=5)

        # New batch count entry
        ctk.CTkLabel(self, text="New Batch Count:").pack(pady=(15, 5))
        self.batch_entry = ctk.CTkEntry(self, width=100)
        # Pre-fill with current value
        if options:
            _, current_batches = recipe_options[options[0]]
            self.batch_entry.insert(0, str(current_batches))
        self.batch_entry.pack(pady=5)

        # Reason entry
        ctk.CTkLabel(self, text="Reason (required):").pack(pady=(15, 5))
        self.reason_entry = ctk.CTkTextbox(self, height=80, width=350)
        self.reason_entry.pack(pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Modify", command=self._on_confirm).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=10)

        self.wait_window()

    def _on_recipe_change(self, selected: str):
        """Update batch entry when recipe selection changes."""
        if selected in self.recipe_options:
            _, current_batches = self.recipe_options[selected]
            self.batch_entry.delete(0, "end")
            self.batch_entry.insert(0, str(current_batches))

    def _on_confirm(self):
        reason = self.reason_entry.get("1.0", "end-1c").strip()
        if not reason:
            messagebox.showerror("Error", "Reason is required.")
            return

        selected = self.recipe_var.get()
        if not selected:
            messagebox.showerror("Error", "Select a recipe.")
            return

        try:
            new_batches = int(self.batch_entry.get())
            if new_batches < 0:
                raise ValueError("Cannot be negative")
        except ValueError:
            messagebox.showerror("Error", "Batch count must be a non-negative integer.")
            return

        recipe_id, _ = self.recipe_options[selected]
        self.result = (recipe_id, new_batches, reason)
        self.destroy()

    def get_result(self):
        return self.result
