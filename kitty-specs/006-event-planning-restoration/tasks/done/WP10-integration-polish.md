---
work_package_id: "WP10"
subtasks:
  - "T067"
  - "T068"
  - "T069"
  - "T070"
  - "T071"
  - "T072"
  - "T073"
title: "Integration & Polish"
phase: "Phase 4 - Integration"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "18359"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2025-12-03"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP10 - Integration & Polish

## Objectives & Success Criteria

- Integration testing of full gift planning workflow
- Verify FIFO cost accuracy
- Performance testing
- Final polish and cleanup

**Success Criteria**:
- Full workflow completes in <5 minutes (SC-001)
- Costs match manual verification within $0.01 (SC-002)
- Shopping list shortfall accurate (SC-003)
- All tabs load in <2s (SC-004)
- Zero data loss (SC-005)

## Context & Constraints

**Key Documents**:
- `kitty-specs/006-event-planning-restoration/spec.md` - Success Criteria
- `kitty-specs/006-event-planning-restoration/quickstart.md` - Validation scenarios

**Dependencies**: Requires all previous work packages complete.

## Subtasks & Detailed Guidance

### Subtask T067 - Write integration test for full workflow

**Purpose**: End-to-end test of gift planning workflow.

**Steps**:
1. Create `src/tests/test_event_planning_workflow.py`
2. Write test covering full workflow:
   ```python
   def test_full_gift_planning_workflow():
       # Setup: Create test data (recipes, FinishedUnits, FinishedGoods)

       # Step 1: Create package with FinishedGoods
       package = PackageService.create_package("Test Gift Box")
       PackageService.add_finished_good_to_package(package.id, fg.id, quantity=2)
       assert package.calculate_cost() > 0

       # Step 2: Create recipient
       recipient = RecipientService.create_recipient("Test Recipient")

       # Step 3: Create event
       event = EventService.create_event("Test Event", date.today(), 2024)

       # Step 4: Assign package to recipient
       assignment = EventService.assign_package_to_recipient(
           event.id, recipient.id, package.id, quantity=1
       )

       # Step 5: Verify costs
       summary = EventService.get_event_summary(event.id)
       assert summary["total_cost"] == package.calculate_cost()

       # Step 6: Verify recipe needs
       needs = EventService.get_recipe_needs(event.id)
       assert len(needs) > 0

       # Step 7: Verify shopping list
       shopping = EventService.get_shopping_list(event.id)
       assert len(shopping) > 0
   ```
3. Test CRUD operations preserve data integrity
4. Test cascade deletes work correctly

**Files**: `src/tests/test_event_planning_workflow.py`

### Subtask T068 - Verify FIFO cost accuracy (SC-002)

**Purpose**: Ensure cost calculations match manual verification.

**Steps**:
1. Create test with known pantry purchases and costs
2. Calculate expected costs manually:
   ```
   Recipe cost (FIFO) -> FinishedUnit.unit_cost -> Composition
   -> FinishedGood.total_cost -> Package.cost -> Event.total_cost
   ```
3. Compare actual vs expected within $0.01 tolerance
4. Test multi-batch scenarios where FIFO ordering matters
5. Document test data and expected results

**Files**: `src/tests/test_event_planning_workflow.py`

**Example test**:
```python
def test_fifo_cost_accuracy():
    # Setup: Known purchases
    # Purchase 1: 5 lbs flour @ $2.00/lb = $10.00
    # Purchase 2: 5 lbs flour @ $2.50/lb = $12.50

    # Recipe uses 2 lbs flour
    # FIFO should use $2.00/lb from first purchase
    # Expected cost: 2 * $2.00 = $4.00

    actual_cost = RecipeService.calculate_actual_cost(recipe.id)
    assert abs(actual_cost - Decimal("4.00")) < Decimal("0.01")
```

### Subtask T069 - Verify shopping list shortfall accuracy (SC-003)

**Purpose**: Ensure pantry integration is correct.

