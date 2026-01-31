"""
FinishedGood form dialog for creating and editing assembled packages.

This dialog provides a modal form for managing FinishedGood records, which
represent assembled packages containing multiple FinishedUnits and/or other
FinishedGoods (e.g., gift boxes, variety packs, seasonal collections).

Feature 088: Finished Goods Catalog UI - WP04
"""

import customtkinter as ctk
from typing import Optional, Dict, List

from src.models.finished_good import FinishedGood
from src.models.assembly_type import AssemblyType


class FinishedGoodFormDialog(ctk.CTkToplevel):
    """
    Modal dialog for creating/editing FinishedGoods.

    Provides form fields for:
    - Name (required)
    - Assembly Type (required, defaults to Custom Order)
    - Packaging Instructions (optional)
    - Notes (optional)

    The dialog returns a result dictionary on save, or None on cancel.
    Component management is handled in WP05/WP06.
    """

    # Mapping from display names to enum values
    _type_to_enum: Dict[str, AssemblyType] = {
        "Custom Order": AssemblyType.CUSTOM_ORDER,
        "Gift Box": AssemblyType.GIFT_BOX,
        "Variety Pack": AssemblyType.VARIETY_PACK,
        "Holiday Set": AssemblyType.HOLIDAY_SET,
        "Bulk Pack": AssemblyType.BULK_PACK,
    }

    # Reverse mapping from enum values to display names
    _enum_to_type: Dict[AssemblyType, str] = {
        AssemblyType.CUSTOM_ORDER: "Custom Order",
        AssemblyType.GIFT_BOX: "Gift Box",
        AssemblyType.VARIETY_PACK: "Variety Pack",
        AssemblyType.HOLIDAY_SET: "Holiday Set",
        AssemblyType.BULK_PACK: "Bulk Pack",
    }

    def __init__(
        self,
        parent,
        finished_good: Optional[FinishedGood] = None,
        title: str = "Create Finished Good",
    ):
        """
        Initialize the FinishedGood form dialog.

        Args:
            parent: Parent window
            finished_good: Existing FinishedGood to edit (None for new)
            title: Dialog title (overridden in edit mode)
        """
        super().__init__(parent)

        self.finished_good = finished_good
        self.result: Optional[Dict] = None

        # Window configuration
        if finished_good:
            self.title(f"Edit: {finished_good.display_name}")
        else:
            self.title(title)
        self.geometry("600x700")
        self.resizable(True, True)
        self.minsize(500, 500)

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Build UI
        self._create_widgets()
        self._populate_form()

        # Center on parent
        self._center_on_parent(parent)

    def _center_on_parent(self, parent):
        """Center the dialog on its parent window."""
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create all form widgets."""
        # Main container
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Scrollable form area
        self.form_scroll = ctk.CTkScrollableFrame(
            self.main_frame,
            label_text="",
            label_anchor="nw",
        )
        self.form_scroll.pack(fill="both", expand=True, pady=(0, 10))

        # Configure scroll frame grid for consistent widget sizing
        self.form_scroll.grid_columnconfigure(0, weight=0)  # Labels
        self.form_scroll.grid_columnconfigure(1, weight=1)  # Inputs

        # Create form sections
        self._create_basic_info_section()
        self._create_packaging_section()
        self._create_notes_section()

        # Button frame at bottom (not scrollable)
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(fill="x", pady=(10, 0))

        # Create buttons
        self._create_buttons()

    def _create_basic_info_section(self):
        """Create the Basic Information section with Name and Assembly Type."""
        # Section header
        header = ctk.CTkLabel(
            self.form_scroll,
            text="Basic Information",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(10, 5))

        # Name label
        name_label = ctk.CTkLabel(self.form_scroll, text="Name *")
        name_label.grid(row=1, column=0, sticky="w", pady=5, padx=(0, 10))

        # Name entry
        self.name_entry = ctk.CTkEntry(
            self.form_scroll,
            placeholder_text="Enter name (e.g., Holiday Gift Box)",
        )
        self.name_entry.grid(row=1, column=1, sticky="ew", pady=5)

        # Assembly Type label
        type_label = ctk.CTkLabel(self.form_scroll, text="Assembly Type *")
        type_label.grid(row=2, column=0, sticky="w", pady=5, padx=(0, 10))

        # Assembly Type dropdown
        type_values = list(self._type_to_enum.keys())
        self.type_dropdown = ctk.CTkComboBox(
            self.form_scroll,
            values=type_values,
            state="readonly",
        )
        self.type_dropdown.set("Custom Order")  # Default
        self.type_dropdown.grid(row=2, column=1, sticky="ew", pady=5)

    def _create_packaging_section(self):
        """Create the Packaging Instructions section."""
        # Section header
        header = ctk.CTkLabel(
            self.form_scroll,
            text="Packaging Instructions",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        header.grid(row=3, column=0, columnspan=2, sticky="w", pady=(15, 5))

        # Textarea
        self.packaging_text = ctk.CTkTextbox(
            self.form_scroll,
            height=100,
            wrap="word",
        )
        self.packaging_text.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

    def _create_notes_section(self):
        """Create the Notes section."""
        # Section header
        header = ctk.CTkLabel(
            self.form_scroll,
            text="Notes",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        header.grid(row=5, column=0, columnspan=2, sticky="w", pady=(15, 5))

        # Textarea
        self.notes_text = ctk.CTkTextbox(
            self.form_scroll,
            height=80,
            wrap="word",
        )
        self.notes_text.grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)

    def _create_buttons(self):
        """Create Save and Cancel buttons."""
        # Cancel button
        self.cancel_btn = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self._on_cancel,
            fg_color="gray",
        )
        self.cancel_btn.pack(side="right", padx=5)

        # Save button
        self.save_btn = ctk.CTkButton(
            self.button_frame,
            text="Save",
            command=self._on_save,
        )
        self.save_btn.pack(side="right", padx=5)

    def _populate_form(self):
        """Populate form fields from existing FinishedGood."""
        if not self.finished_good:
            return

        # Name
        self.name_entry.insert(0, self.finished_good.display_name)

        # Assembly Type
        type_display = self._enum_to_type.get(
            self.finished_good.assembly_type,
            "Custom Order",
        )
        self.type_dropdown.set(type_display)

        # Packaging Instructions
        if self.finished_good.packaging_instructions:
            self.packaging_text.insert("1.0", self.finished_good.packaging_instructions)

        # Notes
        if self.finished_good.notes:
            self.notes_text.insert("1.0", self.finished_good.notes)

    def _show_error(self, message: str):
        """Show error indication on the name field."""
        # Highlight the name field with red border
        self.name_entry.configure(border_color="red")

    def _clear_error(self):
        """Clear error indication on the name field."""
        # Reset to default border color
        self.name_entry.configure(border_color=("gray50", "gray30"))

    def _get_assembly_type(self) -> str:
        """Get the selected assembly type as enum value string."""
        selected = self.type_dropdown.get()
        enum_value = self._type_to_enum.get(selected, AssemblyType.CUSTOM_ORDER)
        return enum_value.value

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()

    def _on_save(self):
        """Handle save button click with validation."""
        # Clear any previous error
        self._clear_error()

        # Validate required fields
        name = self.name_entry.get().strip()
        if not name:
            self._show_error("Name is required")
            return

        # Build result
        self.result = {
            "display_name": name,
            "assembly_type": self._get_assembly_type(),
            "packaging_instructions": self.packaging_text.get("1.0", "end-1c").strip(),
            "notes": self.notes_text.get("1.0", "end-1c").strip(),
            "components": [],  # WP05/WP06 will populate this
        }
        self.destroy()

    def get_result(self) -> Optional[Dict]:
        """
        Wait for dialog to close and return result.

        Returns:
            Dictionary with form data if saved, None if cancelled
        """
        self.wait_window()
        return self.result
