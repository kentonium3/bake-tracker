---
work_package_id: "WP07"
subtasks:
  - "T037"
  - "T038"
  - "T039"
  - "T040"
title: "Assembly Enforcement"
phase: "Phase 7 - Assembly Flow"
lane: "planned"
assignee: ""
agent: ""
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

# Work Package Prompt: WP07 - Assembly Enforcement

## Objectives & Success Criteria

- Check for unassigned packaging at assembly completion
- Create prompt dialog with three options (Quick Assign, Details, Bypass)
- Flag event for reconciliation when bypass used
- Add visual indicator for bypassed assemblies
- Workflow is smooth, not blocking

## Context & Constraints

**References**:
- `kitty-specs/026-deferred-packaging-decisions/plan.md` - Phase 7 details
- `kitty-specs/026-deferred-packaging-decisions/spec.md` - User Story 5
- Existing assembly completion flow

**Constraints**:
- Must not block workflow unnecessarily
- Bypass option always available
- Clear consequences for bypass

## Subtasks & Detailed Guidance

### Subtask T037 - Add assembly completion check

- **Purpose**: Detect unassigned packaging before completing assembly
- **Steps**:
  1. Locate assembly completion flow in UI
  2. Before final confirmation, call `packaging_service.get_pending_requirements()`
  3. Filter to pending requirements for current assembly
  4. If pending exists, trigger prompt dialog
  5. If no pending, proceed with normal completion
- **Files**: `src/ui/assembly_screen.py` or equivalent
- **Parallel?**: No
- **Notes**: Check should be fast; cache if needed

### Subtask T038 - Create prompt dialog

- **Purpose**: Give user options when packaging is unassigned
- **Steps**:
  1. Create dialog (modal) with three buttons:
     - "Quick Assign" - opens PackagingAssignmentDialog
     - "Assembly Details" - navigates to full assembly screen
     - "Record Assembly Anyway" - proceeds with bypass
  2. Dialog header: "Unassigned Packaging"
  3. Body: List pending packaging requirements
  4. Clear explanation of consequences for each option
- **Files**: `src/ui/assembly_screen.py` or new dialog file
- **Parallel?**: No
- **Notes**:
  - "Quick Assign" returns to completion flow after assignment
  - "Details" exits completion flow entirely
  - "Bypass" continues with warning

### Subtask T039 - Flag event for reconciliation

- **Purpose**: Track bypassed assemblies for later attention
- **Steps**:
  1. When "Record Assembly Anyway" selected:
     - Set bypass flag on AssemblyRun (or related model)
     - Record timestamp and reason
  2. Create or update reconciliation tracking
  3. Show confirmation: "Assembly recorded. Packaging needs reconciliation."
- **Files**: `src/services/assembly_service.py`, `src/ui/assembly_screen.py`
- **Parallel?**: No
- **Notes**:
  - May need model change if bypass field doesn't exist
  - Reconciliation list shows all bypassed items

### Subtask T040 - Add bypassed assembly indicator

- **Purpose**: Visual cue for assemblies needing reconciliation
- **Steps**:
  1. Query assemblies with bypass flag set
  2. Add indicator icon to assembly list/dashboard
  3. Different styling from pending indicator (maybe yellow vs orange)
  4. Tooltip: "Packaging recorded without assignment"
  5. Click navigates to assignment dialog
- **Files**: `src/ui/dashboard.py` or assembly list
- **Parallel?**: No
- **Notes**: Consider combining with pending indicator logic

## Test Strategy

Manual testing checklist:
1. Create assembly with unassigned generic packaging
2. Try to complete assembly
3. Verify prompt dialog appears with all three options
4. Test "Quick Assign" - complete assignment, verify completion resumes
5. Test "Assembly Details" - verify navigation works
6. Test "Record Anyway" - verify bypass recorded
7. Verify bypassed assembly shows indicator
8. Click indicator - verify navigation to assignment

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Blocking workflow annoys users | Bypass always available |
| Forgotten reconciliation | Prominent indicators; consider periodic reminder |
| Dialog fatigue | Remember user's frequent choice; offer "don't ask again" option |

## Definition of Done Checklist

- [ ] Assembly completion checks for pending packaging
- [ ] Prompt dialog appears with three options
- [ ] Each option works correctly
- [ ] Bypass flag recorded on assembly
- [ ] Bypassed assemblies show indicator
- [ ] Manual testing completed

## Review Guidance

- Test all three dialog options
- Verify bypass flag persists correctly
- Check that indicator appears immediately after bypass
- Confirm reconciliation workflow is clear

## Activity Log

- 2025-12-21T12:00:00Z - system - lane=planned - Prompt created.
