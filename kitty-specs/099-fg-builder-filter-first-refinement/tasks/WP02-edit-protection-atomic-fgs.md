---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
title: "Edit Protection for Atomic FGs"
phase: "Phase 1 - Edit Protection"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-08T23:13:33Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 -- Edit Protection for Atomic FGs

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

Block editing of BARE (atomic) FinishedGoods from the Finished Goods tab. BARE FGs are auto-generated wrappers around FinishedUnits and should not be edited directly — users should edit the source recipe instead.

**Success criteria**:
- Clicking Edit on a BARE FG shows an info message: "This item is auto-created from a recipe. Edit the recipe to change it."
- Clicking Edit on a BUNDLE FG opens the builder dialog normally
- Double-clicking a BARE FG shows the same block message
- Double-clicking a BUNDLE FG opens the builder dialog normally

## Context & Constraints

**Primary file**: `src/ui/finished_goods_tab.py`

**Key references**:
- Spec: `kitty-specs/099-fg-builder-filter-first-refinement/spec.md` (User Story 4)
- Plan: `kitty-specs/099-fg-builder-filter-first-refinement/plan.md` (Design Decision D5)
- Research: `kitty-specs/099-fg-builder-filter-first-refinement/research.md` (R5)

**Architecture constraints**:
- `AssemblyType.BARE` = atomic, auto-generated from FinishedUnit (1 component, no packaging)
- `AssemblyType.BUNDLE` = user-built multi-component assembly
- The `assembly_type` field is on the `FinishedGood` model, always populated (default=BUNDLE)
- Edit is triggered from two paths: Edit button (`_edit_finished_good()`) and double-click (`_on_row_double_click()`)
- The FG is loaded via `finished_good_service.get_finished_good_by_id()` which returns the full object with `assembly_type`

**Parallelization**: This WP modifies `finished_goods_tab.py` only. It can be implemented in parallel with WP01 which modifies `finished_good_builder.py`.

**Implementation command** (no dependencies):
```bash
spec-kitty implement WP02
```

## Subtasks & Detailed Guidance

### Subtask T007 -- Add Assembly Type Guard in `_edit_finished_good()`

**Purpose**: The `_edit_finished_good()` method (line 443) loads a FinishedGood and opens the builder dialog. Add a check after loading to block editing of BARE FGs.

**Steps**:

1. Add the `AssemblyType` import at the top of the file:
   ```python
   from src.models.assembly_type import AssemblyType
   ```

2. In `_edit_finished_good()` (line 443), after the FG is loaded via service (line 449-453), add the guard check BEFORE opening the builder dialog (line 456):

   ```python
   def _edit_finished_good(self):
       """Show builder dialog to edit the selected finished good."""
       if not self.selected_finished_good:
           return

       try:
           fg = finished_good_service.get_finished_good_by_id(
               self.selected_finished_good.id
           )
       except ServiceError as e:
           handle_error(e, parent=self, operation="Load finished good for editing")
           return

       # Block editing atomic (BARE) FGs - they are auto-created from recipes
       if fg.assembly_type == AssemblyType.BARE:
           from tkinter import messagebox
           messagebox.showinfo(
               "Cannot Edit",
               "This item is auto-created from a recipe. "
               "Edit the recipe to change it.",
               parent=self,
           )
           return

       dialog = FinishedGoodBuilderDialog(self, finished_good=fg)
       # ... rest of method unchanged
   ```

3. **Note**: Use `tkinter.messagebox.showinfo` rather than CustomTkinter's dialog to keep the interaction lightweight (simple info message, not a custom dialog). Check if there's a `show_info` utility already available in the project:
   ```bash
   grep -rn "show_info\|showinfo" src/ui/ --include="*.py" | head -10
   ```
   If a `show_info` utility exists, use that instead of raw `messagebox.showinfo`.

**Files**: `src/ui/finished_goods_tab.py`
**Parallel?**: No — T008 and T009 depend on the pattern established here.

**Validation**:
- [ ] Clicking Edit on a BARE FG shows the info message
- [ ] Clicking Edit on a BUNDLE FG opens the builder normally
- [ ] The info message text matches: "This item is auto-created from a recipe. Edit the recipe to change it."

