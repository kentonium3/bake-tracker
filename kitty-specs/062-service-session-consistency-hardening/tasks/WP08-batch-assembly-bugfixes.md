---
work_package_id: "WP08"
subtasks:
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
title: "Batch & Assembly Service Bug Fixes"
phase: "Phase 1 - Service Hardening"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "55981"
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

# Work Package Prompt: WP08 – Batch & Assembly Service Bug Fixes

## Implementation Command

```bash
spec-kitty implement WP08 --base WP01
```

---

## Objectives & Success Criteria

**Fix the critical bug** where history query functions accept a session parameter but completely ignore it, shadowing with a new session.

**Functions to fix** (4 total):
1. `batch_production_service.get_production_history` (line ~519 shadows session)
2. `batch_production_service.get_production_run` (line ~573 shadows session)
3. `assembly_service.get_assembly_history` (line ~599 shadows session)
4. `assembly_service.get_assembly_run` (line ~654 shadows session)

**Bug Pattern** (from research.md):
```python
def get_production_history(
    *,
    session=None,  # Session parameter EXISTS...
) -> List[Dict[str, Any]]:
    with session_scope() as session:  # ...but is SHADOWED here!
```

**Success Criteria**:
- [ ] All 4 functions use provided session (no shadowing)
- [ ] Session parameter is REQUIRED (not optional)
- [ ] Test verifies uncommitted data visible with session
- [ ] Existing tests pass

---

## Context & Constraints

**Files**:
- `src/services/batch_production_service.py`
- `src/services/assembly_service.py`

**Reference (correct pattern)**: `record_batch_production` in same file uses session correctly.

**Spec Decision**: Session parameter becomes REQUIRED (no default value), not optional with nullcontext pattern.

---

## Subtasks & Detailed Guidance

### Subtask T036 – Fix batch_production_service.get_production_history

**Location**: `src/services/batch_production_service.py`, line ~500-548

**Current (buggy)**:
```python
def get_production_history(
    *,
    recipe_id: Optional[int] = None,
    # ... other filters
    session=None,  # <-- EXISTS
) -> List[Dict[str, Any]]:
    with session_scope() as session:  # <-- SHADOWS IT!
        query = session.query(ProductionRun)
        # ...
```

**Fixed**:
```python
def get_production_history(
    *,
    recipe_id: Optional[int] = None,
    # ... other filters
    session: Session,  # <-- REQUIRED, no default
) -> List[Dict[str, Any]]:
    # Use session directly - no internal session_scope()
    query = session.query(ProductionRun)
    # ...
```

**Steps**:
1. Change `session=None` to `session: Session`
2. Remove `with session_scope() as session:` wrapper
3. Unindent the code block
4. Keep all query logic unchanged

**Files**: `src/services/batch_production_service.py`

---

### Subtask T037 – Fix batch_production_service.get_production_run

**Location**: Line ~551-590

**Same pattern fix**:
```python
def get_production_run(
    production_run_id: int,
    *,
    include_consumptions: bool = True,
    include_losses: bool = False,
    session: Session,  # REQUIRED
) -> Dict[str, Any]:
    # Use session directly
    query = session.query(ProductionRun).filter(...)
```

**Files**: `src/services/batch_production_service.py`

---

### Subtask T038 – Fix assembly_service.get_assembly_history

**Location**: `src/services/assembly_service.py`, line ~574-630

**Same pattern fix** as T036:
```python
def get_assembly_history(
    *,
    finished_good_id: Optional[int] = None,
    # ... other filters
    session: Session,  # REQUIRED
) -> List[Dict[str, Any]]:
    # Use session directly
    query = session.query(AssemblyRun)
```

**Files**: `src/services/assembly_service.py`

---

### Subtask T039 – Fix assembly_service.get_assembly_run

**Location**: Line ~632-680

```python
def get_assembly_run(
    assembly_run_id: int,
    *,
    include_consumptions: bool = True,
    session: Session,  # REQUIRED
) -> Dict[str, Any]:
```

**Files**: `src/services/assembly_service.py`

---

### Subtask T040 – Add uncommitted data visibility tests

**Purpose**: Verify the fix works - queries should see uncommitted data when given a session.

```python
# src/tests/test_batch_production_service.py (or similar)

def test_get_production_history_sees_uncommitted_data():
    """History query should see uncommitted records in same session."""
    with session_scope() as session:
        # Create a production run (uncommitted)
        run = ProductionRun(
            recipe_id=1,
            finished_unit_id=1,
            # ... required fields
        )
        session.add(run)
        session.flush()  # Gets ID but doesn't commit

        # Query history with same session
        history = get_production_history(session=session)

        # Should see the uncommitted run
        run_ids = [h["id"] for h in history]
        assert run.id in run_ids

    # After session closes, nothing persisted (test isolation)


def test_get_assembly_history_sees_uncommitted_data():
    """Assembly history should see uncommitted records."""
    # Similar pattern for assembly_service
```

**Files**: `src/tests/test_batch_production_service.py`, `src/tests/test_assembly_service.py`

---

### Subtask T041 – Update existing tests

**Find and update tests**:
```bash
grep -r "get_production_history\|get_production_run\|get_assembly_history\|get_assembly_run" src/tests/ --include="*.py"
```

Update all callers to pass session:
```python
# Before
history = batch_production_service.get_production_history(recipe_id=1)

# After
with session_scope() as session:
    history = batch_production_service.get_production_history(recipe_id=1, session=session)
```

**Files**: Test files found by grep

---

## Test Strategy

```bash
./run-tests.sh src/tests/test_batch_production_service.py -v
./run-tests.sh src/tests/test_assembly_service.py -v
./run-tests.sh -v  # Full run
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Similar bug elsewhere | Data inconsistency | Search for `session=None` followed by `session_scope()` |
| UI callers not updated | Runtime error | Grep for function names in UI code |

---

## Definition of Done Checklist

- [ ] `get_production_history` uses provided session (no shadowing)
- [ ] `get_production_run` uses provided session
- [ ] `get_assembly_history` uses provided session
- [ ] `get_assembly_run` uses provided session
- [ ] All 4 functions have `session: Session` (required)
- [ ] Uncommitted data visibility tests pass
- [ ] Existing tests updated and passing
- [ ] No `with session_scope()` remains in these functions

---

## Review Guidance

**Critical check**: Verify no `with session_scope() as session:` remains in these 4 functions. The bug is subtle - the parameter exists but was shadowed.

---

## Activity Log

- 2026-01-22T15:30:43Z – system – lane=planned – Prompt created.
- 2026-01-22T21:07:13Z – claude-opus – shell_pid=55981 – lane=doing – Started review via workflow command
- 2026-01-22T21:09:04Z – claude-opus – shell_pid=55981 – lane=done – Review passed: Fixed session shadowing bug in 4 history query functions. All functions now require session parameter. Added 4 uncommitted data visibility tests. Updated 12+ existing tests. Export functions updated to handle session properly. 92 tests pass.
