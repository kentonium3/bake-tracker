---
id: WP04
title: Tree View Removal
lane: "done"
agent: null
review_status: null
created_at: 2026-01-15
---

# WP04: Tree View Removal

**Feature**: 055-workflow-aligned-navigation-cleanup
**Phase**: 4 | **Risk**: Low
**FR Coverage**: FR-013

---

## Objective

Remove the unused Flat/Tree view toggle from the Ingredients tab. F052 Hierarchy Admin now provides tree-based hierarchy management, making the embedded tree view redundant.

---

## Context

### Current State (ingredients_tab.py)
- View toggle (`CTkSegmentedButton`) between "Flat" and "Tree" modes
- `_view_mode` variable tracks current view
- `_create_tree_view()` creates `IngredientTreeWidget`
- `_on_view_change()` handles toggle switches
- Tree container at row 3, hidden by default

### Target State
- Always show flat grid view
- No toggle button visible
- Remove all tree-related code from ingredients_tab.py

### Important: Preserve IngredientTreeWidget
The `IngredientTreeWidget` class (`src/ui/widgets/ingredient_tree_widget.py`) is used in `recipe_form.py` for ingredient selection. Do NOT delete this file - only remove it from ingredients_tab.py.

---

## Subtasks

- [ ] T013: Remove _view_mode and view toggle from filter bar
- [ ] T014: Remove _create_tree_view() method and tree container
- [ ] T015: Remove tree-related event handlers and search logic

---

## Implementation Details

### T013: Remove view toggle from filter bar

In `src/ui/ingredients_tab.py`, locate the filter bar creation (around line 87) and remove:

```python
# REMOVE these lines:
self._view_mode = "flat"  # or similar variable

# REMOVE the segmented button:
self.view_toggle = ctk.CTkSegmentedButton(
    filter_frame,
    values=["Flat", "Tree"],
    command=self._on_view_change
)
```

### T014: Remove _create_tree_view() and tree container

Remove the entire `_create_tree_view()` method (around lines 418-449) and any references to:
- `self.tree_container`
- `self.ingredient_tree`
- `IngredientTreeWidget` import (if only used here)

### T015: Remove tree-related event handlers

Remove:
- `_on_view_change()` method
- Any tree-related refresh logic in `refresh()` method
- Tree-specific search/filter logic
- Tree selection handlers

---

## Code Sections to Remove

Based on research.md, these are the key locations:

| Section | Lines (approx) | Description |
|---------|----------------|-------------|
| View mode variable | ~87 | `_view_mode = "flat"` |
| View toggle button | ~87-100 | `CTkSegmentedButton` |
| Tree view creation | 418-449 | `_create_tree_view()` |
| View change handler | varies | `_on_view_change()` |
| Tree container refs | varies | `tree_container`, `ingredient_tree` |

---

## Files to Modify

| File | Action |
|------|--------|
| `src/ui/ingredients_tab.py` | MODIFY (remove tree code) |

**DO NOT MODIFY:**
- `src/ui/widgets/ingredient_tree_widget.py` - Used in recipe_form.py

---

## Acceptance Criteria

- [ ] No Flat/Tree toggle visible in Ingredients tab
- [ ] Grid view displays by default (always)
- [ ] Search/filter functionality works on grid
- [ ] All CRUD operations work on grid
- [ ] `IngredientTreeWidget` file still exists
- [ ] recipe_form.py ingredient selection still works

---

## Testing

```bash
# Run app and verify:
# 1. Switch to Catalog mode > Ingredients group > Ingredient Catalog
# 2. Verify NO toggle button visible
# 3. Verify grid view displays
# 4. Test search/filter on grid
# 5. Test add/edit/delete ingredient
# 6. Switch to Make mode > create recipe > verify ingredient selector works
```

---

## Notes

This removal is safe because:
1. F052 Hierarchy Admin provides dedicated tree-based hierarchy management
2. The tree view in Ingredients tab was rarely used
3. Grid view is more efficient for browsing/filtering

## Activity Log

- 2026-01-16T02:38:25Z – null – lane=doing – Started implementation via workflow command
- 2026-01-16T02:40:54Z – null – lane=for_review – Removed tree view toggle and related code from ingredients_tab.py. IngredientTreeWidget preserved for recipe_form.py
- 2026-01-16T04:31:27Z – null – lane=doing – Started review
- 2026-01-16T04:31:47Z – null – lane=done – Review passed: tree view removed from ingredients_tab.py, IngredientTreeWidget preserved for recipe_form.py
