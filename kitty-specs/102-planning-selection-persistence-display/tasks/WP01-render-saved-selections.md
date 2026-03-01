---
work_package_id: WP01
title: Render Saved Selections on Planning Tab Load
lane: "done"
dependencies: []
base_branch: main
base_commit: a47eaf74994131dc3d0b24c50e1e183c00a51e73
created_at: '2026-03-01T14:29:05.768199+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Core Implementation
assignee: ''
agent: "claude-opus"
shell_pid: "88222"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-03-01T14:25:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Render Saved Selections on Planning Tab Load

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

**Objective**: When the Planning tab loads an event with saved recipe/FG selections, display those selections immediately with contextual labels — eliminating the confusing blank placeholder that currently appears despite having data loaded into memory.

**Success Criteria**:
1. Events with saved recipe selections display those recipes with checked checkboxes within 1 second of event selection
2. Events with saved FG selections display those FGs with checked checkboxes and populated quantities within 1 second
3. Both frames show a "Saved plan selections" contextual label to distinguish from filter results
4. Events with NO selections still show blank placeholders (no regression)
5. Applying a filter after viewing saved selections transitions cleanly to filtered view with selections pre-checked
6. Existing save/cancel, filter persistence, and "Show All Selected" functionality work without regression
7. Selection count labels are accurate on initial load

## Context & Constraints

**Architecture constraint**: All changes are in the UI layer only. No service or model modifications. This is explicitly required by FR-007 in the spec.

**Key documents**:
- Spec: `kitty-specs/102-planning-selection-persistence-display/spec.md` (4 user stories, 8 FRs)
- Plan: `kitty-specs/102-planning-selection-persistence-display/plan.md` (3 design changes)
- Research: `kitty-specs/102-planning-selection-persistence-display/research.md` (root cause analysis)

**Root cause**: `set_selected()` and `set_selected_with_quantities()` populate in-memory persistence state (`_selected_recipe_ids`, `_selected_fg_ids`, `_fg_quantities`) but never trigger a render. The filter-first pattern expects the user to select a filter before items are displayed. When loading an event with existing selections, no filter is applied, so the frames remain blank.

**Files to modify**:
- `src/ui/components/recipe_selection_frame.py` — Add `render_saved_selections()` method
- `src/ui/components/fg_selection_frame.py` — Add `render_saved_selections()` method
- `src/ui/planning_tab.py` — Add conditional render triggers after `set_selected()` calls

**Implement command**: `spec-kitty implement WP01`

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add `render_saved_selections()` to RecipeSelectionFrame

**Purpose**: Create a public method that queries Recipe objects for the IDs in `_selected_recipe_ids` and renders them with a contextual label, so saved recipes are visible immediately when the Planning tab loads an event with a draft plan.

**Steps**:

1. **Add the new method** to `RecipeSelectionFrame` in `src/ui/components/recipe_selection_frame.py`. Place it after `set_selected()` (after line 303) as a logical grouping:

```python
def render_saved_selections(self) -> None:
    """
    Render saved selections on initial load (F102).

    Queries Recipe objects for IDs in the persistence set and renders
    them with a contextual label. Called by PlanningTab after
    set_selected() when loading an event with existing selections.
    """
    if not self._selected_recipe_ids:
        return

    # Query Recipe objects for saved IDs
    with session_scope() as session:
        recipes = (
            session.query(Recipe)
            .filter(Recipe.id.in_(self._selected_recipe_ids))
            .all()
        )

    if not recipes:
        return

    # Render the saved recipes (restores checkbox state from persistence set)
    self._render_recipes(recipes)

    # Add contextual label at the top of the scroll frame
    # Insert before the first recipe checkbox
    saved_label = ctk.CTkLabel(
        self._scroll_frame,
        text="Saved plan selections",
        font=ctk.CTkFont(size=11, slant="italic"),
        text_color=("gray50", "gray60"),
    )
    # Pack at top, before recipe checkboxes
    # Use pack_configure to reorder - need to pack first then move to top
    saved_label.pack(anchor="w", pady=(5, 2), padx=5)
    # Move to top of pack order (before recipe checkboxes)
    first_child = self._scroll_frame.winfo_children()[0]
    if first_child != saved_label:
        saved_label.pack_configure(before=first_child)
```

