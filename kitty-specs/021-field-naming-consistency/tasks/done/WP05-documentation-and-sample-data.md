---
work_package_id: "WP05"
subtasks:
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
title: "Documentation and Sample Data"
phase: "Phase 3 - Validation"
lane: "done"
assignee: ""
agent: "system"
shell_pid: ""
review_status: "approved without changes"
reviewed_by: "claude-reviewer"
history:
  - timestamp: "2025-12-15T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Documentation and Sample Data

## Objectives & Success Criteria

- Update import/export specification to v3.4 with changelog documenting the field renames
- Update all sample JSON files to use new field names
- **Success**: `grep -rn "purchase_unit\|purchase_quantity" docs/ examples/ test_data/` returns zero matches (excluding archive)

## Context & Constraints

### Prerequisites
- WP02 (Service Layer) should be completed to ensure import/export code matches documentation.

### Related Documents
- Spec: `kitty-specs/021-field-naming-consistency/spec.md` (FR-017, FR-018, FR-019)
- Current spec: `docs/design/import_export_specification.md` (v3.3)

### Constraints
- Import/export spec must be bumped to v3.4 with proper changelog entry.
- All JSON files must use exact field names: `package_unit`, `package_unit_quantity`.
- Archive files (docs/archive/) do not need to be updated.

## Subtasks & Detailed Guidance

### Subtask T037 - Update import_export_specification.md to v3.4

**Purpose**: Document the field name changes in the official specification.

**Steps**:
1. Open `docs/design/import_export_specification.md`
2. Update version header from 3.3 to 3.4
3. Add changelog entry:
   ```markdown
   ### v3.4 (2025-12-15 - Feature 021)
   - **Changed**: Product fields `purchase_unit` renamed to `package_unit`
   - **Changed**: Product fields `purchase_quantity` renamed to `package_unit_quantity`
   - **Note**: These changes align JSON field names with internal model attribute names
   ```
4. Update the Products entity schema section (~lines 144-179):
   - Change `purchase_unit` to `package_unit` in schema and table
   - Change `purchase_quantity` to `package_unit_quantity`
5. Update Appendix C example (~lines 780-785):
   - Change JSON examples to use new field names
6. Update footer version from 3.2/3.3 to 3.4
7. Ensure validation rules section references new field names if mentioned

**Files**: `docs/design/import_export_specification.md`

**Parallel?**: No - foundational documentation update.

### Subtask T038 - Update examples/import/README.md

**Purpose**: Update documentation examples.

**Steps**:
1. Open `examples/import/README.md`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace with `package_unit` and `package_unit_quantity`

**Files**: `examples/import/README.md`

**Parallel?**: Yes.

### Subtask T039 - Update ai_generated_sample.json

**Purpose**: Update sample import file.

**Steps**:
1. Open `examples/import/ai_generated_sample.json`
2. Find all `"purchase_unit":` and replace with `"package_unit":`
3. Find all `"purchase_quantity":` and replace with `"package_unit_quantity":`

**Files**: `examples/import/ai_generated_sample.json`

**Parallel?**: Yes.

### Subtask T040 - Update combined_import.json

**Steps**:
1. Open `examples/import/combined_import.json`
2. Replace `"purchase_unit":` with `"package_unit":`
3. Replace `"purchase_quantity":` with `"package_unit_quantity":`

**Files**: `examples/import/combined_import.json`

**Parallel?**: Yes.

### Subtask T041 - Update simple_ingredients.json

**Steps**:
1. Open `examples/import/simple_ingredients.json`
2. Replace field names as above

**Files**: `examples/import/simple_ingredients.json`

**Parallel?**: Yes.

### Subtask T042 - Update test_errors.json

**Steps**:
1. Open `examples/import/test_errors.json`
2. Replace field names
3. Update any error message notes that reference the old field names

**Files**: `examples/import/test_errors.json`

**Parallel?**: Yes.

### Subtask T043 - Update examples/test_data.json

**Steps**:
1. Open `examples/test_data.json`
2. Replace field names

**Files**: `examples/test_data.json`

**Parallel?**: Yes.

### Subtask T044 - Update test_data_v2.json

**Steps**:
1. Open `examples/test_data_v2.json`
2. Replace field names

**Files**: `examples/test_data_v2.json`

**Parallel?**: Yes.

### Subtask T045 - Update test_data_v2_original.json

**Steps**:
1. Open `examples/test_data_v2_original.json`
2. Replace field names

**Files**: `examples/test_data_v2_original.json`

**Parallel?**: Yes.

### Subtask T046 - Update sample_catalog.json

**Steps**:
1. Open `test_data/sample_catalog.json`
2. Replace field names

**Files**: `test_data/sample_catalog.json`

**Parallel?**: Yes.

### Subtask T047 - Update sample_data.json

**Steps**:
1. Open `test_data/sample_data.json`
2. Replace field names

**Files**: `test_data/sample_data.json`

**Parallel?**: Yes.

### Subtask T048 - Update test_data/README.md

**Steps**:
1. Open `test_data/README.md`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace with new field names

**Files**: `test_data/README.md`

**Parallel?**: Yes.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missed JSON files cause import failures | Run grep verification after updates |
| Spec version inconsistency | Verify header and footer versions match |

## Definition of Done Checklist

- [ ] Import/export spec bumped to v3.4 with changelog
- [ ] All sample JSON files updated
- [ ] `grep -rn "purchase_unit\|purchase_quantity" docs/ examples/ test_data/` returns zero matches (excluding archive)
- [ ] JSON files are valid (no syntax errors)
- [ ] `tasks.md` updated with status change

## Review Guidance

- Verify spec version is 3.4 in header AND footer
- Verify changelog entry is complete and accurate
- Run grep to confirm zero matches
- Validate a sample JSON file imports successfully

## Activity Log

- 2025-12-15T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-15T17:41:27Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-15T17:43:34Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-15T21:52:16Z – system – shell_pid= – lane=done – Code review approved: Docs and sample data updated to v3.4
