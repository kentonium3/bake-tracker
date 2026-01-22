---
work_package_id: "WP06"
subtasks:
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
title: "Event Service Target & Status Operations"
phase: "Phase 1 - Service Hardening"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "42843"
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

# Work Package Prompt: WP06 – Event Service Target & Status Operations

## Implementation Command

```bash
spec-kitty implement WP06 --base WP01
```

---

## Objectives & Success Criteria

Add required `session` parameter to production/assembly target functions and fulfillment status functions.

**Functions to update** (8 total):

**Target operations**:
1. `set_production_target` (line ~1722)
2. `set_assembly_target` (line ~1778)
3. `get_production_targets` (line ~1834)
4. `get_assembly_targets` (line ~1859)
5. `delete_production_target` (line ~1884)
6. `delete_assembly_target` (line ~1911)

**Status operations**:
7. `update_fulfillment_status` (line ~2379)
8. `get_packages_by_status` (line ~2449)

**Success Criteria**:
- [ ] All 8 functions require `session` parameter
- [ ] No internal `session_scope()` in these functions
- [ ] UI callers use `ui_session()`
- [ ] Tests pass

---

## Subtasks & Detailed Guidance

### Subtask T026 – Add session to target set/get functions (1/2)

```python
def set_production_target(
    event_id: int,
    recipe_id: int,
    target: int,
    session: Session,
) -> EventProductionTarget:

def set_assembly_target(
    event_id: int,
    finished_good_id: int,
    target: int,
    session: Session,
) -> EventAssemblyTarget:

def get_production_targets(event_id: int, session: Session) -> List[EventProductionTarget]:

def get_assembly_targets(event_id: int, session: Session) -> List[EventAssemblyTarget]:
```

---

### Subtask T027 – Add session to delete functions (2/2)

```python
def delete_production_target(event_id: int, recipe_id: int, session: Session) -> bool:

def delete_assembly_target(event_id: int, finished_good_id: int, session: Session) -> bool:
```

---

### Subtask T028 – Add session to status functions

```python
def update_fulfillment_status(
    assignment_id: int,
    status: FulfillmentStatus,
    session: Session,
) -> EventRecipientPackage:

def get_packages_by_status(
    event_id: int,
    status: FulfillmentStatus,
    session: Session,
) -> List[EventRecipientPackage]:
```

---

### Subtask T029 – Remove internal session_scope

For all 8 functions:
1. Remove `with session_scope() as session:` wrapper
2. Use session parameter directly
3. Keep `session.flush()` for write operations

---

### Subtask T030 – Update UI callers and tests

**Find callers**:
```bash
grep -r "set_production_target\|get_production_targets\|update_fulfillment_status" src/ui/ --include="*.py"
```

**Likely callers**:
- Planning views (target setting)
- Delivery/status tracking views

---

## Definition of Done Checklist

- [ ] All 8 functions have required `session` parameter
- [ ] No `session_scope()` inside these functions
- [ ] UI callers use `ui_session()`
- [ ] Tests pass

---

## Activity Log

- 2026-01-22T15:30:43Z – system – lane=planned – Prompt created.
- 2026-01-22T20:11:12Z – claude-opus – shell_pid=31173 – lane=doing – Started implementation via workflow command
- 2026-01-22T20:41:03Z – claude-opus – shell_pid=31173 – lane=for_review – All 8 functions updated with required session parameter. UI callers and tests updated. 2636 tests pass.
- 2026-01-22T20:43:22Z – claude-opus – shell_pid=42843 – lane=doing – Started review via workflow command
- 2026-01-22T20:44:42Z – claude-opus – shell_pid=42843 – lane=done – Review passed: All 8 functions have required session parameter, no internal session_scope(), UI callers properly wrapped, 54 related tests pass.
