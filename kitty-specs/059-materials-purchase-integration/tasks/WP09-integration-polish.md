---
work_package_id: WP09
title: Integration & Polish
lane: "doing"
dependencies: []
subtasks:
- T046
- T047
- T048
- T049
- T050
phase: Final
assignee: ''
agent: "claude-opus"
shell_pid: "18602"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-18T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 - Integration & Polish

## Important: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# Depends on ALL previous work packages (WP01-WP08)
spec-kitty implement WP09
```

---

## Objectives & Success Criteria

End-to-end validation and final polish across all F059 components. This ensures:
- All workflows work end-to-end without errors
- Edge cases are handled gracefully
- UI is consistent across all new features
- Code is clean and ready for merge

**Success Criteria**:
- [ ] E2E: Purchase → View → Adjust workflow passes
- [ ] E2E: CLI provisional → UI enrichment workflow passes
- [ ] FIFO display order consistent (newest first in UI)
- [ ] All edge cases handled gracefully
- [ ] Code review complete (no debug code, consistent style)
- [ ] All acceptance criteria from spec.md satisfied

---

## Context & Constraints

**Feature**: F059 - Materials Purchase Integration & Workflows
**Reference Documents**:
- Spec: `kitty-specs/059-materials-purchase-integration/spec.md` (acceptance criteria)
- All WP prompts for component details

**Acceptance Criteria Reference** (from spec.md):
- FR-001 through FR-022 must all be satisfied
- User Stories 1-6 must work end-to-end

**IMPORTANT**: This is a validation and polish work package. Do NOT implement new features here. Focus on:
1. Testing existing features work together
2. Fixing integration bugs
3. Cleaning up code
4. Ensuring consistency

---

## Subtasks & Detailed Guidance

### Subtask T046 - E2E Test: Purchase → View → Adjust

**Purpose**: Validate the core material purchase workflow end-to-end.

**Test Scenario**:
1. **Setup**:
   - Ensure at least one Material exists (e.g., "Red Ribbon" with linear_cm)
   - Ensure at least one MaterialProduct exists for that Material

2. **Purchase**:
   - Open Purchases tab
   - Click Add Purchase
   - Select "Material" product type
   - Select a MaterialProduct from dropdown
   - Enter: Qty=2, Package Size=100, Total Cost=$15.00
   - Save

3. **View**:
   - Navigate to Materials Inventory section
   - Verify new inventory item appears
   - Check values: Qty Purchased=200 (2×100), Cost/Unit=$0.075

4. **Adjust**:
   - Select the inventory item
   - Click Adjust (or right-click context menu)
   - For linear_cm: Enter 50% remaining
   - Verify preview shows 200 → 100
   - Save adjustment
   - Verify quantity_remaining updated to 100
   - Verify notes field contains adjustment record

**Validation Checklist**:
- [ ] Purchase form accepts material purchase
- [ ] Inventory item created with correct quantities
- [ ] Inventory item visible in display
- [ ] Adjustment dialog opens correctly
- [ ] Adjustment calculates correctly
- [ ] Adjustment persists to database
- [ ] Notes recorded in adjustment

**Files**: N/A (manual testing)

**Parallel?**: Yes - can run alongside T047

---

### Subtask T047 - E2E Test: CLI Provisional → UI Enrichment

**Purpose**: Validate the provisional product workflow end-to-end.

**Test Scenario**:
1. **CLI Purchase with New Product**:
   ```bash
   python src/utils/import_export_cli.py purchase-material \
     --name "Holiday Gift Tags" \
     --material-id 1 \
     --package-size 50 \
     --package-unit each \
     --qty 2 \
     --cost 12.00
   ```

2. **Verify Provisional Product**:
   - Open Materials tab
   - Find "Holiday Gift Tags" in products list
   - Verify "⚠ Needs Info" indicator shows
   - Verify is_provisional=True in database

3. **Enrich Product**:
   - Click Edit on the product
   - Verify missing fields are listed (brand, slug if blank)
   - Enter brand: "Craft Supplies Co"
   - Enter/verify slug: "holiday-gift-tags"
   - Save

4. **Verify Promotion**:
   - Verify indicator changes to "Complete"
   - Verify is_provisional=False in database

5. **Verify Inventory**:
   - Navigate to Materials Inventory
   - Verify the purchase from step 1 shows with correct quantities

**Validation Checklist**:
- [ ] CLI creates provisional product
- [ ] CLI records purchase correctly
- [ ] UI shows provisional indicator
- [ ] Edit dialog shows missing fields
- [ ] Saving complete product clears is_provisional
- [ ] Table updates to show new status
- [ ] Inventory correctly linked to product

**Files**: N/A (manual testing)

**Parallel?**: Yes - can run alongside T046

---

### Subtask T048 - Verify FIFO Display Order Consistency

**Purpose**: Ensure FIFO ordering is consistent across UI components.

**Test Scenario**:
1. **Create Multiple Inventory Items**:
   - Purchase material on 2026-01-10 (older)
   - Purchase same material on 2026-01-15 (middle)
   - Purchase same material on 2026-01-17 (newest)

2. **Check Display Order**:
   - Navigate to Materials Inventory
   - Verify items show newest first by default (2026-01-17 at top)
   - Click "Date" column header
   - Verify sort toggles to oldest first (2026-01-10 at top)
   - Click again to return to newest first

3. **Verify FIFO Consumption** (if applicable):
   - Note: FIFO consumption is handled by F058 service
   - Verify display order is DIFFERENT from consumption order
   - Display: newest first (for user visibility)
   - Consumption: oldest first (FIFO)

**Validation Checklist**:
- [ ] Default sort is purchased_at DESC (newest first)
- [ ] Sort toggle works correctly
- [ ] Sort indicator shows current state
- [ ] Sort state persists during session

**Files**: N/A (manual testing)

---

### Subtask T049 - Edge Case Testing

**Purpose**: Verify graceful handling of edge cases.

**Test Cases**:

1. **Empty States**:
   - [ ] Materials Inventory shows "No items" when empty
   - [ ] Product dropdown shows "No products available" when empty
   - [ ] Adjustment dialog handles missing data gracefully

2. **Validation Errors**:
   - [ ] Purchase form rejects negative quantities
   - [ ] Purchase form rejects negative costs
   - [ ] Adjustment rejects percentage > 100
   - [ ] Adjustment prevents negative quantity result

3. **Large Quantities**:
   - [ ] Purchase with qty=10000 works correctly
   - [ ] Display formatting handles large numbers
   - [ ] Decimal precision maintained

4. **Boundary Values**:
   - [ ] Quantity=0 after adjustment (fully depleted)
   - [ ] Percentage=0 (fully depleted)
   - [ ] Percentage=100 (no change)
   - [ ] Cost=$0.00 (free material)

5. **Concurrent Operations**:
   - [ ] Multiple purchases for same product
   - [ ] Adjustment during data refresh
   - [ ] Filter change during sort

**Validation Checklist**:
- [ ] All empty states show appropriate messages
- [ ] All validation errors show helpful messages
- [ ] Large numbers display correctly
- [ ] Boundary values handled correctly
- [ ] No crashes or data corruption

**Files**: N/A (manual testing)

---

### Subtask T050 - Code Review and Cleanup

**Purpose**: Ensure code quality before merge.

**Review Checklist**:

1. **Remove Debug Code**:
   - [ ] No `print()` statements (except CLI output)
   - [ ] No `console.log()` or equivalent
   - [ ] No commented-out code blocks
   - [ ] No TODO comments without issue numbers

2. **Consistent Formatting**:
   - [ ] Run `black src/` and verify no changes
   - [ ] Run `flake8 src/` and address warnings
   - [ ] Run `mypy src/` for type hints (if applicable)

3. **Documentation**:
   - [ ] New functions have docstrings
   - [ ] Complex logic has inline comments
   - [ ] No excessive comments (code should be self-documenting)

4. **Test Coverage**:
   - [ ] Run `pytest --cov=src` for new files
   - [ ] Verify >70% coverage for new service code
   - [ ] UI code may have lower coverage (manual testing)

5. **Import Cleanup**:
   - [ ] No unused imports
   - [ ] Imports sorted (if using isort)
   - [ ] No circular import issues

6. **Security Review**:
   - [ ] No SQL injection vulnerabilities (using ORM)
   - [ ] No command injection (CLI args validated)
   - [ ] Input validation on all user inputs

**Commands**:
```bash
# Format check
black --check src/

