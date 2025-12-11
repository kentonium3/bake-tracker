---
work_package_id: "WP03"
subtasks:
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
title: "Service Layer - Target CRUD"
phase: "Phase 2 - Service Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Service Layer - Target CRUD

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Implement EventService methods for creating, reading, updating, and deleting production/assembly targets.

**Success Criteria**:
- `set_production_target()` creates new or updates existing target
- `set_assembly_target()` creates new or updates existing target
- `get_production_targets()` returns all targets for an event with eager-loaded relationships
- `get_assembly_targets()` returns all targets for an event with eager-loaded relationships
- `delete_production_target()` removes target, returns True if deleted
- `delete_assembly_target()` removes target, returns True if deleted
- Target values validated (> 0)
- Unit tests cover all operations and edge cases

## Context & Constraints

**Reference Documents**:
- `kitty-specs/016-event-centric-production/spec.md` - FR-013, FR-014, FR-021, FR-022
- `kitty-specs/016-event-centric-production/contracts/event-service-contracts.md` - Full method signatures
- `kitty-specs/016-event-centric-production/data-model.md` - Entity specifications

**Existing Code**:
- `src/services/event_service.py` - Add new methods here

**Constraints**:
- Follow existing EventService patterns
- Eager load recipe/finished_good relationships
- Validate target values > 0
- Handle upsert pattern (create or update)

**Dependencies**: WP01 must be complete (target models exist)

---

## Subtasks & Detailed Guidance

### Subtask T014 - Implement EventService.set_production_target()

**Purpose**: Create or update production target for a recipe in an event.

**Steps**:
1. Open `src/services/event_service.py`
2. Add method:
   ```python
   def set_production_target(
       self,
       event_id: int,
       recipe_id: int,
       target_batches: int,
       notes: Optional[str] = None,
       session: Optional[Session] = None
   ) -> EventProductionTarget:
       """Create or update production target for a recipe in an event."""
       if target_batches <= 0:
           raise ValueError("target_batches must be positive")

       with self._get_session(session) as sess:
           # Check if target already exists
           existing = sess.query(EventProductionTarget).filter_by(
               event_id=event_id,
               recipe_id=recipe_id
           ).first()

           if existing:
               existing.target_batches = target_batches
               existing.notes = notes
               sess.commit()
               return existing
           else:
               target = EventProductionTarget(
                   event_id=event_id,
                   recipe_id=recipe_id,
                   target_batches=target_batches,
                   notes=notes
               )
               sess.add(target)
               sess.commit()
               return target
   ```
3. Add import: `from src.models import EventProductionTarget`

**Files**: `src/services/event_service.py`
**Parallel?**: No (foundational)
**Notes**: Use existing session management pattern from EventService.

---

### Subtask T015 - Implement EventService.set_assembly_target()

**Purpose**: Create or update assembly target for a finished good in an event.

**Steps**:
1. Add method following same pattern as T014:
   ```python
   def set_assembly_target(
       self,
       event_id: int,
       finished_good_id: int,
       target_quantity: int,
       notes: Optional[str] = None,
       session: Optional[Session] = None
   ) -> EventAssemblyTarget:
       """Create or update assembly target for a finished good in an event."""
       if target_quantity <= 0:
           raise ValueError("target_quantity must be positive")

       with self._get_session(session) as sess:
           existing = sess.query(EventAssemblyTarget).filter_by(
               event_id=event_id,
               finished_good_id=finished_good_id
           ).first()

           if existing:
               existing.target_quantity = target_quantity
               existing.notes = notes
               sess.commit()
               return existing
           else:
               target = EventAssemblyTarget(
                   event_id=event_id,
                   finished_good_id=finished_good_id,
                   target_quantity=target_quantity,
                   notes=notes
               )
               sess.add(target)
               sess.commit()
               return target
   ```
2. Add import: `from src.models import EventAssemblyTarget`

**Files**: `src/services/event_service.py`
**Parallel?**: Yes (can proceed with T014)
**Notes**: Mirror structure of set_production_target.

---

### Subtask T016 - Implement EventService.get_production_targets()

**Purpose**: Retrieve all production targets for an event with recipe data.

**Steps**:
1. Add method:
   ```python
   def get_production_targets(
       self,
       event_id: int,
       session: Optional[Session] = None
   ) -> List[EventProductionTarget]:
       """Get all production targets for an event."""
       with self._get_session(session) as sess:
           return sess.query(EventProductionTarget).options(
               joinedload(EventProductionTarget.recipe)
           ).filter_by(event_id=event_id).all()
   ```
2. Add import: `from sqlalchemy.orm import joinedload`

