---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Session Ownership Foundation"
phase: "Phase 0 - Foundation"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "79653"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-20T20:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Session Ownership Foundation

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - this is the foundational work package.

---

## Objectives & Success Criteria

**Primary Objective**: Establish the session parameter pattern contract and test infrastructure to validate atomicity guarantees across all services.

**Success Criteria**:
1. Test infrastructure exists that can verify transaction rollback across multi-service operations
2. Session ownership pattern is documented with clear examples
3. Existing correct services are audited and confirmed compliant
4. Optional helper module provides consistent session handling utility

**Key Acceptance Checkpoints**:
- [ ] `test_session_atomicity.py` passes with multi-service rollback verification
- [ ] Documentation explains the `nullcontext` pattern with before/after examples
- [ ] Audit report confirms batch_production, assembly, recipe, ingredient, inventory_item services are compliant

---

## Context & Constraints

### Supporting Documents
- **Constitution**: `.kittify/memory/constitution.md` - Session ownership principle (Principle V)
- **Plan**: `kitty-specs/060-architecture-hardening-service-boundaries/plan.md`
- **Research**: `kitty-specs/060-architecture-hardening-service-boundaries/research.md` - Gold standard pattern analysis

### Architectural Decisions
- Use `nullcontext` pattern from `batch_production_service.py` lines 279-281
- All services must accept optional `session=None` parameter
- When session provided: use it exclusively, no internal commits
- When session not provided: open own session_scope (backward compatibility)

### Gold Standard Pattern Reference

```python
from contextlib import nullcontext

def record_batch_production(..., session=None):
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # All operations use same session
        result = inventory_item_service.consume_fifo(..., session=session)
        # No internal commit when session provided
```

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create test_session_atomicity.py

**Purpose**: Establish test infrastructure that verifies session atomicity across multi-service operations. This is the foundation for validating all other WPs.

**Steps**:

1. Create new test file at `src/tests/services/test_session_atomicity.py`

2. Implement test fixture for multi-service transactions:
   ```python
   @pytest.fixture
   def multi_service_session():
       """Provide a session that spans multiple service calls."""
       with session_scope() as session:
           yield session
           # Explicit rollback to verify no side effects
           session.rollback()
   ```

3. Implement test case for successful multi-service commit:
   ```python
   def test_multi_service_commit_atomicity(multi_service_session):
       """Verify all changes commit together when session shared."""
       session = multi_service_session

       # Call service A with session
       result_a = some_service.create_something(..., session=session)

       # Call service B with same session
       result_b = other_service.update_something(..., session=session)

       # Both should be visible in same transaction
       assert result_a is not None
       assert result_b is not None
   ```

4. Implement test case for rollback on failure:
   ```python
   def test_multi_service_rollback_on_failure(multi_service_session):
       """Verify all changes rollback when any service fails."""
       session = multi_service_session

       # Service A succeeds
       result_a = some_service.create_something(..., session=session)

       # Service B fails (simulate error)
       with pytest.raises(SomeError):
           other_service.failing_operation(..., session=session)

       # Rollback session
       session.rollback()

       # Verify service A's changes were also rolled back
       # (query should return None or empty)
   ```

5. Implement test for detached session detection:
   ```python
   def test_nested_session_causes_detachment_without_passthrough():
       """Document the anti-pattern: nested session_scope causes detachment."""
       # This test documents the PROBLEM we're fixing
       pass
   ```

**Files**:
- `src/tests/services/test_session_atomicity.py` (new, ~150 lines)

**Parallel?**: No - foundational test infrastructure

**Notes**:
- Use `batch_production_service` and `inventory_item_service` as real examples (they already support session param)
- Don't mock - use real services to verify actual atomicity
- Include both SQLite and general SQLAlchemy patterns

---

### Subtask T002 – Add session ownership pattern documentation

**Purpose**: Document the session ownership pattern so all developers understand the contract and can apply it consistently.

**Steps**:

1. Create documentation file at `docs/design/session_ownership_pattern.md`

2. Include these sections:

   **Problem Statement**:
   - Explain the detached object issue
   - Show the anti-pattern (nested session_scope)
   - Reference the existing remediation spec

   **The Pattern**:
   ```python
   from contextlib import nullcontext

   def service_method(..., session=None):
       """
       Accept optional session for transactional control.

       Args:
           session: Optional SQLAlchemy session. If provided, all operations
                   use this session and caller controls commit/rollback.
                   If None, method manages its own transaction.
       """
       cm = nullcontext(session) if session is not None else session_scope()
       with cm as session:
           # All database operations here
           # Pass session to any downstream service calls
           downstream_result = other_service.method(..., session=session)
           # NO commit when session provided - caller controls transaction
   ```

   **Rules**:
   1. All public service methods MUST accept `session=None`
   2. When session provided, use it exclusively (no internal session_scope)
   3. When session provided, do NOT commit (caller controls transaction)
   4. Pass session to ALL downstream service calls
   5. When session NOT provided, open own session (backward compatible)

   **Examples**: Good vs bad patterns with code snippets

3. Update `docs/design/session_management_remediation_spec.md` to reference new pattern doc

**Files**:
- `docs/design/session_ownership_pattern.md` (new, ~100 lines)
- `docs/design/session_management_remediation_spec.md` (update reference)

