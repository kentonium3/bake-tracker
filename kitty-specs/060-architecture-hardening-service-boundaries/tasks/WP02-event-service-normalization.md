---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Event Service Session Normalization"
phase: "Phase 0 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-20T20:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Event Service Session Normalization

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

Depends on WP01 (session ownership pattern established).

---

## Objectives & Success Criteria

**Primary Objective**: Add optional session parameter to event service helpers so planning services can include event reads in their transactions.

**Success Criteria**:
1. `get_production_progress()` accepts optional session parameter
2. `get_assembly_progress()` accepts optional session parameter
3. `get_shopping_list()` accepts optional session parameter
4. All methods work correctly both with and without session
5. Existing callers continue to work (backward compatible)

**Key Acceptance Checkpoints**:
- [ ] All 3 methods have `session=None` parameter
- [ ] When session provided, methods use it (no internal session_scope)
- [ ] When session NOT provided, methods work as before (open own session)
- [ ] Tests verify both modes work correctly

---

## Context & Constraints

### Supporting Documents
- **Research**: `kitty-specs/060-architecture-hardening-service-boundaries/research.md` - Section 2, Services Needing Session Parameter
- **Plan**: `kitty-specs/060-architecture-hardening-service-boundaries/plan.md` - WP02 section

### File Locations (from research)
- `src/services/event_service.py`:
  - `get_production_progress()` at line 1927
  - `get_assembly_progress()` at line 2005
  - `get_shopping_list()` at line 946

### Pattern to Apply

Follow the if/else session pattern (simpler than nullcontext for these methods):

```python
def get_production_progress(event_id: int, session=None):
    """Get production progress for event."""
    if session is not None:
        return _get_production_progress_impl(event_id, session)
    with session_scope() as session:
        return _get_production_progress_impl(event_id, session)

def _get_production_progress_impl(event_id: int, session):
    """Implementation using provided session."""
    # All queries use session parameter
    # No internal commits
    pass
```

---

## Subtasks & Detailed Guidance

### Subtask T005 – Add session param to get_production_progress()

**Purpose**: Allow planning/progress.py to include production progress reads in the same transaction as other planning operations.

**Steps**:

1. Open `src/services/event_service.py` and locate `get_production_progress()` (line ~1927)

2. Add `session=None` parameter to function signature:
   ```python
   def get_production_progress(event_id: int, session=None) -> Dict[str, Any]:
   ```

3. Extract implementation to helper function (if not already):
   ```python
   def _get_production_progress_impl(event_id: int, session) -> Dict[str, Any]:
       # Move existing implementation here
       # Ensure all queries use the session parameter
       pass
   ```

4. Update main function to handle session conditionally:
   ```python
   def get_production_progress(event_id: int, session=None) -> Dict[str, Any]:
       """
       Get production progress for an event.

       Args:
           event_id: The event ID
           session: Optional session for transactional control
       """
       if session is not None:
           return _get_production_progress_impl(event_id, session)
       with session_scope() as session:
           return _get_production_progress_impl(event_id, session)
   ```

5. Verify no internal commits in the implementation

**Files**:
- `src/services/event_service.py` (modify ~50 lines around line 1927)

**Parallel?**: No - must complete before T006, T007 can parallelize

**Notes**:
- Check if method already has helper pattern; if so, just add session param
- Ensure all internal queries use `session.query(...)` not new session_scope

---

### Subtask T006 – Add session param to get_assembly_progress()

**Purpose**: Allow planning/progress.py to include assembly progress reads in the same transaction.

**Steps**:

1. Locate `get_assembly_progress()` (line ~2005)

2. Apply same pattern as T005:
   ```python
   def get_assembly_progress(event_id: int, session=None) -> Dict[str, Any]:
       if session is not None:
           return _get_assembly_progress_impl(event_id, session)
       with session_scope() as session:
           return _get_assembly_progress_impl(event_id, session)
   ```

3. Extract implementation to helper if needed

4. Verify no internal commits

**Files**:
- `src/services/event_service.py` (modify ~50 lines around line 2005)

**Parallel?**: Yes - can proceed in parallel with T007 after T005 establishes pattern

**Notes**:
- Similar structure to production progress
- May share common patterns with T005

---

### Subtask T007 – Add session param to get_shopping_list()

**Purpose**: Allow shopping_list.py to include event shopping list reads in the same transaction.

**Steps**:

1. Locate `get_shopping_list()` (line ~946)

2. Apply same pattern:
   ```python
   def get_shopping_list(event_id: int, session=None) -> List[Dict[str, Any]]:
       if session is not None:
           return _get_shopping_list_impl(event_id, session)
       with session_scope() as session:
           return _get_shopping_list_impl(event_id, session)
   ```

3. Extract implementation to helper if needed

