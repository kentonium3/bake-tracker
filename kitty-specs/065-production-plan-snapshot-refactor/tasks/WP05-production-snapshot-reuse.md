---
work_package_id: "WP05"
subtasks:
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "Production Service Snapshot Reuse"
phase: "Phase 3 - Service Layer - Snapshot Reuse"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP02"]
history:
  - timestamp: "2026-01-24T19:47:15Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Production Service Snapshot Reuse

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
# Depends on WP02 (recipe_snapshot_id FK on target)
# Can run in parallel with WP06
spec-kitty implement WP05 --base WP02
```

---

## Objectives & Success Criteria

Update batch_production_service to reuse planning snapshots instead of always creating new ones.

**Success Criteria**:
- [ ] Production for planned event reuses target's recipe_snapshot_id
- [ ] Legacy/ad-hoc production creates new snapshot (backward compatibility)
- [ ] Production run references correct snapshot (planning or new)
- [ ] Unit tests verify both scenarios

## Context & Constraints

**Reference Documents**:
- `kitty-specs/065-production-plan-snapshot-refactor/research.md` - RQ-4 (snapshot reuse pattern)
- `kitty-specs/065-production-plan-snapshot-refactor/plan.md` - Phase 3 details

**Target Pattern** (from research.md):
```python
def record_batch_production(recipe_id, quantity, event_id=None, session=None):
    # Check if production is for a planned event target
    snapshot_id = None
    if event_id:
        target = get_production_target(event_id, recipe_id, session)
        if target and target.recipe_snapshot_id:
            # Use snapshot created during planning
            snapshot_id = target.recipe_snapshot_id

    # If no planning snapshot, create one now (backward compatibility)
    if not snapshot_id:
        # ... create new snapshot
