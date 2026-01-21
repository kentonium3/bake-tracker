---
work_package_id: "WP04"
subtasks:
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "Planning Snapshot Aggregated Ingredients"
phase: "Phase 2 - Parallel Track"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "8216"
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-20T20:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Planning Snapshot Aggregated Ingredients

## Implementation Command

```bash
spec-kitty implement WP04 --base WP01
```

Depends on WP01 (session pattern for recipe service calls).

**Codex Parallelizable**: YES - This WP can be assigned to Codex for parallel execution with WP05, WP06, WP07 after WP01 completes.

---

## Objectives & Success Criteria

**Primary Objective**: Complete the TODO at line 293 of planning_service.py to populate aggregated ingredients in planning snapshots.

**Success Criteria**:
1. Planning snapshots include `aggregated_ingredients` array
2. Each ingredient has: slug, display_name, quantity, unit, cost_per_unit
3. Yield ratios from recipes are correctly applied
4. Cost is snapshotted at calculation time (not live lookup)
5. Export/import preserves aggregated ingredients

**Key Acceptance Checkpoints**:
- [ ] `calculation_results["aggregated_ingredients"]` is populated (not empty list)
- [ ] Ingredient quantities respect recipe yield ratios
- [ ] Cost per unit is captured at snapshot time
- [ ] Export/import round-trip preserves data

---

## Context & Constraints

### Supporting Documents
- **Research**: `kitty-specs/060-architecture-hardening-service-boundaries/research.md` - Section 4 (Staleness gaps, TODO)
- **Data Model**: `kitty-specs/060-architecture-hardening-service-boundaries/data-model.md` - Planning Snapshot Extensions
- **Plan**: `kitty-specs/060-architecture-hardening-service-boundaries/plan.md` - WP04 section

### File Location
- `src/services/planning/planning_service.py` line 293:
  ```python
  "aggregated_ingredients": []  # TODO: Populate from recipe aggregation
  ```

### Target Structure (from data-model.md)
```python
"aggregated_ingredients": [
    {
        "ingredient_slug": "flour-all-purpose",
        "display_name": "All-Purpose Flour",
        "quantity": 2.5,
        "unit": "kg",
        "cost_per_unit": 1.50
    },
    # ... more ingredients
]
```

### Existing Helper
- `recipe_service.get_aggregated_ingredients()` already exists and accepts session parameter
- Use this function to get ingredients for each recipe, then aggregate across all recipes in plan

---

## Subtasks & Detailed Guidance

### Subtask T016 – Implement aggregated ingredient calculation

**Purpose**: Calculate total ingredients needed across all recipes in the production plan.

**Steps**:

1. Open `src/services/planning/planning_service.py`

2. Locate the TODO at line ~293 in `_calculate_plan_impl()` or similar

3. Identify where recipe batch requirements are calculated (should be nearby)

