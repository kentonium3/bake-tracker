---
work_package_id: WP04
title: Amendment Production Validation
lane: planned
dependencies:
- WP01
subtasks:
- T013
- T014
- T015
- T016
- T017
phase: Phase 2 - Core Features
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T06:03:15Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Amendment Production Validation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if work is returned from review.]*

---

## Implementation Command

```bash
# No dependencies on WP01 - can start from main
spec-kitty implement WP04
```

---

## Objectives & Success Criteria

**Objective**: Add validation to prevent MODIFY_BATCH and DROP_FG amendments when recipes have completed production records.

**Success Criteria**:
- [ ] MODIFY_BATCH is blocked for recipes with any ProductionRun records
- [ ] DROP_FG is blocked for finished goods where contributing recipes have production
- [ ] Amendments are allowed when no production exists
- [ ] Error messages clearly explain why amendment was rejected
- [ ] Tests cover: blocked with production, allowed without, clear error messages
- [ ] All existing tests pass

---

## Context & Constraints

**Feature**: F079 Production-Aware Planning Calculations
**Spec**: `kitty-specs/079-production-aware-planning-calculations/spec.md` (User Story 5)
**Plan**: `kitty-specs/079-production-aware-planning-calculations/plan.md`

**No dependencies**: This WP can run in parallel with WP02 and WP03.

**Key Constraints**:
- Must not break existing amendment functionality for events without production
- Error messages must include recipe/FG name for user clarity
- Must follow existing validation patterns in plan_amendment_service.py

**Existing Code Context**:
- File to modify: `src/services/plan_amendment_service.py`
- Key functions: `modify_batch_decision()`, `drop_finished_good()`
- Model: `ProductionRun` (for checking production existence)
- Existing validation: `_validate_amendment_allowed()` checks plan state

---

## Subtasks & Detailed Guidance

### Subtask T013 – Add _has_production_for_recipe() Helper Function

**Purpose**: Check if any production has been recorded for a recipe in an event.

**Steps**:
1. Open `src/services/plan_amendment_service.py`
2. Add import for ProductionRun model:
   ```python
   from src.models import Event, PlanAmendment, EventFinishedGood, BatchDecision, ProductionRun
   ```
3. Add helper function after `_get_event_or_raise()`:
   ```python
   def _has_production_for_recipe(
       event_id: int,
       recipe_id: int,
       session: Session
   ) -> bool:
       """Check if any production has been recorded for a recipe in an event.

       Args:
           event_id: Event to check
           recipe_id: Recipe to check
           session: Database session

       Returns:
           True if at least one ProductionRun exists for this recipe/event
       """
       count = session.query(ProductionRun).filter(
           ProductionRun.event_id == event_id,
           ProductionRun.recipe_id == recipe_id,
       ).count()
       return count > 0
   ```

**Files**: `src/services/plan_amendment_service.py`

**Notes**: Simple count query - returns True if any production exists.

---

### Subtask T014 – Add Validation to modify_batch_decision()

**Purpose**: Block batch modifications for recipes that have completed production.

**Steps**:
1. Locate `_modify_batch_decision_impl()` function (around line 294)
2. Add validation after `_validate_amendment_allowed()` check:
   ```python
   def _modify_batch_decision_impl(
       event_id: int,
       recipe_id: int,
       new_batches: int,
       reason: str,
       session: Session
   ) -> PlanAmendment:
       """Internal implementation of modify_batch_decision."""
       event = _get_event_or_raise(event_id, session)
       _validate_amendment_allowed(event, reason)

       # NEW: Check for existing production
       if _has_production_for_recipe(event_id, recipe_id, session):
           # Get recipe name for clear error message
           from src.models import Recipe
           recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
           recipe_name = recipe.name if recipe else f"Recipe {recipe_id}"
           raise ValidationError([
               f"Cannot modify batch decision for recipe '{recipe_name}' - "
               "production has already been recorded. "
               "Complete or void existing production first."
           ])

       # ... rest of existing code ...
   ```

**Files**: `src/services/plan_amendment_service.py`

**Notes**:
- Validation happens early, before any data modification
- Error message includes recipe name for user clarity
- Suggests next action (complete or void production)

---

### Subtask T015 – Add _get_recipes_for_finished_good() Helper

**Purpose**: Find all recipes that contribute to a finished good (for DROP_FG validation).

