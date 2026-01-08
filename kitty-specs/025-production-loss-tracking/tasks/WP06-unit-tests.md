---
work_package_id: WP06
title: Unit Tests
lane: done
history:
- timestamp: '2025-12-21T16:55:08Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 6 - Testing
shell_pid: '75205'
subtasks:
- T034
- T035
- T036
- T037
- T038
- T039
- T040
- T041
---

# Work Package Prompt: WP06 - Unit Tests

## Objectives & Success Criteria

- Comprehensive test coverage for loss recording functionality
- Tests cover complete, partial loss, and total loss scenarios
- Validation tests confirm actual > expected is rejected
- Loss record creation tests verify category, notes, and cost
- All tests pass with >70% coverage on modified functions
- Tests follow existing test patterns and use existing fixtures

## Context & Constraints

- **Spec**: `kitty-specs/025-production-loss-tracking/spec.md` - Acceptance Scenarios
- **Plan**: `kitty-specs/025-production-loss-tracking/plan.md` - Phase 5
- **Constitution**: `.kittify/memory/constitution.md` - Principle IV: TDD
- **Existing Tests**: `src/tests/services/test_batch_production_service.py`

**Key Constraints**:
- Follow existing test patterns and fixtures
- Each test should be independent with fresh state
- Verify both return values and database state
- Target >70% coverage on service layer

**Dependencies**:
- Requires WP01 and WP02 complete (code to test must exist)

## Subtasks & Detailed Guidance

### Subtask T034 - Test complete production (no loss)
- **Purpose**: Verify FR-004 COMPLETE status when actual = expected
- **File**: `src/tests/services/test_batch_production_service.py`
- **Steps**:
  1. Add test function:
     ```python
     def test_record_production_complete_no_loss(db_session, sample_recipe, sample_finished_unit, sample_inventory):
         """Test that production with actual = expected results in COMPLETE status."""
         # Setup: ensure inventory available
         # Act: record production with actual_yield = expected_yield
         result = batch_production_service.record_batch_production(
             recipe_id=sample_recipe.id,
             finished_unit_id=sample_finished_unit.id,
             num_batches=1,
             actual_yield=sample_finished_unit.items_per_batch,
         )
         # Assert
         assert result["production_status"] == "complete"
         assert result["loss_quantity"] == 0
         assert result["loss_record_id"] is None
         # Verify no ProductionLoss created
         with session_scope() as session:
             losses = session.query(ProductionLoss).filter_by(
                 production_run_id=result["production_run_id"]
             ).all()
             assert len(losses) == 0
     ```
- **Parallel?**: Yes, all test functions are independent
- **Notes**: Reuse existing fixtures for recipe, finished unit, inventory

### Subtask T035 - Test partial loss recording
- **Purpose**: Verify FR-004 PARTIAL_LOSS status and ProductionLoss creation
- **File**: `src/tests/services/test_batch_production_service.py`
- **Steps**:
  1. Add test function:
     ```python
     def test_record_production_partial_loss(db_session, sample_recipe, sample_finished_unit, sample_inventory):
         """Test that production with actual < expected results in PARTIAL_LOSS."""
         expected_yield = sample_finished_unit.items_per_batch
         actual_yield = expected_yield - 5  # 5 units lost

         result = batch_production_service.record_batch_production(
             recipe_id=sample_recipe.id,
             finished_unit_id=sample_finished_unit.id,
             num_batches=1,
             actual_yield=actual_yield,
             loss_category=LossCategory.BURNT,
         )

         assert result["production_status"] == "partial_loss"
         assert result["loss_quantity"] == 5
         assert result["loss_record_id"] is not None

         # Verify ProductionLoss created
         with session_scope() as session:
             loss = session.query(ProductionLoss).get(result["loss_record_id"])
             assert loss is not None
             assert loss.loss_category == "burnt"
             assert loss.loss_quantity == 5
     ```
- **Parallel?**: Yes
- **Notes**: Verify both service result and database state

