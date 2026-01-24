---
work_package_id: "WP06"
subtasks:
  - "T025"
  - "T026"
  - "T027"
  - "T028"
title: "Assembly Service Snapshot Reuse"
phase: "Phase 3 - Service Layer - Snapshot Reuse"
lane: "for_review"
assignee: ""
agent: "claude-opus"
shell_pid: "88485"
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

# Work Package Prompt: WP06 – Assembly Service Snapshot Reuse

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
# Depends on WP02 (finished_good_snapshot_id FK on target)
# Can run in parallel with WP05
spec-kitty implement WP06 --base WP02 --feature 065-production-plan-snapshot-refactor
```

---

## Objectives & Success Criteria

Update assembly_service to reuse planning snapshots instead of always creating new ones.

**Success Criteria**:
- [ ] Assembly for planned event reuses target's finished_good_snapshot_id
- [ ] Legacy/ad-hoc assembly creates new snapshot (backward compatibility)
- [ ] Assembly run references correct snapshot (planning or new)
- [ ] Unit tests verify both scenarios

## Context & Constraints

**Reference Documents**:
- `kitty-specs/065-production-plan-snapshot-refactor/research.md` - RQ-4 (snapshot reuse pattern)
- `kitty-specs/065-production-plan-snapshot-refactor/plan.md` - Phase 3 details

**Pattern**: Mirror WP05 (production reuse) for assembly context.

**Key Constraints**:
- Maintain backward compatibility (legacy assembly still works)
- Match on (event_id, finished_good_id) to find correct target
- Follow F064 patterns for FinishedGoodSnapshot creation

## Subtasks & Detailed Guidance

### Subtask T025 – Add/verify event_id parameter in record_assembly()

**Purpose**: To check for planning snapshots, we need to know which event (if any) this assembly is for.

**Steps**:
1. Open `src/services/assembly_service.py`
2. Find record_assembly() function signature
3. Verify or add event_id parameter:
   ```python
   def record_assembly(
       finished_good_id: int,
       quantity: int,
       event_id: int = None,  # Optional: for planned assembly
       session=None
   ) -> dict:
       """Record an assembly run.

       Args:
           finished_good_id: Finished good being assembled
           quantity: Number assembled
           event_id: Optional event ID (for planned assembly, enables snapshot reuse)
           session: Optional session for transaction management
       """
   ```

4. If event_id already exists, verify it's optional with default None

**Files**:
- `src/services/assembly_service.py` (modify)

**Parallel?**: No - foundation for T026, T027

---

### Subtask T026 – Query EventAssemblyTarget for finished_good_snapshot_id

**Purpose**: When event_id is provided, check if the target already has a planning snapshot.

**Steps**:
1. In the implementation, add target lookup:
   ```python
   def _record_assembly_impl(
       finished_good_id: int,
       quantity: int,
       event_id: int,
       session
   ) -> dict:
       # Check for existing planning snapshot
       planning_snapshot_id = None
       if event_id:
           target = session.query(EventAssemblyTarget).filter(
               EventAssemblyTarget.event_id == event_id,
               EventAssemblyTarget.finished_good_id == finished_good_id
           ).first()

           if target and target.finished_good_snapshot_id:
               planning_snapshot_id = target.finished_good_snapshot_id
   ```

2. Import EventAssemblyTarget if needed:
   ```python
   from src.models.event import EventAssemblyTarget
   ```

**Files**:
- `src/services/assembly_service.py` (modify)

**Parallel?**: No - builds on T025

---

### Subtask T027 – Implement reuse logic: use existing or create new

**Purpose**: Use planning snapshot if available, otherwise create new (backward compatibility).

**Steps**:
1. Continue the implementation:
   ```python
       # Determine which snapshot to use
       if planning_snapshot_id:
           # Reuse snapshot from planning
           fg_snapshot_id = planning_snapshot_id
       else:
           # Create new snapshot (legacy/ad-hoc assembly)
           # First create the assembly run to get ID
           assembly_run = AssemblyRun(
               finished_good_id=finished_good_id,
               quantity=quantity,
               event_id=event_id,
               assembled_at=datetime.utcnow()
           )
           session.add(assembly_run)
           session.flush()  # Get assembly_run.id

           # Create snapshot with assembly_run context (F064 pattern)
           snapshot = finished_good_service.create_finished_good_snapshot(
               finished_good_id=finished_good_id,
               recursive=True,
               assembly_run_id=assembly_run.id,
               session=session
           )
           fg_snapshot_id = snapshot["id"]

       # If we reused planning snapshot, still need to create assembly run
       if planning_snapshot_id:
           assembly_run = AssemblyRun(
               finished_good_id=finished_good_id,
               quantity=quantity,
               event_id=event_id,
               finished_good_snapshot_id=fg_snapshot_id,  # Link to planning snapshot
               assembled_at=datetime.utcnow()
           )
           session.add(assembly_run)
           session.flush()

       return {
           "assembly_run_id": assembly_run.id,
           "finished_good_snapshot_id": fg_snapshot_id,
           "snapshot_reused": planning_snapshot_id is not None
       }
   ```

2. Note: Mirror of WP05 pattern, adapted for assembly context

**Files**:
- `src/services/assembly_service.py` (modify)

**Parallel?**: No - builds on T026

**Notes**:
- F064 established create_finished_good_snapshot() pattern
- Verify exact signature matches what F064 implemented
- The "snapshot_reused" flag helps with testing

---

### Subtask T028 – Unit tests for assembly snapshot reuse

**Purpose**: Verify snapshot reuse works for planned assembly and new snapshots work for legacy.

**Steps**:
1. Create/update test file: `src/tests/unit/test_assembly_service.py`

2. Test snapshot reuse (planned assembly):
   ```python
   def test_assembly_reuses_planning_snapshot(db_session):
       """Assembly for planned event should reuse existing snapshot."""
       # Setup: event with target that has finished_good_snapshot_id
       event = create_test_event(db_session)
       fg = create_test_finished_good(db_session)
       target = EventAssemblyTarget(
           event_id=event.id,
           finished_good_id=fg.id,
           target_quantity=10
       )
       db_session.add(target)

       # Create planning snapshot (F064 pattern)
       planning_snapshot = finished_good_service.create_finished_good_snapshot(
           finished_good_id=fg.id,
           recursive=True,
           assembly_run_id=None,  # Planning context
           session=db_session
       )
       target.finished_good_snapshot_id = planning_snapshot["id"]
       db_session.flush()

       # Act: record assembly for this event
       result = record_assembly(
           finished_good_id=fg.id,
           quantity=5,
           event_id=event.id,
           session=db_session
       )

       # Assert: should reuse planning snapshot
       assert result["finished_good_snapshot_id"] == planning_snapshot["id"]
       assert result["snapshot_reused"] == True
   ```

3. Test new snapshot (legacy/ad-hoc):
   ```python
   def test_assembly_creates_new_snapshot_when_no_plan(db_session):
       """Assembly without plan should create new snapshot."""
       fg = create_test_finished_good(db_session)

       # Act: record assembly without event_id
       result = record_assembly(
           finished_good_id=fg.id,
           quantity=3,
           event_id=None,  # No event
           session=db_session
       )

       # Assert: new snapshot created
       assert result["finished_good_snapshot_id"] is not None
       assert result["snapshot_reused"] == False
   ```

4. Test backward compatibility (event without snapshot):
   ```python
   def test_assembly_creates_snapshot_for_legacy_event(db_session):
       """Assembly for event without planning snapshot creates new."""
       event = create_test_event(db_session)
       fg = create_test_finished_good(db_session)
       target = EventAssemblyTarget(
           event_id=event.id,
           finished_good_id=fg.id,
           target_quantity=10,
           finished_good_snapshot_id=None  # Legacy: no planning snapshot
       )
       db_session.add(target)
       db_session.flush()

       # Act: record assembly
       result = record_assembly(
           finished_good_id=fg.id,
           quantity=5,
           event_id=event.id,
           session=db_session
       )

       # Assert: new snapshot created (backward compatibility)
       assert result["snapshot_reused"] == False
   ```

**Files**:
- `src/tests/unit/test_assembly_service.py` (create or modify)

**Parallel?**: No - requires T025-T027 complete

---

## Test Strategy

**Run Tests**:
```bash
./run-tests.sh src/tests/unit/test_assembly_service.py -v
```

**Coverage Target**: >70% for assembly_service.py

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Wrong target found | Query filters on both event_id AND finished_good_id |
| F064 service signature different | Verify exact signature before implementing |
| Snapshot FK not set on AssemblyRun | Verify model has finished_good_snapshot_id field |

## Definition of Done Checklist

- [ ] event_id parameter available in record_assembly()
- [ ] Target lookup implemented for snapshot reuse
- [ ] Planning snapshot reused when available
- [ ] New snapshot created for legacy/ad-hoc assembly
- [ ] Return includes "snapshot_reused" indicator
- [ ] Unit tests pass for all scenarios
- [ ] Activity log entry added

## Review Guidance

Reviewers should verify:
1. Pattern matches WP05 (production reuse) for consistency
2. Target lookup uses correct filters (event_id, finished_good_id)
3. F064 service integration correct
4. Backward compatibility maintained

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-24T19:47:15Z – system – lane=planned – Prompt created.
- 2026-01-24T21:57:57Z – claude-opus – shell_pid=88485 – lane=doing – Started implementation via workflow command
- 2026-01-24T22:02:19Z – claude-opus – shell_pid=88485 – lane=for_review – Ready for review: Assembly snapshot reuse implemented. Added finished_good_snapshot_id FK to AssemblyRun. When event_id provided, checks EventAssemblyTarget for snapshot. 40 tests pass, 4 new F065 tests.
