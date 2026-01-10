---
work_package_id: "WP04"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "UI Verification & Polish"
phase: "Phase 3 - UI Verification"
lane: "for_review"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-10T07:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - UI Verification & Polish

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Primary Goal**: Verify that UI displays costs correctly in appropriate contexts and that all user workflows function without errors.

**Success Criteria**:
1. Finished Goods tab (CATALOG mode) shows NO cost columns
2. Assembly tab (MAKE mode) shows cost history with per_unit_cost
3. Record Assembly dialog shows cost preview before confirming
4. Event Planning assigns packages without crashes
5. Full test suite passes

**UI Principle**: "No costs in CATALOG, costs in MAKE/PLAN" - definitions don't show costs; only instances (assemblies, packages in planning) show costs.

## Context & Constraints

**Why This Matters**: The UI already exists but may need minor adjustments after the model/service changes. This work package is primarily verification with targeted fixes if needed.

**Dependencies**: WP01, WP02, WP03 must all be complete before starting.

**Key User Stories Being Verified**:
- US1: Define a Finished Good -> Verify CRUD works
- US2: Record an Assembly -> Verify cost snapshot capture
- US3: Event Planning -> Verify package costs work
- US5: View Assembly History -> Verify historical costs display

## Subtasks & Detailed Guidance

### Subtask T011 - Verify Finished Goods Tab (CATALOG Mode)

**Purpose**: Confirm the Finished Goods catalog view does NOT display cost columns.

**File**: `src/ui/finished_goods_tab.py`

**Verification Steps**:
1. Launch the application: `python src/main.py`
2. Navigate to CATALOG mode
3. Select "Finished Goods" tab
4. Verify:
   - Grid displays: Name, Type, Component Count (or similar)
   - Grid does NOT display: Cost, Total Cost, Unit Cost, or any price columns
   - "Add Finished Good" button works
   - Edit and Delete actions work

**Code Check**:
```bash
# Search for any cost-related columns in the tab
grep -n "cost\|price\|total" src/ui/finished_goods_tab.py
```

If cost columns are found, they should be removed or hidden.

**Expected Footer Text** (if present): "No costs shown - costs are calculated when assemblies are recorded"

**Parallel?**: Yes - can run alongside T012, T013, T014

### Subtask T012 - Verify Assembly Tab (MAKE Mode)

**Purpose**: Confirm the Assembly tab displays cost history correctly.

**File**: `src/ui/tabs/assembly_tab.py`

**Verification Steps**:
1. Navigate to MAKE mode
2. Select "Assembly" tab
3. If assembly history exists, verify columns include:
   - Date/Time
   - Finished Good name
   - Quantity assembled
   - Cost per Unit (`per_unit_cost`)
   - Total Cost (`total_component_cost`)
4. If no history, verify empty state displays appropriately

**Code Check**:
```bash
# Verify the tab references AssemblyRun cost fields
grep -n "per_unit_cost\|total_component_cost" src/ui/tabs/assembly_tab.py
```

**Parallel?**: Yes - can run alongside T011, T013, T014

### Subtask T013 - Verify Record Assembly Dialog

**Purpose**: Confirm the Record Assembly dialog shows cost preview and captures costs correctly.

**File**: `src/ui/forms/record_assembly_dialog.py`

**Verification Steps**:
1. From Assembly tab, click "Record Assembly"
2. Select a Finished Good
3. Enter quantity
4. Verify dialog shows:
   - Component list with quantities needed
   - Current cost per component (calculated dynamically)
   - Total estimated cost
   - Inventory availability status
5. Complete the assembly
6. Verify the new record appears in history with captured costs

**Code Check**:
```bash
# Verify dialog uses calculate_current_cost or similar
grep -n "calculate_current_cost\|cost" src/ui/forms/record_assembly_dialog.py
```

**If Cost Preview Missing**: The dialog may need enhancement to show cost preview. Key additions:
```python
# In the dialog, after selecting FinishedGood:
cost = selected_fg.calculate_current_cost()
self.cost_label.configure(text=f"Est. Cost: ${cost:.2f}")
```

