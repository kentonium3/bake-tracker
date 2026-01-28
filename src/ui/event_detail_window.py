"""
Event detail window for managing event planning.

Provides comprehensive interface for:
- Assigning packages to recipients
- Viewing recipe needs
- Generating shopping lists
- Event summary and cost tracking
"""

import customtkinter as ctk
import re
from tkinter import filedialog, messagebox
from typing import Optional

from src.models.event import Event, EventRecipientPackage, FulfillmentStatus
from src.services import event_service, recipe_service
from src.services.database import session_scope
from src.services.finished_good_service import get_all_finished_goods
from src.services.event_service import AssignmentNotFoundError
from src.ui.utils import ui_session
from typing import List
from src.utils.constants import (
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.dialogs import (
    show_confirmation,
    show_error,
    show_success,
)
from src.ui.forms.assignment_form import AssignmentFormDialog


class EventDetailWindow(ctk.CTkToplevel):
    """
    Event detail window with tabbed interface.

    Provides comprehensive event planning:
    - Assignments: Assign recipients to packages
    - Recipe Needs: View batch requirements
    - Shopping List: See what to buy
    - Summary: Overview and costs
    """

    def __init__(self, parent, event: Event):
        """
        Initialize the event detail window.

        Args:
            parent: Parent widget
            event: Event to display/edit
        """
        super().__init__(parent)

        self.event = event
        self.selected_assignment: Optional[EventRecipientPackage] = None

        # Configure window
        self.title(f"Event Planning - {event.name}")
        self.geometry("1000x700")

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=1)  # Tabview
        self.grid_rowconfigure(2, weight=0)  # Buttons

        # Create title
        self._create_title()

        # Create tabbed interface
        self._create_tabs()

        # Create buttons
        self._create_buttons()

        # Load initial data
        self.refresh()

    def _create_title(self):
        """Create title section."""
        title_frame = ctk.CTkFrame(self)
        title_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        title_frame.grid_columnconfigure(0, weight=1)

        # Event name
        name_label = ctk.CTkLabel(
            title_frame, text=self.event.name, font=ctk.CTkFont(size=20, weight="bold")
        )
        name_label.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM)

        # Event details
        details_text = (
            f"Date: {self.event.event_date.strftime('%B %d, %Y')} | Year: {self.event.year}"
        )
        details_label = ctk.CTkLabel(title_frame, text=details_text, font=ctk.CTkFont(size=12))
        details_label.grid(row=1, column=0, sticky="w", padx=PADDING_MEDIUM)

    def _create_tabs(self):
        """Create tabbed interface."""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(
            row=1, column=0, padx=PADDING_LARGE, pady=(0, PADDING_MEDIUM), sticky="nsew"
        )

        # Add tabs
        self.tabview.add("Assignments")
        self.tabview.add("Targets")  # Feature 016: Production/Assembly progress
        self.tabview.add("Recipe Needs")
        self.tabview.add("Shopping List")
        self.tabview.add("Summary")

        # Create tab contents
        self._create_assignments_tab()
        self._create_targets_tab()  # Feature 016
        self._create_recipe_needs_tab()
        self._create_shopping_list_tab()
        self._create_summary_tab()

    def _create_assignments_tab(self):
        """Create assignments tab."""
        tab_frame = self.tabview.tab("Assignments")
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(1, weight=1)

        # Action buttons
        button_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
        button_frame.grid(row=0, column=0, sticky="ew", pady=(0, PADDING_MEDIUM))

        add_button = ctk.CTkButton(
            button_frame,
            text="➕ Assign Package to Recipient",
            command=self._add_assignment,
            width=200,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        self.edit_assignment_button = ctk.CTkButton(
            button_frame,
            text="✏️ Edit",
            command=self._edit_assignment,
            width=100,
            state="disabled",
        )
        self.edit_assignment_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        self.delete_assignment_button = ctk.CTkButton(
            button_frame,
            text="🗑️ Remove",
            command=self._delete_assignment,
            width=100,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_assignment_button.grid(row=0, column=2, padx=PADDING_MEDIUM)

        # Assignments list (scrollable frame)
        self.assignments_frame = ctk.CTkScrollableFrame(tab_frame, height=450)
        self.assignments_frame.grid(row=1, column=0, sticky="nsew")
        self.assignments_frame.grid_columnconfigure(0, weight=1)

    def _create_targets_tab(self):
        """Create targets tab for production/assembly progress (Feature 016)."""
        tab_frame = self.tabview.tab("Targets")
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(0, weight=1)

        # Main scrollable frame for targets
        self.targets_frame = ctk.CTkScrollableFrame(tab_frame)
        self.targets_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.targets_frame.grid_columnconfigure(0, weight=1)

        # Production Targets section
        self._create_production_targets_section()

        # Separator
        separator = ctk.CTkFrame(self.targets_frame, height=2, fg_color="gray50")
        separator.pack(fill="x", pady=15)

        # Assembly Targets section
        self._create_assembly_targets_section()

    def _create_production_targets_section(self):
        """Create the Production Targets section with header and list."""
        # Header frame with title and Add button
        header_frame = ctk.CTkFrame(self.targets_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))

        header_label = ctk.CTkLabel(
            header_frame,
            text="Production Targets",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header_label.pack(side="left", padx=5)

        add_btn = ctk.CTkButton(
            header_frame,
            text="+ Add Target",
            width=100,
            command=self._on_add_production_target,
        )
        add_btn.pack(side="right", padx=5)

        # Container for production target rows
        self.production_targets_container = ctk.CTkFrame(self.targets_frame, fg_color="transparent")
        self.production_targets_container.pack(fill="x", pady=5)

    def _create_assembly_targets_section(self):
        """Create the Assembly Targets section with header and list."""
        # Header frame with title and Add button
        header_frame = ctk.CTkFrame(self.targets_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))

        header_label = ctk.CTkLabel(
            header_frame,
            text="Assembly Targets",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header_label.pack(side="left", padx=5)

        add_btn = ctk.CTkButton(
            header_frame,
            text="+ Add Target",
            width=100,
            command=self._on_add_assembly_target,
        )
        add_btn.pack(side="right", padx=5)

        # Container for assembly target rows
        self.assembly_targets_container = ctk.CTkFrame(self.targets_frame, fg_color="transparent")
        self.assembly_targets_container.pack(fill="x", pady=5)

    def _create_progress_row(
        self,
        parent,
        name: str,
        produced: int,
        target: int,
        target_id: int,
        is_production: bool = True,
    ):
        """Create a single progress row for a target.

        Args:
            parent: Parent widget
            name: Recipe or FinishedGood name
            produced: Number produced/assembled
            target: Target number
            target_id: ID of the target record (recipe_id or finished_good_id)
            is_production: True for production targets, False for assembly
        """
        row = ctk.CTkFrame(parent, fg_color=("gray90", "gray20"))
        row.pack(fill="x", pady=2, padx=5)

        # Name label
        name_label = ctk.CTkLabel(row, text=name, width=200, anchor="w")
        name_label.pack(side="left", padx=10, pady=8)

        # Progress bar
        progress_pct = produced / target if target > 0 else 0
        progress_bar = ctk.CTkProgressBar(row, width=150)
        progress_bar.set(min(progress_pct, 1.0))  # Cap at 1.0 for display
        progress_bar.pack(side="left", padx=10)

        # Progress text (can show > 100%)
        pct_display = int(progress_pct * 100)
        text = f"{produced}/{target} ({pct_display}%)"
        text_label = ctk.CTkLabel(row, text=text, width=100)
        text_label.pack(side="left", padx=10)

        # Complete indicator
        if produced >= target:
            check = ctk.CTkLabel(row, text="✓", text_color="green", font=ctk.CTkFont(size=16))
            check.pack(side="left", padx=5)

        # Delete button
        def on_delete():
            if is_production:
                self._on_delete_production_target(target_id)
            else:
                self._on_delete_assembly_target(target_id)

        del_btn = ctk.CTkButton(
            row,
            text="Del",
            width=50,
            fg_color="darkred",
            hover_color="red",
            command=on_delete,
        )
        del_btn.pack(side="right", padx=5, pady=5)

        # Edit button
        def on_edit():
            if is_production:
                self._on_edit_production_target(target_id, target)
            else:
                self._on_edit_assembly_target(target_id, target)

        edit_btn = ctk.CTkButton(row, text="Edit", width=50, command=on_edit)
        edit_btn.pack(side="right", padx=5, pady=5)

        return row

    def _on_add_production_target(self):
        """Handle Add Production Target button click."""
        dialog = AddProductionTargetDialog(self, event_id=self.event.id)
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                with session_scope() as session:
                    event_service.set_production_target(
                        event_id=self.event.id,
                        recipe_id=result["recipe_id"],
                        target_batches=result["target_batches"],
                        notes=result.get("notes"),
                        session=session,
                    )
                show_success("Success", "Production target added", parent=self)
                self._refresh_targets()
            except Exception as e:
                show_error("Error", f"Failed to add target: {str(e)}", parent=self)

    def _on_add_assembly_target(self):
        """Handle Add Assembly Target button click."""
        dialog = AddAssemblyTargetDialog(self, event_id=self.event.id)
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                with session_scope() as session:
                    event_service.set_assembly_target(
                        event_id=self.event.id,
                        finished_good_id=result["finished_good_id"],
                        target_quantity=result["target_quantity"],
                        notes=result.get("notes"),
                        session=session,
                    )
                show_success("Success", "Assembly target added", parent=self)
                self._refresh_targets()
            except Exception as e:
                show_error("Error", f"Failed to add target: {str(e)}", parent=self)

    def _on_edit_production_target(self, recipe_id: int, current_target: int):
        """Handle edit production target."""
        dialog = EditTargetDialog(
            self,
            title="Edit Production Target",
            current_value=current_target,
            label="Target Batches:",
        )
        self.wait_window(dialog)

        result = dialog.get_result()
        if result is not None:
            try:
                with session_scope() as session:
                    event_service.set_production_target(
                        event_id=self.event.id,
                        recipe_id=recipe_id,
                        target_batches=result,
                        session=session,
                    )
                show_success("Success", "Production target updated", parent=self)
                self._refresh_targets()
            except Exception as e:
                show_error("Error", f"Failed to update target: {str(e)}", parent=self)

    def _on_edit_assembly_target(self, finished_good_id: int, current_target: int):
        """Handle edit assembly target."""
        dialog = EditTargetDialog(
            self,
            title="Edit Assembly Target",
            current_value=current_target,
            label="Target Quantity:",
        )
        self.wait_window(dialog)

        result = dialog.get_result()
        if result is not None:
            try:
                with session_scope() as session:
                    event_service.set_assembly_target(
                        event_id=self.event.id,
                        finished_good_id=finished_good_id,
                        target_quantity=result,
                        session=session,
                    )
                show_success("Success", "Assembly target updated", parent=self)
                self._refresh_targets()
            except Exception as e:
                show_error("Error", f"Failed to update target: {str(e)}", parent=self)

    def _on_delete_production_target(self, recipe_id: int):
        """Handle delete production target."""
        if not show_confirmation(
            "Confirm Delete",
            "Delete this production target?",
            parent=self,
        ):
            return

        try:
            with session_scope() as session:
                event_service.delete_production_target(
                    self.event.id, recipe_id, session=session
                )
            show_success("Success", "Production target deleted", parent=self)
            self._refresh_targets()
        except Exception as e:
            show_error("Error", f"Failed to delete target: {str(e)}", parent=self)

    def _on_delete_assembly_target(self, finished_good_id: int):
        """Handle delete assembly target."""
        if not show_confirmation(
            "Confirm Delete",
            "Delete this assembly target?",
            parent=self,
        ):
            return

        try:
            with session_scope() as session:
                event_service.delete_assembly_target(
                    self.event.id, finished_good_id, session=session
                )
            show_success("Success", "Assembly target deleted", parent=self)
            self._refresh_targets()
        except Exception as e:
            show_error("Error", f"Failed to delete target: {str(e)}", parent=self)

    def _refresh_targets(self):
        """Refresh the targets tab with current progress data."""
        # Clear production targets
        for widget in self.production_targets_container.winfo_children():
            widget.destroy()

        # Clear assembly targets
        for widget in self.assembly_targets_container.winfo_children():
            widget.destroy()

        try:
            # Get production progress
            prod_progress = event_service.get_production_progress(self.event.id)

            if not prod_progress:
                empty_label = ctk.CTkLabel(
                    self.production_targets_container,
                    text="No production targets set. Click '+ Add Target' to create one.",
                    text_color="gray",
                    font=ctk.CTkFont(slant="italic"),
                )
                empty_label.pack(pady=10)
            else:
                for p in prod_progress:
                    self._create_progress_row(
                        self.production_targets_container,
                        name=p["recipe_name"],
                        produced=p["produced_batches"],
                        target=p["target_batches"],
                        target_id=p["recipe_id"],
                        is_production=True,
                    )

            # Get assembly progress
            asm_progress = event_service.get_assembly_progress(self.event.id)

            if not asm_progress:
                empty_label = ctk.CTkLabel(
                    self.assembly_targets_container,
                    text="No assembly targets set. Click '+ Add Target' to create one.",
                    text_color="gray",
                    font=ctk.CTkFont(slant="italic"),
                )
                empty_label.pack(pady=10)
            else:
                for a in asm_progress:
                    self._create_progress_row(
                        self.assembly_targets_container,
                        name=a["finished_good_name"],
                        produced=a["assembled_quantity"],
                        target=a["target_quantity"],
                        target_id=a["finished_good_id"],
                        is_production=False,
                    )

        except Exception as e:
            error_label = ctk.CTkLabel(
                self.production_targets_container,
                text=f"Error loading targets: {str(e)}",
                text_color="red",
            )
            error_label.pack(pady=10)

    def _create_recipe_needs_tab(self):
        """Create recipe needs tab."""
        tab_frame = self.tabview.tab("Recipe Needs")
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(0, weight=1)

        # Recipe needs display (scrollable)
        self.recipe_needs_frame = ctk.CTkScrollableFrame(tab_frame)
        self.recipe_needs_frame.grid(row=0, column=0, sticky="nsew", pady=PADDING_MEDIUM)
        self.recipe_needs_frame.grid_columnconfigure(0, weight=1)

    def _create_shopping_list_tab(self):
        """Create shopping list tab."""
        tab_frame = self.tabview.tab("Shopping List")
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(2, weight=1)

        # Header frame with title and export button (Feature 017)
        header_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, PADDING_MEDIUM))
        header_frame.grid_columnconfigure(0, weight=1)

        # Instructions (left side)
        instructions = ctk.CTkLabel(
            header_frame,
            text="Shopping list compares what you need for this event vs current inventory on hand.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray",
        )
        instructions.grid(row=0, column=0, sticky="w")

        # Export CSV button (right side) - Feature 017
        self.export_csv_button = ctk.CTkButton(
            header_frame,
            text="Export CSV",
            command=self._export_shopping_list_csv,
            width=100,
        )
        self.export_csv_button.grid(row=0, column=1, sticky="e", padx=PADDING_MEDIUM)

        # Shopping list display (scrollable)
        self.shopping_list_frame = ctk.CTkScrollableFrame(tab_frame)
        self.shopping_list_frame.grid(row=2, column=0, sticky="nsew", pady=PADDING_MEDIUM)
        self.shopping_list_frame.grid_columnconfigure(0, weight=1)

    # =========================================================================
    # Feature 017: CSV Export Methods
    # =========================================================================

    def _get_default_csv_filename(self) -> str:
        """Generate default CSV filename from event name.

        Returns:
            Filename like 'christmas-cookies-2024-shopping-list.csv'
        """
        # Convert event name to slug: lowercase, replace non-alphanumeric with hyphens
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", self.event.name.lower()).strip("-")
        return f"{slug}-shopping-list.csv"

    def _export_shopping_list_csv(self):
        """Handle CSV export button click (Feature 017 - T016-T019)."""
        # T017: Show file save dialog with default filename
        default_filename = self._get_default_csv_filename()
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Shopping List",
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )

        # User cancelled
        if not file_path:
            return

        # T018: Call export service method
        try:
            with ui_session() as session:
                success = event_service.export_shopping_list_csv(
                    self.event.id,
                    file_path,
                    session=session,
                )
            if success:
                # T019: Show success notification
                messagebox.showinfo(
                    "Export Successful",
                    f"Shopping list exported to:\n{file_path}",
                    parent=self,
                )
            else:
                # Nothing to export - show informational message
                messagebox.showinfo(
                    "Nothing to Export",
                    "The shopping list is empty. There are no ingredients or packaging "
                    "materials to export for this event.",
                    parent=self,
                )
        except IOError as e:
            # T019: Show error notification
            messagebox.showerror(
                "Export Failed",
                f"Could not write file:\n{str(e)}",
                parent=self,
            )
        except Exception as e:
            messagebox.showerror(
                "Export Failed",
                f"An error occurred:\n{str(e)}",
                parent=self,
            )

    # =========================================================================
    # End Feature 017 CSV Export
    # =========================================================================

    def _create_summary_tab(self):
        """Create summary tab."""
        tab_frame = self.tabview.tab("Summary")
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(0, weight=1)

        # Summary display (scrollable)
        self.summary_frame = ctk.CTkScrollableFrame(tab_frame)
        self.summary_frame.grid(row=0, column=0, sticky="nsew", pady=PADDING_MEDIUM)
        self.summary_frame.grid_columnconfigure(0, weight=1)

    def _create_buttons(self):
        """Create bottom buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        button_frame.grid_columnconfigure(0, weight=1)

        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
            width=150,
        )
        close_button.grid(row=0, column=0, pady=5)

    def _add_assignment(self):
        """Add a new package assignment to recipient."""
        dialog = AssignmentFormDialog(
            self, event_id=self.event.id, title="Assign Package to Recipient"
        )
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                with ui_session() as session:
                    event_service.assign_package_to_recipient(
                        self.event.id,
                        result["recipient_id"],
                        result["package_id"],
                        result.get("quantity", 1),
                        result.get("notes"),
                        session=session,
                    )
                show_success("Success", "Package assigned successfully", parent=self)
                self.refresh()
            except Exception as e:
                show_error("Error", f"Failed to assign package: {str(e)}", parent=self)

    def _edit_assignment(self):
        """Edit selected assignment."""
        if not self.selected_assignment:
            return

        dialog = AssignmentFormDialog(
            self,
            event_id=self.event.id,
            assignment=self.selected_assignment,
            title="Edit Assignment",
        )
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                with ui_session() as session:
                    event_service.update_assignment(
                        self.selected_assignment.id,
                        result["package_id"],
                        result.get("quantity", 1),
                        result.get("notes"),
                        session=session,
                    )
                show_success("Success", "Assignment updated successfully", parent=self)
                self.refresh()
            except Exception as e:
                show_error("Error", f"Failed to update assignment: {str(e)}", parent=self)

    def _delete_assignment(self):
        """Delete selected assignment."""
        if not self.selected_assignment:
            return

        recipient_name = (
            self.selected_assignment.recipient.name
            if self.selected_assignment.recipient
            else "Unknown"
        )

        if not show_confirmation(
            "Confirm Removal", f"Remove package assignment for {recipient_name}?", parent=self
        ):
            return

        try:
            with ui_session() as session:
                event_service.remove_assignment(self.selected_assignment.id, session=session)
            show_success("Success", "Assignment removed successfully", parent=self)
            self.selected_assignment = None
            self.refresh()
        except AssignmentNotFoundError:
            show_error("Error", "Assignment not found", parent=self)
            self.refresh()
        except Exception as e:
            show_error("Error", f"Failed to remove assignment: {str(e)}", parent=self)

    def refresh(self):
        """Refresh all tab contents."""
        self._refresh_assignments()
        self._refresh_targets()  # Feature 016
        self._refresh_recipe_needs()
        self._refresh_shopping_list()
        self._refresh_summary()

    def _refresh_assignments(self):
        """Refresh assignments tab."""
        # Clear existing
        for widget in self.assignments_frame.winfo_children():
            widget.destroy()

        # Get assignments
        try:
            with ui_session() as session:
                assignments = event_service.get_event_assignments(self.event.id, session=session)

            if not assignments:
                label = ctk.CTkLabel(
                    self.assignments_frame,
                    text="No package assignments yet. Click 'Assign Package to Recipient' to get started.",
                    font=ctk.CTkFont(size=12, slant="italic"),
                    text_color="gray",
                )
                label.grid(row=0, column=0, pady=50)
                return

            # Header - Feature 016: Added Status column
            header_frame = ctk.CTkFrame(self.assignments_frame, fg_color=("gray85", "gray25"))
            header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
            header_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

            ctk.CTkLabel(header_frame, text="Recipient", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=0, padx=10, pady=8
            )
            ctk.CTkLabel(header_frame, text="Package", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=1, padx=10, pady=8
            )
            ctk.CTkLabel(header_frame, text="Quantity", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=2, padx=10, pady=8
            )
            ctk.CTkLabel(header_frame, text="Cost", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=3, padx=10, pady=8
            )
            ctk.CTkLabel(header_frame, text="Status", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=4, padx=10, pady=8
            )

            # Rows
            for idx, assignment in enumerate(assignments, start=1):
                recipient_name = assignment.recipient.name if assignment.recipient else "Unknown"
                package_name = assignment.package.name if assignment.package else "Unknown"
                cost = assignment.calculate_cost()

                # Feature 016: Check if delivered for styling
                is_delivered = assignment.fulfillment_status == FulfillmentStatus.DELIVERED
                text_color = "gray" if is_delivered else None

                row_frame = ctk.CTkFrame(self.assignments_frame, fg_color="transparent")
                row_frame.grid(row=idx, column=0, sticky="ew", pady=2)
                row_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

                # Make row clickable
                def make_click_handler(asgn):
                    return lambda e: self._on_assignment_select(asgn)

                row_frame.bind("<Button-1>", make_click_handler(assignment))

                recipient_label = ctk.CTkLabel(
                    row_frame, text=recipient_name, text_color=text_color
                )
                recipient_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
                recipient_label.bind("<Button-1>", make_click_handler(assignment))

                package_label = ctk.CTkLabel(row_frame, text=package_name, text_color=text_color)
                package_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")
                package_label.bind("<Button-1>", make_click_handler(assignment))

                qty_label = ctk.CTkLabel(
                    row_frame, text=str(assignment.quantity), text_color=text_color
                )
                qty_label.grid(row=0, column=2, padx=10, pady=5, sticky="w")
                qty_label.bind("<Button-1>", make_click_handler(assignment))

                cost_label = ctk.CTkLabel(row_frame, text=f"${cost:.2f}", text_color=text_color)
                cost_label.grid(row=0, column=3, padx=10, pady=5, sticky="w")
                cost_label.bind("<Button-1>", make_click_handler(assignment))

                # Feature 016: Add fulfillment status control
                self._create_fulfillment_status_control(row_frame, assignment, 4)

        except Exception as e:
            label = ctk.CTkLabel(
                self.assignments_frame,
                text=f"Error loading assignments: {str(e)}",
                text_color="red",
            )
            label.grid(row=0, column=0, pady=20)

    def _on_assignment_select(self, assignment: EventRecipientPackage):
        """Handle assignment selection."""
        self.selected_assignment = assignment
        self.edit_assignment_button.configure(state="normal")
        self.delete_assignment_button.configure(state="normal")

    def _get_valid_next_statuses(
        self, current_status: FulfillmentStatus
    ) -> List[FulfillmentStatus]:
        """Get valid next statuses for sequential workflow (Feature 016).

        Args:
            current_status: Current fulfillment status

        Returns:
            List of valid next statuses (empty if terminal)
        """
        transitions = {
            FulfillmentStatus.PENDING: [FulfillmentStatus.READY],
            FulfillmentStatus.READY: [FulfillmentStatus.DELIVERED],
            FulfillmentStatus.DELIVERED: [],  # Terminal state
        }
        return transitions.get(current_status, [])

    def _create_fulfillment_status_control(
        self, parent, assignment: EventRecipientPackage, column: int
    ):
        """Create the fulfillment status control for an assignment row (Feature 016).

        Args:
            parent: Parent widget (row frame)
            assignment: The EventRecipientPackage
            column: Grid column to place the control
        """
        current_status = assignment.fulfillment_status or FulfillmentStatus.PENDING
        valid_next = self._get_valid_next_statuses(current_status)

        if current_status == FulfillmentStatus.DELIVERED:
            # Terminal state - show checkmark with green styling
            label = ctk.CTkLabel(
                parent,
                text="✓ Delivered",
                text_color="green",
                font=ctk.CTkFont(weight="bold"),
            )
            label.grid(row=0, column=column, padx=10, pady=5, sticky="w")
        elif not valid_next:
            # No valid transitions (shouldn't happen for non-delivered)
            label = ctk.CTkLabel(parent, text=current_status.value.capitalize())
            label.grid(row=0, column=column, padx=10, pady=5, sticky="w")
        else:
            # Show dropdown with current + valid next statuses
            options = [current_status.value.capitalize()] + [
                s.value.capitalize() for s in valid_next
            ]
            var = ctk.StringVar(value=current_status.value.capitalize())

            def on_change(value, asgn=assignment):
                self._on_fulfillment_status_change(asgn, value)

            dropdown = ctk.CTkOptionMenu(
                parent,
                variable=var,
                values=options,
                width=100,
                command=on_change,
            )
            dropdown.grid(row=0, column=column, padx=10, pady=5, sticky="w")

    def _on_fulfillment_status_change(self, assignment: EventRecipientPackage, new_status_str: str):
        """Handle fulfillment status change from dropdown (Feature 016).

        Args:
            assignment: The EventRecipientPackage being updated
            new_status_str: New status string (e.g., "Ready", "Delivered")
        """
        try:
            new_status = FulfillmentStatus(new_status_str.lower())
            with session_scope() as session:
                event_service.update_fulfillment_status(
                    assignment.id, new_status, session=session
                )
            self._refresh_assignments()
        except ValueError as e:
            show_error(
                "Invalid Transition",
                f"Cannot change status: {str(e)}",
                parent=self,
            )
            self._refresh_assignments()  # Refresh to reset dropdown to valid state

    def _refresh_recipe_needs(self):
        """Refresh recipe needs tab."""
        # Clear existing
        for widget in self.recipe_needs_frame.winfo_children():
            widget.destroy()

        try:
            with ui_session() as session:
                recipe_needs = event_service.get_recipe_needs(self.event.id, session=session)

            if not recipe_needs:
                label = ctk.CTkLabel(
                    self.recipe_needs_frame,
                    text="No recipe needs calculated yet. Add package assignments first.",
                    font=ctk.CTkFont(size=12, slant="italic"),
                    text_color="gray",
                )
                label.grid(row=0, column=0, pady=50)
                return

            # Title
            title_label = ctk.CTkLabel(
                self.recipe_needs_frame,
                text="Recipes Needed for This Event",
                font=ctk.CTkFont(size=16, weight="bold"),
            )
            title_label.grid(row=0, column=0, sticky="w", pady=(0, 15))

            # Recipe list
            row = 1
            for recipe_id, data in recipe_needs.items():
                recipe = data["recipe"]
                batches = data["batches"]
                items = data["items"]

                frame = ctk.CTkFrame(self.recipe_needs_frame, fg_color=("gray90", "gray20"))
                frame.grid(row=row, column=0, sticky="ew", pady=5)
                frame.grid_columnconfigure(0, weight=1)

                name_label = ctk.CTkLabel(
                    frame, text=recipe.name, font=ctk.CTkFont(size=14, weight="bold")
                )
                name_label.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

                details_label = ctk.CTkLabel(
                    frame,
                    text=f"  • Batches needed: {batches:.2f}   |   Total items: {items}",
                    font=ctk.CTkFont(size=12),
                )
                details_label.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 10))

                row += 1

        except Exception as e:
            label = ctk.CTkLabel(
                self.recipe_needs_frame,
                text=f"Error calculating recipe needs: {str(e)}",
                text_color="red",
            )
            label.grid(row=0, column=0, pady=20)

    def _format_single_product(self, rec, show_preferred=False, recipe_unit="unit"):
        """Format columns for a single product recommendation.

        Args:
            rec: Product recommendation dict
            show_preferred: Whether to show [preferred] indicator
            recipe_unit: Unit for cost display (e.g., "cup")

        Returns:
            Tuple of (brand, package_size, cost_unit, est_cost) strings
        """
        if not rec:
            return ("", "", "", "")

        # Brand with [preferred] indicator (T010)
        brand = rec.get("brand", "")
        if show_preferred and rec.get("is_preferred"):
            brand = f"{brand} [preferred]"

        # Package size context: "25 lb bag"
        package_size = rec.get("package_size", "")

        # Cost per recipe unit: "$0.18/cup"
        cost_per_unit = rec.get("cost_per_recipe_unit")
        cost_available = rec.get("cost_available", True)
        if cost_per_unit and cost_available:
            cost_unit = f"${float(cost_per_unit):.2f}/{recipe_unit}"
        elif not cost_available:
            cost_unit = "Cost unknown"
        else:
            cost_unit = "-"

        # Estimated total cost
        total_cost = rec.get("total_cost")
        if total_cost and cost_available:
            est_cost = f"${float(total_cost):.2f}"
        else:
            est_cost = "-"

        return (brand, package_size, cost_unit, est_cost)

    def _refresh_shopping_list(self):
        """Refresh shopping list tab with product recommendations (Feature 007)."""
        # Clear existing
        for widget in self.shopping_list_frame.winfo_children():
            widget.destroy()

        try:
            # Feature 007: Now returns dict with 'items' key
            with ui_session() as session:
                shopping_data = event_service.get_shopping_list(
                    self.event.id,
                    session=session,
                )

            if not shopping_data or not shopping_data.get("items"):
                label = ctk.CTkLabel(
                    self.shopping_list_frame,
                    text="No shopping needed. Add package assignments first.",
                    font=ctk.CTkFont(size=12, slant="italic"),
                    text_color="gray",
                )
                label.grid(row=0, column=0, pady=50)
                return

            # Title
            title_label = ctk.CTkLabel(
                self.shopping_list_frame,
                text="Shopping List",
                font=ctk.CTkFont(size=16, weight="bold"),
            )
            title_label.grid(row=0, column=0, sticky="w", pady=(0, 15))

            # Header (T008: Extended with product columns)
            header_frame = ctk.CTkFrame(self.shopping_list_frame, fg_color=("gray85", "gray25"))
            header_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
            header_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)

            headers = [
                "Ingredient",
                "Needed",
                "On Hand",
                "To Buy",
                "Product",
                "Package",
                "Cost/Unit",
                "Est. Cost",
            ]
            for col, header in enumerate(headers):
                ctk.CTkLabel(header_frame, text=header, font=ctk.CTkFont(weight="bold")).grid(
                    row=0, column=col, padx=8, pady=8
                )

            # Shopping items
            row = 2
            for item in shopping_data["items"]:
                shortfall = float(item.get("shortfall", 0))
                if shortfall <= 0:
                    continue  # Skip items we don't need to buy

                ingredient_name = item.get("ingredient_name", "Unknown")
                quantity_needed = float(item.get("quantity_needed", 0))
                quantity_on_hand = float(item.get("quantity_on_hand", 0))
                unit = item.get("unit", "")
                product_status = item.get("product_status", "none")

                # Format base columns
                needed_str = f"{quantity_needed:.2f} {unit}"
                on_hand_str = f"{quantity_on_hand:.2f} {unit}"
                to_buy_str = f"{shortfall:.2f} {unit}"

                # Handle different product statuses (T009, T010, T011)
                if product_status == "multiple":
                    # T009: Multiple products - display as stacked rows
                    all_products = item.get("all_products", [])
                    if all_products:
                        # First row with ingredient info
                        first_product = all_products[0]
                        v_cols = self._format_single_product(
                            first_product, show_preferred=False, recipe_unit=unit
                        )
                        self._create_shopping_row(
                            row,
                            ingredient_name,
                            needed_str,
                            on_hand_str,
                            to_buy_str,
                            *v_cols,
                        )
                        row += 1

                        # Additional product rows (blank ingredient columns)
                        for product in all_products[1:]:
                            v_cols = self._format_single_product(
                                product, show_preferred=False, recipe_unit=unit
                            )
                            self._create_shopping_row(row, "", "", "", "", *v_cols, indent=True)
                            row += 1
                    else:
                        # No products available
                        self._create_shopping_row(
                            row,
                            ingredient_name,
                            needed_str,
                            on_hand_str,
                            to_buy_str,
                            "No product configured",
                            "",
                            "",
                            "",
                        )
                        row += 1

                elif product_status == "preferred":
                    # T010: Show preferred product with indicator
                    rec = item.get("product_recommendation")
                    v_cols = self._format_single_product(rec, show_preferred=True, recipe_unit=unit)
                    self._create_shopping_row(
                        row,
                        ingredient_name,
                        needed_str,
                        on_hand_str,
                        to_buy_str,
                        *v_cols,
                    )
                    row += 1

                elif product_status == "none":
                    # T011: No product configured fallback
                    self._create_shopping_row(
                        row,
                        ingredient_name,
                        needed_str,
                        on_hand_str,
                        to_buy_str,
                        "No product configured",
                        "",
                        "",
                        "",
                    )
                    row += 1

                else:
                    # Sufficient or other status - just show basic info
                    self._create_shopping_row(
                        row,
                        ingredient_name,
                        needed_str,
                        on_hand_str,
                        to_buy_str,
                        product_status.capitalize(),
                        "",
                        "",
                        "",
                    )
                    row += 1

            # Feature 011: Packaging section (if present)
            # Feature 026: Updated to show generic packaging with estimated costs
            packaging_data = shopping_data.get("packaging", [])
            if packaging_data:
                row += 1  # Add spacing

                # Packaging section title
                packaging_title = ctk.CTkLabel(
                    self.shopping_list_frame,
                    text="Packaging Materials",
                    font=ctk.CTkFont(size=16, weight="bold"),
                )
                packaging_title.grid(row=row, column=0, sticky="w", pady=(20, 10))
                row += 1

                # Packaging header - Feature 026: Added Est. Cost column
                pkg_header_frame = ctk.CTkFrame(
                    self.shopping_list_frame, fg_color=("gray85", "gray25")
                )
                pkg_header_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
                pkg_header_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

                pkg_headers = [
                    "Material",
                    "Product",
                    "Needed",
                    "On Hand",
                    "To Buy",
                    "Unit",
                    "Est. Cost",
                ]
                for col, header in enumerate(pkg_headers):
                    ctk.CTkLabel(
                        pkg_header_frame, text=header, font=ctk.CTkFont(weight="bold")
                    ).grid(row=0, column=col, padx=8, pady=8)
                row += 1

                # Packaging items
                for pkg_item in packaging_data:
                    ingredient_name = pkg_item.get("ingredient_name", "Unknown")
                    product_name = pkg_item.get("product_name", "")
                    total_needed = pkg_item.get("total_needed", 0)
                    on_hand = pkg_item.get("on_hand", 0)
                    to_buy = pkg_item.get("to_buy", 0)
                    unit = pkg_item.get("unit", "")
                    # Feature 026: Generic packaging fields
                    is_generic = pkg_item.get("is_generic", False)
                    estimated_cost = pkg_item.get("estimated_cost")

                    pkg_row_frame = ctk.CTkFrame(self.shopping_list_frame, fg_color="transparent")
                    pkg_row_frame.grid(row=row, column=0, sticky="ew", pady=1)
                    pkg_row_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

                    ctk.CTkLabel(pkg_row_frame, text=ingredient_name).grid(
                        row=0, column=0, padx=8, pady=5, sticky="w"
                    )

                    # Feature 026: For generic items, show product_name with indicator
                    if is_generic:
                        product_display = f"{product_name} (any)"
                        product_color = "gray60"
                    else:
                        product_display = product_name
                        product_color = None

                    product_label = ctk.CTkLabel(pkg_row_frame, text=product_display)
                    if product_color:
                        product_label.configure(text_color=product_color)
                    product_label.grid(row=0, column=1, padx=8, pady=5, sticky="w")

                    ctk.CTkLabel(pkg_row_frame, text=f"{total_needed:.1f}").grid(
                        row=0, column=2, padx=8, pady=5, sticky="w"
                    )
                    ctk.CTkLabel(pkg_row_frame, text=f"{on_hand:.1f}").grid(
                        row=0, column=3, padx=8, pady=5, sticky="w"
                    )

                    # Highlight to_buy if > 0
                    to_buy_text = f"{to_buy:.1f}"
                    to_buy_color = "red" if to_buy > 0 else None
                    to_buy_label = ctk.CTkLabel(pkg_row_frame, text=to_buy_text)
                    if to_buy_color:
                        to_buy_label.configure(text_color=to_buy_color)
                    to_buy_label.grid(row=0, column=4, padx=8, pady=5, sticky="w")

                    ctk.CTkLabel(pkg_row_frame, text=unit).grid(
                        row=0, column=5, padx=8, pady=5, sticky="w"
                    )

                    # Feature 026: Show estimated cost for generic items
                    if is_generic and estimated_cost is not None:
                        cost_text = f"~${float(estimated_cost):.2f}"
                        cost_label = ctk.CTkLabel(
                            pkg_row_frame, text=cost_text, text_color="gray60"
                        )
                    else:
                        cost_label = ctk.CTkLabel(pkg_row_frame, text="-")
                    cost_label.grid(row=0, column=6, padx=8, pady=5, sticky="w")

                    row += 1

            # T012: Total estimated cost at bottom
            total_estimated_cost = shopping_data.get("total_estimated_cost", 0)
            total_frame = ctk.CTkFrame(self.shopping_list_frame, fg_color=("gray90", "gray20"))
            total_frame.grid(row=row, column=0, sticky="ew", pady=(15, 0))
            total_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                total_frame,
                text=f"Total Estimated Cost: ${float(total_estimated_cost):.2f}",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=0, columnspan=8, padx=15, pady=15)

            # Note about total calculation
            note_label = ctk.CTkLabel(
                total_frame,
                text="* Total includes only items with a preferred product selected",
                font=ctk.CTkFont(size=10, slant="italic"),
                text_color="gray",
            )
            note_label.grid(row=1, column=0, columnspan=8, padx=15, pady=(0, 10))

        except Exception as e:
            label = ctk.CTkLabel(
                self.shopping_list_frame,
                text=f"Error generating shopping list: {str(e)}",
                text_color="red",
            )
            label.grid(row=0, column=0, pady=20)

    def _create_shopping_row(
        self,
        row,
        ingredient,
        needed,
        on_hand,
        to_buy,
        product,
        package,
        cost_unit,
        est_cost,
        indent=False,
    ):
        """Create a single row in the shopping list table.

        Args:
            row: Grid row number
            ingredient: Ingredient name (blank for sub-rows)
            needed: Quantity needed string
            on_hand: Quantity on hand string
            to_buy: Quantity to buy string
            product: Product brand/status text
            package: Package size text
            cost_unit: Cost per unit text
            est_cost: Estimated total cost text
            indent: Whether this is an indented sub-row (for multiple products)
        """
        # Different background for sub-rows to show grouping
        if indent:
            fg_color = ("gray95", "gray15")
        else:
            fg_color = "transparent"

        item_frame = ctk.CTkFrame(self.shopping_list_frame, fg_color=fg_color)
        item_frame.grid(row=row, column=0, sticky="ew", pady=1)
        item_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)

        # Add slight indent for sub-rows
        indent_text = "  " if indent else ""

        ctk.CTkLabel(item_frame, text=ingredient).grid(row=0, column=0, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=needed).grid(row=0, column=1, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=on_hand).grid(row=0, column=2, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=to_buy).grid(row=0, column=3, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=f"{indent_text}{product}").grid(
            row=0, column=4, padx=8, pady=5, sticky="w"
        )
        ctk.CTkLabel(item_frame, text=package).grid(row=0, column=5, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=cost_unit).grid(row=0, column=6, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=est_cost).grid(row=0, column=7, padx=8, pady=5, sticky="w")

    def _refresh_summary(self):
        """Refresh summary tab with comprehensive event reporting (Feature 017)."""
        # Clear existing
        for widget in self.summary_frame.winfo_children():
            widget.destroy()

        try:
            # Event info header
            ctk.CTkLabel(
                self.summary_frame,
                text="Event Summary",
                font=ctk.CTkFont(size=18, weight="bold"),
            ).pack(anchor="w", pady=(0, 10))

            # Get fresh event data
            with ui_session() as session:
                event = event_service.get_event_by_id(self.event.id, session=session)

            recipient_count = event.get_recipient_count()
            package_count = event.get_package_count()
            estimated_cost = event.get_total_cost()

            # Basic info section
            info_frame = ctk.CTkFrame(self.summary_frame, fg_color=("gray90", "gray20"))
            info_frame.pack(fill="x", pady=(0, 10))

            info_row = ctk.CTkFrame(info_frame, fg_color="transparent")
            info_row.pack(fill="x", padx=15, pady=10)

            ctk.CTkLabel(
                info_row,
                text=f"Recipients: {recipient_count}",
                font=ctk.CTkFont(size=14),
            ).pack(side="left", padx=10)

            ctk.CTkLabel(
                info_row,
                text=f"Total Packages: {package_count}",
                font=ctk.CTkFont(size=14),
            ).pack(side="left", padx=10)

            ctk.CTkLabel(
                info_row,
                text=f"Estimated Cost: ${estimated_cost:.2f}",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(side="left", padx=10)

            # Feature 017: T022 - Package fulfillment status counts
            self._create_summary_fulfillment_section()

            # Feature 017: T020 - Production planned vs actual
            self._create_summary_production_section()

            # Feature 017: T021 - Assembly planned vs actual
            self._create_summary_assembly_section()

            # Feature 017: T023 - Cost variance display
            self._create_summary_cost_section()

            # Notes section
            if event.notes:
                notes_frame = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
                notes_frame.pack(fill="x", pady=10)

                ctk.CTkLabel(
                    notes_frame,
                    text="Notes:",
                    font=ctk.CTkFont(size=14, weight="bold"),
                ).pack(anchor="w")

                ctk.CTkLabel(
                    notes_frame,
                    text=event.notes,
                    font=ctk.CTkFont(size=12),
                    wraplength=900,
                    justify="left",
                ).pack(anchor="w", pady=(5, 0))

        except Exception as e:
            label = ctk.CTkLabel(
                self.summary_frame,
                text=f"Error loading summary: {str(e)}",
                text_color="red",
            )
            label.pack(pady=20)

    # =========================================================================
    # Feature 017: Summary Enhancement Sections (T020-T023)
    # =========================================================================

    def _create_summary_fulfillment_section(self):
        """Create package fulfillment status section (T022)."""
        section_frame = ctk.CTkFrame(self.summary_frame, fg_color=("gray90", "gray20"))
        section_frame.pack(fill="x", pady=5)

        # Header
        ctk.CTkLabel(
            section_frame,
            text="Package Fulfillment Status",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        try:
            # Get overall progress which includes package counts
            from src.ui.utils import ui_session

            with ui_session() as session:
                progress = event_service.get_event_overall_progress(
                    self.event.id,
                    session=session,
                )

            # Create status row
            counts_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
            counts_frame.pack(fill="x", padx=15, pady=(0, 10))

            # Pending - light orange
            pending_label = ctk.CTkLabel(
                counts_frame,
                text=f"  Pending: {progress.get('packages_pending', 0)}  ",
                fg_color="#D4A574",
                text_color="black",
                corner_radius=5,
            )
            pending_label.pack(side="left", padx=5)

            # Ready - light green
            ready_label = ctk.CTkLabel(
                counts_frame,
                text=f"  Ready: {progress.get('packages_ready', 0)}  ",
                fg_color="#90EE90",
                text_color="black",
                corner_radius=5,
            )
            ready_label.pack(side="left", padx=5)

            # Delivered - light blue
            delivered_label = ctk.CTkLabel(
                counts_frame,
                text=f"  Delivered: {progress.get('packages_delivered', 0)}  ",
                fg_color="#87CEEB",
                text_color="black",
                corner_radius=5,
            )
            delivered_label.pack(side="left", padx=5)

            # Total
            ctk.CTkLabel(
                counts_frame,
                text=f"Total: {progress.get('packages_total', 0)}",
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=15)

        except Exception as e:
            ctk.CTkLabel(
                section_frame,
                text=f"Could not load fulfillment data: {e}",
                text_color="red",
            ).pack(padx=15, pady=5)

    def _create_summary_production_section(self):
        """Create production planned vs actual section (T020)."""
        section_frame = ctk.CTkFrame(self.summary_frame, fg_color=("gray90", "gray20"))
        section_frame.pack(fill="x", pady=5)

        # Header
        ctk.CTkLabel(
            section_frame,
            text="Production Summary (Planned vs Actual)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        try:
            progress = event_service.get_production_progress(self.event.id)

            if not progress:
                ctk.CTkLabel(
                    section_frame,
                    text="No production targets set for this event",
                    text_color="gray",
                    font=ctk.CTkFont(slant="italic"),
                ).pack(padx=15, pady=10)
                return

            # Table header
            header_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
            header_frame.pack(fill="x", padx=15)

            for col, width in [("Recipe", 200), ("Target", 80), ("Actual", 80), ("%", 80)]:
                ctk.CTkLabel(
                    header_frame,
                    text=col,
                    width=width,
                    font=ctk.CTkFont(weight="bold"),
                    anchor="w",
                ).pack(side="left")

            # Data rows
            for item in progress:
                row_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
                row_frame.pack(fill="x", padx=15)

                pct = item["progress_pct"]
                pct_text = f"{pct:.0f}%"
                pct_color = "green" if pct >= 100 else None

                ctk.CTkLabel(
                    row_frame,
                    text=item["recipe_name"],
                    width=200,
                    anchor="w",
                ).pack(side="left")
                ctk.CTkLabel(
                    row_frame,
                    text=str(item["target_batches"]),
                    width=80,
                    anchor="w",
                ).pack(side="left")
                ctk.CTkLabel(
                    row_frame,
                    text=str(item["produced_batches"]),
                    width=80,
                    anchor="w",
                ).pack(side="left")
                ctk.CTkLabel(
                    row_frame,
                    text=pct_text,
                    width=80,
                    text_color=pct_color,
                    anchor="w",
                ).pack(side="left")

            # Add padding at bottom
            ctk.CTkFrame(section_frame, height=5, fg_color="transparent").pack()

        except Exception as e:
            ctk.CTkLabel(
                section_frame,
                text=f"Could not load production data: {e}",
                text_color="red",
            ).pack(padx=15, pady=5)

    def _create_summary_assembly_section(self):
        """Create assembly planned vs actual section (T021)."""
        section_frame = ctk.CTkFrame(self.summary_frame, fg_color=("gray90", "gray20"))
        section_frame.pack(fill="x", pady=5)

        # Header
        ctk.CTkLabel(
            section_frame,
            text="Assembly Summary (Planned vs Actual)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        try:
            progress = event_service.get_assembly_progress(self.event.id)

            if not progress:
                ctk.CTkLabel(
                    section_frame,
                    text="No assembly targets set for this event",
                    text_color="gray",
                    font=ctk.CTkFont(slant="italic"),
                ).pack(padx=15, pady=10)
                return

            # Table header
            header_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
            header_frame.pack(fill="x", padx=15)

            for col, width in [("Finished Good", 200), ("Target", 80), ("Actual", 80), ("%", 80)]:
                ctk.CTkLabel(
                    header_frame,
                    text=col,
                    width=width,
                    font=ctk.CTkFont(weight="bold"),
                    anchor="w",
                ).pack(side="left")

            # Data rows
            for item in progress:
                row_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
                row_frame.pack(fill="x", padx=15)

                pct = item["progress_pct"]
                pct_text = f"{pct:.0f}%"
                pct_color = "green" if pct >= 100 else None

                ctk.CTkLabel(
                    row_frame,
                    text=item["finished_good_name"],
                    width=200,
                    anchor="w",
                ).pack(side="left")
                ctk.CTkLabel(
                    row_frame,
                    text=str(item["target_quantity"]),
                    width=80,
                    anchor="w",
                ).pack(side="left")
                ctk.CTkLabel(
                    row_frame,
                    text=str(item["assembled_quantity"]),
                    width=80,
                    anchor="w",
                ).pack(side="left")
                ctk.CTkLabel(
                    row_frame,
                    text=pct_text,
                    width=80,
                    text_color=pct_color,
                    anchor="w",
                ).pack(side="left")

            # Add padding at bottom
            ctk.CTkFrame(section_frame, height=5, fg_color="transparent").pack()

        except Exception as e:
            ctk.CTkLabel(
                section_frame,
                text=f"Could not load assembly data: {e}",
                text_color="red",
            ).pack(padx=15, pady=5)

    def _create_summary_cost_section(self):
        """Create cost variance section (T023)."""
        section_frame = ctk.CTkFrame(self.summary_frame, fg_color=("gray90", "gray20"))
        section_frame.pack(fill="x", pady=5)

        # Header
        ctk.CTkLabel(
            section_frame,
            text="Cost Analysis",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        try:
            with ui_session() as session:
                costs = event_service.get_event_cost_analysis(self.event.id, session=session)

            # Cost summary row
            cost_row = ctk.CTkFrame(section_frame, fg_color="transparent")
            cost_row.pack(fill="x", padx=15, pady=5)

            # Estimated cost
            ctk.CTkLabel(
                cost_row,
                text=f"Estimated: ${costs.get('estimated_cost', 0):.2f}",
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=10)

            # Actual cost
            ctk.CTkLabel(
                cost_row,
                text=f"Actual: ${costs.get('grand_total', 0):.2f}",
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=10)

            # Variance (positive = under budget, negative = over budget)
            variance = costs.get("variance", 0)
            variance_sign = "+" if variance >= 0 else ""
            variance_color = "green" if variance >= 0 else "red"

            ctk.CTkLabel(
                cost_row,
                text=f"Variance: {variance_sign}${variance:.2f}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=variance_color,
            ).pack(side="left", padx=10)

            # Breakdown section (if data available)
            prod_costs = costs.get("production_costs", [])
            asm_costs = costs.get("assembly_costs", [])

            if prod_costs or asm_costs:
                breakdown_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
                breakdown_frame.pack(fill="x", padx=15, pady=(5, 10))

                # Production costs breakdown
                if prod_costs:
                    ctk.CTkLabel(
                        breakdown_frame,
                        text="Production Costs by Recipe:",
                        font=ctk.CTkFont(size=11, weight="bold"),
                    ).pack(anchor="w")

                    for item in prod_costs:
                        text = f"  {item['recipe_name']}: ${item['total_cost']:.2f} ({item['run_count']} runs)"
                        ctk.CTkLabel(breakdown_frame, text=text).pack(anchor="w")

                # Assembly costs breakdown
                if asm_costs:
                    ctk.CTkLabel(
                        breakdown_frame,
                        text="Assembly Costs by Finished Good:",
                        font=ctk.CTkFont(size=11, weight="bold"),
                    ).pack(anchor="w", pady=(5, 0))

                    for item in asm_costs:
                        text = f"  {item['finished_good_name']}: ${item['total_cost']:.2f} ({item['run_count']} runs)"
                        ctk.CTkLabel(breakdown_frame, text=text).pack(anchor="w")
            else:
                ctk.CTkLabel(
                    section_frame,
                    text="No production or assembly costs recorded yet",
                    text_color="gray",
                    font=ctk.CTkFont(slant="italic"),
                ).pack(padx=15, pady=(0, 10))

        except Exception as e:
            ctk.CTkLabel(
                section_frame,
                text=f"Could not load cost data: {e}",
                text_color="red",
            ).pack(padx=15, pady=5)

    # =========================================================================
    # End Feature 017 Summary Enhancement
    # =========================================================================


# Feature 016: Dialog classes for target management


class AddProductionTargetDialog(ctk.CTkToplevel):
    """Dialog for adding a production target."""

    def __init__(self, parent, event_id: int):
        super().__init__(parent)

        self.event_id = event_id
        self.result = None

        self.title("Add Production Target")
        self.geometry("400x300")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        # Load recipes
        self.recipes = recipe_service.get_all_recipes()

        # Get existing targets to exclude
        with session_scope() as session:
            existing_targets = event_service.get_production_targets(
                event_id, session=session
            )
            existing_recipe_ids = {t.recipe_id for t in existing_targets}

        # Filter out already-targeted recipes
        self.available_recipes = [r for r in self.recipes if r.id not in existing_recipe_ids]

        self._create_widgets()
        self._center_on_parent()

    def _center_on_parent(self):
        """Center the dialog on its parent."""
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _create_widgets(self):
        """Create dialog widgets."""
        # Recipe selection
        ctk.CTkLabel(self, text="Recipe:").pack(pady=(20, 5), padx=20, anchor="w")

        if not self.available_recipes:
            ctk.CTkLabel(
                self,
                text="All recipes already have targets for this event.",
                text_color="gray",
            ).pack(pady=5, padx=20)
            self.recipe_var = None
        else:
            recipe_names = [r.name for r in self.available_recipes]
            self.recipe_var = ctk.StringVar(value=recipe_names[0] if recipe_names else "")
            self.recipe_dropdown = ctk.CTkOptionMenu(
                self,
                variable=self.recipe_var,
                values=recipe_names,
                width=300,
            )
            self.recipe_dropdown.pack(pady=5, padx=20)

        # Target batches
        ctk.CTkLabel(self, text="Target Batches:").pack(pady=(15, 5), padx=20, anchor="w")
        self.target_entry = ctk.CTkEntry(self, width=100)
        self.target_entry.insert(0, "1")
        self.target_entry.pack(pady=5, padx=20, anchor="w")

        # Notes
        ctk.CTkLabel(self, text="Notes (optional):").pack(pady=(15, 5), padx=20, anchor="w")
        self.notes_entry = ctk.CTkEntry(self, width=300)
        self.notes_entry.pack(pady=5, padx=20)

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=20)

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._on_save,
            state="normal" if self.recipe_var else "disabled",
        )
        save_btn.pack(side="left", padx=10)

        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side="left", padx=10)

    def _on_save(self):
        """Handle save button click."""
        if not self.recipe_var:
            return

        try:
            target_batches = int(self.target_entry.get())
            if target_batches < 1:
                raise ValueError("Target must be at least 1")
        except ValueError as e:
            show_error("Invalid Input", str(e), parent=self)
            return

        # Find selected recipe
        selected_name = self.recipe_var.get()
        recipe_id = None
        for r in self.available_recipes:
            if r.name == selected_name:
                recipe_id = r.id
                break

        if not recipe_id:
            show_error("Error", "Recipe not found", parent=self)
            return

        notes = self.notes_entry.get().strip() or None

        self.result = {
            "recipe_id": recipe_id,
            "target_batches": target_batches,
            "notes": notes,
        }
        self.destroy()

    def get_result(self):
        """Return the dialog result."""
        return self.result


class AddAssemblyTargetDialog(ctk.CTkToplevel):
    """Dialog for adding an assembly target."""

    def __init__(self, parent, event_id: int):
        super().__init__(parent)

        self.event_id = event_id
        self.result = None

        self.title("Add Assembly Target")
        self.geometry("400x300")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        # Load finished goods
        self.finished_goods = get_all_finished_goods()

        # Get existing targets to exclude
        with session_scope() as session:
            existing_targets = event_service.get_assembly_targets(
                event_id, session=session
            )
            existing_fg_ids = {t.finished_good_id for t in existing_targets}

        # Filter out already-targeted finished goods
        self.available_fgs = [fg for fg in self.finished_goods if fg.id not in existing_fg_ids]

        self._create_widgets()
        self._center_on_parent()

    def _center_on_parent(self):
        """Center the dialog on its parent."""
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _create_widgets(self):
        """Create dialog widgets."""
        # Finished Good selection
        ctk.CTkLabel(self, text="Finished Good:").pack(pady=(20, 5), padx=20, anchor="w")

        if not self.available_fgs:
            ctk.CTkLabel(
                self,
                text="All finished goods already have targets for this event.",
                text_color="gray",
            ).pack(pady=5, padx=20)
            self.fg_var = None
        else:
            fg_names = [fg.display_name for fg in self.available_fgs]
            self.fg_var = ctk.StringVar(value=fg_names[0] if fg_names else "")
            self.fg_dropdown = ctk.CTkOptionMenu(
                self,
                variable=self.fg_var,
                values=fg_names,
                width=300,
            )
            self.fg_dropdown.pack(pady=5, padx=20)

        # Target quantity
        ctk.CTkLabel(self, text="Target Quantity:").pack(pady=(15, 5), padx=20, anchor="w")
        self.target_entry = ctk.CTkEntry(self, width=100)
        self.target_entry.insert(0, "1")
        self.target_entry.pack(pady=5, padx=20, anchor="w")

        # Notes
        ctk.CTkLabel(self, text="Notes (optional):").pack(pady=(15, 5), padx=20, anchor="w")
        self.notes_entry = ctk.CTkEntry(self, width=300)
        self.notes_entry.pack(pady=5, padx=20)

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=20)

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._on_save,
            state="normal" if self.fg_var else "disabled",
        )
        save_btn.pack(side="left", padx=10)

        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side="left", padx=10)

    def _on_save(self):
        """Handle save button click."""
        if not self.fg_var:
            return

        try:
            target_quantity = int(self.target_entry.get())
            if target_quantity < 1:
                raise ValueError("Target must be at least 1")
        except ValueError as e:
            show_error("Invalid Input", str(e), parent=self)
            return

        # Find selected finished good
        selected_name = self.fg_var.get()
        fg_id = None
        for fg in self.available_fgs:
            if fg.display_name == selected_name:
                fg_id = fg.id
                break

        if not fg_id:
            show_error("Error", "Finished good not found", parent=self)
            return

        notes = self.notes_entry.get().strip() or None

        self.result = {
            "finished_good_id": fg_id,
            "target_quantity": target_quantity,
            "notes": notes,
        }
        self.destroy()

    def get_result(self):
        """Return the dialog result."""
        return self.result


class EditTargetDialog(ctk.CTkToplevel):
    """Simple dialog for editing a target value."""

    def __init__(self, parent, title: str, current_value: int, label: str):
        super().__init__(parent)

        self.result = None

        self.title(title)
        self.geometry("300x150")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._create_widgets(label, current_value)
        self._center_on_parent()

    def _center_on_parent(self):
        """Center the dialog on its parent."""
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _create_widgets(self, label: str, current_value: int):
        """Create dialog widgets."""
        ctk.CTkLabel(self, text=label).pack(pady=(20, 5), padx=20, anchor="w")

        self.value_entry = ctk.CTkEntry(self, width=100)
        self.value_entry.insert(0, str(current_value))
        self.value_entry.pack(pady=5, padx=20, anchor="w")

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=20)

        save_btn = ctk.CTkButton(button_frame, text="Save", command=self._on_save)
        save_btn.pack(side="left", padx=10)

        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side="left", padx=10)

    def _on_save(self):
        """Handle save button click."""
        try:
            value = int(self.value_entry.get())
            if value < 1:
                raise ValueError("Value must be at least 1")
            self.result = value
            self.destroy()
        except ValueError as e:
            show_error("Invalid Input", str(e), parent=self)

    def get_result(self):
        """Return the dialog result."""
        return self.result
