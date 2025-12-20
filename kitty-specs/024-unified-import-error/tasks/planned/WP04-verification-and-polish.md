---
work_package_id: "WP04"
subtasks:
  - "T008"
  - "T009"
title: "Verification and Polish"
phase: "Phase 4 - Unified Import Path Verification"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-19T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Verification and Polish

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Verify unified import still works correctly, run all manual test scenarios, ensure no regressions.

**Success Criteria**:
- Unified import (File > Import Data) works exactly as before
- Log path now displays as relative (enhancement, not breaking change)
- All manual test scenarios pass per spec
- Both import paths produce consistent user experience

## Context & Constraints

**Reference Documents**:
- Feature Spec: `kitty-specs/024-unified-import-error/spec.md` (User Story 5, Edge Cases)
- Implementation Plan: `kitty-specs/024-unified-import-error/plan.md` (Phase 4)
- Testing Checklist: `kitty-specs/024-unified-import-error/spec.md` (Success Criteria)

**Dependencies**:
- **WP01, WP02, WP03**: All implementation must be complete

**Critical Constraint**:
This is the final verification gate. Feature should not be marked complete until all scenarios pass.

## Subtasks & Detailed Guidance

### Subtask T008 - Verify Unified Import Path

**Purpose**: Confirm the unified import (v3.4) still works correctly with the relative path change.

**Steps**:

1. **Launch the application**:
   ```bash
   cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/024-unified-import-error
   source venv/bin/activate
   python src/main.py
   ```

2. **Perform a unified import**:
   - File > Import Data
   - Select a valid backup JSON file
   - Choose "Merge" mode
   - Click "Import"

3. **Verify ImportResultsDialog behavior**:
   - [ ] Dialog appears with "Import Complete" title
   - [ ] Summary shows record counts
   - [ ] "Copy to Clipboard" button works
   - [ ] Log path is displayed (now relative, e.g., `docs/user_testing/import_...`)
   - [ ] Close button works

4. **Verify log file**:
   - [ ] Log file created in `docs/user_testing/`
   - [ ] Log contains expected format (timestamp, source, mode, summary)
   - [ ] Log file is UTF-8 encoded

5. **Test error scenarios**:
   - [ ] Import a file with intentional errors
   - [ ] Verify errors are displayed in scrollable dialog
   - [ ] Verify copy includes all errors

**Parallel?**: Yes - independent verification activity.

**Expected Results**:
- All existing unified import functionality works
- Only change: log path display is now relative instead of absolute

### Subtask T009 - Run Manual Test Scenarios

**Purpose**: Execute all manual test scenarios from the spec to ensure complete feature coverage.

**Steps**:

#### Scenario 1: Many Errors (10+)
1. Create or use a catalog file with 20+ validation errors
2. File > Import Catalog
3. Select the file, leave defaults, click Import
4. **Verify**: All errors visible via scrolling (not truncated to 5)

#### Scenario 2: Suggestions Displayed
1. Create a catalog file with unit validation errors (e.g., `"unit": "whole"`)
2. Import the file
3. **Verify**: Each error shows suggestion with valid units list

#### Scenario 3: Copy to Clipboard
1. After import with errors, click "Copy to Clipboard"
2. Paste into a text editor
3. **Verify**: All errors and suggestions are included, properly formatted

#### Scenario 4: Log File Written
1. Complete any catalog import
2. Check `docs/user_testing/` directory
3. **Verify**: New log file exists with timestamp in name
4. **Verify**: Log contains all errors (not truncated)
5. **Verify**: Suggestions included in log

#### Scenario 5: Relative Path Display
1. Complete an import (unified or catalog)
2. Look at log path in dialog
3. **Verify**: Path is relative (e.g., `docs/user_testing/import_...`)
4. **Verify**: NOT absolute (e.g., `/Users/kentgale/...`)

#### Scenario 6: Dry-Run Mode
1. File > Import Catalog
2. Check "Preview changes before importing (dry-run)"
3. Click "Preview..."
4. **Verify**: "DRY RUN - No changes made" at top of results
5. **Verify**: Title is "Preview Complete"
6. **Verify**: Log file still written
7. **Verify**: Catalog dialog stays open after closing results

#### Scenario 7: ADD_ONLY Mode
1. Import a catalog with new entities using "Add Only" mode
2. **Verify**: Results show "added" counts
3. **Verify**: Dialog works correctly

#### Scenario 8: AUGMENT Mode
1. Import a catalog with existing entities using "Augment" mode
2. **Verify**: Results show "augmented" counts
3. **Verify**: Dialog works correctly

#### Scenario 9: Zero Errors
1. Import a valid catalog with no errors
2. **Verify**: Success summary shown with log path
3. **Verify**: No error section (or empty error section)

#### Scenario 10: 100+ Errors
1. Import a catalog with 100+ errors
2. **Verify**: All errors visible via scrolling
3. **Verify**: Dialog remains responsive
4. **Verify**: Copy includes all 100+ errors

**Parallel?**: Yes - can run alongside T008.

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Subtle regression in unified import | Low | High | Explicit verification step (T008) |
| Test data not available | Medium | Medium | Create test files or use existing test data |
| Performance with 100+ errors | Low | Low | CTkTextbox handles large text well |

## Definition of Done Checklist

- [ ] T008: Unified import verified working
- [ ] T008: Log path now shows as relative
- [ ] T009: Scenario 1 - Many errors visible
- [ ] T009: Scenario 2 - Suggestions displayed
- [ ] T009: Scenario 3 - Copy to clipboard works
- [ ] T009: Scenario 4 - Log file written correctly
- [ ] T009: Scenario 5 - Relative paths displayed
- [ ] T009: Scenario 6 - Dry-run mode works
- [ ] T009: Scenario 7 - ADD_ONLY mode works
- [ ] T009: Scenario 8 - AUGMENT mode works
- [ ] T009: Scenario 9 - Zero errors handled
- [ ] T009: Scenario 10 - 100+ errors handled
- [ ] All success criteria from spec verified
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Checkpoints**:
1. All 10 manual test scenarios pass
2. No regressions in unified import path
3. Consistent user experience between import types

**Final Acceptance**:
This work package completes the feature. After verification:
1. Run `/spec-kitty.review` for code review
2. Run `/spec-kitty.accept` for final acceptance
3. Run `/spec-kitty.merge` to merge to main

## Activity Log

- 2025-12-19T00:00:00Z - system - lane=planned - Prompt created.
