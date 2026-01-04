---
work_package_id: "WP03"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "Production Integration"
phase: "Phase 1 - Core Snapshot System"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-03T06:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Production Integration

## Objectives & Success Criteria

Modify batch_production_service to create snapshot BEFORE production and use snapshot data for cost calculation.

**Success Criteria**:
- Snapshot created FIRST in production transaction
- Costs calculated from snapshot ingredient data
- scale_factor flows through production
- Expected yield = base_yield x scale_factor x num_batches
- Ingredient consumption = base_quantity x scale_factor x num_batches
- Integration tests pass with FIFO consumption

## Context & Constraints

**Key References**:
- `src/services/batch_production_service.py` - Primary modification target
- `kitty-specs/037-recipe-template-snapshot/research.md` - Production integration points
- `CLAUDE.md` - Session management (CRITICAL)

**Current Flow** (from research.md):
1. Validate recipe exists (line 275)
2. Get aggregated ingredients (line 314)
3. FIFO consumption (line 328)
4. Create ProductionRun (line 367)

**New Flow**:
1. Validate recipe exists
2. Create snapshot FIRST (captures recipe state)
3. Get ingredients from snapshot data
4. Apply scale_factor to quantities
5. FIFO consumption
6. Create ProductionRun with recipe_snapshot_id

**Constraints**:
- All operations must share same session
- FIFO consumption logic unchanged
- Backward compatible with existing data

## Subtasks & Detailed Guidance

### Subtask T010 - Modify record_batch_production() to Create Snapshot First

**Purpose**: Capture recipe state before any consumption occurs.

**File**: `src/services/batch_production_service.py`

**Steps**:
1. Add import for recipe_snapshot_service
2. Add scale_factor parameter (default 1.0)
3. After recipe validation, call create_recipe_snapshot() FIRST
4. Store snapshot_id for ProductionRun creation
5. Update ProductionRun creation to set recipe_snapshot_id

**Modification Points**:

```python
# Add to imports:
from src.services import recipe_snapshot_service

# Modify function signature (around line 209):
def record_batch_production(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    notes: str = None,
    event_id: int = None,
    scale_factor: float = 1.0,  # NEW PARAMETER
    session=None
) -> dict:

# After recipe validation (around line 280), add snapshot creation:
    # Create snapshot FIRST - captures recipe state before production
    snapshot = recipe_snapshot_service.create_recipe_snapshot(
        recipe_id=recipe_id,
        scale_factor=scale_factor,
        production_run_id=None,  # Will update after ProductionRun created
        session=session
    )
    snapshot_id = snapshot["id"]

# Update ProductionRun creation (around line 367):
    production_run = ProductionRun(
        recipe_id=recipe_id,  # Keep for backward compatibility
        recipe_snapshot_id=snapshot_id,  # NEW
        finished_unit_id=finished_unit_id,
        # ... rest unchanged
    )
```

**Note**: We need to handle the chicken-and-egg problem where snapshot needs production_run_id but ProductionRun needs snapshot_id. Solution: Create snapshot without production_run_id, create ProductionRun, then update snapshot.

---

### Subtask T011 - Update Cost Calculation to Use Snapshot Data

**Purpose**: Calculate costs from snapshot ingredients, not live recipe.

**Steps**:
1. After snapshot creation, use snapshot's ingredients_data for consumption
2. Apply scale_factor to base quantities
3. Maintain FIFO consumption logic

**Key Change**:
```python
# Instead of:
aggregated = get_aggregated_ingredients(recipe_id, multiplier=num_batches, session=session)

# Use snapshot data:
ingredients_data = snapshot["ingredients_data"]
for item in ingredients_data:
    # Apply scale_factor to base quantity, then multiply by num_batches
    base_quantity = Decimal(str(item["quantity"]))
    quantity_needed = base_quantity * Decimal(str(scale_factor)) * Decimal(str(num_batches))

    result = inventory_item_service.consume_fifo(
        item["ingredient_slug"],
        quantity_needed,
        item["unit"],
        dry_run=False,
        session=session
    )
```

---

### Subtask T012 - Add scale_factor to Production Flow

**Purpose**: Ensure scale_factor is properly stored and used throughout.

**Steps**:
1. scale_factor stored on snapshot (already done in snapshot creation)
2. Expected yield calculation: `base_yield x scale_factor x num_batches`
3. Include scale_factor in production run response

**Expected Yield Calculation**:
```python
# Get base yield from recipe
base_yield = recipe.yield_quantity

# Calculate expected yield with scaling
expected_yield = int(base_yield * scale_factor * num_batches)
```

---

### Subtask T013 - Create Integration Tests

**Purpose**: Verify end-to-end production with snapshots works correctly.

**File**: `src/tests/services/test_batch_production_service.py`

**Tests to Add**:
1. `test_production_creates_snapshot` - Snapshot created before consumption
2. `test_production_snapshot_has_correct_data` - Recipe data captured correctly
3. `test_production_with_scale_factor` - scale_factor=2.0 doubles quantities
4. `test_production_cost_from_snapshot` - Cost calculated from snapshot data
5. `test_production_historical_cost_unchanged` - Modify recipe after production, verify historical cost stable
6. `test_production_expected_yield_with_scaling` - yield = base x scale x batches

**Critical Test - Historical Accuracy**:
```python
def test_production_historical_cost_unchanged(test_session):
    """
    FR-001: Historical production costs remain accurate when recipes are modified.

    1. Create recipe with 2 cups flour at $0.50/cup = $1.00
    2. Run production
    3. Modify recipe to 3 cups flour
    4. Verify historical production still shows $1.00
    """
    # Setup recipe with known cost
    recipe = create_test_recipe(...)
    add_ingredient(recipe, "flour", quantity=2, unit="cups")

    # Setup inventory with known price
    add_inventory("flour", cost_per_unit=0.50)

    # Run production
    result = record_batch_production(recipe.id, ..., scale_factor=1.0)
    production_run_id = result["id"]

    # Verify initial cost
    assert result["total_ingredient_cost"] == Decimal("1.00")

    # Modify recipe (simulate user editing)
    update_recipe_ingredient(recipe.id, "flour", quantity=3)

    # Get historical production - should still show $1.00
    snapshot = get_snapshot_by_production_run(production_run_id)
    ingredients = snapshot["ingredients_data"]

    # Original quantity preserved in snapshot
    flour_in_snapshot = next(i for i in ingredients if "flour" in i["ingredient_slug"])
    assert flour_in_snapshot["quantity"] == 2.0  # Original, not modified
```

## Test Strategy

- Run: `pytest src/tests/services/test_batch_production_service.py -v -k snapshot`
- Run full suite to ensure no regressions
- Use fixtures with known ingredient costs for deterministic tests

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing production | Comprehensive integration tests |
| Session detachment | Pass session through all calls |
| FIFO consumption errors | Keep existing consume_fifo() unchanged |
| Chicken-and-egg (snapshot needs run_id) | Create snapshot first, update after run created |

## Definition of Done Checklist

- [ ] record_batch_production() creates snapshot FIRST
- [ ] scale_factor parameter added and flows through
- [ ] Cost calculation uses snapshot ingredient data
- [ ] Expected yield calculation: base x scale x batches
- [ ] ProductionRun.recipe_snapshot_id populated
- [ ] Integration tests pass (6 new tests)
- [ ] No regressions in existing tests

## Review Guidance

- Verify snapshot creation happens BEFORE any FIFO consumption
- Check scale_factor is applied correctly to quantities
- Confirm historical cost test demonstrates immutability

## Activity Log

- 2026-01-03T06:30:00Z - system - lane=planned - Prompt created.
