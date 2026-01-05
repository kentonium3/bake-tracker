"""
Record Production dialog for recording batch production of FinishedUnits.

Provides a modal dialog for recording batch production with:
- Batch count input
- Adjustable actual yield
- Loss tracking with auto-expand (Feature 025)
- Optional notes
- Availability check display with refresh button
- Service integration for recording production
"""

import customtkinter as ctk
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

from src.models.finished_unit import FinishedUnit
from src.models.event import Event
from src.models.enums import LossCategory
from src.ui.widgets.availability_display import AvailabilityDisplay
from src.ui.widgets.dialogs import show_error, show_confirmation
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import batch_production_service, event_service, recipe_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


class RecordProductionDialog(ctk.CTkToplevel):
    """
    Dialog for recording batch production of a FinishedUnit.

    Displays availability check results and accepts batch count,
    yield adjustment, and optional notes before recording.
    """

    def __init__(self, parent, finished_unit: FinishedUnit):
        """
        Initialize the Record Production dialog.

        Args:
            parent: Parent widget
            finished_unit: The FinishedUnit to record production for
        """
        super().__init__(parent)

        self.finished_unit = finished_unit
        self.result: Optional[Dict[str, Any]] = None
        self._can_produce = False
        self._initializing = True
        self._last_expected = 0
        self.service_integrator = get_ui_service_integrator()

        # Feature 025: Loss tracking state
        self._loss_details_visible = False
        self._estimated_per_unit_cost: Optional[Decimal] = None

        # Feature 016: Load events for event selector
        self.events: List[Event] = self._load_events()

        self._setup_window()
        self._create_widgets()
        self._setup_modal()
        self._check_availability()

        self._initializing = False

    def get_result(self) -> Optional[Dict[str, Any]]:
        """
        Get the result of the dialog.

        Returns:
            Dict with production details if confirmed, None if cancelled
        """
        return self.result

    def _setup_window(self):
        """Configure the dialog window."""
        self.title(f"Record Production - {self.finished_unit.display_name}")
        self.geometry("520x700")  # Feature 025: Larger to accommodate loss section
        self.minsize(500, 650)
        self.resizable(True, True)

        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(8, weight=1)  # Availability expands (adjusted for loss rows)

    def _setup_modal(self):
        """Set up modal behavior."""
        self.transient(self.master)
        self.wait_visibility()
        self.grab_set()
        self.focus_force()
        self._center_on_parent()

    def _center_on_parent(self):
        """Center the dialog on its parent."""
        self.update_idletasks()

        parent = self.master
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        # Ensure on screen
        x = max(0, x)
        y = max(0, y)

        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create all dialog widgets."""
        row = 0

        # Header with name
        header = ctk.CTkLabel(
            self,
            text=self.finished_unit.display_name,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        header.grid(row=row, column=0, columnspan=2, pady=PADDING_LARGE)
        row += 1

        # Recipe info
        recipe_name = (
            self.finished_unit.recipe.name if self.finished_unit.recipe else "No recipe"
        )
        recipe_label = ctk.CTkLabel(self, text=f"Recipe: {recipe_name}")
        recipe_label.grid(
            row=row, column=0, columnspan=2, pady=(0, PADDING_MEDIUM)
        )
        row += 1

        # Feature 016: Event selector
        ctk.CTkLabel(self, text="Event (optional):").grid(
            row=row, column=0, sticky="e", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        event_options = ["(None - standalone)"] + [e.name for e in self.events]
        self.event_var = ctk.StringVar(value=event_options[0])
        self.event_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.event_var,
            values=event_options,
            width=250,
        )
        self.event_dropdown.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Batch count
        ctk.CTkLabel(self, text="Batch Count:").grid(
            row=row, column=0, sticky="e", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        self.batch_entry = ctk.CTkEntry(self, width=100)
        self.batch_entry.insert(0, "1")
        self.batch_entry.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        self.batch_entry.bind("<KeyRelease>", self._on_batch_changed)
        row += 1

        # Feature 037: Scale factor
        scale_frame = ctk.CTkFrame(self, fg_color="transparent")
        scale_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)

        scale_label = ctk.CTkLabel(scale_frame, text="Scale Factor:", width=120)
        scale_label.pack(side="left", padx=(PADDING_MEDIUM, 0))

        self.scale_factor_var = ctk.StringVar(value="1.0")
        self.scale_factor_entry = ctk.CTkEntry(
            scale_frame, textvariable=self.scale_factor_var, width=80
        )
        self.scale_factor_entry.pack(side="left", padx=5)

        scale_hint = ctk.CTkLabel(
            scale_frame,
            text="(1.0 = normal, 2.0 = double batch, 0.5 = half batch)",
            text_color="gray",
        )
        scale_hint.pack(side="left", padx=5)

        # Bind to update handler
        self.scale_factor_var.trace_add("write", self._on_scale_changed)
        row += 1

        # Expected yield (calculated, read-only)
        ctk.CTkLabel(self, text="Expected Yield:").grid(
            row=row, column=0, sticky="e", padx=PADDING_MEDIUM
        )
        self.expected_yield_label = ctk.CTkLabel(self, text="0")
        self.expected_yield_label.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM
        )
        row += 1

        # Actual yield
        ctk.CTkLabel(self, text="Actual Yield:").grid(
            row=row, column=0, sticky="e", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        self.yield_entry = ctk.CTkEntry(self, width=100)
        self.yield_entry.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        # Feature 025: Bind yield change for loss calculation
        self.yield_entry.bind("<KeyRelease>", self._on_yield_changed)
        row += 1

        # Feature 025: Loss quantity display (read-only)
        ctk.CTkLabel(self, text="Loss Quantity:").grid(
            row=row, column=0, sticky="e", padx=PADDING_MEDIUM
        )
        self.loss_quantity_label = ctk.CTkLabel(self, text="0")
        self.loss_quantity_label.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM
        )
        row += 1

        # Feature 025: Expandable loss details frame
        self._loss_details_row = row
        self._create_loss_details_frame()
        row += 1

        # Notes
        ctk.CTkLabel(self, text="Notes:").grid(
            row=row, column=0, sticky="ne", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        self.notes_textbox = ctk.CTkTextbox(self, height=60)
        self.notes_textbox.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Feature 037: Ingredient requirements display (scaled)
        ctk.CTkLabel(self, text="Ingredients Needed:").grid(
            row=row, column=0, sticky="ne", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        self.requirements_label = ctk.CTkLabel(
            self, text="", justify="left", anchor="nw", wraplength=350
        )
        self.requirements_label.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Availability display
        self.availability_display = AvailabilityDisplay(
            self, title="Ingredient Availability"
        )
        self.availability_display.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=PADDING_MEDIUM,
            pady=PADDING_MEDIUM,
        )
        row += 1

        # Buttons
        self._create_buttons(row)

        # Update expected yield
        self._update_expected_yield()

    def _create_buttons(self, row: int):
        """Create the button row."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=row, column=0, columnspan=2, pady=PADDING_LARGE)

        self.refresh_btn = ctk.CTkButton(
            button_frame,
            text="Refresh Availability",
            command=self._on_refresh_availability,
            width=150,
        )
        self.refresh_btn.pack(side="left", padx=PADDING_MEDIUM)

        self.confirm_btn = ctk.CTkButton(
            button_frame,
            text="Confirm",
            command=self._on_confirm,
            width=100,
        )
        self.confirm_btn.pack(side="left", padx=PADDING_MEDIUM)

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=100,
        )
        cancel_btn.pack(side="left", padx=PADDING_MEDIUM)

    def _check_availability(self):
        """Check ingredient availability for the current batch count."""
        # Check if recipe exists
        if not self.finished_unit.recipe:
            self.availability_display.clear()
            self._can_produce = False
            self._update_confirm_button()
            return

        batch_count = self._get_batch_count()
        if batch_count < 1:
            return

        result = self.service_integrator.execute_service_operation(
            operation_name="Check Production Availability",
            operation_type=OperationType.READ,
            service_function=lambda: batch_production_service.check_can_produce(
                self.finished_unit.recipe_id, batch_count
            ),
            parent_widget=self,
            error_context="Checking ingredient availability",
            suppress_exception=True,
        )

        if result:
            self.availability_display.set_availability(result)
            self._can_produce = result.get("can_produce", False)
        else:
            self._can_produce = False

        self._update_confirm_button()

    def _on_refresh_availability(self):
        """Handle refresh availability button click."""
        self._check_availability()

    def _on_confirm(self):
        """Handle confirm button click."""
        if not self._validate():
            return

        batch_count = self._get_batch_count()
        scale_factor = self._get_scale_factor()  # Feature 037
        actual_yield = self._get_actual_yield()
        notes = self.notes_textbox.get("1.0", "end-1c").strip() or None
        event_id = self._get_selected_event_id()  # Feature 016

        # Feature 025: Get loss tracking data
        loss_qty = self._calculate_loss_quantity()
        loss_category = self._get_loss_category() if loss_qty > 0 else None
        loss_notes = self._get_loss_notes() if loss_qty > 0 else None

        # Confirmation dialog
        expected = self._calculate_expected_yield(batch_count, scale_factor)
        event_info = ""
        if event_id:
            selected_event = self.event_var.get()
            event_info = f"Event: {selected_event}\n"

        # Feature 037: Include scale factor in confirmation if not 1.0
        scale_info = ""
        if scale_factor != 1.0:
            scale_info = f"Scale Factor: {scale_factor}x\n"

        # Feature 025: Include loss info in confirmation
        loss_info = ""
        if loss_qty > 0:
            category_display = loss_category.value.replace("_", " ").title() if loss_category else "Other"
            loss_info = f"Loss: {loss_qty} units ({category_display})\n"

        message = (
            f"Record {batch_count} batch(es) of {self.finished_unit.display_name}?\n\n"
            f"{event_info}"
            f"{scale_info}"
            f"Expected yield: {expected}\n"
            f"Actual yield: {actual_yield}\n"
            f"{loss_info}\n"
            f"This will consume ingredients from inventory.\n"
            f"This action cannot be undone."
        )
        if not show_confirmation("Confirm Production", message, parent=self):
            return

        result = self.service_integrator.execute_service_operation(
            operation_name="Record Production",
            operation_type=OperationType.CREATE,
            service_function=lambda: batch_production_service.record_batch_production(
                recipe_id=self.finished_unit.recipe_id,
                finished_unit_id=self.finished_unit.id,
                num_batches=batch_count,
                actual_yield=actual_yield,
                notes=notes,
                event_id=event_id,  # Feature 016
                loss_category=loss_category,  # Feature 025
                loss_notes=loss_notes,  # Feature 025
                scale_factor=scale_factor,  # Feature 037
            ),
            parent_widget=self,
            success_message=f"Recorded {batch_count} batch(es) - {actual_yield} units produced",
            error_context="Recording batch production",
            show_success_dialog=True,
            suppress_exception=True,
        )

        if result:
            self.result = {
                "recipe_id": self.finished_unit.recipe_id,
                "finished_unit_id": self.finished_unit.id,
                "num_batches": batch_count,
                "actual_yield": actual_yield,
                "notes": notes,
                "event_id": event_id,  # Feature 016
                "production_run_id": result.get("production_run_id"),
                "loss_quantity": loss_qty,  # Feature 025
                "production_status": result.get("production_status"),  # Feature 025
                "scale_factor": scale_factor,  # Feature 037
            }
            self.destroy()

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()

    def _validate(self) -> bool:
        """Validate inputs before confirming."""
        # Validate batch count
        batch_count = self._get_batch_count()
        if batch_count < 1:
            show_error(
                "Validation Error", "Batch count must be at least 1.", parent=self
            )
            return False

        # Feature 037: Validate scale_factor > 0 (T021)
        try:
            scale_factor = float(self.scale_factor_var.get())
            if scale_factor <= 0:
                show_error(
                    "Validation Error",
                    "Scale factor must be greater than 0.",
                    parent=self,
                )
                return False
        except ValueError:
            show_error(
                "Validation Error",
                "Scale factor must be a valid number.",
                parent=self,
            )
            return False

        # Validate actual yield
        actual_yield = self._get_actual_yield()
        if actual_yield < 0:
            show_error(
                "Validation Error", "Actual yield cannot be negative.", parent=self
            )
            return False

        # Feature 025: Validate actual yield <= expected yield
        expected = self._calculate_expected_yield(batch_count, scale_factor)
        if actual_yield > expected:
            show_error(
                "Validation Error",
                f"Actual yield ({actual_yield}) cannot exceed expected yield ({expected}).",
                parent=self,
            )
            return False

        # Warn if yield is 0
        if actual_yield == 0:
            if not show_confirmation(
                "Zero Yield",
                "Actual yield is 0. This will consume ingredients but produce no units.\n\n"
                "Continue anyway?",
                parent=self,
            ):
                return False

        # Check availability
        if not self._can_produce:
            show_error(
                "Insufficient Inventory",
                "Cannot produce - some ingredients are insufficient.\n"
                "Check the availability display for details.",
                parent=self,
            )
            return False

        return True

    def _get_batch_count(self) -> int:
        """Get the batch count from input."""
        try:
            return int(self.batch_entry.get())
        except ValueError:
            return 0

    def _get_scale_factor(self) -> float:
        """Get the scale factor from input. Returns 1.0 if invalid."""
        try:
            value = float(self.scale_factor_var.get())
            return value if value > 0 else 1.0
        except ValueError:
            return 1.0

    def _get_actual_yield(self) -> int:
        """Get the actual yield from input."""
        try:
            value = self.yield_entry.get().strip()
            if not value:
                # Default to expected yield
                return self._calculate_expected_yield(
                    self._get_batch_count(), self._get_scale_factor()
                )
            return int(value)
        except ValueError:
            return self._calculate_expected_yield(
                self._get_batch_count(), self._get_scale_factor()
            )

    def _calculate_expected_yield(
        self, batch_count: int, scale_factor: float = 1.0
    ) -> int:
        """Calculate expected yield based on batch count and scale factor.

        Formula: expected = base_yield x scale_factor x num_batches
        """
        items_per_batch = self.finished_unit.items_per_batch or 1
        return int(items_per_batch * scale_factor * batch_count)

    def _update_expected_yield(self):
        """Update the expected yield display with formula."""
        batch_count = self._get_batch_count()
        scale_factor = self._get_scale_factor()
        items_per_batch = self.finished_unit.items_per_batch or 1
        expected = self._calculate_expected_yield(batch_count, scale_factor)

        # Display with formula for clarity (T019)
        if scale_factor != 1.0:
            formula = f"{items_per_batch} x {scale_factor} x {batch_count}"
            self.expected_yield_label.configure(text=f"{expected} ({formula})")
        else:
            self.expected_yield_label.configure(text=str(expected))

        # Also update actual yield default if user hasn't changed it
        if not self._initializing:
            current = self.yield_entry.get().strip()
            if not current or current == str(self._last_expected):
                self.yield_entry.delete(0, "end")
                self.yield_entry.insert(0, str(expected))

        self._last_expected = expected

        # Update ingredient requirements display (T020)
        self._update_ingredient_requirements()

    def _update_ingredient_requirements(self):
        """Update ingredient requirements display with scaling applied (T020)."""
        if not self.finished_unit.recipe_id:
            self.requirements_label.configure(text="No recipe linked")
            return

        batch_count = self._get_batch_count()
        scale_factor = self._get_scale_factor()

        if batch_count <= 0 or scale_factor <= 0:
            self.requirements_label.configure(text="")
            return

        multiplier = scale_factor * batch_count

        try:
            # Get aggregated ingredients with scaling applied
            ingredients = recipe_service.get_aggregated_ingredients(
                self.finished_unit.recipe_id, multiplier=multiplier
            )

            if not ingredients:
                self.requirements_label.configure(text="No ingredients")
                return

            # Build requirements display
            requirements = []
            for ing in ingredients:
                scaled_qty = ing.get("total_quantity", 0)
                unit = ing.get("unit", "")
                name = ing.get("ingredient_name", "Unknown")
                requirements.append(f"{name}: {scaled_qty:.2f} {unit}")

            self.requirements_label.configure(text="\n".join(requirements))
        except Exception:
            # If we can't get ingredients, just show empty
            self.requirements_label.configure(text="Unable to load ingredients")

    def _on_batch_changed(self, event=None):
        """Handle batch count change."""
        if self._initializing:
            return
        self._update_expected_yield()

    def _on_scale_changed(self, *args):
        """Handle scale factor change (T018)."""
        if self._initializing:
            return
        self._update_expected_yield()

    def _update_confirm_button(self):
        """Update confirm button state based on availability."""
        if self._can_produce:
            self.confirm_btn.configure(state="normal")
        else:
            self.confirm_btn.configure(state="disabled")

    def _load_events(self) -> List[Event]:
        """Load events sorted by date (nearest upcoming first)."""
        try:
            events = event_service.get_all_events()
            # Sort by event_date ascending; events without date go to end
            events.sort(key=lambda e: e.event_date or datetime.max.date())
            return events
        except Exception:
            # If event loading fails, return empty list
            return []

    def _get_selected_event_id(self) -> Optional[int]:
        """Get the event_id for the selected event, or None for standalone."""
        selected = self.event_var.get()
        if selected == "(None - standalone)":
            return None
        for event in self.events:
            if event.name == selected:
                return event.id
        return None

    # =========================================================================
    # Feature 025: Loss Tracking Methods
    # =========================================================================

    def _create_loss_details_frame(self):
        """Create the expandable loss details frame with category and notes."""
        self.loss_details_frame = ctk.CTkFrame(self)

        # Loss category dropdown
        ctk.CTkLabel(self.loss_details_frame, text="Loss Category:").grid(
            row=0, column=0, sticky="e", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        category_options = [cat.value.replace("_", " ").title() for cat in LossCategory]
        self.loss_category_var = ctk.StringVar(value="Other")
        self.loss_category_dropdown = ctk.CTkOptionMenu(
            self.loss_details_frame,
            variable=self.loss_category_var,
            values=category_options,
            width=200,
        )
        self.loss_category_dropdown.grid(
            row=0, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

        # Loss notes textbox
        ctk.CTkLabel(self.loss_details_frame, text="Loss Notes:").grid(
            row=1, column=0, sticky="ne", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        self.loss_notes_textbox = ctk.CTkTextbox(
            self.loss_details_frame, height=60, width=300
        )
        self.loss_notes_textbox.grid(
            row=1, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

        # Cost breakdown frame
        self.cost_breakdown_frame = ctk.CTkFrame(
            self.loss_details_frame, fg_color="transparent"
        )
        self.cost_breakdown_frame.grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        self.good_units_cost_label = ctk.CTkLabel(
            self.cost_breakdown_frame, text="", anchor="w"
        )
        self.good_units_cost_label.pack(anchor="w")
        self.lost_units_cost_label = ctk.CTkLabel(
            self.cost_breakdown_frame, text="", anchor="w", text_color="orange"
        )
        self.lost_units_cost_label.pack(anchor="w")
        self.total_cost_label = ctk.CTkLabel(
            self.cost_breakdown_frame, text="", anchor="w", font=ctk.CTkFont(weight="bold")
        )
        self.total_cost_label.pack(anchor="w")

        # Initially hidden
        self._loss_details_visible = False

    def _toggle_loss_details(self, show: bool):
        """Show or hide the loss details frame."""
        if show and not self._loss_details_visible:
            self.loss_details_frame.grid(
                row=self._loss_details_row,
                column=0,
                columnspan=2,
                sticky="ew",
                padx=PADDING_MEDIUM,
                pady=PADDING_MEDIUM,
            )
            self._loss_details_visible = True
        elif not show and self._loss_details_visible:
            self.loss_details_frame.grid_remove()
            self._loss_details_visible = False

    def _calculate_loss_quantity(self) -> int:
        """Calculate loss quantity from expected vs actual yield."""
        batch_count = self._get_batch_count()
        scale_factor = self._get_scale_factor()  # Feature 037
        expected = self._calculate_expected_yield(batch_count, scale_factor)
        actual = self._get_actual_yield()
        return max(0, expected - actual)

    def _update_loss_quantity_display(self):
        """Update the loss quantity label and auto-expand/collapse loss details."""
        loss_qty = self._calculate_loss_quantity()
        self.loss_quantity_label.configure(text=str(loss_qty))

        # Auto-expand/collapse loss details
        self._toggle_loss_details(loss_qty > 0)

        # Update cost breakdown if we have cost data
        if self._estimated_per_unit_cost and loss_qty > 0:
            self._update_cost_breakdown(self._estimated_per_unit_cost)

    def _update_cost_breakdown(self, per_unit_cost: Decimal):
        """Update the cost breakdown display."""
        actual = self._get_actual_yield()
        loss = self._calculate_loss_quantity()
        good_cost = actual * per_unit_cost
        lost_cost = loss * per_unit_cost
        total_cost = good_cost + lost_cost

        self.good_units_cost_label.configure(
            text=f"Good units ({actual}): ${good_cost:.2f}"
        )
        self.lost_units_cost_label.configure(
            text=f"Lost units ({loss}): ${lost_cost:.2f}"
        )
        self.total_cost_label.configure(
            text=f"Total batch cost: ${total_cost:.2f}"
        )

    def _on_yield_changed(self, event=None):
        """Handle actual yield change for loss tracking."""
        if self._initializing:
            return
        self._update_loss_quantity_display()

    def _get_loss_category(self) -> LossCategory:
        """Get the selected loss category as enum."""
        selected = self.loss_category_var.get().lower().replace(" ", "_")
        try:
            return LossCategory(selected)
        except ValueError:
            return LossCategory.OTHER

    def _get_loss_notes(self) -> Optional[str]:
        """Get loss notes from textbox."""
        notes = self.loss_notes_textbox.get("1.0", "end-1c").strip()
        return notes if notes else None