4. Verify no internal commits

**Files**:
- `src/services/event_service.py` (modify ~50 lines around line 946)

**Parallel?**: Yes - can proceed in parallel with T006 after T005 establishes pattern

**Notes**:
- This method may have different return structure than progress methods
- Ensure shopping list data structure is preserved

---

### Subtask T008 – Update event_service tests for session pass-through

**Purpose**: Verify that all three methods work correctly when session is provided.

**Steps**:

1. Locate event service tests at `src/tests/services/test_event_service.py`

2. Add tests for session pass-through for each method:
   ```python
   def test_get_production_progress_with_session():
       """Verify production progress uses provided session."""
       with session_scope() as session:
           # Create test event and production data
           event = _create_test_event(session)

           # Call with session
           result = event_service.get_production_progress(event.id, session=session)

           # Verify result structure
           assert result is not None
           # Verify session was used (no detachment errors)

   def test_get_assembly_progress_with_session():
       """Verify assembly progress uses provided session."""
       # Similar pattern
       pass

   def test_get_shopping_list_with_session():
       """Verify shopping list uses provided session."""
       # Similar pattern
       pass
   ```

3. Add tests that verify session is actually used (not ignored):
   ```python
   def test_progress_sees_uncommitted_changes():
       """Verify progress method sees uncommitted changes in same session."""
       with session_scope() as session:
           # Create event
           event = _create_test_event(session)
           session.flush()  # Make ID available but don't commit

           # Add production record (uncommitted)
           _add_production_record(event.id, session)
           session.flush()

           # Progress should see the uncommitted record
           result = event_service.get_production_progress(event.id, session=session)
           assert result["total_produced"] > 0  # Sees uncommitted data
   ```

**Files**:
- `src/tests/services/test_event_service.py` (add ~100 lines)

**Parallel?**: No - depends on T005-T007 completing

**Notes**:
- Focus on verifying session is actually used, not just accepted
- Test that uncommitted changes are visible when session shared

---

### Subtask T009 – Verify backward compatibility

**Purpose**: Ensure existing callers that don't pass session continue to work.

**Steps**:

1. Find existing callers of these methods:
   ```bash
   grep -r "get_production_progress\|get_assembly_progress\|get_shopping_list" src/ --include="*.py"
   ```

2. Verify each caller still works without modification:
   - Most callers don't pass session (backward compatible)
   - Callers should not need changes

3. Add explicit backward compatibility tests:
   ```python
   def test_get_production_progress_without_session():
       """Verify method works without session parameter (backward compat)."""
       # Create test data in separate transaction
       event_id = _create_test_event_committed()

       # Call without session parameter
       result = event_service.get_production_progress(event_id)

       # Should work correctly
       assert result is not None
   ```

4. Run full test suite to catch any regressions:
   ```bash
   ./run-tests.sh -v
   ```

**Files**:
- `src/tests/services/test_event_service.py` (add ~30 lines)
- Various caller files (verify only, no changes needed)

**Parallel?**: No - final verification step

**Notes**:
- This is primarily verification, not new code
- If any caller breaks, fix is likely missing default value

---

## Test Strategy

**Required Tests**:
1. `test_get_production_progress_with_session` - Session pass-through works
2. `test_get_assembly_progress_with_session` - Session pass-through works
3. `test_get_shopping_list_with_session` - Session pass-through works
4. `test_progress_sees_uncommitted_changes` - Session actually used
5. `test_get_*_without_session` - Backward compatibility (3 tests)

**Test Commands**:
```bash
# Run event service tests
./run-tests.sh src/tests/services/test_event_service.py -v

# Run all tests to verify no regressions
./run-tests.sh -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing callers | T009 explicitly verifies backward compatibility |
| Session not actually used | T008 tests that uncommitted changes are visible |
| Method signature change breaks imports | session=None default ensures no import changes needed |

---

## Definition of Done Checklist

- [ ] T005: `get_production_progress()` has session parameter
- [ ] T006: `get_assembly_progress()` has session parameter
- [ ] T007: `get_shopping_list()` has session parameter
- [ ] T008: Tests verify session pass-through works
- [ ] T009: Backward compatibility verified
- [ ] All tests pass: `./run-tests.sh src/tests/services/test_event_service.py -v`
- [ ] Full test suite passes: `./run-tests.sh -v`

---

## Review Guidance

**Key Review Checkpoints**:
1. Session parameter has default `None` (backward compatible)
2. Implementation helper receives and uses session
3. No internal commits when session provided
4. Tests verify session is actually used (not just accepted)

**Questions for Reviewer**:
- Are all 3 methods updated consistently?
- Do tests verify the session is actually used (sees uncommitted data)?
- Does the full test suite pass?

---

## Activity Log

- 2026-01-20T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
