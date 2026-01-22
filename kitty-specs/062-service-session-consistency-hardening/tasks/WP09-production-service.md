---
work_package_id: "WP09"
subtasks:
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
title: "Production Service Session Hardening"
phase: "Phase 1 - Service Hardening"
lane: "done"
assignee: ""
agent: "codex"
shell_pid: "65344"
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

# Work Package Prompt: WP09 – Production Service Session Hardening

## Implementation Command

```bash
spec-kitty implement WP09 --base WP01
```

---

## Objectives & Success Criteria

Add required `session` parameter to all `production_service.py` functions.

**Note**: This is `src/services/production_service.py`, NOT `batch_production_service.py` (which is WP08).

**Functions to update** (8 total, per research.md):
1. `get_production_records`
2. `get_production_total`
3. `can_assemble_package`
4. `update_package_status`
5. `get_production_progress`
6. `get_dashboard_summary`
7. `get_recipe_cost_breakdown`
8. `get_event_assignments`

**Success Criteria**:
- [ ] All 8 functions require `session` parameter
- [ ] No internal `session_scope()` in these functions
- [ ] UI callers use `ui_session()`
- [ ] Tests pass

---

## Context & Constraints

**File**: `src/services/production_service.py`

**Note**: `production_service.py` provides query/status functions for production tracking. `batch_production_service.py` provides recording functions.

---

## Subtasks & Detailed Guidance

### Subtask T042 – Add session to query functions (1/2)

```python
def get_production_records(event_id: int, session: Session) -> List[ProductionRecord]:

def get_production_total(event_id: int, recipe_id: int, session: Session) -> Dict[str, Any]:
```

---

### Subtask T043 – Add session to package functions (2/2)

```python
def can_assemble_package(assignment_id: int, session: Session) -> Dict[str, Any]:

def update_package_status(
    assignment_id: int,
    status: PackageStatus,
    session: Session,
) -> EventRecipientPackage:
```

---

### Subtask T044 – Add session to progress/dashboard functions

```python
def get_production_progress(event_id: int, session: Session) -> Dict[str, Any]:

def get_dashboard_summary(session: Session) -> List[Dict[str, Any]]:
```

---

### Subtask T045 – Add session to cost/assignment functions

```python
def get_recipe_cost_breakdown(event_id: int, session: Session) -> List[Dict[str, Any]]:

def get_event_assignments(event_id: int, session: Session) -> List[Dict[str, Any]]:
```

---

### Subtask T046 – Remove internal session_scope from all functions

For all 8 functions:
1. Remove `with session_scope() as session:` wrapper
2. Use session parameter directly
3. Keep `session.flush()` for any write operations

---

### Subtask T047 – Update UI callers

**Find callers**:
```bash
grep -r "production_service\." src/ui/ --include="*.py"
```

**Likely callers**:
- `src/ui/production_dashboard_tab.py`
- `src/ui/dashboards/make_dashboard.py`
- Planning views

---

### Subtask T048 – Update tests

**Find and update**:
```bash
grep -r "production_service\." src/tests/ --include="*.py"
```

---

## Definition of Done Checklist

- [ ] All 8 functions have required `session` parameter
- [ ] No `session_scope()` inside these functions
- [ ] UI callers use `ui_session()`
- [ ] Tests pass

---

## Activity Log

- 2026-01-22T15:30:43Z – system – lane=planned – Prompt created.
- 2026-01-22T21:16:27Z – codex – shell_pid=65344 – lane=doing – Started implementation via workflow command
- 2026-01-22T21:28:03Z – codex – shell_pid=65344 – lane=for_review – Ready for review: production_service functions require session, session threaded through update/status/progress/dashboard/cost/assignments; tests updated and production_service test suite passes
- 2026-01-22T21:30:13Z – codex – shell_pid=65344 – lane=doing – Started review via workflow command
- 2026-01-22T21:30:52Z – codex – shell_pid=65344 – lane=done – Review passed: production_service functions require session, no internal session_scope, tests updated; production_service test suite passes
