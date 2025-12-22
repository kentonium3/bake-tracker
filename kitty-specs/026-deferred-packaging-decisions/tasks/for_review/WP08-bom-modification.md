---
work_package_id: "WP08"
subtasks:
  - "T041"
  - "T042"
  - "T043"
  - "T044"
title: "BOM Modification"
phase: "Phase 8 - BOM Changes"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-21T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - BOM Modification

## Objectives & Success Criteria

- Enable adding/removing packaging from assembly definition
- Clear previous assignments when requirements change
- Recalculate costs and availability after changes
- Warn if changes affect other productions
- Preserve data integrity through changes

## Context & Constraints

**References**:
- `kitty-specs/026-deferred-packaging-decisions/plan.md` - Phase 8 details
- `kitty-specs/026-deferred-packaging-decisions/spec.md` - User Story 6
- `kitty-specs/026-deferred-packaging-decisions/data-model.md` - Relationships

**Constraints**:
- Must handle cascading changes safely
- User confirmation before destructive changes
- Maintain referential integrity
- Clear feedback about impacts

## Subtasks & Detailed Guidance

### Subtask T041 - Enable packaging add/remove

- **Purpose**: Allow modifying packaging requirements after initial planning
- **Steps**:
  1. Locate assembly definition editor UI
  2. Add ability to add new packaging compositions
  3. Add ability to remove existing packaging compositions
  4. Handle both generic and specific packaging
  5. Update UI to reflect changes immediately
- **Files**: `src/ui/assembly_definition.py` or equivalent
- **Parallel?**: No
- **Notes**:
  - Existing pattern: RecipeComponent editing
  - Consider inline editing vs dialog

### Subtask T042 - Clear assignments on requirement change

- **Purpose**: Invalidate assignments when requirement changes
- **Steps**:
  1. When composition quantity changes:
     - If has assignments, prompt for confirmation
     - Clear existing CompositionAssignment records
     - Reset assignment status
  2. When composition is removed:
     - Cascade delete assignments (per FK constraint)
  3. When product_name changes on generic:
     - Clear assignments (new product type)
- **Files**: `src/services/composition_service.py`, `src/ui/`
- **Parallel?**: No
- **Notes**:
  - Confirmation dialog: "This will clear existing material assignments. Continue?"
  - Activity log records the clearing

### Subtask T043 - Recalculate costs after changes

- **Purpose**: Keep cost display accurate after modifications
- **Steps**:
  1. After any packaging change:
     - Recalculate estimated costs for generic compositions
     - Recalculate actual costs for assigned compositions
     - Update total assembly cost
  2. Refresh cost displays in UI
- **Files**: `src/services/`, `src/ui/`
- **Parallel?**: No
- **Notes**: Consider debouncing for rapid changes

### Subtask T044 - Warn about cross-production impact

- **Purpose**: Alert user if changes affect related data
- **Steps**:
  1. When modifying packaging for an assembly:
     - Check if assembly is used in multiple events
     - Check if assembly has pending/completed runs
  2. If impacts exist, show warning dialog:
     - "This assembly is used in 3 events. Changes will affect all."
     - List affected events/productions
  3. Allow cancel or proceed
- **Files**: `src/services/`, `src/ui/`
- **Parallel?**: No
- **Notes**:
  - Query EventProductionTarget/EventAssemblyTarget for usage
  - Warning is informational, not blocking

## Test Strategy

Manual testing checklist:
1. Open assembly definition with assigned packaging
2. Change quantity - verify assignment clear prompt
3. Confirm clear - verify assignments removed
4. Verify costs recalculated
5. Add new packaging component
6. Remove packaging component
7. Verify cross-production warning appears when applicable

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Losing assignment data unexpectedly | Confirmation dialog before clearing |
| Cross-production confusion | Clear warning with affected list |
| State management complexity | Transactional updates; clear refresh patterns |

## Definition of Done Checklist

- [ ] Can add packaging to assembly definition
- [ ] Can remove packaging from assembly definition
- [ ] Assignments cleared with confirmation on change
- [ ] Costs recalculate correctly after changes
- [ ] Cross-production warning shows when applicable
- [ ] Manual testing completed

## Review Guidance

- Test with both generic and specific packaging
- Verify confirmation dialogs are clear
- Check that costs update immediately
- Confirm cross-production warning is accurate

## Activity Log

- 2025-12-21T12:00:00Z - system - lane=planned - Prompt created.
- 2025-12-21T22:39:12Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-21T22:41:26Z – system – shell_pid= – lane=for_review – Moved to for_review
