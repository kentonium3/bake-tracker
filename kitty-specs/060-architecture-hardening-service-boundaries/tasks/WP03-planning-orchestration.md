---
work_package_id: "WP03"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Planning Orchestration Session Discipline"
phase: "Phase 1 - Critical Path"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "94225"
review_status: ""
reviewed_by: ""
dependencies: ["WP02"]
history:
  - timestamp: "2026-01-20T20:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Planning Orchestration Session Discipline

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

Depends on WP02 (event service accepts session parameter).

---

## Objectives & Success Criteria

**Primary Objective**: Thread session through planning services and remove internal commits that break caller transaction control.

**Success Criteria**:
1. `progress.py` passes session to event service calls
2. `shopping_list.py` has no internal commits (lines 223, 266 removed)
3. `feasibility.py` returns cost and assignment blockers distinctly
4. `available_to_assemble` calculated via feasibility service (not hardcoded)
5. All planning operations maintain transactional atomicity

**Key Acceptance Checkpoints**:
- [ ] Progress operations see uncommitted changes from same transaction
- [ ] Shopping list completion doesn't auto-commit
- [ ] Feasibility returns structured blocker types
- [ ] Backward compatibility maintained

---

## Context & Constraints

### Supporting Documents
- **Research**: `kitty-specs/060-architecture-hardening-service-boundaries/research.md` - Section 2 (Shopping list commits)
- **Plan**: `kitty-specs/060-architecture-hardening-service-boundaries/plan.md` - WP03 section

### File Locations (from research)
- `src/services/planning/progress.py`:
  - Line 98: calls `event_service.get_production_progress(event_id)` - needs session
  - Line 154: calls `event_service.get_assembly_progress(event_id)` - needs session
- `src/services/planning/shopping_list.py`:
  - Line 223: `session.commit()` in `_mark_shopping_complete_impl()` - REMOVE
  - Line 266: `session.commit()` in `_unmark_shopping_complete_impl()` - REMOVE

### Critical Warning

Removing `session.commit()` calls changes behavior for standalone usage. Must verify:
- Callers that expect auto-commit are updated
- Or ensure session_scope auto-commits on clean exit (which it does)

---

## Subtasks & Detailed Guidance

### Subtask T010 – Update progress.py to pass session to event service

**Purpose**: Allow progress calculations to participate in caller's transaction.

**Steps**:

1. Open `src/services/planning/progress.py`

2. Locate line ~98 where `get_production_progress` is called:
   ```python
   # Before
   production_progress = event_service.get_production_progress(event_id)

   # After
   production_progress = event_service.get_production_progress(event_id, session=session)
   ```

3. Locate line ~154 where `get_assembly_progress` is called:
   ```python
   # Before
   assembly_progress = event_service.get_assembly_progress(event_id)

   # After
   assembly_progress = event_service.get_assembly_progress(event_id, session=session)
   ```

4. Verify that progress.py methods already accept session parameter (they should per research)

5. If progress.py methods don't have session param, add them following WP01 pattern

**Files**:
- `src/services/planning/progress.py` (modify ~10 lines)

**Parallel?**: No - foundational for this WP

**Notes**:
- Simple change - just add `session=session` to calls
- Verify the containing function has session available

---

### Subtask T011 – Remove session.commit() from shopping_list.py

**Purpose**: Allow shopping list operations to participate in caller's transaction without auto-committing.

**Steps**:

1. Open `src/services/planning/shopping_list.py`

2. Locate line 223 in `_mark_shopping_complete_impl()`:
   ```python
   # Before (line 223)
   session.commit()

   # After - REMOVE THE LINE ENTIRELY
   # Or replace with session.flush() if intermediate visibility needed
   ```

3. Locate line 266 in `_unmark_shopping_complete_impl()`:
   ```python
   # Before (line 266)
   session.commit()

   # After - REMOVE THE LINE ENTIRELY
   ```

4. Verify the session_scope context manager auto-commits on clean exit:
   - When session is NOT provided, method opens own session_scope
   - session_scope commits on __exit__ without exception
   - This maintains backward compatibility

5. Add `session.flush()` if the implementation needs the changes visible within the same session (but not committed):
   ```python
   # If visibility needed before return
   session.flush()
   # No commit - caller controls transaction
   ```

