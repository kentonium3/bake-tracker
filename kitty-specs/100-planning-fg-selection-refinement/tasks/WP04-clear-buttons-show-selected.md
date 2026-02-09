---
work_package_id: WP04
title: Clear Buttons and Show All Selected
lane: "doing"
dependencies:
- WP02
base_branch: 100-planning-fg-selection-refinement-WP02
base_commit: edb0cb78f8dfec56da3b6d6d55f98924929028e0
created_at: '2026-02-09T22:41:31.159132+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 3 - UX Enhancements
assignee: ''
agent: ''
shell_pid: "31798"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-09T21:25:52Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 -- Clear Buttons and Show All Selected

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
spec-kitty implement WP04 --base WP03
```

Depends on WP02 (recipe selection persistence) and WP03 (FG selection persistence). Use WP03 as base since it includes WP01.

---

## Objectives & Success Criteria

Add two-level clear buttons (Clear All, Clear Finished Goods) and a "Show All Selected" toggle button. This implements User Stories 4 and 5 from the spec.

**Success Criteria:**
- "Clear All" resets recipes + FGs + quantities with confirmation dialog
- "Clear Finished Goods" resets only FGs + quantities, keeping recipe selections
- Canceling either clear dialog preserves all state
- "Show All Selected" shows only checked FGs regardless of filters
- Visual indicator shows count of selected items
- Changing any filter exits show-selected mode
- "No items selected" shown when toggle clicked with nothing selected

## Context & Constraints

- **Spec**: US4 (6 acceptance scenarios), US5 (5 acceptance scenarios)
- **Plan**: Phase 3, Phase 4
- **WP02**: RecipeSelectionFrame has `clear_selections()` method
- **WP03**: FGSelectionFrame has `clear_selections()`, `_selected_fg_ids`, `_fg_quantities`

**Key Constraints:**
- Clear buttons live on the planning_tab.py level (affect both frames)
- Show All Selected toggle lives on the FGSelectionFrame (only affects FG display)
- Clear only affects UI state — database is not written until Save

## Subtasks & Detailed Guidance

### Subtask T013 -- Add "Clear All" button with confirmation dialog

- **Purpose**: Add a button that resets the entire plan (recipes + FGs + quantities) after confirmation.
- **Files**: `src/ui/planning_tab.py`
- **Parallel?**: [P] Can run alongside T016-T018

**Steps**:

1. Add a "Clear All" button in the planning container, near the Save/Cancel buttons area:
```python
self._clear_all_button = ctk.CTkButton(
    self._button_frame,  # or appropriate container
    text="Clear All",
    width=100,
    fg_color="gray40",
    hover_color="gray30",
    command=self._handle_clear_all,
)
self._clear_all_button.pack(side="left", padx=5)
```

2. Implement `_handle_clear_all()`:
```python
def _handle_clear_all(self) -> None:
    """Handle Clear All button - reset entire plan."""
    from tkinter import messagebox
    confirmed = messagebox.askyesno(
        "Clear All",
        "Clear all recipes and finished goods? This resets the entire plan to blank.",
    )
    if not confirmed:
        return

    # Clear recipe selections
    self._recipe_selection_frame.clear_selections()

    # Clear FG selections
    self._fg_selection_frame.clear_selections()

    # Return both frames to blank state
    # (Re-show placeholders by resetting filter state)
    self._recipe_selection_frame._on_category_change("")
    self._fg_selection_frame._reset_to_blank()
```

### Subtask T014 -- Add "Clear Finished Goods" button with confirmation dialog

- **Purpose**: Add a button that resets only FG selections while keeping recipe selections.
- **Files**: `src/ui/planning_tab.py`
- **Parallel?**: [P] Can run alongside T013

**Steps**:

1. Add "Clear Finished Goods" button next to Clear All:
```python
self._clear_fgs_button = ctk.CTkButton(
    self._button_frame,
    text="Clear Finished Goods",
    width=150,
    fg_color="gray40",
    hover_color="gray30",
    command=self._handle_clear_fgs,
)
self._clear_fgs_button.pack(side="left", padx=5)
```

2. Implement `_handle_clear_fgs()`:
```python
def _handle_clear_fgs(self) -> None:
    """Handle Clear FGs button - reset only FG selections."""
    from tkinter import messagebox
    confirmed = messagebox.askyesno(
        "Clear Finished Goods",
        "Clear all finished good selections? Recipe selections will remain.",
    )
    if not confirmed:
        return

    # Clear only FG selections
    self._fg_selection_frame.clear_selections()

    # Reset FG frame to blank (recipes stay)
    self._fg_selection_frame._reset_to_blank()
```

### Subtask T015 -- Wire clear button callbacks and add `_reset_to_blank()` to FGSelectionFrame

- **Purpose**: Ensure clear actions properly reset all state and return frames to blank.
- **Files**: `src/ui/components/fg_selection_frame.py`, `src/ui/planning_tab.py`
- **Parallel?**: No (depends on T013, T014)

**Steps**:

1. Add `_reset_to_blank()` to FGSelectionFrame:
```python
def _reset_to_blank(self) -> None:
    """Reset the frame to blank state with placeholder."""
    # Clear rendered items
    for widget in self._scroll_frame.winfo_children():
        widget.destroy()
    self._checkbox_vars.clear()
    self._checkboxes.clear()
    self._fg_data.clear()
    self._quantity_vars.clear()
    self._quantity_entries.clear()
    self._feedback_labels.clear()

    # Reset filter dropdowns
    self._recipe_cat_var.set("")
    self._item_type_var.set("")
    self._yield_type_var.set("")

    # Show placeholder
    self._placeholder_label = ctk.CTkLabel(
        self._scroll_frame,
        text="Select filters to see available finished goods",
        font=ctk.CTkFont(size=12, slant="italic"),
        text_color=("gray50", "gray60"),
    )
    self._placeholder_label.pack(pady=40)

    # Reset count
    self._count_label.configure(text="0 of 0 selected")
