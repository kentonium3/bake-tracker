---
work_package_id: WP01
title: Filter-First Builder Dialog
lane: "doing"
dependencies: []
base_branch: main
base_commit: 847afa7bf6ac7099bb461302afd2ce53a409309f
created_at: '2026-02-08T23:58:30.885328+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Core UI Changes
assignee: ''
agent: ''
shell_pid: "82425"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T23:13:33Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 -- Filter-First Builder Dialog

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

Transform the FinishedGoods Builder dialog from auto-load-all to a blank-start, filter-driven workflow.

**Success criteria**:
- Dialog opens with no items loaded and shows placeholder text
- Filter options are "Finished Units" / "Existing Assemblies" / "Both" (not "All" / "Bare Items Only")
- Items load only after a filter option is selected
- Search has 300ms debounce (no query on every keystroke)
- Changing filters with selections present shows a warning dialog
- If user cancels filter change, filter reverts to previous value

## Context & Constraints

**Primary file**: `src/ui/builders/finished_good_builder.py`

**Key references**:
- Spec: `kitty-specs/099-fg-builder-filter-first-refinement/spec.md`
- Plan: `kitty-specs/099-fg-builder-filter-first-refinement/plan.md` (Design Decisions D1-D4)
- Research: `kitty-specs/099-fg-builder-filter-first-refinement/research.md` (R1, R2, R4, R6, R7)

**Architecture constraints**:
- No service layer changes needed. Existing service methods handle all filtering.
- `finished_unit_service.get_all_finished_units(name_search=..., category=...)` — already supports needed filters
- `finished_good_service.get_all_finished_goods(name_search=..., assembly_type=...)` — already supports needed filters
- `AssemblyType.BARE` = atomic items from recipes; `AssemblyType.BUNDLE` = user-built assemblies
- UI follows existing CustomTkinter patterns in the builder

**Implementation command** (no dependencies):
```bash
spec-kitty implement WP01
```

## Subtasks & Detailed Guidance

### Subtask T001 -- Remove Auto-Load and Add Blank Start Placeholder

**Purpose**: The dialog currently calls `_on_food_filter_changed()` in `_set_initial_state()` (line 213), which immediately queries ALL FinishedUnits and FinishedGoods. Remove this call and show a placeholder instead.

**Steps**:

1. In `_set_initial_state()` (line 204), remove the line `self._on_food_filter_changed()` (line 213) from the `else` branch (create mode). Keep the edit-mode branch unchanged.

2. In `_create_food_step_content()`, after creating `_food_item_list_frame` (line 339), add a placeholder label inside it:
   ```python
   self._food_placeholder_label = ctk.CTkLabel(
       self._food_item_list_frame,
       text="Select item type above to see available items",
       text_color="gray",
       wraplength=400,
   )
   self._food_placeholder_label.pack(padx=20, pady=40)
   ```

3. In `_render_food_items()`, remove the placeholder label if it exists before rendering items:
   ```python
   if hasattr(self, '_food_placeholder_label') and self._food_placeholder_label:
       self._food_placeholder_label.destroy()
       self._food_placeholder_label = None
   ```

**Files**: `src/ui/builders/finished_good_builder.py`
**Parallel?**: No — T002-T006 build on this.

**Validation**:
- [ ] Dialog opens with blank item list showing placeholder text
- [ ] No database queries execute on dialog open
- [ ] Edit mode still works normally (loads existing data)

---

### Subtask T002 -- Replace Filter Toggle with New Options

**Purpose**: Replace the "All" / "Bare Items Only" segmented button with "Finished Units" / "Existing Assemblies" / "Both". The button should start with no selection (or a neutral default) to support the blank-start UX.

**Steps**:

1. In `_create_food_step_content()`, find the `CTkSegmentedButton` creation (lines 317-325). Change the values:
   ```python
   self._food_type_var = ctk.StringVar(value="")  # No default selection
   self._food_type_toggle = ctk.CTkSegmentedButton(
       filter_frame,
       values=["Finished Units", "Existing Assemblies", "Both"],
       variable=self._food_type_var,
       command=lambda _: self._on_food_filter_changed(),
   )
   ```

2. **Important**: Test whether `CTkSegmentedButton` supports an empty string as the initial value (no segment selected). If it auto-selects the first value, you may need to handle this differently:
   - Option A: Set default to empty string and handle in query logic
   - Option B: Disable the toggle until user clicks, then enable
   - Option C: Accept that a default is selected and trigger the query (less ideal but functional)

   The preferred approach is Option A — if the `CTkSegmentedButton` doesn't support empty default, initialize to empty string anyway and guard the query logic to skip when empty.

**Files**: `src/ui/builders/finished_good_builder.py`
**Parallel?**: No — depends on T001 being in place.

