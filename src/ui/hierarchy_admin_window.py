"""
Hierarchy Admin Window for Feature 052.

Provides a reusable admin window for managing ingredient or material
hierarchies. Supports tree view, detail panel, and action buttons.
"""

import customtkinter as ctk
from tkinter import ttk
from typing import Literal, Optional, Callable, Dict, Any


class HierarchyAdminWindow(ctk.CTkToplevel):
    """
    Admin window for managing ingredient or material hierarchies.

    Feature 052: Single window class configurable for either entity type.
    Displays tree view, detail panel with usage counts, and action buttons.

    Args:
        parent: Parent window
        entity_type: "ingredient" or "material"
        on_close: Optional callback when window closes
    """

    def __init__(
        self,
        parent,
        entity_type: Literal["ingredient", "material"],
        on_close: Optional[Callable] = None,
    ):
        super().__init__(parent)

        self.entity_type = entity_type
        self.on_close = on_close
        self.selected_item: Optional[Dict[str, Any]] = None
        self._node_data: Dict[str, Dict] = {}

        # Window setup
        title = (
            "Ingredient Hierarchy Admin"
            if entity_type == "ingredient"
            else "Material Hierarchy Admin"
        )
        self.title(title)
        self.geometry("900x600")
        self.minsize(700, 500)

        # Import appropriate service
        if entity_type == "ingredient":
            from src.services import ingredient_hierarchy_service

            self.hierarchy_service = ingredient_hierarchy_service
        else:
            from src.services import material_hierarchy_service

            self.hierarchy_service = material_hierarchy_service

        # Build UI
        self._create_layout()
        self._load_tree()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """Handle window close."""
        if self.on_close:
            self.on_close()
        self.destroy()

    def _create_layout(self):
        """Create the main layout with tree and detail panels."""
        # Main container
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left panel - Tree view
        self.tree_frame = ctk.CTkFrame(self.main_frame)
        self.tree_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # Tree header
        tree_label = ctk.CTkLabel(
            self.tree_frame,
            text=f"{self.entity_type.title()} Hierarchy",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        tree_label.pack(pady=(5, 10))

        # Tree controls (expand/collapse)
        self._create_tree_controls()

        # Treeview with scrollbar
        tree_container = ctk.CTkFrame(self.tree_frame)
        tree_container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_container, show="tree", selectmode="browse")
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind selection
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Right panel - Detail view
        self._create_detail_panel()

    def _create_tree_controls(self):
        """Add expand/collapse all buttons."""
        control_frame = ctk.CTkFrame(self.tree_frame)
        control_frame.pack(fill="x", pady=(0, 5))

        expand_btn = ctk.CTkButton(
            control_frame, text="Expand All", width=90, command=self._expand_all
        )
        expand_btn.pack(side="left", padx=2)

        collapse_btn = ctk.CTkButton(
            control_frame, text="Collapse All", width=90, command=self._collapse_all
        )
        collapse_btn.pack(side="left", padx=2)

        refresh_btn = ctk.CTkButton(
            control_frame, text="Refresh", width=70, command=self._load_tree
        )
        refresh_btn.pack(side="right", padx=2)

    def _create_detail_panel(self):
        """Create the detail panel on the right side."""
        self.detail_frame = ctk.CTkFrame(self.main_frame, width=300)
        self.detail_frame.pack(side="right", fill="y", padx=(5, 0))
        self.detail_frame.pack_propagate(False)

        # Header
        detail_label = ctk.CTkLabel(
            self.detail_frame,
            text="Item Details",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        detail_label.pack(pady=(5, 10))

        # Name display
        name_frame = ctk.CTkFrame(self.detail_frame)
        name_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(name_frame, text="Name:").pack(anchor="w")
        self.name_label = ctk.CTkLabel(name_frame, text="-", wraplength=250)
        self.name_label.pack(anchor="w")

        # Level/Type display
        level_frame = ctk.CTkFrame(self.detail_frame)
        level_frame.pack(fill="x", padx=10, pady=5)

        level_label_text = "Level:" if self.entity_type == "ingredient" else "Type:"
        ctk.CTkLabel(level_frame, text=level_label_text).pack(anchor="w")
        self.level_label = ctk.CTkLabel(level_frame, text="-")
        self.level_label.pack(anchor="w")

        # Path display
        path_frame = ctk.CTkFrame(self.detail_frame)
        path_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(path_frame, text="Path:").pack(anchor="w")
        self.path_label = ctk.CTkLabel(path_frame, text="-", wraplength=250)
        self.path_label.pack(anchor="w")

        # Usage counts frame
        self.usage_frame = ctk.CTkFrame(self.detail_frame)
        self.usage_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.usage_frame, text="Usage:").pack(anchor="w")
        self.usage_label = ctk.CTkLabel(self.usage_frame, text="-")
        self.usage_label.pack(anchor="w")

        # Action buttons frame
        self.actions_frame = ctk.CTkFrame(self.detail_frame)
        self.actions_frame.pack(fill="x", padx=10, pady=20)

        # Create action buttons
        self._create_action_buttons()

    def _create_action_buttons(self):
        """Create action buttons in detail panel."""
        # Clear existing buttons
        for widget in self.actions_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.actions_frame, text="Actions", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", pady=(0, 5))

        # Add button
        self.add_btn = ctk.CTkButton(
            self.actions_frame,
            text="Add New...",
            command=self._on_add_click,
            state="normal",
        )
        self.add_btn.pack(fill="x", pady=2)

        # Rename button
        self.rename_btn = ctk.CTkButton(
            self.actions_frame,
            text="Rename...",
            command=self._on_rename_click,
            state="disabled",  # Enabled in WP06
        )
        self.rename_btn.pack(fill="x", pady=2)

        # Reparent button
        self.reparent_btn = ctk.CTkButton(
            self.actions_frame,
            text="Move to...",
            command=self._on_reparent_click,
            state="disabled",  # Enabled in WP07
        )
        self.reparent_btn.pack(fill="x", pady=2)

    def _load_tree(self):
        """Load hierarchy data into tree view."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._node_data.clear()

        # Get tree data from service
        if self.entity_type == "ingredient":
            tree_data = self.hierarchy_service.get_ingredient_tree()
        else:
            tree_data = self.hierarchy_service.get_hierarchy_tree()

        # Build tree
        for node in tree_data:
            self._insert_tree_node("", node)

        # Clear selection
        self._clear_detail_panel()

    def _insert_tree_node(self, parent_id: str, node: dict):
        """Recursively insert node and children into tree."""
        # Determine display text based on entity type
        if self.entity_type == "ingredient":
            name = node.get("display_name", node.get("name", "Unknown"))
            level = node.get("hierarchy_level", 0)
            prefix = {0: "[L0]", 1: "[L1]", 2: ""}.get(level, "")
        else:
            name = node.get("name", "Unknown")
            item_type = node.get("type", "material")
            prefix = {"category": "[Cat]", "subcategory": "[Sub]", "material": ""}.get(
                item_type, ""
            )

        display_text = f"{prefix} {name}".strip()

        # Insert node
        item_id = self.tree.insert(
            parent_id,
            "end",
            text=display_text,
            open=False,
            tags=(str(node.get("id")),),
        )

        # Store node data for lookup
        self._node_data[item_id] = node

        # Insert children
        for child in node.get("children", []):
            self._insert_tree_node(item_id, child)

    def _expand_all(self):
        """Expand all tree nodes."""

        def expand(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                expand(child)

        for item in self.tree.get_children():
            expand(item)

    def _collapse_all(self):
        """Collapse all tree nodes."""

        def collapse(item):
            self.tree.item(item, open=False)
            for child in self.tree.get_children(item):
                collapse(child)

        for item in self.tree.get_children():
            collapse(item)

    def _on_tree_select(self, event):
        """Handle tree selection change."""
        selection = self.tree.selection()
        if not selection:
            self._clear_detail_panel()
            return

        item_id = selection[0]
        node = self._node_data.get(item_id)
        if not node:
            self._clear_detail_panel()
            return

        self.selected_item = node
        self._update_detail_panel(node)

    def _update_detail_panel(self, node: dict):
        """Update detail panel with selected node info."""
        # Update name
        if self.entity_type == "ingredient":
            name = node.get("display_name", node.get("name", "-"))
        else:
            name = node.get("name", "-")
        self.name_label.configure(text=name)

        # Update level/type
        if self.entity_type == "ingredient":
            level = node.get("hierarchy_level", 0)
            level_names = {0: "Root (L0)", 1: "Category (L1)", 2: "Leaf (L2)"}
            self.level_label.configure(text=level_names.get(level, f"Level {level}"))
        else:
            item_type = node.get("type", "unknown")
            type_names = {
                "category": "Category",
                "subcategory": "Subcategory",
                "material": "Material",
            }
            self.level_label.configure(text=type_names.get(item_type, item_type.title()))

        # Build path
        path = self._get_item_path(node)
        self.path_label.configure(text=path)

        # Update usage counts
        self._update_usage_counts(node)

    def _get_item_path(self, node: dict) -> str:
        """Build display path for item."""
        if self.entity_type == "ingredient":
            # For ingredients, find the tree item and walk up parents
            # The node dict may have parent info we need to extract
            name = node.get("display_name", node.get("name", "-"))

            # Find this node's tree item to walk up
            for item_id, item_node in self._node_data.items():
                if item_node is node:
                    # Walk up tree to build path
                    parts = []
                    current = item_id
                    while current:
                        if current in self._node_data:
                            current_node = self._node_data[current]
                            current_name = current_node.get(
                                "display_name", current_node.get("name", "")
                            )
                            parts.insert(0, current_name)
                        parent = self.tree.parent(current)
                        current = parent if parent else None
                    return " > ".join(parts) if parts else name
            return name
        else:
            # For materials, use type to build path
            item_type = node.get("type")
            name = node.get("name", "-")

            if item_type == "material":
                # Find parent subcategory and category
                for item_id, item_node in self._node_data.items():
                    if item_node is node:
                        parts = []
                        current = item_id
                        while current:
                            if current in self._node_data:
                                current_node = self._node_data[current]
                                parts.insert(0, current_node.get("name", ""))
                            parent = self.tree.parent(current)
                            current = parent if parent else None
                        return " > ".join(parts) if parts else name
            elif item_type == "subcategory":
                # Find parent category
                for item_id, item_node in self._node_data.items():
                    if item_node is node:
                        parent = self.tree.parent(item_id)
                        if parent and parent in self._node_data:
                            cat_name = self._node_data[parent].get("name", "")
                            return f"{cat_name} > {name}"
                        return name
            return name

    def _update_usage_counts(self, node: dict):
        """Fetch and display usage counts for selected item."""
        if self.entity_type == "ingredient":
            level = node.get("hierarchy_level", 0)
            if level != 2:
                self.usage_label.configure(text="(Select L2 item for usage)")
                return

            item_id = node.get("id")
            if item_id:
                counts = self.hierarchy_service.get_usage_counts(item_id)
                text = f"Products: {counts['product_count']}, Recipes: {counts['recipe_count']}"
                self.usage_label.configure(text=text)
        else:
            item_type = node.get("type")
            if item_type != "material":
                self.usage_label.configure(text="(Select material for usage)")
                return

            item_id = node.get("id")
            if item_id:
                counts = self.hierarchy_service.get_usage_counts(item_id)
                text = f"Products: {counts['product_count']}"
                self.usage_label.configure(text=text)

    def _clear_detail_panel(self):
        """Clear detail panel when nothing selected."""
        self.selected_item = None
        self.name_label.configure(text="-")
        self.level_label.configure(text="-")
        self.path_label.configure(text="-")
        self.usage_label.configure(text="-")

    def _get_parent_options(self) -> list:
        """Get valid parent options for add operation."""
        if self.entity_type == "ingredient":
            # Get all L1 ingredients
            tree = self.hierarchy_service.get_ingredient_tree()
            options = []
            for l0 in tree:
                l0_name = l0.get("display_name", l0.get("name", ""))
                for l1 in l0.get("children", []):
                    l1_name = l1.get("display_name", l1.get("name", ""))
                    options.append({"id": l1["id"], "display": f"{l0_name} > {l1_name}"})
            return sorted(options, key=lambda x: x["display"])
        else:
            # Get all subcategories
            tree = self.hierarchy_service.get_hierarchy_tree()
            options = []
            for cat in tree:
                for subcat in cat.get("children", []):
                    if subcat.get("type") == "subcategory":
                        options.append(
                            {"id": subcat["id"], "display": f"{cat['name']} > {subcat['name']}"}
                        )
            return sorted(options, key=lambda x: x["display"])

    def _on_add_click(self):
        """Handle add button click - open add dialog."""
        parent_options = self._get_parent_options()

        if not parent_options:
            # Show error - no valid parents
            from tkinter import messagebox

            entity_name = "L1 ingredients" if self.entity_type == "ingredient" else "subcategories"
            messagebox.showerror("Cannot Add", f"No valid parent {entity_name} available.")
            return

        def on_save(data):
            """Callback when dialog saves."""
            try:
                if self.entity_type == "ingredient":
                    self.hierarchy_service.add_leaf_ingredient(
                        parent_id=data["parent_id"], name=data["name"]
                    )
                else:
                    self.hierarchy_service.add_material(
                        subcategory_id=data["parent_id"],
                        name=data["name"],
                        base_unit_type=data.get("base_unit_type", "each"),
                    )

                # Refresh tree
                self._load_tree()

                # Show success
                from tkinter import messagebox

                messagebox.showinfo("Success", f"{self.entity_type.title()} added successfully!")

            except ValueError as e:
                raise  # Re-raise for dialog to display

        AddItemDialog(self, self.entity_type, parent_options, on_save)

    def _on_rename_click(self):
        """Placeholder for rename operation."""
        pass  # Implemented in WP06

    def _on_reparent_click(self):
        """Placeholder for reparent operation."""
        pass  # Implemented in WP07


class AddItemDialog(ctk.CTkToplevel):
    """
    Dialog for adding new ingredient or material.

    Feature 052: Modal dialog for add operations in Hierarchy Admin.
    """

    def __init__(
        self,
        parent,
        entity_type: str,
        parent_options: list,
        on_save: Callable,
    ):
        super().__init__(parent)

        self.entity_type = entity_type
        self.on_save = on_save
        self.result = None

        # Window setup
        self.title(f"Add New {entity_type.title()}")
        self.geometry("400x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Build form
        self._create_form(parent_options)

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Focus on name entry after a brief delay
        self.after(100, lambda: self.name_entry.focus())

    def _create_form(self, parent_options):
        """Create the add form."""
        # Parent selection
        parent_frame = ctk.CTkFrame(self)
        parent_frame.pack(fill="x", padx=20, pady=10)

        if self.entity_type == "ingredient":
            label_text = "Parent (L1):"
        else:
            label_text = "Subcategory:"

        ctk.CTkLabel(parent_frame, text=label_text).pack(anchor="w")

        self.parent_var = ctk.StringVar()
        self.parent_dropdown = ctk.CTkComboBox(
            parent_frame,
            values=[p["display"] for p in parent_options],
            variable=self.parent_var,
            state="readonly",
            width=340,
        )
        self.parent_dropdown.pack(fill="x", pady=5)

        # Store mapping for lookup
        self._parent_map = {p["display"]: p["id"] for p in parent_options}

        # Set default selection if available
        if parent_options:
            self.parent_var.set(parent_options[0]["display"])

        # Name input
        name_frame = ctk.CTkFrame(self)
        name_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(name_frame, text="Name:").pack(anchor="w")
        self.name_entry = ctk.CTkEntry(name_frame, width=340)
        self.name_entry.pack(fill="x", pady=5)

        # Unit type (materials only)
        if self.entity_type == "material":
            unit_frame = ctk.CTkFrame(self)
            unit_frame.pack(fill="x", padx=20, pady=10)

            ctk.CTkLabel(unit_frame, text="Unit Type:").pack(anchor="w")
            self.unit_var = ctk.StringVar(value="each")
            self.unit_dropdown = ctk.CTkComboBox(
                unit_frame,
                values=["each", "linear_inches", "square_inches"],
                variable=self.unit_var,
                state="readonly",
                width=340,
            )
            self.unit_dropdown.pack(fill="x", pady=5)

        # Error label
        self.error_label = ctk.CTkLabel(self, text="", text_color="red")
        self.error_label.pack(pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            btn_frame, text="Cancel", command=self.destroy, fg_color="gray", width=100
        ).pack(side="right", padx=5)

        ctk.CTkButton(btn_frame, text="Add", command=self._on_save, width=100).pack(
            side="right", padx=5
        )

    def _on_save(self):
        """Handle save button click."""
        # Validate parent selection
        parent_display = self.parent_var.get()
        if not parent_display:
            self.error_label.configure(text="Please select a parent")
            return

        # Validate name
        name = self.name_entry.get().strip()
        if not name:
            self.error_label.configure(text="Name is required")
            return

        parent_id = self._parent_map.get(parent_display)
        if not parent_id:
            self.error_label.configure(text="Invalid parent selection")
            return

        # Build result
        self.result = {"parent_id": parent_id, "name": name}

        if self.entity_type == "material":
            self.result["base_unit_type"] = self.unit_var.get()

        # Call save callback
        try:
            self.on_save(self.result)
            self.destroy()
        except ValueError as e:
            self.error_label.configure(text=str(e))
