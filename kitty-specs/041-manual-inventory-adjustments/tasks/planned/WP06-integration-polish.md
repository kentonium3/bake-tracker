---
work_package_id: "WP06"
subtasks:
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
title: "Integration Testing & Polish"
phase: "Phase 3 - Integration (Both Agents)"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
history:
  - timestamp: "2026-01-07T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Integration Testing & Polish

## Objectives & Success Criteria

- Validate all acceptance scenarios from spec.md
- Verify performance meets success criteria
- Ensure complete feature works end-to-end
- Document any issues found

**Success**: All acceptance scenarios pass; performance targets met (SC-001 to SC-005).

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/041-manual-inventory-adjustments/spec.md` (acceptance scenarios)
- Success Criteria from spec:
  - SC-001: Depletion in under 30 seconds
  - SC-002: 100% audit trail coverage
  - SC-003: Live preview updates within 100ms
  - SC-004: Zero data entry beyond amount for standard depletions
  - SC-005: Inventory accuracy improves

**Dependencies**:
- All previous work packages (WP01-WP05) must be complete

## Subtasks & Detailed Guidance

### Subtask T030 - Integration: Spoilage scenario (User Story 1) [P]

**Purpose**: Validate primary use case end-to-end.

**Steps**:
1. Start with inventory item showing 10 cups
2. Click [Adjust] button
3. Enter 5 cups reduction
4. Select "Spoilage/Waste" reason
5. Enter note "Weevils discovered"
6. Click Apply
7. **Verify**: Inventory shows 5 cups remaining
8. **Verify**: History shows adjustment with reason and notes

**Acceptance Criteria** (from spec):
> Given user has 10 cups of flour in inventory, When user opens adjustment dialog, enters 5 cups reduction with "Spoilage" reason and note "Weevils discovered", Then inventory shows 5 cups remaining and depletion history shows the adjustment with reason and notes.

**Files**: Manual testing / test script
**Parallel?**: Yes - independent scenario

### Subtask T031 - Integration: Correction scenario (User Story 2) [P]

**Purpose**: Validate physical count correction use case.

**Steps**:
1. Start with inventory item showing 10 cups
2. Click [Adjust] button
3. Enter 3 cups reduction (physical count shows 7)
4. Select "Physical Count Correction" reason
5. Click Apply
6. **Verify**: Inventory shows 7 cups
7. **Verify**: History shows correction

**Acceptance Criteria** (from spec):
> Given system shows 10 cups sugar but physical count is 7, When user reduces by 3 cups with "Physical Count Correction" reason, Then inventory shows 7 cups and history shows correction.

**Files**: Manual testing / test script
**Parallel?**: Yes - independent scenario

### Subtask T032 - Integration: Gift scenario (User Story 3) [P]

**Purpose**: Validate gift/donation tracking use case.

**Steps**:
1. Start with inventory item showing 6 cups
2. Click [Adjust] button
3. Enter 2 cups reduction
4. Select "Gift/Donation" reason
5. Enter note "Gave to neighbor for cookies"
6. Click Apply
7. **Verify**: Inventory shows 4 cups
8. **Verify**: History shows gift with notes

**Acceptance Criteria** (from spec):
> Given user has 6 cups chocolate chips, When user depletes 2 cups with "Gift" reason and note "Gave to neighbor for cookies", Then inventory shows 4 cups and history shows gift with notes.

**Files**: Manual testing / test script
**Parallel?**: Yes - independent scenario

### Subtask T033 - Integration: Ad Hoc scenario (User Story 4) [P]

**Purpose**: Validate ad hoc usage tracking.

**Steps**:
1. Start with inventory of eggs
2. Click [Adjust] button
3. Enter quantity reduction
4. Select "Ad Hoc Usage (Testing/Personal)" reason
5. Click Apply
6. **Verify**: Inventory reflects the usage

**Acceptance Criteria** (from spec):
> Given user used 2 eggs testing a recipe outside the app, When user depletes with "Ad Hoc Usage" reason, Then inventory reflects the usage.

**Files**: Manual testing / test script
**Parallel?**: Yes - independent scenario

### Subtask T034 - Integration: Validation prevents exceeding quantity [P]

**Purpose**: Verify validation edge case.

**Steps**:
1. Start with inventory item showing 3 cups
2. Click [Adjust] button
3. Enter 5 cups reduction (more than available)
4. **Verify**: System shows validation error
5. **Verify**: Adjustment is NOT applied
6. **Verify**: Inventory still shows 3 cups

**Acceptance Criteria** (from spec):
> Given user has 3 cups of an ingredient, When user attempts to deplete 5 cups, Then system shows validation error "Cannot reduce by more than available quantity" and prevents the adjustment.

**Files**: Manual testing / test script
**Parallel?**: Yes - independent scenario

### Subtask T035 - Integration: Notes required for OTHER [P]

**Purpose**: Verify notes validation.

**Steps**:
1. Click [Adjust] on any inventory item
2. Enter valid quantity
3. Select "Other (specify in notes)"
4. Leave notes empty
5. Click Apply
6. **Verify**: Error message appears requiring notes
7. Enter notes and try again
8. **Verify**: Adjustment succeeds

**Files**: Manual testing / test script
**Parallel?**: Yes - independent scenario

### Subtask T036 - Verify preview < 100ms (SC-003) [P]

**Purpose**: Verify performance target.

**Steps**:
1. Open adjustment dialog
2. Start typing in quantity field
3. **Observe**: Preview updates should feel instant
4. **Measure** (if possible): Time between keypress and preview update

**Success Criteria**:
> SC-003: Live preview updates within 100ms of user input (perceived as instant)

**Method**: Visual observation - if there's any perceptible lag, it fails.

**Files**: Manual testing
**Parallel?**: Yes - performance test

### Subtask T037 - Verify depletion < 30 seconds (SC-001) [P]

**Purpose**: Verify efficiency target.

**Steps**:
1. Time the complete workflow:
   - Start: Click [Adjust] button
   - Enter quantity
   - Select reason
   - Click Apply
   - End: See success confirmation
2. **Target**: Under 30 seconds for simple depletion

**Success Criteria**:
> SC-001: Users can complete a simple inventory depletion (single item, standard reason) in under 30 seconds

**Method**: Stopwatch timing of 3 attempts, average should be under 30 seconds.

**Files**: Manual testing
**Parallel?**: Yes - performance test

## Test Strategy

**Manual Integration Testing Checklist**:
```
[ ] T030: Spoilage scenario passes
[ ] T031: Correction scenario passes
[ ] T032: Gift scenario passes
[ ] T033: Ad Hoc scenario passes
[ ] T034: Quantity validation works
[ ] T035: Notes validation for OTHER works
[ ] T036: Preview feels instant (<100ms)
[ ] T037: Workflow under 30 seconds
```

**Edge Cases to Also Check**:
```
[ ] Zero quantity result allowed (deplete all remaining)
[ ] Decimal quantities work (2.5 cups)
[ ] Very long notes truncate correctly in history
[ ] History sorted newest first
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Test database needs setup | Delays | Use existing test data or create setup script |
| Performance varies by machine | False failures | Test on representative hardware |
| Edge cases missed | Bugs | Review spec edge cases section |

## Definition of Done Checklist

- [ ] All acceptance scenarios (T030-T035) pass
- [ ] Live preview performance verified (T036)
- [ ] Workflow efficiency verified (T037)
- [ ] Edge cases tested (zero result, decimals, long notes)
- [ ] No regressions in existing functionality
- [ ] All issues documented and resolved

## Review Guidance

- Run through all acceptance scenarios from spec.md
- Verify audit trail is complete (who, when, why, how much)
- Check depletion history includes both automatic and manual entries
- Verify no negative inventory possible

## Activity Log

- 2026-01-07T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
