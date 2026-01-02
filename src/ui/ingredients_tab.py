"""
My Ingredients tab for the Seasonal Baking Tracker.

Provides CRUD interface for managing generic ingredient catalog
(brand-agnostic ingredient definitions) using the v0.4.0 refactored architecture.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import unicodedata
from typing import Optional, List, Dict, Any
from tkinter import messagebox


def normalize_for_search(text: str) -> str:
    """
    Normalize text for search by removing diacriticals and converting to lowercase.

    Examples:
        "Crème Brûlée" -> "creme brulee"
        "Café" -> "cafe"
        "Jalapeño" -> "jalapeno"
    """
    if not text:
        return ""

    # Normalize to NFKD form (canonical decomposition)
    nfkd = unicodedata.normalize("NFKD", text)

    # Remove combining marks (accents)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("ASCII")

    # Convert to lowercase for case-insensitive matching
    return ascii_text.lower()


from src.services import ingredient_service, product_service, ingredient_hierarchy_service
from src.services.ingredient_service import delete_ingredient_safe
from src.services.unit_service import get_units_for_dropdown
from src.services.exceptions import (
    IngredientInUse,
    IngredientNotFound,
    IngredientNotFoundBySlug,
    SlugAlreadyExists,
    ValidationError,
    DatabaseError,
    ProductInUse,
    ProductNotFound,
)
from src.utils.constants import (
    PADDING_MEDIUM,
    PADDING_LARGE,
    VOLUME_UNITS,
    WEIGHT_UNITS,
    PACKAGE_TYPES,
)
from src.ui.widgets.ingredient_tree_widget import IngredientTreeWidget


class IngredientsTab(ctk.CTkFrame):
    """
    Ingredient catalog management tab.

    Provides interface for:
    - Viewing all generic ingredients
    - Adding new ingredients
    - Editing existing ingredients
    - Deleting ingredients (with dependency checks)
    - Searching by name
    - Filtering by category
    """

    def __init__(self, parent):
        """
        Initialize the ingredients tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.selected_ingredient_slug: Optional[str] = None
        self.selected_ingredient_id: Optional[int] = None  # Feature 031: Track by ID too
        self.ingredients: List[dict] = []
        self._data_loaded = False  # Lazy loading flag
        self._view_mode = "flat"  # Feature 031: "flat" or "tree"
        self._hierarchy_path_cache: Dict[int, str] = {}  # Feature 033: Cache for hierarchy paths

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=0)  # Search/filter
        self.grid_rowconfigure(2, weight=0)  # Action buttons
        self.grid_rowconfigure(3, weight=1)  # Ingredient list
        self.grid_rowconfigure(4, weight=0)  # Status bar

        # Create UI components
        self._create_title()
        self._create_search_filter()
        self._create_action_buttons()
        self._create_ingredient_list()
        self._create_tree_view()  # Feature 031
        self._create_status_bar()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Show initial state - data will be loaded when tab is selected
        self._show_initial_state()

    def _create_title(self):
        """Create the title label."""
        title_label = ctk.CTkLabel(
            self,
            text="My Ingredients",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.grid(
            row=0, column=0, sticky="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM)
        )

    def _create_search_filter(self):
        """Create search and filter controls."""
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)
        search_frame.grid_columnconfigure(0, weight=1)

        # Search entry
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by ingredient name...",
            height=36,
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, PADDING_MEDIUM))
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # Feature 032: Level filter dropdown (replaces category filter)
        self.level_filter_var = ctk.StringVar(value="All Levels")
        self.level_filter_dropdown = ctk.CTkOptionMenu(
            search_frame,
            values=[
                "All Levels",
                "Root Categories (L0)",
                "Subcategories (L1)",
                "Leaf Ingredients (L2)",
            ],
            variable=self.level_filter_var,
            command=self._on_level_filter_change,
            width=200,
        )
        self.level_filter_dropdown.grid(row=0, column=1, padx=(0, PADDING_MEDIUM))

        # Feature 031: View toggle (Flat/Tree)
        self.view_var = ctk.StringVar(value="Flat")
        view_toggle = ctk.CTkSegmentedButton(
            search_frame,
            values=["Flat", "Tree"],
            variable=self.view_var,
            command=self._on_view_change,
            width=120,
        )
        view_toggle.grid(row=0, column=2, padx=(0, PADDING_MEDIUM))

        # Clear button
        clear_button = ctk.CTkButton(
            search_frame,
            text="Clear",
            command=self._clear_filters,
            width=100,
        )
        clear_button.grid(row=0, column=3)

    def _create_action_buttons(self):
        """Create action buttons for CRUD operations."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

        # Add button
        add_button = ctk.CTkButton(
            button_frame,
            text="➕ Add Ingredient",
            command=self._add_ingredient,
            width=150,
            height=36,
        )
        add_button.grid(row=0, column=0, padx=(0, PADDING_MEDIUM))

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="✏️ Edit",
            command=self._edit_ingredient,
            width=120,
            height=36,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=(0, PADDING_MEDIUM))

    def _create_ingredient_list(self):
        """Create the ingredient list using ttk.Treeview for performance."""
        # Container frame for grid and scrollbar
        self.grid_container = ctk.CTkFrame(self)
        self.grid_container.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=PADDING_LARGE,
            pady=PADDING_MEDIUM,
        )
        self.grid_container.grid_columnconfigure(0, weight=1)
        self.grid_container.grid_rowconfigure(0, weight=1)

        # Track current sort state
        self.sort_column = "name"
        self.sort_ascending = True

        # Define columns - Feature 033: Added hierarchy_path column
        columns = ("hierarchy_path", "name", "density")
        self.tree = ttk.Treeview(
            self.grid_container,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=20,  # Show more rows (default is 10)
        )

        # Configure column headings with click-to-sort - Feature 033: hierarchy path
        self.tree.heading(
            "hierarchy_path",
            text="Hierarchy",
            anchor="w",
            command=lambda: self._on_header_click("hierarchy_path"),
        )
        self.tree.heading(
            "name", text="Name", anchor="w", command=lambda: self._on_header_click("name")
        )
        self.tree.heading(
            "density",
            text="Density",
            anchor="w",
            command=lambda: self._on_header_click("density_display"),
        )

        # Configure column widths - Feature 033: hierarchy path column
        self.tree.column("hierarchy_path", width=300, minwidth=200)
        self.tree.column("name", width=200, minwidth=150)
        self.tree.column("density", width=120, minwidth=80)

        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(
            self.grid_container,
            orient="vertical",
            command=self.tree.yview,
        )
        x_scrollbar = ttk.Scrollbar(
            self.grid_container,
            orient="horizontal",
            command=self.tree.xview,
        )
        self.tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
        )

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        # Configure tag for packaging items
        self.tree.tag_configure("packaging", foreground="#0066cc")

        # Bind events
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _on_header_click(self, sort_key: str):
        """Handle column header click for sorting."""
        if self.sort_column == sort_key:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = sort_key
            self.sort_ascending = True
        self._update_ingredient_display()

    def _build_hierarchy_path_cache(self) -> Dict[int, str]:
        """Build cache mapping ingredient ID to hierarchy path string.

        Feature 033: This cache is built once per display refresh to avoid N+1 queries.
        Returns paths like "Baking > Flour > All-Purpose Flour" for L2 ingredients.

        Returns:
            Dict mapping ingredient ID to hierarchy path string
        """
        cache = {}
        for ingredient in self.ingredients:
            ing_id = ingredient.get("id")
            if not ing_id:
                continue

            ing_name = ingredient.get("display_name") or ingredient.get("name", "")
            hierarchy_level = ingredient.get("hierarchy_level", 2)

            if hierarchy_level == 0:
                # L0 (root) - just the name
                cache[ing_id] = ing_name
            elif hierarchy_level == 1:
                # L1 (subcategory) - L0 > L1
                try:
                    ancestors = ingredient_hierarchy_service.get_ancestors(ing_id)
                    if ancestors:
                        l0_name = ancestors[0].get("display_name", "")
                        cache[ing_id] = f"{l0_name} > {ing_name}"
                    else:
                        cache[ing_id] = ing_name
                except Exception:
                    cache[ing_id] = ing_name
            else:
                # L2 (leaf) - L0 > L1 > L2
                try:
                    ancestors = ingredient_hierarchy_service.get_ancestors(ing_id)
                    # ancestors[0] = immediate parent (L1), ancestors[1] = grandparent (L0)
                    if len(ancestors) >= 2:
                        l0_name = ancestors[1].get("display_name", "")
                        l1_name = ancestors[0].get("display_name", "")
                        cache[ing_id] = f"{l0_name} > {l1_name} > {ing_name}"
                    elif len(ancestors) == 1:
                        l1_name = ancestors[0].get("display_name", "")
                        cache[ing_id] = f"{l1_name} > {ing_name}"
                    else:
                        cache[ing_id] = ing_name
                except Exception:
                    cache[ing_id] = ing_name

        return cache

    def _on_double_click(self, event):
        """Handle double-click on ingredient row to open edit dialog."""
        selection = self.tree.selection()
        if selection:
            slug = selection[0]
            self.selected_ingredient_slug = slug
            self._enable_selection_buttons()
            self._edit_ingredient()

    def _on_tree_select(self, event):
        """Handle tree selection change."""
        selection = self.tree.selection()
        if selection:
            self.selected_ingredient_slug = selection[0]
            self._enable_selection_buttons()
        else:
            self._disable_selection_buttons()

    def _create_tree_view(self):
        """Create the hierarchical tree view for ingredients (Feature 031)."""
        # Container frame for tree widget (hidden by default)
        self.tree_container = ctk.CTkFrame(self)
        # Don't grid initially - will be shown when view mode is "Tree"

        # Create the tree widget
        self.ingredient_tree = IngredientTreeWidget(
            self.tree_container,
            on_select_callback=self._on_hierarchy_tree_select,
            leaf_only=False,  # Allow selecting all ingredients in this view
            show_search=False,  # Use our existing search
            show_breadcrumb=True,
        )
        self.ingredient_tree.pack(fill="both", expand=True, padx=5, pady=5)

    def _on_view_change(self, value: str):
        """Handle view toggle between Flat and Tree views (Feature 031)."""
        if value == "Tree":
            self._view_mode = "tree"
            # Hide flat view, show tree view
            self.grid_container.grid_remove()
            self.tree_container.grid(
                row=3,
                column=0,
                sticky="nsew",
                padx=PADDING_LARGE,
                pady=PADDING_MEDIUM,
            )
            # Refresh tree
            self.ingredient_tree.refresh()
            # Hide level filter (tree has its own navigation)
            self.level_filter_dropdown.configure(state="disabled")
            self.update_status("Tree view - navigate hierarchy")
        else:
            self._view_mode = "flat"
            # Hide tree view, show flat view
            self.tree_container.grid_remove()
            self.grid_container.grid(
                row=3,
                column=0,
                sticky="nsew",
                padx=PADDING_LARGE,
                pady=PADDING_MEDIUM,
            )
            # Re-enable level filter
            self.level_filter_dropdown.configure(state="normal")
            self._update_ingredient_display()

    def _on_hierarchy_tree_select(self, ingredient: Dict[str, Any]):
        """Handle selection in the hierarchy tree widget (Feature 031)."""
        if ingredient:
            self.selected_ingredient_slug = ingredient.get("slug")
            self.selected_ingredient_id = ingredient.get("id")
            self._enable_selection_buttons()
            name = ingredient.get("display_name", "Unknown")
            level = ingredient.get("hierarchy_level", 2)
            level_names = {0: "Category", 1: "Group", 2: "Ingredient"}
            self.update_status(f"Selected: {name} ({level_names.get(level, 'Unknown')})")
        else:
            self._disable_selection_buttons()

    def _create_status_bar(self):
        """Create status bar for displaying messages."""
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            anchor="w",
            height=30,
        )
        self.status_label.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=PADDING_LARGE,
            pady=(PADDING_MEDIUM, PADDING_LARGE),
        )

    def refresh(self):
        """Refresh the ingredient list from the database."""
        try:
            # Get all ingredients from service
            self.ingredients = ingredient_service.get_all_ingredients()

            # Feature 031: Refresh based on current view mode
            if self._view_mode == "tree":
                self.ingredient_tree.refresh()
                self.update_status("Tree view refreshed")
            else:
                # Update flat display
                self._update_ingredient_display()
                # Update status
                count = len(self.ingredients)
                self.update_status(f"{count} ingredient{'s' if count != 1 else ''} loaded")

        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to load ingredients: {e}")
            self.update_status("Error loading ingredients")

    def _show_initial_state(self):
        """Show initial loading state."""
        # Clear any existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.update_status("Loading...")

    def _update_ingredient_display(self):
        """Update the displayed list of ingredients based on current filters."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Feature 033: Build hierarchy path cache once per refresh
        self._hierarchy_path_cache = self._build_hierarchy_path_cache()

        # Apply filters
        filtered_ingredients = self._apply_filters(self.ingredients)

        # Populate grid with all ingredients (Treeview handles large datasets well)
        for ingredient in filtered_ingredients:
            # Feature 033: Get hierarchy path from cache
            ing_id = ingredient.get("id")
            hierarchy_path = self._hierarchy_path_cache.get(ing_id, "")

            name = ingredient.get("display_name") or ingredient.get("name", "Unknown")
            is_packaging = ingredient.get("is_packaging", False)
            density = ingredient.get("density_display", "—")
            if density == "Not set":
                density = "—"

            values = (hierarchy_path, name, density)
            tags = ("packaging",) if is_packaging else ()

            # Use slug as the item ID for easy lookup
            self.tree.insert("", "end", iid=ingredient["slug"], values=values, tags=tags)

        # Restore selection if still present
        if self.selected_ingredient_slug:
            try:
                self.tree.selection_set(self.selected_ingredient_slug)
                self._enable_selection_buttons()
            except tk.TclError:
                # Item not in filtered list
                self.selected_ingredient_slug = None
                self._disable_selection_buttons()
        else:
            self._disable_selection_buttons()

        # Update status with count
        count = len(filtered_ingredients)
        total = len(self.ingredients)
        if count < total:
            self.update_status(f"Showing {count} of {total} ingredients")
        else:
            self.update_status(f"{count} ingredient{'s' if count != 1 else ''}")

    def _apply_filters(self, ingredients: List[dict]) -> List[dict]:
        """Apply search, level filters, and sorting to ingredient list."""
        filtered = ingredients

        # Feature 032: Apply level filter
        selected_level = self._get_selected_level()
        if selected_level is not None:
            filtered = [ing for ing in filtered if ing.get("hierarchy_level") == selected_level]

        # Apply search filter with diacritical normalization
        # (e.g., "creme" matches "crème", "cafe" matches "café")
        search_text = normalize_for_search(self.search_entry.get())
        if search_text:
            filtered = [
                ing
                for ing in filtered
                if search_text
                in normalize_for_search(ing.get("display_name") or ing.get("name", ""))
            ]

        # Sort by selected column - Feature 033: support hierarchy_path sorting
        sort_key = getattr(self, "sort_column", "name")
        ascending = getattr(self, "sort_ascending", True)

        def get_sort_value(ing):
            """Get the sortable value for an ingredient based on sort_key."""
            if sort_key == "hierarchy_path":
                # Get hierarchy path from cache
                ing_id = ing.get("id")
                path = self._hierarchy_path_cache.get(ing_id, "")
                return path.lower()
            elif sort_key == "name":
                name = ing.get("display_name") or ing.get("name", "")
                return name.lower()
            else:
                val = ing.get(sort_key, "")
                return val.lower() if isinstance(val, str) else str(val)

        filtered = sorted(filtered, key=get_sort_value, reverse=not ascending)

        return filtered

    def _on_search(self, event=None):
        """Handle search text change."""
        # Feature 031: Handle search based on view mode
        if self._view_mode == "tree":
            query = self.search_entry.get().strip()
            self.ingredient_tree.search(query)
        else:
            self._update_ingredient_display()

    def _on_level_filter_change(self, level: str):
        """Handle level filter change (Feature 032)."""
        self._update_ingredient_display()

    def _get_selected_level(self) -> Optional[int]:
        """Convert level filter dropdown value to hierarchy level number.

        Feature 032: Maps dropdown text to hierarchy_level values.

        Returns:
            0 for L0, 1 for L1, 2 for L2, or None for All Levels
        """
        value = self.level_filter_var.get()
        level_map = {
            "All Levels": None,
            "Root Categories (L0)": 0,
            "Subcategories (L1)": 1,
            "Leaf Ingredients (L2)": 2,
        }
        return level_map.get(value)

    def _clear_filters(self):
        """Clear all filters and refresh display."""
        self.search_entry.delete(0, "end")
        self.level_filter_var.set("All Levels")  # Feature 032: Reset level filter
        # Feature 031: Clear search based on view mode
        if self._view_mode == "tree":
            self.ingredient_tree.clear_search()
        else:
            self._update_ingredient_display()

    def select_ingredient(self, ingredient_slug: str) -> None:
        """
        Programmatically select an ingredient from the list.

        Args:
            ingredient_slug: Slug of the ingredient to select.
        """
        if not ingredient_slug:
            return

        if not any(ing["slug"] == ingredient_slug for ing in self.ingredients):
            self.refresh()

        if not any(ing["slug"] == ingredient_slug for ing in self.ingredients):
            self.update_status(f"Ingredient '{ingredient_slug}' not found")
            return

        self.selected_ingredient_slug = ingredient_slug
        self._update_ingredient_display()
        # Treeview selection is handled in _update_ingredient_display()
        self.update_status(f"Ingredient '{ingredient_slug}' selected")

    def _enable_selection_buttons(self):
        """Enable buttons that require a selection."""
        self.edit_button.configure(state="normal")

    def _disable_selection_buttons(self):
        """Disable buttons that require a selection."""
        self.edit_button.configure(state="disabled")
        self.selected_ingredient_slug = None

    def _add_ingredient(self):
        """Open dialog to add a new ingredient."""
        dialog = IngredientFormDialog(self, title="Add Ingredient")
        self.wait_window(dialog)

        if dialog.result:
            try:
                # Create ingredient using service
                ingredient_obj = ingredient_service.create_ingredient(dialog.result)
                ingredient_name = getattr(
                    ingredient_obj, "name", dialog.result.get("name", "Ingredient")
                )
                self.selected_ingredient_slug = getattr(ingredient_obj, "slug", None)
                self.refresh()
                # Selection is restored by refresh() -> _update_ingredient_display()
                self.update_status(f"Ingredient '{ingredient_name}' added successfully")
                messagebox.showinfo("Success", f"Ingredient '{ingredient_name}' created!")

            except ValidationError as e:
                messagebox.showerror("Validation Error", str(e))
            except SlugAlreadyExists as e:
                messagebox.showerror("Duplicate Ingredient", str(e))
            except DatabaseError as e:
                messagebox.showerror("Database Error", f"Failed to create ingredient: {e}")

    def _edit_ingredient(self):
        """Open dialog to edit the selected ingredient."""
        if not self.selected_ingredient_slug:
            return

        try:
            # Get current ingredient data
            ingredient_obj = ingredient_service.get_ingredient(self.selected_ingredient_slug)
            ingredient_data = (
                ingredient_obj.to_dict()
                if hasattr(ingredient_obj, "to_dict")
                else {
                    "name": ingredient_obj.display_name,
                    "category": ingredient_obj.category,
                    "density_volume_value": ingredient_obj.density_volume_value,
                    "density_volume_unit": ingredient_obj.density_volume_unit,
                    "density_weight_value": ingredient_obj.density_weight_value,
                    "density_weight_unit": ingredient_obj.density_weight_unit,
                }
            )
            # Store slug in ingredient_data for delete operation
            ingredient_data["slug"] = self.selected_ingredient_slug

            dialog = IngredientFormDialog(
                self,
                ingredient=ingredient_data,
                title="Edit Ingredient",
            )
            self.wait_window(dialog)

            # Check if ingredient was deleted
            if dialog.deleted:
                self.selected_ingredient_slug = None
                self.refresh()
                return

            if dialog.result:
                # Update ingredient using service
                updated_obj = ingredient_service.update_ingredient(
                    self.selected_ingredient_slug,
                    dialog.result,
                )
                if updated_obj:
                    updated_name = getattr(
                        updated_obj, "name", dialog.result.get("name", "Ingredient")
                    )
                    self.selected_ingredient_slug = getattr(
                        updated_obj, "slug", self.selected_ingredient_slug
                    )
                    self.update_status(f"Ingredient '{updated_name}' updated successfully")
                else:
                    self.update_status("Ingredient updated successfully")
                self.refresh()
                # Selection is restored by refresh() -> _update_ingredient_display()
                messagebox.showinfo("Success", "Ingredient updated!")

        except IngredientNotFoundBySlug:
            messagebox.showerror("Error", "Ingredient not found")
            self.refresh()
        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e))
        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to update ingredient: {e}")

    def _delete_ingredient(self):
        """Delete the selected ingredient after confirmation.

        Uses delete_ingredient_safe() which:
        - Blocks deletion if products, recipes, or children reference the ingredient
        - Denormalizes snapshot records before deletion to preserve history
        - Cascades delete for aliases and crosswalks via DB constraints
        """
        if not self.selected_ingredient_slug:
            return

        try:
            # Get ingredient for confirmation and ID
            ingredient = ingredient_service.get_ingredient(self.selected_ingredient_slug)
            name = ingredient.display_name
            ingredient_id = ingredient.id

            # Confirm deletion
            result = messagebox.askyesno(
                "Confirm Deletion",
                f"Are you sure you want to delete '{name}'?\n\n"
                "This will fail if the ingredient has products, recipes, or child ingredients.",
            )

            if result:
                # Delete using safe deletion service (F035)
                delete_ingredient_safe(ingredient_id)
                self.selected_ingredient_slug = None
                self.refresh()
                self.update_status(f"Ingredient '{name}' deleted successfully")
                messagebox.showinfo("Success", "Ingredient deleted!")

        except IngredientNotFoundBySlug:
            messagebox.showerror("Error", "Ingredient not found")
            self.refresh()
        except IngredientNotFound:
            messagebox.showerror("Error", "Ingredient not found")
            self.refresh()
        except IngredientInUse as e:
            # F035: Show detailed message with counts
            self._show_deletion_blocked_message(e.details if hasattr(e, "details") else {})
        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to delete ingredient: {e}")
        except Exception as e:
            # Catch-all for unexpected errors
            messagebox.showerror("Error", f"Unexpected error deleting ingredient: {e}")
            import traceback

            traceback.print_exc()

    def _show_deletion_blocked_message(self, details: dict):
        """Display user-friendly message when ingredient deletion is blocked.

        Args:
            details: Dict with counts {products: N, recipes: N, children: N, snapshots: N}
        """
        parts = []

        if details.get("products", 0) > 0:
            count = details["products"]
            parts.append(f"{count} product{'s' if count > 1 else ''}")

        if details.get("recipes", 0) > 0:
            count = details["recipes"]
            parts.append(f"{count} recipe{'s' if count > 1 else ''}")

        if details.get("children", 0) > 0:
            count = details["children"]
            parts.append(f"{count} child ingredient{'s' if count > 1 else ''}")

        if parts:
            # Build grammatically correct list (a, b and c)
            if len(parts) == 1:
                items = parts[0]
            elif len(parts) == 2:
                items = f"{parts[0]} and {parts[1]}"
            else:
                items = ", ".join(parts[:-1]) + f" and {parts[-1]}"

            message = (
                f"Cannot delete this ingredient.\n\n"
                f"It is referenced by {items}.\n\n"
                f"Please reassign or remove these references first."
            )
        else:
            message = "Cannot delete this ingredient. It has active references."

        messagebox.showerror("Cannot Delete", message)

    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.configure(text=message)


class IngredientFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a generic ingredient.

    Simplified form for the v0.4.0 architecture (no brand, quantity, etc.).
    """

    def __init__(
        self,
        parent,
        ingredient: Optional[dict] = None,
        title: str = "Add Ingredient",
    ):
        """
        Initialize the ingredient form dialog.

        Args:
            parent: Parent window
            ingredient: Existing ingredient dict to edit (None for new)
            title: Dialog title
        """
        super().__init__(parent)

        # Feature 032: Apply modal pattern - hide while building
        self.withdraw()

        # Store reference to parent tab for accessing data
        self.parent_tab = parent

        if ingredient is not None and hasattr(ingredient, "to_dict"):
            ingredient = ingredient.to_dict()
        self.ingredient = ingredient
        self.result: Optional[Dict[str, Any]] = None
        self.deleted = False  # Track if item was deleted

        # Configure window
        self.title(title)
        self.geometry("550x600")  # Height for hierarchy fields
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Create form
        self._create_form()
        self._create_buttons()

        # Populate if editing
        if self.ingredient:
            self._populate_form()

        # Feature 032: Show dialog after UI is complete
        self.deiconify()
        self.update()
        try:
            self.wait_visibility()
            self.grab_set()
        except Exception:
            if not self.winfo_exists():
                return
        self.lift()
        self.focus_force()

    def _create_form(self):
        """Create form fields."""
        form_frame = ctk.CTkFrame(self)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        form_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Name field - editable when adding, read-only when editing
        # (Name is tied to slug which is used as FK, so editing is not supported)
        if self.ingredient:
            # Editing mode - show name as read-only label
            ctk.CTkLabel(form_frame, text="Name:").grid(
                row=row, column=0, sticky="w", padx=10, pady=(10, 5)
            )
            # Get name from either 'name' or 'display_name' key
            ingredient_name = self.ingredient.get("name") or self.ingredient.get("display_name", "")
            self.name_label = ctk.CTkLabel(
                form_frame,
                text=ingredient_name,
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            )
            self.name_label.grid(row=row, column=1, sticky="ew", padx=10, pady=(10, 5))
            self.name_entry = None  # No entry when editing
        else:
            # Add mode - editable entry
            ctk.CTkLabel(form_frame, text="Name*:").grid(
                row=row, column=0, sticky="w", padx=10, pady=(10, 5)
            )
            self.name_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g., All-Purpose Flour")
            self.name_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=(10, 5))
        row += 1

        # Feature 011: Is Packaging checkbox
        ctk.CTkLabel(form_frame, text="Type:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.is_packaging_var = ctk.BooleanVar(value=False)
        self.is_packaging_checkbox = ctk.CTkCheckBox(
            form_frame,
            text="This is a packaging material (bags, boxes, ribbon, etc.)",
            variable=self.is_packaging_var,
        )
        self.is_packaging_checkbox.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # Feature 033: Parent selection section header
        ctk.CTkLabel(
            form_frame,
            text="Parent Ingredient (determines level):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        row += 1

        # Feature 033: Root Category (L0) dropdown
        self.l0_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        self.l0_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self.l0_frame, text="Root Category (L0):").grid(
            row=0, column=0, sticky="w", padx=0, pady=0
        )

        # Build L0 options from root ingredients
        self._l0_options = self._build_l0_options()
        self.l0_var = ctk.StringVar(value="(None - create root)")
        self.l0_dropdown = ctk.CTkComboBox(
            self.l0_frame,
            values=["(None - create root)"] + list(self._l0_options.keys()),
            variable=self.l0_var,
            command=self._on_l0_change,
            width=280,
        )
        self.l0_dropdown.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=0)
        row += 1

        # Feature 033: Subcategory (L1) dropdown
        self.l1_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        self.l1_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self.l1_frame, text="Subcategory (L1):").grid(
            row=0, column=0, sticky="w", padx=0, pady=0
        )

        self._l1_options: Dict[str, int] = {}  # Populated on L0 change
        self.l1_var = ctk.StringVar(value="(Select L0 first)")
        self.l1_dropdown = ctk.CTkComboBox(
            self.l1_frame,
            values=["(Select L0 first)"],
            variable=self.l1_var,
            command=self._on_l1_change,
            state="disabled",
            width=280,
        )
        self.l1_dropdown.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=0)
        row += 1

        # Feature 033: Level display (computed from parent selection)
        self.level_display_var = ctk.StringVar(value="Level: L0 (Root Category)")
        self.level_display = ctk.CTkLabel(
            form_frame,
            textvariable=self.level_display_var,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="gray",
        )
        self.level_display.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        row += 1

        # Feature 033: Warning label for parent changes (hidden by default)
        self.warning_label = ctk.CTkLabel(
            form_frame,
            text="",
            text_color="orange",
            wraplength=350,
        )
        self.warning_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=2)
        self.warning_label.grid_remove()  # Hidden by default
        row += 1

        # Density section (4-field input)
        ctk.CTkLabel(form_frame, text="Density (optional):").grid(
            row=row, column=0, sticky="nw", padx=10, pady=5
        )

        # Create density frame for 4-field layout
        density_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        density_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Volume value entry
        self.density_volume_value_entry = ctk.CTkEntry(
            density_frame,
            width=70,
            placeholder_text="1.0",
        )
        self.density_volume_value_entry.grid(row=0, column=0, padx=(0, 5))

        # Volume unit dropdown
        self.density_volume_unit_var = ctk.StringVar(value="")
        self.density_volume_unit_dropdown = ctk.CTkComboBox(
            density_frame,
            values=[""] + VOLUME_UNITS,
            variable=self.density_volume_unit_var,
            width=90,
        )
        self.density_volume_unit_dropdown.grid(row=0, column=1, padx=(0, 10))

        # Equals label
        ctk.CTkLabel(
            density_frame,
            text="=",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=2, padx=10)

        # Weight value entry
        self.density_weight_value_entry = ctk.CTkEntry(
            density_frame,
            width=70,
            placeholder_text="4.25",
        )
        self.density_weight_value_entry.grid(row=0, column=3, padx=(10, 5))

        # Weight unit dropdown
        self.density_weight_unit_var = ctk.StringVar(value="")
        self.density_weight_unit_dropdown = ctk.CTkComboBox(
            density_frame,
            values=[""] + WEIGHT_UNITS,
            variable=self.density_weight_unit_var,
            width=90,
        )
        self.density_weight_unit_dropdown.grid(row=0, column=4)

        # Density error label (hidden by default)
        self.density_error_label = ctk.CTkLabel(
            form_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#F44336",  # Red
        )
        self.density_error_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=0)
        row += 1

        # Help text
        help_label = ctk.CTkLabel(
            form_frame,
            text="* Required fields\n\n"
            "Density is used for volume-weight conversions.\n"
            "Example: 1 cup = 4.25 oz (for flour)\n"
            "Leave all density fields blank if not applicable.",
            text_color="gray",
            justify="left",
        )
        help_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=10)

    def _create_buttons(self):
        """Create Save, Cancel, and Delete buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        button_frame.grid_columnconfigure(0, weight=1)  # Left side expands

        # Delete button on left (only when editing)
        if self.ingredient:
            delete_button = ctk.CTkButton(
                button_frame,
                text="Delete",
                command=self._delete,
                width=100,
                fg_color="#8B0000",
                hover_color="#B22222",
            )
            delete_button.grid(row=0, column=0, sticky="w")

        # Cancel and Save buttons on right
        right_buttons = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_buttons.grid(row=0, column=1, sticky="e")

        cancel_button = ctk.CTkButton(
            right_buttons,
            text="Cancel",
            command=self._cancel,
            width=120,
        )
        cancel_button.grid(row=0, column=0, padx=(0, 10))

        save_button = ctk.CTkButton(
            right_buttons,
            text="Save",
            command=self._save,
            width=120,
        )
        save_button.grid(row=0, column=1)

    def _build_l0_options(self) -> Dict[str, int]:
        """Build L0 (root category) options for dropdown.

        Feature 032: Returns dict mapping display name to ingredient ID.
        """
        options = {}
        try:
            roots = ingredient_hierarchy_service.get_root_ingredients()
            for root in roots:
                display = root.get("display_name", "Unknown")
                options[display] = root.get("id")
        except Exception:
            pass
        return options

    def _compute_and_display_level(self):
        """Compute and display the ingredient level based on parent selection.

        Feature 033: Level is determined by parent selection, not explicit dropdown.
        """
        l0_selection = self.l0_var.get()
        l1_selection = self.l1_var.get()

        # Check if no L0 selected = creating root (L0)
        if l0_selection == "(None - create root)" or l0_selection == "":
            level = 0
            level_text = "Level: L0 (Root Category)"
        # Check if L0 selected but no L1 = creating subcategory (L1)
        elif l1_selection in [
            "(Select L0 first)",
            "(None - create L1)",
            "(No subcategories)",
            "",
        ]:
            level = 1
            level_text = "Level: L1 (Subcategory)"
        # L1 selected = creating leaf (L2)
        else:
            level = 2
            level_text = "Level: L2 (Leaf Ingredient)"

        self.level_display_var.set(level_text)
        self._check_parent_change_warnings()
        return level

    def _check_parent_change_warnings(self):
        """Check and display warnings for parent change on existing ingredient.

        Feature 033: Informational warnings when editing existing ingredient's parent.
        """
        # Only check for existing ingredients
        if not self.ingredient or not self.ingredient.get("id"):
            self.warning_label.grid_remove()
            return

        ingredient_id = self.ingredient.get("id")
        new_parent_id = self._get_selected_parent_id()

        # Check with can_change_parent
        try:
            result = ingredient_hierarchy_service.can_change_parent(ingredient_id, new_parent_id)

            if not result["allowed"]:
                self.warning_label.configure(text=result["reason"], text_color="red")
                self.warning_label.grid()
            elif result["warnings"]:
                warning_text = " | ".join(result["warnings"])
                self.warning_label.configure(text=warning_text, text_color="orange")
                self.warning_label.grid()
            else:
                self.warning_label.grid_remove()
        except Exception:
            self.warning_label.grid_remove()

    def _get_selected_parent_id(self) -> Optional[int]:
        """Get the parent ingredient ID based on current dropdown selections.

        Feature 033: Returns the appropriate parent based on level.
        """
        l0_selection = self.l0_var.get()
        l1_selection = self.l1_var.get()

        # No L0 selected = root ingredient
        if l0_selection == "(None - create root)" or l0_selection == "":
            return None

        # L0 selected but no valid L1 = L1 ingredient (parent is L0)
        if (
            l1_selection
            in [
                "(Select L0 first)",
                "(None - create L1)",
                "(No subcategories)",
                "",
            ]
            or l1_selection not in self._l1_options
        ):
            return self._l0_options.get(l0_selection)

        # L1 selected = L2 ingredient (parent is L1)
        return self._l1_options.get(l1_selection)

    def _on_l0_change(self, value: str):
        """Handle L0 category selection - populate L1 dropdown.

        Feature 033: Cascading dropdown behavior with level computation.
        """
        if value == "(None - create root)" or value not in self._l0_options:
            # Reset L1 dropdown
            self.l1_dropdown.configure(values=["(Select L0 first)"], state="disabled")
            self.l1_var.set("(Select L0 first)")
            self._compute_and_display_level()
            return

        # Get children of selected L0 (only L1 ingredients)
        l0_id = self._l0_options[value]
        try:
            subcategories = ingredient_hierarchy_service.get_children(l0_id)
            # Filter to only include L1 ingredients
            l1_subs = [s for s in subcategories if s.get("hierarchy_level") == 1]
            self._l1_options = {sub.get("display_name", "?"): sub.get("id") for sub in l1_subs}

            if l1_subs:
                sub_names = ["(None - create L1)"] + sorted(self._l1_options.keys())
                self.l1_dropdown.configure(values=sub_names, state="normal")
                self.l1_var.set("(None - create L1)")
            else:
                self.l1_dropdown.configure(values=["(None - create L1)"], state="normal")
                self.l1_var.set("(None - create L1)")
        except Exception:
            self.l1_dropdown.configure(values=["(Error loading)"], state="disabled")
            self.l1_var.set("(Error loading)")

        self._compute_and_display_level()

    def _on_l1_change(self, value: str):
        """Handle L1 subcategory selection.

        Feature 033: Update level display when L1 selection changes.
        """
        self._compute_and_display_level()

    def _populate_form(self):
        """Populate form with existing ingredient data."""
        if not self.ingredient:
            return

        # Name is shown as read-only label in edit mode (set during _create_form)

        # Feature 011: Set is_packaging checkbox
        is_packaging = self.ingredient.get("is_packaging", False)
        self.is_packaging_var.set(is_packaging)

        # Feature 033: Pre-populate hierarchy dropdowns based on ancestors
        level = self.ingredient.get("hierarchy_level", 2)
        ing_id = self.ingredient.get("id")

        if level == 0:
            # L0 (Root): No parent selected
            self.l0_var.set("(None - create root)")
            self.l1_var.set("(Select L0 first)")
            self.l1_dropdown.configure(state="disabled")
        elif ing_id and level > 0:
            try:
                ancestors = ingredient_hierarchy_service.get_ancestors(ing_id)
                if level == 2 and len(ancestors) >= 2:
                    # L2: Has L1 parent and L0 grandparent
                    l0_name = ancestors[1].get("display_name")
                    l1_name = ancestors[0].get("display_name")
                    if l0_name and l0_name in self._l0_options:
                        self.l0_var.set(l0_name)
                        self._on_l0_change(l0_name)  # Populate L1 dropdown
                        if l1_name and l1_name in self._l1_options:
                            self.l1_var.set(l1_name)
                elif level == 2 and len(ancestors) == 1:
                    # L2 with only L1 parent (unusual but handle it)
                    l1_name = ancestors[0].get("display_name")
                    # Can't set L0 dropdown, just show error state
                elif level == 1 and len(ancestors) >= 1:
                    # L1: Has L0 parent
                    l0_name = ancestors[0].get("display_name")
                    if l0_name and l0_name in self._l0_options:
                        self.l0_var.set(l0_name)
                        self._on_l0_change(l0_name)  # Populate L1 but set to None
                        self.l1_var.set("(None - create L1)")
            except Exception:
                pass  # Leave dropdowns at default if ancestors lookup fails

        # Feature 033: Update level display based on parent selection
        self._compute_and_display_level()

        # Populate 4-field density
        if self.ingredient.get("density_volume_value") is not None:
            self.density_volume_value_entry.insert(0, str(self.ingredient["density_volume_value"]))
        if self.ingredient.get("density_volume_unit"):
            self.density_volume_unit_var.set(self.ingredient["density_volume_unit"])
        if self.ingredient.get("density_weight_value") is not None:
            self.density_weight_value_entry.insert(0, str(self.ingredient["density_weight_value"]))
        if self.ingredient.get("density_weight_unit"):
            self.density_weight_unit_var.set(self.ingredient["density_weight_unit"])

    def _get_density_values(self):
        """Get density values from form fields.

        Returns:
            Tuple of (volume_value, volume_unit, weight_value, weight_unit)
        """
        # Get volume value
        volume_value_str = self.density_volume_value_entry.get().strip()
        volume_value = float(volume_value_str) if volume_value_str else None

        # Get volume unit
        volume_unit = self.density_volume_unit_var.get()
        volume_unit = volume_unit if volume_unit else None

        # Get weight value
        weight_value_str = self.density_weight_value_entry.get().strip()
        weight_value = float(weight_value_str) if weight_value_str else None

        # Get weight unit
        weight_unit = self.density_weight_unit_var.get()
        weight_unit = weight_unit if weight_unit else None

        return volume_value, volume_unit, weight_value, weight_unit

    def _validate_density_input(self):
        """Validate density input fields.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            volume_value, volume_unit, weight_value, weight_unit = self._get_density_values()
        except ValueError:
            return False, "Please enter valid numbers for density values"

        from src.services.ingredient_service import validate_density_fields

        return validate_density_fields(volume_value, volume_unit, weight_value, weight_unit)

    def _save(self):
        """Validate and save the form data."""
        # Get values - name is only editable when adding (not editing)
        if self.name_entry:
            # Add mode - get name from entry
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showerror("Validation Error", "Name is required")
                return
        else:
            # Edit mode - name is read-only, use existing name
            name = self.ingredient.get("name") or self.ingredient.get("display_name", "")

        is_packaging = self.is_packaging_var.get()  # Feature 011

        # Feature 033: Determine hierarchy level and parent from dropdown selections
        hierarchy_level = self._compute_and_display_level()
        parent_ingredient_id = self._get_selected_parent_id()

        # Validate L2 has a proper L1 parent selected
        if hierarchy_level == 2:
            l1_selection = self.l1_var.get()
            if l1_selection not in self._l1_options:
                messagebox.showerror(
                    "Validation Error", "Please select a Subcategory (L1) for leaf ingredients"
                )
                return

        # Validate density fields
        is_valid, error = self._validate_density_input()
        if not is_valid:
            self.density_error_label.configure(text=error)
            return

        # Clear error on success
        self.density_error_label.configure(text="")

        # Get density values
        try:
            volume_value, volume_unit, weight_value, weight_unit = self._get_density_values()
        except ValueError:
            self.density_error_label.configure(text="Please enter valid numbers")
            return

        # Build result dict - Feature 032: Use hierarchy_level and parent_ingredient_id
        result: Dict[str, Any] = {
            "name": name,
            "is_packaging": is_packaging,
            "hierarchy_level": hierarchy_level,
        }

        # Add parent_ingredient_id if not root
        if parent_ingredient_id is not None:
            result["parent_ingredient_id"] = parent_ingredient_id

        # Add density fields if any are provided
        if volume_value is not None:
            result["density_volume_value"] = volume_value
        if volume_unit:
            result["density_volume_unit"] = volume_unit
        if weight_value is not None:
            result["density_weight_value"] = weight_value
        if weight_unit:
            result["density_weight_unit"] = weight_unit

        self.result = result

        self.destroy()

    def _cancel(self):
        """Cancel the form."""
        self.result = None
        self.destroy()

    def _delete(self):
        """Delete the ingredient after confirmation.

        Uses delete_ingredient_safe() which:
        - Blocks deletion if products, recipes, or children reference the ingredient
        - Denormalizes snapshot records before deletion to preserve history
        - Cascades delete for aliases and crosswalks via DB constraints
        """
        if not self.ingredient:
            return

        # Get ingredient name and ID for confirmation
        name = self.ingredient.get("name") or self.ingredient.get("display_name", "")
        ingredient_id = self.ingredient.get("id")

        if not ingredient_id:
            messagebox.showerror("Error", "Cannot delete: ingredient ID not found")
            return

        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete '{name}'?\n\n"
            "This will fail if the ingredient has products, recipes, or child ingredients.",
        )

        if result:
            try:
                # Delete using safe deletion service (F035)
                delete_ingredient_safe(ingredient_id)
                self.deleted = True
                self.result = None
                messagebox.showinfo("Success", f"Ingredient '{name}' deleted!")
                self.destroy()

            except IngredientNotFound:
                messagebox.showerror("Error", "Ingredient not found")
            except IngredientNotFoundBySlug:
                messagebox.showerror("Error", "Ingredient not found")
            except IngredientInUse as e:
                # F035: Show detailed message with counts
                self._show_dialog_deletion_blocked_message(e.details if hasattr(e, "details") else {})
            except DatabaseError as e:
                messagebox.showerror("Database Error", f"Failed to delete ingredient: {e}")

    def _show_dialog_deletion_blocked_message(self, details: dict):
        """Display user-friendly message when ingredient deletion is blocked (dialog version).

        Args:
            details: Dict with counts {products: N, recipes: N, children: N, snapshots: N}
        """
        parts = []

        if details.get("products", 0) > 0:
            count = details["products"]
            parts.append(f"{count} product{'s' if count > 1 else ''}")

        if details.get("recipes", 0) > 0:
            count = details["recipes"]
            parts.append(f"{count} recipe{'s' if count > 1 else ''}")

        if details.get("children", 0) > 0:
            count = details["children"]
            parts.append(f"{count} child ingredient{'s' if count > 1 else ''}")

        if parts:
            # Build grammatically correct list (a, b and c)
            if len(parts) == 1:
                items = parts[0]
            elif len(parts) == 2:
                items = f"{parts[0]} and {parts[1]}"
            else:
                items = ", ".join(parts[:-1]) + f" and {parts[-1]}"

            message = (
                f"Cannot delete this ingredient.\n\n"
                f"It is referenced by {items}.\n\n"
                f"Please reassign or remove these references first."
            )
        else:
            message = "Cannot delete this ingredient. It has active references."

        messagebox.showerror("Cannot Delete", message)
