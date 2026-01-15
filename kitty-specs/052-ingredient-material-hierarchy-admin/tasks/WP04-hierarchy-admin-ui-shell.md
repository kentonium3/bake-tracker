---
work_package_id: "WP04"
subtasks:
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
title: "Hierarchy Admin UI Shell"
phase: "Phase 3 - UI Shell"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-14T15:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Hierarchy Admin UI Shell

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: When you understand feedback and begin addressing it.
- **Report progress**: Update Activity Log as you address each item.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Create reusable tree admin window configurable for Ingredients or Materials with tree view, detail panel, and action button placeholders.

**Success Criteria**:
- Single `hierarchy_admin_window.py` with `entity_type` parameter
- Tree view displays 3-level hierarchy with expand/collapse
- Selection shows detail panel with item info and usage counts
- Action button placeholders visible (Add, Rename, Reparent)
- Window works for both Ingredient and Material modes

**User Story Reference**: User Stories 4, 5, 6 (spec.md) - Tree view and operations UI

## Context & Constraints

**Constitution Principles**:
- V. Layered Architecture: UI calls services; no direct database access
- II. User-Centric Design: UI must be intuitive

**Related Documents**:
- `kitty-specs/052-ingredient-material-hierarchy-admin/spec.md` - User Stories 4-6
- `kitty-specs/052-ingredient-material-hierarchy-admin/plan.md` - UI architecture

**Existing Code**:
- `src/ui/base_tab.py` - Base patterns for UI components
- `src/ui/ingredients_tab.py` - Existing ingredient UI patterns
- `src/ui/materials_tab.py` - Existing material UI patterns
- `src/services/ingredient_hierarchy_service.py` - Tree and usage methods (WP03)
- `src/services/material_hierarchy_service.py` - Tree and usage methods (WP03)

**Dependencies**: WP03 must be complete (needs tree and usage count services).

## Subtasks & Detailed Guidance

### Subtask T022 – Create hierarchy_admin_window.py as CTkToplevel window

- **Purpose**: Create the main admin window container.
- **Files**: Create `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - foundation for all other subtasks

**Implementation**:
```python
import customtkinter as ctk
from tkinter import ttk
from typing import Literal, Optional, Callable

class HierarchyAdminWindow(ctk.CTkToplevel):
    """
    Admin window for managing ingredient or material hierarchies.

    Args:
        parent: Parent window
        entity_type: "ingredient" or "material"
        on_close: Optional callback when window closes
    """

    def __init__(
        self,
        parent,
        entity_type: Literal["ingredient", "material"],
        on_close: Optional[Callable] = None
    ):
        super().__init__(parent)

        self.entity_type = entity_type
        self.on_close = on_close
        self.selected_item = None

        # Window setup
        title = "Ingredient Hierarchy Admin" if entity_type == "ingredient" else "Material Hierarchy Admin"
        self.title(title)
        self.geometry("900x600")
        self.minsize(700, 500)

        # Import appropriate service
        if entity_type == "ingredient":
            from src.services.ingredient_hierarchy_service import ingredient_hierarchy_service
            self.hierarchy_service = ingredient_hierarchy_service
        else:
            from src.services.material_hierarchy_service import material_hierarchy_service
            self.hierarchy_service = material_hierarchy_service

        # Build UI
        self._create_layout()
        self._load_tree()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self.on_close:
            self.on_close()
        self.destroy()
```

### Subtask T023 – Implement tree view using ttk.Treeview with CustomTkinter styling

- **Purpose**: Display hierarchical data in expandable tree.
- **Files**: Add to `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - depends on T022

**Implementation**:
```python
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
        font=ctk.CTkFont(size=14, weight="bold")
    )
    tree_label.pack(pady=(5, 10))

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

def _load_tree(self):
    """Load hierarchy data into tree view."""
    # Clear existing items
    for item in self.tree.get_children():
        self.tree.delete(item)

    # Get tree data from service
    tree_data = self.hierarchy_service.get_hierarchy_tree()

    # Build tree
    for node in tree_data:
        self._insert_tree_node("", node)

def _insert_tree_node(self, parent_id: str, node: dict):
    """Recursively insert node and children into tree."""
    # Determine display text and icon based on level/type
    name = node.get("name", "Unknown")

    if self.entity_type == "ingredient":
        level = node.get("level", 0)
        prefix = ["[L0]", "[L1]", ""][min(level, 2)]
    else:
        item_type = node.get("type", "material")
        prefix = {"category": "[Cat]", "subcategory": "[Sub]", "material": ""}[item_type]

    display_text = f"{prefix} {name}".strip()

    # Insert node
    item_id = self.tree.insert(
        parent_id, "end",
        text=display_text,
        open=False,
        tags=(str(node.get("id")),)
    )

    # Store node data for lookup
    if not hasattr(self, "_node_data"):
        self._node_data = {}
    self._node_data[item_id] = node

    # Insert children
    for child in node.get("children", []):
        self._insert_tree_node(item_id, child)
```

