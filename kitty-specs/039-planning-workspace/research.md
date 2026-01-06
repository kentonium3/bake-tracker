# Research: Planning Workspace (F039)

**Feature Branch**: `039-planning-workspace`
**Research Date**: 2026-01-05
**Status**: Complete

## Executive Summary

Research confirms the existing codebase provides a solid foundation for the Planning Workspace feature. Key services (`event_service`, `batch_production_service`, `assembly_service`) already implement much of the required functionality. However, one critical discrepancy exists between the spec and reality regarding recipe yield options.

---

## Critical Finding: Recipe Yield Model Discrepancy

### Spec Assumption
The spec (FR-011) assumes recipes have **multiple yield options** (e.g., 24, 48, 96 cookies per batch) and the system optimizes by selecting the yield option that minimizes waste under 15% threshold.

### Actual Codebase
**No RecipeYieldOption model exists.** Recipe has a single fixed yield:
- `yield_quantity` (Float) - e.g., 48
- `yield_unit` (String) - e.g., "cookies"

### Impact
- FR-011 (yield option optimization) cannot work as specified
- Waste calculation simplifies to: `(batches * yield_quantity) - needed`
- No optimization between yield options possible

### Decision Required
**Options:**
1. **Simplify spec** - Remove yield option optimization; calculate batches using single yield (recommended for Phase 2)
2. **Add RecipeYieldOption model** - New schema, migration, more complexity
3. **Use Recipe variants** - Existing `base_recipe_id`/variants structure could represent yield options

**Recommendation**: Option 1 for Phase 2. Batch calculation uses single yield. Document yield options as Phase 3+ enhancement.

---

## Model Research Findings

### BaseModel Timestamps
All models inherit from BaseModel which provides:
- `created_at` (DateTime, default=utc_now)
- `updated_at` (DateTime, default=utc_now, **onupdate=utc_now**)

This supports timestamp-based staleness detection (Engineering Decision).

**Exception**: Event and Recipe override with `date_added`/`last_modified` instead. Plan staleness should compare against these fields for those models.

### Event Model - Changes Needed
Current Event model does NOT have `output_mode`. Must add:
```python
output_mode = Column(Enum(OutputMode), nullable=True)  # BUNDLED, BULK_COUNT
```

Timestamps available: `date_added`, `last_modified` (not standard `updated_at`)

### FinishedUnit Model - Key Method
Already has `calculate_batches_needed(quantity)` method:
- Uses `items_per_batch` for DISCRETE_COUNT yield_mode
- Uses `batch_percentage` for BATCH_PORTION yield_mode
- Returns number of recipe batches needed

### Composition Model - Bundle Contents
Links FinishedGood to components via polymorphic FKs:
- `finished_unit_id` - FinishedUnit component
- `finished_good_id` - Nested FinishedGood (bundles within bundles)
- `packaging_product_id` - Packaging materials
- `component_quantity` - How many of each per bundle

### EventAssemblyTarget & EventProductionTarget
Already exist and link events to targets:
- `EventAssemblyTarget`: event_id, finished_good_id, target_quantity
- `EventProductionTarget`: event_id, recipe_id, target_batches

---

## Service Research Findings

### Existing Service Capabilities

| Need | Existing Service | Function | Status |
|------|------------------|----------|--------|
| Ingredient aggregation | recipe_service | `get_aggregated_ingredients(recipe_id, multiplier)` | Ready |
| Production feasibility | batch_production_service | `check_can_produce(recipe_id, num_batches)` | Ready |
| Assembly feasibility | assembly_service | `check_can_assemble(finished_good_id, quantity)` | Ready |
| Shopping list | event_service | `get_shopping_list(event_id)` | Ready |
| Production progress | event_service | `get_production_progress(event_id)` | Ready |
| Assembly progress | event_service | `get_assembly_progress(event_id)` | Ready |
| Overall progress | event_service | `get_event_overall_progress(event_id)` | Ready |
| Set targets | event_service | `set_production_target()`, `set_assembly_target()` | Ready |
| Inventory check | inventory_item_service | `consume_fifo(..., dry_run=True)` | Ready |

