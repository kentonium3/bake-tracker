# Quickstart: Production-Aware Planning Calculations

**Feature**: F079 | **Date**: 2026-01-28

## Overview

This feature makes planning calculations aware of production progress so that feasibility checks, shopping lists, and amendments operate on **remaining needs** rather than total planned needs.

## Key APIs

### Get Remaining Production Needs

```python
from src.services.planning.progress import get_remaining_production_needs

# Returns {recipe_id: remaining_batches}
remaining = get_remaining_production_needs(event_id)
# Example: {1: 3, 2: 0, 3: 5}  # Recipe 2 is complete
```

### Production-Aware Feasibility Check

```python
from src.services.planning.feasibility import check_production_feasibility

# Default: checks remaining batches (production_aware=True)
results = check_production_feasibility(event_id)

# Legacy: checks total batches
results = check_production_feasibility(event_id, production_aware=False)
```

### Production-Aware Shopping List

```python
from src.services.planning.shopping_list import get_shopping_list

# Default: shows needs for remaining production (production_aware=True)
items = get_shopping_list(event_id)

# Legacy: shows needs for total production
items = get_shopping_list(event_id, production_aware=False)
```

### Amendment Validation

Amendments are automatically blocked for recipes/FGs with production:

```python
from src.services.plan_amendment_service import modify_batch_decision

# Raises ValidationError if recipe has any ProductionRun records
try:
    modify_batch_decision(event_id, recipe_id, new_batches=5, reason="Adjustment")
except ValidationError as e:
    print(e.errors)
    # ["Cannot modify batch decision for recipe 'Cookies' - production already recorded"]
```

## Progress Display

```python
from src.services.planning.progress import get_production_progress

progress = get_production_progress(event_id)
for p in progress:
    print(f"{p.recipe_name}: {p.completed_batches}/{p.target_batches}")
    print(f"  Remaining: {p.remaining_batches}")
    if p.overage_batches > 0:
        print(f"  Overage: +{p.overage_batches}")
```

## Testing

```bash
# Run all F079 tests
./run-tests.sh src/tests/planning/test_progress.py -v -k "remaining"
./run-tests.sh src/tests/planning/test_feasibility.py -v -k "production_aware"
./run-tests.sh src/tests/test_plan_amendment_service.py -v -k "production"
```

## Work Package Order

1. **WP01**: Remaining calculation (foundation)
2. **WP02-04**: Feasibility, shopping, amendments (parallelizable)
3. **WP05**: UI updates (depends on WP01-04)

## Implementation Notes

- All functions accept `session=None` for transaction control
- Default behavior is production-aware; pass `production_aware=False` for legacy behavior
- Validation errors include recipe/FG names for clear user feedback