**Files**:
- `src/services/planning/shopping_list.py` (modify ~4 lines)

**Parallel?**: Yes - can proceed alongside T010

**Notes**:
- session_scope already auto-commits on clean exit
- Removing explicit commit is safe for standalone callers
- For transactional callers, this is the fix we need

---

### Subtask T012 – Update feasibility.py to return cost/assignment blockers distinctly

**Purpose**: Provide structured blocker information so callers can distinguish inventory vs cost vs assignment issues.

**Steps**:

1. Open `src/services/planning/feasibility.py`

2. Identify the return structure of `check_assembly_feasibility()` and similar methods

3. Update return structure to include distinct blocker categories:
   ```python
   return {
       "can_assemble": bool,
       "blockers": {
           "inventory_blockers": [
               {"item": "flour", "needed": 10, "available": 5, "type": "inventory"}
           ],
           "cost_blockers": [
               {"item": "vanilla", "issue": "no_cost_data", "type": "cost"}
           ],
           "assignment_blockers": [
               {"item": "packaging", "issue": "not_assigned", "type": "assignment"}
           ]
       },
       "summary": {
           "total_blockers": 3,
           "inventory_count": 1,
           "cost_count": 1,
           "assignment_count": 1
       }
   }
   ```

4. If currently returning flat blocker list, restructure:
   ```python
   # Before
   return {"can_assemble": False, "blockers": [...]}

   # After
   return {
       "can_assemble": False,
       "blockers": {
           "inventory_blockers": [...],
           "cost_blockers": [...],
           "assignment_blockers": [...]
       }
   }
   ```

5. Update any callers that depend on old structure

**Files**:
- `src/services/planning/feasibility.py` (modify ~30 lines)
- Any callers of feasibility methods (update if structure changed)

**Parallel?**: Yes - can proceed alongside T010, T011