**Validation**:
- [ ] Three filter options visible: "Finished Units", "Existing Assemblies", "Both"
- [ ] Old "All" / "Bare Items Only" labels are gone
- [ ] Dialog starts with no filter selected (or gracefully handles default)

---

### Subtask T003 -- Update Query Logic for New Filter Values

**Purpose**: Modify `_query_food_items()` to map the new filter values to the correct service calls.

**Steps**:

1. Replace the body of `_query_food_items()` (lines 368-438) with new filter logic:

   ```python
   def _query_food_items(self) -> List[Dict]:
       """Query items matching current filter state.

       Filter mapping:
       - "Finished Units": FinishedUnits only (atomic recipe outputs)
       - "Existing Assemblies": FinishedGoods where assembly_type=BUNDLE
       - "Both": FinishedUnits + BUNDLE FinishedGoods
       - "" (empty): No query (blank start)
       """
       type_filter = self._food_type_var.get()
       category_filter = self._food_category_var.get()
       search_text = self._food_search_var.get().strip().lower()

       # Blank start: no filter selected yet
       if not type_filter:
           return []

       items = []

       # Include FinishedUnits when "Finished Units" or "Both"
       if type_filter in ("Finished Units", "Both"):
           try:
               all_units = finished_unit_service.get_all_finished_units(
                   name_search=search_text if search_text else None,
                   category=category_filter if category_filter != "All Categories" else None,
               )
           except Exception:
               all_units = []

           for fu in all_units:
               key = f"finished_unit:{fu.id}"
               items.append({
                   "key": key,
                   "id": fu.id,
                   "display_name": fu.display_name,
                   "category": fu.category or "",
                   "assembly_type": AssemblyType.BARE,
                   "comp_type": "finished_unit",
                   "comp_id": fu.id,
               })

       # Include assembled FinishedGoods when "Existing Assemblies" or "Both"
       if type_filter in ("Existing Assemblies", "Both"):
           try:
               all_fgs = finished_good_service.get_all_finished_goods(
                   name_search=search_text if search_text else None,
                   assembly_type=AssemblyType.BUNDLE,
               )
           except Exception:
               all_fgs = []

           for fg in all_fgs:
               # Self-reference prevention in edit mode
               if self._is_edit_mode and fg.id == self._finished_good_id:
                   continue

               key = f"finished_good:{fg.id}"
               items.append({
                   "key": key,
                   "id": fg.id,
                   "display_name": fg.display_name,
                   "category": self._get_fg_category(fg),
                   "assembly_type": fg.assembly_type,
                   "comp_type": "finished_good",
                   "comp_id": fg.id,
               })

       return items
   ```

