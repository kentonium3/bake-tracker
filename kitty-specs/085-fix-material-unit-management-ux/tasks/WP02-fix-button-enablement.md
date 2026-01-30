---
work_package_id: WP02
title: Fix Edit/Delete Button Enablement
lane: "for_review"
dependencies: []
base_branch: main
base_commit: 9d1d78d6fdf94f828079a4fe6874f921a3b1a70f
created_at: '2026-01-30T22:51:22.957347+00:00'
subtasks:
- T004
- T005
phase: Phase 1 - Bug Fixes
assignee: ''
agent: ''
shell_pid: "74720"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-30T22:39:29Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Fix Edit/Delete Button Enablement

## Implementation Command

```bash
spec-kitty implement WP02
```

No dependencies - this WP starts fresh from main.

---

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Fix the Edit and Delete buttons in the Edit Product dialog's Material Units section to enable when a unit is selected, regardless of material type.

**Success Criteria**:
- [ ] Edit button enables when a MaterialUnit is selected (for ANY material type)
- [ ] Delete button enables when a MaterialUnit is selected (for ANY material type)
- [ ] Buttons disable when no unit is selected
- [ ] Works for "each" type products AND "linear_cm" type products

---

## Context & Constraints

**Background**: Users report that the Edit/Delete buttons stay disabled even when selecting a MaterialUnit for linear products. The handler code at `materials_tab.py:794-804` appears correct, so the issue is likely:
- Event binding not working
- Conditional logic elsewhere
- Button references are None

**Related Documents**:
- Spec: `kitty-specs/085-fix-material-unit-management-ux/spec.md` (FR-002, User Story 2)
- Plan: `kitty-specs/085-fix-material-unit-management-ux/plan.md` (Issue 2)

**Key Code Location** (`src/ui/materials_tab.py:794-804`):
```python
def _on_units_tree_select(self, event=None):
    """Update button states based on selection."""
    if not self.units_tree:
        return

    selection = self.units_tree.selection()
    state = "normal" if selection else "disabled"
    if self.edit_unit_btn:
        self.edit_unit_btn.configure(state=state)
    if self.delete_unit_btn:
        self.delete_unit_btn.configure(state=state)
```

**Constraints**:
- Do NOT change button behavior for "each" type products if it already works
- Must maintain compatibility with the Add Unit button visibility logic
- Keep solution simple - this is a bug fix, not a redesign

---

## Subtasks & Detailed Guidance

### Subtask T004 – Debug _on_units_tree_select Handler

**Purpose**: Identify why the selection handler isn't enabling buttons for linear product units.

**Steps**:
1. Add temporary debug logging to trace execution:
   ```python
   def _on_units_tree_select(self, event=None):
       """Update button states based on selection."""
       print(f"DEBUG: _on_units_tree_select called, units_tree={self.units_tree}")
       if not self.units_tree:
           print("DEBUG: units_tree is None, returning")
           return

       selection = self.units_tree.selection()
       print(f"DEBUG: selection={selection}")
       state = "normal" if selection else "disabled"
       print(f"DEBUG: edit_unit_btn={self.edit_unit_btn}, delete_unit_btn={self.delete_unit_btn}")
       print(f"DEBUG: Setting state to '{state}'")
       # ... rest of handler
   ```

2. Test with a linear product:
   - Open Edit Product dialog for a linear product (e.g., ribbon)
   - Select a MaterialUnit in the tree
   - Check console output to see if handler is called

3. Possible findings:
   - Handler not being called → Check event binding (`<<TreeviewSelect>>`)
   - `self.units_tree` is None → Check dialog construction order
   - `self.edit_unit_btn` is None → Check if buttons created correctly
   - Handler called but buttons don't update → CTk state issue

4. Document the root cause before proceeding to fix

**Files**:
- `src/ui/materials_tab.py` - Add debug logging

**Notes**:
- Keep debug logging temporary - remove before completing the WP
- Check if there are multiple Treeview instances (one might be bound, one not)

---

### Subtask T005 – Fix Button Enablement for All Material Types

**Purpose**: Apply the fix based on T004 findings to enable buttons for all material types.

**Possible Fixes** (depending on T004 findings):

**If event binding is missing**:
```python
# In _create_units_section() or dialog initialization
self.units_tree.bind("<<TreeviewSelect>>", self._on_units_tree_select)
```

**If binding exists but wrong tree instance**:
```python
# Ensure binding is on the correct Treeview instance
# Check if `self.units_tree` is reassigned after binding
```

**If button references are None**:
```python
# Ensure buttons are created BEFORE the handler is called
# Check dialog construction order
```

**If handler is called but CTk state not updating**:
```python
# Try using configure with explicit state
self.edit_unit_btn.configure(state=state)
self.edit_unit_btn.update()  # Force UI refresh
```

**Steps**:
1. Apply the appropriate fix based on T004 findings
2. Remove debug logging added in T004
3. Test with multiple scenarios:
   - "each" type product with units → Edit/Delete should enable
   - "linear_cm" type product with units → Edit/Delete should enable
   - Product with no units → Edit/Delete should stay disabled
4. Verify Add Unit button visibility logic still works:
   - Hidden for "each" type (auto-generated)
   - Visible for "linear_cm" type

**Files**:
- `src/ui/materials_tab.py` - Apply fix and remove debug logging

**Notes**:
- The fix should be minimal - only change what's necessary
- Don't refactor surrounding code unless directly related to the bug

---

## Test Strategy

**Manual Testing Required**:

1. **Test "each" Type Product** (should already work):
   - Open Edit Product dialog for a product under an "each" type material
   - Verify MaterialUnit appears in the list
   - Select the unit → Edit and Delete buttons should enable
   - Deselect → buttons should disable

2. **Test "linear_cm" Type Product** (this was broken):
   - Open Edit Product dialog for a linear product (e.g., ribbon)
   - Verify MaterialUnit appears in the list
   - Select the unit → Edit and Delete buttons should NOW enable
   - Click Edit → Edit dialog should open
   - Click Delete → Confirmation should appear

3. **Test No Units**:
   - If a product has no units, buttons should stay disabled
   - No errors should appear in console

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Root cause is complex | Start with debug logging; escalate if findings are unclear |
| Fix breaks "each" type functionality | Test both types after fix |
| Multiple code paths for different product types | Unify if found (but minimize changes) |

---

## Definition of Done Checklist

- [ ] T004: Root cause identified and documented in Activity Log
- [ ] T005: Fix applied and debug logging removed
- [ ] Edit button enables for "each" type products
- [ ] Edit button enables for "linear_cm" type products
- [ ] Delete button enables when unit selected
- [ ] Buttons disable when no selection
- [ ] Add Unit button visibility still correct (hidden for "each", visible for "linear")
- [ ] No console errors

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Test with BOTH "each" and "linear_cm" type products
2. Verify Edit opens the edit dialog correctly
3. Verify Delete shows confirmation dialog
4. Check console for any new errors or warnings

**Code Review Focus**:
- Minimal change principle - only fix what's broken
- No debug logging left in code
- No unintended side effects on Add Unit button

---

## Activity Log

- 2026-01-30T22:39:29Z – system – lane=planned – Prompt created.
- 2026-01-30T23:03:07Z – unknown – shell_pid=74720 – lane=for_review – Added update_idletasks() calls to ensure button state changes are reflected, and moved visibility update to after form population
