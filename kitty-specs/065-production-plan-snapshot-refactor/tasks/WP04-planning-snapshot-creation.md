---
work_package_id: WP04
title: Planning Service Snapshot Creation
lane: "done"
dependencies:
- WP02
base_branch: 065-production-plan-snapshot-refactor-WP03
base_commit: a8bf5582287439f5e53e02cf83b5d48cb9ccdfbb
created_at: '2026-01-24T21:24:41.256932+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
- T020
phase: Phase 2 - Service Layer - Snapshot Creation
assignee: ''
agent: "claude-opus"
shell_pid: "85459"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-24T19:47:15Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Planning Service Snapshot Creation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Implementation Command

```bash
# Depends on WP02 (FK fields) and WP03 (recipe snapshot service)
spec-kitty implement WP04 --base WP03 --feature 065-production-plan-snapshot-refactor
```

---

## Objectives & Success Criteria

Update planning service to create and link snapshots when a plan is finalized.

**Success Criteria**:
- [ ] create_plan() function creates RecipeSnapshot for each production target
- [ ] create_plan() function creates FinishedGoodSnapshot for each assembly target
- [ ] Snapshots linked to targets (recipe_snapshot_id, finished_good_snapshot_id set)
- [ ] All snapshot creation in single atomic transaction
- [ ] Session passed through all nested service calls
- [ ] Plan creation succeeds end-to-end

## Context & Constraints

**Reference Documents**:
- `kitty-specs/065-production-plan-snapshot-refactor/research.md` - RQ-3 (planning service workflow)
- `kitty-specs/065-production-plan-snapshot-refactor/plan.md` - Implementation Phases, Session Management
- `.kittify/memory/constitution.md` - Principle VIII (Session Management)
- `CLAUDE.md` - Session Management section (CRITICAL - read before implementing!)

**Target Workflow** (from research.md):
1. Validate event and output_mode
2. For each production target: create RecipeSnapshot, link to target
3. For each assembly target: create FinishedGoodSnapshot, link to target
4. Create ProductionPlanSnapshot as container (no calculation_results)
5. Return success indicator

**Key Constraints**:
- MUST pass session to all nested service calls
- MUST use single transaction (atomic snapshot creation)
- MUST handle failure gracefully (rollback all on error)

## Subtasks & Detailed Guidance

### Subtask T014 – Refactor calculate_plan() to create_plan() entry point

**Purpose**: Rename/refactor the main entry point to reflect its new role: creating snapshots, not caching calculations.

**Steps**:
1. Open `src/services/planning/planning_service.py`
2. Create new function `create_plan()` (or rename calculate_plan):
   ```python
   def create_plan(
       event_id: int,
       force_recreate: bool = False,
       session=None
   ) -> dict:
       """Create production plan with immutable snapshots.

       Creates RecipeSnapshot for each production target and
       FinishedGoodSnapshot for each assembly target. Links
       snapshots to targets for use during production/assembly.

       Args:
           event_id: Event to create plan for
           force_recreate: If True, create new plan even if one exists
           session: Optional session for transaction management

       Returns:
           dict with planning_snapshot_id, snapshot counts, etc.
       """
       if session is not None:
           return _create_plan_impl(event_id, force_recreate, session)
       with session_scope() as session:
           return _create_plan_impl(event_id, force_recreate, session)
   ```

3. Keep calculate_plan() as deprecated alias if needed for backward compatibility:
   ```python
   def calculate_plan(event_id, force_recalculate=False, session=None):
       """Deprecated: Use create_plan() instead."""
       import warnings
       warnings.warn("calculate_plan() is deprecated, use create_plan()", DeprecationWarning)
       return create_plan(event_id, force_recalculate, session)
   ```

**Files**:
- `src/services/planning/planning_service.py` (modify)

**Parallel?**: No - foundation for T015-T020

---

### Subtask T015 – Create RecipeSnapshot for each production target

**Purpose**: When creating a plan, snapshot each recipe so production uses immutable definitions.

**Steps**:
1. In _create_plan_impl(), iterate over production targets:
   ```python
   def _create_plan_impl(event_id: int, force_recreate: bool, session) -> dict:
       event = session.get(Event, event_id)
       if not event:
           raise ValueError(f"Event {event_id} not found")

       # Create snapshots for production targets
       recipe_snapshots_created = 0
       for target in event.production_targets:
           # Skip if already has snapshot (unless force_recreate)
           if target.recipe_snapshot_id and not force_recreate:
               continue

           # Create recipe snapshot (planning context)
           snapshot = recipe_snapshot_service.create_recipe_snapshot(
               recipe_id=target.recipe_id,
               scale_factor=1.0,  # Base scale; target has quantity
               production_run_id=None,  # Planning context
               session=session  # CRITICAL: pass session!
           )
           target.recipe_snapshot_id = snapshot["id"]
           recipe_snapshots_created += 1
   ```

