---
work_package_id: "WP04"
subtasks:
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "Service Layer - Progress Calculation"
phase: "Phase 3 - Progress & Fulfillment"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "85015"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Service Layer - Progress Calculation

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Implement EventService methods for calculating production and assembly progress.

**Success Criteria**:
- `get_production_progress()` returns progress for each target recipe
- `get_assembly_progress()` returns progress for each target finished good
- `get_event_overall_progress()` returns event-wide summary
- Progress only counts runs with matching event_id
- Over-production (>100%) is displayed correctly
- Unit tests cover 0%, 50%, 100%, 125% scenarios

## Context & Constraints

**Reference Documents**:
- `kitty-specs/016-event-centric-production/spec.md` - FR-015, FR-016, FR-017, User Stories 5-6, 8
- `kitty-specs/016-event-centric-production/contracts/event-service-contracts.md` - Return type specifications

**Return Type Specifications**:

`get_production_progress()` returns:
```python
[
    {
        'recipe': Recipe,
        'recipe_name': str,
        'target_batches': int,
        'produced_batches': int,
        'produced_yield': int,
        'progress_pct': float,
        'is_complete': bool
    }
]
```

`get_assembly_progress()` returns:
```python
[
    {
        'finished_good': FinishedGood,
        'finished_good_name': str,
        'target_quantity': int,
        'assembled_quantity': int,
        'progress_pct': float,
        'is_complete': bool
    }
]
```

`get_event_overall_progress()` returns:
```python
{
    'production_targets_count': int,
    'production_complete_count': int,
    'production_complete': bool,
    'assembly_targets_count': int,
    'assembly_complete_count': int,
    'assembly_complete': bool,
    'packages_pending': int,
    'packages_ready': int,
    'packages_delivered': int,
    'packages_total': int
}
```

**Dependencies**: WP02 (event_id stored), WP03 (targets exist)

---

## Subtasks & Detailed Guidance

### Subtask T021 - Implement EventService.get_production_progress()

**Purpose**: Calculate and return production progress for each target recipe.

**Steps**:
1. Open `src/services/event_service.py`
2. Add method:
   ```python
   def get_production_progress(
       self,
       event_id: int,
       session: Optional[Session] = None
   ) -> List[Dict[str, Any]]:
       """Get production progress for an event."""
       with self._get_session(session) as sess:
           # Get all targets for this event
           targets = sess.query(EventProductionTarget).options(
               joinedload(EventProductionTarget.recipe)
           ).filter_by(event_id=event_id).all()

           results = []
           for target in targets:
               # Sum production runs for this recipe and event
               produced = sess.query(
                   func.coalesce(func.sum(ProductionRun.num_batches), 0),
                   func.coalesce(func.sum(ProductionRun.actual_yield), 0)
               ).filter(
                   ProductionRun.recipe_id == target.recipe_id,
                   ProductionRun.event_id == event_id
               ).first()

               produced_batches = produced[0] or 0
               produced_yield = produced[1] or 0
               progress_pct = (produced_batches / target.target_batches) * 100

               results.append({
                   'recipe': target.recipe,
                   'recipe_name': target.recipe.name,
                   'target_batches': target.target_batches,
                   'produced_batches': produced_batches,
                   'produced_yield': produced_yield,
                   'progress_pct': progress_pct,
                   'is_complete': produced_batches >= target.target_batches
               })

           return results
   ```
3. Add imports: `from sqlalchemy import func`

**Files**: `src/services/event_service.py`
**Parallel?**: No (foundational)
**Notes**: Use func.coalesce to handle NULL sums. Progress can exceed 100%.

---

### Subtask T022 - Implement EventService.get_assembly_progress()

**Purpose**: Calculate and return assembly progress for each target finished good.

**Steps**:
1. Add method following same pattern:
   ```python
   def get_assembly_progress(
       self,
       event_id: int,
       session: Optional[Session] = None
   ) -> List[Dict[str, Any]]:
       """Get assembly progress for an event."""
       with self._get_session(session) as sess:
           targets = sess.query(EventAssemblyTarget).options(
               joinedload(EventAssemblyTarget.finished_good)
           ).filter_by(event_id=event_id).all()

           results = []
           for target in targets:
               assembled = sess.query(
                   func.coalesce(func.sum(AssemblyRun.quantity_assembled), 0)
               ).filter(
                   AssemblyRun.finished_good_id == target.finished_good_id,
                   AssemblyRun.event_id == event_id
               ).scalar() or 0

               progress_pct = (assembled / target.target_quantity) * 100

               results.append({
                   'finished_good': target.finished_good,
                   'finished_good_name': target.finished_good.name,
                   'target_quantity': target.target_quantity,
                   'assembled_quantity': assembled,
                   'progress_pct': progress_pct,
                   'is_complete': assembled >= target.target_quantity
               })

           return results
   ```

**Files**: `src/services/event_service.py`
**Parallel?**: Yes (can proceed with T021)
**Notes**: Same pattern as production progress.

---

### Subtask T023 - Implement EventService.get_event_overall_progress()

**Purpose**: Return summary of all progress metrics for an event.