4. Implement aggregation logic:
   ```python
   def _aggregate_plan_ingredients(batch_requirements: List[Dict], session) -> List[Dict]:
       """
       Aggregate ingredients across all recipe batches in the plan.

       Args:
           batch_requirements: List of {"recipe_id": int, "batches": int, "scale_factor": float}
           session: SQLAlchemy session

       Returns:
           List of aggregated ingredients with totals
       """
       from collections import defaultdict
       from src.services.recipe_service import get_aggregated_ingredients

       # Aggregate by ingredient slug
       totals = defaultdict(lambda: {
           "ingredient_slug": "",
           "display_name": "",
           "quantity": 0.0,
           "unit": "",
           "cost_per_unit": 0.0,
           "cost_sources": []  # Track for weighted average
       })

       for req in batch_requirements:
           recipe_id = req["recipe_id"]
           batches = req["batches"]
           scale_factor = req.get("scale_factor", 1.0)

           # Get ingredients for this recipe
           multiplier = batches * scale_factor
           ingredients = get_aggregated_ingredients(
               recipe_id, multiplier=multiplier, session=session
           )

           for ing in ingredients:
               slug = ing["ingredient_slug"]
               totals[slug]["ingredient_slug"] = slug
               totals[slug]["display_name"] = ing["display_name"]
               totals[slug]["unit"] = ing["unit"]
               totals[slug]["quantity"] += ing["quantity"]

               # Track cost for weighted average
               if ing.get("cost_per_unit"):
                   totals[slug]["cost_sources"].append({
                       "quantity": ing["quantity"],
                       "cost": ing["cost_per_unit"]
                   })

       # Calculate weighted average cost per unit
       result = []
       for slug, data in totals.items():
           cost_per_unit = 0.0
           if data["cost_sources"]:
               total_qty = sum(s["quantity"] for s in data["cost_sources"])
               if total_qty > 0:
                   cost_per_unit = sum(
                       s["quantity"] * s["cost"] for s in data["cost_sources"]
                   ) / total_qty

           result.append({
               "ingredient_slug": data["ingredient_slug"],
               "display_name": data["display_name"],
               "quantity": data["quantity"],
               "unit": data["unit"],
               "cost_per_unit": cost_per_unit
           })

       return sorted(result, key=lambda x: x["display_name"])
   ```

5. Call this function and populate the TODO:
   ```python
   # Replace the TODO line
   aggregated_ingredients = _aggregate_plan_ingredients(batch_requirements, session)

   calculation_results = {
       # ... existing fields ...
       "aggregated_ingredients": aggregated_ingredients,  # Was []
   }
   ```

**Files**:
- `src/services/planning/planning_service.py` (add ~60 lines)

**Parallel?**: No - foundational for T017-T019

**Notes**:
- Use existing `get_aggregated_ingredients()` - don't reinvent
- Handle edge case: recipe with no ingredients
- Handle edge case: ingredient with no cost data (cost_per_unit = 0)

---

### Subtask T017 – Include required fields (slug, display_name, quantity, unit, cost_per_unit)

**Purpose**: Ensure all required fields are present in each aggregated ingredient record.

**Steps**:

1. Verify the structure from T016 includes all fields:
   - `ingredient_slug`: String identifier
   - `display_name`: Human-readable name
   - `quantity`: Numeric total needed
   - `unit`: Unit of measure
   - `cost_per_unit`: Cost per unit at snapshot time

2. Add validation:
   ```python
   def _validate_aggregated_ingredient(ing: Dict) -> bool:
       """Validate ingredient record has all required fields."""
       required = ["ingredient_slug", "display_name", "quantity", "unit", "cost_per_unit"]
       return all(key in ing for key in required)
   ```

3. Handle missing fields gracefully:
   ```python
   # In aggregation loop
   result.append({
       "ingredient_slug": data["ingredient_slug"] or "unknown",
       "display_name": data["display_name"] or data["ingredient_slug"],
       "quantity": float(data["quantity"]),
       "unit": data["unit"] or "each",
       "cost_per_unit": float(data.get("cost_per_unit", 0.0))
   })
   ```

**Files**:
- `src/services/planning/planning_service.py` (within T016 implementation)

**Parallel?**: No - part of T016

**Notes**:
- This is validation/cleanup within T016's implementation
- Ensure numeric types are consistent (float, not Decimal)

---

### Subtask T018 – Ensure yield ratios respected from recipe service

**Purpose**: Verify that recipe yield ratios are correctly applied to ingredient quantities.

**Steps**:

1. Understand how `get_aggregated_ingredients()` handles yield:
   - Check if it already applies yield ratio internally
   - Verify `multiplier` parameter is respected

2. Test yield calculation:
   ```python
   # If recipe yields 24 cookies and we need 48
   # multiplier should be 2.0
   # Ingredient quantities should be doubled
   ```