**Parallel?**: Yes - can run alongside T011, T012, T014

### Subtask T014 - Verify Event Planning (PLAN Mode)

**Purpose**: Confirm event planning with packages works without crashes.

**Files**: `src/ui/planning/`, `src/ui/tabs/event_status_tab.py`

**Verification Steps**:
1. Navigate to PLAN mode
2. Create or select an Event
3. Add a Recipient
4. Assign a Package to the Recipient
5. Verify:
   - Package cost displays (not zero, not crash)
   - Cost updates if you change package
   - No AttributeError or exceptions

**Critical Test**: This was the original "Package cost calculation crashes" bug. Verify it's fixed by:
1. Selecting a package that contains FinishedGoods
2. Confirming the cost displays without errors

**If Crash Occurs**: Check the stack trace - likely a reference to `total_cost` that wasn't caught in WP02. Fix in the appropriate model file.

**Parallel?**: Yes - can run alongside T011, T012, T013

### Subtask T015 - Run Full Test Suite

**Purpose**: Ensure all changes haven't broken existing functionality.

**Commands**:
```bash
# Run full test suite
pytest src/tests -v

# Run with coverage for models and services
pytest src/tests -v --cov=src/models --cov=src/services

# Focus on cost-related tests if any fail
pytest src/tests -v -k "cost or assembly or package or finished"
```

**If Tests Fail**:
1. Check if failure is in cost-related code (expected updates needed)
2. Check if failure is unrelated (regression - investigate)
3. Fix any test assertions that expect `total_cost` attribute to exist
4. Update test mocks/fixtures if they reference removed fields

**Common Fixes**:
```python
# Old test code:
assert finished_unit.unit_cost == Decimal("1.50")  # FAILS - field removed

# New test code:
assert finished_unit.calculate_current_cost() == Decimal("1.5000")  # Use method
```

**Parallel?**: No - should run after T011-T014 are complete

## Test Strategy

**Manual Testing Checklist**:
- [ ] Launch app without errors
- [ ] CATALOG > Finished Goods tab displays list
- [ ] Create new Finished Good works
- [ ] Edit Finished Good works
- [ ] Delete Finished Good works
- [ ] MAKE > Assembly tab shows history
- [ ] Record Assembly captures costs
- [ ] PLAN > Event planning shows package costs
- [ ] No crashes in any workflow

**Automated Tests**:
```bash
pytest src/tests -v --tb=short
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| UI files have additional broken references | Medium | Grep search before verification |
| Test fixtures reference removed fields | Low | Update fixtures as needed |
| Cost display formatting issues | Low | Use standard `${:.2f}` format |

## Definition of Done Checklist

- [ ] T011: Finished Goods tab verified (no cost columns)
- [ ] T012: Assembly tab verified (shows cost history)
- [ ] T013: Record Assembly dialog verified (shows cost preview)
- [ ] T014: Event Planning verified (package costs work)
- [ ] T015: Full test suite passes
- [ ] All 5 user stories have working UI paths
- [ ] No crashes in any verified workflow
- [ ] No new linting errors

## Review Guidance

**Key Checkpoints**:
1. All manual verification steps completed
2. Screenshots or notes documenting each verification
3. Any fixes made are documented in Activity Log
4. Test suite passes with no regressions

**Acceptance Criteria from Spec**:
- SC-001: Create finished good in <2 min -> Test with timer
- SC-002: Record assembly in <1 min -> Test with timer
- SC-003: Package cost calculation (zero crashes) -> Verify multiple times
- SC-006: No cost columns in catalog -> Visual verification
- SC-007: Assembly history shows snapshots -> Query database to confirm

## Activity Log

- 2026-01-10T07:30:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-10T13:06:47Z – unknown – lane=doing – Moved to doing
- 2026-01-10T13:08:30Z – unknown – lane=for_review – Moved to for_review
