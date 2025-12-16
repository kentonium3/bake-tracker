---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
title: "UI Layer Changes"
phase: "Phase 2 - Core Logic"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "83880"
review_status: "approved without changes"
reviewed_by: "claude-reviewer"
history:
  - timestamp: "2025-12-15T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: "automated"
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - UI Layer Changes

## Objectives & Success Criteria

- Update UI code variable names that reference the old field names
- **CRITICAL**: Preserve all user-facing "Pantry" labels unchanged
- **Success**: `grep -rn "purchase_unit\|purchase_quantity" src/ui/ src/utils/` returns zero matches

## Context & Constraints

### Prerequisites
- WP01 (Model Layer Changes) must be completed first.

### Related Documents
- Spec: `kitty-specs/021-field-naming-consistency/spec.md` (FR-015, FR-016)
- User Story 2: "User Sees Familiar 'Pantry' Labels"

### Constraints
- **DO NOT** change any user-facing string literals.
- Only rename internal variable names that reference model fields.
- User must still see "Pantry" in UI tabs, labels, buttons, and messages.

## Subtasks & Detailed Guidance

### Subtask T013 - Update inventory_tab.py

**Purpose**: Update internal variable names in the inventory tab.

**Steps**:
1. Open `src/ui/inventory_tab.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace variable names with `package_unit` and `package_unit_quantity`
4. **DO NOT** change any string literals like `"Pantry"`, `"Purchase Unit"`, etc.

**Files**: `src/ui/inventory_tab.py`

**Parallel?**: Yes - can be done alongside other UI updates.

**Notes**: If a variable is used for display purposes (like column headers), only rename the variable, not the display string.

### Subtask T014 - Update ingredients_tab.py

**Purpose**: Update internal variable names in the ingredients tab.

**Steps**:
1. Open `src/ui/ingredients_tab.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace variable names with `package_unit` and `package_unit_quantity`
4. **DO NOT** change any string literals

**Files**: `src/ui/ingredients_tab.py`

**Parallel?**: Yes.

### Subtask T015 - Update recipe_form.py

**Purpose**: Update internal variable names in recipe forms.

**Steps**:
1. Open `src/ui/forms/recipe_form.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace variable names with `package_unit` and `package_unit_quantity`
4. **DO NOT** change any string literals

**Files**: `src/ui/forms/recipe_form.py`

**Parallel?**: Yes.

### Subtask T016 - Update ingredient_form.py

**Purpose**: Update internal variable names in ingredient forms.

**Steps**:
1. Open `src/ui/forms/ingredient_form.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace variable names with `package_unit` and `package_unit_quantity`
4. **DO NOT** change any string literals

**Files**: `src/ui/forms/ingredient_form.py`

**Parallel?**: Yes.

### Subtask T017 - Update data_table.py

**Purpose**: Update internal variable names in data table widget.

**Steps**:
1. Open `src/ui/widgets/data_table.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace variable names with `package_unit` and `package_unit_quantity`
4. **DO NOT** change any column header strings or display text

**Files**: `src/ui/widgets/data_table.py`

**Parallel?**: Yes.

### Subtask T018 - Update validators.py

**Purpose**: Update field references in validation utilities.

**Steps**:
1. Open `src/utils/validators.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace with `package_unit` and `package_unit_quantity`
4. Update any validation error messages if they reference field names internally

**Files**: `src/utils/validators.py`

**Parallel?**: Yes.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Accidentally changing user-facing labels | Only change Python variable names, never string literals |
| Breaking UI layout | Test UI after changes to verify display is unchanged |

## Definition of Done Checklist

- [ ] All UI files updated
- [ ] `grep -rn "purchase_unit\|purchase_quantity" src/ui/ src/utils/` returns zero matches
- [ ] No user-facing string literals were changed
- [ ] UI still displays "Pantry" in tabs and forms
- [ ] No syntax errors in any UI file
- [ ] `tasks.md` updated with status change

## Review Guidance

- Run the application and verify "Pantry" appears in UI
- Check that no string literals were changed (only variable names)
- Run grep to confirm zero matches for old field names

## Activity Log

- 2025-12-15T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-15T17:15:54Z – claude – shell_pid=83880 – lane=doing – Started implementation
- 2025-12-15T17:35:00Z – claude – shell_pid=83880 – lane=doing – Completed: Updated 5 UI files (T013-T018) + validators.py. grep returns zero matches.
- 2025-12-15T17:20:31Z – claude – shell_pid=83880 – lane=for_review – Ready for review
- 2025-12-15T21:51:57Z – claude – shell_pid=83880 – lane=done – Code review approved: UI layer correctly updated
