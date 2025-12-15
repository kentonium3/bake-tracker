---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
title: "Model Layer Changes"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "83880"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-15T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Model Layer Changes

## Objectives & Success Criteria

- Rename `purchase_unit` column to `package_unit` in the Product model
- Rename `purchase_quantity` column to `package_unit_quantity` in the Product model
- Update all docstrings and comments to reflect the new field names
- **Success**: `grep -n "package_unit\|package_unit_quantity" src/models/product.py` shows the column definitions

## Context & Constraints

### Prerequisites
- This is the foundational work package; no dependencies.

### Related Documents
- Spec: `kitty-specs/021-field-naming-consistency/spec.md` (FR-001, FR-002, FR-003)
- Plan: `kitty-specs/021-field-naming-consistency/plan.md`
- Data Model: `kitty-specs/021-field-naming-consistency/data-model.md`

### Constraints
- **DO NOT** change any other fields or relationships in the model.
- **DO NOT** create SQL migration scripts (Constitution v1.2.0 - use export/reset/import).
- Keep the same data types, constraints, and nullability.

## Subtasks & Detailed Guidance

### Subtask T001 - Rename purchase_unit column to package_unit

**Purpose**: Rename the column to better describe its meaning (package contents, not purchase transaction).

**Steps**:
1. Open `src/models/product.py`
2. Find line ~58: `purchase_unit = Column(String(50), nullable=False)`
3. Rename to: `package_unit = Column(String(50), nullable=False)`
4. Update the inline comment if present

**Files**: `src/models/product.py`

**Parallel?**: No - must be done with T002 and T003 in sequence.

### Subtask T002 - Rename purchase_quantity column to package_unit_quantity

**Purpose**: Rename to match new naming convention and clarify the field's meaning.

**Steps**:
1. In `src/models/product.py`
2. Find line ~59: `purchase_quantity = Column(Float, nullable=False)`
3. Rename to: `package_unit_quantity = Column(Float, nullable=False)`
4. Update the inline comment if present

**Files**: `src/models/product.py`

**Parallel?**: No - must be done with T001 and T003 in sequence.

### Subtask T003 - Update Product model docstrings and comments

**Purpose**: Ensure documentation reflects the new field names.

**Steps**:
1. Update the class-level docstring in `Product` class (~lines 22-43)
2. Find references to `purchase_unit` and `purchase_quantity` in docstring
3. Replace with `package_unit` and `package_unit_quantity`
4. Update any inline comments referencing these fields
5. Optionally add a comment noting the rename (e.g., "# Renamed from purchase_unit in v3.4")

**Files**: `src/models/product.py`

**Parallel?**: No - part of the same file update.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Database schema mismatch | This is expected; use export/reset/import cycle per Constitution |
| Breaking imports in other files | Other WPs handle those updates |

## Definition of Done Checklist

- [ ] `purchase_unit` column renamed to `package_unit`
- [ ] `purchase_quantity` column renamed to `package_unit_quantity`
- [ ] Class docstring updated with new field names
- [ ] Any inline comments updated
- [ ] File saves without syntax errors
- [ ] `tasks.md` updated with status change

## Review Guidance

- Verify ONLY the Product model file was changed
- Confirm column definitions use exact names: `package_unit`, `package_unit_quantity`
- Confirm docstrings reference new names
- Confirm no other fields or relationships were modified

## Activity Log

- 2025-12-15T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-15T17:07:10Z – claude – shell_pid=83880 – lane=doing – Started implementation
