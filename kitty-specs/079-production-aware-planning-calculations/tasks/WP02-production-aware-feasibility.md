---
work_package_id: WP02
title: Production-Aware Feasibility
lane: "doing"
dependencies: [WP01]
base_branch: 079-production-aware-planning-calculations-WP01
base_commit: 2ef43f9ed9781cb38411cbfbb17660c86a9c15e8
created_at: '2026-01-28T06:17:32.902705+00:00'
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 2 - Core Features
assignee: ''
agent: ''
shell_pid: "96255"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T06:03:15Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Production-Aware Feasibility

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
# Depends on WP01 - branch from WP01 worktree
spec-kitty implement WP02 --base WP01
```

---

## Objectives & Success Criteria

**Objective**: Modify `check_production_feasibility()` to check ingredient availability for **remaining batches** instead of total planned batches when `production_aware=True` (the default).

**Success Criteria**:
- [ ] `check_production_feasibility()` accepts `production_aware: bool = True` parameter
- [ ] When `production_aware=True`, feasibility checks remaining batches (not total)
- [ ] When `production_aware=False`, feasibility checks total batches (backward compatibility)
- [ ] Recipes with all batches completed are marked as complete (no ingredient check needed)
- [ ] Tests verify: sufficient for remaining, insufficient for remaining, all complete, legacy mode
- [ ] All existing tests pass

---

## Context & Constraints

**Feature**: F079 Production-Aware Planning Calculations
**Spec**: `kitty-specs/079-production-aware-planning-calculations/spec.md` (User Story 2)
**Plan**: `kitty-specs/079-production-aware-planning-calculations/plan.md`

**Dependency**: This WP depends on WP01 for `get_remaining_production_needs()`.

**Key Constraints**:
- Must maintain backward compatibility (existing callers get new behavior by default)
- Must follow session management pattern
- Must not duplicate remaining calculation logic (import from progress module)

**Existing Code Context**:
- File to modify: `src/services/planning/feasibility.py`
- Key function: `check_production_feasibility()` (lines 206-269)
- Uses: `batch_production_service.check_can_produce()` for ingredient checks
- Integration: Import `get_remaining_production_needs` from progress module

---

## Subtasks & Detailed Guidance

### Subtask T005 – Add production_aware Parameter to Function Signature

**Purpose**: Add the parameter that controls whether to check total or remaining batches.

**Steps**:
1. Open `src/services/planning/feasibility.py`
2. Locate `check_production_feasibility()` function (line 206)
3. Add parameter to signature:
   ```python
   def check_production_feasibility(
       event_id: int,
       *,
       production_aware: bool = True,  # NEW
       session: Optional[Session] = None,
   ) -> List[Dict[str, Any]]:
   ```
4. Update the docstring:
   ```python
   """Check production feasibility for all production targets of an event.

   Wraps batch_production_service.check_can_produce() for each EventProductionTarget
   to determine if recipes can be produced with current inventory.

   Args:
       event_id: Event to check production targets for
       production_aware: If True (default), check remaining batches only.
                        If False, check total planned batches (legacy behavior).
       session: Optional database session

   Returns:
       List of dicts with recipe feasibility status
   """
   ```
5. Pass parameter to implementation function:
   ```python
   if session is not None:
       return _check_production_feasibility_impl(event_id, production_aware, session)
   with session_scope() as session:
       return _check_production_feasibility_impl(event_id, production_aware, session)
   ```

**Files**: `src/services/planning/feasibility.py`

---

### Subtask T006 – Import get_remaining_production_needs from Progress Module

**Purpose**: Access the remaining batches calculation from the progress module.

**Steps**:
1. Add import at top of `feasibility.py`:
   ```python
   from src.services.planning.progress import get_remaining_production_needs
   ```
2. Verify the import works by checking progress.py exports the function

**Files**: `src/services/planning/feasibility.py`

**Notes**: The import establishes the dependency on WP01's work.

---

### Subtask T007 – Modify Implementation to Use Remaining Batches

**Purpose**: When production_aware=True, check ingredient availability for remaining batches only.

**Steps**:
1. Locate `_check_production_feasibility_impl()` function (line 234)
2. Update function signature to accept production_aware:
   ```python
   def _check_production_feasibility_impl(
       event_id: int,
       production_aware: bool,
       session: Session,
   ) -> List[Dict[str, Any]]:
   ```
3. At the start of the function, get remaining needs if production_aware:
   ```python
   # Get remaining batches per recipe if production-aware
   remaining_by_recipe = {}
   if production_aware:
       remaining_by_recipe = get_remaining_production_needs(event_id, session=session)
   ```
4. In the loop over targets, determine batches to check:
   ```python
   for target in targets:
       recipe_name = target.recipe.name if target.recipe else f"Recipe {target.recipe_id}"

       # Determine how many batches to check
       if production_aware:
           batches_to_check = remaining_by_recipe.get(target.recipe_id, target.target_batches)
       else:
           batches_to_check = target.target_batches

       # Skip if no batches remaining (all complete)
       if batches_to_check == 0:
           results.append({
               "recipe_id": target.recipe_id,
               "recipe_name": recipe_name,
               "target_batches": target.target_batches,
               "remaining_batches": 0,
               "can_produce": True,  # Already complete
               "missing": [],
               "status": "COMPLETE",
           })
           continue

       # Check feasibility for the batches we need to produce
       check_result = batch_production_service.check_can_produce(
           target.recipe_id,
           batches_to_check,  # Use remaining, not total
           session=session,
       )

       results.append({
           "recipe_id": target.recipe_id,
           "recipe_name": recipe_name,
           "target_batches": target.target_batches,
           "remaining_batches": batches_to_check if production_aware else None,
           "can_produce": check_result["can_produce"],
           "missing": check_result["missing"],
       })
   ```

**Files**: `src/services/planning/feasibility.py`

**Notes**:
- When `remaining_batches == 0`, skip the ingredient check entirely (return COMPLETE status)
- Include `remaining_batches` in result dict for UI display
- Keep existing behavior when `production_aware=False`

---

### Subtask T008 – Write Tests for Production-Aware Feasibility

**Purpose**: Verify feasibility correctly uses remaining batches.

**Steps**:
1. Open or create `src/tests/planning/test_feasibility.py`
2. Add tests for production-aware scenarios:

```python
class TestProductionAwareFeasibility:
    """Tests for production-aware feasibility checking."""

    def test_sufficient_inventory_for_remaining_shows_can_produce(
        self, session, event_partial_production, inventory_for_3_batches
    ):
        """
        Given: 10 target batches, 7 completed, inventory sufficient for 3
        When: check_production_feasibility(production_aware=True)
        Then: can_produce is True (only checking remaining 3)
        """
        results = check_production_feasibility(
            event_partial_production.id,
            production_aware=True,
            session=session,
        )

        assert len(results) == 1
        assert results[0]["can_produce"] is True
        assert results[0]["remaining_batches"] == 3

    def test_insufficient_inventory_for_remaining_shows_missing(
        self, session, event_partial_production, inventory_for_1_batch
    ):
        """
        Given: 10 target batches, 7 completed, inventory sufficient for 1 batch
        When: check_production_feasibility(production_aware=True)
        Then: can_produce is False with missing ingredients for 2 batches
        """
        results = check_production_feasibility(
            event_partial_production.id,
            production_aware=True,
            session=session,
        )

        assert results[0]["can_produce"] is False
        assert len(results[0]["missing"]) > 0

    def test_all_batches_complete_shows_complete_status(
        self, session, event_all_complete
    ):
        """
        Given: 5 target batches, 5 completed
        When: check_production_feasibility(production_aware=True)
        Then: status is COMPLETE, no ingredient check performed
        """
        results = check_production_feasibility(
            event_all_complete.id,
            production_aware=True,
            session=session,
        )

        assert results[0]["remaining_batches"] == 0
        assert results[0]["can_produce"] is True
        assert results[0].get("status") == "COMPLETE"

    def test_legacy_mode_checks_total_batches(
        self, session, event_partial_production, inventory_for_3_batches
    ):
        """
        Given: 10 target batches, 7 completed, inventory for 3
        When: check_production_feasibility(production_aware=False)
        Then: can_produce is False (checking all 10 batches)
        """
        results = check_production_feasibility(
            event_partial_production.id,
            production_aware=False,  # Legacy mode
            session=session,
        )

        # With only inventory for 3 batches, checking 10 should fail
        assert results[0]["can_produce"] is False

    def test_default_is_production_aware(self, session, event_partial_production):
        """Default behavior should be production_aware=True."""
        # Call without explicit parameter
        results = check_production_feasibility(
            event_partial_production.id,
            session=session,
        )

        # Should check remaining, not total
        assert results[0].get("remaining_batches") is not None
