---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "RecipesTab ttk.Treeview Conversion"
phase: "Phase 1 - Core Pattern Validation"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "5999"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-31T02:38:50Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – RecipesTab ttk.Treeview Conversion

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

**Primary Objective**: Replace the custom `RecipeDataTable` widget with a native `ttk.Treeview` to enable trackpad scrolling support.

**Success Criteria**:
1. Two-finger trackpad swipe scrolls the recipe list smoothly
2. Column headers remain clickable for sorting (ascending/descending toggle)
3. Row selection triggers the same callback behavior as before
4. Double-click opens the recipe edit dialog
5. Variant recipes display with "↳ " prefix and appear after their base recipe
6. Recipe count in status bar continues to display correctly
7. All existing CRUD functionality preserved

**Why This is MVP**: Trackpad scrolling is the primary usability fix requested. This WP validates the ttk.Treeview pattern that will be applied to other tabs.

---

## Context & Constraints

**Reference Files**:
- `src/ui/recipes_tab.py` - Target file for changes
- `src/ui/ingredients_tab.py:215-296` - Reference ttk.Treeview implementation to copy
- `src/ui/widgets/data_table.py` - Current RecipeDataTable (study before replacing)
- `kitty-specs/087-catalog-tab-layout-standardization/research.md` - Pattern documentation

**Key Constraint**: RecipeDataTable has variant grouping logic that MUST be preserved. Variants (recipes with `base_recipe_id` set) must:
1. Display with "↳ " prefix before the name
2. Appear immediately after their base recipe in the list
3. Sort correctly when column headers are clicked

**Architecture**: Pure UI refactoring - no service layer changes allowed.

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create ttk.Treeview with Columns

**Purpose**: Replace the RecipeDataTable initialization with ttk.Treeview.

**Steps**:
1. Import ttk from tkinter (add to existing imports at top of file)
2. In `_create_data_table()` method, replace RecipeDataTable creation with:
   ```python
   # Container frame for grid and scrollbar (like IngredientsTab)
   self.grid_container = ctk.CTkFrame(self, fg_color="transparent")
   self.grid_container.grid(
       row=2, column=0, sticky="nsew",
       padx=PADDING_LARGE, pady=PADDING_MEDIUM
   )
   self.grid_container.grid_columnconfigure(0, weight=1)
   self.grid_container.grid_rowconfigure(0, weight=1)

   # Define columns matching RecipeDataTable
   columns = ("name", "category", "yield")
   self.tree = ttk.Treeview(
       self.grid_container,
       columns=columns,
       show="headings",
       selectmode="browse",
   )
   ```
3. Configure column headings:
   ```python
   self.tree.heading("name", text="Recipe Name", anchor="w")
   self.tree.heading("category", text="Category", anchor="w")
   self.tree.heading("yield", text="Yield", anchor="w")
   ```
4. Configure column widths to match RecipeDataTable:
   ```python
   self.tree.column("name", width=330, minwidth=200)
   self.tree.column("category", width=120, minwidth=80)
   self.tree.column("yield", width=150, minwidth=100)
   ```

**Files**: `src/ui/recipes_tab.py` - modify `_create_data_table()` method

---

### Subtask T002 – Add Vertical Scrollbar Configuration

**Purpose**: Enable native trackpad scrolling by connecting a ttk.Scrollbar.

**Steps**:
1. Add scrollbar after tree creation:
   ```python
   y_scrollbar = ttk.Scrollbar(
       self.grid_container,
       orient="vertical",
       command=self.tree.yview,
   )
   self.tree.configure(yscrollcommand=y_scrollbar.set)
   ```
2. Grid the tree and scrollbar:
   ```python
   self.tree.grid(row=0, column=0, sticky="nsew")
   y_scrollbar.grid(row=0, column=1, sticky="ns")
   ```

**Files**: `src/ui/recipes_tab.py` - add to `_create_data_table()`

**Validation**: After this subtask, trackpad scrolling should work in the Recipes tab.

---

### Subtask T003 – Implement Column Header Click-to-Sort

**Purpose**: Preserve sorting functionality when column headers are clicked.

**Steps**:
1. Add sort state tracking at class level (in `__init__`):
   ```python
   self.sort_column = "name"
   self.sort_ascending = True
   ```