**Steps**:
1. Add method:
   ```python
   def get_event_overall_progress(
       self,
       event_id: int,
       session: Optional[Session] = None
   ) -> Dict[str, Any]:
       """Get overall event progress summary."""
       with self._get_session(session) as sess:
           # Get production progress
           prod_progress = self.get_production_progress(event_id, sess)
           prod_complete = [p for p in prod_progress if p['is_complete']]

           # Get assembly progress
           asm_progress = self.get_assembly_progress(event_id, sess)
           asm_complete = [a for a in asm_progress if a['is_complete']]

           # Get package counts by status
           packages = sess.query(EventRecipientPackage).filter_by(
               event_id=event_id
           ).all()

           pending = len([p for p in packages if p.fulfillment_status == FulfillmentStatus.PENDING.value])
           ready = len([p for p in packages if p.fulfillment_status == FulfillmentStatus.READY.value])
           delivered = len([p for p in packages if p.fulfillment_status == FulfillmentStatus.DELIVERED.value])

           return {
               'production_targets_count': len(prod_progress),
               'production_complete_count': len(prod_complete),
               'production_complete': len(prod_progress) == 0 or len(prod_complete) == len(prod_progress),
               'assembly_targets_count': len(asm_progress),
               'assembly_complete_count': len(asm_complete),
               'assembly_complete': len(asm_progress) == 0 or len(asm_complete) == len(asm_progress),
               'packages_pending': pending,
               'packages_ready': ready,
               'packages_delivered': delivered,
               'packages_total': len(packages)
           }
   ```

**Files**: `src/services/event_service.py`
**Parallel?**: No (depends on T021, T022)
**Notes**: production_complete is True if no targets (nothing to do) or all complete.

---

### Subtask T024 - Write unit tests for progress calculation

**Purpose**: Verify progress calculations are accurate for all scenarios.

**Steps**:
1. Create `src/tests/services/test_event_service_progress.py`
2. Add test cases:
   ```python
   class TestProductionProgress:
       def test_progress_zero_percent(self, db_session, event, recipe):
           """0% when no production recorded for target."""
           # Set target, no production
           # Assert: produced_batches=0, progress_pct=0, is_complete=False

       def test_progress_fifty_percent(self, db_session, event, recipe):
           """50% when half of target produced."""
           # Set target=4, record 2 batches
           # Assert: progress_pct=50, is_complete=False

       def test_progress_one_hundred_percent(self, db_session, event, recipe):
           """100% when target exactly met."""
           # Set target=4, record 4 batches
           # Assert: progress_pct=100, is_complete=True

       def test_progress_over_hundred_percent(self, db_session, event, recipe):
           """125% when over-produced."""
           # Set target=4, record 5 batches
           # Assert: progress_pct=125, is_complete=True

       def test_progress_only_counts_event_runs(self, db_session, event, recipe):
           """Only counts runs with matching event_id."""
           # Record production for event AND standalone
           # Assert: only event production counted

       def test_progress_empty_when_no_targets(self, db_session, event):
           """Empty list when no targets set."""

   class TestAssemblyProgress:
       # Mirror tests for assembly

   class TestOverallProgress:
       def test_overall_with_mixed_progress(self, db_session, event):
           """Correctly aggregates all progress metrics."""

       def test_production_complete_when_no_targets(self, db_session, event):
           """production_complete=True when no targets (nothing to do)."""

       def test_package_counts_by_status(self, db_session, event):
           """Correctly counts packages by fulfillment status."""
   ```

**Files**: `src/tests/services/test_event_service_progress.py`
**Parallel?**: No
**Notes**: Test that standalone production (event_id=NULL) is excluded.

---

## Test Strategy

**Run Tests**:
```bash
pytest src/tests/services/test_event_service_progress.py -v
```

**Coverage Requirements**:
- 0%, 50%, 100%, >100% progress scenarios
- Event-specific filtering (exclude other events)
- Empty/no targets case
- Package status counting

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| N+1 queries | Use aggregate queries, not loops |
| Division by zero | Not possible: targets must be > 0 |
| Performance | Consider caching for large events |

---

## Definition of Done Checklist

- [ ] `get_production_progress()` implemented
- [ ] `get_assembly_progress()` implemented
- [ ] `get_event_overall_progress()` implemented
- [ ] Progress only counts runs with matching event_id
- [ ] Over-production (>100%) handled correctly
- [ ] Unit tests for all progress scenarios
- [ ] All tests pass
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Reviewers should verify**:
1. Event_id filtering is correct in aggregate queries
2. Progress percentage can exceed 100%
3. is_complete correctly set when produced >= target
4. Empty target list returns empty progress list
5. Overall progress correctly aggregates individual progress

---

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-11T04:03:42Z – claude – shell_pid=85015 – lane=doing – Started implementation - progress calculation service
- 2025-12-11T04:30:00Z – claude – shell_pid=85015 – lane=doing – Completed all subtasks:
  - T021: Implemented get_production_progress() with aggregate queries
  - T022: Implemented get_assembly_progress() with aggregate queries
  - T023: Implemented get_event_overall_progress() combining all metrics
  - T024: Created test_event_service_progress.py with 17 tests:
    - TestProductionProgress: 7 tests (0%, 50%, 100%, 125%, event filtering, empty, multiple)
    - TestAssemblyProgress: 6 tests (0%, 50%, 100%, 125%, event filtering, empty)
    - TestOverallProgress: 4 tests (no targets, production counts, package counts, mixed)
  - All 17 tests pass
