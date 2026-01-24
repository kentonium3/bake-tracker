"""
FinishedUnit detail dialog for viewing and managing production.

Provides a modal dialog showing FinishedUnit details, production history,
and access to Record Production functionality.
"""

import customtkinter as ctk
from typing import Optional, Callable

from src.models.finished_unit import FinishedUnit
from src.ui.widgets.production_history_table import ProductionHistoryTable
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import batch_production_service, finished_unit_service, recipe_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


class FinishedUnitDetailDialog(ctk.CTkToplevel):
    """
    Modal dialog for displaying FinishedUnit details and production history.

    Shows:
    - Name and category
    - Recipe, inventory count
    - Production history table
    - Record Production button
    """

    def __init__(
        self,
        parent,
        finished_unit: FinishedUnit,
        on_inventory_changed: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize the FinishedUnit detail dialog.

        Args:
            parent: Parent widget
            finished_unit: The FinishedUnit to display
            on_inventory_changed: Optional callback when inventory changes
        """
        super().__init__(parent)

        self.finished_unit = finished_unit
        self._on_inventory_changed = on_inventory_changed
        self.service_integrator = get_ui_service_integrator()

        self._setup_window()
        self._create_widgets()
        self._load_data()
        self._setup_modal()

    def _setup_window(self):
        """Configure the dialog window."""
        self.title(f"Details - {self.finished_unit.display_name}")
        self.geometry("520x620")
        self.minsize(480, 550)
        self.resizable(True, True)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # History table expands

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
        self._create_header()
        self._create_info_section()
        self._create_history_section()
        self._create_buttons()

    def _create_header(self):
        """Create the header section with name and category."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

        name_label = ctk.CTkLabel(
            header_frame,
            text=self.finished_unit.display_name,
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        name_label.pack(anchor="w")

        if self.finished_unit.category:
            category_label = ctk.CTkLabel(
                header_frame,
                text=f"Category: {self.finished_unit.category}",
                text_color=("gray60", "gray40"),
            )
            category_label.pack(anchor="w")

    def _create_info_section(self):
        """Create the info section with recipe, inventory, and cost."""
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)
        info_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Recipe
        ctk.CTkLabel(info_frame, text="Recipe:").grid(
            row=row, column=0, sticky="e", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        recipe_name = (
            self.finished_unit.recipe.name if self.finished_unit.recipe else "No recipe assigned"
        )
        self.recipe_label = ctk.CTkLabel(info_frame, text=recipe_name)
        self.recipe_label.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Inventory count
        ctk.CTkLabel(info_frame, text="In Stock:").grid(
            row=row, column=0, sticky="e", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        self.inventory_label = ctk.CTkLabel(
            info_frame,
            text=str(self.finished_unit.inventory_count or 0),
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.inventory_label.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Items per batch - use primitive for variant yield inheritance (Feature 063)
        items_per_batch = self._get_inherited_items_per_batch()
        if items_per_batch:
            ctk.CTkLabel(info_frame, text="Items/Batch:").grid(
                row=row, column=0, sticky="e", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
            )
            ctk.CTkLabel(info_frame, text=str(items_per_batch)).grid(
                row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
            )

    def _create_history_section(self):
        """Create the production history section."""
        # Section header
        history_header = ctk.CTkLabel(
            self,
            text="Production History",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        history_header.grid(
            row=2,
            column=0,
            sticky="w",
            padx=PADDING_LARGE,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )

        # History table
        self.history_table = ProductionHistoryTable(
            self,
            on_row_select=self._on_history_select,
            on_row_double_click=self._on_history_double_click,
            height=180,
        )
        self.history_table.grid(
            row=3, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

    def _create_buttons(self):
        """Create the button row."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=4, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

        # Record Production button
        self.record_btn = ctk.CTkButton(
            button_frame,
            text="Record Production",
            command=self._open_record_production,
            width=150,
        )
        self.record_btn.pack(side="left", padx=PADDING_MEDIUM)

        # Disable if no recipe assigned
        if not self.finished_unit.recipe:
            self.record_btn.configure(state="disabled")
            note = ctk.CTkLabel(
                button_frame, text="(No recipe assigned)", text_color=("gray60", "gray40")
            )
            note.pack(side="left", padx=PADDING_MEDIUM)

        # Close button
        close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
            width=100,
        )
        close_btn.pack(side="right", padx=PADDING_MEDIUM)

    def _load_data(self):
        """Load initial data (production history)."""
        self._load_history()

    def _load_history(self):
        """Load production history for this FinishedUnit."""
        history = self.service_integrator.execute_service_operation(
            operation_name="Load Production History",
            operation_type=OperationType.READ,
            service_function=lambda: batch_production_service.get_production_history(
                finished_unit_id=self.finished_unit.id,
                limit=50,
                include_consumptions=False,
            ),
            parent_widget=self,
            error_context="Loading production history",
            suppress_exception=True,
        )

        if history:
            self.history_table.set_data(history)
        else:
            self.history_table.clear()

    def _on_history_select(self, run):
        """Handle production run selection."""
        # Optional: could show run details
        pass

    def _on_history_double_click(self, run):
        """Handle production run double-click."""
        # Optional: could show run detail dialog
        pass

    def _open_record_production(self):
        """Open the Record Production dialog."""
        from src.ui.forms.record_production_dialog import RecordProductionDialog

        dialog = RecordProductionDialog(self, self.finished_unit)
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            self._after_recording_success()

    def _after_recording_success(self):
        """Handle successful production recording."""
        # Refresh FinishedUnit data
        self._reload_finished_unit()

        # Refresh history table
        self._load_history()

        # Notify parent
        if self._on_inventory_changed:
            self._on_inventory_changed()

    def _get_inherited_items_per_batch(self):
        """Get items_per_batch from base recipe (Feature 063 variant yield inheritance).

        For variant recipes, the FinishedUnit has NULL yield fields. This method
        uses the get_base_yield_structure primitive to resolve to the base recipe's
        yield values transparently.

        Returns:
            Items per batch value or None if not defined
        """
        if not self.finished_unit.recipe_id:
            return None

        try:
            yields = recipe_service.get_base_yield_structure(self.finished_unit.recipe_id)
            if yields:
                # Find matching FU by slug or use first yield
                for y in yields:
                    if y.get("slug") == self.finished_unit.slug:
                        return y.get("items_per_batch")
                # Fallback to first yield if no slug match
                return yields[0].get("items_per_batch")
        except Exception:
            pass

        return None

    def _reload_finished_unit(self):
        """Reload FinishedUnit data from database."""
        updated = self.service_integrator.execute_service_operation(
            operation_name="Reload FinishedUnit",
            operation_type=OperationType.READ,
            service_function=lambda: finished_unit_service.get_finished_unit_by_id(
                self.finished_unit.id
            ),
            parent_widget=self,
            error_context="Reloading finished unit data",
            suppress_exception=True,
        )

        if updated:
            self.finished_unit = updated
            self._update_info_display()

    def _update_info_display(self):
        """Update the info section with current data."""
        self.inventory_label.configure(text=str(self.finished_unit.inventory_count or 0))