```

3. Create necessary fixtures:
   - `event_partial_production`: Event with 10 target batches, 7 ProductionRun records
   - `event_all_complete`: Event with 5 target batches, 5 completed
   - `inventory_for_3_batches`: Inventory sufficient for exactly 3 batches

4. Run tests: `./run-tests.sh src/tests/planning/test_feasibility.py -v`

**Files**: `src/tests/planning/test_feasibility.py`

**Parallel?**: Yes - tests can be written alongside implementation

---

## Test Strategy

**Required Tests**:
- Sufficient inventory for remaining batches → can_produce = True
- Insufficient inventory for remaining → can_produce = False with missing list
- All batches complete → COMPLETE status, no ingredient check
- Legacy mode (production_aware=False) → checks total batches
- Default parameter is True

**Commands**:
```bash
# Run feasibility tests
./run-tests.sh src/tests/planning/test_feasibility.py -v

# Run with coverage
./run-tests.sh src/tests/planning/test_feasibility.py -v --cov=src/services/planning/feasibility
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing callers | Low | High | Default production_aware=True is new but sensible |
| Incorrect remaining lookup | Low | Medium | Use get() with fallback to target_batches |
| Missing session propagation | Medium | High | Pass session to get_remaining_production_needs() |

---

## Definition of Done Checklist

- [ ] `check_production_feasibility()` has `production_aware` parameter
- [ ] Implementation uses remaining batches when production_aware=True
- [ ] Complete recipes (remaining=0) return COMPLETE status
- [ ] Legacy mode (production_aware=False) checks total batches
- [ ] Tests cover all scenarios
- [ ] All existing tests pass
- [ ] Session management pattern followed

---

## Review Guidance

**Key Checkpoints**:
1. Verify session is passed to `get_remaining_production_needs()`
2. Verify `remaining_by_recipe.get()` has sensible fallback
3. Verify COMPLETE status is returned when remaining=0 (no ingredient check)
4. Verify legacy mode still works for backward compatibility

---

## Activity Log

- 2026-01-28T06:03:15Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