### Subtask T036 - Test total loss recording
- **Purpose**: Verify FR-004 TOTAL_LOSS status when actual = 0
- **File**: `src/tests/services/test_batch_production_service.py`
- **Steps**:
  1. Add test function:
     ```python
     def test_record_production_total_loss(db_session, sample_recipe, sample_finished_unit, sample_inventory):
         """Test that production with actual = 0 results in TOTAL_LOSS."""
         expected_yield = sample_finished_unit.items_per_batch

         result = batch_production_service.record_batch_production(
             recipe_id=sample_recipe.id,
             finished_unit_id=sample_finished_unit.id,
             num_batches=1,
             actual_yield=0,
             loss_category=LossCategory.CONTAMINATED,
         )

         assert result["production_status"] == "total_loss"
         assert result["loss_quantity"] == expected_yield
         assert result["actual_yield"] == 0

         # Verify inventory NOT increased
         with session_scope() as session:
             fu = session.query(FinishedUnit).get(sample_finished_unit.id)
             # inventory_count should not have increased by expected_yield
     ```
- **Parallel?**: Yes
- **Notes**: Verify inventory unchanged when total loss

### Subtask T037 - Test yield validation
- **Purpose**: Verify FR-003 rejection when actual > expected
- **File**: `src/tests/services/test_batch_production_service.py`
- **Steps**:
  1. Add test function:
     ```python
     def test_record_production_rejects_excess_yield(db_session, sample_recipe, sample_finished_unit, sample_inventory):
         """Test that actual > expected raises ValueError."""
         expected_yield = sample_finished_unit.items_per_batch

         with pytest.raises(ValueError) as exc_info:
             batch_production_service.record_batch_production(
                 recipe_id=sample_recipe.id,
                 finished_unit_id=sample_finished_unit.id,
                 num_batches=1,
                 actual_yield=expected_yield + 10,  # Exceeds expected
             )

         assert "cannot exceed expected yield" in str(exc_info.value).lower()
     ```
- **Parallel?**: Yes
- **Notes**: Use pytest.raises context manager

### Subtask T038 - Test loss with category
- **Purpose**: Verify loss category is stored correctly
- **File**: `src/tests/services/test_batch_production_service.py`
- **Steps**:
  1. Add parametrized test for each category:
     ```python
     @pytest.mark.parametrize("category", list(LossCategory))
     def test_record_production_loss_categories(db_session, sample_recipe, sample_finished_unit, sample_inventory, category):
         """Test that all loss categories can be recorded."""
         result = batch_production_service.record_batch_production(
             recipe_id=sample_recipe.id,
             finished_unit_id=sample_finished_unit.id,
             num_batches=1,
             actual_yield=sample_finished_unit.items_per_batch - 1,
             loss_category=category,
         )

         with session_scope() as session:
             loss = session.query(ProductionLoss).get(result["loss_record_id"])
             assert loss.loss_category == category.value
     ```
- **Parallel?**: Yes
- **Notes**: Parametrized test covers all enum values

### Subtask T039 - Test loss with notes
- **Purpose**: Verify loss notes are stored correctly
- **File**: `src/tests/services/test_batch_production_service.py`
- **Steps**:
  1. Add test function:
     ```python
     def test_record_production_loss_notes(db_session, sample_recipe, sample_finished_unit, sample_inventory):
         """Test that loss notes are stored correctly."""
         notes = "Oven temperature was too high - check thermostat"

         result = batch_production_service.record_batch_production(
             recipe_id=sample_recipe.id,
             finished_unit_id=sample_finished_unit.id,
             num_batches=1,
             actual_yield=sample_finished_unit.items_per_batch - 3,
             loss_category=LossCategory.BURNT,
             loss_notes=notes,
         )

         with session_scope() as session:
             loss = session.query(ProductionLoss).get(result["loss_record_id"])
             assert loss.notes == notes
     ```
