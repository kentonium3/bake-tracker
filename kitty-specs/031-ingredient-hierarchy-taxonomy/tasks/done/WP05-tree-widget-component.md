---
work_package_id: "WP05"
subtasks:
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
title: "Tree Widget Component"
phase: "Phase 3 - UI"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "4378"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-30T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Tree Widget Component

## Objectives & Success Criteria

**Goal**: Create reusable tree selection widget for ingredient hierarchy.

**Success Criteria**:
- Tree widget displays hierarchical ingredients
- Expand/collapse works with lazy loading
- Search auto-expands matching branches
- Breadcrumb shows selected item's path
- Leaf-only mode restricts selection for recipe context
- Visual distinction between categories and leaves
- Widget integrates with CustomTkinter styling

## Context & Constraints

**References**:
- Plan: `kitty-specs/031-ingredient-hierarchy-taxonomy/plan.md` - UI Layer Design
- Research: `kitty-specs/031-ingredient-hierarchy-taxonomy/research.md` - Decision D3 (ttk.Treeview)
- Quickstart: `kitty-specs/031-ingredient-hierarchy-taxonomy/quickstart.md`

**Constraints**:
- Use ttk.Treeview wrapped in CTkFrame for CustomTkinter compatibility
- Lazy-load children to handle 500+ ingredients efficiently
- Follow existing UI patterns in `src/ui/widgets/`
- Widget must work in multiple contexts (ingredients tab, recipe dialogs)

**PARALLEL SAFE**: This entire work package can be done in parallel with WP02-WP04 (service work). Stub service calls for initial development.

## Subtasks & Detailed Guidance

### Subtask T026 – Create tree widget file [PARALLEL SAFE]
- **Purpose**: Establish reusable widget with basic structure.
- **Steps**:
  1. Create `src/ui/widgets/ingredient_tree_widget.py`
  2. Create class `IngredientTreeWidget(ctk.CTkFrame)`:
     ```python
     import customtkinter as ctk
     from tkinter import ttk

     class IngredientTreeWidget(ctk.CTkFrame):
         def __init__(self, master, on_select_callback=None, leaf_only=False, **kwargs):
             super().__init__(master, **kwargs)
             self.on_select_callback = on_select_callback
             self.leaf_only = leaf_only
             self._setup_ui()
             self._load_roots()
     ```
  3. Add ttk.Treeview as main component
  4. Add internal _load_roots() and _on_item_expand() methods
- **Files**: `src/ui/widgets/ingredient_tree_widget.py`
- **Parallel?**: Yes (different file set from services)
- **Notes**: Can stub service calls initially; replace with real calls when WP02 complete

### Subtask T027 – Implement expand/collapse with lazy loading [PARALLEL SAFE]
- **Purpose**: Load children only when node is expanded.
- **Steps**:
  1. Bind to <<TreeviewOpen>> event
  2. On expand, call `get_children(parent_id)` from hierarchy service
  3. Insert children as new tree items
  4. Add placeholder children to show expand arrow before first expand
  5. Remove placeholder after real children loaded
- **Files**: `src/ui/widgets/ingredient_tree_widget.py`
- **Parallel?**: Yes
- **Notes**: Lazy loading is critical for performance with 500+ items

### Subtask T028 – Implement search with auto-expand [PARALLEL SAFE]
- **Purpose**: Search box that filters and expands matching branches.
- **Steps**:
  1. Add CTkEntry for search input above tree
  2. Bind to KeyRelease event for live search
  3. Call `search_ingredients(query)` from hierarchy service
  4. For each match, expand ancestors to reveal item
  5. Highlight or select matching items
  6. Debounce search to avoid excessive API calls (300ms delay)
- **Files**: `src/ui/widgets/ingredient_tree_widget.py`
- **Parallel?**: Yes
- **Notes**: Use after() for debouncing; clear highlights on new search