### Subtask T024 – Implement expand/collapse functionality

- **Purpose**: Allow users to expand/collapse tree nodes.
- **Files**: Add to `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - depends on T023

**Implementation**:
```python
# Already handled by ttk.Treeview default behavior
# Nodes expand/collapse on double-click or arrow keys
# The `open=False` in _insert_tree_node starts collapsed

# Add expand all / collapse all buttons if desired:
def _create_tree_controls(self):
    """Add expand/collapse all buttons."""
    control_frame = ctk.CTkFrame(self.tree_frame)
    control_frame.pack(fill="x", pady=(0, 5))

    expand_btn = ctk.CTkButton(
        control_frame,
        text="Expand All",
        width=80,
        command=self._expand_all
    )
    expand_btn.pack(side="left", padx=2)

    collapse_btn = ctk.CTkButton(
        control_frame,
        text="Collapse All",
        width=80,
        command=self._collapse_all
    )
    collapse_btn.pack(side="left", padx=2)

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
```

### Subtask T025 – Implement item selection with detail panel

- **Purpose**: Show selected item details in right panel.
- **Files**: Add to `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - depends on T023

**Implementation**:
```python
def _create_detail_panel(self):
    """Create the detail panel on the right side."""
    self.detail_frame = ctk.CTkFrame(self.main_frame, width=300)
    self.detail_frame.pack(side="right", fill="y", padx=(5, 0))
    self.detail_frame.pack_propagate(False)

    # Header
    detail_label = ctk.CTkLabel(
        self.detail_frame,
        text="Item Details",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    detail_label.pack(pady=(5, 10))

    # Name display
    name_frame = ctk.CTkFrame(self.detail_frame)
    name_frame.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(name_frame, text="Name:").pack(anchor="w")
    self.name_label = ctk.CTkLabel(name_frame, text="-", wraplength=250)
    self.name_label.pack(anchor="w")

    # Path display
    path_frame = ctk.CTkFrame(self.detail_frame)
    path_frame.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(path_frame, text="Path:").pack(anchor="w")
    self.path_label = ctk.CTkLabel(path_frame, text="-", wraplength=250)
    self.path_label.pack(anchor="w")

    # Usage counts frame (populated in T026)
    self.usage_frame = ctk.CTkFrame(self.detail_frame)
    self.usage_frame.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(self.usage_frame, text="Usage:").pack(anchor="w")
    self.usage_label = ctk.CTkLabel(self.usage_frame, text="-")
    self.usage_label.pack(anchor="w")

    # Action buttons frame (populated in T028)
    self.actions_frame = ctk.CTkFrame(self.detail_frame)
    self.actions_frame.pack(fill="x", padx=10, pady=20)

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
    self.name_label.configure(text=node.get("name", "-"))

    # Build path
    path = self._get_item_path(node)
    self.path_label.configure(text=path)

    # Update usage counts (T026)
    self._update_usage_counts(node)

def _get_item_path(self, node: dict) -> str:
    """Build display path for item."""
    if self.entity_type == "ingredient":
        ing = node.get("ingredient")
        if ing and hasattr(ing, "get_ancestors"):
            ancestors = ing.get_ancestors()
            names = [a.display_name for a in ancestors] + [ing.display_name]
            return " > ".join(names)
        return node.get("name", "-")
    else:
        # For materials, build from node type
        item_type = node.get("type")
        if item_type == "material":
            mat = node.get("material")
            if mat and mat.subcategory:
                subcat = mat.subcategory
                cat = subcat.category if subcat else None
                parts = []
                if cat:
                    parts.append(cat.name)
                if subcat:
                    parts.append(subcat.name)
                parts.append(mat.name)
                return " > ".join(parts)
        return node.get("name", "-")

def _clear_detail_panel(self):
    """Clear detail panel when nothing selected."""
    self.selected_item = None
    self.name_label.configure(text="-")
    self.path_label.configure(text="-")
    self.usage_label.configure(text="-")
```

### Subtask T026 – Display usage counts (products, recipes) for selected item

