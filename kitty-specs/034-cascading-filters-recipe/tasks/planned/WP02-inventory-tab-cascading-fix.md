---
work_package_id: "WP02"
subtasks:
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Inventory Tab Cascading Fix"
phase: "Phase B - Parallel Implementation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T10:45:22Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Inventory Tab Cascading Fix

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if work is returned from review.]*

---

## Objectives & Success Criteria

**Primary Objective**: Apply the same cascading filter fix pattern from WP01 to the Inventory tab.

**Success Criteria**:
- SC-001: When user selects an L0 category, L1 dropdown shows ONLY children of that L0
- SC-002: When user selects an L1 subcategory, L2 dropdown shows ONLY children of that L1
- SC-003: "Clear Filters" button resets all hierarchy filters
- SC-004: No infinite loops or event handler recursion
- SC-005: Inventory list correctly reflects filter selections

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/034-cascading-filters-recipe/spec.md` - User Story 2
- Plan: `kitty-specs/034-cascading-filters-recipe/plan.md` - WP2 details
- **Reference Pattern**: `kitty-specs/034-cascading-filters-recipe/tasks/done/WP01-products-tab-cascading-fix.md` (once completed)

**Key Findings from Research**:
- Inventory tab code at `src/ui/inventory_tab.py:426-500` is nearly identical to products tab
- Same event handler pattern: `_on_l0_filter_change()`, `_on_l1_filter_change()`
- Same service calls: `ingredient_hierarchy_service.get_children()`

**Architecture Constraints**:
- **CRITICAL**: You MUST reference WP01's completed implementation as the source of truth
- Apply identical fix pattern - this is essentially a copy-paste with minor adaptations
- Touch ONLY `src/ui/inventory_tab.py` - no other files

**Parallelization Note**:
- This WP runs in parallel with WP03
- NO dependency on WP03
- Depends on WP01 for the fix pattern (review WP01 implementation first)

## Subtasks & Detailed Guidance

### Subtask T009 - Review WP01 fix pattern

**Purpose**: Understand exactly what was done in WP01 before applying to inventory tab.

**Steps**:
1. Read the completed WP01 prompt file for implementation notes
2. Review the git diff or changed code in `src/ui/products_tab.py`
3. Identify the specific fixes applied:
   - What was the root cause?
   - What code was added/modified?
   - What re-entry guard pattern was used?
   - How was Clear button implemented?
4. Document the pattern to apply

**Files**: `src/ui/products_tab.py` (read-only reference)
**Parallel?**: Yes - read-only

### Subtask T010 - Apply fix to _on_l0_filter_change()

**Purpose**: Fix L0->L1 cascading in inventory tab.

**Steps**:
1. Open `src/ui/inventory_tab.py` and locate `_on_l0_filter_change()` at line 426
2. Apply the same fix pattern identified in T009
3. Key areas to check:
   - Line ~437: `l0_id = self._l0_map[value].get("id")`
   - Line ~439: `ingredient_hierarchy_service.get_children(l0_id)`
   - Line ~443: `self.l1_filter_dropdown.configure(values=l1_values, state="normal")`
4. Add any additional logging or guards from WP01

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: Yes - can start after T009

### Subtask T011 - Apply fix to _on_l1_filter_change()

**Purpose**: Fix L1->L2 cascading in inventory tab.

**Steps**:
1. Locate `_on_l1_filter_change()` at line 453
2. Apply the same fix pattern from WP01
3. Key areas:
   - Line ~461: `l1_id = self._l1_map[value].get("id")`
   - Line ~463: `ingredient_hierarchy_service.get_children(l1_id)`
   - Line ~467: `self.l2_filter_dropdown.configure(values=l2_values, state="normal")`

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: Yes - can proceed with T010

### Subtask T012 - Add re-entry guards

**Purpose**: Prevent infinite loops matching WP01 pattern.

**Steps**:
1. Add `self._updating_filters = False` to `__init__`
2. Wrap both filter handlers with re-entry check:
   ```python
   def _on_l0_filter_change(self, value: str):
       if self._updating_filters:
           return
       self._updating_filters = True
       try:
           # ... existing logic
       finally:
           self._updating_filters = False
   ```
3. Apply same pattern to `_on_l1_filter_change()`

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: Yes - after T010/T011

### Subtask T013 - Add "Clear Filters" button

**Purpose**: Add Clear button matching WP01 pattern.

**Steps**:
1. Locate filter frame creation (around line 142)
2. Add Clear button:
   ```python
   clear_button = ctk.CTkButton(
       filter_frame,
       text="Clear",
       command=self._clear_hierarchy_filters,
       width=60,
   )
   clear_button.pack(side="left", padx=10, pady=5)
   ```
3. Note: Inventory tab may already have `_clear_hierarchy_labels()` - use different method name

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: Yes - UI change

### Subtask T014 - Implement _clear_hierarchy_filters()

**Purpose**: Reset all hierarchy filter dropdowns.

**Steps**:
1. Add method (check existing method names to avoid conflicts):
   ```python
   def _clear_hierarchy_filters(self):
       """Clear all hierarchy filters and refresh."""
       self.l0_filter_var.set("All Categories")
       self.l1_filter_var.set("All")
       self.l2_filter_var.set("All")
       self._l1_map = {}
       self._l2_map = {}
       self.l1_filter_dropdown.configure(values=["All"], state="disabled")
       self.l2_filter_dropdown.configure(values=["All"], state="disabled")
       self._apply_filters()  # Note: inventory uses _apply_filters() not _load_products()
   ```
2. Verify the correct refresh method is called

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: Yes - depends on T013

### Subtask T015 - Manual testing

**Purpose**: Validate all acceptance scenarios.

**Steps**:
1. Start application and navigate to Inventory tab
2. Test Scenario 1: Select L0 category -> L1 shows only children
3. Test Scenario 2: Change L0 -> L1 and L2 clear and update
4. Test Scenario 3: Click Clear -> All hierarchy filters reset
5. Verify inventory list filters correctly
6. Test rapid clicking to verify no infinite loops

**Files**: N/A - testing
**Parallel?**: No - final validation

## Test Strategy

Manual testing is primary. Automated tests in WP04.

**Manual Test Checklist**:
- [ ] L0 selection updates L1 options correctly
- [ ] L1 selection updates L2 options correctly
- [ ] Changing L0 clears L1 and L2 selections
- [ ] Clear button resets hierarchy filters
- [ ] Inventory list updates based on filter selections
- [ ] No console errors or infinite loops

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Variable names differ from products tab | Medium | Careful review of inventory_tab.py structure |
| Existing clear methods conflict | Low | Use distinct method name like `_clear_hierarchy_filters` |
| Pattern doesn't transfer cleanly | Low | WP01 and inventory tab are very similar |

## Definition of Done Checklist

- [ ] All subtasks T009-T015 completed
- [ ] WP01 pattern successfully applied
- [ ] Cascading L0->L1 works correctly
- [ ] Cascading L1->L2 works correctly
- [ ] Clear button resets hierarchy filters
- [ ] No infinite loops or recursion
- [ ] Manual testing passes all scenarios
- [ ] `tasks.md` updated with status change

## Review Guidance

**Reviewers should verify**:
1. Fix pattern matches WP01 implementation
2. L0/L1/L2 cascading works correctly
3. Clear button resets appropriate filters (hierarchy only, or all?)
4. No regressions in existing inventory tab functionality
5. No console errors during rapid filter changes

## Activity Log

- 2026-01-02T10:45:22Z - system - lane=planned - Prompt created via /spec-kitty.tasks
