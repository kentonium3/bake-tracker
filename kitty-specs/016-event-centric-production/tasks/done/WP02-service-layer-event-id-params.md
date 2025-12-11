---
work_package_id: "WP02"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "Service Layer - Event ID Parameters"
phase: "Phase 2 - Service Layer"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "83960"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Service Layer - Event ID Parameters

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Update BatchProductionService and AssemblyService to accept and store event_id.

**Success Criteria**:
- `record_batch_production()` accepts optional `event_id` parameter
- `record_assembly()` accepts optional `event_id` parameter
- Event_id is validated (event must exist if provided)
- Event_id is stored on ProductionRun/AssemblyRun records
- Existing callers continue to work (backward compatible)
- Unit tests cover all scenarios

## Context & Constraints

**Reference Documents**:
- `kitty-specs/016-event-centric-production/spec.md` - FR-011, FR-012
- `kitty-specs/016-event-centric-production/data-model.md` - Service method contracts
- `kitty-specs/016-event-centric-production/contracts/event-service-contracts.md`

**Existing Code**:
- `src/services/batch_production_service.py` - `record_batch_production()` method
- `src/services/assembly_service.py` - `record_assembly()` method

**Constraints**:
- Parameter must be optional with default None for backward compatibility
- Validate event exists before setting event_id
- Follow existing error handling patterns

**Dependencies**: WP01 must be complete (models with event_id FK)

---

## Subtasks & Detailed Guidance

### Subtask T010 - Update BatchProductionService.record_batch_production() with event_id

**Purpose**: Enable linking production runs to events when recording production.

**Steps**:
1. Open `src/services/batch_production_service.py`
2. Locate `record_batch_production()` method
3. Add parameter after existing parameters:
   ```python
   def record_batch_production(
       self,
       recipe_id: int,
       num_batches: int,
       actual_yield: int,
       notes: str = None,
       session: Session = None,
       event_id: int = None  # NEW
   ) -> ProductionRun:
   ```
4. Add validation if event_id provided:
   ```python
   if event_id is not None:
       event = session.query(Event).filter_by(id=event_id).first()
       if not event:
           raise ValueError(f"Event with id {event_id} not found")
   ```
5. Set event_id on ProductionRun before session.add():
   ```python
   production_run = ProductionRun(
       recipe_id=recipe_id,
       # ... existing fields ...
       event_id=event_id,  # NEW
   )
   ```
6. Add import: `from src.models import Event`

**Files**: `src/services/batch_production_service.py`
**Parallel?**: No (foundational change)
**Notes**: Review existing method to find correct insertion points.

---

### Subtask T011 - Update AssemblyService.record_assembly() with event_id

**Purpose**: Enable linking assembly runs to events when recording assembly.

**Steps**:
1. Open `src/services/assembly_service.py`
2. Locate `record_assembly()` method
3. Add parameter (note: existing method uses keyword-only args after `*`):
   ```python
   def record_assembly(
       self,
       finished_good_id: int,
       quantity: int,
       *,
       event_id: int = None,  # NEW - add before other kwargs
       assembled_at: Optional[datetime] = None,
       notes: Optional[str] = None,
       session=None,
   ) -> Dict[str, Any]:
   ```
4. Add validation if event_id provided (same pattern as T010)
5. Set event_id on AssemblyRun before session.add()
6. Add import: `from src.models import Event`

**Files**: `src/services/assembly_service.py`
**Parallel?**: Yes (can proceed with T010)
**Notes**: Keyword-only args require special care with parameter order.

---

### Subtask T012 - Write unit tests for record_batch_production with event_id

**Purpose**: Verify event_id functionality in BatchProductionService.

**Steps**:
1. Open or create `src/tests/services/test_batch_production_service.py`
2. Add test cases:
   ```python
   def test_record_batch_production_with_event_id(db_session):
       """Production run links to event when event_id provided."""
       # Setup: create recipe, event
       # Act: record_batch_production with event_id
       # Assert: production_run.event_id == event.id

   def test_record_batch_production_without_event_id(db_session):
       """Production run has null event_id when not provided."""
       # Setup: create recipe
       # Act: record_batch_production without event_id
       # Assert: production_run.event_id is None

   def test_record_batch_production_invalid_event_id(db_session):
       """ValueError raised for non-existent event_id."""
       # Setup: create recipe
       # Act/Assert: record_batch_production with invalid event_id raises ValueError
   ```