2. **Key implementation details**:
   - **Guard clause**: If `_selected_recipe_ids` is empty, return immediately — preserves blank placeholder for events with no selections
   - **DB query**: Uses `session_scope()` within the frame, consistent with `populate_categories()` (line 137-143) which already does this
   - **Rendering**: Calls `_render_recipes(recipes)` which clears existing children (line 200-201), creates checkboxes, and auto-checks saved IDs via line 222: `var = ctk.BooleanVar(value=recipe.id in self._selected_recipe_ids)`
   - **Contextual label**: Added AFTER `_render_recipes()` because that method clears all children first. The label is packed and then reordered to appear before recipe checkboxes using `pack_configure(before=...)`
   - **Label lifecycle**: Automatically destroyed when user applies a filter — `_on_category_change()` calls `_render_recipes()` which clears all scroll frame children (line 200-201)

3. **Edge case — deleted recipes**: If a saved recipe ID no longer exists in the database, the query silently excludes it. The count label will reflect only valid recipes. This matches the spec edge case: "should be silently excluded from display."

**Files**: `src/ui/components/recipe_selection_frame.py`
**Parallel?**: Yes — independent from T002 (different file)

---

### Subtask T002 – Add `render_saved_selections()` to FGSelectionFrame

**Purpose**: Create a public method that leverages the existing `_render_selected_only()` to display saved FG selections with quantities on initial load, with a contextual label.

**Steps**:

1. **Add the new method** to `FGSelectionFrame` in `src/ui/components/fg_selection_frame.py`. Place it after `set_selected_with_quantities()` (after line 550) for logical grouping:

```python
def render_saved_selections(self) -> None:
    """
    Render saved selections on initial load (F102).

    Sets up the selected-only view state and renders saved FGs using
    the existing _render_selected_only() method. Called by PlanningTab
    after set_selected_with_quantities() when loading an event with
    existing selections.
    """
    if not self._selected_fg_ids:
        return

    # Enter selected-only mode (same state as _toggle_show_selected)
    self._show_selected_only = True
    self._show_selected_button.configure(text="Show Filtered View")

    # Set contextual indicator label
    count = len(self._selected_fg_ids)
    self._selected_indicator.configure(
        text=f"Saved plan selections ({count} items)"
    )

    # Render only selected FGs (queries DB and calls _render_finished_goods)
    self._render_selected_only()
```

2. **Key implementation details**:
   - **Guard clause**: If `_selected_fg_ids` is empty, return immediately — preserves blank placeholder
   - **State setup**: Sets `_show_selected_only = True` and updates button text to "Show Filtered View" — this mirrors the state in `_toggle_show_selected()` (lines 767-768)
   - **Contextual label**: Uses the existing `_selected_indicator` label (already positioned at line 168-173) with text "Saved plan selections (N items)" instead of the usual "Showing N selected items"
   - **Rendering**: Delegates to `_render_selected_only()` (line 775-788) which queries FG objects by `_selected_fg_ids` and calls `_render_finished_goods()` — this already restores checkbox states and quantity values from persistence dicts
   - **Why a wrapper**: `_render_selected_only()` is a private method. The public `render_saved_selections()` encapsulates the state setup (mode flag, button text, indicator) and provides a clean API for PlanningTab

3. **Filter transition**: When the user applies a filter after viewing saved selections, `_on_filter_change()` (line 265-289) handles the transition:
   - Line 276-280: Checks `_show_selected_only`, sets it to `False`, resets button text and indicator
   - Then re-renders with filtered FGs — saved selections are pre-checked via persistence dicts
   - This is exactly the correct transition behavior — no new code needed

4. **"Show All Selected" toggle**: Works correctly because:
   - `_toggle_show_selected()` (line 750) checks `_show_selected_only` state
   - If True (set by our method), clicking toggles to False → exits selected-only mode → re-applies filters
   - If the user clicks back to selected-only, it re-enters with "Showing N selected items" (standard text, not "Saved plan selections" — this is correct, the contextual label is only for initial load)

