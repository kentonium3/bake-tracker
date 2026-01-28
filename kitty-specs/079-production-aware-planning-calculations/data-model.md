# Data Model: Production-Aware Planning Calculations

**Feature**: F079 | **Date**: 2026-01-28

## Overview

This feature requires **no schema changes**. All calculations use existing models:
- `EventProductionTarget` - target batches per recipe
- `ProductionRun` - completed production records
- `BatchDecision` - batch decisions to be protected from amendments

## DTO Extensions

### ProductionProgress (Extended)

**File**: `src/services/planning/progress.py`

```python
@dataclass
class ProductionProgress:
    """Progress for a single recipe target.

    Attributes:
        recipe_id: The recipe ID
        recipe_name: The recipe display name
        target_batches: Number of batches planned to produce
        completed_batches: Number of batches actually produced
        remaining_batches: Batches still to produce (NEW)
        overage_batches: Batches produced beyond target (NEW)
        progress_percent: Percentage complete (0-100+, can exceed 100%)
        is_complete: True if completed_batches >= target_batches
    """

    recipe_id: int
    recipe_name: str
    target_batches: int
    completed_batches: int
    remaining_batches: int      # NEW: max(0, target - completed)
    overage_batches: int        # NEW: max(0, completed - target)
    progress_percent: float
    is_complete: bool
```

**Calculation Logic**:
```python
remaining_batches = max(0, target_batches - completed_batches)
overage_batches = max(0, completed_batches - target_batches)
```

## Existing Models Used (No Changes)

### EventProductionTarget

```
EventProductionTarget
├── event_id: FK → Event
├── recipe_id: FK → Recipe
├── target_batches: int
└── Unique(event_id, recipe_id)
```

### ProductionRun

```
ProductionRun
├── id: PK
├── event_id: FK → Event (nullable)
├── recipe_id: FK → Recipe
├── num_batches: int
├── actual_yield: int
├── production_status: str
└── created_at: datetime
```

### BatchDecision

```
BatchDecision
├── id: PK
├── event_id: FK → Event
├── recipe_id: FK → Recipe
├── batches: int (the planned batch count)
└── Unique(event_id, recipe_id)
```

## Query Patterns

### Get Remaining Needs

```python
# In progress.py
def get_remaining_production_needs(event_id, session) -> Dict[int, int]:
    progress_list = get_production_progress(event_id, session=session)
    return {p.recipe_id: p.remaining_batches for p in progress_list}
```

### Check Production Exists for Recipe

```python
# In plan_amendment_service.py
def _has_production_for_recipe(event_id, recipe_id, session) -> bool:
    from src.models import ProductionRun
    count = session.query(ProductionRun).filter(
        ProductionRun.event_id == event_id,
        ProductionRun.recipe_id == recipe_id,
    ).count()
    return count > 0
```

## Validation Rules

| Rule | Implementation |
|------|----------------|
| remaining_batches >= 0 | `max(0, target - completed)` enforces this |
| overage_batches >= 0 | `max(0, completed - target)` enforces this |
| Amendment blocked if production exists | Check ProductionRun count > 0 |

## No State Transitions

This feature does not introduce new state machines. It reads existing state (production records) and derives calculated values (remaining needs).