**Files**: `src/services/event_service.py`
**Parallel?**: No
**Notes**: Eager load recipe to avoid N+1 queries in UI.

---

### Subtask T017 - Implement EventService.get_assembly_targets()

**Purpose**: Retrieve all assembly targets for an event with finished good data.

**Steps**:
1. Add method:
   ```python
   def get_assembly_targets(
       self,
       event_id: int,
       session: Optional[Session] = None
   ) -> List[EventAssemblyTarget]:
       """Get all assembly targets for an event."""
       with self._get_session(session) as sess:
           return sess.query(EventAssemblyTarget).options(
               joinedload(EventAssemblyTarget.finished_good)
           ).filter_by(event_id=event_id).all()
   ```

**Files**: `src/services/event_service.py`
**Parallel?**: Yes (can proceed with T016)
**Notes**: Same pattern as get_production_targets.

---

### Subtask T018 - Implement EventService.delete_production_target()

**Purpose**: Remove a production target from an event.

**Steps**:
1. Add method:
   ```python
   def delete_production_target(
       self,
       event_id: int,
       recipe_id: int,
       session: Optional[Session] = None
   ) -> bool:
       """Remove a production target. Returns True if deleted."""
       with self._get_session(session) as sess:
           target = sess.query(EventProductionTarget).filter_by(
               event_id=event_id,
               recipe_id=recipe_id
           ).first()
           if target:
               sess.delete(target)
               sess.commit()
               return True
           return False
   ```

**Files**: `src/services/event_service.py`
**Parallel?**: No
**Notes**: Return bool to indicate success/failure for UI feedback.

---

### Subtask T019 - Implement EventService.delete_assembly_target()

**Purpose**: Remove an assembly target from an event.

**Steps**:
1. Add method following same pattern as T018:
   ```python
   def delete_assembly_target(
       self,
       event_id: int,
       finished_good_id: int,
       session: Optional[Session] = None
   ) -> bool:
       """Remove an assembly target. Returns True if deleted."""
       with self._get_session(session) as sess:
           target = sess.query(EventAssemblyTarget).filter_by(
               event_id=event_id,
               finished_good_id=finished_good_id
           ).first()
           if target:
               sess.delete(target)
               sess.commit()
               return True
           return False
   ```

**Files**: `src/services/event_service.py`
**Parallel?**: Yes (can proceed with T018)
**Notes**: Same pattern as delete_production_target.

---

### Subtask T020 - Write unit tests for target CRUD

**Purpose**: Verify all target CRUD operations work correctly.

**Steps**:
1. Create `src/tests/services/test_event_service_targets.py`
2. Add test cases:
   ```python
   class TestProductionTargets:
       def test_set_production_target_creates_new(self, db_session, event, recipe):
           """New target is created when none exists."""

       def test_set_production_target_updates_existing(self, db_session, event, recipe):
           """Existing target is updated, not duplicated."""

       def test_set_production_target_validates_positive(self, db_session, event, recipe):
           """ValueError raised for non-positive target_batches."""

       def test_get_production_targets_returns_all(self, db_session, event):
           """Returns all targets for the event."""

       def test_get_production_targets_empty(self, db_session, event):
           """Returns empty list when no targets set."""

       def test_delete_production_target_returns_true(self, db_session, event, recipe):
           """Returns True when target deleted."""

       def test_delete_production_target_returns_false(self, db_session, event, recipe):
           """Returns False when target not found."""

   class TestAssemblyTargets:
       # Mirror tests for assembly targets
   ```

**Files**: `src/tests/services/test_event_service_targets.py`
**Parallel?**: No
**Notes**: Create fixtures for event, recipe, finished_good if not existing.

---

## Test Strategy

**Run Tests**:
```bash
pytest src/tests/services/test_event_service_targets.py -v
```

**Coverage Requirements**:
- Create new target
- Update existing target
- Validation error for invalid values
- Get all targets (with data)
- Get all targets (empty)
- Delete existing target
- Delete non-existent target

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session management | Follow existing EventService patterns |
| Eager loading | Use joinedload to avoid N+1 |
| Upsert race condition | Single-user app, not a concern |

---

## Definition of Done Checklist

- [ ] `set_production_target()` implemented
- [ ] `set_assembly_target()` implemented
- [ ] `get_production_targets()` with eager loading
- [ ] `get_assembly_targets()` with eager loading
- [ ] `delete_production_target()` implemented
- [ ] `delete_assembly_target()` implemented
- [ ] Unit tests for all operations
- [ ] All tests pass
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Reviewers should verify**:
1. Upsert pattern correctly checks for existing
2. Validation rejects values <= 0
3. Eager loading prevents N+1
4. Return types match contracts
5. Tests cover create, update, get, delete scenarios

---

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