- **Parallel?**: Yes
- **Notes**: Verify exact notes text preserved

### Subtask T040 - Test cost calculations
- **Purpose**: Verify FR-010, FR-011 cost snapshot and calculation
- **File**: `src/tests/services/test_batch_production_service.py`
- **Steps**:
  1. Add test function:
     ```python
     def test_record_production_loss_cost_calculation(db_session, sample_recipe, sample_finished_unit, sample_inventory):
         """Test that loss cost equals loss_quantity * per_unit_cost."""
         loss_quantity = 5

         result = batch_production_service.record_batch_production(
             recipe_id=sample_recipe.id,
             finished_unit_id=sample_finished_unit.id,
             num_batches=1,
             actual_yield=sample_finished_unit.items_per_batch - loss_quantity,
             loss_category=LossCategory.BROKEN,
         )

         per_unit_cost = Decimal(result["per_unit_cost"])

         with session_scope() as session:
             loss = session.query(ProductionLoss).get(result["loss_record_id"])
             assert loss.per_unit_cost == per_unit_cost
             assert loss.total_loss_cost == loss_quantity * per_unit_cost
     ```
- **Parallel?**: Yes
- **Notes**: Verify cost matches production run per_unit_cost

### Subtask T041 - Test ProductionLoss model
- **Purpose**: Verify model creation and relationships
- **File**: `src/tests/services/test_batch_production_service.py` or `src/tests/models/test_production_loss.py`
- **Steps**:
  1. Add model tests:
     ```python
     def test_production_loss_creation(db_session):
         """Test ProductionLoss model can be created."""
         # Create prerequisite records (run, finished_unit)
         # Create ProductionLoss
         loss = ProductionLoss(
             production_run_id=run.id,
             finished_unit_id=fu.id,
             loss_category="burnt",
             loss_quantity=5,
             per_unit_cost=Decimal("0.50"),
             total_loss_cost=Decimal("2.50"),
         )
         db_session.add(loss)
         db_session.commit()

         assert loss.id is not None
         assert loss.uuid is not None

     def test_production_loss_relationship(db_session, sample_production_run_with_loss):
         """Test ProductionLoss relationship to ProductionRun."""
         run = sample_production_run_with_loss
         assert len(run.losses) > 0
         assert run.losses[0].production_run == run
     ```
- **Parallel?**: Yes
- **Notes**: May need new fixture for production run with loss

## Test Strategy

Run all tests:
```bash
pytest src/tests/services/test_batch_production_service.py -v
pytest src/tests -v --cov=src/services/batch_production_service --cov-report=term-missing
```

Coverage target: >70% on modified functions.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Fixture complexity | Reuse existing fixtures where possible |
| Flaky tests | Ensure database isolation between tests |
| Missing edge cases | Parametrize for enum values |

## Definition of Done Checklist

- [ ] Test for complete production (no loss)
- [ ] Test for partial loss
- [ ] Test for total loss
- [ ] Test for yield validation (actual > expected)
- [ ] Test for each loss category
- [ ] Test for loss notes
- [ ] Test for cost calculations
- [ ] Test for ProductionLoss model
- [ ] All tests pass
- [ ] Coverage >70% on modified functions
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Verify tests cover all acceptance scenarios from spec
- Check tests are independent (no shared state)
- Confirm edge cases tested (0 yield, exact yield, over yield)
- Verify both service results and database state checked

## Activity Log

- 2025-12-21T16:55:08Z - system - lane=planned - Prompt created.
- 2025-12-21T18:37:44Z – claude – shell_pid=69086 – lane=doing – Starting unit test implementation
- 2025-12-21T18:42:09Z – claude – shell_pid=69086 – lane=for_review – T034-T041 complete. All 22 unit tests pass.
- 2025-12-21T19:17:23Z – claude-reviewer – shell_pid=75205 – lane=done – Code review APPROVED: 21 unit tests all pass. Complete, partial, total loss covered. All categories parametrized. Cost calculations verified.
