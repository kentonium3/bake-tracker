---
work_package_id: WP02
title: Recipe Selection Filter-First
lane: "doing"
dependencies: []
base_branch: main
base_commit: 25479c9caf608df6fc4f8a2c1cd76a6c8df5ee38
created_at: '2026-02-09T21:32:52.569797+00:00'
subtasks:
- T005
- T006
- T007
phase: Phase 1 - Recipe Selection Enhancement
assignee: ''
agent: ''
shell_pid: "22294"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-09T21:25:52Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 -- Recipe Selection Filter-First

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP02
```

No dependencies on WP01 - can run in parallel. Branches from main.

---

## Objectives & Success Criteria

Replace the auto-load-all recipe selection in `RecipeSelectionFrame` with a category-filtered blank-start pattern. This implements User Story 1 from the spec.

**Success Criteria:**
- Recipe selection frame starts blank with placeholder text "Select recipe category to see available recipes"
- Category dropdown populated from `recipe_category_service.list_categories()` plus "All Categories" option
- Selecting a category loads only matching recipes
- Selecting "All Categories" loads all non-archived recipes
- Checking recipes and then changing category preserves prior selections
- Returning to original category shows checkboxes still checked

## Context & Constraints

- **Spec**: US1 - Recipe Category Filter-First Selection (5 acceptance scenarios)
- **Plan**: Phase 1, Design Decision D2
- **Current code**: `src/ui/components/recipe_selection_frame.py` (215 lines, simple checkbox list)
- **Current orchestration**: `src/ui/planning_tab.py` lines 549-576 (`_show_recipe_selection`)
- **Recipe service**: `recipe_service.get_recipes_by_category()` already exists at line 1527
- **Category service**: `recipe_category_service.list_categories()` exists

**Key Constraints:**
- Recipe.category is a plain string field matching RecipeCategory.name
- `get_all_recipes(include_archived=False)` returns only non-archived recipes
- `get_recipes_by_category(category)` filters by Recipe.category string
- Save callback must still pass list of selected recipe IDs to planning_tab

## Subtasks & Detailed Guidance

### Subtask T005 -- Refactor RecipeSelectionFrame with category filter and blank-start

- **Purpose**: Transform the frame from auto-populated to filter-first with blank start.
- **Files**: `src/ui/components/recipe_selection_frame.py`
- **Parallel?**: [P] Can run alongside T007

**Steps**:

1. **Add imports** at top:
```python
from src.services import recipe_category_service, recipe_service
```

2. **Add category dropdown** in `_setup_ui()`, between the header and scroll frame:
```python
# Filter frame
self._filter_frame = ctk.CTkFrame(self, fg_color="transparent")
self._filter_frame.pack(fill="x", padx=10, pady=(0, 5))

filter_label = ctk.CTkLabel(
    self._filter_frame,
    text="Category:",
    font=ctk.CTkFont(size=12),
)
filter_label.pack(side="left", padx=(0, 5))

self._category_var = ctk.StringVar(value="")
self._category_dropdown = ctk.CTkComboBox(
    self._filter_frame,
    variable=self._category_var,
    values=[],  # Populated later
    command=self._on_category_change,
    width=200,
    state="readonly",
)
self._category_dropdown.pack(side="left")
```

3. **Add placeholder** in the scroll frame (shown initially):
```python
self._placeholder_label = ctk.CTkLabel(
    self._scroll_frame,
    text="Select recipe category to see available recipes",
    font=ctk.CTkFont(size=12, slant="italic"),
    text_color=("gray50", "gray60"),
)
self._placeholder_label.pack(pady=40)
```

4. **Add new method** `populate_categories()` to load dropdown options:
```python
def populate_categories(self) -> None:
    """Load category options into the dropdown."""
    from src.services.database import session_scope
    with session_scope() as session:
        categories = recipe_category_service.list_categories(session=session)

    category_names = ["All Categories"] + [c.name for c in categories]
    self._category_dropdown.configure(values=category_names)
```

5. **Add new method** `_on_category_change(choice: str)`:
```python
def _on_category_change(self, choice: str) -> None:
    """Handle category dropdown change."""
    from src.services.database import session_scope

    # Save current selections before re-render
    self._save_current_selections()

    with session_scope() as session:
        if choice == "All Categories":
            recipes = recipe_service.get_all_recipes(include_archived=False)
        else:
            recipes = recipe_service.get_recipes_by_category(choice)

    self._render_recipes(recipes)
```

6. **Refactor `populate_recipes()`** to become `_render_recipes()`:
   - Move the checkbox rendering logic to `_render_recipes(recipes: List[Recipe])`
   - After rendering, restore selections from `_selected_recipe_ids`
   - Remove the placeholder label if it exists
   - `populate_recipes()` becomes a compatibility wrapper that calls `_render_recipes()`

7. **Modify blank-start behavior**: When frame is first shown, only populate categories and show placeholder. Do NOT auto-load recipes.

### Subtask T006 -- Add selection persistence across category changes

- **Purpose**: Ensure checked recipes remain checked even when they're filtered out of view by a category change.
- **Files**: `src/ui/components/recipe_selection_frame.py`
- **Parallel?**: No (depends on T005 structure)

**Steps**:

1. **Add persistence state** to `__init__`:
```python
self._selected_recipe_ids: set = set()  # Persists across category changes
```

2. **Add `_save_current_selections()` method**:
```python
def _save_current_selections(self) -> None:
    """Save current checkbox state to persistence set."""
    for recipe_id, var in self._recipe_vars.items():
        if var.get():
            self._selected_recipe_ids.add(recipe_id)
        else:
            self._selected_recipe_ids.discard(recipe_id)
