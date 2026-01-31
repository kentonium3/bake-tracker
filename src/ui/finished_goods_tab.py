"""
Finished Goods tab for the Seasonal Baking Tracker.

Feature 088: Finished Goods Catalog UI - F087 3-row layout pattern.

Provides full CRUD interface for managing FinishedGood assemblies
(gift boxes, variety packs, etc.) using ttk.Treeview for trackpad scrolling.
"""

import customtkinter as ctk
from tkinter import ttk
from typing import Optional, List

from src.models.finished_good import FinishedGood
from src.models.assembly_type import AssemblyType
from src.services import finished_good_service
from src.utils.constants import (
    PADDING_MEDIUM,
    PADDING_LARGE,
    COLOR_SUCCESS,
    COLOR_ERROR,
)
from src.ui.widgets.dialogs import (
    show_confirmation,
    show_error,
    show_success,
    show_info,
)
from src.ui.forms.finished_good_form import FinishedGoodFormDialog


class FinishedGoodsTab(ctk.CTkFrame):
    """
    Finished Goods management tab with full CRUD capabilities.

    Uses F087 3-row layout pattern:
    - Row 0: Search bar with assembly type filter
    - Row 1: Action buttons (Add, Edit, Delete, View Details, Refresh)
    - Row 2: ttk.Treeview for trackpad scrolling
    - Row 3: Status bar

    Provides interface for:
    - Viewing all finished goods in a searchable treeview
    - Adding new finished goods with components
    - Editing existing finished goods
    - Deleting finished goods
    - Viewing finished good details
    - Filtering by assembly type
    """

    def __init__(self, parent):
        """
        Initialize the finished goods tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.selected_finished_good: Optional[FinishedGood] = None

        # Track current finished goods for selection lookup
        self._current_finished_goods: List[FinishedGood] = []

        # Track current sort state for column header sorting
        self.sort_column = "name"
        self.sort_ascending = True

        # Configure grid - F087 3-row layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Search bar
        self.grid_rowconfigure(1, weight=0)  # Action buttons
        self.grid_rowconfigure(2, weight=1)  # Data table (Treeview)
        self.grid_rowconfigure(3, weight=0)  # Status bar

        # Create UI components
        self._create_search_bar()
        self._create_action_buttons()
        self._create_data_table()
        self._create_status_bar()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _get_assembly_type_options(self) -> List[str]:
        """Get display names for assembly type filter dropdown."""
        return [
            "Custom Order",
            "Gift Box",
            "Variety Pack",
            "Holiday Set",
            "Bulk Pack",
        ]

    def _create_search_bar(self):
        """Create the search bar with assembly type filter."""
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.grid(
            row=0, column=0, sticky="ew",
            padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM)
        )
        self.search_frame.grid_columnconfigure(0, weight=0)  # Type dropdown
        self.search_frame.grid_columnconfigure(1, weight=1)  # Search entry
        self.search_frame.grid_columnconfigure(2, weight=0)  # Search button

        # Assembly Type filter dropdown
        self.type_var = ctk.StringVar(value="All Types")
        self.type_dropdown = ctk.CTkOptionMenu(
            self.search_frame,
            variable=self.type_var,
            values=["All Types"] + self._get_assembly_type_options(),
            width=150,
            command=self._on_type_filter_changed,
        )
        self.type_dropdown.grid(row=0, column=0, padx=(0, 10), sticky="w")

        # Search entry
        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Search by name...",
            height=35,
        )
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self._on_search())
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_key_release())

        # Search button
        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Search",
            width=100,
            command=self._on_search,
        )
        self.search_button.grid(row=0, column=2, padx=(10, 0), sticky="e")

    def _create_action_buttons(self):
        """Create action buttons for CRUD operations."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(
            row=1, column=0, sticky="ew",
            padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

        # Add button
        add_button = ctk.CTkButton(
            button_frame,
            text="+ Add Finished Good",
            command=self._add_finished_good,
            width=180,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="Edit",
            command=self._edit_finished_good,
            width=120,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="Delete",
            command=self._delete_finished_good,
            width=120,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_button.grid(row=0, column=2, padx=PADDING_MEDIUM)

        # View Details button
        self.details_button = ctk.CTkButton(
            button_frame,
            text="View Details",
            command=self._view_details,
            width=150,
            state="disabled",
        )
        self.details_button.grid(row=0, column=3, padx=PADDING_MEDIUM)

        # Refresh button
        refresh_button = ctk.CTkButton(
            button_frame,
            text="Refresh",
            command=self.refresh,
            width=120,
        )
        refresh_button.grid(row=0, column=4, padx=PADDING_MEDIUM)

    def _create_data_table(self):
        """Create the data table using ttk.Treeview (F087 pattern)."""
        # Container frame for treeview and scrollbar
        self.grid_container = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_container.grid(
            row=2, column=0, sticky="nsew",
            padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )
        self.grid_container.grid_columnconfigure(0, weight=1)
        self.grid_container.grid_rowconfigure(0, weight=1)

        # Define columns: Name, Assembly Type, Component Count, Notes
        columns = ("name", "assembly_type", "components", "notes")
        self.tree = ttk.Treeview(
            self.grid_container,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        # Configure column headings with click-to-sort
        self.tree.heading(
            "name", text="Name", anchor="w",
            command=lambda: self._on_header_click("name")
        )
        self.tree.heading(
            "assembly_type", text="Assembly Type", anchor="w",
            command=lambda: self._on_header_click("assembly_type")
        )
        self.tree.heading(
            "components", text="Components", anchor="w",
            command=lambda: self._on_header_click("components")
        )
        self.tree.heading(
            "notes", text="Notes", anchor="w",
            command=lambda: self._on_header_click("notes")
        )

        # Configure column widths
        self.tree.column("name", width=250, minwidth=150)
        self.tree.column("assembly_type", width=120, minwidth=80)
        self.tree.column("components", width=100, minwidth=60)
        self.tree.column("notes", width=200, minwidth=100)

        # Add vertical scrollbar for trackpad scrolling
        y_scrollbar = ttk.Scrollbar(
            self.grid_container,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=y_scrollbar.set)

        # Grid the tree and scrollbar
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind selection and double-click events
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

    def _create_status_bar(self):
        """Create status bar for displaying info."""
        self.status_frame = ctk.CTkFrame(self, height=30)
        self.status_frame.grid(
            row=3, column=0, sticky="ew",
            padx=PADDING_LARGE, pady=(0, PADDING_LARGE)
        )
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

    def _on_type_filter_changed(self, selection):
        """Handle assembly type filter change."""
        self._on_search()

    def _on_key_release(self):
        """Handle key release in search entry (placeholder for live search)."""
        pass

    def _on_header_click(self, column: str):
        """Handle column header click for sorting."""
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True
        self._refresh_tree_display()

    def _on_tree_select(self, event):
        """Handle tree selection change."""
        selection = self.tree.selection()
        if selection:
            fg_id = int(selection[0])
            fg = self._get_finished_good_by_id(fg_id)
            self._on_row_select(fg)
        else:
            self._on_row_select(None)

    def _on_tree_double_click(self, event):
        """Handle double-click on finished good row."""
        selection = self.tree.selection()
        if selection:
            fg_id = int(selection[0])
            fg = self._get_finished_good_by_id(fg_id)
            if fg:
                self._on_row_double_click(fg)

    def _get_finished_good_by_id(self, fg_id: int) -> Optional[FinishedGood]:
        """Find finished good by ID in current data."""
        return next(
            (fg for fg in self._current_finished_goods if fg.id == fg_id),
            None
        )

    def _refresh_tree_display(self):
        """Refresh the tree display with current finished goods and sorting."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        finished_goods = self._current_finished_goods
        if not finished_goods:
            return

        # Sort finished goods by current sort column
        finished_goods = self._sort_finished_goods(finished_goods)

        # Insert into tree
        for fg in finished_goods:
            self._insert_finished_good_row(fg)

    def _sort_finished_goods(
        self, finished_goods: List[FinishedGood]
    ) -> List[FinishedGood]:
        """Sort finished goods by current sort column."""
        def get_sort_key(fg):
            if self.sort_column == "name":
                return (fg.display_name or "").lower()
            elif self.sort_column == "assembly_type":
                return (fg.assembly_type.value if fg.assembly_type else "").lower()
            elif self.sort_column == "components":
                return len(fg.components) if fg.components else 0
            elif self.sort_column == "notes":
                return (fg.notes or "").lower()
            return ""

        return sorted(finished_goods, key=get_sort_key, reverse=not self.sort_ascending)

    def _insert_finished_good_row(self, fg: FinishedGood):
        """Insert a finished good row into the tree."""
        name = fg.display_name or ""
        assembly_type = self._get_assembly_type_display(fg.assembly_type)
        component_count = str(len(fg.components)) if fg.components else "0"
        notes = (fg.notes or "")[:50]  # Truncate notes for display
        if fg.notes and len(fg.notes) > 50:
            notes += "..."

        values = (name, assembly_type, component_count, notes)
        self.tree.insert("", "end", iid=str(fg.id), values=values)

    def _get_assembly_type_display(self, assembly_type: Optional[AssemblyType]) -> str:
        """Convert AssemblyType enum to display string."""
        if not assembly_type:
            return "Custom Order"
        type_map = {
            AssemblyType.CUSTOM_ORDER: "Custom Order",
            AssemblyType.GIFT_BOX: "Gift Box",
            AssemblyType.VARIETY_PACK: "Variety Pack",
            AssemblyType.HOLIDAY_SET: "Holiday Set",
            AssemblyType.BULK_PACK: "Bulk Pack",
        }
        return type_map.get(assembly_type, "Custom Order")

    def _get_assembly_type_from_display(self, display: str) -> Optional[AssemblyType]:
        """Convert display string to AssemblyType enum."""
        if display == "All Types":
            return None
        display_map = {
            "Custom Order": AssemblyType.CUSTOM_ORDER,
            "Gift Box": AssemblyType.GIFT_BOX,
            "Variety Pack": AssemblyType.VARIETY_PACK,
            "Holiday Set": AssemblyType.HOLIDAY_SET,
            "Bulk Pack": AssemblyType.BULK_PACK,
        }
        return display_map.get(display)

    def _on_search(self):
        """Handle search and filter."""
        search_text = self.search_entry.get().strip()
        type_filter = self.type_var.get()

        # Determine assembly type filter
        assembly_type = self._get_assembly_type_from_display(type_filter)

        try:
            finished_goods = finished_good_service.get_all_finished_goods(
                name_search=search_text if search_text else None,
                assembly_type=assembly_type,
            )

            # Store finished goods for selection lookup and refresh display
            self._current_finished_goods = finished_goods
            self._refresh_tree_display()
            self._update_status(f"Found {len(finished_goods)} finished good(s)")
        except Exception as e:
            show_error(
                "Search Error",
                f"Failed to search finished goods: {str(e)}",
                parent=self
            )
            self._update_status("Search failed", error=True)

    def _on_row_select(self, finished_good: Optional[FinishedGood]):
        """Handle row selection."""
        self.selected_finished_good = finished_good

        # Enable/disable action buttons
        has_selection = finished_good is not None
        self.edit_button.configure(state="normal" if has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")
        self.details_button.configure(state="normal" if has_selection else "disabled")

        if finished_good:
            self._update_status(f"Selected: {finished_good.display_name}")
        else:
            self._update_status("Ready")

    def _on_row_double_click(self, finished_good: FinishedGood):
        """Handle row double-click (opens edit dialog)."""
        self.selected_finished_good = finished_good
        self._edit_finished_good()

    def _add_finished_good(self):
        """Show dialog to add a new finished good."""
        dialog = FinishedGoodFormDialog(self, title="Add New Finished Good")
        self.wait_window(dialog)
        result = dialog.result

        if result:
            try:
                # Extract components from result
                components = result.pop("components", [])

                # Map assembly_type string to enum
                assembly_type_str = result.pop("assembly_type", "custom_order")
                assembly_type = self._get_assembly_type_from_value(assembly_type_str)

                # Create finished good
                new_fg = finished_good_service.create_finished_good(
                    display_name=result.get("display_name", ""),
                    assembly_type=assembly_type,
                    packaging_instructions=result.get("packaging_instructions"),
                    notes=result.get("notes"),
                    components=components,
                )

                show_success(
                    "Success",
                    f"Finished good '{new_fg.display_name}' added successfully",
                    parent=self,
                )
                self.refresh()
                self._update_status(f"Added: {new_fg.display_name}", success=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to add finished good: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to add finished good", error=True)

    def _get_assembly_type_from_value(self, value: str) -> AssemblyType:
        """Convert assembly type value string to AssemblyType enum."""
        value_map = {
            "custom_order": AssemblyType.CUSTOM_ORDER,
            "gift_box": AssemblyType.GIFT_BOX,
            "variety_pack": AssemblyType.VARIETY_PACK,
            "holiday_set": AssemblyType.HOLIDAY_SET,
            "bulk_pack": AssemblyType.BULK_PACK,
        }
        return value_map.get(value.lower(), AssemblyType.CUSTOM_ORDER)

    def _edit_finished_good(self):
        """Show dialog to edit the selected finished good."""
        if not self.selected_finished_good:
            return

        try:
            # Reload finished good to avoid lazy loading issues
            fg = finished_good_service.get_finished_good(self.selected_finished_good.id)

            dialog = FinishedGoodFormDialog(
                self,
                finished_good=fg,
                title=f"Edit: {fg.display_name}",
            )
            self.wait_window(dialog)
            result = dialog.result
        except Exception as e:
            show_error(
                "Error",
                f"Failed to load finished good for editing: {str(e)}",
                parent=self,
            )
            return

        if result:
            try:
                # Extract components from result
                components = result.pop("components", [])

                # Map assembly_type string to enum
                assembly_type_str = result.pop("assembly_type", "custom_order")
                assembly_type = self._get_assembly_type_from_value(assembly_type_str)

                # Update finished good
                updated_fg = finished_good_service.update_finished_good(
                    self.selected_finished_good.id,
                    display_name=result.get("display_name"),
                    assembly_type=assembly_type,
                    packaging_instructions=result.get("packaging_instructions"),
                    notes=result.get("notes"),
                    components=components,
                )

                show_success(
                    "Success",
                    f"Finished good '{updated_fg.display_name}' updated successfully",
                    parent=self,
                )
                self.refresh()
                self._update_status(f"Updated: {updated_fg.display_name}", success=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to update finished good: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to update finished good", error=True)

    def _delete_finished_good(self):
        """Delete the selected finished good after confirmation."""
        if not self.selected_finished_good:
            return

        # Confirm deletion
        confirmed = show_confirmation(
            "Confirm Deletion",
            f"Are you sure you want to delete '{self.selected_finished_good.display_name}'?\n\n"
            "This will remove the finished good and all its component associations.\n"
            "This action cannot be undone.",
            parent=self,
        )

        if confirmed:
            try:
                finished_good_service.delete_finished_good(self.selected_finished_good.id)
                show_success(
                    "Success",
                    f"Finished good '{self.selected_finished_good.display_name}' deleted successfully",
                    parent=self,
                )
                self.selected_finished_good = None
                self.refresh()
                self._update_status("Finished good deleted", success=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to delete finished good: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to delete finished good", error=True)

    def _view_details(self):
        """Show detailed information about the selected finished good."""
        if not self.selected_finished_good:
            return

        try:
            # Get finished good with relationships
            fg = finished_good_service.get_finished_good(self.selected_finished_good.id)

            if not fg:
                show_error(
                    "Error",
                    "Finished good not found.",
                    parent=self,
                )
                return

            # Build details message
            details = []
            details.append(f"Name: {fg.display_name}")
            details.append(f"Assembly Type: {self._get_assembly_type_display(fg.assembly_type)}")

            if fg.packaging_instructions:
                details.append(f"\nPackaging Instructions:\n{fg.packaging_instructions}")

            # Show components
            if fg.components:
                details.append(f"\nComponents ({len(fg.components)}):")
                for comp in fg.components:
                    if comp.finished_unit_id:
                        details.append(f"  • {comp.component_quantity}x Finished Unit #{comp.finished_unit_id}")
                    elif comp.material_unit_id:
                        details.append(f"  • {comp.component_quantity}x Material Unit #{comp.material_unit_id}")
                    elif comp.finished_good_id:
                        details.append(f"  • {comp.component_quantity}x Finished Good #{comp.finished_good_id}")
                    if comp.component_notes:
                        details.append(f"      Note: {comp.component_notes}")
            else:
                details.append("\nComponents: None defined")

            if fg.notes:
                details.append(f"\nNotes:\n{fg.notes}")

            show_info(
                f"Finished Good Details: {fg.display_name}",
                "\n".join(details),
                parent=self,
            )

        except Exception as e:
            show_error(
                "Error",
                f"Failed to load finished good details: {str(e)}",
                parent=self,
            )

    def refresh(self):
        """Refresh the finished good list."""
        try:
            finished_goods = finished_good_service.get_all_finished_goods()

            # Apply assembly type filter if set
            type_filter = self.type_var.get()
            assembly_type = self._get_assembly_type_from_display(type_filter)
            if assembly_type:
                finished_goods = [
                    fg for fg in finished_goods
                    if fg.assembly_type == assembly_type
                ]

            # Store finished goods for selection lookup and refresh display
            self._current_finished_goods = finished_goods
            self._refresh_tree_display()

            if finished_goods:
                self._update_status(f"Loaded {len(finished_goods)} finished good(s)")
            else:
                self._update_status("No finished goods found. Click '+ Add Finished Good' to create one.")
        except Exception as e:
            show_error(
                "Error",
                f"Failed to load finished goods: {str(e)}",
                parent=self,
            )
            self._update_status("Failed to load finished goods", error=True)

    def _update_status(self, message: str, success: bool = False, error: bool = False):
        """Update status bar message."""
        self.status_label.configure(text=message)

        # Set color based on message type
        if success:
            self.status_label.configure(text_color=COLOR_SUCCESS)
        elif error:
            self.status_label.configure(text_color=COLOR_ERROR)
        else:
            # Default theme colors
            self.status_label.configure(text_color=("gray10", "gray90"))
