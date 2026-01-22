---
work_package_id: "WP05"
subtasks:
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
title: "Event Service Progress Operations"
phase: "Phase 1 - Service Hardening"
lane: "for_review"
assignee: ""
agent: "codex"
shell_pid: "65344"
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

# Work Package Prompt: WP05 – Event Service Progress Operations

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` field above.

---

## Review Feedback

*[Empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP05 --base WP01
```

**Dependency**: Requires WP01 (ui_session infrastructure).

---

## Objectives & Success Criteria

Add required `session` parameter to progress tracking functions with **proper session threading** to sub-calls.

**Functions to update** (2 main + threading):
1. `get_event_overall_progress`
2. `get_events_with_progress`

**Critical Issue**: `get_events_with_progress` currently calls progress functions OUTSIDE the session (line 2261-2267). This must be fixed to thread the session through.

**Success Criteria**:
- [ ] Both functions require `session` parameter
- [ ] `get_events_with_progress` threads session to ALL sub-calls
- [ ] Progress queries see consistent data within a transaction
- [ ] Tests pass with transaction consistency verification

---

## Context & Constraints

**Service file**: `src/services/event_service.py`

**Current Bug** (from research.md):
```python
# Current code (lines 2261-2267):
# Now fetch progress for each event (outside session)
# Each progress function manages its own session per CLAUDE.md pattern
for event_data in results:
    event_id = event_data["event_id"]
    event_data["production_progress"] = get_production_progress(event_id)
    event_data["assembly_progress"] = get_assembly_progress(event_id)
    event_data["overall_progress"] = get_event_overall_progress(event_id)
```

This creates separate transactions for each call - potential for inconsistent reads!

**Note**: `get_production_progress` and `get_assembly_progress` already accept `session=None`. We need to make session required and pass it.

---

## Subtasks & Detailed Guidance

### Subtask T021 – Add session to get_event_overall_progress

**Location**: Line ~2113

**Steps**:
```python
def get_event_overall_progress(event_id: int, session: Session) -> Dict[str, Any]:
```

1. Add `session: Session` parameter
2. Remove `with session_scope() as session:` wrapper
3. Pass session to any internal calls

**Files**: `src/services/event_service.py`

---

### Subtask T022 – Add session to get_events_with_progress

**Location**: Line ~2203

**Steps**:
```python
def get_events_with_progress(
    filter_type: str = "active_future",
    date_from: date = None,
    date_to: date = None,
    session: Session,  # ADD - required
) -> List[Dict[str, Any]]:
```

**Files**: `src/services/event_service.py`

---

### Subtask T023 – Thread session to progress sub-calls

**This is the critical fix!**

**Current broken code** (line 2261-2267):
```python
# After session closes, calls progress functions with their own sessions
for event_data in results:
    event_id = event_data["event_id"]
    event_data["production_progress"] = get_production_progress(event_id)
    event_data["assembly_progress"] = get_assembly_progress(event_id)
    event_data["overall_progress"] = get_event_overall_progress(event_id)
```

**Fixed code**:
```python
def get_events_with_progress(
    filter_type: str = "active_future",
    date_from: date = None,
    date_to: date = None,
    session: Session,
) -> List[Dict[str, Any]]:
    try:
        # Use provided session directly - no internal session_scope()
        today = date.today()
        query = session.query(Event)
        # ... filters ...
        events = query.all()

        # Build results INCLUDING progress - all in same session
        results = []
        for event in events:
            event_data = {
                "event_id": event.id,
                "event_name": event.name,
                "event_date": event.event_date,
                # Thread session to progress functions:
                "production_progress": get_production_progress(event.id, session=session),
                "assembly_progress": get_assembly_progress(event.id, session=session),
                "overall_progress": get_event_overall_progress(event.id, session=session),
            }
            results.append(event_data)

        return results
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get events with progress: {str(e)}")
```

**Note**: `get_production_progress` and `get_assembly_progress` already accept session. After WP05, they will require it.

**Files**: `src/services/event_service.py`

---

### Subtask T024 – Update UI callers

**Find callers**:
```bash
grep -r "get_events_with_progress\|get_event_overall_progress" src/ui/ --include="*.py"
```

**Likely callers**:
- Planning dashboards
- Event list views with progress indicators
- Reports/status views

**Steps**:
1. Add `from src.ui.utils import ui_session`
2. Wrap calls in `with ui_session() as session:`

**Files**: UI files found by grep

---

### Subtask T025 – Add transaction consistency test

**Purpose**: Verify that progress queries see consistent data when called within a transaction.

**Test approach**:
```python
def test_get_events_with_progress_session_consistency():
    """Progress queries should see uncommitted data within same session."""
    with session_scope() as session:
        # Create event
        event = Event(name="Test", event_date=date.today())
        session.add(event)
        session.flush()  # Gets ID but doesn't commit

        # Set a target (uncommitted)
        set_production_target(event.id, recipe_id=1, target=10, session=session)

        # Query progress - should see the uncommitted target
        results = get_events_with_progress(session=session)

        # Find our event
        our_event = next(e for e in results if e["event_id"] == event.id)

        # Should have production targets
        assert len(our_event["production_progress"]) > 0

    # After rollback, nothing persisted (session_scope rolls back in test)
```

**Files**: `src/tests/test_services.py` or new `src/tests/test_event_progress.py`

---

## Test Strategy

```bash
./run-tests.sh -v -k "progress"
./run-tests.sh -v  # Full run
```

**Manual verification**:
1. Open app with multiple events
2. Check progress displays update consistently
3. No stale data visible when switching views

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Session threading missed | Inconsistent progress data | Trace ALL calls in get_events_with_progress |
| get_production_progress still optional | Breaks threading | Verify WP05 runs before or makes it required |
| Detached objects after session | AttributeError | Return dicts with primitive data, not ORM objects |

---

## Definition of Done Checklist

- [ ] `get_event_overall_progress` requires session
- [ ] `get_events_with_progress` requires session
- [ ] Session threaded to get_production_progress call
- [ ] Session threaded to get_assembly_progress call
- [ ] Session threaded to get_event_overall_progress call
- [ ] UI callers use `ui_session()`
- [ ] Transaction consistency test passes
- [ ] All tests pass

---

## Review Guidance

**Critical checks**:
1. Verify the progress sub-calls are INSIDE the session block, not after it
2. Verify session is passed to ALL three progress functions
3. Verify no `with session_scope()` remains in these functions

---

## Activity Log

- 2026-01-22T15:30:43Z – system – lane=planned – Prompt created.
- 2026-01-22T19:39:35Z – codex – shell_pid=65344 – lane=doing – Started implementation via workflow command
- 2026-01-22T20:13:34Z – codex – shell_pid=65344 – lane=for_review – Ready for review: thread session through event progress services, update UI/test callers, add consistency test; event_service_progress tests pass