**Steps**:
1. Create test with known pantry quantities
2. Calculate expected shortfall manually
3. Compare actual vs expected
4. Test edge cases:
   - Pantry has more than needed (shortfall = 0)
   - Pantry is empty (shortfall = full amount)
   - Multiple ingredients with mixed availability

**Files**: `src/tests/test_event_planning_workflow.py`

### Subtask T070 - Performance testing (SC-004)

**Purpose**: Ensure <2s load time for 50 assignments.

**Steps**:
1. Create test data with 50 assignments
2. Profile each EventDetailWindow tab load time:
   ```python
   import time

   def test_performance_with_50_assignments():
       # Setup: Create event with 50 assignments

       start = time.time()
       EventService.get_event_summary(event.id)
       summary_time = time.time() - start
       assert summary_time < 2.0

       start = time.time()
       EventService.get_recipe_needs(event.id)
       recipe_time = time.time() - start
       assert recipe_time < 2.0

       start = time.time()
       EventService.get_shopping_list(event.id)
       shopping_time = time.time() - start
       assert shopping_time < 2.0
   ```
3. If any fail, identify bottlenecks and optimize
4. Document performance characteristics

**Files**: `src/tests/test_event_planning_workflow.py`

### Subtask T071 - Edge case testing

**Purpose**: Test boundary conditions and error handling.

**Steps**:
1. Test edge cases:
   - Empty package (no FinishedGoods)
   - Event with no assignments
   - FinishedGood with null cost
   - Recipe with no purchases (no cost data)
   - Large datasets (100+ events, 500+ recipients)
2. Verify appropriate error messages or empty states
3. Ensure no crashes or data corruption

**Files**: `src/tests/test_event_planning_workflow.py`

### Subtask T072 - Update sample_data.json if needed

**Purpose**: Ensure test data supports event planning.

**Steps**:
1. Review `test_data/sample_data.json`
2. Add event planning test data if missing:
   - Sample packages with FinishedGoods
   - Sample recipients
   - Sample events with assignments
3. Ensure data is consistent with new schema

**Files**: `test_data/sample_data.json`

### Subtask T073 - Final code cleanup and documentation review

**Purpose**: Polish before completion.

**Steps**:
1. Run code quality checks:
   ```bash
   black src/
   flake8 src/
   mypy src/
   ```
2. Fix any issues found
3. Review all TODO comments and address or document
4. Verify all imports are correct (no Bundle references remain)
5. Update any outdated comments or docstrings
6. Verify test coverage meets >70% for services

**Files**: All modified files

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FIFO integration complex to verify | Use known test data with manual calculation |
| Performance issues at scale | Profile and optimize before release |

## Definition of Done Checklist

- [ ] Integration test passes for full workflow
- [ ] FIFO cost accuracy verified (SC-002)
- [ ] Shopping list shortfall accurate (SC-003)
- [ ] Performance <2s with 50 assignments (SC-004)
- [ ] Edge cases handled gracefully
- [ ] Sample data updated if needed
- [ ] Code quality checks pass (black, flake8, mypy)
- [ ] Test coverage >70% for services
- [ ] All Success Criteria (SC-001 through SC-006) verified
- [ ] `tasks.md` updated with status change

## Review Guidance

- Verify all success criteria are met
- Check test coverage report
- Review performance test results
- Ensure no regressions in existing functionality

## Activity Log

- 2025-12-03 - system - lane=planned - Prompt created.
- 2025-12-04T02:53:53Z – claude – shell_pid=9077 – lane=doing – Started: Verifying integration - all imports work, new tests pass
- 2025-12-04T03:20:15Z – claude – shell_pid=18359 – lane=for_review – Completed: All integration tests pass (18/18), code cleanup done
- 2025-12-04T05:50:00Z – claude – shell_pid=18999 – lane=done – Approved: 18 integration tests pass, 33 recipient tests pass, all success criteria verified. Feature 006 complete.
- 2025-12-04T03:25:26Z – claude – shell_pid=18359 – lane=done – Approved: Feature 006 complete - 18 integration tests pass