2. **Key changes from current logic**:
   - Uses service-level `name_search` and `category` filters instead of loading all and filtering in-memory
   - Only queries BUNDLE FGs (not BARE) when showing assemblies — BARE FGs are represented by their FinishedUnits
   - Returns empty list when no filter selected (blank start)
   - In-memory category filtering for FGs via `_get_fg_category()` still needed (service doesn't support FG category filter)

**Files**: `src/ui/builders/finished_good_builder.py`
**Parallel?**: No — depends on T002 for new filter values.

**Validation**:
- [ ] "Finished Units" shows only FinishedUnits (no assembled FGs)
- [ ] "Existing Assemblies" shows only BUNDLE FinishedGoods
- [ ] "Both" shows both types
- [ ] Empty filter value returns empty list (no query)
- [ ] Category and search filters work correctly with each type
- [ ] Self-reference prevention still works in edit mode

---

### Subtask T004 -- Add 300ms Search Debounce

**Purpose**: Currently, every keystroke in the search box triggers a query (`<KeyRelease>` binding at line 336). Add a 300ms debounce so the query only fires after the user stops typing.

**Steps**:

1. Add a `_search_debounce_id` instance variable in `__init__()`:
   ```python
   self._search_debounce_id = None
   ```

2. Replace the search entry's `<KeyRelease>` binding (line 336) with a debounced version:
   ```python
   self._food_search_entry.bind("<KeyRelease>", self._on_search_key_release)
   ```

3. Add the debounce handler method:
   ```python
   def _on_search_key_release(self, event=None) -> None:
       """Debounce search input by 300ms."""
       if self._search_debounce_id:
           self.after_cancel(self._search_debounce_id)
       self._search_debounce_id = self.after(300, self._on_food_filter_changed)
   ```

**Files**: `src/ui/builders/finished_good_builder.py`
**Parallel?**: No — modifies the same file as T001-T003.

**Notes**: The `after()` and `after_cancel()` methods are built into all tkinter widgets. No import needed.

**Validation**:
- [ ] Typing in search does not trigger immediate query
- [ ] Query fires 300ms after last keystroke
- [ ] Rapid typing cancels previous timer (only final state queried)

---

### Subtask T005 -- Track Previous Filter Values for Revert

**Purpose**: When the user cancels a filter change (T006), the filter must revert to its previous value. Track previous values in instance variables.

**Steps**:

1. Add instance variables in `__init__()`:
   ```python
   self._prev_food_type = ""
   self._prev_food_category = "All Categories"
   ```

2. Update `_on_food_filter_changed()` to save current values before processing:
   - Save the new current values as "previous" AFTER the filter change is confirmed (not cancelled)
   - The exact placement depends on T006's confirmation flow

**Files**: `src/ui/builders/finished_good_builder.py`
**Parallel?**: No — tightly coupled with T006.

**Validation**:
- [ ] Previous values track the last confirmed filter state
- [ ] Initial state has empty type and "All Categories"

---

### Subtask T006 -- Add Filter Change Warning with Revert-on-Cancel

**Purpose**: When the user has items selected and changes the type or category filter, show a confirmation dialog. If cancelled, revert the filter to its previous value.

**Steps**:

1. Modify `_on_food_filter_changed()` to check for existing selections before proceeding:

   ```python
   def _on_food_filter_changed(self) -> None:
       """Re-query and re-render the food item list based on current filters."""
       current_type = self._food_type_var.get()
       current_category = self._food_category_var.get()

       # Check if selections exist and filter actually changed
       if self._food_selections and (
           current_type != self._prev_food_type
           or current_category != self._prev_food_category
       ):
           confirmed = show_confirmation(
               "Clear Selections?",
               "Changing filters will clear your current selections. Continue?",
               parent=self,
           )
           if not confirmed:
               # Revert to previous values
               self._food_type_var.set(self._prev_food_type)
               self._food_category_var.set(self._prev_food_category)
               return

           # Clear selections on confirm
           self._food_selections.clear()

       # Update previous values
       self._prev_food_type = current_type
       self._prev_food_category = current_category

       # Skip query if no filter selected (blank start)
       if not current_type:
           return

       # Query and render
       items = self._query_food_items()
       self._render_food_items(items)
   ```

2. Verify that `show_confirmation` is already imported (it is, at line 30).

3. **Edge case**: Category combo change also triggers this handler (line 313). The same warning applies for category changes when selections exist.

4. **Edge case**: Search text changes (via debounce in T004) should NOT trigger the warning — search narrows within the same filter. Only type and category changes should warn. Modify to only check type/category changes:
   - The debounce timer in T004 calls `_on_food_filter_changed()` for search.
   - Add a parameter or separate method to distinguish search-triggered calls from filter-triggered calls.
   - Simplest approach: split into `_on_food_filter_changed()` (for type/category) and `_on_food_search_changed()` (for search, no warning).

**Files**: `src/ui/builders/finished_good_builder.py`
**Parallel?**: No — depends on T005 for previous value tracking.

**Validation**:
- [ ] No warning when changing filters with no selections
- [ ] Warning shown when changing type filter with selections
- [ ] Warning shown when changing category filter with selections
- [ ] Cancel reverts filter to previous value
- [ ] Confirm clears selections and reloads items
- [ ] Search changes do NOT trigger the warning
- [ ] Filter revert updates both the variable and the widget display

## Risks & Mitigations

- **CTkSegmentedButton empty default**: May not support deselected state. Test early; if not supported, use a neutral default and guard query logic.
- **show_confirmation behavior**: Verify it returns True/False (not None). Check existing usage patterns in the codebase.
- **Widget update on variable set**: When reverting filter via `_food_type_var.set()`, verify the `CTkSegmentedButton` visually updates. Some CustomTkinter widgets may need explicit `.set()` call on the widget itself.
- **Edit mode interactions**: Ensure edit mode still works correctly — `_load_existing_data()` handles its own flow and shouldn't be affected by blank start changes.

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] Dialog opens blank with placeholder text (no auto-load)
- [ ] Three filter options work correctly
- [ ] Search has 300ms debounce
- [ ] Filter change warning works with revert-on-cancel
- [ ] Edit mode still works correctly
- [ ] No regressions in Step 2 (Materials) or Step 3 (Review & Save)

## Review Guidance

- **Key test**: Open dialog, verify blank start. Select "Finished Units", verify only FUs load. Switch to "Existing Assemblies", verify only BUNDLE FGs load. Select "Both", verify both types.
- **Filter warning test**: Select some items, change filter, verify warning. Cancel and verify revert. Confirm and verify selections cleared.
- **Search test**: Type quickly, verify query fires once after 300ms pause.
- **Edit mode test**: Open builder in edit mode, verify existing data loads correctly (unaffected by blank start).

## Activity Log

- 2026-02-08T23:13:33Z -- system -- lane=planned -- Prompt created.
