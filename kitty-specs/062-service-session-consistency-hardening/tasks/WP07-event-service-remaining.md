---
work_package_id: "WP07"
subtasks:
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
title: "Event Service Remaining Operations"
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

# Work Package Prompt: WP07 – Event Service Remaining Operations

## Implementation Command

```bash
spec-kitty implement WP07 --base WP01
```

---

## Objectives & Success Criteria

Add required `session` parameter to remaining event service functions (clone, export, packaging, history).

**Functions to update** (5 total):
1. `clone_event` (line ~1239)
2. `export_shopping_list_csv` (line ~1152)
3. `get_event_packaging_needs` (line ~1448)
4. `get_event_packaging_breakdown` (line ~1577)
5. `get_recipient_history` (line ~1678)

**Note**: `get_shopping_list` already accepts `session=None` - make it required.

**Success Criteria**:
- [ ] All 5 functions require `session` parameter
- [ ] `get_shopping_list` session parameter becomes required
- [ ] `clone_event` uses session for all cloned entities
- [ ] Private helpers receive session where needed
- [ ] Tests pass

---

## Subtasks & Detailed Guidance

### Subtask T031 – Add session to clone/export functions

**clone_event**: This is complex - creates new event and copies assignments.

```python
def clone_event(
    source_event_id: int,
    new_name: str,
    new_date: date,
    session: Session,
) -> Event:
```

**Ensure**: All entity creation uses the provided session.

**export_shopping_list_csv**: May need session for data reads before file write.

```python
def export_shopping_list_csv(event_id: int, file_path: str, session: Session) -> bool:
```

---

### Subtask T032 – Add session to packaging query functions

```python
def get_event_packaging_needs(event_id: int, session: Session) -> Dict[str, PackagingNeed]:

def get_event_packaging_breakdown(event_id: int, session: Session) -> Dict[int, List[PackagingSource]]:
```

**Note**: These may call private helpers (`_aggregate_packaging`, `_get_packaging_on_hand`). Pass session to those helpers.

---

### Subtask T033 – Add session to get_recipient_history

```python
def get_recipient_history(recipient_id: int, session: Session) -> List[Dict[str, Any]]:
```

---

### Subtask T034 – Remove internal session_scope and update helpers

1. Remove `with session_scope() as session:` from all functions
2. Update private helper signatures to accept session:

```python
def _get_packaging_on_hand(session: Session, product_id: int) -> float:

def _aggregate_packaging(session: Session, event: Event) -> tuple[Dict[int, float], Dict[str, float]]:

def _get_generic_packaging_on_hand(session: Session, product_name: str) -> float:
```

**Important**: Private helpers are called internally - ensure session threading.

---

### Subtask T035 – Update UI callers and tests

**Find callers**:
```bash
grep -r "clone_event\|get_event_packaging\|get_recipient_history" src/ui/ --include="*.py"
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| clone_event misses session in entity creation | Partial clone | Trace all session.add() calls |
| Private helpers not updated | AttributeError | Update all _ prefixed functions |

---

## Definition of Done Checklist

- [ ] All 5 functions have required `session` parameter
- [ ] `get_shopping_list` changed from optional to required session
- [ ] Private helpers accept and use session
- [ ] `clone_event` tested with rollback to verify atomicity
- [ ] UI callers use `ui_session()`
- [ ] Tests pass

---

## Activity Log

- 2026-01-22T15:30:43Z – system – lane=planned – Prompt created.
- 2026-01-22T20:35:54Z – codex – shell_pid=65344 – lane=doing – Started implementation via workflow command
- 2026-01-22T20:59:03Z – codex – shell_pid=65344 – lane=for_review – Ready for review: require session for remaining event service ops (shopping list, export, clone, packaging, history), thread session through helpers/UI/tests, update planning wrapper; targeted tests pass
