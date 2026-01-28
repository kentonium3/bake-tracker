---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Remaining Needs Calculation"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-28T06:03:15Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Remaining Needs Calculation

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
# No dependencies - start from main
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

**Objective**: Extend the `ProductionProgress` dataclass with `remaining_batches` and `overage_batches` fields, and add a helper function for downstream consumers (feasibility, shopping list).

**Success Criteria**:
- [ ] ProductionProgress DTO includes `remaining_batches: int` and `overage_batches: int` fields
- [ ] `remaining_batches = max(0, target_batches - completed_batches)` calculation is correct
- [ ] `overage_batches = max(0, completed_batches - target_batches)` calculation is correct
- [ ] `get_remaining_production_needs()` returns `Dict[int, int]` mapping recipe_id → remaining_batches
- [ ] Tests cover: partial completion, exact completion, overage, zero target, no production records
- [ ] All existing tests pass (no regressions)

---

## Context & Constraints

**Feature**: F079 Production-Aware Planning Calculations
**Spec**: `kitty-specs/079-production-aware-planning-calculations/spec.md`
**Plan**: `kitty-specs/079-production-aware-planning-calculations/plan.md`
**Data Model**: `kitty-specs/079-production-aware-planning-calculations/data-model.md`

**Key Constraints**:
- Must not break existing callers of `ProductionProgress` (additive change only)
- Must follow session management pattern from CLAUDE.md (accept `session=None`)
- Must maintain >70% test coverage per constitution

**Existing Code Context**:
- File to modify: `src/services/planning/progress.py`
- Test file: `src/tests/planning/test_progress.py`
- Related: `event_service.get_production_progress()` provides raw data

---

## Subtasks & Detailed Guidance

### Subtask T001 – Extend ProductionProgress Dataclass

**Purpose**: Add two new fields to track remaining work and overage production.

**Steps**:
1. Open `src/services/planning/progress.py`
2. Locate the `ProductionProgress` dataclass (around line 24)
3. Add two new fields after `completed_batches`:
   ```python
   @dataclass
   class ProductionProgress:
       recipe_id: int
       recipe_name: str
       target_batches: int
       completed_batches: int
       remaining_batches: int      # NEW: max(0, target - completed)
       overage_batches: int        # NEW: max(0, completed - target)
       progress_percent: float
       is_complete: bool
   ```
4. Update the docstring to document the new fields

**Files**: `src/services/planning/progress.py`

**Notes**: Field order matters for dataclass - add between `completed_batches` and `progress_percent` for logical grouping.

---

### Subtask T002 – Update Implementation to Calculate Remaining/Overage

**Purpose**: Compute the new fields when creating ProductionProgress instances.

**Steps**:
1. Locate `_get_production_progress_impl()` function (around line 91)
2. After calculating `completed` from `item["produced_batches"]`, add:
   ```python
   # Calculate remaining and overage
   remaining = max(0, target - completed)
   overage = max(0, completed - target)
   ```
3. Update the ProductionProgress constructor call to include new fields:
   ```python
   results.append(
       ProductionProgress(
           recipe_id=item["recipe_id"],
           recipe_name=item["recipe_name"],
           target_batches=target,
           completed_batches=completed,
           remaining_batches=remaining,      # NEW
           overage_batches=overage,          # NEW
           progress_percent=progress_percent,
           is_complete=completed >= target,
       )
   )
   ```

**Files**: `src/services/planning/progress.py`

**Notes**:
- `max(0, ...)` ensures we never return negative values
- When completed > target, remaining is 0 and overage is the excess

---

### Subtask T003 – Add get_remaining_production_needs() Helper Function

**Purpose**: Provide a convenience function for downstream services to get remaining batches by recipe.

**Steps**:
1. Add new function after `get_production_progress()`:
   ```python
   def get_remaining_production_needs(
       event_id: int,
       *,
       session: Optional[Session] = None,
   ) -> Dict[int, int]:
       """Get remaining batches needed per recipe.

       Convenience function that returns a mapping from recipe_id to
       remaining_batches for use by feasibility and shopping list services.

       Args:
           event_id: Event to get remaining needs for
           session: Optional database session

       Returns:
           Dict mapping recipe_id -> remaining_batches (0 if complete)
       """
       progress_list = get_production_progress(event_id, session=session)
       return {p.recipe_id: p.remaining_batches for p in progress_list}
   ```
2. Add import for `Dict` from typing if not present
3. Export the function in module's `__all__` if one exists

**Files**: `src/services/planning/progress.py`

**Notes**: This function wraps get_production_progress() and extracts just the remaining counts into a dict for easy lookup.

---

### Subtask T004 – Write Tests for Remaining Calculation

**Purpose**: Ensure remaining/overage calculation is correct for all edge cases.