2. Note: session is passed to create_recipe_snapshot() for atomicity

**Files**:
- `src/services/planning/planning_service.py` (modify)

**Parallel?**: Yes - can be developed alongside T016

---

### Subtask T016 – Create FinishedGoodSnapshot for each assembly target

**Purpose**: When creating a plan, snapshot each finished good so assembly uses immutable definitions.

**Steps**:
1. Continue in _create_plan_impl(), iterate over assembly targets:
   ```python
       # Create snapshots for assembly targets
       fg_snapshots_created = 0
       for target in event.assembly_targets:
           # Skip if already has snapshot (unless force_recreate)
           if target.finished_good_snapshot_id and not force_recreate:
               continue

           # Create finished good snapshot (planning context)
           # Note: verify F064 service signature
           snapshot = finished_good_service.create_finished_good_snapshot(
               finished_good_id=target.finished_good_id,
               recursive=True,  # Include component snapshots
               assembly_run_id=None,  # Planning context
               session=session  # CRITICAL: pass session!
           )
           target.finished_good_snapshot_id = snapshot["id"]
           fg_snapshots_created += 1
   ```

2. Verify finished_good_service signature matches (F064)

**Files**:
- `src/services/planning/planning_service.py` (modify)

**Parallel?**: Yes - can be developed alongside T015

**Notes**: The F064 implementation should have create_finished_good_snapshot(). Verify exact signature.

---

### Subtask T017 – Link recipe snapshots to targets

**Purpose**: Set recipe_snapshot_id on EventProductionTarget after creating snapshot.

**Steps**:
1. This is done in T015 with:
   ```python
   target.recipe_snapshot_id = snapshot["id"]
   ```

2. Verify the assignment persists (session tracking):
   - target is loaded via session
   - assignment modifies ORM object
   - session.flush() or commit captures change

3. Add explicit flush if needed:
   ```python
   session.flush()  # Ensure FKs are set before continuing
   ```

**Files**:
- `src/services/planning/planning_service.py` (verify in T015)

**Parallel?**: Yes - part of T015/T016 implementation

---

### Subtask T018 – Link finished good snapshots to targets

**Purpose**: Set finished_good_snapshot_id on EventAssemblyTarget after creating snapshot.

**Steps**:
1. This is done in T016 with:
   ```python
   target.finished_good_snapshot_id = snapshot["id"]
   ```

2. Same session tracking considerations as T017

**Files**:
- `src/services/planning/planning_service.py` (verify in T016)

**Parallel?**: Yes - part of T015/T016 implementation

---

### Subtask T019 – Ensure atomic transaction for all snapshots

**Purpose**: If any snapshot creation fails, all changes must roll back.

**Steps**:
1. Wrap snapshot creation in try/except:
   ```python
   def _create_plan_impl(event_id: int, force_recreate: bool, session) -> dict:
       event = session.get(Event, event_id)
       if not event:
           raise ValueError(f"Event {event_id} not found")

       try:
           # Create production target snapshots
           recipe_snapshots_created = 0
           for target in event.production_targets:
               if target.recipe_snapshot_id and not force_recreate:
                   continue
               snapshot = recipe_snapshot_service.create_recipe_snapshot(
                   recipe_id=target.recipe_id,
                   production_run_id=None,
                   session=session
               )
               target.recipe_snapshot_id = snapshot["id"]
               recipe_snapshots_created += 1

           # Create assembly target snapshots
           fg_snapshots_created = 0
           for target in event.assembly_targets:
               if target.finished_good_snapshot_id and not force_recreate:
                   continue
               snapshot = finished_good_service.create_finished_good_snapshot(
                   finished_good_id=target.finished_good_id,
                   recursive=True,
                   assembly_run_id=None,
                   session=session
               )
               target.finished_good_snapshot_id = snapshot["id"]
               fg_snapshots_created += 1

           # Create lightweight ProductionPlanSnapshot container
           plan_snapshot = ProductionPlanSnapshot(
               event_id=event_id,
               calculated_at=datetime.utcnow()
           )
           session.add(plan_snapshot)
           session.flush()

           return {
               "success": True,
               "planning_snapshot_id": plan_snapshot.id,
               "recipe_snapshots_created": recipe_snapshots_created,
               "finished_good_snapshots_created": fg_snapshots_created
           }

       except Exception as e:
           # Session rollback handled by session_scope context manager
           raise RuntimeError(f"Plan creation failed: {e}") from e
   ```