2. Add header command callbacks in `_create_data_table()`:
   ```python
   self.tree.heading(
       "name", text="Recipe Name", anchor="w",
       command=lambda: self._on_header_click("name")
   )
   self.tree.heading(
       "category", text="Category", anchor="w",
       command=lambda: self._on_header_click("category")
   )
   self.tree.heading(
       "yield", text="Yield", anchor="w",
       command=lambda: self._on_header_click("yield")
   )
   ```
3. Add `_on_header_click()` method:
   ```python
   def _on_header_click(self, column: str):
       """Handle column header click for sorting."""
       if self.sort_column == column:
           self.sort_ascending = not self.sort_ascending
       else:
           self.sort_column = column
           self.sort_ascending = True
       self._refresh_tree_display()
   ```

**Files**: `src/ui/recipes_tab.py`

---

### Subtask T004 – Implement Row Selection Callback

**Purpose**: Enable row selection to update button states and status bar.

**Steps**:
1. Bind selection event in `_create_data_table()`:
   ```python
   self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
   ```
2. Add `_on_tree_select()` method:
   ```python
   def _on_tree_select(self, event):
       """Handle tree selection change."""
       selection = self.tree.selection()
       if selection:
           recipe_id = int(selection[0])
           # Find recipe in current list
           recipe = self._get_recipe_by_id(recipe_id)
           self._on_row_select(recipe)
       else:
           self._on_row_select(None)

   def _get_recipe_by_id(self, recipe_id: int):
       """Find recipe by ID in current data."""
       # Need to store recipes list - add self._current_recipes in refresh
       return next(
           (r for r in getattr(self, '_current_recipes', []) if r.id == recipe_id),
           None
       )
   ```
3. Store recipes in `refresh()` method for lookup:
   ```python
   self._current_recipes = recipes  # Add before calling data_table.set_data
   ```

**Files**: `src/ui/recipes_tab.py`

---

### Subtask T005 – Implement Double-Click Callback

**Purpose**: Open edit dialog when user double-clicks a recipe row.

**Steps**:
1. Bind double-click event in `_create_data_table()`:
   ```python
   self.tree.bind("<Double-1>", self._on_tree_double_click)
   ```
2. Add `_on_tree_double_click()` method:
   ```python
   def _on_tree_double_click(self, event):
       """Handle double-click on recipe row."""
       selection = self.tree.selection()
       if selection:
           recipe_id = int(selection[0])
           recipe = self._get_recipe_by_id(recipe_id)
           if recipe:
               self._on_row_double_click(recipe)
   ```

**Files**: `src/ui/recipes_tab.py`

---

### Subtask T006 – Implement Variant Grouping

**Purpose**: Display variant recipes with "↳ " prefix immediately after their base recipe.

**Critical Logic**: This is the most complex part. Study `RecipeDataTable.set_data()` in `src/ui/widgets/data_table.py` for the current implementation.

**Steps**:
1. Create `_refresh_tree_display()` method that handles sorting and variant grouping:
   ```python
   def _refresh_tree_display(self):
       """Refresh the tree display with current recipes, sorting, and variant grouping."""
       # Clear existing items
       for item in self.tree.get_children():
           self.tree.delete(item)

       recipes = getattr(self, '_current_recipes', [])
       if not recipes:
           return

       # Separate base recipes and variants
       base_recipes = [r for r in recipes if r.base_recipe_id is None]
       variants = [r for r in recipes if r.base_recipe_id is not None]

       # Sort base recipes by current sort column
       base_recipes = self._sort_recipes(base_recipes)

       # Group variants by base_recipe_id
       variants_by_base = {}
       for v in variants:
           base_id = v.base_recipe_id
           if base_id not in variants_by_base:
               variants_by_base[base_id] = []
           variants_by_base[base_id].append(v)

       # Sort variants within each group
       for base_id in variants_by_base:
           variants_by_base[base_id] = self._sort_recipes(variants_by_base[base_id])

       # Insert into tree: base recipe, then its variants
       for recipe in base_recipes:
           self._insert_recipe_row(recipe, is_variant=False)
           # Insert variants for this base
           for variant in variants_by_base.get(recipe.id, []):
               self._insert_recipe_row(variant, is_variant=True)

   def _sort_recipes(self, recipes: list) -> list:
       """Sort recipes by current sort column."""
       def get_sort_key(r):
           if self.sort_column == "name":
               return (r.name or "").lower()
           elif self.sort_column == "category":
               return (r.category or "").lower()
           elif self.sort_column == "yield":
               # Sort by first yield type's items_per_batch
               return 0  # Simplified - can enhance later
           return ""

       return sorted(recipes, key=get_sort_key, reverse=not self.sort_ascending)

   def _insert_recipe_row(self, recipe, is_variant: bool):
       """Insert a recipe row into the tree."""
       name = recipe.name or ""
       if is_variant:
           name = f"↳ {name}"

       category = recipe.category or ""

       # Get yield display (simplified - can copy from RecipeDataTable)
       yield_display = ""  # TODO: Copy yield formatting from RecipeDataTable

       values = (name, category, yield_display)
       self.tree.insert("", "end", iid=str(recipe.id), values=values)
   ```

