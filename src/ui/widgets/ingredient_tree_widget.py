"""
Ingredient tree widget for hierarchical ingredient selection.

This module provides a reusable tree selection widget for navigating the
ingredient hierarchy (root categories -> mid-tier groups -> leaf ingredients).

Features:
- Lazy loading of children for performance with 500+ ingredients
- Search with auto-expand of matching branches
- Breadcrumb display showing path to selected item
- Leaf-only selection mode for recipe ingredient context
- Visual distinction between categories and leaf ingredients

Usage:
    from src.ui.widgets.ingredient_tree_widget import IngredientTreeWidget

    tree = IngredientTreeWidget(
        master=frame,
        on_select_callback=on_ingredient_selected,
        leaf_only=True  # For recipe dialogs
    )
"""

import customtkinter as ctk
from tkinter import ttk
from typing import Callable, Optional, List, Dict, Any


# Placeholder ID for nodes that haven't had children loaded yet
_PLACEHOLDER_ID = "__placeholder__"


class IngredientTreeWidget(ctk.CTkFrame):
    """
    Tree widget for hierarchical ingredient selection.

    Wraps ttk.Treeview in a CTkFrame for CustomTkinter compatibility.
    Supports lazy loading, search, breadcrumbs, and leaf-only selection.
    """

    def __init__(
        self,
        master: Any,
        on_select_callback: Optional[Callable[[Dict], None]] = None,
        leaf_only: bool = False,
        show_search: bool = True,
        show_breadcrumb: bool = True,
        **kwargs,
    ):
        """
        Initialize the IngredientTreeWidget.

        Args:
            master: Parent widget
            on_select_callback: Callback invoked with ingredient dict on selection
            leaf_only: If True, only leaf ingredients (level=2) can be selected
            show_search: If True, display search bar above tree
            show_breadcrumb: If True, display breadcrumb below tree
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, **kwargs)

        self.on_select_callback = on_select_callback
        self.leaf_only = leaf_only
        self.show_search = show_search
        self.show_breadcrumb = show_breadcrumb

        # Track loaded nodes to avoid reloading
        self._loaded_nodes: set = set()

        # Track item data by tree item ID
        self._item_data: Dict[str, Dict] = {}

        # Search debounce
        self._search_after_id: Optional[str] = None
        self._search_debounce_ms: int = 300

        # Service stub flag - set to False to use real hierarchy service
        self._use_stub_data: bool = False

        self._setup_ui()
        self._setup_styles()
        self._load_roots()

    def _setup_ui(self) -> None:
        """Set up the widget UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        row = 0

        # Search bar (optional)
        if self.show_search:
            self._search_frame = ctk.CTkFrame(self, fg_color="transparent")
            self._search_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=(5, 5))
            self._search_frame.grid_columnconfigure(0, weight=1)

            self._search_entry = ctk.CTkEntry(
                self._search_frame,
                placeholder_text="Search ingredients...",
                height=30,
            )
            self._search_entry.grid(row=0, column=0, sticky="ew")
            self._search_entry.bind("<KeyRelease>", self._on_search_key_release)

            self._clear_search_btn = ctk.CTkButton(
                self._search_frame,
                text="Clear",
                width=60,
                height=30,
                command=self._clear_search,
            )
            self._clear_search_btn.grid(row=0, column=1, padx=(5, 0))

            row += 1

        # Tree container frame
        self._tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._tree_frame.grid(row=row, column=0, sticky="nsew", padx=5, pady=5)
        self._tree_frame.grid_columnconfigure(0, weight=1)
        self._tree_frame.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(row, weight=1)
        row += 1

        # Treeview widget
        self._tree = ttk.Treeview(
            self._tree_frame,
            selectmode="browse",
            show="tree",  # Hide column headers
        )
        self._tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        self._scrollbar = ttk.Scrollbar(
            self._tree_frame,
            orient="vertical",
            command=self._tree.yview,
        )
        self._scrollbar.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=self._scrollbar.set)

        # Bind events
        self._tree.bind("<<TreeviewOpen>>", self._on_item_expand)
        self._tree.bind("<<TreeviewSelect>>", self._on_item_select)

        # Breadcrumb label (optional)
        if self.show_breadcrumb:
            self._breadcrumb_label = ctk.CTkLabel(
                self,
                text="",
                anchor="w",
                text_color=("gray40", "gray60"),
                font=ctk.CTkFont(size=11),
            )
            self._breadcrumb_label.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 5))
            row += 1

    def _setup_styles(self) -> None:
        """Configure ttk styles for tree appearance."""
        style = ttk.Style()

        # Get current CustomTkinter appearance mode
        appearance_mode = ctk.get_appearance_mode().lower()

        if appearance_mode == "dark":
            bg_color = "#2b2b2b"
            fg_color = "#DCE4EE"
            select_bg = "#1f538d"
            select_fg = "#ffffff"
        else:
            bg_color = "#ffffff"
            fg_color = "#1a1a1a"
            select_bg = "#1f538d"
            select_fg = "#ffffff"

        # Configure Treeview style
        style.configure(
            "Ingredient.Treeview",
            background=bg_color,
            foreground=fg_color,
            fieldbackground=bg_color,
            rowheight=25,
        )
        style.map(
            "Ingredient.Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", select_fg)],
        )

        self._tree.configure(style="Ingredient.Treeview")

        # Define tags for visual distinction
        # Categories (level 0, 1) - slightly grayed, bold
        self._tree.tag_configure(
            "category",
            foreground="gray50" if appearance_mode == "light" else "gray60",
        )
        # Leaf items (level 2) - normal text
        self._tree.tag_configure(
            "leaf",
            foreground=fg_color,
        )
        # Non-selectable (in leaf_only mode) - italic and grayed
        self._tree.tag_configure(
            "non_selectable",
            foreground="gray60" if appearance_mode == "light" else "gray50",
        )
        # Search match highlight
        self._tree.tag_configure(
            "search_match",
            background="#ffeb3b" if appearance_mode == "light" else "#5d4d00",
        )

    def _load_roots(self) -> None:
        """Load root-level ingredients into the tree."""
        roots = self._get_root_ingredients()

        for root in roots:
            item_id = self._insert_item("", root)
            # Add placeholder child to show expand arrow
            if root.get("has_children", True):
                self._tree.insert(item_id, "end", iid=f"{item_id}{_PLACEHOLDER_ID}", text="")

    def _insert_item(self, parent_id: str, ingredient: Dict) -> str:
        """
        Insert an ingredient into the tree.

        Args:
            parent_id: Parent tree item ID (empty string for root)
            ingredient: Ingredient dictionary

        Returns:
            The tree item ID
        """
        # Generate unique item ID
        item_id = str(ingredient.get("id", id(ingredient)))

        # Determine display text and tags
        display_name = ingredient.get("display_name", "Unknown")
        hierarchy_level = ingredient.get("hierarchy_level", 2)
        is_leaf = hierarchy_level == 2

        # Determine visual tags
        tags = []
        if is_leaf:
            tags.append("leaf")
            prefix = "    "  # Indent for visual distinction (no folder icon)
        else:
            tags.append("category")
            prefix = "[+] " if hierarchy_level == 0 else "  [>] "

        # In leaf_only mode, mark non-leaves as non-selectable
        if self.leaf_only and not is_leaf:
            tags.append("non_selectable")

        # Insert into tree
        self._tree.insert(
            parent_id,
            "end",
            iid=item_id,
            text=f"{prefix}{display_name}",
            open=False,
            tags=tags,
        )

        # Store item data
        self._item_data[item_id] = ingredient

        return item_id

    def _on_item_expand(self, event) -> None:
        """Handle tree item expansion - lazy load children."""
        selected_items = self._tree.selection()
        if not selected_items:
            # Get the item being expanded from focus
            item_id = self._tree.focus()
        else:
            item_id = selected_items[0]

        if not item_id:
            return

        # Check if already loaded
        if item_id in self._loaded_nodes:
            return

        # Mark as loaded
        self._loaded_nodes.add(item_id)

        # Remove placeholder
        placeholder_id = f"{item_id}{_PLACEHOLDER_ID}"
        if self._tree.exists(placeholder_id):
            self._tree.delete(placeholder_id)

        # Get ingredient data
        ingredient = self._item_data.get(item_id)
        if not ingredient:
            return

        # Load children
        children = self._get_children(ingredient.get("id"))

        for child in children:
            child_item_id = self._insert_item(item_id, child)
            # Add placeholder for non-leaf children
            if child.get("hierarchy_level", 2) < 2:
                self._tree.insert(
                    child_item_id,
                    "end",
                    iid=f"{child_item_id}{_PLACEHOLDER_ID}",
                    text="",
                )

    def _on_item_select(self, event) -> None:
        """Handle tree item selection."""
        selected_items = self._tree.selection()
        if not selected_items:
            return

        item_id = selected_items[0]
        ingredient = self._item_data.get(item_id)
        if not ingredient:
            return

        # Update breadcrumb
        if self.show_breadcrumb:
            self._update_breadcrumb(ingredient)

        # Check if selection is allowed
        is_leaf = ingredient.get("hierarchy_level", 2) == 2
        if self.leaf_only and not is_leaf:
            # In leaf-only mode, expand non-leaf items instead of selecting
            if not self._tree.item(item_id, "open"):
                self._tree.item(item_id, open=True)
                self._on_item_expand(event)
            return

        # Invoke callback
        if self.on_select_callback:
            self.on_select_callback(ingredient)

    def _update_breadcrumb(self, ingredient: Dict) -> None:
        """Update the breadcrumb display for the selected ingredient."""
        if not self.show_breadcrumb:
            return

        ancestors = self._get_ancestors(ingredient.get("id"))

        # Build path: ancestors (reversed to go root->leaf) + current item
        path_parts = [a.get("display_name", "?") for a in reversed(ancestors)]
        path_parts.append(ingredient.get("display_name", "?"))

        breadcrumb_text = " > ".join(path_parts)
        self._breadcrumb_label.configure(text=breadcrumb_text)

    def _on_search_key_release(self, event) -> None:
        """Handle key release in search entry with debounce."""
        # Cancel pending search
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
            self._search_after_id = None

        # Schedule new search
        self._search_after_id = self.after(
            self._search_debounce_ms,
            self._perform_search,
        )

    def _perform_search(self) -> None:
        """Execute the search and expand matching branches."""
        query = self._search_entry.get().strip()

        # Clear previous highlights
        self._clear_search_highlights()

        if not query or len(query) < 2:
            return

        # Search for matches
        matches = self._search_ingredients(query)

        if not matches:
            return

        # Process matches and find first one to select
        first_match_id = self._process_search_matches(matches)

        # Select and scroll to first match
        if first_match_id:
            self._tree.selection_set(first_match_id)
            self._tree.focus(first_match_id)
            self._tree.see(first_match_id)

    def _clear_search_highlights(self) -> None:
        """Clear search_match tag from all items."""
        for item_id in self._item_data:
            if self._tree.exists(item_id):
                current_tags = list(self._tree.item(item_id, "tags"))
                if "search_match" in current_tags:
                    current_tags.remove("search_match")
                    self._tree.item(item_id, tags=current_tags)

    def _process_search_matches(self, matches: List[Dict]) -> Optional[str]:
        """
        Process search matches: load ancestors, highlight items.

        Returns the first match ID for selection, or None.
        """
        first_match_id = None
        for match in matches:
            match_id = str(match.get("id"))

            # Ensure item exists in tree (may need to load ancestors)
            ancestors = match.get("ancestors", [])
            self._ensure_ancestors_loaded(ancestors)

            # Ensure the match item itself is loaded
            self._ensure_match_loaded(match)

            # Highlight match if exists
            if self._tree.exists(match_id):
                self._add_search_highlight(match_id)
                if first_match_id is None:
                    first_match_id = match_id

        return first_match_id

    def _ensure_match_loaded(self, match: Dict) -> None:
        """Ensure a search match item is loaded into the tree."""
        match_id = str(match.get("id"))
        if self._tree.exists(match_id):
            return

        # Need to load it - find its parent
        parent_id = str(match.get("parent_ingredient_id", ""))
        if parent_id and self._tree.exists(parent_id):
            self._load_node_children(parent_id)

    def _add_search_highlight(self, item_id: str) -> None:
        """Add search_match tag to an item."""
        current_tags = list(self._tree.item(item_id, "tags"))
        if "search_match" not in current_tags:
            current_tags.append("search_match")
            self._tree.item(item_id, tags=current_tags)

    def _ensure_ancestors_loaded(self, ancestors: List[Dict]) -> None:
        """Ensure all ancestor nodes are loaded and expanded."""
        # Process from root to leaf
        for ancestor in reversed(ancestors):
            ancestor_id = str(ancestor.get("id"))

            # If not in tree yet, we need to find its parent and load
            if not self._tree.exists(ancestor_id):
                # Try to load from parent
                parent_id = str(ancestor.get("parent_ingredient_id", ""))
                if parent_id and self._tree.exists(parent_id):
                    self._load_node_children(parent_id)

            # Expand the node
            if self._tree.exists(ancestor_id):
                if not self._tree.item(ancestor_id, "open"):
                    self._tree.item(ancestor_id, open=True)
                self._load_node_children(ancestor_id)

    def _load_node_children(self, node_id: str) -> None:
        """Load children for a specific node if not already loaded."""
        if node_id in self._loaded_nodes:
            return

        self._loaded_nodes.add(node_id)

        # Remove placeholder
        placeholder_id = f"{node_id}{_PLACEHOLDER_ID}"
        if self._tree.exists(placeholder_id):
            self._tree.delete(placeholder_id)

        # Get ingredient data
        ingredient = self._item_data.get(node_id)
        if not ingredient:
            return

        # Load children
        children = self._get_children(ingredient.get("id"))

        for child in children:
            child_item_id = self._insert_item(node_id, child)
            if child.get("hierarchy_level", 2) < 2:
                self._tree.insert(
                    child_item_id,
                    "end",
                    iid=f"{child_item_id}{_PLACEHOLDER_ID}",
                    text="",
                )

    def _clear_search(self) -> None:
        """Clear the search entry and highlights."""
        if self.show_search:
            self._search_entry.delete(0, "end")

        # Clear highlights
        for item_id in self._item_data:
            if self._tree.exists(item_id):
                current_tags = list(self._tree.item(item_id, "tags"))
                if "search_match" in current_tags:
                    current_tags.remove("search_match")
                    self._tree.item(item_id, tags=current_tags)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_selected_ingredient(self) -> Optional[Dict]:
        """
        Get the currently selected ingredient.

        Returns:
            Ingredient dictionary or None if nothing selected
        """
        selected = self._tree.selection()
        if not selected:
            return None

        item_id = selected[0]
        return self._item_data.get(item_id)

    def select_ingredient(self, ingredient_id: int) -> bool:
        """
        Programmatically select an ingredient by ID.

        Args:
            ingredient_id: The ingredient ID to select

        Returns:
            True if ingredient was found and selected, False otherwise
        """
        item_id = str(ingredient_id)

        # First, try to find it in loaded items
        if item_id in self._item_data:
            if self._tree.exists(item_id):
                self._tree.selection_set(item_id)
                self._tree.focus(item_id)
                self._tree.see(item_id)
                return True

        # Need to load ancestors first
        ancestors = self._get_ancestors(ingredient_id)
        self._ensure_ancestors_loaded(ancestors)

        # Try to find and load the item's parent
        if ancestors:
            parent_id = str(ancestors[0].get("id"))
            if self._tree.exists(parent_id):
                self._load_node_children(parent_id)

        # Now try to select
        if self._tree.exists(item_id):
            self._tree.selection_set(item_id)
            self._tree.focus(item_id)
            self._tree.see(item_id)
            return True

        return False

    def refresh(self) -> None:
        """Refresh the tree by reloading all data."""
        # Clear current tree
        self._tree.delete(*self._tree.get_children())
        self._loaded_nodes.clear()
        self._item_data.clear()

        # Reload roots
        self._load_roots()

        # Clear breadcrumb
        if self.show_breadcrumb:
            self._breadcrumb_label.configure(text="")

    def set_leaf_only(self, leaf_only: bool) -> None:
        """
        Change the leaf-only selection mode.

        Args:
            leaf_only: If True, only leaf ingredients can be selected
        """
        self.leaf_only = leaf_only
        self.refresh()

    def search(self, query: str) -> None:
        """
        Perform a search from external trigger.

        Args:
            query: Search query string
        """
        # Update internal search entry if visible
        if self.show_search:
            self._search_entry.delete(0, "end")
            self._search_entry.insert(0, query)

        # Clear previous highlights
        self._clear_search_highlights()

        if not query or len(query) < 2:
            return

        # Search for matches
        matches = self._search_ingredients(query)

        if not matches:
            return

        # Process matches and find first one to select
        first_match_id = self._process_search_matches(matches)

        # Select and scroll to first match
        if first_match_id:
            self._tree.selection_set(first_match_id)
            self._tree.focus(first_match_id)
            self._tree.see(first_match_id)

    def clear_search(self) -> None:
        """Clear search highlights and reset tree state."""
        self._clear_search()

    # -------------------------------------------------------------------------
    # Service Interface (Stubbed - Replace with real service calls)
    # -------------------------------------------------------------------------

    def _get_root_ingredients(self) -> List[Dict]:
        """
        Get root-level ingredients (hierarchy_level=0).

        Returns list of ingredient dicts with id, display_name, hierarchy_level, etc.
        """
        if self._use_stub_data:
            return self._stub_get_root_ingredients()

        from src.services import ingredient_hierarchy_service

        return ingredient_hierarchy_service.get_root_ingredients()

    def _get_children(self, parent_id: int) -> List[Dict]:
        """
        Get children of an ingredient.

        Returns list of ingredient dicts that are direct children of parent_id.
        """
        if self._use_stub_data:
            return self._stub_get_children(parent_id)

        from src.services import ingredient_hierarchy_service

        return ingredient_hierarchy_service.get_children(parent_id)

    def _get_ancestors(self, ingredient_id: int) -> List[Dict]:
        """
        Get ancestors of an ingredient (immediate parent to root).

        Returns list ordered from immediate parent to root.
        """
        if self._use_stub_data:
            return self._stub_get_ancestors(ingredient_id)

        from src.services import ingredient_hierarchy_service

        return ingredient_hierarchy_service.get_ancestors(ingredient_id)

    def _search_ingredients(self, query: str) -> List[Dict]:
        """
        Search ingredients by display name.

        Returns matching ingredients with their ancestors for tree expansion.
        """
        if self._use_stub_data:
            return self._stub_search_ingredients(query)

        from src.services import ingredient_hierarchy_service

        results = ingredient_hierarchy_service.search_ingredients(query, limit=50)
        # Add ancestors to each result for tree expansion
        for result in results:
            result["ancestors"] = ingredient_hierarchy_service.get_ancestors(result["id"])
        return results

    # -------------------------------------------------------------------------
    # Stub Data (for development without service layer)
    # -------------------------------------------------------------------------

    def _stub_get_root_ingredients(self) -> List[Dict]:
        """Return stub root ingredients for testing."""
        return [
            {
                "id": 1,
                "display_name": "Chocolate",
                "slug": "chocolate",
                "hierarchy_level": 0,
                "parent_ingredient_id": None,
                "has_children": True,
            },
            {
                "id": 11,
                "display_name": "Flour",
                "slug": "flour",
                "hierarchy_level": 0,
                "parent_ingredient_id": None,
                "has_children": True,
            },
            {
                "id": 21,
                "display_name": "Sugar",
                "slug": "sugar",
                "hierarchy_level": 0,
                "parent_ingredient_id": None,
                "has_children": True,
            },
            {
                "id": 31,
                "display_name": "Dairy",
                "slug": "dairy",
                "hierarchy_level": 0,
                "parent_ingredient_id": None,
                "has_children": True,
            },
            {
                "id": 41,
                "display_name": "Nuts",
                "slug": "nuts",
                "hierarchy_level": 0,
                "parent_ingredient_id": None,
                "has_children": True,
            },
        ]

    def _stub_get_children(self, parent_id: int) -> List[Dict]:
        """Return stub children for testing."""
        stub_children = {
            # Chocolate children (level 1)
            1: [
                {
                    "id": 2,
                    "display_name": "Dark Chocolate",
                    "slug": "dark_chocolate",
                    "hierarchy_level": 1,
                    "parent_ingredient_id": 1,
                },
                {
                    "id": 6,
                    "display_name": "Milk Chocolate",
                    "slug": "milk_chocolate",
                    "hierarchy_level": 1,
                    "parent_ingredient_id": 1,
                },
                {
                    "id": 9,
                    "display_name": "White Chocolate",
                    "slug": "white_chocolate",
                    "hierarchy_level": 1,
                    "parent_ingredient_id": 1,
                },
            ],
            # Dark Chocolate children (level 2 - leaves)
            2: [
                {
                    "id": 3,
                    "display_name": "Semi-Sweet Chocolate Chips",
                    "slug": "semi_sweet_chocolate_chips",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 2,
                },
                {
                    "id": 4,
                    "display_name": "Bittersweet Chocolate Chips",
                    "slug": "bittersweet_chocolate_chips",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 2,
                },
                {
                    "id": 5,
                    "display_name": "Dark Chocolate Bar 70%",
                    "slug": "dark_chocolate_bar_70",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 2,
                },
            ],
            # Milk Chocolate children (level 2 - leaves)
            6: [
                {
                    "id": 7,
                    "display_name": "Milk Chocolate Chips",
                    "slug": "milk_chocolate_chips",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 6,
                },
                {
                    "id": 8,
                    "display_name": "Milk Chocolate Bar",
                    "slug": "milk_chocolate_bar",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 6,
                },
            ],
            # White Chocolate children (level 2 - leaves)
            9: [
                {
                    "id": 10,
                    "display_name": "White Chocolate Chips",
                    "slug": "white_chocolate_chips",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 9,
                },
            ],
            # Flour children (level 1)
            11: [
                {
                    "id": 12,
                    "display_name": "Wheat Flour",
                    "slug": "wheat_flour",
                    "hierarchy_level": 1,
                    "parent_ingredient_id": 11,
                },
                {
                    "id": 16,
                    "display_name": "Alternative Flour",
                    "slug": "alternative_flour",
                    "hierarchy_level": 1,
                    "parent_ingredient_id": 11,
                },
            ],
            # Wheat Flour children (level 2 - leaves)
            12: [
                {
                    "id": 13,
                    "display_name": "All-Purpose Flour",
                    "slug": "all_purpose_flour",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 12,
                },
                {
                    "id": 14,
                    "display_name": "Bread Flour",
                    "slug": "bread_flour",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 12,
                },
                {
                    "id": 15,
                    "display_name": "Cake Flour",
                    "slug": "cake_flour",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 12,
                },
            ],
            # Alternative Flour children (level 2 - leaves)
            16: [
                {
                    "id": 17,
                    "display_name": "Almond Flour",
                    "slug": "almond_flour",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 16,
                },
                {
                    "id": 18,
                    "display_name": "Coconut Flour",
                    "slug": "coconut_flour",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 16,
                },
            ],
            # Sugar children (level 1)
            21: [
                {
                    "id": 22,
                    "display_name": "Granulated Sugar",
                    "slug": "granulated_sugar",
                    "hierarchy_level": 1,
                    "parent_ingredient_id": 21,
                },
                {
                    "id": 25,
                    "display_name": "Brown Sugar",
                    "slug": "brown_sugar",
                    "hierarchy_level": 1,
                    "parent_ingredient_id": 21,
                },
            ],
            # Granulated Sugar children (level 2 - leaves)
            22: [
                {
                    "id": 23,
                    "display_name": "White Sugar",
                    "slug": "white_sugar",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 22,
                },
                {
                    "id": 24,
                    "display_name": "Superfine Sugar",
                    "slug": "superfine_sugar",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 22,
                },
            ],
            # Brown Sugar children (level 2 - leaves)
            25: [
                {
                    "id": 26,
                    "display_name": "Light Brown Sugar",
                    "slug": "light_brown_sugar",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 25,
                },
                {
                    "id": 27,
                    "display_name": "Dark Brown Sugar",
                    "slug": "dark_brown_sugar",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 25,
                },
            ],
            # Dairy children (level 1)
            31: [
                {
                    "id": 32,
                    "display_name": "Butter",
                    "slug": "butter",
                    "hierarchy_level": 1,
                    "parent_ingredient_id": 31,
                },
                {
                    "id": 35,
                    "display_name": "Milk",
                    "slug": "milk",
                    "hierarchy_level": 1,
                    "parent_ingredient_id": 31,
                },
            ],
            # Butter children (level 2 - leaves)
            32: [
                {
                    "id": 33,
                    "display_name": "Unsalted Butter",
                    "slug": "unsalted_butter",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 32,
                },
                {
                    "id": 34,
                    "display_name": "Salted Butter",
                    "slug": "salted_butter",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 32,
                },
            ],
            # Milk children (level 2 - leaves)
            35: [
                {
                    "id": 36,
                    "display_name": "Whole Milk",
                    "slug": "whole_milk",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 35,
                },
                {
                    "id": 37,
                    "display_name": "Heavy Cream",
                    "slug": "heavy_cream",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 35,
                },
            ],
            # Nuts children (level 1)
            41: [
                {
                    "id": 42,
                    "display_name": "Tree Nuts",
                    "slug": "tree_nuts",
                    "hierarchy_level": 1,
                    "parent_ingredient_id": 41,
                },
                {
                    "id": 46,
                    "display_name": "Peanuts",
                    "slug": "peanuts",
                    "hierarchy_level": 1,
                    "parent_ingredient_id": 41,
                },
            ],
            # Tree Nuts children (level 2 - leaves)
            42: [
                {
                    "id": 43,
                    "display_name": "Walnuts",
                    "slug": "walnuts",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 42,
                },
                {
                    "id": 44,
                    "display_name": "Pecans",
                    "slug": "pecans",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 42,
                },
                {
                    "id": 45,
                    "display_name": "Almonds",
                    "slug": "almonds",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 42,
                },
            ],
            # Peanuts children (level 2 - leaves)
            46: [
                {
                    "id": 47,
                    "display_name": "Roasted Peanuts",
                    "slug": "roasted_peanuts",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 46,
                },
                {
                    "id": 48,
                    "display_name": "Peanut Butter",
                    "slug": "peanut_butter",
                    "hierarchy_level": 2,
                    "parent_ingredient_id": 46,
                },
            ],
        }
        return stub_children.get(parent_id, [])

    def _stub_get_ancestors(self, ingredient_id: int) -> List[Dict]:
        """Return stub ancestors (parent -> root order) for testing."""
        # Build ancestor lookup from stub data
        stub_ancestors = {
            # Level 2 -> their ancestors
            3: [
                {"id": 2, "display_name": "Dark Chocolate", "parent_ingredient_id": 1},
                {"id": 1, "display_name": "Chocolate", "parent_ingredient_id": None},
            ],
            4: [
                {"id": 2, "display_name": "Dark Chocolate", "parent_ingredient_id": 1},
                {"id": 1, "display_name": "Chocolate", "parent_ingredient_id": None},
            ],
            5: [
                {"id": 2, "display_name": "Dark Chocolate", "parent_ingredient_id": 1},
                {"id": 1, "display_name": "Chocolate", "parent_ingredient_id": None},
            ],
            7: [
                {"id": 6, "display_name": "Milk Chocolate", "parent_ingredient_id": 1},
                {"id": 1, "display_name": "Chocolate", "parent_ingredient_id": None},
            ],
            8: [
                {"id": 6, "display_name": "Milk Chocolate", "parent_ingredient_id": 1},
                {"id": 1, "display_name": "Chocolate", "parent_ingredient_id": None},
            ],
            10: [
                {"id": 9, "display_name": "White Chocolate", "parent_ingredient_id": 1},
                {"id": 1, "display_name": "Chocolate", "parent_ingredient_id": None},
            ],
            13: [
                {"id": 12, "display_name": "Wheat Flour", "parent_ingredient_id": 11},
                {"id": 11, "display_name": "Flour", "parent_ingredient_id": None},
            ],
            14: [
                {"id": 12, "display_name": "Wheat Flour", "parent_ingredient_id": 11},
                {"id": 11, "display_name": "Flour", "parent_ingredient_id": None},
            ],
            15: [
                {"id": 12, "display_name": "Wheat Flour", "parent_ingredient_id": 11},
                {"id": 11, "display_name": "Flour", "parent_ingredient_id": None},
            ],
            17: [
                {"id": 16, "display_name": "Alternative Flour", "parent_ingredient_id": 11},
                {"id": 11, "display_name": "Flour", "parent_ingredient_id": None},
            ],
            18: [
                {"id": 16, "display_name": "Alternative Flour", "parent_ingredient_id": 11},
                {"id": 11, "display_name": "Flour", "parent_ingredient_id": None},
            ],
            # Level 1 -> their ancestors
            2: [{"id": 1, "display_name": "Chocolate", "parent_ingredient_id": None}],
            6: [{"id": 1, "display_name": "Chocolate", "parent_ingredient_id": None}],
            9: [{"id": 1, "display_name": "Chocolate", "parent_ingredient_id": None}],
            12: [{"id": 11, "display_name": "Flour", "parent_ingredient_id": None}],
            16: [{"id": 11, "display_name": "Flour", "parent_ingredient_id": None}],
        }
        return stub_ancestors.get(ingredient_id, [])

    def _stub_search_ingredients(self, query: str) -> List[Dict]:
        """Return stub search results for testing."""
        query_lower = query.lower()

        # All stub items for searching
        all_items = [
            {
                "id": 3,
                "display_name": "Semi-Sweet Chocolate Chips",
                "hierarchy_level": 2,
                "parent_ingredient_id": 2,
            },
            {
                "id": 4,
                "display_name": "Bittersweet Chocolate Chips",
                "hierarchy_level": 2,
                "parent_ingredient_id": 2,
            },
            {
                "id": 5,
                "display_name": "Dark Chocolate Bar 70%",
                "hierarchy_level": 2,
                "parent_ingredient_id": 2,
            },
            {
                "id": 7,
                "display_name": "Milk Chocolate Chips",
                "hierarchy_level": 2,
                "parent_ingredient_id": 6,
            },
            {
                "id": 8,
                "display_name": "Milk Chocolate Bar",
                "hierarchy_level": 2,
                "parent_ingredient_id": 6,
            },
            {
                "id": 10,
                "display_name": "White Chocolate Chips",
                "hierarchy_level": 2,
                "parent_ingredient_id": 9,
            },
            {
                "id": 13,
                "display_name": "All-Purpose Flour",
                "hierarchy_level": 2,
                "parent_ingredient_id": 12,
            },
            {
                "id": 14,
                "display_name": "Bread Flour",
                "hierarchy_level": 2,
                "parent_ingredient_id": 12,
            },
            {
                "id": 15,
                "display_name": "Cake Flour",
                "hierarchy_level": 2,
                "parent_ingredient_id": 12,
            },
            {
                "id": 17,
                "display_name": "Almond Flour",
                "hierarchy_level": 2,
                "parent_ingredient_id": 16,
            },
            {
                "id": 18,
                "display_name": "Coconut Flour",
                "hierarchy_level": 2,
                "parent_ingredient_id": 16,
            },
            {
                "id": 23,
                "display_name": "White Sugar",
                "hierarchy_level": 2,
                "parent_ingredient_id": 22,
            },
            {
                "id": 24,
                "display_name": "Superfine Sugar",
                "hierarchy_level": 2,
                "parent_ingredient_id": 22,
            },
            {
                "id": 26,
                "display_name": "Light Brown Sugar",
                "hierarchy_level": 2,
                "parent_ingredient_id": 25,
            },
            {
                "id": 27,
                "display_name": "Dark Brown Sugar",
                "hierarchy_level": 2,
                "parent_ingredient_id": 25,
            },
            {
                "id": 33,
                "display_name": "Unsalted Butter",
                "hierarchy_level": 2,
                "parent_ingredient_id": 32,
            },
            {
                "id": 34,
                "display_name": "Salted Butter",
                "hierarchy_level": 2,
                "parent_ingredient_id": 32,
            },
            {
                "id": 36,
                "display_name": "Whole Milk",
                "hierarchy_level": 2,
                "parent_ingredient_id": 35,
            },
            {
                "id": 37,
                "display_name": "Heavy Cream",
                "hierarchy_level": 2,
                "parent_ingredient_id": 35,
            },
            {"id": 43, "display_name": "Walnuts", "hierarchy_level": 2, "parent_ingredient_id": 42},
            {"id": 44, "display_name": "Pecans", "hierarchy_level": 2, "parent_ingredient_id": 42},
            {"id": 45, "display_name": "Almonds", "hierarchy_level": 2, "parent_ingredient_id": 42},
            {
                "id": 47,
                "display_name": "Roasted Peanuts",
                "hierarchy_level": 2,
                "parent_ingredient_id": 46,
            },
            {
                "id": 48,
                "display_name": "Peanut Butter",
                "hierarchy_level": 2,
                "parent_ingredient_id": 46,
            },
        ]

        matches = []
        for item in all_items:
            if query_lower in item["display_name"].lower():
                # Add ancestors for breadcrumb/expansion
                item["ancestors"] = self._stub_get_ancestors(item["id"])
                matches.append(item)

        return matches