### Session Management Pattern
All services follow consistent pattern:
```python
def operation(..., session=None):
    if session is not None:
        return _operation_impl(..., session)
    with session_scope() as session:
        return _operation_impl(..., session)
```

PlanningService MUST follow this pattern.

### Exception Patterns
Services use domain-specific exceptions:
- `InsufficientInventoryError`
- `RecipeNotFoundError`
- `FinishedGoodNotFoundError`
- `ValidationError`

PlanningService should define:
- `PlanningError` (base)
- `StalePlanError`
- `IncompleteRequirementsError`

---

## New Code Required

### Models
1. **ProductionPlanSnapshot** (new) - Persisted plan calculations
2. **Event.output_mode** (add field) - BUNDLED vs BULK_COUNT mode

### Services
1. **planning/** module (new):
   - `planning_service.py` - Facade
   - `batch_calculation.py` - Batch count optimization
   - `shopping_list.py` - Wraps/extends event_service
   - `feasibility.py` - Combined production + assembly checks
   - `progress.py` - Wraps event_service progress functions

### UI
1. **ui/planning/** module (new):
   - `planning_workspace.py` - Main wizard container
   - `phase_sidebar.py` - Navigation with status indicators
   - `calculate_view.py` - Calculate phase UI
   - `shop_view.py` - Shopping phase UI
   - `produce_view.py` - Production phase UI
   - `assemble_view.py` - Assembly phase UI

---

## Integration Points

### Batch Calculation Flow
```
EventAssemblyTarget.target_quantity (bundles needed)
    -> FinishedGood.components (get Compositions)
    -> component_quantity * target_quantity (units per component)
    -> FinishedUnit.calculate_batches_needed(units) (batches per recipe)
    -> Aggregate by recipe_id (some recipes may serve multiple FinishedUnits)
```

### Staleness Detection Flow
```
ProductionPlanSnapshot.calculated_at vs:
    - Recipe.last_modified (for each recipe in plan)
    - FinishedGood.updated_at (for each bundle)
    - Composition.created_at (bundle contents - no updated_at)
    - EventAssemblyTarget timestamps
    - EventProductionTarget timestamps

If any input is newer than calculated_at -> plan is stale
```

### Shopping List Generation
Existing `event_service.get_shopping_list()` provides:
- Aggregated ingredient needs
- Inventory comparison (in_stock vs needed)
- Purchase quantities
- Product recommendations

PlanningService can wrap this with additional formatting for wizard UI.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Composition has no `updated_at` | Cannot detect bundle content changes | Use `created_at` or add `updated_at` field |
| Event uses `last_modified` not `updated_at` | Inconsistent timestamp naming | Handle both patterns in staleness check |
| No yield options | Spec FR-011 cannot be implemented | Simplify to single yield; document for Phase 3 |
| Large events (10+ recipes) | Performance concern | Optimize with batch queries; cache aggregations |

---

## Open Questions (Resolved)

1. **Q: How to handle multiple FinishedUnits from same recipe?**
   A: Aggregate by recipe_id. Total batches = max needed across all FinishedUnits.

2. **Q: What if bundle contains nested FinishedGoods?**
   A: Recursively explode. Composition supports nested assemblies via `finished_good_id` FK.

3. **Q: Event timestamps vs BaseModel timestamps?**
   A: Use model-specific field names (`last_modified` for Event/Recipe, `updated_at` for others).

---

## Recommendations

1. **Proceed with simplified batch calculation** - Use single recipe yield, defer yield options to Phase 3
2. **Add output_mode to Event** - Simple schema change
3. **Create ProductionPlanSnapshot** - New model for plan persistence
4. **Leverage existing event_service** - Much functionality already implemented
5. **Follow session management pattern** - Critical for transactional safety