3. Add test case for yield ratio:
   ```python
   def test_aggregated_ingredients_respects_yield():
       """Verify yield ratio affects ingredient quantities."""
       # Create recipe with known yield
       recipe = _create_recipe(yield_per_batch=24)
       _add_ingredient(recipe, "flour", quantity=2, unit="cups")

       # Aggregate for 2 batches
       result = _aggregate_plan_ingredients(
           [{"recipe_id": recipe.id, "batches": 2, "scale_factor": 1.0}],
           session
       )

       # Should need 4 cups flour (2 batches * 2 cups)
       flour = next(i for i in result if i["ingredient_slug"] == "flour")
       assert flour["quantity"] == 4.0
   ```

4. If yield not applied correctly, fix in aggregation:
   ```python
   # May need to adjust multiplier based on yield
   base_yield = recipe.yield_per_batch
   target_units = batches * base_yield * scale_factor
   multiplier = target_units / base_yield  # Simplifies to batches * scale_factor
   ```

**Files**:
- `src/services/planning/planning_service.py` (verify/fix in T016)
- `src/tests/services/planning/test_planning_service.py` (add test)

**Parallel?**: No - depends on T016

**Notes**:
- Recipe yield model may have changed with F056
- Check current yield calculation pattern in batch_production_service

---

### Subtask T019 – Snapshot cost at plan calculation time

**Purpose**: Ensure cost_per_unit is captured at the moment of plan calculation, not looked up later.

**Steps**:

1. Verify cost is captured in the aggregation (T016 should already do this)

2. Cost should come from:
   - Ingredient catalog cost
   - Or average cost from inventory (FIFO weighted)

3. Do NOT look up cost when displaying plan later:
   ```python
   # WRONG - live lookup
   def get_ingredient_cost(slug):
       return ingredient_service.get_current_cost(slug)

   # CORRECT - use snapshotted value
   cost = aggregated_ingredient["cost_per_unit"]
   ```

4. Add test to verify snapshot:
   ```python
   def test_cost_snapshot_at_calculation_time():
       """Verify cost is captured at plan time, not live."""
       # Create plan
       plan = planning_service.calculate_plan(event_id, session=session)
       original_cost = plan.calculation_results["aggregated_ingredients"][0]["cost_per_unit"]

       # Change ingredient cost
       _update_ingredient_cost("flour", original_cost * 2)

       # Reload plan (not recalculate)
       plan = planning_service.get_plan(plan.id, session=session)
       stored_cost = plan.calculation_results["aggregated_ingredients"][0]["cost_per_unit"]

       # Should still have original cost
       assert stored_cost == original_cost
   ```

**Files**:
- `src/services/planning/planning_service.py` (verify in T016)
- `src/tests/services/planning/test_planning_service.py` (add test)

**Parallel?**: No - depends on T016

**Notes**:
- This is mostly verification that T016 captures cost correctly
- The snapshot is implicit in storing the calculated value

---

### Subtask T020 – Add tests for snapshot completeness

**Purpose**: Comprehensive tests for aggregated ingredients in snapshots.

**Steps**:

1. Add test for basic aggregation:
   ```python
   def test_plan_has_aggregated_ingredients():
       """Verify plan snapshot includes aggregated ingredients."""
       plan = planning_service.calculate_plan(event_id, session=session)

       assert "aggregated_ingredients" in plan.calculation_results
       assert len(plan.calculation_results["aggregated_ingredients"]) > 0
   ```

2. Add test for field completeness:
   ```python
   def test_aggregated_ingredient_fields():
       """Verify each ingredient has required fields."""
       plan = planning_service.calculate_plan(event_id, session=session)

       for ing in plan.calculation_results["aggregated_ingredients"]:
           assert "ingredient_slug" in ing
           assert "display_name" in ing
           assert "quantity" in ing
           assert "unit" in ing
           assert "cost_per_unit" in ing
   ```

3. Add test for multi-recipe aggregation:
   ```python
   def test_aggregated_across_recipes():
       """Verify same ingredient from multiple recipes is summed."""
       # Create event with 2 recipes both using flour
       # Verify flour quantity is sum of both
       pass
   ```

