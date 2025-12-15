---
work_package_id: "WP06"
subtasks:
  - "T049"
  - "T050"
  - "T051"
  - "T052"
  - "T057"
title: "Verification and Validation"
phase: "Phase 4 - Final Validation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-15T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Verification and Validation

## Objectives & Success Criteria

- Verify all code changes are complete with zero old terminology matches
- Verify all tests pass
- Verify data integrity through export/import cycle
- Verify UI labels are preserved
- **Success**: All success criteria from spec.md are met (SC-001 through SC-006)

## Context & Constraints

### Prerequisites
- WP01 through WP05 must be completed.

### Related Documents
- Spec: `kitty-specs/021-field-naming-consistency/spec.md` (Success Criteria)
- Quickstart: `kitty-specs/021-field-naming-consistency/quickstart.md` (Verification Checklist)

### Constraints
- Must use export/reset/import workflow per Constitution v1.2.0.
- Do not skip any verification step.

## Subtasks & Detailed Guidance

### Subtask T049 - Run full test suite

**Purpose**: Verify all tests pass after the refactor.

**Steps**:
1. Activate virtual environment: `source venv/bin/activate`
2. Run: `pytest src/tests -v`
3. Verify 100% pass rate
4. If any failures, investigate and fix before proceeding

**Command**:
```bash
pytest src/tests -v
```

**Expected Result**: All tests pass (0 failures, 0 errors)

**Parallel?**: Yes - can run alongside T052.

### Subtask T050 - Verify export/import cycle data integrity

**Purpose**: Ensure data survives the schema change via export/reset/import.

**Steps**:
1. **Document current record counts** (before any changes):
   - Open the application or use a script to count records
   - Record counts for: ingredients, products, purchases, inventory_items, recipes, events, recipients

2. **Export data**:
   - Use File > Export Data in the application
   - Save to a safe location OUTSIDE the project directory
   - Verify the export file is valid JSON

3. **Delete database files**:
   ```bash
   rm -f data/bake_tracker.db data/bake_tracker.db-wal data/bake_tracker.db-shm
   ```

4. **Restart application** to create fresh database with new schema

5. **Import data**:
   - Use File > Import Data
   - Select the exported JSON file
   - Choose "Replace" mode

6. **Verify record counts match**:
   - Compare counts to step 1
   - All counts must match exactly

7. **Verify relationships intact**:
   - Open a recipe and verify ingredients are linked
   - Open an inventory item and verify product is linked
   - Open an event and verify recipients/packages are linked

**Parallel?**: No - sequential steps required.

### Subtask T051 - Verify UI "Pantry" labels preserved

**Purpose**: Ensure user-facing labels were not changed.

**Steps**:
1. Run the application: `python src/main.py`
2. Verify main window has a "Pantry" tab (not "Inventory")
3. Click on the Pantry tab
4. Verify all labels, buttons, and messages use "Pantry" terminology
5. Open any forms related to pantry/inventory
6. Verify form labels use "Pantry" where appropriate

**Expected Locations**:
- Main window tab: "Pantry"
- Any pantry-related form labels
- Any pantry-related buttons or messages

**Parallel?**: No - requires manual UI inspection.

### Subtask T052 - Run grep validation for zero old terminology matches

**Purpose**: Verify no old field names remain in code.

**Steps**:
1. Run the following grep commands:

```bash
# Check for old field names in Python code
grep -rn "purchase_unit\|purchase_quantity" src/ --include="*.py"

# Check for old field names in docs (excluding archive)
grep -rn "purchase_unit\|purchase_quantity" docs/design/

# Check for old field names in sample data
grep -rn "purchase_unit\|purchase_quantity" examples/ test_data/
```

2. All commands should return zero matches
3. If any matches found, go back and fix them

**Expected Result**: Zero matches for all grep commands

**Parallel?**: Yes - can run alongside T049.

### Subtask T057 - Run grep validation for pantry terminology

**Purpose**: Verify `pantry` references in internal code have been renamed to `inventory`, with only acceptable exceptions remaining.

**Steps**:
1. Run the following grep command:

```bash
# Check for pantry references in Python code
grep -rni "pantry" src/ --include="*.py"
```

2. Review each match and categorize:

**Acceptable matches (should remain):**
- UI string literals: `"My Pantry"`, `"pantry items"`, `"Add more to the pantry"` etc.
- Comments explaining history: `"Note: Renamed from PantryItem to InventoryItem"`
- Skip reasons with "(formerly PantryItem)" annotation (if preserved)

**Unacceptable matches (should be fixed):**
- Function names: `test_*_pantry_*`
- Variable names: `pantry_state`, `pantry_qty`
- Class names: `PantryItem`
- Docstrings using "pantry" for internal concepts

3. If unacceptable matches found, return to WP04 to fix them

**Expected Result**:
- Only UI string literals and history comments should remain
- No internal function/variable/class names should contain `pantry`

**Parallel?**: Yes - can run alongside T049 and T052.

## Success Criteria Validation

Map each success criterion from spec.md to verification:

| Criterion | Verification | Status |
|-----------|-------------|--------|
| SC-001: Zero matches for old field names | T052 grep validation | [ ] |
| SC-002: Zero pantry matches in internal code | T057 grep validation (model/service clean; tests need update) | [ ] |
| SC-003: All tests pass (100%) | T049 pytest | [ ] |
| SC-004: UI displays "Pantry" | T051 manual inspection | [ ] |
| SC-005: 100% data preserved | T050 export/import cycle | [ ] |
| SC-006: Import/export spec v3.4 | WP05 completion | [ ] |

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss during export/import | Keep backup of export file; verify counts match |
| Missed code references | Comprehensive grep validation |
| Test failures | Investigate root cause; may indicate missed references |

## Definition of Done Checklist

- [ ] All tests pass (100%) - T049
- [ ] Export/import cycle preserves all data - T050
- [ ] Record counts match before/after - T050
- [ ] UI shows "Pantry" labels - T051
- [ ] Grep returns zero matches for `purchase_unit`/`purchase_quantity` - T052
- [ ] Grep for `pantry` returns only acceptable matches (UI strings, history comments) - T057
- [ ] All success criteria (SC-001 through SC-006) are met
- [ ] `tasks.md` updated with status change

## Review Guidance

- Request test output showing 100% pass rate
- Request record count comparison before/after
- Request screenshot of UI showing "Pantry" tab
- Request grep output showing zero matches

## Activity Log

- 2025-12-15T00:00:00Z - system - lane=planned - Prompt created.
