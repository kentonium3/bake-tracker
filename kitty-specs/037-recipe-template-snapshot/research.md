# Research: Recipe Template & Snapshot System

**Feature**: F037-recipe-template-snapshot
**Created**: 2026-01-03
**Status**: Complete

## Planning Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D001 | Snapshot Storage | Full denormalization | Snapshots are completely self-contained with all recipe data as JSON; stronger immutability guarantees |
| D002 | Migration Strategy | Backfill with is_backfilled flag | Existing production runs get snapshots from current recipe data; UI shows "(approximated)" for historical data honesty |
| D003 | Variant UI | Indented list | Variants indented under base recipes, consistent with ingredient hierarchy display patterns |

---

## Key Findings

### 1. Recipe Model (src/models/recipe.py)

**Current Structure**:
- Fields: name, category, source, yield_quantity, yield_unit, yield_description, estimated_time_minutes, notes, is_archived
- Relationships: recipe_ingredients (1:N), recipe_components (1:N self-ref), production_runs (1:N), finished_units (1:N)
- Methods: `calculate_cost()`, `get_cost_per_unit()`, `to_dict()`

**Needed Additions**:
- `base_recipe_id` (nullable FK, self-referential) - FR-010
- `variant_name` (String(100), nullable) - FR-011
- `is_production_ready` (Boolean, default=False) - FR-014
- CHECK constraint: `base_recipe_id != id` - FR-013
- ON DELETE SET NULL for base_recipe_id - FR-012

### 2. ProductionRun Model (src/models/production_run.py)

**Current Structure**:
- Foreign keys: recipe_id (RESTRICT), finished_unit_id (RESTRICT), event_id (nullable)
- Fields: num_batches, expected_yield, actual_yield, produced_at, notes, production_status, loss_quantity, total_ingredient_cost, per_unit_cost

**Needed Changes**:
- Add `recipe_snapshot_id` FK (nullable initially for migration)
- Keep `recipe_id` temporarily for migration reference
- Remove direct recipe_id after migration complete

### 3. Recipe Service Patterns (src/services/recipe_service.py)

**Session Management**:
- Most functions use `session_scope()` internally
- `get_aggregated_ingredients(recipe_id, multiplier, session=None)` - ALREADY ACCEPTS SESSION
- Pattern: `if session is not None: return _impl(); else: with session_scope()...`

**Key Methods for Modification**:
| Method | Lines | Change Required |
|--------|-------|-----------------|
| `create_recipe()` | 78-164 | Add variant fields + is_production_ready |
| `update_recipe()` | 316-401 | Check snapshot dependencies before edit |
| `delete_recipe()` | 403-460 | Check snapshots exist (RESTRICT) |
| `check_recipe_dependencies()` | 462-479 | Add snapshot count |
| `get_aggregated_ingredients()` | 1517-1559 | Add snapshot data source option |

**New Functions Needed**:
1. `create_recipe_snapshot(recipe_id, scale_factor, production_run_id, session=None)`
2. `get_recipe_snapshots(recipe_id)` - for history view
3. `get_recipe_variants(base_recipe_id)` - for variant queries
4. `create_recipe_from_snapshot(snapshot_id)` - restore from history

### 4. Batch Production Service (src/services/batch_production_service.py)

**Integration Point: `record_batch_production()`** (Lines 208-429):
1. Validates recipe exists (line 275)
2. Calls `get_aggregated_ingredients(recipe_id, multiplier=num_batches, session=session)` (line 314)
3. Consumes FIFO via `inventory_item_service.consume_fifo()` (line 328)
4. Creates ProductionRun record (line 367)

**For F037**:
- Snapshot creation must happen BEFORE ingredient consumption
- Scale factor affects ingredient quantities: `quantity * scale_factor * num_batches`
- Expected yield: `base_yield * scale_factor * num_batches`
- Session must be passed through entire chain

**Cost Calculation Flow**:
- Ingredient aggregation scaled by num_batches
- FIFO consumption returns actual historical costs
- per_unit_cost = total_ingredient_cost / actual_yield

### 5. UI Patterns

**Recipe List (src/ui/recipes_tab.py)**:
- RecipeDataTable extends DataTable base class
- Columns: Name, Category, Yield, Total Cost, Cost/Unit
- No current grouping/indentation - needs variant indentation

