---
work_package_id: WP07
title: Tab Integration & Polish
lane: "done"
dependencies: [WP06]
base_branch: 097-finished-goods-builder-ui-WP06
base_commit: 8a0fc0ded00f910027a9383b5efc42c56cef54ab
created_at: '2026-02-07T00:49:54.543369+00:00'
subtasks:
- T032
- T033
- T034
- T035
- T036
phase: Phase D - Polish
assignee: ''
agent: "claude-opus"
shell_pid: "34512"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-06T23:51:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 -- Tab Integration & Polish

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- FinishedGoodsTab launches builder dialog for both Create and Edit flows
- "+ Create Finished Good" button replaces the existing "+ Add" button
- Double-click on list item opens builder in edit mode
- "Edit" button opens builder in edit mode for selected item
- Finished Goods list refreshes after successful save
- Existing `FinishedGoodFormDialog` is no longer called from this tab (but not deleted)
- Integration tests verify end-to-end create and edit flows

**Implementation command**: `spec-kitty implement WP07 --base WP06`

## Context & Constraints

- **Feature**: 097-finished-goods-builder-ui
- **Plan**: Design Decision D-007 (tab integration)
- **Existing file**: `src/ui/finished_goods_tab.py` — current integration with `FinishedGoodFormDialog`
- **Current patterns** (from codebase research):
  - `_add_finished_good()` at line 419: Creates `FinishedGoodFormDialog(self, title="Add New Finished Good")`
  - `_edit_finished_good()` at line 469: Creates `FinishedGoodFormDialog(self, finished_good=fg)`
  - `_on_row_double_click()` at line 414: Calls `_edit_finished_good()`
  - Both use `self.wait_window(dialog)` + `dialog.result` pattern
- **Import change**: Replace `FinishedGoodFormDialog` import with `FinishedGoodBuilderDialog`
- **Result format**: Builder returns same-shaped result dict — `{"finished_good_id": int, "display_name": str}`

## Subtasks & Detailed Guidance

### Subtask T032 -- Update _add_finished_good() to launch FinishedGoodBuilderDialog

- **Purpose**: Replace the existing form dialog with the new builder for creating FinishedGoods.

- **Steps**:
  1. Update import in `finished_goods_tab.py`:
     ```python
     # Replace:
     from src.ui.forms.finished_good_form import FinishedGoodFormDialog
     # With:
     from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
     ```
  2. Modify `_add_finished_good()`:
     ```python
     def _add_finished_good(self):
         """Show builder dialog to create a new finished good."""
         dialog = FinishedGoodBuilderDialog(self)
         self.wait_window(dialog)
         result = dialog.result

         if result:
             show_success(
                 "Success",
                 f"Finished good '{result['display_name']}' created successfully",
                 parent=self,
             )
             self.refresh()
             self._update_status(f"Created: {result['display_name']}", success=True)
     ```
  3. Remove the old result-processing code that manually called service methods — the builder handles create internally

- **Files**: `src/ui/finished_goods_tab.py`

- **Notes**:
  - The old code extracted components from result, mapped assembly_type, and called service — the builder now handles all of this internally
  - The new result dict is simpler: just `finished_good_id` and `display_name` for confirmation messaging
  - Error handling is now inside the builder dialog (errors shown inline, not propagated to tab)

### Subtask T033 -- Update _edit_finished_good() to launch FinishedGoodBuilderDialog in edit mode

- **Purpose**: Replace the existing form dialog with the builder for editing FinishedGoods.

