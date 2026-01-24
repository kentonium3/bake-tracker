---
work_package_id: WP07
title: On-Demand Calculation
lane: "doing"
dependencies:
- WP01
subtasks:
- T029
- T030
- T031
- T032
- T033
- T034
phase: Phase 4 - On-Demand Calculation
assignee: ''
agent: "claude-opus"
shell_pid: "98086"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-24T19:47:15Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – On-Demand Calculation

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
# Depends on WP01 (cache fields removed) and WP04 (snapshots exist)
spec-kitty implement WP07 --base WP04 --feature 065-production-plan-snapshot-refactor
```

---

## Objectives & Success Criteria

Replace cached calculation_results with on-demand calculation from linked snapshots.

**Success Criteria**:
- [ ] get_plan_summary() function calculates batch requirements from snapshots
- [ ] get_plan_summary() calculates shopping list from snapshots
- [ ] get_plan_summary() aggregates ingredients from snapshots
- [ ] Staleness detection code removed
- [ ] Performance: calculation completes in <5 seconds
- [ ] Return format compatible with UI expectations

## Context & Constraints

**Reference Documents**:
- `kitty-specs/065-production-plan-snapshot-refactor/research.md` - RQ-3 (planning workflow)
- `kitty-specs/065-production-plan-snapshot-refactor/spec.md` - SC-005 (5 second performance target)
- `kitty-specs/065-production-plan-snapshot-refactor/plan.md` - Phase 4 details

**New Workflow** (replaces cached results):
1. Load event with targets and linked snapshots (eager load)
2. Calculate batch requirements from snapshot data
3. Calculate shopping list from snapshot ingredient data
4. Aggregate ingredients from all snapshots
5. Return calculated results (no caching)

**Key Constraints**:
- Must match old return format for UI compatibility
- Must complete in <5 seconds for typical events
- Must handle missing snapshots gracefully (fallback to live definitions)

## Subtasks & Detailed Guidance

### Subtask T029 – Create get_plan_summary() function

**Purpose**: New entry point for on-demand calculation (replaces reading cached results).

**Steps**:
1. In `src/services/planning/planning_service.py`, add new function:
   ```python
   def get_plan_summary(
       event_id: int,
       session=None
   ) -> dict:
       """Get production plan summary calculated on-demand from snapshots.

       Unlike cached calculation_results, this calculates fresh each time
       using the immutable snapshots linked to production/assembly targets.

       Args:
           event_id: Event to get plan summary for
           session: Optional session for query management

       Returns:
           dict with:
           - recipe_batches: List of {recipe_name, batches_needed, ...}
           - shopping_list: List of {ingredient_name, quantity, unit, ...}
           - aggregated_ingredients: Dict of ingredient totals

       Performance: Designed to complete in <5 seconds for typical events.
       """
       if session is not None:
           return _get_plan_summary_impl(event_id, session)
       with session_scope() as session:
           return _get_plan_summary_impl(event_id, session)
   ```

2. Create implementation skeleton:
   ```python
   def _get_plan_summary_impl(event_id: int, session) -> dict:
       # Eager load event with targets and snapshots
       event = session.query(Event).options(
           joinedload(Event.production_targets).joinedload(EventProductionTarget.recipe_snapshot),
           joinedload(Event.assembly_targets).joinedload(EventAssemblyTarget.finished_good_snapshot)
       ).filter(Event.id == event_id).first()

       if not event:
           raise ValueError(f"Event {event_id} not found")

       # Calculate each component
       recipe_batches = _calculate_recipe_batches(event, session)
       shopping_list = _calculate_shopping_list(event, session)
       aggregated_ingredients = _aggregate_ingredients(event, session)

       return {
           "recipe_batches": recipe_batches,
           "shopping_list": shopping_list,
           "aggregated_ingredients": aggregated_ingredients
       }
   ```

**Files**:
- `src/services/planning/planning_service.py` (modify)

**Parallel?**: No - foundation for T030-T032

---

### Subtask T030 – Implement batch requirements calculation from snapshots

**Purpose**: Calculate how many batches of each recipe are needed, using snapshot data.

**Steps**:
1. Create helper function:
   ```python
   def _calculate_recipe_batches(event: Event, session) -> list:
       """Calculate recipe batch requirements from target snapshots.

       Returns list of dicts with recipe info and batch requirements.
       """
       batches = []
       for target in event.production_targets:
           # Get recipe data from snapshot if available
           if target.recipe_snapshot:
               recipe_data = json.loads(target.recipe_snapshot.recipe_data)
               recipe_name = recipe_data.get("name", f"Recipe {target.recipe_id}")
           else:
               # Fallback: use live recipe (legacy compatibility)
               recipe = session.get(Recipe, target.recipe_id)
               recipe_name = recipe.name if recipe else f"Recipe {target.recipe_id}"
               recipe_data = recipe.to_dict() if recipe else {}

           batches.append({
               "recipe_id": target.recipe_id,
               "recipe_name": recipe_name,
               "target_batches": target.target_batches,
               "recipe_snapshot_id": target.recipe_snapshot_id,
               "recipe_data": recipe_data
           })

       return batches
   ```

2. Match old format if different (check what UI expects)

**Files**:
- `src/services/planning/planning_service.py` (modify)

**Parallel?**: Yes - can be developed alongside T031, T032

---

### Subtask T031 – Implement shopping list calculation from snapshots

**Purpose**: Calculate shopping list (ingredients needed) from snapshot data.

**Steps**:
1. Create helper function:
   ```python
   def _calculate_shopping_list(event: Event, session) -> list:
       """Calculate shopping list from target snapshot ingredient data.

       Aggregates all ingredients needed across all recipe snapshots,
       accounting for batch quantities.
       """
       ingredients_needed = {}  # {ingredient_id: {name, quantity, unit}}

       for target in event.production_targets:
           # Get ingredients from snapshot
           if target.recipe_snapshot:
               ingredients_data = json.loads(target.recipe_snapshot.ingredients_data)
           else:
               # Fallback: use live recipe ingredients
               recipe = session.get(Recipe, target.recipe_id)
               ingredients_data = [ing.to_dict() for ing in recipe.ingredients] if recipe else []

           # Scale by batch count
           batch_multiplier = target.target_batches

           for ing in ingredients_data:
               ing_id = ing.get("ingredient_id") or ing.get("id")
               quantity = (ing.get("quantity") or 0) * batch_multiplier
               unit = ing.get("unit", "")
               name = ing.get("name", f"Ingredient {ing_id}")

               if ing_id in ingredients_needed:
                   ingredients_needed[ing_id]["quantity"] += quantity
               else:
                   ingredients_needed[ing_id] = {
                       "ingredient_id": ing_id,
                       "name": name,
                       "quantity": quantity,
                       "unit": unit
                   }

       return list(ingredients_needed.values())
   ```

**Files**:
- `src/services/planning/planning_service.py` (modify)

**Parallel?**: Yes - can be developed alongside T030, T032

---

### Subtask T032 – Implement ingredient aggregation from snapshots

**Purpose**: Provide aggregated ingredient totals (may be same as shopping list or different format).

**Steps**:
1. Create helper function:
   ```python
   def _aggregate_ingredients(event: Event, session) -> dict:
       """Aggregate ingredients across all snapshots.

       Returns dict keyed by ingredient, with totals.
       This may duplicate shopping_list logic but provides
       a dict format for different consumers.
       """
       # Reuse shopping list calculation
       shopping_list = _calculate_shopping_list(event, session)

       # Convert to dict format
       aggregated = {}
       for item in shopping_list:
           key = item["name"]
           aggregated[key] = {
               "ingredient_id": item["ingredient_id"],
               "total_quantity": item["quantity"],
               "unit": item["unit"]
           }

       return aggregated
   ```

2. Verify this matches what old get_aggregated_ingredients() returned

**Files**:
- `src/services/planning/planning_service.py` (modify)

**Parallel?**: Yes - can be developed alongside T030, T031

---

### Subtask T033 – Remove staleness detection code

**Purpose**: Clean up old staleness detection that's no longer needed.

**Steps**:
1. In `src/services/planning/planning_service.py`, find and remove:
   - `_check_staleness_impl()` function
   - `_get_latest_requirements_timestamp()` function
   - `_get_latest_recipes_timestamp()` function
   - `_get_latest_bundles_timestamp()` function
   - Any calls to these functions
   - Any staleness-related logic in calculate_plan()

2. Search for staleness references:
   ```bash
   grep -rn "staleness\|stale\|_check_staleness" src/services/planning/
   ```

3. Remove or comment out identified code

4. Update imports if any become unused

**Files**:
- `src/services/planning/planning_service.py` (modify)

**Parallel?**: No - cleanup after T029-T032

---

### Subtask T034 – Performance verification

**Purpose**: Ensure on-demand calculation meets <5 second target.

**Steps**:
1. Create performance test:
   ```python
   import time

   def test_get_plan_summary_performance(db_session):
       """Verify get_plan_summary completes in <5 seconds."""
       # Setup: create event with typical number of targets
       event = create_event_with_targets(
           db_session,
           production_target_count=20,  # Typical event size
           assembly_target_count=10
       )

       # Create plan (creates snapshots)
       create_plan(event.id, session=db_session)

       # Time the calculation
       start = time.time()
       result = get_plan_summary(event.id, session=db_session)
       elapsed = time.time() - start

       # Assert
       assert elapsed < 5.0, f"get_plan_summary took {elapsed:.2f}s, expected <5s"
       assert "recipe_batches" in result
       assert "shopping_list" in result
   ```

2. Run with profiling if slow:
   ```bash
   python -m cProfile -o profile.out -c "
   from src.services.planning.planning_service import get_plan_summary
   # ... test code
   "
   ```

3. Optimize if needed:
   - Ensure eager loading is working (check SQL queries)
   - Consider caching JSON.loads results
   - Batch database queries if possible

**Files**:
- `src/tests/unit/test_planning_service.py` (add test)

**Parallel?**: No - requires T029-T032 complete

---

## Test Strategy

**Run Tests**:
```bash
./run-tests.sh src/tests/unit/test_planning_service.py -v -k "get_plan_summary"
```

**Performance Test**:
```bash
./run-tests.sh src/tests/unit/test_planning_service.py -v -k "performance"
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance regression | Profile and optimize; eager loading |
| Different results than cached | Compare outputs; verify calculation logic |
| Missing snapshot data | Fallback to live definitions |
| UI expects different format | Match old return structure |

## Definition of Done Checklist

- [ ] get_plan_summary() function implemented
- [ ] Batch requirements calculated from snapshots
- [ ] Shopping list calculated from snapshots
- [ ] Ingredient aggregation implemented
- [ ] Staleness detection code removed
- [ ] Performance <5 seconds verified
- [ ] Legacy fallback works (missing snapshots)
- [ ] Activity log entry added

## Review Guidance

Reviewers should verify:
1. Return format matches old calculate_plan() output
2. Eager loading prevents N+1 queries
3. JSON parsing handles edge cases
4. Performance test passes
5. Staleness code fully removed

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-24T19:47:15Z – system – lane=planned – Prompt created.
- 2026-01-24T22:54:42Z – claude-opus – shell_pid=93958 – lane=doing – Started implementation via workflow command
- 2026-01-24T23:15:12Z – claude-opus – shell_pid=93958 – lane=for_review – Ready for review: Implemented on-demand calculation from snapshots, deprecated staleness detection, added tests
- 2026-01-24T23:32:07Z – claude-opus – shell_pid=98086 – lane=doing – Started review via workflow command