- **Purpose**: Show how many products/recipes use the selected item.
- **Files**: Add to `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - depends on T025

**Implementation**:
```python
def _update_usage_counts(self, node: dict):
    """Fetch and display usage counts for selected item."""
    # Only show usage for leaf items
    if self.entity_type == "ingredient":
        level = node.get("level", 0)
        if level != 2:
            self.usage_label.configure(text="(Select L2 item for usage)")
            return

        ing = node.get("ingredient")
        if ing:
            counts = self.hierarchy_service.get_usage_counts(ing.id)
            text = f"Products: {counts['product_count']}, Recipes: {counts['recipe_count']}"
            self.usage_label.configure(text=text)
    else:
        item_type = node.get("type")
        if item_type != "material":
            self.usage_label.configure(text="(Select material for usage)")
            return

        mat = node.get("material")
        if mat:
            counts = self.hierarchy_service.get_usage_counts(mat.id)
            text = f"Products: {counts['product_count']}"
            self.usage_label.configure(text=text)
```

### Subtask T027 – Add configuration parameter to switch between Ingredient/Material mode

- **Purpose**: Allow single window class to handle both entity types.
- **Files**: Already implemented in `src/ui/hierarchy_admin_window.py` via `entity_type` parameter
- **Parallel?**: N/A - already designed into T022

*The `entity_type` parameter in `__init__` handles this:*
- Determines window title
- Selects appropriate hierarchy service
- Adjusts display formatting (L0/L1/L2 vs Category/Subcategory/Material)
- Configures usage count display

### Subtask T028 – Create action button placeholders (Add, Rename, Reparent)

- **Purpose**: Add buttons for operations (functionality in WP05-WP07).
- **Files**: Add to `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - depends on T025

**Implementation**:
```python
def _create_action_buttons(self):
    """Create action buttons in detail panel."""
    # Clear existing buttons
    for widget in self.actions_frame.winfo_children():
        widget.destroy()

    ctk.CTkLabel(
        self.actions_frame,
        text="Actions",
        font=ctk.CTkFont(weight="bold")
    ).pack(anchor="w", pady=(0, 5))

    # Add button
    self.add_btn = ctk.CTkButton(
        self.actions_frame,
        text="Add New...",
        command=self._on_add_click,
        state="disabled"  # Enabled in WP05
    )
    self.add_btn.pack(fill="x", pady=2)

    # Rename button
    self.rename_btn = ctk.CTkButton(
        self.actions_frame,
        text="Rename...",
        command=self._on_rename_click,
        state="disabled"  # Enabled in WP06
    )
    self.rename_btn.pack(fill="x", pady=2)

    # Reparent button
    self.reparent_btn = ctk.CTkButton(
        self.actions_frame,
        text="Move to...",
        command=self._on_reparent_click,
        state="disabled"  # Enabled in WP07
    )
    self.reparent_btn.pack(fill="x", pady=2)

def _on_add_click(self):
    """Placeholder for add operation."""
    pass  # Implemented in WP05

def _on_rename_click(self):
    """Placeholder for rename operation."""
    pass  # Implemented in WP06

def _on_reparent_click(self):
    """Placeholder for reparent operation."""
    pass  # Implemented in WP07

# Call _create_action_buttons() at end of _create_detail_panel()
```

## Test Strategy

**Manual Testing** (UI components):
1. Open window in ingredient mode - verify tree displays correctly
2. Open window in material mode - verify tree displays correctly
3. Expand/collapse nodes - verify functionality
4. Select items - verify detail panel updates
5. Verify usage counts display for leaf items

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| ttk.Treeview styling mismatch | Test appearance on target platforms |
| Tree performance with many items | Lazy loading if >500 items |
| Detail panel layout issues | Use fixed width; test with long names |

## Definition of Done Checklist

- [ ] `hierarchy_admin_window.py` created as CTkToplevel
- [ ] Tree view displays 3-level hierarchy for both entity types
- [ ] Expand/collapse works correctly
- [ ] Selection updates detail panel
- [ ] Usage counts display for leaf items
- [ ] Action button placeholders visible
- [ ] Window works for both "ingredient" and "material" modes

## Review Guidance

**Key checkpoints for reviewer**:
1. Open Hierarchy Admin for Ingredients - verify tree structure
2. Open Hierarchy Admin for Materials - verify tree structure
3. Expand/collapse all nodes
4. Select various items - verify detail panel
5. Check usage counts display correctly
6. Verify buttons are visible (disabled is OK for this WP)

## Activity Log

- 2026-01-14T15:00:00Z – system – lane=planned – Prompt created.
- 2026-01-15T03:49:33Z – claude – lane=doing – Moved to doing