**Files**: `src/ui/components/fg_selection_frame.py`
**Parallel?**: Yes — independent from T001 (different file)

---

### Subtask T003 – Wire Conditional Render Triggers in PlanningTab

**Purpose**: Add conditional calls to `render_saved_selections()` in PlanningTab after the existing `set_selected()` / `set_selected_with_quantities()` calls, so saved selections are rendered when loading events with draft plans.

**Steps**:

1. **In `_show_recipe_selection()`** (`src/ui/planning_tab.py`, after line 614):

   After `self._recipe_selection_frame.set_selected(selected_ids)`, add:
   ```python
   # F102: Render saved selections if event has existing plan
   if selected_ids:
       self._recipe_selection_frame.render_saved_selections()
   ```

   The conditional `if selected_ids:` preserves the blank-start behavior for events with no selections (FR-004).

2. **In `_show_fg_selection()`** (`src/ui/planning_tab.py`, after line 777):

   After `self._fg_selection_frame.set_selected_with_quantities(qty_tuples)`, add:
   ```python
   # F102: Render saved selections if event has existing plan
   if qty_tuples:
       self._fg_selection_frame.render_saved_selections()
   ```

   Same conditional pattern — preserves blank-start for events with no FG selections.

3. **Placement**: Both additions go AFTER `set_selected()` / `set_selected_with_quantities()` but BEFORE `pack()` — this ensures the frame renders its content before becoming visible, avoiding a visual flash.

**Key detail**: The recipe frame trigger is inside the try block (between line 614 and line 616 `self._original_recipe_selection = selected_ids.copy()`). The FG frame trigger is inside its try block (between line 777 and line 779 `self._original_fg_selection = qty_tuples.copy()`). Both are within the existing error handling.

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No — depends on T001 and T002 (calls methods they create). However, the changes are trivial (2 lines each) and can be written alongside T001/T002 if the method signatures are agreed upon.

---

### Subtask T004 – Add Regression Tests

**Purpose**: Ensure the blank-start and saved-selections display paths are both covered, preventing future regressions.

**Steps**:

1. **Create or add to test file** for planning tab selection rendering. Recommended location: `src/tests/test_planning_selection_display.py`

2. **Test cases to implement**:

   a. **Test blank-start preserved (recipe frame)**:
      - Create a RecipeSelectionFrame
      - Call `set_selected([])` (empty selections)
      - Verify `render_saved_selections()` is a no-op (no DB queries, no rendered items)
      - Verify the scroll frame still shows the placeholder

   b. **Test blank-start preserved (FG frame)**:
      - Create an FGSelectionFrame
      - Call `set_selected_with_quantities([])` (empty selections)
      - Verify `render_saved_selections()` is a no-op
      - Verify `_show_selected_only` remains False

   c. **Test saved selections rendered (recipe frame)**:
      - Create test recipes in the database
      - Set `_selected_recipe_ids` with those recipe IDs
      - Call `render_saved_selections()`
      - Verify recipes are rendered (check `_recipe_vars` is populated)
      - Verify selection count reflects saved selections
      - Verify contextual label "Saved plan selections" is present in scroll frame children

   d. **Test saved selections rendered (FG frame)**:
      - Create test FGs in the database
      - Call `set_selected_with_quantities([(fg1_id, 10), (fg2_id, 5)])`
      - Call `render_saved_selections()`
      - Verify `_show_selected_only` is True
      - Verify `_selected_indicator` text contains "Saved plan selections"
      - Verify FGs are rendered with quantities

   e. **Test deleted recipe handling**:
      - Set `_selected_recipe_ids` with an ID that doesn't exist in DB
      - Call `render_saved_selections()`
      - Verify no error raised, missing ID silently excluded

