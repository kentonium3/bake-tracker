---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Event Service Assignment Operations"
phase: "Phase 1 - Service Hardening"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "14709"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-22T15:30:43Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Event Service Assignment Operations

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` field above.

---

## Review Feedback

*[Empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

**Dependency**: Requires WP01 (ui_session infrastructure).

---

## Objectives & Success Criteria

Add required `session` parameter to event assignment functions and update callers.

**Functions to update** (5 total):
1. `assign_package_to_recipient`
2. `update_assignment`
3. `remove_assignment`
4. `get_event_assignments`
5. `get_recipient_assignments_for_event`

**Success Criteria**:
- [ ] All 5 functions require `session` parameter
- [ ] No internal `session_scope()` in these functions
- [ ] UI callers use `ui_session()`
- [ ] Tests pass

---

## Context & Constraints

**Service file**: `src/services/event_service.py`
**Primary UI callers**: `src/ui/forms/assignment_form.py`, `src/ui/packaging_assignment_dialog.py`

**Pattern**: Same as WP02 - add `session: Session`, remove internal `session_scope()`.

---

## Subtasks & Detailed Guidance

### Subtask T011 – Add session to assign/update/remove functions

**Functions** (approx line numbers from research.md):
- `assign_package_to_recipient` (line ~420)
- `update_assignment` (line ~493)
- `remove_assignment` (line ~561)

**Steps**:
1. Add `session: Session` parameter to each function
2. Place session as last positional parameter (before keyword-only args)

**Example**:
```python
def assign_package_to_recipient(
    event_id: int,
    recipient_id: int,
    package_id: int,
    quantity: int = 1,
    notes: Optional[str] = None,
    session: Session,  # Required, no default
) -> EventRecipientPackage:
```

**Files**: `src/services/event_service.py`

---

### Subtask T012 – Add session to query functions

**Functions**:
- `get_event_assignments` (line ~594)
- `get_recipient_assignments_for_event` (line ~624)

**Steps**:
1. Add `session: Session` parameter

```python
def get_event_assignments(event_id: int, session: Session) -> List[EventRecipientPackage]:

def get_recipient_assignments_for_event(
    event_id: int,
    recipient_id: int,
    session: Session,
) -> List[EventRecipientPackage]:
```

**Files**: `src/services/event_service.py`

---

### Subtask T013 – Remove internal session_scope

**Steps**:
1. For each function in T011/T012, remove `with session_scope() as session:`
2. Unindent code block
3. Use `session` parameter directly
4. Keep `session.flush()` for write operations
5. Do NOT add `session.commit()`

**Files**: `src/services/event_service.py`

---

### Subtask T014 – Update UI callers

**Files to update**:
- `src/ui/forms/assignment_form.py`
- `src/ui/packaging_assignment_dialog.py`

**Steps**:
1. Add import: `from src.ui.utils import ui_session`
2. Wrap service calls in `with ui_session() as session:`
3. Pass `session=session` to all service calls

**Find callers**:
```bash
grep -r "assign_package_to_recipient\|get_event_assignments" src/ui/ --include="*.py"
```

**Files**: UI files found by grep

---

### Subtask T015 – Update tests

**Steps**:
1. Find tests for assignment functions
2. Update to pass session parameter

```bash
grep -r "assign_package_to_recipient\|get_event_assignments" src/tests/ --include="*.py"
```

**Files**: Test files found by grep

---

## Test Strategy

```bash
./run-tests.sh -v -k "assignment"
./run-tests.sh -v  # Full test run
```

---

## Definition of Done Checklist

- [ ] All 5 functions have required `session` parameter
- [ ] No `session_scope()` inside these functions
- [ ] `assignment_form.py` uses `ui_session()`
- [ ] `packaging_assignment_dialog.py` uses `ui_session()`
- [ ] Tests pass

---

## Activity Log

- 2026-01-22T15:30:43Z – system – lane=planned – Prompt created.
- 2026-01-22T16:54:32Z – claude-opus – shell_pid=85707 – lane=doing – Started implementation via workflow command
- 2026-01-22T17:11:51Z – claude-opus – shell_pid=85707 – lane=for_review – All 5 assignment functions (assign_package_to_recipient, update_assignment, remove_assignment, get_event_assignments, get_recipient_assignments_for_event) updated with required session parameter. All 2636 tests pass.
- 2026-01-22T19:29:57Z – claude – shell_pid=14709 – lane=doing – Started review via workflow command
- 2026-01-22T19:31:09Z – claude – shell_pid=14709 – lane=done – Review passed: All 5 assignment functions have required session param, no internal session_scope, UI callers use ui_session(), 2636 tests pass