```

3. **Modify checkbox creation in `_render_recipes()`** to restore state:
```python
# After creating checkbox:
var = ctk.BooleanVar(value=recipe.id in self._selected_recipe_ids)
```

4. **Modify `_update_count()`** to update persistence set:
```python
def _update_count(self) -> None:
    """Update count and sync persistence set."""
    for recipe_id, var in self._recipe_vars.items():
        if var.get():
            self._selected_recipe_ids.add(recipe_id)
        else:
            self._selected_recipe_ids.discard(recipe_id)

    selected = len(self._selected_recipe_ids)
    total = len(self._recipe_vars)
    visible_selected = sum(1 for var in self._recipe_vars.values() if var.get())
    self._count_label.configure(
        text=f"{visible_selected} of {total} shown selected ({selected} total)"
    )
```

5. **Modify `get_selected_ids()`** to return from persistence set:
```python
def get_selected_ids(self) -> List[int]:
    """Get ALL selected recipe IDs (including those not currently visible)."""
    self._save_current_selections()
    return list(self._selected_recipe_ids)
```

6. **Modify `set_selected()`** to populate persistence set:
```python
def set_selected(self, recipe_ids: List[int]) -> None:
    self._selected_recipe_ids = set(recipe_ids)
    # Restore visible checkboxes
    for recipe_id, var in self._recipe_vars.items():
        var.set(recipe_id in self._selected_recipe_ids)
    self._update_count()
```

7. **Add `clear_selections()` method** (needed by WP04):
```python
def clear_selections(self) -> None:
    """Clear all selections and return to blank state."""
    self._selected_recipe_ids.clear()
    for var in self._recipe_vars.values():
        var.set(False)
    self._update_count()
```

### Subtask T007 -- Update planning_tab.py orchestration for filtered recipe selection

- **Purpose**: Modify the planning tab to work with the new filter-first recipe selection.
- **Files**: `src/ui/planning_tab.py`
- **Parallel?**: [P] Can run alongside T005

**Steps**:

1. **Modify `_show_recipe_selection()`** (around line 549):
   - Instead of loading all recipes and calling `populate_recipes()`:
   - Call `_recipe_selection_frame.populate_categories()` to load the dropdown
   - Call `_recipe_selection_frame.set_selected(selected_ids)` to restore existing selections
   - Do NOT call `populate_recipes()` with all recipes — let the frame start blank

2. **Before**:
```python
def _show_recipe_selection(self, event_id):
    recipes = recipe_service.get_all_recipes(include_archived=False)
    self._recipe_selection_frame.populate_recipes(recipes, event_name)
    self._recipe_selection_frame.set_selected(selected_ids)
```

3. **After**:
```python
def _show_recipe_selection(self, event_id):
    self._recipe_selection_frame.populate_categories()
    with session_scope() as session:
        selected_ids = get_event_recipe_ids(session, event_id)
    self._recipe_selection_frame.set_selected(selected_ids)
    # Frame starts blank; user selects category to see recipes
```

4. **Verify save callback** still works: The save callback calls `get_selected_ids()` which now returns from the persistence set — this should work without changes.

## Risks & Mitigations

- **Risk**: No RecipeCategories in database → dropdown empty
  - **Mitigation**: If `list_categories()` returns empty, show "All Categories" only and auto-select it
- **Risk**: recipe_service functions create their own sessions
  - **Mitigation**: `get_recipes_by_category()` and `get_all_recipes()` already manage sessions internally; safe to call from UI
- **Risk**: Count display confusing when hidden recipes are selected
  - **Mitigation**: Show "X of Y shown selected (Z total)" format

## Definition of Done Checklist

- [ ] Recipe frame starts blank with placeholder text
- [ ] Category dropdown shows all categories + "All Categories"
- [ ] Selecting a category loads matching recipes
- [ ] Recipe selections persist across category changes
- [ ] `get_selected_ids()` returns all selected IDs including hidden ones
- [ ] Count label shows both visible and total selections
- [ ] `clear_selections()` method exists for future WP04 use
- [ ] All existing tests still pass (no regressions)

## Review Guidance

- **US1 Acceptance Scenarios**: Walk through all 5 scenarios from spec
- Verify blank-start behavior (no recipes loaded until category selected)
- Verify persistence: check cookies, switch to brownies, switch back, verify cookies still checked
- Verify "All Categories" loads every non-archived recipe
- Verify count shows accurate total including hidden selections
- Check for session management: no nested session_scope() calls

## Activity Log

- 2026-02-09T21:25:52Z -- system -- lane=planned -- Prompt created.
