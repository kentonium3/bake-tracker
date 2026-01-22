---
work_package_id: "WP04"
subtasks:
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
title: "Event Service Calculation Operations"
phase: "Phase 1 - Service Hardening"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "29403"
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

# Work Package Prompt: WP04 – Event Service Calculation Operations

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` field above.

---

## Review Feedback

*[Empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP04 --base WP01
```

**Dependency**: Requires WP01 (ui_session infrastructure).

---

## Objectives & Success Criteria

Add required `session` parameter to event calculation and summary functions.

**Functions to update** (6 total):
1. `get_event_total_cost`
2. `get_event_recipient_count`
3. `get_event_package_count`
4. `get_event_summary`
5. `get_recipe_needs`
6. `get_event_cost_analysis`

**Success Criteria**:
- [ ] All 6 functions require `session` parameter
- [ ] No internal `session_scope()` in these functions
- [ ] Session threaded to any sub-queries
- [ ] UI callers use `ui_session()`
- [ ] Tests pass

---

## Context & Constraints

**Service file**: `src/services/event_service.py`

**Important**: These functions perform complex aggregations. Ensure any internal calls to other service functions also receive the session parameter.

---

## Subtasks & Detailed Guidance

### Subtask T016 – Add session to count/cost functions

**Functions** (approx line numbers):
- `get_event_total_cost` (line ~661)
- `get_event_recipient_count` (line ~696)
- `get_event_package_count` (line ~724)

**Steps**:
```python
def get_event_total_cost(event_id: int, session: Session) -> Decimal:

def get_event_recipient_count(event_id: int, session: Session) -> int:

def get_event_package_count(event_id: int, session: Session) -> int:
```

**Files**: `src/services/event_service.py`

---

### Subtask T017 – Add session to complex aggregation functions

**Functions**:
- `get_event_summary` (line ~757) - returns Dict with multiple aggregates
- `get_recipe_needs` (line ~822) - calculates ingredient needs
- `get_event_cost_analysis` (line ~2275) - complex cost breakdown

**Steps**:
```python
def get_event_summary(event_id: int, session: Session) -> Dict[str, Any]:

def get_recipe_needs(event_id: int, session: Session) -> List[Dict[str, Any]]:

def get_event_cost_analysis(event_id: int, session: Session) -> Dict[str, Any]:
```

**Critical**: `get_event_summary` likely calls other functions internally. Ensure session is passed to those calls.

**Files**: `src/services/event_service.py`

---

### Subtask T018 – Remove internal session_scope and thread session

**Steps**:
1. Remove `with session_scope() as session:` from each function
2. If function calls other service functions, pass session to them
3. Verify no nested session_scope() calls remain

**Example for get_event_summary**:
```python
def get_event_summary(event_id: int, session: Session) -> Dict[str, Any]:
    # Before: with session_scope() as session:
    # After: Use session parameter directly

    event = session.query(Event).get(event_id)
    if not event:
        raise EventNotFoundError(event_id)

    # If calling other functions, pass session:
    total_cost = get_event_total_cost(event_id, session)
    # ...
```

**Files**: `src/services/event_service.py`

---

### Subtask T019 – Update UI callers

**Find callers**:
```bash
grep -r "get_event_summary\|get_event_total_cost\|get_recipe_needs\|get_event_cost_analysis" src/ui/ --include="*.py"
```

**Likely callers**:
- Event cards showing cost/count summaries
- Dashboard displaying recipe needs
- Planning views with cost analysis

**Steps**:
1. Add `from src.ui.utils import ui_session`
2. Wrap calls in `with ui_session() as session:`

**Files**: UI files found by grep

---

### Subtask T020 – Update tests

**Find and update tests**:
```bash
grep -r "get_event_summary\|get_recipe_needs" src/tests/ --include="*.py"
```

**Files**: Test files found by grep

---

## Test Strategy

```bash
./run-tests.sh -v -k "summary or recipe_needs or cost"
./run-tests.sh -v  # Full run
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Internal calls don't receive session | Data inconsistency | Trace all internal calls, pass session |
| Complex aggregation returns stale data | Incorrect reports | Test with uncommitted data |

---

## Definition of Done Checklist

- [ ] All 6 functions have required `session` parameter
- [ ] No `session_scope()` inside these functions
- [ ] Internal calls receive session parameter
- [ ] UI callers use `ui_session()`
- [ ] Tests pass

---

## Activity Log

- 2026-01-22T15:30:43Z – system – lane=planned – Prompt created.
- 2026-01-22T19:33:51Z – claude-opus – shell_pid=15857 – lane=doing – Started implementation via workflow command
- 2026-01-22T19:54:30Z – claude-opus – shell_pid=15857 – lane=for_review – All 6 calculation functions updated with required session param. get_shopping_list threading fixed. All 2636 tests pass.
- 2026-01-22T20:04:48Z – claude – shell_pid=29403 – lane=doing – Started review via workflow command
- 2026-01-22T20:05:44Z – claude – shell_pid=29403 – lane=done – Review passed: All 6 calculation functions have required session param, session properly threaded to sub-calls, UI callers use ui_session(), 2636 tests pass
