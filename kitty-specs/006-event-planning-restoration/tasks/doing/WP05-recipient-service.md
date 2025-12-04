---
work_package_id: "WP05"
subtasks:
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
title: "Recipient Service Verification"
phase: "Phase 2 - Services Layer"
lane: "doing"
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

# Work Package Prompt: WP05 - Recipient Service Verification

## Objectives & Success Criteria

- Verify existing RecipientService is functional or implement if missing
- Implement dependency checking for safe deletion
- Ensure all methods from contract are available

**Success Criteria**:
- All methods from contracts/recipient_service.md implemented
- Deletion warning works when recipient has event assignments (FR-018)
- Unit tests pass with >70% coverage

## Context & Constraints

**Background**: Recipient model is already enabled in `__init__.py`. The service may be partially or fully functional. This WP verifies and completes the implementation.

**Key Documents**:
- `kitty-specs/006-event-planning-restoration/contracts/recipient_service.md` - Full interface specification
- `kitty-specs/006-event-planning-restoration/data-model.md` - Recipient entity definition

**Dependencies**: Requires WP02 complete (Recipient model verification).

**Parallel**: Can proceed in parallel with WP04 after WP02 is complete.

## Subtasks & Detailed Guidance

### Subtask T035 - Review existing `src/services/recipient_service.py` for functionality

**Purpose**: Determine what already exists and what needs to be added.

**Steps**:
1. Check if `src/services/recipient_service.py` exists
2. If exists, review implemented methods
3. Compare against contracts/recipient_service.md
4. Document what's missing or needs updating

**Files**: `src/services/recipient_service.py`

### Subtask T036 - Verify/implement get_recipient_by_id, get_recipient_by_name, get_all_recipients

**Purpose**: Basic read operations.

**Steps**:
1. Verify or implement get_recipient_by_id
2. Verify or implement get_recipient_by_name
3. Verify or implement get_all_recipients ordered by name

**Files**: `src/services/recipient_service.py`

### Subtask T037 - Verify/implement create_recipient, update_recipient, delete_recipient

**Purpose**: CRUD operations with deletion safety.

**Steps**:
1. Verify or implement create_recipient (FR-016):
   ```python
   def create_recipient(name: str, household_name: str = None,
                        address: str = None, notes: str = None) -> Recipient:
       if not name or not name.strip():
           raise ValueError("Recipient name is required")
       recipient = Recipient(name=name, household_name=household_name,
                            address=address, notes=notes)
       session.add(recipient)
       session.commit()
       return recipient
   ```
2. Verify or implement update_recipient (FR-017)
3. Implement delete_recipient with force flag (FR-018):
   ```python
   def delete_recipient(recipient_id: int, force: bool = False) -> bool:
       if check_recipient_has_assignments(recipient_id) and not force:
           raise RecipientHasAssignmentsError(
               f"Recipient {recipient_id} has event assignments. Use force=True to delete."
           )
       # If force, cascade delete will remove assignments via relationship
       recipient = get_recipient_by_id(recipient_id)
       if not recipient:
           return False
       session.delete(recipient)
       session.commit()
       return True
   ```

**Files**: `src/services/recipient_service.py`

### Subtask T038 - Implement check_recipient_has_assignments, get_recipient_assignment_count

**Purpose**: Dependency checking for deletion dialogs.

**Steps**:
1. Implement check_recipient_has_assignments:
   ```python
   def check_recipient_has_assignments(recipient_id: int) -> bool:
       return session.query(EventRecipientPackage).filter(
           EventRecipientPackage.recipient_id == recipient_id
       ).count() > 0
   ```
2. Implement get_recipient_assignment_count:
   ```python
   def get_recipient_assignment_count(recipient_id: int) -> int:
       return session.query(EventRecipientPackage).filter(
           EventRecipientPackage.recipient_id == recipient_id
       ).count()
   ```

**Files**: `src/services/recipient_service.py`

### Subtask T039 - Implement get_recipient_events

**Purpose**: Find all events where recipient has assignments.

**Steps**:
1. Implement get_recipient_events:
   ```python
   def get_recipient_events(recipient_id: int) -> List[Event]:
       return session.query(Event).join(EventRecipientPackage).filter(
           EventRecipientPackage.recipient_id == recipient_id
       ).distinct().all()
   ```

**Files**: `src/services/recipient_service.py`

### Subtask T040 - Implement search_recipients, get_recipients_by_household

**Purpose**: Query operations for finding recipients.

**Steps**:
1. Implement search_recipients:
   ```python
   def search_recipients(query: str) -> List[Recipient]:
       return session.query(Recipient).filter(
           (Recipient.name.ilike(f"%{query}%")) |
           (Recipient.household_name.ilike(f"%{query}%"))
       ).all()
   ```
2. Implement get_recipients_by_household:
   ```python
   def get_recipients_by_household(household_name: str) -> List[Recipient]:
       return session.query(Recipient).filter(
           Recipient.household_name == household_name
       ).all()
   ```

**Files**: `src/services/recipient_service.py`

### Subtask T041 - Write unit tests in `src/tests/test_recipient_service.py`

**Purpose**: Achieve >70% coverage per constitution.

**Steps**:
1. Create or update `src/tests/test_recipient_service.py`
2. Write tests for:
   - CRUD operations
   - Search functionality
   - Dependency checking (has assignments)
   - Delete with force flag
3. Use pytest fixtures for test data

**Files**: `src/tests/test_recipient_service.py`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Service doesn't exist | Create from scratch following contract |
| Missing EventRecipientPackage relationship | Import from models |

## Definition of Done Checklist

- [ ] All methods from contract verified or implemented
- [ ] Deletion warning works with assignments
- [ ] Force delete cascades assignments
- [ ] Search functionality works
- [ ] Unit tests pass with >70% coverage
- [ ] `tasks.md` updated with status change

## Review Guidance

- Verify deletion warning is triggered correctly
- Check force delete actually removes assignments
- Test search with household names

## Activity Log

- 2025-12-03 - system - lane=planned - Prompt created.
- 2025-12-04T02:38:59Z – claude – shell_pid=9077 – lane=doing – Started verification
