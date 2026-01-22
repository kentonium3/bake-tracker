---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Event Service CRUD Operations"
phase: "Phase 1 - Service Hardening"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "75488"
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-22T15:30:43Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Event Service CRUD Operations

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

**Dependency**: Requires WP01 (ui_session infrastructure) to be complete.

---

## Objectives & Success Criteria

Add required `session` parameter to all event CRUD functions in `event_service.py` and update their UI callers to use `ui_session()`.

**Functions to update** (8 total):
1. `create_event`
2. `get_event_by_id`
3. `get_event_by_name`
4. `get_all_events`
5. `get_events_by_year`
6. `get_available_years`
7. `update_event`
8. `delete_event`

**Success Criteria**:
- [ ] All 8 functions require `session` parameter (not optional)
- [ ] No internal `session_scope()` calls in these functions
- [ ] All UI callers wrap calls in `with ui_session() as session:`
- [ ] All existing tests pass with updated function signatures
- [ ] Transaction rollback works correctly on error

---

## Context & Constraints

**References**:
- Service file: `src/services/event_service.py`
- Plan: `kitty-specs/062-service-session-consistency-hardening/plan.md`
- Research: `kitty-specs/062-service-session-consistency-hardening/research.md`

**Key Pattern Change**:

**Before** (current):
```python
def create_event(name: str, event_date: date, ...) -> Event:
    with session_scope() as session:
        # ... implementation
```

**After** (required):
```python
def create_event(name: str, event_date: date, ..., session: Session) -> Event:
    # Use session directly - no internal session_scope()
    # ... implementation
```

**Type Import**:
```python
from sqlalchemy.orm import Session
```

---

## Subtasks & Detailed Guidance

### Subtask T005 – Add required `session` param to first 4 CRUD functions

**Purpose**: Update `create_event`, `get_event_by_id`, `get_event_by_name`, `get_all_events`.

**Steps**:
1. Open `src/services/event_service.py`
2. Add `session: Session` as LAST parameter (after all other params)
3. Add import: `from sqlalchemy.orm import Session` (if not present)

**Changes for each function**:

```python
# create_event (around line 144)
def create_event(
    name: str,
    event_date: date,
    description: Optional[str] = None,
    notes: Optional[str] = None,
    session: Session,  # ADD - required, no default
) -> Event:

# get_event_by_id (around line 202)
def get_event_by_id(event_id: int, session: Session) -> Optional[Event]:

# get_event_by_name (around line 233)
def get_event_by_name(name: str, session: Session) -> Optional[Event]:

# get_all_events (around line 257)
def get_all_events(session: Session) -> List[Event]:
```

**Files**:
- `src/services/event_service.py`

**Parallel?**: Yes - can work on T005 and T006 together.

---

### Subtask T006 – Add required `session` param to remaining 4 CRUD functions

**Purpose**: Update `get_events_by_year`, `get_available_years`, `update_event`, `delete_event`.

**Steps**:
1. Continue in `src/services/event_service.py`
2. Add `session: Session` as parameter

**Changes for each function**:

```python
# get_events_by_year (around line 278)
def get_events_by_year(year: int, session: Session) -> List[Event]:

# get_available_years (around line 303)
def get_available_years(session: Session) -> List[int]:

# update_event (around line 319)
def update_event(event_id: int, session: Session, **updates) -> Event:
# Note: session should come before **updates

# delete_event (around line 374)
def delete_event(event_id: int, cascade_assignments: bool = False, session: Session) -> bool:
# Note: session should come after named params, before return
```

**Files**:
- `src/services/event_service.py`

**Parallel?**: Yes - can work alongside T005.

---

### Subtask T007 – Remove internal `session_scope()` from all CRUD functions

**Purpose**: Use the provided session directly instead of creating new sessions.

**Steps**:
1. For each function updated in T005/T006:
   - Remove the `with session_scope() as session:` wrapper
   - Unindent the code that was inside the with block
   - Use `session` parameter directly

**Example transformation**:

**Before**:
```python
def create_event(name: str, event_date: date, ...):
    try:
        with session_scope() as session:
            event = Event(
                name=name,
                event_date=event_date,
                ...
            )
            session.add(event)
            session.flush()
            return event
    except SQLAlchemyError as e:
        raise DatabaseError(...)
```

**After**:
```python
def create_event(name: str, event_date: date, ..., session: Session):
    try:
        event = Event(
            name=name,
            event_date=event_date,
            ...
        )
        session.add(event)
        session.flush()
        return event
    except SQLAlchemyError as e:
        raise DatabaseError(...)
```