2. Note: session_scope() context manager handles rollback on exception

**Files**:
- `src/services/planning/planning_service.py` (modify)

**Parallel?**: No - integrates T015-T018

---

### Subtask T020 – Session management compliance

**Purpose**: Verify all nested service calls receive session parameter.

**Steps**:
1. Audit all service calls in _create_plan_impl():
   - `recipe_snapshot_service.create_recipe_snapshot(..., session=session)` ✓
   - `finished_good_service.create_finished_good_snapshot(..., session=session)` ✓

2. Verify no new session_scope() calls inside _create_plan_impl()

3. Add comment documenting session flow:
   ```python
   def _create_plan_impl(event_id: int, force_recreate: bool, session) -> dict:
       """Implementation of create_plan.

       Session Management:
           This function receives a session from create_plan() and passes it
           to all nested service calls. This ensures:
           1. All changes are in single transaction (atomic)
           2. ORM objects remain attached (no detachment bugs)
           3. Caller controls commit/rollback

       All service calls MUST include session=session parameter.
       """
   ```

4. Run session management checklist:
   - [ ] No nested session_scope() calls
   - [ ] All service calls include session=session
   - [ ] ORM objects modified within same session context
   - [ ] session.flush() called to get IDs before return

**Files**:
- `src/services/planning/planning_service.py` (audit)

**Parallel?**: No - final verification

---

## Test Strategy

**Unit Tests**:
```python
def test_create_plan_creates_recipe_snapshots(db_session):
    """Test that create_plan creates RecipeSnapshot for each production target."""
    # Setup: event with production targets
    event = create_test_event_with_targets(db_session)

    # Act
    result = create_plan(event.id, session=db_session)

    # Assert
    assert result["success"]
    assert result["recipe_snapshots_created"] > 0
    for target in event.production_targets:
        assert target.recipe_snapshot_id is not None

def test_create_plan_creates_fg_snapshots(db_session):
    """Test that create_plan creates FinishedGoodSnapshot for each assembly target."""
    # Similar pattern

def test_create_plan_atomic_rollback(db_session):
    """Test that failure rolls back all snapshots."""
    # Setup: event with invalid recipe reference
    # Act: attempt create_plan
    # Assert: no partial snapshots created
```

**Run Tests**:
```bash
./run-tests.sh src/tests/unit/test_planning_service.py -v
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| F064 service signature mismatch | Verify create_finished_good_snapshot() params |
| Session detachment | Strict session=session passing |
| Partial snapshot creation | Atomic transaction with rollback |
| Performance (many snapshots) | Batch operations if needed |

## Definition of Done Checklist

- [ ] create_plan() function implemented
- [ ] RecipeSnapshot created for each production target
- [ ] FinishedGoodSnapshot created for each assembly target
- [ ] Targets linked to snapshots (FK values set)
- [ ] All operations in single atomic transaction
- [ ] Session passed to all nested service calls
- [ ] Unit tests pass
- [ ] Activity log entry added

## Review Guidance

Reviewers should verify:
1. Session management follows CLAUDE.md exactly
2. All service calls include session=session
3. No nested session_scope() calls
4. Atomic transaction (rollback on failure)
5. Return structure matches expected format

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-24T19:47:15Z – system – lane=planned – Prompt created.
- 2026-01-24T21:34:21Z – unknown – shell_pid=83183 – lane=for_review – Ready for review: create_plan() creates RecipeSnapshot and FinishedGoodSnapshot for targets, links via FKs, uses atomic transaction with proper session management. 37 passed, 7 skipped (deprecated), 36 warnings.
- 2026-01-24T21:39:08Z – claude-opus – shell_pid=85459 – lane=doing – Started review via workflow command
- 2026-01-24T21:40:36Z – claude-opus – shell_pid=85459 – lane=done – Review passed: create_plan() correctly creates RecipeSnapshot/FinishedGoodSnapshot for targets, links via FKs, uses atomic transaction with proper session=session passing. 37 tests pass, 7 correctly skipped (WP01 removed fields). All success criteria met.
