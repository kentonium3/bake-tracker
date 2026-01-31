---
work_package_id: "WP01"
title: "Tab Shell with F087 Layout"
lane: "for_review"
dependencies: []
subtasks: ["T001", "T002", "T003", "T004", "T005", "T006", "T007"]
priority: "P0"
estimated_lines: 350
agent: "claude-lead"
shell_pid: "21510"
history:
  - date: "2026-01-30"
    action: "created"
    agent: "claude"
---

# WP01: Tab Shell with F087 Layout

## Objective

Create the Finished Goods tab following F087 standardized layout exactly. The tab appears in Catalog mode as the 4th tab after Recipes, displaying an empty ttk.Treeview grid with search bar, assembly type filter, and action buttons.

## Context

- **Feature**: 088-finished-goods-catalog-ui
- **Priority**: P0 (foundation for all other WPs)
- **Dependencies**: None (starting package)
- **Estimated Size**: ~350 lines

### Reference Files

- `src/ui/recipes_tab.py` - Primary pattern for F087 3-row layout with ttk.Treeview
- `src/ui/finished_units_tab.py` - Recently converted to ttk.Treeview, good reference for selection state
- `src/ui/widgets/search_bar.py` - Reusable SearchBar widget
- `src/ui/modes/catalog_mode.py` - Where to add the new tab (lines 59-87)

### F087 Layout Pattern (MANDATORY)

```python
# 3-row layout from recipes_tab.py - copy this pattern exactly
self.grid_rowconfigure(0, weight=0)  # Search/filters (fixed height)
self.grid_rowconfigure(1, weight=0)  # Action buttons (fixed height)
self.grid_rowconfigure(2, weight=1)  # ttk.Treeview (expandable)
self.grid_rowconfigure(3, weight=0)  # Status bar (fixed height)
```

## Implementation Command

```bash
spec-kitty implement WP01
```

---

## Subtasks

### T001: Create `src/ui/finished_goods_tab.py` with F087 3-row layout shell

**Purpose**: Create the main tab file with the standard F087 layout structure.

**Steps**:
1. Create new file `src/ui/finished_goods_tab.py`
2. Import dependencies:
   ```python
   import customtkinter as ctk
   from tkinter import ttk
   from typing import Optional, List
   from src.models.finished_good import FinishedGood
   from src.models.assembly_type import AssemblyType
   from src.services import finished_good_service
   from src.ui.widgets.search_bar import SearchBar
   ```
3. Create `FinishedGoodsTab` class extending `ctk.CTkFrame`
4. Implement `__init__` with F087 grid configuration:
   - Row 0: Controls frame (search + filter)
   - Row 1: Actions frame (buttons)
   - Row 2: Tree container (ttk.Treeview)
   - Row 3: Status bar
5. Store instance variables: `_current_finished_goods`, `_selected_id`

**Files**:
- `src/ui/finished_goods_tab.py` (new file, ~80 lines for shell)

**Validation**:
- [ ] Class instantiates without error
- [ ] Grid layout matches recipes_tab.py pattern
- [ ] All 4 rows configured with correct weights

---

### T002: Add SearchBar with assembly type filter dropdown

**Purpose**: Implement the controls row with search and assembly type filter.

**Steps**:
1. Create controls frame in row 0:
   ```python
   self.controls_frame = ctk.CTkFrame(self)
   self.controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
   ```
2. Add SearchBar widget on the left:
   ```python
   self.search_bar = SearchBar(
       self.controls_frame,
       placeholder="Search finished goods...",
       on_search=self._on_search
   )
   ```
3. Add assembly type filter dropdown on the right:
   ```python
   self.type_filter = ctk.CTkComboBox(
       self.controls_frame,
       values=["All", "Custom Order", "Gift Box", "Variety Pack", "Seasonal Box", "Event Package"],
       command=self._on_type_filter_changed
   )
   self.type_filter.set("All")
   ```
4. Implement stub methods `_on_search()` and `_on_type_filter_changed()`

**Files**:
- `src/ui/finished_goods_tab.py` (~40 lines added)

**Validation**:
- [ ] SearchBar appears and accepts input
- [ ] Dropdown shows all assembly type options plus "All"
- [ ] Filter defaults to "All"

---

### T003: Create ttk.Treeview with columns (Name, Assembly Type, Component Count, Notes)

**Purpose**: Implement the main data grid following F087 ttk.Treeview pattern.

**Steps**:
1. Create tree container frame in row 2:
   ```python
   self.tree_frame = ctk.CTkFrame(self)
   self.tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
   ```
2. Create ttk.Treeview with columns:
   ```python
   columns = ("name", "assembly_type", "component_count", "notes")
   self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", selectmode="browse")
   ```
3. Configure column headings:
   - Name (width=200, anchor=W)
   - Assembly Type (width=120, anchor=W)
   - Component Count (width=100, anchor=CENTER)
   - Notes (width=300, anchor=W, truncated)
4. Add vertical scrollbar:
   ```python
   scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
   self.tree.configure(yscrollcommand=scrollbar.set)
   ```
5. Bind selection event: `self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed)`
6. Bind double-click: `self.tree.bind("<Double-1>", self._on_double_click)`

**Files**:
- `src/ui/finished_goods_tab.py` (~50 lines added)

**Validation**:
- [ ] Treeview renders with all 4 columns
- [ ] Column headers are clickable (for future sorting)
- [ ] Scrollbar appears when content overflows
- [ ] Trackpad scrolling works (ttk.Treeview native support)

---

### T004: Add action buttons frame (Create New, Edit, Delete) - disabled initially

**Purpose**: Implement the actions row with CRUD buttons.

