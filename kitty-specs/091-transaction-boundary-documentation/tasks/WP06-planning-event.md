---
work_package_id: "WP06"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
title: "Planning & Event Services"
phase: "Phase 2 - Documentation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-02-03T04:37:19Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Planning & Event Services

## Objectives & Success Criteria

**Goal**: Add transaction boundary documentation to planning and event service files.

**Success Criteria**:
- [ ] All public functions in planning services have "Transaction boundary:" section
- [ ] All public functions in event_service.py have "Transaction boundary:" section

**Implementation Command**:
```bash
spec-kitty implement WP06 --base WP01
```

**Parallel-Safe**: Yes - assign to Codex

## Context & Constraints

**References**:
- Templates: `kitty-specs/091-transaction-boundary-documentation/research/docstring_templates.md`

**Key Constraints**:
- Planning services have complex multi-step operations
- Focus on transaction scope clarity for debugging

## Subtasks & Detailed Guidance

### Subtask T019 – Document planning/planning_service.py

**Purpose**: Add transaction boundary documentation to main planning service.

**Files**:
- Edit: `src/services/planning/planning_service.py`

**Common functions to document**:

| Function Pattern | Type | Template |
|-----------------|------|----------|
| `get_plan`, `get_current_plan` | READ | Pattern A |
| `create_plan` | MULTI | Pattern C |
| `update_plan`, `amend_plan` | MULTI | Pattern C |
| `delete_plan` | MULTI | Pattern C |
| `calculate_*` | READ | Pattern A |
| `record_*_confirmation` | MULTI | Pattern C |

**For multi-step planning operations**:
```python
def create_plan(event_id: int, targets: List[dict], session: Optional[Session] = None):
    """
    Create a new production plan for an event.

    Transaction boundary: ALL operations in single session (atomic).
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
    1. Validate event exists and is not already planned
    2. Create Plan record
    3. Create PlanTarget records for each target
    4. Calculate initial requirements
    5. Create shopping list if requested

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.

    Args:
        event_id: ID of the event to plan for
        targets: List of production targets
        session: Optional session for transactional composition

    Returns:
        Created Plan instance with targets loaded

    Raises:
        EventNotFoundError: If event doesn't exist
        PlanAlreadyExistsError: If event already has a plan
    """
```

**Validation**:
- [ ] All public functions documented

---

### Subtask T020 – Document plan_state_service.py

**Purpose**: Add transaction boundary documentation to plan state management.

**Files**:
- Edit: `src/services/plan_state_service.py`

**Typical functions**:
- State transitions are often MULTI (update plan + create history record)
- State queries are READ

**Validation**:
- [ ] All public functions documented

---

### Subtask T021 – Document plan_snapshot_service.py

**Purpose**: Add transaction boundary documentation to snapshot operations.

**Files**:
- Edit: `src/services/plan_snapshot_service.py`

**Note**: Snapshot creation is typically MULTI (creates multiple related records atomically).

**Validation**:
- [ ] All public functions documented

---

### Subtask T022 – Document event_service.py

**Purpose**: Add transaction boundary documentation to event management.

**Files**:
- Edit: `src/services/event_service.py`

**Functions to document**:

| Function | Type | Template |
|----------|------|----------|
| `create_event` | SINGLE | Pattern B |
| `get_event` | READ | Pattern A |
| `get_all_events` | READ | Pattern A |
| `update_event` | SINGLE | Pattern B |
| `delete_event` | MULTI | Pattern C (checks assignments) |
| `add_assignment` | MULTI | Pattern C |
| `remove_assignment` | MULTI | Pattern C |
| `get_event_assignments` | READ | Pattern A |

**For delete_event with dependency check**:
```python
def delete_event(event_id: int, session: Optional[Session] = None):
    """
    Delete an event if it has no assignments.

    Transaction boundary: Multi-step operation (atomic).
    Steps executed atomically:
    1. Check for existing assignments
    2. If assignments exist, raise EventHasAssignmentsError
    3. Delete event record

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.

    Args:
        event_id: ID of the event to delete
        session: Optional session for transactional composition

    Returns:
        None

    Raises:
        EventNotFoundError: If event doesn't exist
        EventHasAssignmentsError: If event has package assignments
    """
```

**Validation**:
- [ ] All public functions documented

---

### Subtask T023 – Document planning submodules

**Purpose**: Add transaction boundary documentation to planning submodules.

**Files**:
- Edit: `src/services/planning/feasibility.py`
- Edit: `src/services/planning/progress.py`
- Edit: `src/services/planning/shopping_list.py`
- Edit: `src/services/planning/batch_calculation.py`

**Common patterns**:
- Feasibility checks: READ (Pattern A)
- Progress calculations: READ (Pattern A)
- Shopping list generation: READ or MULTI depending on whether it saves

**Validation**:
- [ ] All public functions in submodules documented

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Complex planning logic | Focus on transaction scope, not business logic |
| Multiple interconnected services | Document which services share sessions |

## Definition of Done Checklist

- [ ] planning/planning_service.py: All public functions documented
- [ ] plan_state_service.py: All public functions documented
- [ ] plan_snapshot_service.py: All public functions documented
- [ ] event_service.py: All public functions documented
- [ ] Planning submodules: All public functions documented
- [ ] Tests still pass: `pytest src/tests -v -k "planning or event"`

## Review Guidance

**Reviewers should verify**:
1. Multi-step operations have step lists
2. State transitions document atomicity
3. No functional changes

## Activity Log

- 2026-02-03T04:37:19Z – system – lane=planned – Prompt created.