**Steps**:
1. Open or create `src/tests/planning/test_progress.py`
2. Add test fixtures for events with various production states
3. Write tests for these scenarios:

```python
class TestRemainingCalculation:
    """Tests for remaining_batches and overage_batches calculation."""

    def test_partial_completion_shows_remaining(self, session, event_with_production):
        """Given 5 target batches and 3 completed, remaining should be 2."""
        # Setup: event with target_batches=5, completed=3
        progress = get_production_progress(event_with_production.id, session=session)
        recipe_progress = progress[0]

        assert recipe_progress.target_batches == 5
        assert recipe_progress.completed_batches == 3
        assert recipe_progress.remaining_batches == 2
        assert recipe_progress.overage_batches == 0

    def test_exact_completion_shows_zero_remaining(self, session, event_exact_completion):
        """Given 5 target and 5 completed, remaining should be 0."""
        progress = get_production_progress(event_exact_completion.id, session=session)
        recipe_progress = progress[0]

        assert recipe_progress.remaining_batches == 0
        assert recipe_progress.overage_batches == 0
        assert recipe_progress.is_complete is True

    def test_overage_shows_zero_remaining_with_overage_count(self, session, event_with_overage):
        """Given 5 target and 7 completed, remaining=0 and overage=2."""
        progress = get_production_progress(event_with_overage.id, session=session)
        recipe_progress = progress[0]

        assert recipe_progress.target_batches == 5
        assert recipe_progress.completed_batches == 7
        assert recipe_progress.remaining_batches == 0  # Never negative
        assert recipe_progress.overage_batches == 2

    def test_no_production_shows_full_remaining(self, session, event_no_production):
        """Given 5 target and 0 completed, remaining equals target."""
        progress = get_production_progress(event_no_production.id, session=session)
        recipe_progress = progress[0]

        assert recipe_progress.remaining_batches == 5
        assert recipe_progress.overage_batches == 0

    def test_zero_target_shows_zero_remaining(self, session, event_zero_target):
        """Edge case: 0 target batches should show 0 remaining."""
        progress = get_production_progress(event_zero_target.id, session=session)
        recipe_progress = progress[0]

        assert recipe_progress.target_batches == 0
        assert recipe_progress.remaining_batches == 0


class TestGetRemainingProductionNeeds:
    """Tests for get_remaining_production_needs() helper function."""

    def test_returns_dict_of_recipe_id_to_remaining(self, session, event_with_production):
        """Function returns {recipe_id: remaining_batches} dict."""
        needs = get_remaining_production_needs(event_with_production.id, session=session)

        assert isinstance(needs, dict)
        # Check specific recipe has expected remaining
        assert needs[recipe_id] == expected_remaining

    def test_multiple_recipes_returns_all(self, session, event_multiple_recipes):
        """All recipes in event are included in result."""
        needs = get_remaining_production_needs(event_multiple_recipes.id, session=session)

        assert len(needs) == 3  # Event has 3 recipes
        assert all(isinstance(v, int) for v in needs.values())
```

4. Create necessary fixtures using existing patterns in the test file
5. Run tests: `./run-tests.sh src/tests/planning/test_progress.py -v`

**Files**: `src/tests/planning/test_progress.py`

**Notes**:
- Use existing fixture patterns from the test file
- May need to create ProductionRun records to simulate completed production
- Test both the DTO fields and the helper function

---

## Test Strategy

**Required Tests** (per constitution >70% coverage):
- Unit tests for remaining/overage calculation logic
- Edge case tests: zero, partial, exact, overage
- Helper function tests for get_remaining_production_needs()

**Commands**:
```bash
# Run progress tests
./run-tests.sh src/tests/planning/test_progress.py -v

# Run with coverage
./run-tests.sh src/tests/planning/test_progress.py -v --cov=src/services/planning/progress
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing callers | Low | High | New fields are additive; existing code ignores them |
| Incorrect max(0, ...) logic | Low | Medium | Comprehensive test coverage for edge cases |
| Performance regression | Very Low | Low | Simple arithmetic; no new queries |

---

## Definition of Done Checklist

- [ ] ProductionProgress has remaining_batches and overage_batches fields
- [ ] Calculation logic is implemented in _get_production_progress_impl()
- [ ] get_remaining_production_needs() helper function added
- [ ] Tests cover all edge cases (partial, exact, overage, zero)
- [ ] All existing tests pass
- [ ] Code follows session management pattern
- [ ] No linting errors

---

## Review Guidance

**Key Checkpoints**:
1. Verify `max(0, ...)` is used for both calculations (never negative)
2. Verify ProductionProgress field order is sensible
3. Verify tests cover the overage scenario (completed > target)
4. Verify helper function passes session through correctly

---

## Activity Log

- 2026-01-28T06:03:15Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