**Notes**:
- Check existing return structure first
- May need to trace through to see how blockers are currently categorized
- Keep backward compatible if possible (add new keys, don't remove old)

---

### Subtask T013 – Implement available_to_assemble via feasibility service

**Purpose**: Replace hardcoded `available_to_assemble: 0` with actual feasibility calculation.

**Steps**:

1. Find where `available_to_assemble` is currently hardcoded:
   ```bash
   grep -r "available_to_assemble" src/services/planning/
   ```

2. Identify the context - likely in progress.py or planning_service.py

3. Replace hardcoded value with feasibility check:
   ```python
   # Before
   "available_to_assemble": 0  # Hardcoded

   # After
   feasibility_result = feasibility.check_assembly_feasibility(
       finished_good_id, quantity, session=session
   )
   available = quantity if feasibility_result["can_assemble"] else 0
   "available_to_assemble": available
   ```

4. Consider partial availability:
   ```python
   # If feasibility can indicate partial availability
   available = feasibility_result.get("available_quantity", 0)
   ```

5. Thread session through to feasibility call

**Files**:
- `src/services/planning/progress.py` or `planning_service.py` (modify ~15 lines)
- May need to update feasibility.py if partial availability not supported

**Parallel?**: No - depends on T012 (feasibility structure)

**Notes**:
- Locate the hardcoded value first
- May need to check feasibility for multiple items in a loop
- Performance consideration: cache feasibility results if called repeatedly

---

### Subtask T014 – Update planning orchestration tests

**Purpose**: Verify planning operations maintain transactional atomicity.

**Steps**:

1. Add tests for session threading in progress:
   ```python
   def test_progress_uses_shared_session():
       """Verify progress operations use provided session."""
       with session_scope() as session:
           # Create event with uncommitted production
           event = _create_test_event(session)
           _add_uncommitted_production(event.id, session)
           session.flush()

           # Progress should see uncommitted data
           result = progress.get_production_progress(event.id, session=session)
           assert result["completed"] > 0
   ```

2. Add tests for shopping list transaction control:
   ```python
   def test_shopping_complete_no_auto_commit():
       """Verify shopping complete doesn't auto-commit."""
       with session_scope() as session:
           # Create event and shopping list
           event = _create_test_event(session)
           session.flush()

           # Mark complete
           shopping_list.mark_shopping_complete(event.id, session=session)

           # NOT committed yet - verify by rolling back
           session.rollback()

           # Verify shopping was not persisted
           result = shopping_list.is_shopping_complete(event.id)
           assert result is False
   ```

3. Add tests for feasibility blocker structure:
   ```python
   def test_feasibility_returns_distinct_blockers():
       """Verify feasibility returns categorized blockers."""
       result = feasibility.check_assembly_feasibility(...)

       assert "blockers" in result
       assert "inventory_blockers" in result["blockers"]
       assert "cost_blockers" in result["blockers"]
       assert "assignment_blockers" in result["blockers"]
   ```

4. Add test for available_to_assemble calculation:
   ```python
   def test_available_to_assemble_uses_feasibility():
       """Verify available_to_assemble is calculated from feasibility."""
       # Setup: Create assembly with sufficient inventory
       # Verify: available_to_assemble > 0

       # Setup: Create assembly with insufficient inventory
       # Verify: available_to_assemble == 0
       pass
   ```

**Files**:
- `src/tests/services/planning/test_progress.py` (add ~60 lines)
- `src/tests/services/planning/test_shopping_list.py` (add ~40 lines)
- `src/tests/services/planning/test_feasibility.py` (add ~30 lines)

**Parallel?**: No - depends on T010-T013

**Notes**:
- Focus on atomicity verification
- Test both with-session and without-session modes

---

### Subtask T015 – Verify shopping list backward compatibility

**Purpose**: Ensure standalone shopping list usage still works correctly.

**Steps**:

1. Identify standalone callers of shopping list:
   ```bash
   grep -r "mark_shopping_complete\|unmark_shopping_complete" src/ --include="*.py"
   ```

2. For each caller, verify it still works:
   - Callers that don't pass session should still auto-commit (via session_scope)
   - No behavior change expected for these callers

3. Add explicit backward compatibility tests:
   ```python
   def test_mark_shopping_complete_standalone():
       """Verify standalone usage still commits."""
       # Create event in separate transaction
       event_id = _create_committed_event()

       # Mark complete without session (standalone)
       shopping_list.mark_shopping_complete(event_id)

       # Verify persisted
       result = shopping_list.is_shopping_complete(event_id)
       assert result is True
   ```

4. Run full test suite:
   ```bash
   ./run-tests.sh -v
   ```

**Files**:
- `src/tests/services/planning/test_shopping_list.py` (add ~20 lines)

**Parallel?**: No - final verification

**Notes**:
- session_scope commits on clean exit
- Standalone callers should see no behavior change

---

## Test Strategy

**Required Tests**:
1. Session threading in progress operations
2. Shopping list no auto-commit when session provided
3. Shopping list auto-commits when standalone (backward compat)
4. Feasibility returns distinct blocker categories
5. available_to_assemble uses feasibility calculation

**Test Commands**:
```bash
# Run planning tests
./run-tests.sh src/tests/services/planning/ -v

# Run all tests
./run-tests.sh -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Removing commits breaks standalone usage | T015 verifies backward compatibility |
| Feasibility structure change breaks callers | Keep old keys if possible, add new |
| available_to_assemble calculation slow | Cache results if needed |

---

## Definition of Done Checklist

- [ ] T010: progress.py passes session to event service calls
- [ ] T011: session.commit() removed from shopping_list.py (lines 223, 266)
- [ ] T012: feasibility.py returns distinct blocker categories
- [ ] T013: available_to_assemble calculated via feasibility
- [ ] T014: Tests verify atomicity and structure
- [ ] T015: Backward compatibility verified
- [ ] All planning tests pass
- [ ] Full test suite passes

---

## Review Guidance

**Key Review Checkpoints**:
1. session.commit() lines are removed (not just commented)
2. Session passed to event service calls
3. Feasibility blocker structure is useful for callers
4. Backward compatibility tests exist and pass

---

## Activity Log

- 2026-01-20T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-20T22:45:25Z – claude-opus – shell_pid=86115 – lane=doing – Started implementation via workflow command
- 2026-01-20T23:03:53Z – claude-opus – shell_pid=86115 – lane=for_review – All subtasks complete: T010-T015 implemented. Session threading in progress/shopping_list, removed auto-commits, added blocker categories to feasibility, available_to_assemble via feasibility. All 2568 tests pass.
- 2026-01-21T02:45:50Z – claude-opus – shell_pid=94225 – lane=doing – Started review via workflow command
