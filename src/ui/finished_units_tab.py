"""
Finished Units tab for the Seasonal Baking Tracker.

Provides read-only catalog interface for viewing finished units (yield types).
Yield types are managed through Recipe Edit, not directly in this tab.
Double-click navigates to parent recipe for editing.
"""

import customtkinter as ctk
import logging
from tkinter import ttk
from typing import Optional, List
from contextlib import contextmanager

# Conditional imports for forward compatibility
try:
    from src.models.finished_unit import FinishedUnit

    HAS_FINISHED_UNIT_MODEL = True
except ImportError:
    # Fall back to FinishedGood model until FinishedUnit is implemented
    from src.models.finished_good import FinishedGood as FinishedUnit

    HAS_FINISHED_UNIT_MODEL = False

try:
    from src.services import finished_unit_service

    HAS_FINISHED_UNIT_SERVICE = True
except ImportError:
    # Fall back to finished_good_service until FinishedUnit service is implemented
    from src.services import finished_good_service as finished_unit_service

    HAS_FINISHED_UNIT_SERVICE = False
from src.models.recipe import Recipe
from src.services.database import session_scope
from src.utils.constants import (
    PADDING_MEDIUM,
    PADDING_LARGE,
    COLOR_SUCCESS,
    COLOR_ERROR,
)
from src.ui.widgets.search_bar import SearchBar
from src.ui.widgets.dialogs import (
    show_error,
)
from src.services.exceptions import ServiceError
from src.ui.utils.error_handler import handle_error

from src.ui.service_integration import get_ui_service_integrator, OperationType


# Constants for status messages
class StatusMessages:
    """Status message constants for internationalization and consistency."""

    READY = "Ready"
    SEARCH_FAILED = "Search failed"
    FAILED_TO_LOAD = "Failed to load finished units"
    SELECTION_STALE = "Selected item no longer exists"

    @staticmethod
    def found_units(count: int) -> str:
        return f"Found {count} finished unit(s)"

    @staticmethod
    def selected_unit(name: str) -> str:
        return f"Selected: {name}"

    @staticmethod
    def loaded_units(count: int) -> str:
        return f"Loaded {count} finished unit(s)"