**Parallel?**: No - defines the pattern for other subtasks

**Notes**:
- Keep documentation concise and actionable
- Include "before/after" examples
- Link to batch_production_service.py as reference implementation

---

### Subtask T003 – Audit existing services for pattern compliance

**Purpose**: Verify that services claimed to be correct actually follow the pattern. Document any deviations.

**Steps**:

1. Audit each service file for these compliance checks:
   - Has `session=None` parameter on public methods
   - Uses conditional session handling (nullcontext or if/else)
   - Passes session to downstream calls
   - No internal commits when session provided

2. Services to audit (from research.md):
   - `src/services/batch_production_service.py` - Expected: COMPLIANT (gold standard)
   - `src/services/assembly_service.py` - Expected: COMPLIANT
   - `src/services/recipe_service.py` - Expected: COMPLIANT
   - `src/services/ingredient_service.py` - Expected: COMPLIANT
   - `src/services/inventory_item_service.py` - Expected: COMPLIANT

3. For each service, verify:
   ```
   Service: batch_production_service.py
   Methods checked: check_can_produce(), record_batch_production()
   Session param: YES
   Conditional handling: YES (nullcontext pattern)
   Downstream passing: YES (consume_fifo, get_aggregated_ingredients)
   No internal commit: YES
   Status: COMPLIANT
   ```

4. Create audit report as comment in test file or separate markdown

5. If any deviations found:
   - Document the specific issue
   - Flag for immediate fix (do NOT proceed if foundational services are broken)

**Files**:
- Multiple service files (read-only audit)
- `src/tests/services/test_session_atomicity.py` (add audit results as comments)

**Parallel?**: No - must complete before other WPs start

**Notes**:
- This is read-only verification, not modification
- If deviations found, stop and report (foundational assumption violated)

---

### Subtask T004 – Create session_helper utility module (optional)

**Purpose**: Provide a helper function or decorator for consistent session handling. This is optional - skip if the inline pattern is sufficiently clear.

**Steps**:

1. Evaluate whether helper is needed:
   - If the `nullcontext` pattern is simple enough, skip this
   - If repeated boilerplate would benefit from abstraction, create helper

2. If creating helper, add to `src/utils/session_helper.py`:
   ```python
   from contextlib import nullcontext
   from src.utils.db import session_scope

   def with_session(session=None):
       """
       Return context manager for optional session handling.

       Usage:
           def my_service_method(..., session=None):
               with with_session(session) as sess:
                   # Use sess for all operations
       """
       return nullcontext(session) if session is not None else session_scope()
   ```

3. Add tests for helper in `src/tests/utils/test_session_helper.py`

4. Update documentation to reference helper (if created)

**Files**:
- `src/utils/session_helper.py` (optional, ~20 lines)
- `src/tests/utils/test_session_helper.py` (optional, ~30 lines)

**Parallel?**: Yes - can proceed alongside T001-T003

**Notes**:
- This is optional - only create if it adds value
- Keep it simple - don't over-engineer
- The inline pattern may be clearer than an abstraction

---

## Test Strategy

**Required Tests**:
- `test_multi_service_commit_atomicity` - Verify shared session commits together
- `test_multi_service_rollback_on_failure` - Verify rollback cascades to all changes
- `test_session_passthrough_to_downstream` - Verify downstream services receive session

**Test Commands**:
```bash
# Run all session atomicity tests
./run-tests.sh src/tests/services/test_session_atomicity.py -v

# Run with coverage
./run-tests.sh src/tests/services/test_session_atomicity.py -v --cov=src/services
```

**Test Data**:
- Use existing test fixtures for recipes, ingredients, inventory
- Create minimal test data that exercises multi-service paths

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Audit reveals non-compliant foundational services | Stop work, report, fix before continuing |
| Test infrastructure too complex | Keep tests simple, use real services not mocks |
| Helper module adds unnecessary abstraction | Mark T004 optional, skip if pattern is clear enough |

---

## Definition of Done Checklist

- [ ] T001: `test_session_atomicity.py` created with rollback verification tests
- [ ] T002: `session_ownership_pattern.md` documentation created
- [ ] T003: All 5 foundational services audited and confirmed compliant
- [ ] T004: Helper module created OR explicitly skipped with rationale
- [ ] All tests pass: `./run-tests.sh src/tests/services/test_session_atomicity.py -v`
- [ ] Documentation reviewed for clarity

---

## Review Guidance

**Key Review Checkpoints**:
1. Test infrastructure actually verifies atomicity (not just mocked)
2. Documentation is actionable (developer can apply pattern immediately)
3. Audit is thorough (all 5 services checked, all methods verified)
4. Pattern is consistent with batch_production_service gold standard

**Questions for Reviewer**:
- Do the tests use real services or mocks? (Should be real)
- Is the documentation clear enough for a new developer?
- Were any compliance issues found in the audit?

---

## Activity Log

- 2026-01-20T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-20T17:39:12Z – claude-opus – shell_pid=72061 – lane=doing – Started implementation via workflow command
- 2026-01-20T17:54:42Z – claude-opus – shell_pid=72061 – lane=for_review – Moved to for_review
- 2026-01-20T22:21:32Z – claude-opus – shell_pid=79653 – lane=doing – Started review via workflow command