**Files**: `src/tests/services/test_batch_production_service.py`
**Parallel?**: Yes (can proceed with T013)
**Notes**: Use existing test fixtures for recipe/event setup.

---

### Subtask T013 - Write unit tests for record_assembly with event_id

**Purpose**: Verify event_id functionality in AssemblyService.

**Steps**:
1. Open or create `src/tests/services/test_assembly_service.py`
2. Add test cases:
   ```python
   def test_record_assembly_with_event_id(db_session):
       """Assembly run links to event when event_id provided."""
       # Setup: create finished_good, event, required components
       # Act: record_assembly with event_id
       # Assert: assembly_run.event_id == event.id

   def test_record_assembly_without_event_id(db_session):
       """Assembly run has null event_id when not provided."""
       # Setup: create finished_good with components
       # Act: record_assembly without event_id
       # Assert: assembly_run.event_id is None

   def test_record_assembly_invalid_event_id(db_session):
       """ValueError raised for non-existent event_id."""
       # Setup: create finished_good
       # Act/Assert: record_assembly with invalid event_id raises ValueError
   ```

**Files**: `src/tests/services/test_assembly_service.py`
**Parallel?**: Yes (can proceed with T012)
**Notes**: Assembly tests may require more setup (finished goods need components).

---

## Test Strategy

**Run Tests**:
```bash
pytest src/tests/services/test_batch_production_service.py -v
pytest src/tests/services/test_assembly_service.py -v
```

**Coverage Requirements**:
- Test with valid event_id
- Test with null event_id (backward compatibility)
- Test with invalid event_id (error handling)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing callers | Parameter is optional with default None |
| Missing Event import | Add import at top of service file |
| Session management | Use existing session patterns from the service |

---

## Definition of Done Checklist

- [ ] `record_batch_production()` accepts event_id parameter
- [ ] `record_assembly()` accepts event_id parameter
- [ ] Event validation implemented in both methods
- [ ] Event_id stored on created records
- [ ] Unit tests for valid event_id
- [ ] Unit tests for null event_id
- [ ] Unit tests for invalid event_id
- [ ] All tests pass: `pytest src/tests/services/ -v`
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Reviewers should verify**:
1. Parameter is optional with default None
2. Event validation queries database correctly
3. Error message is clear for invalid event_id
4. Existing callers not affected (no breaking changes)
5. Tests cover all three scenarios

---

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-11T02:49:35Z – claude – shell_pid=80123 – lane=doing – Started implementation - adding event_id params to services
- 2025-12-11T03:45:00Z – claude – shell_pid=80123 – lane=doing – Completed all subtasks:
  - T010: Added event_id parameter to BatchProductionService.record_batch_production()
    - Added EventNotFoundError exception
    - Added Event import
    - Added optional event_id parameter with validation
    - Added event_id to ProductionRun creation
    - Added event_id to return value
  - T011: Added event_id parameter to AssemblyService.record_assembly()
    - Added EventNotFoundError exception
    - Added Event import
    - Added optional event_id parameter with validation
    - Added event_id to AssemblyRun creation
    - Added event_id to return value
  - T012: Added TestRecordBatchProductionEventId test class with 3 tests:
    - test_record_production_with_event_id (passes)
    - test_record_production_without_event_id (passes)
    - test_record_production_invalid_event_id (passes)
  - T013: Added TestRecordAssemblyEventId test class with 3 tests:
    - test_record_assembly_with_event_id (passes)
    - test_record_assembly_without_event_id (passes)
    - test_record_assembly_invalid_event_id (passes)
  - All 6 event_id tests pass
  - Note: 5 pre-existing failing tests unrelated to WP02 (exist on main branch)
- 2025-12-11T03:57:31Z – claude – shell_pid=83960 – lane=for_review – Ready for review - all subtasks T010-T013 complete, 6 event_id tests pass
- 2025-12-11T17:49:34Z – claude – shell_pid=83960 – lane=done – Code review approved - all 6 event_id tests pass, implementation meets spec
