---
work_package_id: "WP07"
subtasks:
  - "T049"
  - "T050"
  - "T051"
  - "T052"
  - "T053"
title: "UI - Recipients Tab"
phase: "Phase 3 - UI Layer"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "9077"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-03"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - UI - Recipients Tab

## Objectives & Success Criteria

- Verify/update Recipients tab for managing gift recipients
- Implement deletion with assignment warning confirmation

**Success Criteria**:
- User can create, edit, delete recipients
- Deletion shows warning if recipient has event assignments
- Search functionality works

## Context & Constraints

**Background**: Recipient UI may already be functional since Recipient model was never disabled. This WP verifies and updates as needed.

**Key Documents**:
- `kitty-specs/006-event-planning-restoration/spec.md` - User Story 3 acceptance scenarios
- `kitty-specs/006-event-planning-restoration/contracts/recipient_service.md` - Service interface

**Dependencies**: Requires WP05 complete (RecipientService).

## Subtasks & Detailed Guidance

### Subtask T049 - Review existing `src/ui/recipients_tab.py` for functionality

**Purpose**: Determine what already works and what needs updating.

**Steps**:
1. Check if `src/ui/recipients_tab.py` exists
2. If exists, verify:
   - CRUD operations work
   - List displays correctly
   - Service calls are correct
3. Identify any missing functionality from User Story 3

**Files**: `src/ui/recipients_tab.py`

### Subtask T050 - Verify/update RecipientsTab frame with recipient list view

**Purpose**: Main tab showing all recipients.

**Steps**:
1. Verify list displays: name, household_name
2. Add "Add Recipient" button if missing
3. Double-click to edit
4. Verify or implement using RecipientService.get_all_recipients()

**Files**: `src/ui/recipients_tab.py`

### Subtask T051 - Verify/update Add Recipient dialog with name, household, address, notes

**Purpose**: Dialog for creating/editing recipients.

**Steps**:
1. Verify dialog has all fields:
   - Name (required)
   - Household name (optional)
   - Address (optional, text area)
   - Notes (optional, text area)
2. Verify save calls RecipientService.create_recipient() or update_recipient()
3. Fix any issues found

**Files**: `src/ui/recipients_tab.py`

### Subtask T052 - Implement deletion with assignment warning confirmation

**Purpose**: Safe deletion per FR-018.

**Steps**:
1. On delete button click:
   ```python
   def on_delete_click(self, recipient_id):
       if RecipientService.check_recipient_has_assignments(recipient_id):
           count = RecipientService.get_recipient_assignment_count(recipient_id)
           if not show_confirmation(f"Recipient has {count} event assignments. Delete anyway?"):
               return
           RecipientService.delete_recipient(recipient_id, force=True)
       else:
           RecipientService.delete_recipient(recipient_id)
       self.load_recipients()
   ```
2. Show appropriate confirmation dialog

**Files**: `src/ui/recipients_tab.py`

### Subtask T053 - Add search functionality for recipients

**Purpose**: Allow filtering recipient list.

**Steps**:
1. Add search entry if missing
2. Filter by name and household_name
3. Use RecipientService.search_recipients() or filter locally

**Files**: `src/ui/recipients_tab.py`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI may already be complete | Verify thoroughly, update only as needed |

## Definition of Done Checklist

- [ ] Recipient list displays correctly
- [ ] Add/Edit/Delete operations work
- [ ] Deletion warning shows for assigned recipients
- [ ] Force delete removes assignments
- [ ] Search filters list
- [ ] User Story 3 acceptance scenarios pass
- [ ] `tasks.md` updated with status change

## Review Guidance

- Verify deletion warning is accurate
- Test force delete cascades correctly
- Check search covers both name and household

## Activity Log

- 2025-12-03 - system - lane=planned - Prompt created.
- 2025-12-04T02:52:08Z – claude – shell_pid=9077 – lane=for_review – Completed: RecipientsTab imports verified, no Bundle references