```

**Key Constraints**:
- Maintain backward compatibility (legacy production still works)
- Match on (event_id, recipe_id) to find correct target
- Follow existing session management patterns

## Subtasks & Detailed Guidance

### Subtask T021 – Add/verify event_id parameter in record_batch_production()

**Purpose**: To check for planning snapshots, we need to know which event (if any) this production is for.

**Steps**:
1. Open `src/services/batch_production_service.py`
2. Find record_batch_production() function signature
3. Verify or add event_id parameter:
   ```python
   def record_batch_production(
       recipe_id: int,
       quantity: int,
       batch_number: str = None,
       event_id: int = None,  # Optional: for planned production
       session=None
   ) -> dict:
       """Record a production run.

       Args:
           recipe_id: Recipe being produced
           quantity: Number of batches produced
           batch_number: Optional batch identifier
           event_id: Optional event ID (for planned production, enables snapshot reuse)
           session: Optional session for transaction management
       """
   ```

4. If event_id already exists, verify it's optional with default None

**Files**:
- `src/services/batch_production_service.py` (modify)

**Parallel?**: No - foundation for T022, T023

---

### Subtask T022 – Query EventProductionTarget for recipe_snapshot_id

**Purpose**: When event_id is provided, check if the target already has a planning snapshot.

**Steps**:
1. In the implementation, add target lookup:
   ```python
   def _record_batch_production_impl(
       recipe_id: int,
       quantity: int,
       batch_number: str,
       event_id: int,
       session
   ) -> dict:
       # Check for existing planning snapshot
       planning_snapshot_id = None
       if event_id:
           target = session.query(EventProductionTarget).filter(
               EventProductionTarget.event_id == event_id,
               EventProductionTarget.recipe_id == recipe_id
           ).first()

           if target and target.recipe_snapshot_id:
               planning_snapshot_id = target.recipe_snapshot_id
   ```

2. Import EventProductionTarget if needed:
   ```python
   from src.models.event import EventProductionTarget
   ```

**Files**:
- `src/services/batch_production_service.py` (modify)

**Parallel?**: No - builds on T021

---

### Subtask T023 – Implement reuse logic: use existing or create new

**Purpose**: Use planning snapshot if available, otherwise create new (backward compatibility).

**Steps**:
1. Continue the implementation:
   ```python
       # Determine which snapshot to use
       if planning_snapshot_id:
           # Reuse snapshot from planning
           recipe_snapshot_id = planning_snapshot_id
       else:
           # Create new snapshot (legacy/ad-hoc production)
           # First create the production run to get ID
           production_run = ProductionRun(
               recipe_id=recipe_id,
               quantity=quantity,
               batch_number=batch_number,
               event_id=event_id,
               produced_at=datetime.utcnow()
           )
           session.add(production_run)
           session.flush()  # Get production_run.id

           # Create snapshot with production_run context
           snapshot = recipe_snapshot_service.create_recipe_snapshot(
               recipe_id=recipe_id,
               scale_factor=1.0,
               production_run_id=production_run.id,
               session=session
           )
           recipe_snapshot_id = snapshot["id"]

       # If we reused planning snapshot, still need to create production run
       if planning_snapshot_id:
           production_run = ProductionRun(
               recipe_id=recipe_id,
               quantity=quantity,
               batch_number=batch_number,
               event_id=event_id,
               recipe_snapshot_id=recipe_snapshot_id,  # Link to planning snapshot
               produced_at=datetime.utcnow()
           )
           session.add(production_run)
           session.flush()

       return {
           "production_run_id": production_run.id,
           "recipe_snapshot_id": recipe_snapshot_id,
           "snapshot_reused": planning_snapshot_id is not None
       }
   ```

2. Note the key difference:
   - Planning snapshot: Create ProductionRun with existing recipe_snapshot_id
   - New snapshot: Create ProductionRun first, then create snapshot with production_run_id

**Files**:
- `src/services/batch_production_service.py` (modify)

**Parallel?**: No - builds on T022

**Notes**: The "snapshot_reused" flag in return helps with testing/verification.

---

### Subtask T024 – Unit tests for production snapshot reuse

**Purpose**: Verify snapshot reuse works for planned production and new snapshots work for legacy.

**Steps**:
1. Create/update test file: `src/tests/unit/test_batch_production_service.py`

2. Test snapshot reuse (planned production):
   ```python
   def test_production_reuses_planning_snapshot(db_session):
       """Production for planned event should reuse existing snapshot."""
       # Setup: event with target that has recipe_snapshot_id
       event = create_test_event(db_session)
       recipe = create_test_recipe(db_session)
       target = EventProductionTarget(
           event_id=event.id,
           recipe_id=recipe.id,
           target_batches=5
       )
       db_session.add(target)

       # Create planning snapshot
       planning_snapshot = recipe_snapshot_service.create_recipe_snapshot(
           recipe_id=recipe.id,
           production_run_id=None,
           session=db_session
       )
       target.recipe_snapshot_id = planning_snapshot["id"]
       db_session.flush()

       # Act: record production for this event
       result = record_batch_production(
           recipe_id=recipe.id,
           quantity=3,
           event_id=event.id,
           session=db_session
       )

       # Assert: should reuse planning snapshot
       assert result["recipe_snapshot_id"] == planning_snapshot["id"]
       assert result["snapshot_reused"] == True
   ```

3. Test new snapshot (legacy/ad-hoc):
   ```python
   def test_production_creates_new_snapshot_when_no_plan(db_session):
       """Production without plan should create new snapshot."""
       recipe = create_test_recipe(db_session)

       # Act: record production without event_id
       result = record_batch_production(
           recipe_id=recipe.id,
           quantity=2,
           event_id=None,  # No event
           session=db_session
       )

       # Assert: new snapshot created
       assert result["recipe_snapshot_id"] is not None
       assert result["snapshot_reused"] == False
   ```

4. Test backward compatibility (event without snapshot):
   ```python
   def test_production_creates_snapshot_for_legacy_event(db_session):
       """Production for event without planning snapshot creates new."""
       event = create_test_event(db_session)
       recipe = create_test_recipe(db_session)
       target = EventProductionTarget(
           event_id=event.id,
           recipe_id=recipe.id,
           target_batches=5,
           recipe_snapshot_id=None  # Legacy: no planning snapshot
       )
       db_session.add(target)
       db_session.flush()

       # Act: record production
       result = record_batch_production(
           recipe_id=recipe.id,
           quantity=3,
           event_id=event.id,
           session=db_session
       )

       # Assert: new snapshot created (backward compatibility)
       assert result["snapshot_reused"] == False
   ```

**Files**:
- `src/tests/unit/test_batch_production_service.py` (create or modify)

**Parallel?**: No - requires T021-T023 complete

---

## Test Strategy

**Run Tests**:
```bash
./run-tests.sh src/tests/unit/test_batch_production_service.py -v
```

**Coverage Target**: >70% for batch_production_service.py

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Wrong target found | Query filters on both event_id AND recipe_id |
| Snapshot FK not set on ProductionRun | Verify model has recipe_snapshot_id field |
| Circular import | Use late import if needed |

## Definition of Done Checklist

- [ ] event_id parameter available in record_batch_production()
- [ ] Target lookup implemented for snapshot reuse
- [ ] Planning snapshot reused when available
- [ ] New snapshot created for legacy/ad-hoc production
- [ ] Return includes "snapshot_reused" indicator
- [ ] Unit tests pass for all scenarios
- [ ] Activity log entry added

## Review Guidance

Reviewers should verify:
1. Target lookup uses correct filters (event_id, recipe_id)
2. Snapshot reuse is correct (same ID, not new)
3. Backward compatibility maintained
4. Session management correct

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-24T19:47:15Z – system – lane=planned – Prompt created.
