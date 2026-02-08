---
work_package_id: WP01
title: Add Session Parameter to finished_unit_service
lane: "for_review"
dependencies: []
base_branch: main
base_commit: 76e546c87bd9242af1b5f6190504ce51d009b99a
created_at: '2026-02-08T17:23:22.124336+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 0 - Foundation
assignee: ''
agent: "claude-opus"
shell_pid: "40598"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T17:14:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 - Add Session Parameter to finished_unit_service

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies — this is the starting work package.

---

## Objectives & Success Criteria

Add `session: Optional[Session] = None` parameter to all CRUD methods in `finished_unit_service.py`, enabling transaction composition with callers. This fixes a Constitution Principle VI.C violation (all service functions MUST accept optional session parameter).

**Success criteria:**
- All three CRUD methods accept `session` parameter
- When `session` is provided, operations use that session (no new `session_scope()`)
- When `session=None` (default), behavior is identical to current (backward compatible)
- All existing tests pass without modification
- Module-level convenience functions forward session parameter

## Context & Constraints

**Key documents:**
- Plan: `kitty-specs/098-auto-generation-finished-goods/plan.md`
- Research: `kitty-specs/098-auto-generation-finished-goods/research.md` (Question 4)
- Constitution: `.kittify/memory/constitution.md` (Principle VI.C)
- Transaction patterns: `docs/design/transaction_patterns_guide.md`

**Architecture pattern to follow:**
`finished_good_service.py` already implements this correctly. Study the `_impl` pattern there:

```python
# Pattern from finished_good_service.py (lines 275-284)
@staticmethod
def create_finished_good(display_name, assembly_type=AssemblyType.BUNDLE,
                         components=None, session=None, **kwargs):
    if session is not None:
        return FinishedGoodService._create_finished_good_impl(
            display_name, assembly_type, components, session, **kwargs)
    with session_scope() as sess:
        return FinishedGoodService._create_finished_good_impl(
            display_name, assembly_type, components, sess, **kwargs)
```

**Current state of finished_unit_service.py:**
- `create_finished_unit(display_name, recipe_id, **kwargs)` — line 274, no session param
- `update_finished_unit(finished_unit_id, **updates)` — line 390, no session param
- `delete_finished_unit(finished_unit_id)` — line 495, no session param
- Each creates its own `session_scope()` internally
- Module-level convenience functions at lines 887+ forward to class methods

## Subtasks & Detailed Guidance

### Subtask T001 - Refactor `create_finished_unit()` to accept session parameter

**Purpose**: Enable callers to pass a session for transaction composition, while preserving current behavior when no session is passed.

**Steps**:
1. Read `src/services/finished_unit_service.py` lines 274-387 (the full `create_finished_unit` class method)
2. Extract the body (everything inside the current `session_scope()` block) into a new private method `_create_finished_unit_impl(display_name, recipe_id, session, **kwargs)`
3. Update the public method signature to add `session=None`:
   ```python
   @staticmethod
   def create_finished_unit(display_name: str, recipe_id: int, session=None, **kwargs) -> FinishedUnit:
   ```
4. Add the dispatch pattern:
   ```python
   if session is not None:
       return FinishedUnitService._create_finished_unit_impl(display_name, recipe_id, session, **kwargs)
   with session_scope() as sess:
       return FinishedUnitService._create_finished_unit_impl(display_name, recipe_id, sess, **kwargs)
   ```
5. The `_impl` method should contain all the original logic (validation, slug generation, record creation) but use the passed `session` instead of creating a new one

**Files**: `src/services/finished_unit_service.py`
**Parallel?**: Yes (independent of T002, T003)
**Notes**: Be careful with the `session_scope()` exit handling. The current method may have try/except blocks around the session — those should stay in the public method wrapper, not in `_impl`. The `_impl` method should let exceptions propagate (the caller's session or the wrapper's session_scope handles rollback).

### Subtask T002 - Refactor `update_finished_unit()` to accept session parameter

**Purpose**: Same pattern as T001 but for the update method.

**Steps**:
1. Read `src/services/finished_unit_service.py` lines 390-492
2. Extract body into `_update_finished_unit_impl(finished_unit_id, session, **updates)`
3. Update public signature: `def update_finished_unit(finished_unit_id: int, session=None, **updates)`
4. Add dispatch pattern (same as T001)
5. Ensure slug regeneration (if name changes) uses the passed session

**Files**: `src/services/finished_unit_service.py`
**Parallel?**: Yes (independent of T001, T003)
**Notes**: The update method calls `_generate_unique_slug()` which may need the session. Verify that helper methods also receive the session where needed.