```

2. Verify that `clear_selections()` (from WP03) clears `_selected_fg_ids` and `_fg_quantities` before `_reset_to_blank()` is called.

3. Add similar `_reset_to_blank()` to RecipeSelectionFrame if needed for "Clear All".

### Subtask T016 -- Add "Show All Selected" toggle button to FG frame

- **Purpose**: Add a toggle button that switches between filter-driven view and selected-only view.
- **Files**: `src/ui/components/fg_selection_frame.py`
- **Parallel?**: [P] Can run alongside T013-T015

**Steps**:

1. Add toggle state to `__init__`:
```python
self._show_selected_only: bool = False
```

2. Add toggle button after the filter frame:
```python
self._toggle_frame = ctk.CTkFrame(self, fg_color="transparent")
self._toggle_frame.pack(fill="x", padx=10, pady=(0, 5))

self._show_selected_button = ctk.CTkButton(
    self._toggle_frame,
    text="Show All Selected",
    width=150,
    command=self._toggle_show_selected,
)
self._show_selected_button.pack(side="left")

self._selected_indicator = ctk.CTkLabel(
    self._toggle_frame,
    text="",
    font=ctk.CTkFont(size=11),
)
self._selected_indicator.pack(side="left", padx=10)
```

### Subtask T017 -- Implement show-selected-only rendering mode

- **Purpose**: When "Show All Selected" is active, display only FGs from `_selected_fg_ids`.
- **Files**: `src/ui/components/fg_selection_frame.py`
- **Parallel?**: No (depends on T016)

**Steps**:

1. Implement `_toggle_show_selected()`:
```python
def _toggle_show_selected(self) -> None:
    """Toggle between filtered view and selected-only view."""
    self._save_current_selections()

    if self._show_selected_only:
        # Exit selected-only mode, restore filter view
        self._show_selected_only = False
        self._show_selected_button.configure(text="Show All Selected")
        self._selected_indicator.configure(text="")
        # Re-apply current filters
        self._on_filter_change("")
    else:
        # Enter selected-only mode
        if not self._selected_fg_ids:
            # No items selected
            self._selected_indicator.configure(text="No items selected")
            return

        self._show_selected_only = True
        self._show_selected_button.configure(text="Show Filtered View")
        count = len(self._selected_fg_ids)
        self._selected_indicator.configure(text=f"Showing {count} selected items")

        # Render only selected FGs
        self._render_selected_only()
```

2. Implement `_render_selected_only()`:
```python
def _render_selected_only(self) -> None:
    """Render only the currently selected FGs."""
    if self._event_id is None:
        return

    # Get FG objects for selected IDs
    with session_scope() as session:
        from src.models.finished_good import FinishedGood
        selected_fgs = (
            session.query(FinishedGood)
            .filter(FinishedGood.id.in_(self._selected_fg_ids))
            .all()
        )

    self._render_finished_goods(selected_fgs)
```

### Subtask T018 -- Auto-exit show-selected mode on filter dropdown change

- **Purpose**: When user changes any filter dropdown while in show-selected mode, exit that mode and apply the filter normally.
- **Files**: `src/ui/components/fg_selection_frame.py`
- **Parallel?**: No (depends on T017)

**Steps**:

1. Add check at the beginning of `_on_filter_change()`:
```python
def _on_filter_change(self, choice: str) -> None:
    """Handle any filter dropdown change."""
    # Exit show-selected mode if active (FR-012)
    if self._show_selected_only:
        self._show_selected_only = False
        self._show_selected_button.configure(text="Show All Selected")
        self._selected_indicator.configure(text="")

    # ... rest of filter logic
```

## Risks & Mitigations

- **Risk**: Clear All doesn't properly cascade to FG frame
  - **Mitigation**: Call `clear_selections()` on both frames explicitly
- **Risk**: Show All Selected with detached FG objects
  - **Mitigation**: Query FG objects by ID within a fresh session_scope
- **Risk**: messagebox import varies between tkinter versions
  - **Mitigation**: Use `from tkinter import messagebox` (standard pattern in bake-tracker)

## Definition of Done Checklist

- [ ] "Clear All" button visible in planning UI
- [ ] "Clear All" shows confirmation dialog with correct message
- [ ] "Clear All" resets recipes + FGs + quantities after confirmation
- [ ] "Clear All" cancel preserves all state
- [ ] "Clear Finished Goods" button visible
- [ ] "Clear Finished Goods" shows confirmation with correct message
- [ ] "Clear Finished Goods" resets only FGs + quantities
- [ ] "Clear Finished Goods" preserves recipe selections
- [ ] "Show All Selected" toggle displays only selected FGs
- [ ] Indicator shows "Showing N selected items"
- [ ] Button label changes to "Show Filtered View" when active
- [ ] Filter change exits show-selected mode
- [ ] "No items selected" shown when nothing selected
- [ ] All existing tests still pass

## Review Guidance

- **US4 Acceptance Scenarios**: Walk through all 6 scenarios from spec
- **US5 Acceptance Scenarios**: Walk through all 5 scenarios from spec
- Verify confirmation dialogs have correct text
- Verify cascade behavior of Clear All vs Clear FGs
- Verify show-selected mode renders all selected FGs regardless of filters
- Verify filter change exits show-selected mode

## Activity Log

- 2026-02-09T21:25:52Z -- system -- lane=planned -- Prompt created.
