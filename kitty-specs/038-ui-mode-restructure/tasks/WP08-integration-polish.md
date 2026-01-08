---
work_package_id: WP08
title: Integration & Polish
lane: done
history:
- timestamp: '2026-01-05'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 3 - Integration
review_status: ''
reviewed_by: ''
shell_pid: '41347'
subtasks:
- T042
- T043
- T044
- T045
- T046
- T047
---

# Work Package Prompt: WP08 - Integration & Polish

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Final integration, remove old navigation, test full workflow, handle edge cases.

**Success Criteria**:
- Old flat navigation completely removed (FR-031)
- Full workflow works end-to-end (SC-006)
- Edge cases handled (unsaved changes, empty states, loading)
- Dashboard performance meets requirement (< 1 second per SC-005)
- All existing tests pass

## Context & Constraints

**Prerequisites**: WP01-WP07 must all be complete.

**Reference Documents**:
- `kitty-specs/038-ui-mode-restructure/spec.md` - Edge Cases section, SC-005, SC-006, FR-031
- All mode implementations from WP03-WP07

**Edge Cases from Spec**:
1. Mode switch with unsaved changes → Show confirmation dialog
2. Large data sets in dashboards → Progressive loading, loading indicator
3. Tab fails to load → Show error message, allow retry
4. Keyboard shortcuts in text field → Standard text editing takes precedence
5. No data yet → Show helpful empty states with guidance

## Subtasks & Detailed Guidance

### Subtask T042 - Remove old flat navigation

**Purpose**: Big-bang replacement of old navigation (FR-031).

**Steps**:
1. Remove old CTkTabview-based navigation from main_window.py
2. Remove any residual tab switching code
3. Ensure mode-based navigation is the only navigation
4. Clean up any orphaned imports

**Files**: `src/ui/main_window.py`

**Verification**:
- Application launches with mode bar only
- No trace of old flat tab navigation
- All modes accessible

**Notes**: This is the final migration step. All 5 modes must be working before this.

**Parallel?**: No - blocking step.

### Subtask T043 - Test mode switching and tab state

**Purpose**: Verify FR-003, FR-004, FR-005 work correctly.

**Steps**:
1. Test clicking each mode button switches correctly
2. Test Ctrl+1 through Ctrl+5 shortcuts
3. Test tab state preservation across mode switches
4. Test default OBSERVE mode on launch

**Files**: Manual testing + potential automated tests

**Test Scenarios**:
1. Launch app → OBSERVE mode active
2. Click CATALOG → Switch to CATALOG
3. Select Recipes tab in CATALOG
4. Switch to PLAN → PLAN mode shown
5. Switch back to CATALOG → Recipes tab still selected
6. Press Ctrl+3 → Switch to SHOP
7. Press Ctrl+5 → Switch to OBSERVE

**Parallel?**: No - integration testing.

### Subtask T044 - Implement unsaved changes dialog [P]

**Purpose**: Handle edge case when switching modes with unsaved form data.

**Steps**:
1. Implement dirty state tracking for forms
2. Create confirmation dialog component
3. Intercept mode switching when dirty
4. Allow save, discard, or cancel

**Files**:
- `src/ui/main_window.py` or `src/ui/dialogs/confirm_dialog.py`
- Mode implementations that have forms

**Implementation**:
```python
def switch_mode(self, target_mode: str):
    if self._has_unsaved_changes():
        result = self._show_confirm_dialog(
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save before switching modes?",
            buttons=["Save", "Discard", "Cancel"]
        )
        if result == "Cancel":
            return
        elif result == "Save":
            self._save_current_form()
        # else discard

    # Proceed with mode switch
    self._do_switch_mode(target_mode)
```

**Parallel?**: Yes - can be done while testing.

### Subtask T045 - Implement empty state handling [P]

**Purpose**: Show helpful guidance when user has no data.

**Steps**:
1. Detect empty state in each tab/dashboard
2. Show guidance message with suggested actions
3. Include quick action buttons where appropriate

**Files**: Various tab implementations, dashboard implementations

**Implementation Pattern**:
```python
def refresh(self):
    items = self._load_items()
    if not items:
        self._show_empty_state()
    else:
        self._show_items(items)

def _show_empty_state(self):
    self.empty_label.configure(text="No ingredients yet.\n\nClick 'Add Ingredient' to get started.")
    self.empty_label.pack(expand=True)
    self.tree.pack_forget()
```

**Empty States by Tab**:
- Ingredients: "No ingredients yet. Add your first ingredient to start building recipes."
- Products: "No products yet. Add products to track your pantry inventory."
- Recipes: "No recipes yet. Create recipes to plan your baking."
- Events: "No events planned. Create an event to start planning."
- Inventory: "Your pantry is empty. Record purchases to add inventory."

**Parallel?**: Yes - can be done while testing.

### Subtask T046 - Verify dashboard performance

**Purpose**: Ensure dashboards load within 1 second (SC-005).

**Steps**:
1. Measure dashboard load time for each mode
2. Identify any slow queries or calculations
3. Implement caching or optimization if needed
4. Add loading indicators during data fetch

**Files**: All dashboard implementations

**Performance Targets**:
- Mode switch + dashboard display: < 1 second
- Dashboard refresh: < 1 second
- Initial mode load: < 2 seconds (includes tab setup)

**Optimization Strategies**:
1. Cache dashboard data, refresh on demand
2. Use async loading for slower queries
3. Show loading spinner during data fetch
4. Limit displayed items (e.g., top 5 events)

**Parallel?**: No - requires all modes working.

### Subtask T047 - Final cleanup and organization

**Purpose**: Code cleanup, remove dead code, organize imports.

**Steps**:
1. Remove any deprecated or unused code
2. Clean up imports across modified files
3. Ensure consistent code style
4. Add/update docstrings where needed
5. Run linting and fix issues

**Files**: All files modified during F038

**Cleanup Checklist**:
- [ ] No unused imports
- [ ] No commented-out code
- [ ] Consistent naming conventions
- [ ] Docstrings on public methods
- [ ] Type hints where appropriate
- [ ] No hardcoded values that should be constants

**Parallel?**: No - final step.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Regressions after old nav removal | Thorough testing before removal |
| Performance issues with dashboards | Profile early, optimize as needed |
| Edge cases not all handled | Systematic testing against spec edge cases |

## Definition of Done Checklist

- [ ] Old flat navigation completely removed
- [ ] All 5 modes accessible and functional
- [ ] Mode switching works (click and keyboard)
- [ ] Tab state preserved across mode switches
- [ ] OBSERVE is default on launch
- [ ] Unsaved changes dialog implemented
- [ ] Empty states show helpful guidance
- [ ] Dashboard performance < 1 second
- [ ] All existing tests pass
- [ ] Code is clean and documented
- [ ] No linting errors

## Review Guidance

- Full workflow testing: Create data through CATALOG → Plan in PLAN → Shop in SHOP → Produce in PRODUCE → Observe in OBSERVE
- Test edge cases explicitly
- Verify performance on realistic data volume
- Check for visual regressions

## Activity Log

- 2026-01-05 - system - lane=planned - Prompt created.
- 2026-01-06T01:03:46Z – claude – shell_pid=36161 – lane=doing – Starting implementation - integration and polish
- 2026-01-06T01:15:58Z – claude – shell_pid=37980 – lane=for_review – Implementation complete - integration, cleanup, and unsaved changes infrastructure
- 2026-01-06T01:39:58Z – claude-reviewer – shell_pid=41347 – lane=done – Code review: APPROVED - implementation verified, tests pass
