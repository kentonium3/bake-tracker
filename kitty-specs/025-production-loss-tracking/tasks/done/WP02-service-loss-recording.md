---
work_package_id: "WP02"
subtasks:
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Service Layer - Core Loss Recording"
phase: "Phase 2 - Service Layer"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "74118"
history:
  - timestamp: "2025-12-21T16:55:08Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Service Layer - Core Loss Recording

## Objectives & Success Criteria

- `record_batch_production()` accepts optional `loss_category` and `loss_notes` parameters
- Validation rejects actual_yield > expected_yield with clear error
- Function calculates loss_quantity and sets production_status automatically
- ProductionLoss record created when loss_quantity > 0
- Result dict includes loss data (loss_quantity, production_status, loss_id if applicable)
- `get_production_history()` returns production_status and loss_quantity fields
- Optional eager-loading of losses relationship available

## Context & Constraints

- **Spec**: `kitty-specs/025-production-loss-tracking/spec.md` - User Stories 1, 3
- **Plan**: `kitty-specs/025-production-loss-tracking/plan.md` - Phase 2
- **Data Model**: `kitty-specs/025-production-loss-tracking/data-model.md` - Validation Rules section
- **Constitution**: `.kittify/memory/constitution.md`
- **CLAUDE.md**: Session management pattern - CRITICAL

**Key Constraints**:
- Follow session management pattern: all database operations in same session
- ProductionLoss uses same per_unit_cost as good units (snapshot at production time)
- Validation must happen BEFORE FIFO consumption (fail fast)
- Status determination: COMPLETE if loss=0, TOTAL_LOSS if actual=0, else PARTIAL_LOSS

**Dependencies**:
- Requires WP01 complete (models and enums must exist)

## Subtasks & Detailed Guidance

### Subtask T009 - Add loss parameters to record_batch_production()
- **Purpose**: Allow callers to specify loss category and notes
- **File**: `src/services/batch_production_service.py`
- **Steps**:
  1. Add imports at top: `from src.models import ProductionStatus, LossCategory, ProductionLoss`
  2. Update function signature to add parameters:
     ```python
     def record_batch_production(
         recipe_id: int,
         finished_unit_id: int,
         num_batches: int,
         actual_yield: int,
         *,
         produced_at: Optional[datetime] = None,
         notes: Optional[str] = None,
         event_id: Optional[int] = None,
         loss_category: Optional[LossCategory] = None,  # NEW
         loss_notes: Optional[str] = None,  # NEW
         session=None,
     ) -> Dict[str, Any]:
     ```
  3. Update docstring to document new parameters
- **Parallel?**: No, sequential with T010-T013
- **Notes**: loss_category is Optional - if None and loss exists, default to LossCategory.OTHER

### Subtask T010 - Add yield validation
- **Purpose**: Prevent recording impossible yields (more than expected)
- **File**: `src/services/batch_production_service.py`
- **Steps**:
  1. Add validation BEFORE FIFO consumption starts:
     ```python
     # Calculate expected yield
     if finished_unit.items_per_batch:
         expected_yield = num_batches * finished_unit.items_per_batch
     else:
         expected_yield = num_batches

     # Validate actual_yield <= expected_yield
     if actual_yield > expected_yield:
         raise ValueError(
             f"Actual yield ({actual_yield}) cannot exceed expected yield ({expected_yield})"
         )
     ```
  2. Add custom exception class if preferred: `class ActualYieldExceedsExpectedError(Exception)`
- **Parallel?**: No
- **Notes**: Fail fast - validate before consuming any inventory

### Subtask T011 - Calculate loss_quantity and production_status
- **Purpose**: Derive loss data from yield difference
- **File**: `src/services/batch_production_service.py`
- **Steps**:
  1. After expected_yield calculation, add:
     ```python
     # Calculate loss quantity
     loss_quantity = expected_yield - actual_yield

     # Determine production status
     if loss_quantity == 0:
         production_status = ProductionStatus.COMPLETE
     elif actual_yield == 0:
         production_status = ProductionStatus.TOTAL_LOSS
     else:
         production_status = ProductionStatus.PARTIAL_LOSS
     ```
  2. These values will be used in ProductionRun creation and ProductionLoss creation
- **Parallel?**: No
- **Notes**: Use enum values, not raw strings

### Subtask T012 - Create ProductionLoss record when loss_quantity > 0
- **Purpose**: Capture detailed loss information for tracking and reporting
- **File**: `src/services/batch_production_service.py`
- **Steps**:
  1. After ProductionRun creation and session.flush(), add:
     ```python
     # Create ProductionLoss record if there are losses
     loss_record_id = None
     if loss_quantity > 0:
         loss = ProductionLoss(
             production_run_id=production_run.id,
             finished_unit_id=finished_unit_id,
             loss_category=(loss_category or LossCategory.OTHER).value,
             loss_quantity=loss_quantity,
             per_unit_cost=per_unit_cost,
             total_loss_cost=loss_quantity * per_unit_cost,
             notes=loss_notes,
         )
         session.add(loss)
         session.flush()
         loss_record_id = loss.id
     ```
  2. Ensure this happens within the same session_scope block
