---
work_package_id: "WP07"
subtasks:
  - "T046"
  - "T047"
  - "T048"
  - "T049"
  - "T050"
  - "T051"
  - "T052"
title: "Integration & Polish"
phase: "Phase 4 - Finalization"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-08T22:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - Integration & Polish

## Objectives & Success Criteria

Final integration, testing, and polish.

**Agent Assignment**: Claude

**Success Criteria**:
- All components wire together correctly
- Keyboard shortcuts work (Delete key, Ctrl+N)
- Double-click opens details
- All 6 user stories pass acceptance criteria
- Unit test coverage >70% on service methods
- Edge cases handled (empty list, long names, etc.)

## Context & Constraints

**Reference Documents**:
- `kitty-specs/043-purchases-tab-crud-operations/spec.md` - Acceptance scenarios

**Key Constraints**:
- All WP01-WP06 must be complete before this WP
- Must pass all acceptance criteria from spec

## Subtasks & Detailed Guidance

### Subtask T046 - Component Wiring Verification

**Purpose**: Ensure all components connect correctly.

**Steps**:
1. Verify PurchasesTab is in PurchaseDashboard
2. Verify Add button opens AddPurchaseDialog
3. Verify Edit menu/double-click opens EditPurchaseDialog
4. Verify Delete menu calls validation/confirmation flow
5. Verify View Details opens PurchaseDetailsDialog
6. Verify all callbacks trigger list refresh
7. Fix any import errors or missing connections

**Files**: All UI files
**Parallel?**: No

### Subtask T047 - Keyboard Shortcuts

**Purpose**: Add keyboard accessibility.

**Steps**:
1. In `PurchasesTab`, bind Delete key:
   ```python
   self.tree.bind("<Delete>", lambda e: self._on_delete())
   ```
2. Bind Ctrl+N for new purchase:
   ```python
   self.bind_all("<Control-n>", lambda e: self._on_add_purchase())
   ```
3. Bind Escape to close dialogs:
   ```python
   # In each dialog
   self.bind("<Escape>", lambda e: self.destroy())
   ```
4. Test on macOS (Command key) and Windows/Linux (Control key)

**Files**: `src/ui/tabs/purchases_tab.py`, all dialogs
**Parallel?**: No

### Subtask T048 - Double-click Behavior

**Purpose**: Double-click opens view details.

**Steps**:
1. Verify binding exists:
   ```python
   self.tree.bind("<Double-1>", lambda e: self._on_view_details())
   ```
2. Test that double-click on row opens details dialog
3. Verify single-click still just selects row

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No

### Subtask T049 - Edge Case Testing

**Purpose**: Handle edge cases gracefully.

**Test Cases**:
1. **Empty list**: Shows "No purchases found" message
2. **No filter results**: Shows "No purchases match your filters"
3. **Long product names**: Truncate with ellipsis (set column minwidth)
4. **Very large quantity**: Display formats correctly
5. **Zero price**: Allowed (free samples)
6. **Same-day purchases**: Distinct in list
7. **Database error**: Show error message, don't crash

**Steps**:
1. Test each case manually
2. Fix any issues found
3. Document expected behavior

**Files**: Various
**Parallel?**: No

### Subtask T050 - Unit Test Verification

**Purpose**: Ensure test coverage meets target.

**Steps**:
1. Run test suite:
   ```bash
   pytest src/tests/unit/test_purchase_service.py -v --cov=src/services/purchase_service --cov-report=term-missing
   ```
2. Verify coverage >70% on new methods
3. Add any missing test cases
4. Ensure all tests pass

**Files**: `src/tests/unit/test_purchase_service.py`
**Parallel?**: No

### Subtask T051 - Manual Testing

**Purpose**: Validate against acceptance criteria.

**Test Scenarios** (from spec.md):

**User Story 1 - View Purchase History**:
- [ ] Purchases display in descending date order
- [ ] All columns visible (Date, Product, Supplier, Qty, Price, Total, Remaining)
- [ ] At least 20 rows visible without scrolling
- [ ] Column headers clickable for sorting

**User Story 2 - Filter Purchase History**:
- [ ] Date range filter works (30 days, 90 days, year, all)
- [ ] Supplier filter shows correct results
- [ ] Search filters by product name
- [ ] Filter updates immediate (<200ms perceived)

**User Story 3 - Add New Purchase**:
- [ ] Add Purchase button opens dialog
- [ ] Price auto-fills from last purchase
- [ ] Supplier defaults to preferred
- [ ] Purchase + inventory created on save
- [ ] Future date rejected
- [ ] Zero/negative quantity rejected

**User Story 4 - Edit Purchase**:
- [ ] Edit opens with pre-filled fields
- [ ] Product is read-only
- [ ] Quantity below consumed is rejected
- [ ] Price change recalculates FIFO costs
- [ ] Save updates purchase correctly

**User Story 5 - Delete Purchase**:
- [ ] Consumed purchase deletion blocked
- [ ] Error shows usage details
- [ ] Unconsumed deletion shows confirmation
- [ ] Cancel prevents deletion
- [ ] Confirmed delete removes purchase + inventory

**User Story 6 - View Details**:
- [ ] Shows purchase info
- [ ] Shows original/used/remaining
- [ ] Shows usage history (or "no usage" message)
- [ ] Edit button opens edit dialog

**Files**: N/A (manual testing)
**Parallel?**: No

### Subtask T052 - UI Polish Fixes

**Purpose**: Fix any issues found during testing.

**Common Issues to Check**:
1. Dialog sizing (too small/large for content)
2. Column widths (truncation, alignment)
3. Color contrast (light/dark mode)
4. Focus management (tab order, initial focus)
5. Error message clarity
6. Loading states (if needed for slow queries)

**Steps**:
1. Document issues found in T051
2. Prioritize by severity
3. Fix critical issues
4. Log non-critical issues for future polish

**Files**: Various
**Parallel?**: No

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Integration bugs | Systematic component-by-component testing |
| Platform differences | Test on target platform (or document limitations) |
| Test coverage gaps | Use coverage report to identify gaps |

## Definition of Done Checklist

- [ ] All components wired correctly
- [ ] Keyboard shortcuts work
- [ ] Double-click opens details
- [ ] All 6 user stories pass acceptance criteria
- [ ] Unit test coverage >70%
- [ ] Edge cases handled gracefully
- [ ] No critical bugs remaining

## Review Guidance

- Walk through all 6 user stories end-to-end
- Try edge cases (empty list, long names, etc.)
- Test keyboard shortcuts
- Verify test coverage report

## Activity Log

- 2026-01-08T22:30:00Z - system - lane=planned - Prompt created.
- 2026-01-09T04:05:12Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-09T04:11:01Z – unknown – lane=for_review – Added keyboard shortcuts (Delete, Ctrl+N), verified double-click opens view details, all 1774 tests pass. Feature 042 implementation complete.
- 2026-01-09T04:59:37Z – agent – lane=doing – Started review via workflow command
- 2026-01-09T05:03:00Z – unknown – lane=done – Review passed: Keyboard shortcuts, double-click, all tests pass (1774 passed)
