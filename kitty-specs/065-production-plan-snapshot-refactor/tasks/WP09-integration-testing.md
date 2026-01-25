---
work_package_id: "WP09"
subtasks:
  - "T040"
  - "T041"
  - "T042"
  - "T043"
  - "T044"
title: "Integration Testing & Cleanup"
phase: "Phase 6 - Cleanup & Testing"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "6732"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: ["WP05", "WP06", "WP08"]
history:
  - timestamp: "2026-01-24T19:47:15Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP09 – Integration Testing & Cleanup

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
# Depends on WP05, WP06, WP08 (all functionality complete)
spec-kitty implement WP09 --base WP08 --feature 065-production-plan-snapshot-refactor
```

---

## Objectives & Success Criteria

Comprehensive testing of full workflow and final code cleanup.

**Success Criteria**:
- [ ] Integration test: plan → production flow verifies snapshot reuse
- [ ] Integration test: plan → assembly flow verifies snapshot reuse
- [ ] Backward compatibility test: legacy events work correctly
- [ ] Code cleanup complete (no dead code, updated docstrings)
- [ ] Test coverage >70% for affected services

## Context & Constraints

**Reference Documents**:
- `kitty-specs/065-production-plan-snapshot-refactor/spec.md` - All user stories, success criteria
- `.kittify/memory/constitution.md` - Principle IV (Test-Driven Development, >70% coverage)
- `kitty-specs/065-production-plan-snapshot-refactor/plan.md` - Phase 6 details

**Success Criteria from Spec**:
- SC-001: Event plans stable after definition changes
- SC-002: 100% snapshot reuse for planned production
- SC-003: 100% snapshot reuse for planned assembly
- SC-004: Backward compatibility maintained
- SC-005: <5 second calculation (verified in WP07)
- SC-006: Atomic snapshot creation (verified in WP04)

## Subtasks & Detailed Guidance

### Subtask T040 – Integration test: plan → production → verify snapshot reuse

**Purpose**: Test the complete workflow from plan creation through production execution.

**Steps**:
1. Create integration test file: `src/tests/integration/test_planning_production_workflow.py`

2. Test full workflow:
   ```python
   def test_planning_production_workflow_snapshot_reuse(db_session):
       """Integration test: plan creation → production → snapshot reuse.

       Verifies SC-002: Production runs for planned events reference
       the same snapshot as the plan (100% snapshot reuse).
       """
       # Setup: Create event with production targets
       event = create_event(db_session, name="Holiday 2025")
       recipe = create_recipe(db_session, name="Sugar Cookies")
       target = EventProductionTarget(
           event_id=event.id,
           recipe_id=recipe.id,
           target_batches=10
       )
       db_session.add(target)
       db_session.flush()

       # Act 1: Create plan (creates snapshots)
       plan_result = create_plan(event.id, session=db_session)
       assert plan_result["success"]
       assert plan_result["recipe_snapshots_created"] == 1

       # Verify target has snapshot linked
       db_session.refresh(target)
       planning_snapshot_id = target.recipe_snapshot_id
       assert planning_snapshot_id is not None

       # Act 2: Record production for the planned event
       production_result = record_batch_production(
           recipe_id=recipe.id,
           quantity=5,
           event_id=event.id,
           session=db_session
       )

       # Assert: Same snapshot reused
       assert production_result["recipe_snapshot_id"] == planning_snapshot_id
       assert production_result["snapshot_reused"] == True

       # Verify production run references planning snapshot
       production_run = db_session.get(ProductionRun, production_result["production_run_id"])
       assert production_run.recipe_snapshot_id == planning_snapshot_id
   ```

3. Test plan immutability after definition change:
   ```python
   def test_plan_immutable_after_recipe_change(db_session):
       """Integration test: modifying recipe doesn't affect plan.

       Verifies SC-001: Event plans remain stable after definition changes.
       """
       # Setup: Create event, recipe, plan
       event = create_event(db_session)
       recipe = create_recipe(db_session, name="Original Name")
       target = create_production_target(db_session, event, recipe, batches=5)

       # Create plan
       create_plan(event.id, session=db_session)

       # Get plan summary (captures original recipe name)
       summary_before = get_plan_summary(event.id, session=db_session)
       original_name = summary_before["recipe_batches"][0]["recipe_name"]

       # Modify the recipe
       recipe.name = "Changed Name"
       db_session.flush()

       # Get plan summary again
       summary_after = get_plan_summary(event.id, session=db_session)
       name_in_plan = summary_after["recipe_batches"][0]["recipe_name"]

       # Assert: Plan still shows original name (from snapshot)
       assert name_in_plan == original_name
       assert name_in_plan != "Changed Name"
   ```

**Files**:
- `src/tests/integration/test_planning_production_workflow.py` (create)

**Parallel?**: Yes - can be developed alongside T041, T042

---

### Subtask T041 – Integration test: plan → assembly → verify snapshot reuse

**Purpose**: Test the complete workflow from plan creation through assembly execution.

**Steps**:
1. Add to integration test file or create separate:
   ```python
   def test_planning_assembly_workflow_snapshot_reuse(db_session):
       """Integration test: plan creation → assembly → snapshot reuse.

       Verifies SC-003: Assembly runs for planned events reference
       the same snapshot as the plan (100% snapshot reuse).
       """
       # Setup: Create event with assembly targets
       event = create_event(db_session, name="Holiday 2025")
       finished_good = create_finished_good(db_session, name="Gift Box A")
       target = EventAssemblyTarget(
           event_id=event.id,
           finished_good_id=finished_good.id,
           target_quantity=20
       )
       db_session.add(target)
       db_session.flush()

       # Act 1: Create plan (creates snapshots)
       plan_result = create_plan(event.id, session=db_session)
       assert plan_result["success"]
       assert plan_result["finished_good_snapshots_created"] == 1

       # Verify target has snapshot linked
       db_session.refresh(target)
       planning_snapshot_id = target.finished_good_snapshot_id
       assert planning_snapshot_id is not None

       # Act 2: Record assembly for the planned event
       assembly_result = record_assembly(
           finished_good_id=finished_good.id,
           quantity=10,
           event_id=event.id,
           session=db_session
       )

       # Assert: Same snapshot reused
       assert assembly_result["finished_good_snapshot_id"] == planning_snapshot_id
       assert assembly_result["snapshot_reused"] == True

       # Verify assembly run references planning snapshot
       assembly_run = db_session.get(AssemblyRun, assembly_result["assembly_run_id"])
       assert assembly_run.finished_good_snapshot_id == planning_snapshot_id
   ```

**Files**:
- `src/tests/integration/test_planning_assembly_workflow.py` (create or add to existing)

**Parallel?**: Yes - can be developed alongside T040, T042

---

### Subtask T042 – Backward compatibility test: legacy events

**Purpose**: Verify events created before this refactor still work correctly.

**Steps**:
1. Create backward compatibility tests:
   ```python
   def test_legacy_production_without_plan_creates_snapshot(db_session):
       """Backward compatibility: production without plan creates new snapshot.

       Verifies SC-004: Legacy events without planning snapshots
       continue to function.
       """
       # Setup: Create recipe without event/plan
       recipe = create_recipe(db_session)

       # Act: Record production without event
       result = record_batch_production(
           recipe_id=recipe.id,
           quantity=3,
           event_id=None,  # No event (ad-hoc production)
           session=db_session
       )

       # Assert: New snapshot created
       assert result["recipe_snapshot_id"] is not None
       assert result["snapshot_reused"] == False

   def test_legacy_event_without_snapshots(db_session):
       """Backward compatibility: event with targets but no snapshots.

       Simulates events created before F065 (no planning snapshots on targets).
       """
       # Setup: Create event with target but NO snapshot (legacy state)
       event = create_event(db_session)
       recipe = create_recipe(db_session)
       target = EventProductionTarget(
           event_id=event.id,
           recipe_id=recipe.id,
           target_batches=5,
           recipe_snapshot_id=None  # Legacy: no planning snapshot
       )
       db_session.add(target)
       db_session.flush()

       # Act: Record production for legacy event
       result = record_batch_production(
           recipe_id=recipe.id,
           quantity=3,
           event_id=event.id,
           session=db_session
       )

       # Assert: New snapshot created (backward compatibility)
       assert result["recipe_snapshot_id"] is not None
       assert result["snapshot_reused"] == False

   def test_legacy_assembly_without_plan_creates_snapshot(db_session):
       """Backward compatibility: assembly without plan creates new snapshot."""
       finished_good = create_finished_good(db_session)

       result = record_assembly(
           finished_good_id=finished_good.id,
           quantity=5,
           event_id=None,  # No event
           session=db_session
       )

       assert result["finished_good_snapshot_id"] is not None
       assert result["snapshot_reused"] == False
   ```

**Files**:
- `src/tests/integration/test_backward_compatibility.py` (create)

**Parallel?**: Yes - can be developed alongside T040, T041

---

### Subtask T043 – Code cleanup: remove dead code, update docstrings

**Purpose**: Final cleanup of any orphaned code from the refactoring.

**Steps**:
1. Search for unused imports:
   ```bash
   # Use IDE or tool to find unused imports
   # Or manually review files modified in WP01-WP08
   ```

2. Search for orphaned code (references to removed fields):
   ```bash
   grep -rn "calculation_results\|is_stale\|stale_reason" src/
   grep -rn "get_recipe_batches\|get_shopping_list\|mark_stale" src/
   grep -rn "_check_staleness\|_get_latest" src/
   ```

3. Remove any commented-out code from previous WPs

4. Update docstrings that reference old architecture:
   - `ProductionPlanSnapshot` - done in WP01
   - `planning_service.py` - verify create_plan/get_plan_summary docs
   - `batch_production_service.py` - document snapshot reuse
   - `assembly_service.py` - document snapshot reuse

5. Verify no TODO markers left from implementation:
   ```bash
   grep -rn "TODO\|FIXME\|XXX" src/services/planning/ src/models/
   ```

6. Run linter to catch issues:
   ```bash
   flake8 src/models/ src/services/planning/
   mypy src/models/ src/services/planning/
   ```

**Files**:
- Various files modified in WP01-WP08

**Parallel?**: No - cleanup after T040-T042

---

### Subtask T044 – Verify test coverage >70% for affected services

**Purpose**: Ensure test coverage meets constitutional requirement.

**Steps**:
1. Run coverage report:
   ```bash
   ./run-tests.sh src/tests/ -v --cov=src/services --cov-report=term-missing
   ```

2. Check specific services:
   ```bash
   ./run-tests.sh src/tests/ -v \
     --cov=src/services/planning/planning_service \
     --cov=src/services/batch_production_service \
     --cov=src/services/assembly_service \
     --cov=src/services/recipe_snapshot_service \
     --cov-report=term-missing
   ```

3. Identify uncovered code:
   - Look at "MISSING" column in coverage report
   - Identify critical paths not covered

4. Add tests for uncovered critical paths:
   - Error handling paths
   - Edge cases
   - Fallback logic

5. Target coverage numbers:
   - planning_service.py: >70%
   - batch_production_service.py: >70%
   - assembly_service.py: >70%
   - recipe_snapshot_service.py: >70%

6. Document final coverage in activity log

**Files**:
- Various test files (add tests if needed)

**Parallel?**: No - final verification

---

## Test Strategy

**Run All Tests**:
```bash
./run-tests.sh src/tests/ -v
```

**Run Integration Tests Only**:
```bash
./run-tests.sh src/tests/integration/ -v
```

**Coverage Report**:
```bash
./run-tests.sh src/tests/ --cov=src/services --cov-report=html
# Open htmlcov/index.html in browser
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Coverage below 70% | Add targeted tests for uncovered paths |
| Integration tests flaky | Use proper test fixtures and isolation |
| Dead code missed | Thorough grep search and linter |