class FinishedUnitsTab(ctk.CTkFrame):
    """
    Finished Units read-only catalog tab.

    Provides interface for:
    - Viewing all finished units (individual consumable items) in a searchable table
    - Viewing finished unit details and costs
    - Filtering by category or parent recipe
    - Double-click navigation to edit the parent recipe

    Note: Yield types are managed through Recipe Edit, not directly in this tab.
    """

    def __init__(self, parent):
        """
        Initialize the finished units tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.selected_finished_unit: Optional[FinishedUnit] = None
        self.service_integrator = get_ui_service_integrator()
        self.recipe_categories = self._load_recipe_categories()

        # Track current finished units for selection lookup
        self._current_finished_units: List[FinishedUnit] = []

        # Track current sort state for column header sorting
        self.sort_column = "name"
        self.sort_ascending = True

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Search bar
        self.grid_rowconfigure(1, weight=0)  # Action buttons
        self.grid_rowconfigure(2, weight=1)  # Data table
        self.grid_rowconfigure(3, weight=0)  # Status bar

        # Create UI components
        self._create_search_bar()
        self._create_action_buttons()
        self._create_data_table()
        self._create_status_bar()

        # Data will be loaded when tab is first selected (lazy loading)
        # self.refresh()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    @contextmanager
    def status_context(self, operation_message: str, success_message: Optional[str] = None):
        """
        Context manager for status updates during operations.

        Args:
            operation_message: Message to show while operation is in progress
            success_message: Message to show on successful completion (optional)

        Usage:
            with self.status_context("Creating finished unit", "Unit created successfully"):
                # operation code here
                pass
        """
        # Set initial status
        self._update_status(operation_message)
        try:
            yield
            # Operation succeeded
            if success_message:
                self._update_status(success_message, success=True)
        except Exception as e:
            # Operation failed
            error_msg = getattr(e, "message", str(e))
            self._update_status(f"{operation_message} failed: {error_msg}", error=True)
            raise  # Re-raise the exception

    def _load_recipe_categories(self) -> list:
        """Load recipe categories from database."""
        try:
            with session_scope() as session:
                categories = (
                    session.query(Recipe.category)
                    .distinct()
                    .filter(Recipe.category.isnot(None))
                    .order_by(Recipe.category)
                    .all()
                )
                return [cat[0] for cat in categories if cat[0]]
        except Exception:
            return []

    def _create_search_bar(self):
        """Create the search bar with category filter."""
        # Note: SearchBar adds "All Categories" internally, so don't add it here
        self.search_bar = SearchBar(
            self,
            search_callback=self._on_search,
            categories=self.recipe_categories,
            placeholder="Search by finished unit name...",
        )
        self.search_bar.grid(
            row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM)
        )

    def _create_action_buttons(self):
        """Create action buttons (read-only mode - info label only)."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

        # Info label explaining where to manage yield types
        info_label = ctk.CTkLabel(
            button_frame,
            text="Yield types are managed in Recipe Edit. Double-click to open recipe.",
            text_color="gray50",
            font=ctk.CTkFont(size=12, slant="italic"),
        )
        info_label.grid(row=0, column=0, padx=PADDING_MEDIUM, sticky="w")

    def _create_data_table(self):
        """Create the data table for displaying finished units using ttk.Treeview."""
        # Container frame for grid and scrollbar
        self.grid_container = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_container.grid(
            row=2, column=0, sticky="nsew",
            padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )
        self.grid_container.grid_columnconfigure(0, weight=1)
        self.grid_container.grid_rowconfigure(0, weight=1)

        # Define columns: Name, Recipe, Category, Yield (removed Type column)
        columns = ("name", "recipe", "category", "yield")
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
            "recipe", text="Recipe", anchor="w",
            command=lambda: self._on_header_click("recipe")
        )
        self.tree.heading(
            "category", text="Category", anchor="w",
            command=lambda: self._on_header_click("category")
        )
        self.tree.heading(
            "yield", text="Yield", anchor="w",
            command=lambda: self._on_header_click("yield")
        )

        # Configure column widths
        self.tree.column("name", width=280, minwidth=150)
        self.tree.column("recipe", width=220, minwidth=120)
        self.tree.column("category", width=120, minwidth=80)
        self.tree.column("yield", width=180, minwidth=100)

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
            fu_id = int(selection[0])
            finished_unit = self._get_finished_unit_by_id(fu_id)
            self._on_row_select(finished_unit)
        else:
            self._on_row_select(None)

    def _on_tree_double_click(self, event):
        """Handle double-click on finished unit row."""
        selection = self.tree.selection()
        if selection:
            fu_id = int(selection[0])
            finished_unit = self._get_finished_unit_by_id(fu_id)
            if finished_unit:
                self._on_row_double_click(finished_unit)

    def _get_finished_unit_by_id(self, fu_id: int) -> Optional[FinishedUnit]:
        """Find finished unit by ID in current data."""
        return next(
            (fu for fu in self._current_finished_units if fu.id == fu_id),
            None
        )

    def _refresh_tree_display(self):
        """Refresh the tree display with current finished units, sorting, and variant grouping."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        finished_units = self._current_finished_units
        if not finished_units:
            return

        # Separate base FUs (from base recipes) and variant FUs (from variant recipes)
        base_fus = [fu for fu in finished_units if not fu.recipe or fu.recipe.base_recipe_id is None]
        variant_fus = [fu for fu in finished_units if fu.recipe and fu.recipe.base_recipe_id is not None]

        # Sort base FUs by current sort column
        base_fus = self._sort_finished_units(base_fus)

        # Group variants by their recipe's base_recipe_id
        variants_by_base_recipe = {}
        for vfu in variant_fus:
            base_recipe_id = vfu.recipe.base_recipe_id
            if base_recipe_id not in variants_by_base_recipe:
                variants_by_base_recipe[base_recipe_id] = []
            variants_by_base_recipe[base_recipe_id].append(vfu)

        # Sort variants within each group
        for base_id in variants_by_base_recipe:
            variants_by_base_recipe[base_id] = self._sort_finished_units(variants_by_base_recipe[base_id])

        # Track which base recipes we've added variants for
        processed_base_recipes = set()

        # Insert into tree: base FU, then variants of that FU's recipe
        for fu in base_fus:
            self._insert_finished_unit_row(fu, is_variant=False)
            # Insert variant FUs that belong to variants of this FU's recipe
            if fu.recipe:
                base_recipe_id = fu.recipe.id
                if base_recipe_id in variants_by_base_recipe and base_recipe_id not in processed_base_recipes:
                    for vfu in variants_by_base_recipe[base_recipe_id]:
                        self._insert_finished_unit_row(vfu, is_variant=True)
                    processed_base_recipes.add(base_recipe_id)

        # Add any orphaned variant FUs (their base recipe was deleted)
        for base_id, vfus in variants_by_base_recipe.items():
            if base_id not in processed_base_recipes:
                for vfu in vfus:
                    self._insert_finished_unit_row(vfu, is_variant=True)

    def _sort_finished_units(self, finished_units: List[FinishedUnit]) -> List[FinishedUnit]:
        """Sort finished units by current sort column."""
        def get_sort_key(fu):
            if self.sort_column == "name":
                return (fu.display_name or "").lower()
            elif self.sort_column == "recipe":
                return (fu.recipe.name if fu.recipe else "").lower()
            elif self.sort_column == "category":
                return (fu.category or "").lower()
            elif self.sort_column == "yield":
                return fu.items_per_batch or 0
            return ""

        return sorted(finished_units, key=get_sort_key, reverse=not self.sort_ascending)

    def _insert_finished_unit_row(self, fu: FinishedUnit, is_variant: bool):
        """Insert a finished unit row into the tree."""
        # Name with variant prefix
        name = fu.display_name or ""
        if is_variant:
            name = f"↳ {name}"

        # Recipe name
        recipe_name = fu.recipe.name if fu.recipe else "N/A"

        # Category
        category = fu.category or ""

        # Yield display (includes yield_type for context)
        yield_type = getattr(fu, "yield_type", "SERVING") or "SERVING"
        if fu.yield_mode.value == "discrete_count":
            yield_display = f"{fu.items_per_batch or 0} {fu.item_unit or 'each'}/batch ({yield_type})"
        else:
            yield_display = f"{fu.batch_percentage or 0}% of batch ({yield_type})"

        values = (name, recipe_name, category, yield_display)
        self.tree.insert("", "end", iid=str(fu.id), values=values)

    def _create_status_bar(self):
        """Create status bar for displaying info."""
        self.status_frame = ctk.CTkFrame(self, height=30)
        self.status_frame.grid(
            row=3, column=0, sticky="ew", padx=PADDING_LARGE, pady=(0, PADDING_LARGE)
        )
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text=StatusMessages.READY,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

    def _on_search(
        self, search_text: str, category: Optional[str] = None, recipe_id: Optional[int] = None
    ) -> None:
        """
        Handle search and filter.

        Args:
            search_text: Search query
            category: Selected category filter
            recipe_id: Selected recipe filter (None for all recipes)
        """
        # Determine category filter
        category_filter = None
        if category and category != "All Categories":
            category_filter = category

        # Get filtered finished units with service integration
        try:
            finished_units = self.service_integrator.execute_service_operation(
                operation_name="Search Finished Units",
                operation_type=OperationType.SEARCH,
                service_function=lambda: finished_unit_service.get_all_finished_units(
                    name_search=search_text if search_text else None,
                    category=category_filter,
                    recipe_id=recipe_id,
                ),
                parent_widget=self,
                error_context="Searching finished units",
                log_level=logging.DEBUG,  # Reduce log noise for frequent operations
            )

            # Store finished units for selection lookup and refresh display
            self._current_finished_units = finished_units
            self._refresh_tree_display()
            self._update_status(StatusMessages.found_units(len(finished_units)))

        except (ServiceError, Exception):
            # Error already handled by service integrator
            logging.exception("Search operation failed after service integrator handling")
            self._update_status(StatusMessages.SEARCH_FAILED, error=True)

    def _on_row_select(self, finished_unit: Optional[FinishedUnit]) -> None:
        """
        Handle row selection.

        Args:
            finished_unit: Selected finished unit (None if deselected)
        """
        self.selected_finished_unit = finished_unit

        if finished_unit:
            self._update_status(StatusMessages.selected_unit(finished_unit.display_name))
        else:
            self._update_status(StatusMessages.READY)

    def _on_row_double_click(self, finished_unit: FinishedUnit) -> None:
        """
        Handle row double-click (opens parent recipe for editing).

        Args:
            finished_unit: Double-clicked finished unit
        """
        self.selected_finished_unit = finished_unit

        # Open the parent recipe for editing
        if finished_unit.recipe_id:
            self._open_recipe_edit(finished_unit.recipe_id)
        else:
            show_error(
                "No Recipe", "This finished unit does not have an associated recipe.", parent=self
            )

    def _open_recipe_edit(self, recipe_id: int):
        """
        Open the Recipe Edit dialog for the parent recipe and persist changes.

        Args:
            recipe_id: ID of the recipe to edit
        """
        from src.services import recipe_service
        from src.services import finished_unit_service
        from src.ui.forms.recipe_form import RecipeFormDialog
        from src.ui.widgets.dialogs import show_success

        try:
            recipe = recipe_service.get_recipe(recipe_id)
            if not recipe:
                show_error("Recipe Not Found", "The parent recipe could not be found.", parent=self)
                return

            dialog = RecipeFormDialog(self, recipe=recipe, title=f"Edit Recipe: {recipe.name}")
            self.wait_window(dialog)
            result = dialog.result

            if result:
                # Persist changes (F044 fix: actually save the recipe and yield types)
                try:
                    # Extract ingredients and yield types from result
                    ingredients = result.pop("ingredients", [])
                    result.pop("pending_components", [])  # Not used for edits
                    yield_types = result.pop("yield_types", [])

                    # Map prep_time to estimated_time_minutes
                    if "prep_time" in result:
                        result["estimated_time_minutes"] = result.pop("prep_time")

                    # Update recipe
                    updated_recipe = recipe_service.update_recipe(
                        recipe_id,
                        result,
                        ingredients,
                    )

                    # Save yield types
                    self._save_yield_types_from_catalog(recipe_id, yield_types)

                    show_success(
                        "Success",
                        f"Recipe '{updated_recipe.name}' updated successfully",
                        parent=self,
                    )
                except ServiceError as e:
                    logging.exception(f"Failed to save recipe changes: {e}")
                    handle_error(e, parent=self, operation="Save recipe changes")
                except Exception as e:
                    logging.exception(f"Failed to save recipe changes: {e}")
                    handle_error(e, parent=self, operation="Save recipe changes")

                # Refresh the finished units list since recipe may have changed
                self.refresh()

        except ServiceError as e:
            logging.exception("Failed to open recipe edit dialog")
            handle_error(e, parent=self, operation="Open recipe")
        except Exception as e:
            logging.exception("Failed to open recipe edit dialog")
            handle_error(e, parent=self, operation="Open recipe")

    def _save_yield_types_from_catalog(self, recipe_id: int, yield_types: list):
        """
        Persist yield type changes for a recipe (called from catalog double-click edit).

        Handles:
        - Creating new yield types (id=None)
        - Updating existing yield types (id set)
        - Deleting removed yield types

        Raises:
            Exception: If yield type persistence fails (not swallowed)
        """
        from src.services import finished_unit_service

        # Get existing yield types for this recipe
        existing_units = finished_unit_service.get_units_by_recipe(recipe_id)
        existing_ids = {unit.id for unit in existing_units}

        # Track which IDs we're keeping
        keeping_ids = set()

        for data in yield_types:
            if data["id"] is None:
                # Create new
                finished_unit_service.create_finished_unit(
                    display_name=data["display_name"],
                    recipe_id=recipe_id,
                    item_unit=data.get("item_unit"),
                    items_per_batch=data["items_per_batch"],
                )
            else:
                # Update existing
                keeping_ids.add(data["id"])
                finished_unit_service.update_finished_unit(
                    data["id"],
                    display_name=data["display_name"],
                    item_unit=data.get("item_unit"),
                    items_per_batch=data["items_per_batch"],
                )

        # Delete removed yield types
        for unit in existing_units:
            if unit.id not in keeping_ids:
                finished_unit_service.delete_finished_unit(unit.id)

    def refresh(self):
        """
        Refresh the finished units list and category filter.

        Note: This performs a full refresh which is inefficient for large datasets.
        Consider using incremental update methods for better performance.
        """
        try:
            # Reload categories in case new recipes/categories were added
            self.recipe_categories = self._load_recipe_categories()
            self.search_bar.update_categories(self.recipe_categories)

            finished_units = self.service_integrator.execute_service_operation(
                operation_name="Load All Finished Units",
                operation_type=OperationType.READ,
                service_function=lambda: finished_unit_service.get_all_finished_units(),
                parent_widget=self,
                error_context="Loading finished units",
                log_level=logging.DEBUG,  # Reduce log noise for frequent operations
            )

            # Store finished units for selection lookup and refresh display
            self._current_finished_units = finished_units
            self._refresh_tree_display()
            self._update_status(StatusMessages.loaded_units(len(finished_units)))

        except (ServiceError, Exception):
            # Error already handled by service integrator
            logging.exception(
                "Load finished units operation failed after service integrator handling"
            )
            self._update_status(StatusMessages.FAILED_TO_LOAD, error=True)

    def _update_status(self, message: str, success: bool = False, error: bool = False):
        """
        Update status bar message.

        Args:
            message: Status message
            success: Whether this is a success message (green)
            error: Whether this is an error message (red)
        """
        self.status_label.configure(text=message)

        # Set color based on message type
        if success:
            self.status_label.configure(text_color=COLOR_SUCCESS)
        elif error:
            self.status_label.configure(text_color=COLOR_ERROR)
        else:
            self.status_label.configure(text_color=("gray10", "gray90"))  # Default theme colors
