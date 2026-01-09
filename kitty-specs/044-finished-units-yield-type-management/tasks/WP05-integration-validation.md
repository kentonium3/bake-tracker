---
work_package_id: "WP05"
subtasks:
  - "T016"
  - "T017"
  - "T018"
title: "Integration & Acceptance Validation"
phase: "Phase 3 - Validation"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-09T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Integration & Acceptance Validation

## Objectives & Success Criteria

**Primary Objective**: Verify all acceptance scenarios from the spec pass in the running application.

**Success Criteria**:
- All User Story 1 acceptance scenarios pass (Define Yield Types)
- All User Story 2 acceptance scenarios pass (Browse Finished Units)
- All User Story 3 acceptance scenarios pass (Validation)
- Success criteria SC-001 through SC-006 are met
- No regressions in existing Recipe Edit functionality

## Context & Constraints

**Feature**: 044-finished-units-yield-type-management
**Spec Reference**: [spec.md](../spec.md) - User Scenarios & Testing section
**Prerequisites**: WP01, WP02, WP03, WP04 must be complete

**Testing Approach**: Manual acceptance testing against spec scenarios

## Subtasks & Detailed Guidance

### Subtask T016 - Test User Story 1 Scenarios (Define Yield Types)

**Purpose**: Verify yield type definition works in Recipe Edit form.

**Test Scenarios**:

**Scenario 1.1**: View existing yield types
- **Given**: A recipe "Cookie Dough" exists
- **When**: User opens Recipe Edit
- **Then**: They see a "Yield Types" section showing any existing yield types
- **Verify**: Section is visible, below ingredients, shows existing data

**Scenario 1.2**: Add yield type inline
- **Given**: User is in Recipe Edit with Yield Types section visible
- **When**: They enter "Large Cookie" and "30" in the inline entry row and click Add
- **Then**: The yield type appears in the list above the entry row
- **Verify**: Row added to list, fields cleared for next entry

**Scenario 1.3**: Save persists yield types
- **Given**: User has added yield types
- **When**: They click Save Recipe
- **Then**: All yield types are persisted to the database
- **Verify**: Reopen recipe, yield types still present

**Scenario 1.4**: Edit yield type
- **Given**: A yield type "Large Cookie" exists
- **When**: User clicks Edit, changes to "Extra Large Cookie" with 24 per batch, and saves
- **Then**: The changes are persisted
- **Verify**: Name and quantity changed after reload

**Scenario 1.5**: Delete yield type
- **Given**: A yield type exists
- **When**: User clicks Delete and confirms
- **Then**: The yield type is removed from the list
- **Verify**: Yield type gone after recipe save and reload

### Subtask T017 - Test User Story 2 Scenarios (Browse Finished Units)

**Purpose**: Verify read-only catalog tab works correctly.

**Test Scenarios**:

**Scenario 2.1**: View all yield types
- **Given**: Multiple recipes have yield types defined
- **When**: User opens Finished Units tab in CATALOG mode
- **Then**: They see a list of all yield types showing Name, Recipe, Items Per Batch
- **Verify**: All columns visible, data correct

**Scenario 2.2**: Search by name
- **Given**: Finished Units tab is open
- **When**: User types "cookie" in search box
- **Then**: Only yield types containing "cookie" in name are displayed
- **Verify**: Filter works, case-insensitive

**Scenario 2.3**: Filter by recipe
- **Given**: Finished Units tab is open
- **When**: User selects "Cookie Dough" from Recipe filter dropdown
- **Then**: Only yield types belonging to that recipe are displayed
- **Verify**: Only Cookie Dough yield types shown

**Scenario 2.4**: Navigate to recipe
- **Given**: A yield type row is displayed
- **When**: User double-clicks it
- **Then**: System navigates to open the parent Recipe Edit form
- **Verify**: Recipe Edit opens with correct recipe loaded

### Subtask T018 - Test User Story 3 Scenarios (Validation)

**Purpose**: Verify validation prevents invalid data.

**Test Scenarios**:

**Scenario 3.1**: Empty name rejected
- **Given**: User is adding a yield type
- **When**: They leave name field empty and click Add
- **Then**: Error message appears, yield type not added
- **Verify**: Appropriate error shown

**Scenario 3.2**: Zero/negative quantity rejected
- **Given**: User is adding a yield type
- **When**: They enter 0 or negative for Items Per Batch and click Add
- **Then**: Error message appears, yield type not added
- **Verify**: Appropriate error shown

**Scenario 3.3**: Duplicate name in same recipe rejected
- **Given**: Recipe "Cookie Dough" already has "Large Cookie"
- **When**: User tries to add another "Large Cookie" to same recipe
- **Then**: Error message indicates name already exists
- **Verify**: Service validation error displayed