**Steps**:
1. Add helper function:
   ```python
   def _get_recipes_for_finished_good(
       fg_id: int,
       session: Session
   ) -> List[int]:
       """Get all recipe IDs that contribute to a finished good.

       A recipe contributes to an FG if:
       - The FG's composition includes a FinishedUnit
       - That FinishedUnit is produced by the recipe

       Args:
           fg_id: FinishedGood ID to check
           session: Database session

       Returns:
           List of recipe IDs that contribute to this FG
       """
       from src.models import Composition, FinishedUnit

       # Get all compositions for this FG
       compositions = (
           session.query(Composition)
           .filter(Composition.assembly_id == fg_id)
           .filter(Composition.finished_unit_id.isnot(None))
           .all()
       )

       recipe_ids = set()
       for comp in compositions:
           # Get the FinishedUnit and its recipe
           fu = session.get(FinishedUnit, comp.finished_unit_id)
           if fu and fu.recipe_id:
               recipe_ids.add(fu.recipe_id)

       return list(recipe_ids)
   ```

**Files**: `src/services/plan_amendment_service.py`

**Notes**:
- Traces Composition → FinishedUnit → Recipe
- Only considers FinishedUnit components (not nested FinishedGoods for now)
- Returns empty list if FG has no recipe-based components

---

### Subtask T016 – Add Validation to drop_finished_good()

**Purpose**: Block dropping FGs when their contributing recipes have production.

**Steps**:
1. Locate `_drop_finished_good_impl()` function (around line 120)
2. Add validation after `_validate_amendment_allowed()`:
   ```python
   def _drop_finished_good_impl(
       event_id: int,
       fg_id: int,
       reason: str,
       session: Session
   ) -> PlanAmendment:
       """Internal implementation of drop_finished_good."""
       event = _get_event_or_raise(event_id, session)
       _validate_amendment_allowed(event, reason)

       # NEW: Check for production on contributing recipes
       contributing_recipes = _get_recipes_for_finished_good(fg_id, session)
       recipes_with_production = []

       for recipe_id in contributing_recipes:
           if _has_production_for_recipe(event_id, recipe_id, session):
               from src.models import Recipe
               recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
               recipe_name = recipe.name if recipe else f"Recipe {recipe_id}"
               recipes_with_production.append(recipe_name)

       if recipes_with_production:
           # Get FG name for error message
           from src.models import FinishedGood
           fg = session.query(FinishedGood).filter(FinishedGood.id == fg_id).first()
           fg_name = fg.display_name if fg else f"Finished Good {fg_id}"
           raise ValidationError([
               f"Cannot drop finished good '{fg_name}' - production has been "
               f"recorded for contributing recipe(s): {', '.join(recipes_with_production)}. "
               "Complete or void production first."
           ])

       # ... rest of existing code ...
   ```

**Files**: `src/services/plan_amendment_service.py`

**Notes**:
- Check all contributing recipes, not just one
- List all recipes with production in error message
- FG without recipe components can still be dropped freely

---

### Subtask T017 – Write Tests for Amendment Validation

**Purpose**: Verify amendments are correctly blocked/allowed based on production status.

**Steps**:
1. Open `src/tests/test_plan_amendment_service.py`
2. Add tests for production validation:

