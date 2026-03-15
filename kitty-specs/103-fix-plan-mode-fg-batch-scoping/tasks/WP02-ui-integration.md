---
work_package_id: WP02
title: UI Integration
lane: "doing"
dependencies: [WP01]
base_branch: 103-fix-plan-mode-fg-batch-scoping-WP01
base_commit: f8eb27c4e90fcf5073e82aca88610f9e25e44a88
created_at: '2026-03-15T04:59:04.129980+00:00'
subtasks:
- T006
- T007
- T008
phase: Phase 2 - UI Integration
assignee: ''
agent: ''
shell_pid: "29384"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-15T04:45:47Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 -- UI Integration

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** -- Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Wire the new `get_fgs_for_selected_recipes()` service function into the FG selection UI
- Verify all filter dropdowns work with the new service call
- Confirm end-to-end planning flow works with real event data
- Prior filter fixes (category source, default values) must not regress

## Context & Constraints

- **Spec**: `kitty-specs/103-fix-plan-mode-fg-batch-scoping/spec.md` (FR-001, FR-005, FR-006)
- **Plan**: `kitty-specs/103-fix-plan-mode-fg-batch-scoping/plan.md` (see D4)
- **Dependency**: WP01 must be complete -- this WP uses `get_fgs_for_selected_recipes()` from event_service
- **Prior fixes**: Category filter sourced from `recipe_category_service.list_categories()` (commit `ffd80c3a`). Filter defaults set to "All Categories"/"All Types"/"All Yields" (commit `dfa06772`). These must not regress.
- **Constitution**: UI layer must NOT contain business logic (Principle V)

### Implementation command

```bash
spec-kitty implement WP02 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T006 -- Update `fg_selection_frame.py` service call

- **Purpose**: Replace the call to `get_filtered_available_fgs()` with `get_fgs_for_selected_recipes()` so the FG list shows finished goods for selected recipes instead of requiring all component recipes.

- **Steps**:
  1. Open `src/ui/components/fg_selection_frame.py`
  2. Locate `_on_filter_change()` method (around line 263)
  3. Find the call to `event_service.get_filtered_available_fgs()` (around line 307)
  4. Replace with:
     ```python
     fgs = event_service.get_fgs_for_selected_recipes(
         self._event_id,
         session,
         recipe_category=cat_param,
         item_type=type_param,
         yield_type=yield_param,
     )
     ```
  5. Verify the parameter names match the new function signature from WP01 T002
  6. The return type is still `List[FinishedGood]` so existing display logic should work unchanged

- **Files**: `src/ui/components/fg_selection_frame.py`
- **Parallel?**: No
- **Notes**: Check how `type_param` is derived. The current code converts "Finished Units" to "bare" and "Assemblies" to "bundle" for the old function. The new function accepts `item_type` as the raw string. Verify the parameter mapping.

### Subtask T007 -- Verify filter dropdowns work with new service

- **Purpose**: Ensure all three filter dropdowns (Recipe Category, Item Type, Yield Type) correctly filter the FG list when using the new service function.

- **Steps**:
  1. Trace the filter parameter flow in `_on_filter_change()`:
     - `recipe_cat` -> `cat_param` (None if "All Categories")
     - `item_type` -> `type_param` (mapped to assembly type string)
     - `yield_type` -> `yield_param` (None if "All Yields")
  2. Verify these map correctly to the new function's parameters
  3. Check edge cases:
     - "All Categories" selected -> no category filter applied
     - "All Types" selected -> no item type filter applied
     - "All Yields" selected -> no yield type filter applied
     - Multiple filters combined -> AND logic applied
  4. Verify the prior fixes are preserved:
     - Category dropdown populated from `recipe_category_service.list_categories()` (not from FG data)
     - Filter defaults are "All Categories", "All Types", "All Yields" (not blank)

- **Files**: `src/ui/components/fg_selection_frame.py`
- **Parallel?**: No (same file as T006)
- **Notes**: If the parameter mapping doesn't match, update either the UI code or the service function to align.

### Subtask T008 -- Manual verification checklist

- **Purpose**: Confirm the full planning flow works end-to-end with real data.

- **Steps**:
  1. Launch the app: `python src/main.py`
  2. Navigate to Plan mode
  3. Select "Easter 2026" event (or create a test event)
  4. **Recipe selection**:
     - Select 3+ recipes from different categories
     - Verify all categories appear in recipe category filter
  5. **FG selection**:
     - Navigate to Finished Goods section
     - Verify filter dropdowns show "All Categories", "All Types", "All Yields" (not blank)
     - Verify FGs from ALL selected recipes appear (not just 2)
     - Apply category filter -> only matching FGs shown
     - Apply yield type filter -> only matching FGs shown
     - Clear filters -> all FGs return
  6. **Recipe deselection**:
     - Deselect one recipe
     - Return to FG section -> deselected recipe's FGs gone
     - Check Batch Options -> no batches for deselected recipe
  7. **Edge cases**:
     - Deselect all recipes -> FG section empty, batch options empty
     - Re-select a recipe -> its FGs reappear (fresh, no saved quantities)

- **Files**: N/A (manual testing)
- **Parallel?**: No
- **Notes**: Document any issues found. This is the final validation before marking the feature complete.

## Risks & Mitigations

- **Risk**: Parameter mapping mismatch between old and new service function. **Mitigation**: T007 explicitly verifies parameter flow.
- **Risk**: Display logic assumes FinishedGood object shape that changed. **Mitigation**: WP01 T002 returns FinishedGood objects, preserving the contract.
- **Risk**: Prior filter fixes regress. **Mitigation**: T007 explicitly checks for regressions.

## Definition of Done Checklist

- [ ] `fg_selection_frame.py` calls `get_fgs_for_selected_recipes()` instead of `get_filtered_available_fgs()`
- [ ] All three filter dropdowns work correctly
- [ ] Filter defaults remain "All Categories"/"All Types"/"All Yields"
- [ ] Category dropdown still sourced from canonical recipe_categories table
- [ ] Manual verification passes all checklist items
- [ ] No UI regressions in planning flow
- [ ] `tasks.md` updated with status change

## Review Guidance

- Check that no business logic was added to the UI layer
- Verify prior bug fix commits (`ffd80c3a`, `dfa06772`) are not reverted
- Confirm parameter mapping between UI and service function
- Run the manual verification checklist

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-03-15T04:45:47Z -- system -- lane=planned -- Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP02 --to <lane> --note "message"` (recommended)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
