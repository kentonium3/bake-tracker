"""
Variant creation dialog for creating recipe variants (Feature 063).

Provides inline FinishedUnit display_name input integrated with
variant creation workflow.
"""

import customtkinter as ctk
from typing import Optional, List, Dict, Callable

from src.services import recipe_service
from src.services.exceptions import ValidationError
from src.services.database import session_scope
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


class VariantCreationDialog(ctk.CTkToplevel):
    """
    Dialog for creating a variant of an existing recipe.

    Shows base recipe's FinishedUnits and allows user to enter
    display names for variant FinishedUnits.
    """

    def __init__(
        self,
        parent,
        base_recipe_id: int,
        base_recipe_name: str,
        base_finished_units: List[Dict],
        on_save_callback: Optional[Callable[[Dict], None]] = None,
    ):
        """
        Initialize the variant creation dialog.

        Args:
            parent: Parent widget
            base_recipe_id: ID of the base recipe
            base_recipe_name: Name of the base recipe
            base_finished_units: List of base recipe's FinishedUnits
            on_save_callback: Callback when variant is created successfully
        """
        super().__init__(parent)

        self.base_recipe_id = base_recipe_id
        self.base_recipe_name = base_recipe_name
        self.base_finished_units = base_finished_units
        self.on_save_callback = on_save_callback

        # Track FU entry widgets
        self.fu_entries: Dict[str, Dict] = {}
        self.error_label: Optional[ctk.CTkLabel] = None

        # Configure window
        self.title(f"Create Variant of {base_recipe_name}")
        self.geometry("550x450")
        self.resizable(True, True)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # FU section expands

        # Create UI components
        self._create_variant_name_section()
        self._create_finished_units_section()
        self._create_buttons()

        # Center dialog
        self.update_idletasks()
        self._center_on_parent(parent)

    def _center_on_parent(self, parent):
        """Center dialog on parent window."""
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        x = max(0, parent_x + (parent_width - dialog_width) // 2)
        y = max(0, parent_y + (parent_height - dialog_height) // 2)
        self.geometry(f"+{x}+{y}")

    def _create_variant_name_section(self):
        """Create the variant name input section."""
        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        name_frame.grid_columnconfigure(1, weight=1)

        # Label
        name_label = ctk.CTkLabel(name_frame, text="Variant Name:", anchor="e", width=120)
        name_label.grid(row=0, column=0, sticky="e", padx=(0, PADDING_MEDIUM))

        # Entry with variable for change tracking
        self.variant_name_var = ctk.StringVar()
        self.variant_name_var.trace_add("write", self._on_variant_name_changed)

        self.variant_name_entry = ctk.CTkEntry(
            name_frame,
            textvariable=self.variant_name_var,
            placeholder_text="e.g., Raspberry, Chocolate Chip",
        )
        self.variant_name_entry.grid(row=0, column=1, sticky="ew")

        # Help text
        help_text = ctk.CTkLabel(
            name_frame,
            text="This name distinguishes the variant (e.g., 'Raspberry' for 'Thumbprint Cookies - Raspberry')",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        )
        help_text.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))

    def _create_finished_units_section(self):
        """Create the FinishedUnit display name input section."""
        # Container frame
        fu_container = ctk.CTkFrame(self)
        fu_container.grid(row=2, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)
        fu_container.grid_columnconfigure(0, weight=1)
        fu_container.grid_rowconfigure(1, weight=1)

        if self.base_finished_units:
            # Section header
            header_label = ctk.CTkLabel(
                fu_container,
                text="Yield Type Names:",
                font=ctk.CTkFont(weight="bold"),
            )
            header_label.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5))

            # Scrollable frame for FU entries
            self.fu_frame = ctk.CTkScrollableFrame(fu_container, height=200)
            self.fu_frame.grid(row=1, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)
            self.fu_frame.grid_columnconfigure(1, weight=1)

            # Create row for each base FinishedUnit
            for idx, fu in enumerate(self.base_finished_units):
                self._create_fu_row(idx, fu)

        else:
            # No FinishedUnits - show informational message
            no_fu_label = ctk.CTkLabel(
                fu_container,
                text="Base recipe has no yield types defined.\n"
                     "Variant will also have no yield types.\n\n"
                     "You can add yield types later by editing the variant.",
                text_color="gray",
                justify="center",
            )
            no_fu_label.grid(row=0, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_LARGE)

    def _create_fu_row(self, idx: int, base_fu: Dict):
        """
        Create input row for one FinishedUnit.

        Args:
            idx: Row index
            base_fu: Base FinishedUnit dict with slug, display_name, etc.
        """
        # Base name label
        base_label = ctk.CTkLabel(
            self.fu_frame,
            text=f"Base: {base_fu['display_name']}",
            anchor="w",
            width=180,
        )
        base_label.grid(row=idx, column=0, sticky="w", padx=(0, PADDING_MEDIUM), pady=3)

        # Entry for variant display_name
        entry = ctk.CTkEntry(
            self.fu_frame,
            placeholder_text="Enter variant name...",
        )
        entry.grid(row=idx, column=1, sticky="ew", pady=3)

        # Pre-populate with suggestion based on variant name
        variant_name = self.variant_name_var.get()
        if variant_name:
            suggested_name = f"{variant_name} {base_fu['display_name']}"
        else:
            suggested_name = base_fu['display_name']
        entry.insert(0, suggested_name)

        # Store for later retrieval
        self.fu_entries[base_fu['slug']] = {
            'entry': entry,
            'base_display_name': base_fu['display_name'],
        }

    def _on_variant_name_changed(self, *args):
        """Update FU name suggestions when variant name changes."""
        variant_name = self.variant_name_var.get().strip()

        for slug, data in self.fu_entries.items():
            entry = data['entry']
            base_name = data['base_display_name']
            current = entry.get()

            # Only update if user hasn't customized the name
            # (i.e., it still ends with the base name or is empty)
            if not current or current == base_name or current.endswith(base_name):
                entry.delete(0, 'end')
                if variant_name:
                    entry.insert(0, f"{variant_name} {base_name}")
                else:
                    entry.insert(0, base_name)

    def _create_buttons(self):
        """Create save and cancel buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=3, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            fg_color="gray",
            hover_color="darkgray",
        )
        cancel_btn.grid(row=0, column=0, sticky="e", padx=PADDING_MEDIUM)

        save_btn = ctk.CTkButton(
            button_frame,
            text="Create Variant",
            command=self._on_save,
        )
        save_btn.grid(row=0, column=1, sticky="w", padx=PADDING_MEDIUM)

    def _validate_inputs(self) -> List[str]:
        """
        Validate all inputs.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Validate variant name
        variant_name = self.variant_name_var.get().strip()
        if not variant_name:
            errors.append("Variant name is required")

        # Validate FU display_names
        for slug, data in self.fu_entries.items():
            new_name = data['entry'].get().strip()
            base_name = data['base_display_name']

            if not new_name:
                errors.append(f"Display name for '{base_name}' cannot be empty")
            elif new_name == base_name:
                errors.append(f"'{new_name}' must differ from base name '{base_name}'")

        return errors

    def _show_errors(self, errors: List[str]):
        """Display validation errors in the dialog."""
        # Remove existing error label if present
        if self.error_label:
            self.error_label.destroy()
            self.error_label = None

        if errors:
            error_text = "\n".join(f"- {e}" for e in errors)
            self.error_label = ctk.CTkLabel(
                self,
                text=error_text,
                text_color="red",
                justify="left",
                anchor="w",
            )
            self.error_label.grid(row=1, column=0, sticky="w", padx=PADDING_LARGE, pady=(0, 5))

    def _on_save(self):
        """Handle save button click."""
        # Validate inputs
        errors = self._validate_inputs()
        if errors:
            self._show_errors(errors)
            return

        # Clear any previous errors
        self._show_errors([])

        # Collect data
        variant_name = self.variant_name_var.get().strip()

        # Collect finished_unit_names if any
        finished_unit_names = None
        if self.fu_entries:
            finished_unit_names = [
                {
                    "base_slug": slug,
                    "display_name": data['entry'].get().strip(),
                }
                for slug, data in self.fu_entries.items()
            ]

        # Call service to create variant
        try:
            with session_scope() as session:
                result = recipe_service.create_recipe_variant(
                    base_recipe_id=self.base_recipe_id,
                    variant_name=variant_name,
                    finished_unit_names=finished_unit_names,
                    session=session,
                )

            # Success - close dialog and notify parent
            if self.on_save_callback:
                self.on_save_callback(result)
            self.destroy()

        except ValidationError as e:
            # Extract error messages
            if hasattr(e, 'errors') and e.errors:
                self._show_errors(e.errors)
            else:
                self._show_errors([str(e)])

        except Exception as e:
            self._show_errors([f"Error creating variant: {str(e)}"])
