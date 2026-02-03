---
work_package_id: WP03
title: Event & Package Service Updates
lane: "done"
dependencies: [WP01]
base_branch: 094-core-api-standardization-WP01
base_commit: 4f0333494559e2a44d97431f1ae745eda905680c
created_at: '2026-02-03T16:30:03.623113+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
phase: Phase 2 - Core Services
assignee: ''
agent: "codex"
shell_pid: "51956"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-03T16:10:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 - Event & Package Service Updates

## Objectives & Success Criteria

- Update `event_service.py` get functions to raise exceptions
- Update `package_service.py` get functions to raise exceptions
- Update all calling code to handle exceptions
- Update tests to expect exceptions

## Context & Constraints

- **Depends on WP01**: Exception types must be available
- Reference: `src/services/event_service.py` - heavily used service
- Reference: `src/services/package_service.py`
- Event service is used extensively in UI - test thoroughly

## Subtasks & Detailed Guidance

### Subtask T014 - Update get_event_by_id() to raise exception

**Purpose**: Convert from Optional return to exception-based error handling.

**Current Pattern** (src/services/event_service.py:616):
```python
def get_event_by_id(event_id: int, *, session: Session) -> Optional[Event]:
```

**Target Pattern**:
```python
def get_event_by_id(event_id: int, *, session: Session) -> Event:
    """
    Get event by ID.

    Raises:
        EventNotFoundById: If event doesn't exist
    """
```

**Steps**:
1. Import `EventNotFoundById` from exceptions
2. Change return type from `Optional[Event]` to `Event`
3. After query, check if result is None and raise exception
4. Update docstring

**Files**: `src/services/event_service.py`

### Subtask T015 - Update get_event_by_name() to raise exception

**Purpose**: Convert from Optional return to exception-based error handling.

**Current Pattern** (src/services/event_service.py:650):
```python
def get_event_by_name(name: str, *, session: Session) -> Optional[Event]:
```

**Steps**:
1. Import `EventNotFoundByName` from exceptions
2. Change return type
3. Raise exception if not found

**Files**: `src/services/event_service.py`

### Subtask T016 - Update get_package_by_id() to raise exception

**Purpose**: Convert from Optional return to exception-based error handling.

**Current Pattern** (src/services/package_service.py:222):
```python
def get_package_by_id(package_id: int) -> Optional[Package]:
```

**Steps**:
1. Import `PackageNotFoundById` from exceptions
2. Change return type
3. Raise exception if not found

**Files**: `src/services/package_service.py`

### Subtask T017 - Update get_package_by_name() to raise exception

**Purpose**: Convert from Optional return to exception-based error handling.

**Current Pattern** (src/services/package_service.py:250):
```python
def get_package_by_name(name: str) -> Optional[Package]:
```

**Steps**:
1. Import `PackageNotFoundByName` from exceptions
2. Change return type
3. Raise exception if not found

**Files**: `src/services/package_service.py`

### Subtask T018 - Update calling code for event/package functions

**Purpose**: All code that calls these functions must handle exceptions.

**Steps**:
1. Find all call sites:
   ```bash
   grep -r "get_event_by_id" src/
   grep -r "get_event_by_name" src/
   grep -r "get_package_by_id" src/
   grep -r "get_package_by_name" src/
   ```
2. For each call site, wrap in try/except

**Key files to check**:
- `src/ui/` - Event and package dialogs
- `src/services/` - Cross-service calls
- Planning services that reference events

**Files**: Multiple files

### Subtask T019 - Update event and package tests

**Purpose**: Tests should expect exceptions for not-found cases.

**Steps**:
1. Find tests for event_service and package_service
2. Update tests checking for None to use `pytest.raises`

**Files**:
- `src/tests/services/test_event_service.py`
- `src/tests/services/test_package_service.py`

## Test Strategy

Run affected tests:
```bash
./run-tests.sh src/tests/services/test_event_service.py -v
./run-tests.sh src/tests/services/test_package_service.py -v
```

Full regression:
```bash
./run-tests.sh -v
```

## Risks & Mitigations

- **Event service is critical**: Test all UI flows involving events
- **Many call sites**: Be thorough with grep search
- **Planning integration**: Verify planning workflows still work

## Definition of Done Checklist

- [ ] `get_event_by_id()` raises `EventNotFoundById`
- [ ] `get_event_by_name()` raises `EventNotFoundByName`
- [ ] `get_package_by_id()` raises `PackageNotFoundById`
- [ ] `get_package_by_name()` raises `PackageNotFoundByName`
- [ ] Return types updated (no Optional)
- [ ] All calling code updated
- [ ] Tests updated
- [ ] All tests pass

## Review Guidance

- Verify event UI flows work correctly
- Check planning features that use events
- Ensure package assignment workflows work

## Activity Log

- 2026-02-03T16:10:45Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
- 2026-02-03T16:36:17Z – unknown – shell_pid=3112 – lane=for_review – Event and package service exception handling complete. All 4 get functions now raise domain-specific exceptions. Tests updated.
- 2026-02-03T22:21:42Z – codex – shell_pid=51956 – lane=doing – Started review via workflow command
- 2026-02-03T22:23:22Z – codex – shell_pid=51956 – lane=done – Review passed: event/package lookups raise EventNotFoundBy*/PackageNotFoundBy*; tests updated; targeted test passes
