---
work_package_id: WP01
title: Products Tab Cascading Fix
lane: done
history:
- timestamp: '2026-01-02T10:45:22Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase A - Sequential Foundation
review_status: ''
reviewed_by: ''
shell_pid: '3311'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
---

# Work Package Prompt: WP01 - Products Tab Cascading Fix

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if work is returned from review.]*

---

## Objectives & Success Criteria

**Primary Objective**: Fix cascading filter behavior in Products tab so L1 dropdown updates correctly when L0 selection changes, and L2 updates when L1 changes.

**Success Criteria**:
- SC-001: When user selects an L0 category, L1 dropdown shows ONLY children of that L0
- SC-002: When user selects an L1 subcategory, L2 dropdown shows ONLY children of that L1
- SC-003: When user changes L0, L1 and L2 selections clear automatically
- SC-004: "Clear Filters" button resets all dropdowns to default state
- SC-005: No infinite loops or event handler recursion
- SC-006: Filter interactions complete within 500ms

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/034-cascading-filters-recipe/spec.md` - User Story 1
- Plan: `kitty-specs/034-cascading-filters-recipe/plan.md` - WP1 details
- Research: `kitty-specs/034-cascading-filters-recipe/research.md` - Code analysis

**Key Findings from Research**:
- Cascading filter code EXISTS at `src/ui/products_tab.py:479-554`
- Code structure looks correct but gap analysis says it's broken
- Event handlers are properly bound (lines 129, 143)
- Clear button pattern exists in `ingredients_tab.py:163-170`

**Architecture Constraints**:
- UI layer only - no service layer changes
- Use existing `ingredient_hierarchy_service.get_children()` function
- Follow CustomTkinter patterns

## Subtasks & Detailed Guidance

### Subtask T001 - Debug _on_l0_filter_change()

**Purpose**: Identify the root cause of the cascading filter bug.

**Steps**:
1. Open `src/ui/products_tab.py` and locate `_on_l0_filter_change()` at line 479
2. Add print/logging statements to trace:
   - What value is being passed to the handler
   - What `self._l0_map[value]` returns
   - What `ingredient_hierarchy_service.get_children(l0_id)` returns
   - Whether L1 dropdown values are actually being updated
3. Run the application and test with real data
4. Document findings before proceeding

**Files**: `src/ui/products_tab.py`
**Parallel?**: No - must complete before fixes

### Subtask T002 - Add debug logging

**Purpose**: Create persistent logging for troubleshooting.

**Steps**:
1. Add logging at key points in the cascading chain:
   ```python
   import logging
   logger = logging.getLogger(__name__)

   def _on_l0_filter_change(self, value: str):
       logger.debug(f"L0 filter changed to: {value}")
       # ... existing code with additional debug logs
   ```
2. Log service call results: `logger.debug(f"get_children returned: {len(subcategories)} items")`
3. Log UI updates: `logger.debug(f"L1 dropdown updated with values: {l1_values}")`

**Files**: `src/ui/products_tab.py`
**Parallel?**: No - supports T001 debugging

### Subtask T003 - Fix L0->L1 cascading logic

**Purpose**: Ensure L1 dropdown updates correctly when L0 changes.

**Steps**:
1. Review `_on_l0_filter_change()` logic at line 479-504
2. Verify the mapping: `self._l0_map` should contain ingredient dicts with `id` key
3. Verify service call: `ingredient_hierarchy_service.get_children(l0_id)` should return L1 ingredients
4. Verify dropdown update: `self.l1_filter_dropdown.configure(values=l1_values)`
5. Common issues to check:
   - Is `l0_id` being extracted correctly? (`self._l0_map[value].get("id")`)
   - Are subcategories being populated into `self._l1_map`?
   - Is the dropdown `state` being set to "normal"?
6. Apply fix based on debugging findings

**Files**: `src/ui/products_tab.py`
**Parallel?**: No - depends on T001/T002

### Subtask T004 - Fix L1->L2 cascading logic

**Purpose**: Ensure L2 dropdown updates correctly when L1 changes.

**Steps**:
1. Review `_on_l1_filter_change()` logic at line 506-524
2. Apply same verification pattern as T003:
   - Verify `self._l1_map[value].get("id")` extracts correct L1 ID
   - Verify `get_children(l1_id)` returns L2 leaf ingredients
   - Verify dropdown update works
3. Apply fix based on debugging findings

**Files**: `src/ui/products_tab.py`
**Parallel?**: No - follows T003

### Subtask T005 - Add re-entry guards

**Purpose**: Prevent infinite loops if event handlers trigger each other.

**Steps**:
1. Add a flag to prevent recursive event handling:
   ```python
   def __init__(self, ...):
       ...
       self._updating_filters = False

   def _on_l0_filter_change(self, value: str):
       if self._updating_filters:
           return
       self._updating_filters = True
       try:
           # ... existing logic
       finally:
           self._updating_filters = False
   ```
2. Apply same pattern to `_on_l1_filter_change()`
3. Test that rapid filter changes don't cause recursion

**Files**: `src/ui/products_tab.py`
**Parallel?**: No - depends on T003/T004

### Subtask T006 - Add "Clear Filters" button

**Purpose**: Provide one-click reset of all filters.

**Steps**:
1. Locate filter frame creation in `_create_filters()` around line 114
2. Add Clear button after the existing filter dropdowns:
   ```python
   # Clear button
   clear_button = ctk.CTkButton(
       filter_frame,
       text="Clear",
       command=self._clear_filters,
       width=60,
   )
   clear_button.pack(side="left", padx=10, pady=5)
   ```
3. Position it appropriately (after supplier filter)

**Files**: `src/ui/products_tab.py`
**Parallel?**: No - UI change

### Subtask T007 - Implement _clear_filters() method

**Purpose**: Reset all filter dropdowns to default state.

**Steps**:
1. Add method near other filter handlers:
   ```python
   def _clear_filters(self):
       """Clear all hierarchy and attribute filters."""
       # Reset hierarchy filters
       self.l0_filter_var.set("All Categories")
       self.l1_filter_var.set("All")
       self.l2_filter_var.set("All")

       # Clear maps
       self._l1_map = {}
       self._l2_map = {}

       # Disable child dropdowns
       self.l1_filter_dropdown.configure(values=["All"], state="disabled")
       self.l2_filter_dropdown.configure(values=["All"], state="disabled")

       # Reset brand and supplier filters
       self.brand_var.set("All")
       self.supplier_var.set("All")

       # Refresh product list
       self._load_products()
   ```

**Files**: `src/ui/products_tab.py`
**Parallel?**: No - depends on T006

### Subtask T008 - Manual testing

**Purpose**: Validate all acceptance scenarios from spec.

**Steps**:
1. Start application with database containing L0/L1/L2 ingredients
2. Test Scenario 1: Select L0 "Baking" -> L1 should show only Baking subcategories
3. Test Scenario 2: Change L0 from "Baking" to "Dairy" -> L1 should clear and update
4. Test Scenario 3: Select L1 -> L2 should update with leaves under that L1
5. Test Scenario 4: Click "Clear" -> All dropdowns reset to "All"
6. Verify product list filters correctly based on selections
7. Test rapid clicking to verify no infinite loops

**Files**: N/A - testing
**Parallel?**: No - final validation

## Test Strategy

Manual testing is primary for this work package. Automated tests will be added in WP04.

**Manual Test Checklist**:
- [ ] L0 selection updates L1 options correctly
- [ ] L1 selection updates L2 options correctly
- [ ] Changing L0 clears L1 and L2 selections
- [ ] Clear button resets all filters
- [ ] Product list updates based on filter selections
- [ ] No console errors or infinite loops

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Bug is in service layer, not UI | Medium | T001 debugging will reveal; escalate if service fix needed |
| Event handler timing issues | Low | T005 re-entry guards prevent recursion |
| CustomTkinter dropdown behavior quirks | Low | Test with various data sizes |

## Definition of Done Checklist

- [ ] All subtasks T001-T008 completed
- [ ] Cascading L0->L1 works correctly
- [ ] Cascading L1->L2 works correctly
- [ ] Clear button resets all filters
- [ ] No infinite loops or recursion
- [ ] Manual testing passes all scenarios
- [ ] Debug logging can be removed or left at DEBUG level
- [ ] `tasks.md` updated with status change

## Review Guidance

**Reviewers should verify**:
1. L0 selection actually updates L1 dropdown options (not just values)
2. L1 selection actually updates L2 dropdown options
3. Clear button resets ALL filters including brand/supplier
4. No console errors during rapid filter changes
5. Product list correctly reflects filter selections

## Activity Log

- 2026-01-02T10:45:22Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-02T10:53:00Z – claude – shell_pid=91196 – lane=doing – Started implementation
- 2026-01-02T15:36:59Z – claude – shell_pid=94052 – lane=for_review – Ready for review - re-entry guards and Clear button implemented
- 2026-01-02T16:47:45Z – claude-reviewer – shell_pid=3311 – lane=done – Review approved: Re-entry guards and Clear button implemented correctly. All tests pass.