**Important**: Keep `session.flush()` calls - they write to DB within transaction.
**Important**: Do NOT add `session.commit()` - caller owns commit/rollback.

**Files**:
- `src/services/event_service.py`

**Parallel?**: Must follow T005/T006.

---

### Subtask T008 – Update UI callers in events_tab.py and event_form.py

**Purpose**: Wrap service calls in `ui_session()` context manager.

**Steps**:
1. Open `src/ui/events_tab.py`
2. Add import: `from src.ui.utils import ui_session`
3. Find all calls to CRUD functions, wrap in session context

**Example pattern**:

**Before**:
```python
def _load_events(self):
    events = event_service.get_all_events()
    # ...
```

**After**:
```python
def _load_events(self):
    with ui_session() as session:
        events = event_service.get_all_events(session=session)
    # ... (use events outside session is OK for read-only data)
```

**For write operations**:
```python
def _save_event(self):
    with ui_session() as session:
        if self.editing_event:
            event = event_service.update_event(
                event_id=self.editing_event.id,
                session=session,
                name=name_value,
                ...
            )
        else:
            event = event_service.create_event(
                name=name_value,
                ...,
                session=session,
            )
        # Commit happens automatically on success
```

4. Repeat for `src/ui/forms/event_form.py`

**Files**:
- `src/ui/events_tab.py`
- `src/ui/forms/event_form.py`

**Parallel?**: Must follow T007.

---

### Subtask T009 – Update UI callers in event_detail_window.py and dashboards

**Purpose**: Update remaining UI callers for CRUD functions.

**Steps**:
1. Search for CRUD function calls in:
   - `src/ui/event_detail_window.py`
   - `src/ui/dashboards/plan_dashboard.py`
   - Any other files calling these functions

2. Use grep to find callers:
   ```bash
   grep -r "get_event_by_id\|get_all_events\|create_event" src/ui/ --include="*.py"
   ```

3. For each caller, add `ui_session()` wrapper

**Files** (likely):
- `src/ui/event_detail_window.py`
- `src/ui/dashboards/plan_dashboard.py`
- `src/ui/dashboards/observe_dashboard.py`
- Other files found by grep

**Parallel?**: Can run alongside T008.

---

### Subtask T010 – Update tests for event CRUD

**Purpose**: Update test files to pass session parameter.

**Steps**:
1. Open `src/tests/test_services.py`
2. Find tests for event CRUD functions
3. Update to use session fixture or `session_scope()`

**Example pattern**:
```python
from src.services.database import session_scope

def test_create_event():
    with session_scope() as session:
        event = event_service.create_event(
            name="Test Event",
            event_date=date(2026, 12, 25),
            session=session,
        )
        assert event.name == "Test Event"
```

4. Run tests to verify:
   ```bash
   ./run-tests.sh src/tests/test_services.py -v -k "event"
   ```

**Files**:
- `src/tests/test_services.py`

**Parallel?**: Must follow T007.

---

## Test Strategy

**Run tests after each subtask**:
```bash
# After T007 - expect failures (callers not updated)
./run-tests.sh src/tests/test_services.py -v -k "event" --tb=short

# After T010 - all should pass
./run-tests.sh -v
```

**Manual verification**:
1. Start the application: `python src/main.py`
2. Navigate to Events tab
3. Create a new event - should succeed
4. Edit an event - should succeed
5. Delete an event - should succeed

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missed caller | Medium | High | Use grep to find ALL callers before starting |
| Detached object after session close | Medium | Medium | Return primitive data or IDs, not ORM objects |
| Test database pollution | Low | Medium | Tests use rollback after each test |

---

## Definition of Done Checklist

- [ ] All 8 CRUD functions have required `session` parameter
- [ ] No `session_scope()` inside CRUD functions
- [ ] Type hint `session: Session` on all functions
- [ ] `src/ui/events_tab.py` uses `ui_session()`
- [ ] `src/ui/forms/event_form.py` uses `ui_session()`
- [ ] `src/ui/event_detail_window.py` uses `ui_session()`
- [ ] Dashboard files updated
- [ ] Tests updated and passing
- [ ] App manually tested - CRUD operations work

---

## Review Guidance

**Reviewers should verify**:
1. All 8 functions listed have `session: Session` parameter
2. No `with session_scope()` remains in these functions
3. All callers found by grep have been updated
4. Tests pass: `./run-tests.sh -v`
5. No `session.commit()` added in service functions

---

## Activity Log

- 2026-01-22T15:30:43Z – system – lane=planned – Prompt created.
- 2026-01-22T16:03:47Z – claude-opus – shell_pid=75488 – lane=doing – Started implementation via workflow command
