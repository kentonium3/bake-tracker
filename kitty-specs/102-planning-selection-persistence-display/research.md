# Research: Planning Selection Persistence Display

**Feature**: 102-planning-selection-persistence-display
**Date**: 2026-02-28

## Research Summary

No external research needed — this is a UI-only rendering fix in an existing codebase with well-understood components.

## Key Findings

### 1. Root Cause Confirmed

**Decision**: The blank display is caused by `set_selected()` and `set_selected_with_quantities()` populating in-memory state without triggering a render.

**Rationale**: Both `_show_recipe_selection()` (planning_tab.py:597-614) and `_show_fg_selection()` (planning_tab.py:770-777) correctly query the database and load selections into the frame's persistence layer. However, no render method is called afterward because the filter-first pattern expects the user to select a filter before any items are displayed.

**Alternatives considered**: None — the root cause is clear and unambiguous.

### 2. Recipe Frame: render_saved_selections() Approach

**Decision**: Add a `render_saved_selections()` method to RecipeSelectionFrame that queries Recipe objects by saved IDs and renders them using the existing `_render_recipes()` method.

**Rationale**: RecipeSelectionFrame has no equivalent of FGSelectionFrame's `_render_selected_only()`. The new method follows the same pattern: query objects by ID set, pass to the existing render method. This shows only selected recipes (not the entire catalog), keeping the display focused.

**Key implementation detail**: The method must query `Recipe` objects from the database using `_selected_recipe_ids`. This requires a `session_scope()` call within the frame, which is consistent with how `populate_categories()` already works (line 139).

### 3. FG Frame: Reuse _render_selected_only()

**Decision**: Call existing `_render_selected_only()` after `set_selected_with_quantities()` when selections are non-empty.

**Rationale**: The method already exists (lines 775-788), queries FG objects by `_selected_fg_ids`, and calls `_render_finished_goods()`. It's exactly the right behavior for initial load display.

**Key implementation detail**: Must also set `_show_selected_only = True` and update the indicator label to match the visual state. The "Show All Selected" button text should show "Show Filtered View" since we're in the selected-only view.

### 4. Contextual Label Approach

**Decision**: Add a brief label (e.g., "Showing saved plan selections") in the scroll area above the rendered items, distinguishable from filter result labels.

**Rationale**: User confirmed they want a contextual label to distinguish saved selections from filter results. The label should be visually distinct (italic, muted color) and disappear when the user applies a filter.

**Implementation**: For RecipeSelectionFrame, add a label before rendering saved recipes. For FGSelectionFrame, update `_selected_indicator` (already exists at line 770) with appropriate text.

### 5. Filter Transition Behavior

**Decision**: When the user applies a filter after viewing saved selections, replace the saved-selections view with the filtered view. Saved selections remain pre-checked in the filtered results (existing persistence behavior).

**Rationale**: User confirmed option B — merge/pre-check behavior. This is already how both frames work once a filter is applied (selections persist across filter changes). No new logic needed for the transition.

**Recipe frame**: `_on_category_change()` already calls `_save_current_selections()` then `_render_recipes()` — saved selections will be pre-checked automatically via line 222.

**FG frame**: `_on_filter_change()` already handles this — filter application renders filtered FGs with selections pre-checked. If `_show_selected_only` was True (from initial load), applying a filter should exit that mode and enter normal filter mode.

### 6. Conditional Rendering Logic

**Decision**: In planning_tab.py, after calling `set_selected()` / `set_selected_with_quantities()`, check if selections are non-empty. If yes, trigger the saved-selections render. If no, leave the blank placeholder.

**Rationale**: Simple conditional preserves blank-start for new events while adding the render call for events with existing data.

**Recipe frame trigger point**: `_show_recipe_selection()` line 614 — after `set_selected(selected_ids)`, add: `if selected_ids: self._recipe_selection_frame.render_saved_selections()`

**FG frame trigger point**: `_show_fg_selection()` line 777 — after `set_selected_with_quantities(qty_tuples)`, add: `if qty_tuples: self._fg_selection_frame.render_saved_selections()`