### Subtask T003 - Refactor `delete_finished_unit()` to accept session parameter

**Purpose**: Same pattern as T001 but for the delete method.

**Steps**:
1. Read `src/services/finished_unit_service.py` lines 495-551
2. Extract body into `_delete_finished_unit_impl(finished_unit_id, session)`
3. Update public signature: `def delete_finished_unit(finished_unit_id: int, session=None)`
4. Add dispatch pattern
5. The composition reference check (`ReferencedUnitError`) should remain in `_impl`

**Files**: `src/services/finished_unit_service.py`
**Parallel?**: Yes (independent of T001, T002)
**Notes**: The delete already checks for Composition references. This check must use the passed session for the query.

### Subtask T004 - Update module-level convenience functions

**Purpose**: Module-level functions at the bottom of the file must forward the `session` parameter.

**Steps**:
1. Read the module-level convenience functions (lines ~887+)
2. Add `session=None` parameter to each wrapper:
   ```python
   def create_finished_unit(display_name: str, recipe_id: int = None, session=None, **kwargs):
       return FinishedUnitService.create_finished_unit(display_name, recipe_id=recipe_id, session=session, **kwargs)
   ```
3. Repeat for `update_finished_unit` and `delete_finished_unit` wrappers
4. Verify no other module-level functions need the session parameter

**Files**: `src/services/finished_unit_service.py`
**Parallel?**: No (depends on T001-T003 being done)
**Notes**: Check if `recipe_id` is positional or keyword in the wrapper. Match the class method signature.

### Subtask T005 - Write tests: session parameter respected

**Purpose**: Verify that when a session is passed, the service uses it (no new `session_scope()` created).

**Steps**:
1. Find or create test file `src/tests/test_finished_unit_service.py`
2. Write tests that pass a session and verify operations happen within it:
   ```python
   def test_create_finished_unit_with_session():
       with session_scope() as session:
           fu = create_finished_unit("Test Unit", recipe_id=recipe.id, session=session)
           # Verify FU exists in same session
           found = session.query(FinishedUnit).filter_by(id=fu.id).first()
           assert found is not None
           assert found.display_name == "Test Unit"
   ```
3. Write similar tests for update and delete with passed session
4. Verify that objects remain attached to the passed session (not detached)

**Files**: `src/tests/test_finished_unit_service.py`
**Parallel?**: No (depends on T001-T004)

### Subtask T006 - Verify backward compatibility

**Purpose**: All existing tests must pass with zero changes, confirming `session=None` default preserves current behavior.

**Steps**:
1. Run full existing test suite: `./run-tests.sh src/tests/ -v -k "finished_unit"`
2. If any tests fail, investigate — the refactor should be purely additive
3. Run broader test suite to check for unintended side effects: `./run-tests.sh -v`
4. Document test results

**Files**: No file changes — validation only
**Parallel?**: No (depends on T001-T004)

## Test Strategy

- **Backward compatibility**: Run existing test suite unchanged — must pass
- **Session parameter**: New tests verify session is respected when provided
- **Test command**: `./run-tests.sh src/tests/ -v -k "finished_unit"`
- **Full suite**: `./run-tests.sh -v` to verify no regressions

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Breaking existing callers | `session=None` default ensures backward compatibility |
| Helper methods need session | Check `_generate_unique_slug()` and `_validate_name_unique_in_recipe()` — pass session if they query DB |
| Static method limitations | Follow same `@staticmethod` + `_impl` pattern as `finished_good_service.py` |

## Definition of Done Checklist

- [ ] All three CRUD methods accept `session: Optional[Session] = None`
- [ ] `_impl` pattern extracted for each method
- [ ] Module-level convenience functions forward `session`
- [ ] New tests verify session parameter behavior
- [ ] All existing tests pass without modification
- [ ] Full test suite passes (no regressions)

## Review Guidance

- Verify `_impl` pattern matches `finished_good_service.py` style
- Verify backward compatibility: `session=None` path is identical to original behavior
- Check that helper methods (slug generation, validation) receive session when they query DB
- Ensure no `session_scope()` is created when a session is already provided

## Activity Log

- 2026-02-08T17:14:59Z - system - lane=planned - Prompt created.
- 2026-02-08T17:23:22Z – claude-opus – shell_pid=40598 – lane=doing – Assigned agent via workflow command
- 2026-02-08T17:46:16Z – claude-opus – shell_pid=40598 – lane=for_review – Ready for review: Added session=None to create/update/delete, _impl pattern, 12 new tests, 3575 pass
