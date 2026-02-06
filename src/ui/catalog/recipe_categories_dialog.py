"""
Recipe Categories Admin Dialog for Feature 096.

Provides a dialog for managing recipe categories with CRUD operations
and sort order management. Uses a flat list (no hierarchy).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable

import customtkinter as ctk


class RecipeCategoriesDialog(ctk.CTkToplevel):
    """
    Admin dialog for managing recipe categories.

    Feature 096: Flat list dialog with add, edit, delete, and reorder.

    Args:
        parent: Parent window
        on_close: Optional callback when window closes
    """

    def __init__(self, parent, on_close: Optional[Callable] = None):
        super().__init__(parent)

        self.on_close = on_close

        # Window setup
        self.title("Recipe Categories")
        self.geometry("600x500")
        self.minsize(500, 400)

        # Build UI
        self._create_layout()

        # Load data
        self._refresh_list()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """Handle window close."""
        if self.on_close:
            self.on_close()
        self.destroy()

    def _create_layout(self):
        """Create the main layout with list and action buttons."""
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left panel - Category list
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # Treeview for categories
        columns = ("name", "sort_order", "description")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("name", text="Name")
        self.tree.heading("sort_order", text="Order")
        self.tree.heading("description", text="Description")

        self.tree.column("name", width=150, minwidth=100)
        self.tree.column("sort_order", width=60, minwidth=50)
        self.tree.column("description", width=200, minwidth=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Double-click to edit
        self.tree.bind("<Double-1>", lambda e: self._show_edit_dialog())

        # Right panel - Action buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(side="right", fill="y", padx=(5, 0))

        ctk.CTkButton(
            button_frame, text="Add", width=100, command=self._show_add_dialog
        ).pack(pady=(0, 5))

        ctk.CTkButton(
            button_frame, text="Edit", width=100, command=self._show_edit_dialog
        ).pack(pady=5)

        ctk.CTkButton(
            button_frame, text="Delete", width=100, command=self._delete_selected
        ).pack(pady=5)

        # Separator
        ttk.Separator(button_frame, orient="horizontal").pack(fill="x", pady=10)

        self.move_up_btn = ctk.CTkButton(
            button_frame, text="Move Up", width=100, command=self._move_up
        )
        self.move_up_btn.pack(pady=5)

        self.move_down_btn = ctk.CTkButton(
            button_frame, text="Move Down", width=100, command=self._move_down
        )
        self.move_down_btn.pack(pady=5)

    def _refresh_list(self):
        """Reload categories from the database."""
        from src.services import recipe_category_service

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Load categories
        self._categories = recipe_category_service.list_categories()

        for cat in self._categories:
            self.tree.insert(
                "",
                "end",
                iid=str(cat.id),
                values=(cat.name, cat.sort_order, cat.description or ""),
            )

    def _get_selected_category_id(self) -> Optional[int]:
        """Get the ID of the selected category, or None."""
        selection = self.tree.selection()
        if not selection:
            return None
        return int(selection[0])

    def _show_add_dialog(self):
        """Open dialog to add a new category."""
        dialog = _CategoryFormDialog(self, title="Add Category")
        self.wait_window(dialog)

        if dialog.result:
            from src.services import recipe_category_service
            from src.services.exceptions import ValidationError

            try:
                recipe_category_service.create_category(
                    name=dialog.result["name"],
                    sort_order=dialog.result["sort_order"],
                    description=dialog.result["description"],
                )
                self._refresh_list()
            except ValidationError as e:
                messagebox.showerror(
                    "Error",
                    "; ".join(e.errors),
                    parent=self,
                )

    def _show_edit_dialog(self):
        """Open dialog to edit the selected category."""
        cat_id = self._get_selected_category_id()
        if cat_id is None:
            messagebox.showinfo(
                "Info", "Select a category to edit.", parent=self
            )
            return

        from src.services import recipe_category_service
        from src.services.exceptions import ValidationError

        category = recipe_category_service.get_category_by_id(cat_id)

        dialog = _CategoryFormDialog(
            self,
            title="Edit Category",
            initial_name=category.name,
            initial_sort_order=category.sort_order,
            initial_description=category.description or "",
        )
        self.wait_window(dialog)

        if dialog.result:
            try:
                recipe_category_service.update_category(
                    cat_id,
                    name=dialog.result["name"],
                    sort_order=dialog.result["sort_order"],
                    description=dialog.result["description"],
                )
                self._refresh_list()
            except ValidationError as e:
                messagebox.showerror(
                    "Error",
                    "; ".join(e.errors),
                    parent=self,
                )

    def _delete_selected(self):
        """Delete the selected category with confirmation."""
        cat_id = self._get_selected_category_id()
        if cat_id is None:
            messagebox.showinfo(
                "Info", "Select a category to delete.", parent=self
            )
            return

        from src.services import recipe_category_service
        from src.services.exceptions import ValidationError

        category = recipe_category_service.get_category_by_id(cat_id)

        # Check if in use
        if recipe_category_service.is_category_in_use(cat_id):
            messagebox.showerror(
                "Cannot Delete",
                f"Cannot delete '{category.name}': it is used by one or more recipes.\n\n"
                f"Remove the category from those recipes first.",
                parent=self,
            )
            return

        # Confirm deletion
        if not messagebox.askokcancel(
            "Confirm Delete",
            f"Delete category '{category.name}'?\n\nThis cannot be undone.",
            parent=self,
        ):
            return

        try:
            recipe_category_service.delete_category(cat_id)
            self._refresh_list()
        except ValidationError as e:
            messagebox.showerror("Error", "; ".join(e.errors), parent=self)

    def _move_up(self):
        """Move the selected category up in sort order."""
        cat_id = self._get_selected_category_id()
        if cat_id is None:
            return

        # Find the index in our ordered list
        idx = None
        for i, cat in enumerate(self._categories):
            if cat.id == cat_id:
                idx = i
                break

        if idx is None or idx == 0:
            return  # Already first or not found

        # Swap sort_order with the category above
        from src.services import recipe_category_service

        above = self._categories[idx - 1]
        current = self._categories[idx]

        above_order = above.sort_order
        current_order = current.sort_order

        # If they have the same sort_order, adjust to make the swap meaningful
        if above_order == current_order:
            current_order = above_order + 1

        recipe_category_service.update_category(above.id, sort_order=current_order)
        recipe_category_service.update_category(current.id, sort_order=above_order)

        self._refresh_list()

        # Re-select the moved category
        self.tree.selection_set(str(cat_id))
        self.tree.see(str(cat_id))

    def _move_down(self):
        """Move the selected category down in sort order."""
        cat_id = self._get_selected_category_id()
        if cat_id is None:
            return

        # Find the index in our ordered list
        idx = None
        for i, cat in enumerate(self._categories):
            if cat.id == cat_id:
                idx = i
                break

        if idx is None or idx >= len(self._categories) - 1:
            return  # Already last or not found

        # Swap sort_order with the category below
        from src.services import recipe_category_service

        below = self._categories[idx + 1]
        current = self._categories[idx]

        below_order = below.sort_order
        current_order = current.sort_order

        # If they have the same sort_order, adjust to make the swap meaningful
        if below_order == current_order:
            below_order = current_order + 1

        recipe_category_service.update_category(below.id, sort_order=current_order)
        recipe_category_service.update_category(current.id, sort_order=below_order)

        self._refresh_list()

        # Re-select the moved category
        self.tree.selection_set(str(cat_id))
        self.tree.see(str(cat_id))


class _CategoryFormDialog(ctk.CTkToplevel):
    """Simple form dialog for adding/editing a category."""

    def __init__(
        self,
        parent,
        title: str = "Category",
        initial_name: str = "",
        initial_sort_order: int = 0,
        initial_description: str = "",
    ):
        super().__init__(parent)

        self.result = None
        self.title(title)
        self.geometry("400x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Form fields
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Name
        ctk.CTkLabel(form_frame, text="Name:").pack(anchor="w", pady=(0, 2))
        self.name_entry = ctk.CTkEntry(form_frame, width=350)
        self.name_entry.pack(fill="x", pady=(0, 10))
        self.name_entry.insert(0, initial_name)

        # Sort Order
        ctk.CTkLabel(form_frame, text="Sort Order:").pack(anchor="w", pady=(0, 2))
        self.sort_order_entry = ctk.CTkEntry(form_frame, width=100)
        self.sort_order_entry.pack(anchor="w", pady=(0, 10))
        self.sort_order_entry.insert(0, str(initial_sort_order))

        # Description
        ctk.CTkLabel(form_frame, text="Description:").pack(anchor="w", pady=(0, 2))
        self.description_text = ctk.CTkTextbox(form_frame, height=80, width=350)
        self.description_text.pack(fill="x", pady=(0, 10))
        if initial_description:
            self.description_text.insert("1.0", initial_description)

        # Buttons
        btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(btn_frame, text="Save", command=self._on_save).pack(
            side="right", padx=(5, 0)
        )
        ctk.CTkButton(
            btn_frame, text="Cancel", fg_color="gray", command=self.destroy
        ).pack(side="right")

    def _on_save(self):
        """Validate and save the form data."""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required.", parent=self)
            return

        try:
            sort_order = int(self.sort_order_entry.get().strip())
        except ValueError:
            messagebox.showerror(
                "Error", "Sort order must be a number.", parent=self
            )
            return

        description = self.description_text.get("1.0", "end-1c").strip()

        self.result = {
            "name": name,
            "sort_order": sort_order,
            "description": description if description else None,
        }
        self.destroy()