- **Parallel?**: No
- **Notes**: Use same per_unit_cost calculated for good units - ingredients consumed regardless of outcome

### Subtask T013 - Return loss data in result dict
- **Purpose**: Provide loss information to callers
- **File**: `src/services/batch_production_service.py`
- **Steps**:
  1. Update ProductionRun creation to include new fields:
     ```python
     production_run = ProductionRun(
         # ... existing fields ...
         production_status=production_status.value,
         loss_quantity=loss_quantity,
     )
     ```
  2. Update return dict to include:
     ```python
     return {
         # ... existing fields ...
         "production_status": production_status.value,
         "loss_quantity": loss_quantity,
         "loss_record_id": loss_record_id,  # None if no loss
         "total_loss_cost": str(loss_quantity * per_unit_cost) if loss_quantity > 0 else "0.0000",
     }
     ```
- **Parallel?**: No
- **Notes**: Convert enum to .value for JSON serialization

### Subtask T014 - Update get_production_history() with loss fields
- **Purpose**: Include loss data in history queries
- **File**: `src/services/batch_production_service.py`
- **Steps**:
  1. Update `_production_run_to_dict()` helper to include:
     ```python
     result["production_status"] = run.production_status
     result["loss_quantity"] = run.loss_quantity
     ```
  2. Verify these fields appear in all history query results
- **Parallel?**: Yes, with T015
- **Notes**: production_status is stored as string, return as-is

### Subtask T015 - Add eager-loading for losses relationship
- **Purpose**: Optionally load loss records without N+1 queries
- **File**: `src/services/batch_production_service.py`
- **Steps**:
  1. Add parameter to `get_production_history()`: `include_losses: bool = False`
  2. Add to query options when True:
     ```python
     if include_losses:
         query = query.options(joinedload(ProductionRun.losses))
     ```
  3. Update `_production_run_to_dict()` to include losses when available:
     ```python
     if include_losses and run.losses:
         result["losses"] = [
             {
                 "id": loss.id,
                 "loss_category": loss.loss_category,
                 "loss_quantity": loss.loss_quantity,
                 "per_unit_cost": str(loss.per_unit_cost),
                 "total_loss_cost": str(loss.total_loss_cost),
                 "notes": loss.notes,
             }
             for loss in run.losses
         ]
     ```
- **Parallel?**: Yes, with T014
- **Notes**: Default to False to avoid breaking existing callers

## Test Strategy

After completing all subtasks, run:
```bash
pytest src/tests/services/test_batch_production_service.py -v
```

Verify manually:
1. Record production with no loss - status should be COMPLETE
2. Record production with partial loss - status should be PARTIAL_LOSS, ProductionLoss created
3. Record production with total loss (actual_yield=0) - status should be TOTAL_LOSS
4. Attempt actual_yield > expected_yield - should raise ValueError

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | All operations in single session_scope block |
| Cost calculation mismatch | Use same per_unit_cost for both good and lost units |
| Enum serialization | Use .value when storing/returning enum values |
| Breaking existing callers | New parameters are optional with sensible defaults |

## Definition of Done Checklist

- [ ] loss_category and loss_notes parameters added to record_batch_production()
- [ ] Validation rejects actual_yield > expected_yield
- [ ] loss_quantity calculated correctly as expected - actual
- [ ] production_status determined: COMPLETE/PARTIAL_LOSS/TOTAL_LOSS
- [ ] ProductionLoss record created when loss_quantity > 0
- [ ] ProductionRun includes production_status and loss_quantity fields
- [ ] Result dict includes loss data
- [ ] get_production_history() returns production_status and loss_quantity
- [ ] Optional include_losses parameter works correctly
- [ ] Existing tests pass (no regressions)
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Verify validation happens BEFORE FIFO consumption
- Verify ProductionLoss uses same per_unit_cost as production run
- Check that all operations happen in same session
- Confirm enum values stored correctly (as strings)
- Test edge cases: 0 actual yield, exact expected yield

## Activity Log

- 2025-12-21T16:55:08Z - system - lane=planned - Prompt created.
- 2025-12-21T17:59:49Z – claude – shell_pid=64492 – lane=doing – Starting service layer implementation
- 2025-12-21T18:05:03Z – claude – shell_pid=65334 – lane=for_review – T009-T015 complete. All tests pass. Ready for review.
- 2025-12-21T19:10:05Z – claude-reviewer – shell_pid=74118 – lane=done – Code review APPROVED: Fail-fast validation before FIFO consumption, correct status logic, proper session management, cost snapshot preserved.