2. Update `refresh()` to call `_refresh_tree_display()` instead of `data_table.set_data()`:
   ```python
   # Store recipes for selection lookup
   self._current_recipes = recipes
   # Refresh the tree display
   self._refresh_tree_display()
   # Update status
   self._update_status(f"Loaded {len(recipes)} recipe(s)")
   ```

**Files**: `src/ui/recipes_tab.py`

**Note**: The yield display formatting should be copied from `RecipeDataTable._format_yield()` if it exists, or simplified.

---

### Subtask T007 – Remove RecipeDataTable Import and Update Grid Placement

**Purpose**: Clean up old widget reference and ensure proper grid placement.

**Steps**:
1. Remove RecipeDataTable import from top of file:
   ```python
   # REMOVE this line:
   from src.ui.widgets.data_table import RecipeDataTable
   ```
2. Remove `self.data_table` attribute and replace all references with `self.tree`
3. Update `_on_search()` method to call `_refresh_tree_display()` after filtering
4. Verify grid placement:
   - Row 0: search_bar (weight=0)
   - Row 1: button_frame (weight=0)
   - Row 2: grid_container with tree (weight=1)
   - Row 3: status_frame (weight=0)

**Files**: `src/ui/recipes_tab.py`

---

## Test Strategy

No automated tests required - manual verification:

1. **Trackpad Scrolling**: Open Recipes tab with 20+ recipes, two-finger swipe should scroll smoothly
2. **Column Sorting**: Click Name/Category/Yield headers - should toggle sort direction
3. **Selection**: Click a row - Edit/Delete/Details buttons should enable
4. **Double-Click**: Double-click a row - should open Recipe edit dialog
5. **Variants**: If recipes have variants, they should appear with "↳ " after their base
6. **Status Bar**: Should show "Loaded X recipe(s)" count

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Variant grouping breaks | Test with recipes that have variants before marking complete |
| Yield display incorrect | Copy formatting from RecipeDataTable exactly |
| Selection callback crashes | Verify `_current_recipes` is populated before selection events |
| Sort doesn't toggle | Verify `sort_ascending` flips on same-column click |

---

## Definition of Done Checklist

- [ ] ttk.Treeview replaces RecipeDataTable
- [ ] Trackpad two-finger scroll works
- [ ] Column header sorting works (ascending/descending toggle)
- [ ] Row selection enables action buttons
- [ ] Double-click opens edit dialog
- [ ] Variants display with "↳ " prefix after their base
- [ ] RecipeDataTable import removed
- [ ] No regressions in search/filter/CRUD operations
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Key checkpoints for `/spec-kitty.review`**:
1. Test trackpad scrolling - this is the primary fix
2. Verify variant display order with actual variant recipes
3. Check column sorting toggles correctly
4. Verify all CRUD operations still work

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-31T02:38:50Z – system – lane=planned – Prompt created.
- 2026-01-31T02:44:42Z – claude-opus – shell_pid=4735 – lane=doing – Started implementation via workflow command
- 2026-01-31T02:48:49Z – claude-opus – shell_pid=4735 – lane=for_review – RecipesTab ttk.Treeview conversion complete. Ready for review: trackpad scrolling, column sorting, selection/double-click callbacks, variant grouping preserved.
- 2026-01-31T02:48:58Z – claude-opus – shell_pid=5999 – lane=doing – Started review via workflow command
