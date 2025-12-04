---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "v3.0 Specification Document"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "77233"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - v3.0 Specification Document

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- **Primary Objective**: Create the authoritative v3.0 import/export specification document
- **Success Criteria**:
  - v2.0 specification archived at `docs/archive/import_export_specification_v2.md`
  - v3.0 specification exists at `docs/design/import_export_specification.md`
  - All 16 exportable entities documented with JSON examples
  - Import dependency order clearly documented
  - Validation rules and error handling documented
  - Clear "v3.0 Only" notice per FR-018

## Context & Constraints

**Prerequisite Documents**:
- `kitty-specs/009-ui-import-export/spec.md` - Feature specification with requirements
- `kitty-specs/009-ui-import-export/data-model.md` - Entity definitions (PRIMARY SOURCE)
- `kitty-specs/009-ui-import-export/research.md` - Research findings

**Key Constraints**:
- v2.0 compatibility is OUT OF SCOPE - only v3.0 supported
- Specification must match actual SQLAlchemy models in `src/models/`
- Document must be usable by developers creating compatible import files

**Architecture Reference**:
- `.kittify/memory/constitution.md` - Project principles

## Subtasks & Detailed Guidance

### Subtask T001 - Archive v2.0 Specification

- **Purpose**: Preserve historical reference while making room for v3.0
- **Steps**:
  1. Create `docs/archive/` directory if it doesn't exist
  2. Move `docs/design/import_export_specification.md` to `docs/archive/import_export_specification_v2.md`
  3. Add header note: "ARCHIVED - Superseded by v3.0 specification"
- **Files**:
  - Source: `docs/design/import_export_specification.md`
  - Destination: `docs/archive/import_export_specification_v2.md`
- **Notes**: Check if source file exists first; it may be at `docs/import_export_specification.md`

### Subtask T002 - Create v3.0 Specification Document

- **Purpose**: Establish the authoritative format definition
- **Steps**:
  1. Create new file at `docs/design/import_export_specification.md`
  2. Add document header with version, date, changelog from v2.0
  3. Add clear notice: "This specification supports v3.0 format only. Files with other versions will be rejected."
  4. Structure sections: Overview, JSON Structure, Entity Definitions, Import Order, Validation, Examples
- **Files**: `docs/design/import_export_specification.md`
- **Notes**: Follow structure from `data-model.md` but expand with implementation details

### Subtask T003 - Document All 16 Exportable Entities with JSON Examples

- **Purpose**: Provide clear reference for each entity's JSON structure
- **Steps**:
  1. For each entity in dependency order, document:
     - Entity name and purpose
     - JSON field definitions with types
     - Required vs optional fields
     - Complete JSON example
     - Foreign key references
  2. Entities to document (in order):
     1. unit_conversions
     2. ingredients
     3. variants
     4. purchases
     5. pantry_items
     6. recipes (with embedded recipe_ingredients)
     7. finished_units
     8. finished_goods
     9. compositions
     10. packages
     11. package_finished_goods
     12. recipients
     13. events
     14. event_recipient_packages
     15. production_records
- **Files**: `docs/design/import_export_specification.md`
- **Notes**: Use `data-model.md` as source; verify field names against `src/models/` if uncertain

### Subtask T004 - Document Import Dependency Order

- **Purpose**: Ensure importers understand referential integrity requirements
- **Steps**:
  1. Create dedicated section: "Import Dependency Order"
  2. List entities in required import sequence
  3. Explain why order matters (foreign key constraints)
  4. Add dependency diagram or table showing relationships
- **Files**: `docs/design/import_export_specification.md`
- **Notes**: Order from `data-model.md` line 412-430 is authoritative

### Subtask T005 - Document Validation Rules and Error Handling

- **Purpose**: Enable implementers to validate files before import
- **Steps**:
  1. Document required fields per entity
  2. Document field format requirements (dates, slugs, enums)
  3. Document foreign key validation rules
  4. Document error response format
  5. Add section on version detection and rejection
- **Files**: `docs/design/import_export_specification.md`
- **Notes**: Error messages should be user-friendly per SC-006

## Test Strategy

- **Manual Verification**:
  - Review specification against `src/models/` to verify field names
  - Validate JSON examples are syntactically correct
  - Verify dependency order matches model relationships

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Entity definitions drift from models | Cross-reference with `src/models/__init__.py` exports |
| Missing new fields from Feature 008 | Explicitly verify ProductionRecord and PackageStatus |
| Spec becomes outdated | Add "last validated" date and version |

## Definition of Done Checklist

- [ ] v2.0 spec archived at `docs/archive/import_export_specification_v2.md`
- [ ] v3.0 spec created at `docs/design/import_export_specification.md`
- [ ] All 16 entities documented with JSON examples
- [ ] Import dependency order section complete
- [ ] Validation rules documented
- [ ] "v3.0 Only" notice prominently displayed
- [ ] JSON examples validated for syntax
- [ ] Field names verified against actual models

## Review Guidance

- Verify JSON examples match actual model field names
- Check that dependency order is correct for foreign keys
- Ensure validation rules are complete and actionable
- Confirm user-friendly error message examples

## Activity Log

- 2025-12-04T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-04T19:21:16Z – claude – shell_pid=77233 – lane=doing – Started implementation