# Lint check
flake8 src/

# Type check (if configured)
mypy src/

# Test with coverage
./run-tests.sh --cov=src --cov-report=term-missing
```

**Files**: All new/modified files from WP01-WP08

---

## Definition of Done Checklist

- [ ] T046: E2E Purchase → View → Adjust passes
- [ ] T047: E2E CLI provisional → UI enrichment passes
- [ ] T048: FIFO display order verified consistent
- [ ] T049: All edge cases handled gracefully
- [ ] T050: Code review complete, no issues
- [ ] All FR-001 through FR-022 satisfied (verify against spec)
- [ ] All User Stories 1-6 workable
- [ ] Ready for `/spec-kitty.accept`

---

## Acceptance Criteria Cross-Reference

**From spec.md - verify each is satisfied**:

User Story 1 - Material Purchase:
- [ ] FR-001: Product type selector (Food/Material) exists
- [ ] FR-002: Material fields show when Material selected
- [ ] FR-003: Real-time calculation works
- [ ] FR-004: Validation on submit works
- [ ] FR-005: Purchase creates inventory item

User Story 2 - View Inventory:
- [ ] FR-006: Materials section in Purchases tab
- [ ] FR-007: Sort by column headers
- [ ] FR-008: Filter by product/date/depleted
- [ ] FR-009: Show/hide depleted items

User Story 3 - Adjust Inventory:
- [ ] FR-010: Adjust action available
- [ ] FR-011: "each" adjustment UI
- [ ] FR-012: "variable" percentage UI
- [ ] FR-013: Live preview
- [ ] FR-014: Notes field
- [ ] FR-015: Validation (non-negative)

User Story 4 - Quick CLI Purchase:
- [ ] FR-016: CLI command exists
- [ ] FR-017: Product lookup works
- [ ] FR-018: Provisional creation works
- [ ] FR-019: Success output helpful

User Story 5 - Enrich Provisional:
- [ ] FR-020: Provisional indicator visible
- [ ] FR-021: Edit shows missing fields
- [ ] FR-022: Auto-clears on completion

User Story 6 - MaterialUnit Enhancement:
- [ ] Unit type displayed
- [ ] Quantity label dynamic
- [ ] "each" locked to 1
- [ ] Preview shows consumption

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Integration bugs | Test each workflow step-by-step |
| Regression in existing features | Run full test suite before merge |
| Missed edge cases | Structured edge case checklist |

---

## Review Guidance

- This WP is validation-focused, not feature-focused
- Issues found should be fixed in the originating WP if possible
- Only fix issues directly here if they're integration-related
- Document any known issues that can't be fixed immediately

---

## Activity Log

- 2026-01-18T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-19T03:50:41Z – claude-opus – shell_pid=18602 – lane=doing – Started implementation via workflow command