**Recipe Form (src/ui/forms/recipe_form.py)**:
- CTkScrollableFrame with sections
- Ingredient rows: Quantity | Unit | Ingredient dropdown + Browse button
- Browse uses IngredientSelectionDialog (tree widget)
- Needs: is_production_ready checkbox, variant fields (base_recipe dropdown, variant_name)

**Production Dialog (src/ui/forms/record_production_dialog.py)**:
- Modal with: Event, Batch Count, Expected/Actual Yield, Loss Details
- Needs: Scale Factor input (default 1.0)
- Calculated yield: `base * scale_factor * num_batches`

**Existing Patterns to Leverage**:
- Ingredient tree widget for hierarchical display
- DataTable for list with selection
- CTkScrollableFrame for forms
- Modal dialogs with grab_set()

---

## Architecture Alignment

### Constitution Checks

| Principle | Compliance |
|-----------|------------|
| **I. User-Centric Design** | Snapshots are transparent - user doesn't manage versions manually |
| **II. Data Integrity** | Snapshots ensure historical accuracy; FIFO consumption preserved |
| **III. Future-Proof Schema** | JSON storage allows schema evolution; variant FK enables family tracking |
| **IV. Test-Driven Development** | New service functions require unit tests |
| **V. Layered Architecture** | Snapshot logic in services; UI only displays |
| **VI. Schema Change Strategy** | Export/import cycle for migration if needed |

### Session Management Compliance

All new functions must follow the pattern from CLAUDE.md:
```python
def create_recipe_snapshot(recipe_id, scale_factor, production_run_id, session=None):
    if session is not None:
        return _create_recipe_snapshot_impl(recipe_id, scale_factor, production_run_id, session)
    with session_scope() as session:
        return _create_recipe_snapshot_impl(recipe_id, scale_factor, production_run_id, session)
```

---

## Implementation Priorities

### Phase 1 - Core Snapshot (P1 User Stories 1-2)
1. RecipeSnapshot model with JSON fields
2. Recipe model additions (base_recipe_id, variant_name, is_production_ready)
3. `create_recipe_snapshot()` service function
4. Modify `record_batch_production()` to create snapshot first
5. Update ProductionRun FK from recipe_id to recipe_snapshot_id
6. Migration script for existing production runs

### Phase 2 - Scaling & Variants (P2 User Stories 3-4)
1. Add scale_factor to snapshot and production flow
2. UI: Scale factor input in production dialog
3. Variant creation UI (base_recipe dropdown, variant_name field)
4. Recipe list indentation for variants

### Phase 3 - Production Readiness & History (P3 User Stories 5-6)
1. is_production_ready toggle in recipe form
2. Recipe list filter by production readiness
3. Recipe history view (list of snapshots)
4. "Create from snapshot" functionality

---

## Open Questions

1. **RecipeComponent in Snapshots**: Confirmed - snapshots capture direct ingredients only. Nested recipe support deferred to Phase 3 per spec.

2. **Snapshot on Variant Production**: When producing a variant, does the snapshot capture the variant's data or reference the base?
   - **Decision**: Capture variant data (full denormalization means complete self-contained state)

3. **Edit Recipe with Snapshots**: Should recipe editing be blocked if snapshots exist?
   - **Decision**: No - editing templates is allowed. Snapshots preserve historical state independently.

4. **Scale Factor Location**: Stored on RecipeSnapshot (affects ingredient quantities) not ProductionRun
   - num_batches on ProductionRun (repetition count)
   - scale_factor on RecipeSnapshot (size per batch)

---

## References

| ID | Source | Description |
|----|--------|-------------|
| S001 | src/models/recipe.py | Recipe model with relationships |
| S002 | src/models/production_run.py | ProductionRun FK structure |
| S003 | src/services/recipe_service.py | Session patterns, cost calculation |
| S004 | src/services/batch_production_service.py | Production flow, FIFO integration |
| S005 | src/ui/recipes_tab.py | DataTable patterns |
| S006 | src/ui/forms/recipe_form.py | Form field patterns |
| S007 | src/ui/widgets/ingredient_tree_widget.py | Tree display for hierarchies |
| S008 | CLAUDE.md | Session management rules |
| S009 | .kittify/memory/constitution.md | Architecture principles |
