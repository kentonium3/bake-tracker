"""
Recipe History View - Display production snapshots for a recipe.

Shows chronological list of snapshots with ability to view details
and restore as new recipe.

Feature 037: Recipe Template & Snapshot System
"""

import customtkinter as ctk
from datetime import datetime

from src.services import recipe_snapshot_service


class RecipeHistoryView(ctk.CTkToplevel):
    """Dialog showing snapshot history for a recipe."""

    def __init__(self, parent, recipe_id: int, recipe_name: str):
        """
        Initialize the recipe history view dialog.

        Args:
            parent: Parent window
            recipe_id: ID of the recipe to show history for
            recipe_name: Name of the recipe (for display)
        """
        super().__init__(parent)

        self.recipe_id = recipe_id
        self.recipe_name = recipe_name
        self.selected_snapshot = None

        self.title(f"History: {recipe_name}")
        self.geometry("700x500")
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._load_snapshots()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create dialog widgets."""
        # Header
        header = ctk.CTkLabel(
            self,
            text=f"Production History: {self.recipe_name}",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.pack(pady=10)

        # Main content frame
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=20, pady=10)

        # Snapshot list (left side)
        list_frame = ctk.CTkFrame(content)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        list_label = ctk.CTkLabel(list_frame, text="Snapshots (newest first)")
        list_label.pack(anchor="w", pady=5)

        self.snapshot_listbox = ctk.CTkScrollableFrame(list_frame, height=300)
        self.snapshot_listbox.pack(fill="both", expand=True)

        # Details panel (right side)
        details_frame = ctk.CTkFrame(content)
        details_frame.pack(side="right", fill="both", expand=True)

        details_label = ctk.CTkLabel(details_frame, text="Snapshot Details")
        details_label.pack(anchor="w", pady=5)

        self.details_text = ctk.CTkTextbox(details_frame, height=300, state="disabled")
        self.details_text.pack(fill="both", expand=True)

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=10)

        self.restore_btn = ctk.CTkButton(
            button_frame, text="Restore as New Recipe", command=self._on_restore, state="disabled"
        )
        self.restore_btn.pack(side="left")

        close_btn = ctk.CTkButton(button_frame, text="Close", command=self.destroy)
        close_btn.pack(side="right")

    def _load_snapshots(self):
        """Load and display snapshots."""
        snapshots = recipe_snapshot_service.get_recipe_snapshots(self.recipe_id)

        if not snapshots:
            no_data = ctk.CTkLabel(
                self.snapshot_listbox, text="No production history yet.", text_color="gray"
            )
            no_data.pack(pady=20)
            return

        for snapshot in snapshots:
            self._create_snapshot_row(snapshot)

    def _create_snapshot_row(self, snapshot: dict):
        """
        Create a row for a snapshot.

        Args:
            snapshot: Snapshot dictionary from service
        """
        row = ctk.CTkFrame(self.snapshot_listbox)
        row.pack(fill="x", pady=2)

        # Format date
        date_str = snapshot.get("snapshot_date", "")
        try:
            dt = datetime.fromisoformat(date_str)
            date_display = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            date_display = date_str

        # Build label text
        label_text = f"{date_display}"
        scale_factor = snapshot.get("scale_factor", 1.0)
        if scale_factor != 1.0:
            label_text += f" (Scale: {scale_factor}x)"
        if snapshot.get("is_backfilled"):
            label_text += " (approximated)"

        label = ctk.CTkLabel(row, text=label_text, anchor="w")
        label.pack(side="left", fill="x", expand=True, padx=5)

        # View button
        view_btn = ctk.CTkButton(
            row, text="View", width=60, command=lambda s=snapshot: self._on_view_snapshot(s)
        )
        view_btn.pack(side="right", padx=2)

    def _on_view_snapshot(self, snapshot: dict):
        """
        Display snapshot details.

        Args:
            snapshot: Snapshot dictionary to display
        """
        self.selected_snapshot = snapshot
        self.restore_btn.configure(state="normal")

        # Build details text
        recipe_data = snapshot.get("recipe_data", {})
        ingredients = snapshot.get("ingredients_data", [])

        details = []
        details.append(f"Snapshot Date: {snapshot.get('snapshot_date', 'N/A')}")
        details.append(f"Scale Factor: {snapshot.get('scale_factor', 1.0)}x")
        if snapshot.get("is_backfilled"):
            details.append("** Data approximated from current recipe **")
        details.append("")
        details.append(f"Recipe: {recipe_data.get('name', 'N/A')}")
        details.append(f"Category: {recipe_data.get('category', 'N/A')}")
        # F056: yield_quantity/yield_unit are deprecated but may exist in historical snapshots
        yield_qty = recipe_data.get("yield_quantity")
        yield_unit = recipe_data.get("yield_unit", "")
        if yield_qty:
            details.append(f"Yield: {yield_qty} {yield_unit}")
        else:
            details.append("Yield: (see finished units)")
        details.append("")
        details.append("Ingredients (as captured):")

        for ing in ingredients:
            quantity = ing.get("quantity", 0)
            unit = ing.get("unit", "")
            name = ing.get("ingredient_name", "Unknown")
            details.append(f"  - {quantity} {unit} {name}")

        # Update display
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("1.0", "\n".join(details))
        self.details_text.configure(state="disabled")

    def _on_restore(self):
        """Restore selected snapshot as new recipe."""
        if not self.selected_snapshot:
            return

        # Confirm with user
        from src.ui.widgets.dialogs import show_confirmation

        if not show_confirmation(
            "Restore Snapshot",
            "Create a new recipe from this snapshot?\n\n"
            "This will create a copy, not modify the original.",
            parent=self,
        ):
            return

        try:
            result = recipe_snapshot_service.create_recipe_from_snapshot(
                self.selected_snapshot["id"]
            )

            from src.ui.widgets.dialogs import show_info

            show_info("Recipe Created", f"New recipe created: {result['name']}", parent=self)
            self.destroy()

        except Exception as e:
            from src.ui.widgets.dialogs import show_error

            show_error("Restore Failed", f"Failed to restore: {e}", parent=self)