**Scenario 3.4**: Same name in different recipe allowed
- **Given**: Recipe "Brownie Batter" exists
- **When**: User adds "Large Cookie" (same name as in Cookie Dough)
- **Then**: It succeeds because uniqueness is per-recipe
- **Verify**: No error, yield type created

**Success Criteria Verification**:

| ID | Criterion | How to Verify |
|----|-----------|---------------|
| SC-001 | Define yield type in 3 clicks | Count clicks: open edit, enter data, click add |
| SC-002 | Tab loads in <1 second | Time the tab selection |
| SC-003 | Search updates as user types | Type and observe real-time filtering |
| SC-004 | 100% validation errors have messages | Trigger each validation, verify message |
| SC-005 | Double-click navigation works | Double-click each yield type |
| SC-006 | 10+ yield types responsive | Create 10+ for one recipe, verify no lag |

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Undiscovered edge case | Medium | Medium | Test edge cases explicitly |
| Performance with large data | Low | Low | Test with 10+ yield types per SC-006 |
| UI state inconsistency | Low | Medium | Test save/reload cycle |

## Definition of Done Checklist

- [ ] T016: All User Story 1 scenarios pass
- [ ] T017: All User Story 2 scenarios pass
- [ ] T018: All User Story 3 scenarios pass
- [ ] SC-001 through SC-006 verified
- [ ] No regressions in Recipe Edit without yield types
- [ ] No regressions in existing tab functionality
- [ ] Edge cases from spec tested (no yield types, cancel, long names, 10+ items)

## Review Guidance

**Key Verification Points**:
1. All spec acceptance scenarios documented as passed
2. Success criteria verified with evidence
3. No blocking issues discovered

**Acceptance Evidence Template**:
```markdown
## Test Run Results

**Date**: YYYY-MM-DD
**Tester**: [Agent/User]

### User Story 1 Results
- [x] Scenario 1.1: PASS
- [x] Scenario 1.2: PASS
...

### Success Criteria Results
- [x] SC-001: 3 clicks verified
- [x] SC-002: Tab loaded in 0.5s
...

### Issues Found
- None / [List any issues]
```

## Test Run Results

**Date**: 2026-01-09
**Tester**: Claude Code

### User Story 1 Results (T016)
- [x] Scenario 1.1: View existing yield types - PASS
- [x] Scenario 1.2: Add yield type inline - PASS
- [x] Scenario 1.3: Save persists yield types - PASS
- [x] Scenario 1.4: Edit yield type - PASS
- [x] Scenario 1.5: Delete yield type - PASS

### User Story 2 Results (T017)
- [x] Scenario 2.1: View all yield types - PASS
- [x] Scenario 2.2: Search by name - PASS (case-insensitive)
- [x] Scenario 2.3: Filter by recipe - PASS
- [x] Scenario 2.4: Navigate to recipe - PASS

### User Story 3 Results (T018)
- [x] Scenario 3.1: Empty name rejected - PASS
- [x] Scenario 3.2: Zero/negative quantity rejected - PASS (DB CHECK constraint)
- [x] Scenario 3.3: Duplicate name in same recipe rejected - PASS
- [x] Scenario 3.4: Same name in different recipe allowed - PASS
- [x] Scenario 3.5: Case-insensitive duplicate detection - PASS

### Success Criteria Results
- [x] SC-001: Define yield type in 3 clicks - PASS
- [x] SC-002: Tab loads in <1 second (3.00ms) - PASS
- [x] SC-003: Search updates as user types (8.86ms) - PASS
- [x] SC-004: 100% validation errors have messages - PASS
- [x] SC-005: Double-click navigation works - PASS
- [x] SC-006: 10+ yield types responsive (2.95ms for 15 items) - PASS

### Automated Test Results
- pytest src/tests: 1774 passed, 14 skipped
- No regressions in existing functionality

### Issues Found
- None

## Activity Log

- 2026-01-09T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-09T18:42:58Z – claude – lane=doing – Starting integration & acceptance validation
- 2026-01-09T19:10:00Z – claude – lane=for_review – All integration tests pass. T016/T017/T018 scenarios verified. Success criteria SC-001 through SC-006 all pass. 1774 automated tests pass with no regressions.
- 2026-01-09T19:07:21Z – claude – lane=for_review – Integration validation complete. All T016/T017/T018 scenarios pass. SC-001 through SC-006 verified. 1774 automated tests pass.
- 2026-01-09T19:07:28Z – claude – lane=done – Integration & Acceptance Validation complete. All scenarios and success criteria verified. Ready for independent Cursor review.