### Subtask T029 – Implement breadcrumb display [PARALLEL SAFE]
- **Purpose**: Show selected item's path for context.
- **Steps**:
  1. Add CTkLabel below tree for breadcrumb
  2. On item selection, call `get_ancestors(ingredient_id)`
  3. Build path string: "Chocolate → Dark Chocolate → Semi-Sweet Chips"
  4. Update label with path
  5. Handle root items (no ancestors)
- **Files**: `src/ui/widgets/ingredient_tree_widget.py`
- **Parallel?**: Yes
- **Notes**: Use " → " separator for visual clarity

### Subtask T030 – Add context-aware selection mode [PARALLEL SAFE]
- **Purpose**: Restrict selection to leaves when used in recipe context.
- **Steps**:
  1. Accept `leaf_only=True` parameter in constructor
  2. If leaf_only, check item before allowing selection
  3. Non-leaf items should:
     - Show visual indication they're not selectable
     - Optionally auto-expand on click instead of select
  4. Prevent on_select_callback for non-leaf items
- **Files**: `src/ui/widgets/ingredient_tree_widget.py`
- **Parallel?**: Yes
- **Notes**: Recipe dialogs use leaf_only=True; ingredients tab uses leaf_only=False

### Subtask T031 – Add visual distinction between categories and leaves [PARALLEL SAFE]
- **Purpose**: Users can immediately see which items are selectable.
- **Steps**:
  1. Use different icons or tags for category vs leaf
  2. Options:
     - ttk.Treeview image parameter with folder/file icons
     - Bold text for categories, normal for leaves
     - Color difference (gray for categories, black for leaves)
  3. Test with CustomTkinter dark/light themes
  4. Consider accessibility (not color-only distinction)
- **Files**: `src/ui/widgets/ingredient_tree_widget.py`
- **Parallel?**: Yes
- **Notes**: Test styling compatibility with CustomTkinter early

## Test Strategy

- **Manual Testing**:
  - Test expand/collapse with sample data
  - Test search with various queries
  - Test leaf-only mode prevents category selection
  - Test dark/light theme compatibility

- **Unit Tests** (optional for UI):
  - Test widget creation with various parameters
  - Test callback invocation on selection

- **Commands**:
  ```bash
  # Run app and test manually
  python src/main.py

  # If unit tests added
  pytest src/tests/ui/test_ingredient_tree_widget.py -v
  ```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| ttk.Treeview styling conflicts with CustomTkinter | Test early; use minimal custom styling |
| Slow search with 500+ items | Debounce search; lazy loading helps |
| Service not ready when developing widget | Stub service calls; integration tested in WP06 |

## Definition of Done Checklist

- [ ] T026: Widget file created with basic structure
- [ ] T027: Expand/collapse with lazy loading works
- [ ] T028: Search auto-expands matching branches
- [ ] T029: Breadcrumb displays selected item's path
- [ ] T030: Leaf-only mode restricts selection correctly
- [ ] T031: Categories visually distinct from leaves
- [ ] Widget works with CustomTkinter themes
- [ ] Widget ready for integration in WP06

## Review Guidance

- Verify lazy loading doesn't reload already-loaded children
- Verify search debouncing prevents excessive service calls
- Verify leaf-only mode is respected
- Test with both light and dark CustomTkinter themes
- Check accessibility (not color-only distinction)

## Activity Log

- 2025-12-30T12:00:00Z – system – lane=planned – Prompt created.
- 2025-12-31T14:25:07Z – gemini – shell_pid=31435 – lane=doing – Started parallel implementation
- 2025-12-31T14:31:44Z – gemini – shell_pid=33418 – lane=for_review – Ready for review - all subtasks complete
- 2025-12-31T19:42:25Z – claude-reviewer – shell_pid=4378 – lane=done – Code review passed: Comprehensive tree widget (1232 lines) with lazy loading, search debounce, breadcrumb, leaf-only mode, theme support, and stub data