- **Steps**:
  1. Modify `_edit_finished_good()`:
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

         dialog = FinishedGoodBuilderDialog(self, finished_good=fg)
         self.wait_window(dialog)
         result = dialog.result

         if result:
             show_success(
                 "Success",
                 f"Finished good '{result['display_name']}' updated successfully",
                 parent=self,
             )
             self.refresh()
             self._update_status(f"Updated: {result['display_name']}", success=True)
     ```
  2. Keep the `get_finished_good_by_id()` reload before opening dialog — ensures fresh data
  3. Remove old result-processing code (service calls now internal to builder)

- **Files**: `src/ui/finished_goods_tab.py`

- **Notes**:
  - The reload pattern (`get_finished_good_by_id`) is preserved — the builder needs a fresh ORM object
  - The builder further reloads internally (T027) for safety, but getting a fresh copy here is still good practice

### Subtask T034 -- Rename Add button to "+ Create Finished Good"

- **Purpose**: Update button text per spec FR-001 requirement.

- **Steps**:
  1. Find the "Add" button creation in `_create_action_buttons()` or similar method
  2. Change button text:
     ```python
     # From:
     self.add_button = ctk.CTkButton(... text="+ Add", ...)
     # To:
     self.add_button = ctk.CTkButton(... text="+ Create Finished Good", ...)
     ```
  3. May need to adjust button width to accommodate longer text

- **Files**: `src/ui/finished_goods_tab.py`

- **Notes**:
  - Keep the same command binding (`_add_finished_good`)
  - Button width: increase to `width=180` or similar to fit the longer text

### Subtask T035 -- Verify double-click and Edit button launch builder correctly

- **Purpose**: Confirm existing event bindings work with the new dialog.

- **Steps**:
  1. Verify `_on_tree_double_click()` → `_on_row_double_click()` → `_edit_finished_good()` chain still works
     - No changes should be needed — the chain calls `_edit_finished_good()` which now launches the builder
  2. Verify "Edit" button calls `_edit_finished_good()`
  3. Verify list refresh happens after save:
     - The `self.refresh()` call in both `_add_finished_good()` and `_edit_finished_good()` should still work
  4. Manual verification: Try double-clicking a FinishedGood, verify builder opens in edit mode with correct data

- **Files**: `src/ui/finished_goods_tab.py`

- **Notes**:
  - This subtask is primarily verification — the event binding chain should work without changes
  - If the double-click handler needs adjustment, do it here

### Subtask T036 -- Write integration tests for end-to-end create and edit flows via tab

- **Purpose**: Verify the full flow from tab button click to service call to list refresh.

- **Steps**:
  1. Add tests to `src/tests/test_finished_good_builder.py` (or a new integration test file):
     - `test_tab_add_launches_builder`: Mock builder dialog, verify it's created with no finished_good arg
     - `test_tab_edit_launches_builder_with_fg`: Mock builder dialog, verify it receives the selected FG
     - `test_tab_refresh_after_create`: Mock builder to return result, verify `refresh()` called
     - `test_tab_refresh_after_edit`: Same for edit flow
     - `test_tab_no_refresh_on_cancel`: Mock builder to return None, verify refresh NOT called
  2. Integration test (if feasible):
     - Create a FG via the builder, verify it appears in the tab's treeview
     - Edit it, modify name, verify the name change appears in the treeview

- **Files**: `src/tests/test_finished_good_builder.py`

- **Notes**:
  - Testing UI integration is harder — mock the dialog and verify call patterns
  - For true integration testing, consider a separate integration test that uses a test database

## Risks & Mitigations

- **Risk**: Existing tests may assert on `FinishedGoodFormDialog` instantiation. **Mitigation**: Update or remove those tests.
- **Risk**: Result format difference between old form and new builder. **Mitigation**: New result format is simpler; update tab handlers to match.
- **Risk**: Old `_get_assembly_type_from_value()` helper becomes unused. **Mitigation**: Remove if truly unused; or keep if other code calls it.

## Definition of Done Checklist

- [ ] `_add_finished_good()` launches `FinishedGoodBuilderDialog` (create mode)
- [ ] `_edit_finished_good()` launches `FinishedGoodBuilderDialog` (edit mode)
- [ ] Button text changed to "+ Create Finished Good"
- [ ] Double-click on list item opens builder in edit mode
- [ ] Edit button opens builder in edit mode for selected item
- [ ] List refreshes after successful create or edit
- [ ] No refresh on cancel
- [ ] Old `FinishedGoodFormDialog` no longer imported or called from this file
- [ ] Integration tests pass
- [ ] No linting errors

## Review Guidance

- Create a new FinishedGood via the "+ Create Finished Good" button — verify it appears in the list
- Double-click the new item — verify builder opens in edit mode with correct data
- Edit the name, save — verify the name change appears in the list
- Cancel an edit — verify no changes were made
- Check that `FinishedGoodFormDialog` is no longer referenced in `finished_goods_tab.py`

## Activity Log

- 2026-02-06T23:51:59Z -- system -- lane=planned -- Prompt created.
- 2026-02-07T00:49:55Z – claude-opus – shell_pid=34512 – lane=doing – Assigned agent via workflow command
- 2026-02-07T00:54:00Z – claude-opus – shell_pid=34512 – lane=for_review – Ready for review: Tab integration complete. FinishedGoodBuilderDialog replaces FinishedGoodFormDialog for create and edit. Button renamed. 65 tests pass.
- 2026-02-07T00:55:41Z – claude-opus – shell_pid=34512 – lane=done – Review passed: all 10 checklist items verified. 65/65 tests pass. C901 on _view_details is pre-existing.