**Steps**:
1. Create actions frame in row 1:
   ```python
   self.actions_frame = ctk.CTkFrame(self)
   self.actions_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
   ```
2. Add Create New button (always enabled):
   ```python
   self.create_btn = ctk.CTkButton(
       self.actions_frame,
       text="Create New",
       command=self._on_create_new
   )
   ```
3. Add Edit button (initially disabled):
   ```python
   self.edit_btn = ctk.CTkButton(
       self.actions_frame,
       text="Edit",
       command=self._on_edit,
       state="disabled"
   )
   ```
4. Add Delete button (initially disabled):
   ```python
   self.delete_btn = ctk.CTkButton(
       self.actions_frame,
       text="Delete",
       command=self._on_delete,
       state="disabled"
   )
   ```
5. Implement stub command methods

**Files**:
- `src/ui/finished_goods_tab.py` (~35 lines added)

**Validation**:
- [ ] All 3 buttons render in actions frame
- [ ] Create New is enabled by default
- [ ] Edit and Delete are disabled by default
- [ ] Button click handlers don't crash (stubs)

---

### T005: Add status bar with status messages

**Purpose**: Implement the status bar row for feedback messages.

**Steps**:
1. Create status bar frame in row 3:
   ```python
   self.status_frame = ctk.CTkFrame(self)
   self.status_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
   ```
2. Add status label:
   ```python
   self.status_label = ctk.CTkLabel(
       self.status_frame,
       text="",
       anchor="w"
   )
   self.status_label.pack(fill="x", padx=5)
   ```
3. Implement `_set_status(message: str)` method:
   ```python
   def _set_status(self, message: str):
       self.status_label.configure(text=message)
   ```
4. Implement `_clear_status()` method

**Files**:
- `src/ui/finished_goods_tab.py` (~20 lines added)

**Validation**:
- [ ] Status bar appears at bottom
- [ ] Status message can be set and cleared
- [ ] Status text is left-aligned

---

### T006: Implement empty state message when no FinishedGoods exist

**Purpose**: Show user-friendly message when the list is empty.

**Steps**:
1. Implement `_refresh_list()` method:
   ```python
   def _refresh_list(self):
       # Clear existing items
       for item in self.tree.get_children():
           self.tree.delete(item)

       # Load finished goods
       self._current_finished_goods = finished_good_service.get_all_finished_goods()

       if not self._current_finished_goods:
           self._show_empty_state()
           return

       # Populate tree...
   ```
2. Implement `_show_empty_state()`:
   ```python
   def _show_empty_state(self):
       self._set_status("No finished goods defined. Click 'Create New' to add one.")
   ```
3. Implement `_populate_tree()` to insert FinishedGood records:
   ```python
   def _populate_tree(self):
       for fg in self._current_finished_goods:
           component_count = len(fg.components) if fg.components else 0
           notes = (fg.notes[:50] + "...") if fg.notes and len(fg.notes) > 50 else (fg.notes or "")
           self.tree.insert("", "end", iid=str(fg.id), values=(
               fg.display_name,
               fg.assembly_type.value if fg.assembly_type else "",
               component_count,
               notes
           ))
   ```
4. Call `_refresh_list()` at end of `__init__`

**Files**:
- `src/ui/finished_goods_tab.py` (~45 lines added)

**Validation**:
- [ ] Empty database shows status message
- [ ] Populated database shows items in tree
- [ ] Component count is accurate
- [ ] Notes are truncated to 50 chars

---

### T007: Add tab to `src/ui/modes/catalog_mode.py` as 4th tab after Recipes

**Purpose**: Integrate the new tab into Catalog mode.

**Steps**:
1. Add import at top of catalog_mode.py:
   ```python
   from src.ui.finished_goods_tab import FinishedGoodsTab
   ```
2. Find the tab creation section (around line 59-87)
3. Add FinishedGoodsTab after RecipesTab:
   ```python
   self.finished_goods_tab = FinishedGoodsTab(self.notebook)
   self.notebook.add(self.finished_goods_tab, text="Finished Goods")
   ```
4. Ensure tab order: Ingredients, Products, Recipes, Finished Goods

**Files**:
- `src/ui/modes/catalog_mode.py` (~5 lines added)

**Validation**:
- [ ] Finished Goods tab appears in Catalog mode
- [ ] Tab is 4th position (after Recipes)
- [ ] Switching to tab doesn't crash
- [ ] Tab content displays correctly

---

## Definition of Done

- [ ] All 7 subtasks completed
- [ ] `src/ui/finished_goods_tab.py` created with F087 layout
- [ ] Tab integrated into `catalog_mode.py`
- [ ] Manual testing: Tab appears, treeview works, empty state shows
- [ ] No regressions in existing Catalog tabs

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| F087 layout deviation | Copy directly from recipes_tab.py; compare layouts visually |
| Trackpad scrolling broken | Use ttk.Treeview (native scrolling); test on macOS |
| Import cycle | Keep imports minimal; use lazy loading if needed |

## Reviewer Guidance

1. Verify F087 compliance by comparing with recipes_tab.py
2. Check that all 4 grid rows have correct weights
3. Test trackpad scrolling in treeview
4. Confirm empty state message appears when no data
5. Verify tab position is 4th in Catalog mode

## Activity Log

- 2026-01-31T04:31:45Z – claude-lead – shell_pid=21510 – lane=doing – Started implementation via workflow command
- 2026-01-31T04:37:53Z – claude-lead – shell_pid=21510 – lane=for_review – Ready for review: Implemented F087 ttk.Treeview layout with assembly type filter, click-to-sort columns, and integration with RecipesGroupTab as third sub-tab.