---

### Subtask T008 -- User-Facing Info Message for Blocked Edits

**Purpose**: Ensure the block message is clear, actionable, and uses consistent UI patterns.

**Steps**:

1. Verify the message copy is correct: "This item is auto-created from a recipe. Edit the recipe to change it."

2. Check what dialog utilities exist in the project for info messages:
   ```bash
   grep -rn "def show_info\|def show_message\|from.*dialogs.*import" src/ui/ --include="*.py" | head -20
   ```

3. If a project utility like `show_info()` exists (check `src/ui/widgets/dialogs.py` or similar), use that instead of raw `tkinter.messagebox`. This ensures consistent styling with the rest of the app.

4. If no utility exists, `tkinter.messagebox.showinfo` is acceptable for this simple use case.

5. **Message title**: "Cannot Edit" — clear and specific.
   **Message body**: "This item is auto-created from a recipe. Edit the recipe to change it." — explains why AND what to do instead.

**Files**: `src/ui/finished_goods_tab.py`
**Parallel?**: No — directly related to T007.

**Validation**:
- [ ] Message uses project-consistent dialog pattern
- [ ] Message title is "Cannot Edit"
- [ ] Message body explains both "why" and "what instead"

---

### Subtask T009 -- Add Guard to Double-Click Edit Path

**Purpose**: The `_on_row_double_click()` method (line 424) is an alternate path to editing. It needs the same guard check.

**Steps**:

1. Read the current `_on_row_double_click()` implementation to understand the flow:
   ```python
   def _on_row_double_click(self, event):
       """Handle row double-click (opens edit dialog)."""
       # ...
       self._edit_finished_good()
   ```

2. If `_on_row_double_click()` simply calls `_edit_finished_good()`, the guard from T007 already covers this path. **No additional changes needed.**

3. If `_on_row_double_click()` has its own separate logic that opens the builder directly, add the same guard check:
   ```python
   # After loading the FG:
   if fg.assembly_type == AssemblyType.BARE:
       from tkinter import messagebox
       messagebox.showinfo(
           "Cannot Edit",
           "This item is auto-created from a recipe. "
           "Edit the recipe to change it.",
           parent=self,
       )
       return
   ```

4. Based on the codebase research, `_on_row_double_click()` at line 424-426 does call `self._edit_finished_good()`, so the guard from T007 should already cover it. Verify this is still the case and document it.

**Files**: `src/ui/finished_goods_tab.py`
**Parallel?**: No — depends on T007.

**Validation**:
- [ ] Double-clicking a BARE FG shows the block message (not the builder)
- [ ] Double-clicking a BUNDLE FG opens the builder normally
- [ ] Both Edit button and double-click use the same code path (DRY)

## Risks & Mitigations

- **FG loaded without assembly_type**: The `FinishedGood` model has `assembly_type` with `default=AssemblyType.BUNDLE`. All FGs should have this field populated. If somehow None, treat as BUNDLE (allow editing) since that's the safer default.
- **Selected FG is stale**: The `selected_finished_good` attribute may be a lightweight object without `assembly_type`. The service call `get_finished_good_by_id()` at line 449 loads the full object, so `fg.assembly_type` should always be available after that call.
- **Import conflicts**: `AssemblyType` import may already exist or conflict. Check existing imports at the top of `finished_goods_tab.py` before adding.

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] BARE FGs cannot be edited via Edit button
- [ ] BARE FGs cannot be edited via double-click
- [ ] BUNDLE FGs can still be edited normally (no regression)
- [ ] Block message is clear and actionable
- [ ] No import errors or conflicts

## Review Guidance

- **Key test**: Create or find a BARE FG (auto-generated from a recipe) and a BUNDLE FG in the list. Click Edit on each — BARE should show message, BUNDLE should open builder.
- **Double-click test**: Same test with double-click instead of Edit button.
- **Regression test**: Edit an existing BUNDLE FG, verify builder opens with components loaded, make a change, save — should work exactly as before.
- **Edge case**: If all FGs in the list are BARE (no BUNDLE FGs exist), the Edit button should always show the block message.

## Activity Log

- 2026-02-08T23:13:33Z -- system -- lane=planned -- Prompt created.