```python
class TestAmendmentProductionValidation:
    """Tests for blocking amendments when production exists."""

    def test_modify_batch_blocked_when_production_exists(
        self, session, event_in_production, recipe_with_production
    ):
        """
        Given: Recipe has ProductionRun records
        When: modify_batch_decision() called
        Then: ValidationError raised with clear message
        """
        with pytest.raises(ValidationError) as exc_info:
            modify_batch_decision(
                event_in_production.id,
                recipe_with_production.id,
                new_batches=10,
                reason="Increase production",
                session=session,
            )

        assert "Cannot modify batch decision" in str(exc_info.value)
        assert recipe_with_production.name in str(exc_info.value)
        assert "production has already been recorded" in str(exc_info.value)

    def test_modify_batch_allowed_when_no_production(
        self, session, event_in_production, recipe_no_production
    ):
        """
        Given: Recipe has no ProductionRun records
        When: modify_batch_decision() called
        Then: Amendment succeeds
        """
        amendment = modify_batch_decision(
            event_in_production.id,
            recipe_no_production.id,
            new_batches=10,
            reason="Increase production",
            session=session,
        )

        assert amendment is not None
        assert amendment.amendment_type == AmendmentType.MODIFY_BATCH

    def test_drop_fg_blocked_when_contributing_recipe_has_production(
        self, session, event_in_production, fg_with_production
    ):
        """
        Given: FG's contributing recipe has ProductionRun records
        When: drop_finished_good() called
        Then: ValidationError raised listing the recipe
        """
        with pytest.raises(ValidationError) as exc_info:
            drop_finished_good(
                event_in_production.id,
                fg_with_production.id,
                reason="No longer needed",
                session=session,
            )

        assert "Cannot drop finished good" in str(exc_info.value)
        assert fg_with_production.display_name in str(exc_info.value)

    def test_drop_fg_allowed_when_no_production(
        self, session, event_in_production, fg_no_production
    ):
        """
        Given: FG's contributing recipes have no production
        When: drop_finished_good() called
        Then: Amendment succeeds
        """
        amendment = drop_finished_good(
            event_in_production.id,
            fg_no_production.id,
            reason="No longer needed",
            session=session,
        )

        assert amendment is not None
        assert amendment.amendment_type == AmendmentType.DROP_FG

    def test_add_fg_not_blocked_by_production(
        self, session, event_in_production, new_fg
    ):
        """ADD_FG should not be blocked by existing production."""
        amendment = add_finished_good(
            event_in_production.id,
            new_fg.id,
            quantity=5,
            reason="Adding new item",
            session=session,
        )

        assert amendment is not None
        assert amendment.amendment_type == AmendmentType.ADD_FG

    def test_error_message_includes_recipe_name(
        self, session, event_in_production, recipe_with_production
    ):
        """Error messages should include recipe name for clarity."""
        with pytest.raises(ValidationError) as exc_info:
            modify_batch_decision(
                event_in_production.id,
                recipe_with_production.id,
                new_batches=10,
                reason="Test",
                session=session,
            )

        # Recipe name should be in the error
        assert recipe_with_production.name in str(exc_info.value)


class TestGetRecipesForFinishedGood:
    """Tests for _get_recipes_for_finished_good helper."""

    def test_returns_recipe_ids_from_composition(
        self, session, fg_with_composition
    ):
        """Should return recipe IDs from FG's FinishedUnit components."""
        recipe_ids = _get_recipes_for_finished_good(
            fg_with_composition.id, session
        )

        assert len(recipe_ids) > 0
        assert all(isinstance(rid, int) for rid in recipe_ids)

    def test_returns_empty_for_fg_without_fu_components(
        self, session, fg_packaging_only
    ):
        """FG with only packaging (no FinishedUnits) returns empty list."""
        recipe_ids = _get_recipes_for_finished_good(
            fg_packaging_only.id, session
        )

        assert recipe_ids == []
```

3. Create necessary fixtures:
   - `event_in_production`: Event with plan_state=IN_PRODUCTION
   - `recipe_with_production`: Recipe with ProductionRun records
   - `recipe_no_production`: Recipe without any ProductionRun
   - `fg_with_production`: FinishedGood whose recipe has production
   - `fg_no_production`: FinishedGood whose recipe has no production

4. Run tests: `./run-tests.sh src/tests/test_plan_amendment_service.py -v`

**Files**: `src/tests/test_plan_amendment_service.py`

**Parallel?**: Yes - tests can be written alongside implementation

---

## Test Strategy

**Required Tests**:
- MODIFY_BATCH blocked with production, allowed without
- DROP_FG blocked with production, allowed without
- ADD_FG not affected by production (sanity check)
- Error messages include recipe/FG names
- Helper function correctly traces FG → recipes

**Commands**:
```bash
# Run amendment service tests
./run-tests.sh src/tests/test_plan_amendment_service.py -v

# Run with coverage
./run-tests.sh src/tests/test_plan_amendment_service.py -v --cov=src/services/plan_amendment_service
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FG → Recipe tracing misses some recipes | Medium | Medium | Test with various composition structures |
| Error messages unclear | Low | Medium | Include entity names and suggested actions |
| Performance with many compositions | Low | Low | Queries are simple counts; optimize if needed |

---

## Definition of Done Checklist

- [ ] `_has_production_for_recipe()` helper implemented
- [ ] `modify_batch_decision()` validates production status
- [ ] `_get_recipes_for_finished_good()` helper implemented
- [ ] `drop_finished_good()` validates production status
- [ ] Error messages include entity names
- [ ] Tests cover blocked/allowed scenarios
- [ ] All existing tests pass

---

## Review Guidance

**Key Checkpoints**:
1. Verify validation happens before any data modification
2. Verify error messages are user-friendly with entity names
3. Verify ADD_FG is not affected (only MODIFY_BATCH and DROP_FG)
4. Verify FG composition tracing handles edge cases (empty, nested)

---

## Activity Log

- 2026-01-28T06:03:15Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