4. Add test for empty plan:
   ```python
   def test_empty_plan_has_empty_ingredients():
       """Verify empty plan has empty aggregated_ingredients."""
       # Create event with no recipes
       plan = planning_service.calculate_plan(event_id, session=session)

       assert plan.calculation_results["aggregated_ingredients"] == []
   ```

**Files**:
- `src/tests/services/planning/test_planning_service.py` (add ~80 lines)

**Parallel?**: No - depends on T016-T019

**Notes**:
- Create test fixtures for recipes with known ingredients
- Test edge cases: no cost, no ingredients, multiple recipes

---

### Subtask T021 – Update export/import for aggregated ingredients

**Purpose**: Ensure aggregated ingredients survive export/import cycle.

**Steps**:

1. Locate export logic for ProductionPlanSnapshot in `src/services/import_export_service.py`

2. Verify `calculation_results` JSON is exported completely:
   ```python
   # Export should include full calculation_results
   snapshot_data = {
       "id": snapshot.id,
       "calculation_results": snapshot.calculation_results,  # Includes aggregated_ingredients
       # ... other fields
   }
   ```

3. Verify import reconstructs correctly:
   ```python
   # Import should restore calculation_results as-is
   snapshot = ProductionPlanSnapshot(
       calculation_results=data["calculation_results"],
       # ... other fields
   )
   ```

4. Add round-trip test:
   ```python
   def test_aggregated_ingredients_export_import():
       """Verify aggregated ingredients survive export/import."""
       # Create plan with aggregated ingredients
       plan = planning_service.calculate_plan(event_id, session=session)
       original = plan.calculation_results["aggregated_ingredients"]

       # Export
       export_data = import_export_service.export_data()

       # Clear database (reset)
       _reset_database()

       # Import
       import_export_service.import_data(export_data)

       # Verify
       imported_plan = planning_service.get_plan(plan.id)
       assert imported_plan.calculation_results["aggregated_ingredients"] == original
   ```

**Files**:
- `src/services/import_export_service.py` (verify, likely no changes needed)
- `src/tests/services/test_import_export_service.py` (add test)

**Parallel?**: Yes - can start once T016-T019 complete

**Notes**:
- Export likely already handles JSON fields correctly
- This is mostly verification that nothing special is needed

---

## Test Strategy

**Required Tests**:
1. Plan has aggregated_ingredients
2. All required fields present
3. Yield ratios applied correctly
4. Cost snapshotted at calculation time
5. Multi-recipe aggregation works
6. Export/import round-trip

**Test Commands**:
```bash
# Run planning tests
./run-tests.sh src/tests/services/planning/test_planning_service.py -v

# Run import/export tests
./run-tests.sh src/tests/services/test_import_export_service.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Yield calculation incorrect | Add specific yield ratio test (T018) |
| Cost not snapshotted | Verify with time-based test (T019) |
| Export breaks | Round-trip test (T021) |

---

## Definition of Done Checklist

- [ ] T016: Aggregated ingredient calculation implemented
- [ ] T017: All required fields present
- [ ] T018: Yield ratios respected
- [ ] T019: Cost snapshotted at calculation time
- [ ] T020: Comprehensive tests pass
- [ ] T021: Export/import preserves data
- [ ] Full test suite passes

---

## Review Guidance

**Key Review Checkpoints**:
1. Uses existing `get_aggregated_ingredients()` function
2. Cost is captured at calculation time (not live lookup)
3. Yield calculation matches batch_production pattern
4. Tests verify all edge cases

---

## Activity Log

- 2026-01-20T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-21T03:17:51Z – claude-opus – shell_pid=1900 – lane=doing – Started implementation via workflow command
- 2026-01-21T03:31:09Z – claude-opus – shell_pid=1900 – lane=for_review – Ready for review: Implemented aggregated ingredients in planning snapshots. Added _aggregate_plan_ingredients() helper, populated aggregated_ingredients field, added 7 tests. All 2564 tests pass.
- 2026-01-21T03:37:58Z – claude-opus – shell_pid=8216 – lane=doing – Started review via workflow command