3. **Testing approach**: These are unit tests on the frame components. Use the existing `test_db` fixture for database setup. For CustomTkinter frame creation in tests, follow existing patterns in the test suite (check if there's an existing pattern for UI component testing — you may need to mock or use `ctk.CTk()` root window).

4. **Run tests**:
   ```bash
   ./run-tests.sh src/tests/test_planning_selection_display.py -v
   ```

**Files**: `src/tests/test_planning_selection_display.py` (new file)
**Parallel?**: Yes — can be written alongside T001/T002 once method signatures are defined

**Note**: If UI component testing proves difficult due to CustomTkinter initialization requirements, focus on the testable aspects (guard clauses, state mutations) and document any UI-specific behavior that requires manual verification.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Contextual label not cleaned up on filter | Stale "Saved plan selections" label visible | `_render_recipes()` clears all children (line 200-201); FG `_on_filter_change()` resets indicator (line 280). Both are already handled. |
| `session_scope()` in RecipeSelectionFrame | Potential session nesting | Follows existing pattern from `populate_categories()` (line 137-143). No nesting — this is a standalone scope. |
| Deleted recipe/FG IDs in saved selections | Crash or confusing display | `IN` query silently excludes missing IDs. Count reflects only valid items. |
| Rapid event switching | Stale render from previous event | Each `_show_recipe_selection()` / `_show_fg_selection()` call fully resets the frame state before rendering. |
| CustomTkinter test initialization | Tests fail to create UI components | Focus on testable state mutations; use existing test patterns or mock UI components if needed. |

---

## Definition of Done Checklist

- [ ] `RecipeSelectionFrame.render_saved_selections()` method implemented and functional
- [ ] `FGSelectionFrame.render_saved_selections()` method implemented and functional
- [ ] PlanningTab triggers rendering for events with saved selections
- [ ] Blank-start preserved for events with no selections
- [ ] Contextual "Saved plan selections" label displayed and auto-cleared on filter
- [ ] Selection count accurate on initial load
- [ ] Filter transition works correctly (saved selections pre-checked)
- [ ] "Show All Selected" toggle works after saved-selections render
- [ ] Save/Cancel functionality unchanged
- [ ] Regression tests pass
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Key acceptance checkpoints**:
1. Load an event with saved recipes → recipes displayed with checked checkboxes and "Saved plan selections" label
2. Load an event with saved FGs → FGs displayed with quantities, checked checkboxes, and contextual label
3. Load an event with NO selections → blank placeholders appear (no regression)
4. Apply a filter after viewing saved selections → clean transition to filtered view, saved items pre-checked
5. Click "Show All Selected" toggle after saved-selections render → correct toggle behavior
6. Save and cancel functionality → unchanged behavior
7. Switch rapidly between events → each event loads its own selections correctly

**Code review focus**:
- Verify `session_scope()` usage is standalone (no nesting with other scopes)
- Verify contextual label is destroyed by existing clear-all-children pattern
- Verify guard clauses handle empty selection sets correctly
- Check that no service or model files were modified (FR-007 constraint)

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:
1. Scroll to the bottom of this file (Activity Log section below "Valid lanes")
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – lane=<lane> – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Lane MUST match the frontmatter `lane:` field exactly
6. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:
```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – lane=<lane> – <brief action description>
```

**Initial entry**:
- 2026-03-01T14:25:50Z – system – lane=planned – Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task <WPID> --to <lane> --note "message"` (recommended)

The CLI command updates both frontmatter and activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-03-01T14:29:06Z – claude-opus – shell_pid=86639 – lane=doing – Assigned agent via workflow command
- 2026-03-01T14:44:43Z – claude-opus – shell_pid=86639 – lane=for_review – Ready for review: All 4 subtasks complete. render_saved_selections() added to both frames, PlanningTab wired up, 8 regression tests passing.
- 2026-03-01T14:50:28Z – claude-opus – shell_pid=88222 – lane=doing – Started review via workflow command
- 2026-03-01T14:51:53Z – claude-opus – shell_pid=88222 – lane=done – Review passed: All 8 FRs verified. UI-only changes, no session nesting, guard clauses correct, contextual labels auto-cleared on filter, 8 regression tests pass.