## Definition of Done Checklist

- [ ] Integration test: plan → production passes
- [ ] Integration test: plan → assembly passes
- [ ] Backward compatibility tests pass
- [ ] Code cleanup complete (no dead code)
- [ ] All docstrings updated
- [ ] Coverage >70% for affected services
- [ ] All tests pass: `./run-tests.sh src/tests/ -v`
- [ ] Activity log entry added

## Review Guidance

Reviewers should verify:
1. Integration tests cover all success criteria from spec
2. Backward compatibility properly tested
3. No orphaned code remains
4. Coverage meets constitutional requirement
5. Tests are maintainable (good fixtures, clear assertions)

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-24T19:47:15Z – system – lane=planned – Prompt created.
- 2026-01-25T00:10:44Z – claude-opus – shell_pid=2314 – lane=doing – Started implementation via workflow command
- 2026-01-25T00:34:31Z – claude-opus – shell_pid=2314 – lane=for_review – Ready for review: Integration tests for F065 snapshot workflow, fixed identity map caching bug, coverage >70%
- 2026-01-25T00:35:13Z – claude-opus – shell_pid=6732 – lane=doing – Started review via workflow command
- 2026-01-25T00:48:26Z – claude-opus – shell_pid=6732 – lane=done – Review passed: All integration tests pass (7/7), coverage 71% for planning_service.py (>70% target), fixed identity map caching bug, SC-001/002/003/004 verified
