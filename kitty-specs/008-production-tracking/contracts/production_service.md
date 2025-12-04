# Service Contract: ProductionService

**Module**: `src/services/production_service.py`
**Date**: 2025-12-04

## Overview

The ProductionService provides business logic for recording recipe production, managing package status, and calculating production progress.

---

## Functions

### record_production()

Record batches of a recipe as produced for an event.

**Signature**:
```python
def record_production(
    event_id: int,
    recipe_id: int,
    batches: int,
    notes: Optional[str] = None
) -> ProductionRecord
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| event_id | int | Yes | Event to record production for |
| recipe_id | int | Yes | Recipe that was produced |
| batches | int | Yes | Number of batches produced (must be > 0) |
| notes | str | No | Optional production notes |

**Returns**: `ProductionRecord` - The created production record

**Behavior**:
1. Validate event exists
2. Validate recipe exists
3. Validate batches > 0
4. Check if production would exceed required batches (warn but allow)
5. Calculate ingredient quantities for batches
6. Call `pantry_service.consume_fifo()` for each ingredient with `dry_run=False`
7. Sum actual costs from FIFO consumption
8. Create ProductionRecord with actual_cost snapshot
9. Return created record

**Errors**:
| Exception | When |
|-----------|------|
| EventNotFoundError | Event doesn't exist |
| RecipeNotFoundError | Recipe doesn't exist |
| ValidationError | batches <= 0 |
| InsufficientInventoryError | Pantry doesn't have enough ingredients |

---

### get_production_progress()

Get production progress for an event.

**Signature**:
```python
def get_production_progress(event_id: int) -> Dict[str, Any]
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| event_id | int | Yes | Event to get progress for |

**Returns**: Dictionary with progress data

**Response Structure**:
```python
{
    "event_id": int,
    "event_name": str,
    "recipes": [
        {
            "recipe_id": int,
            "recipe_name": str,
            "batches_required": int,
            "batches_produced": int,
            "is_complete": bool,
            "actual_cost": Decimal,  # Sum of production record costs
            "planned_cost": Decimal  # Estimated from recipe costing
        }
    ],
    "packages": {
        "total": int,
        "pending": int,
        "assembled": int,
        "delivered": int
    },
    "costs": {
        "actual_total": Decimal,
        "planned_total": Decimal
    },
    "is_complete": bool  # All packages delivered
}
```

**Behavior**:
1. Get required batches from `event_service.get_recipe_needs()`
2. Sum produced batches from ProductionRecord
3. Calculate package status counts from EventRecipientPackage
4. Sum actual/planned costs
5. Return aggregated progress

---

### update_package_status()

Update the status of a package assignment.

**Signature**:
```python
def update_package_status(
    assignment_id: int,
    new_status: PackageStatus,
    delivered_to: Optional[str] = None
) -> EventRecipientPackage
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| assignment_id | int | Yes | EventRecipientPackage ID |
| new_status | PackageStatus | Yes | Target status |
| delivered_to | str | No | Delivery note (only for DELIVERED status) |

**Returns**: `EventRecipientPackage` - Updated assignment

**Behavior**:
1. Validate assignment exists
2. Validate status transition is allowed
3. If transitioning to ASSEMBLED:
   - Check all required recipes are fully produced
   - If not, return error with missing batches
4. Update status field
5. If DELIVERED, optionally set delivered_to
6. Return updated record

**Status Transitions**:
```
PENDING -> ASSEMBLED (allowed)
ASSEMBLED -> DELIVERED (allowed)
PENDING -> DELIVERED (blocked: must assemble first)
ASSEMBLED -> PENDING (blocked: no rollback)
DELIVERED -> * (blocked: no rollback)
```

**Errors**:
| Exception | When |
|-----------|------|
| AssignmentNotFoundError | Assignment doesn't exist |
| InvalidStatusTransitionError | Transition not allowed |
| IncompleteProductionError | Trying to assemble but recipes not fully produced |

---

### get_dashboard_summary()

Get production summary across all active events.

**Signature**:
```python
def get_dashboard_summary() -> List[Dict[str, Any]]
```

**Returns**: List of event summaries

**Response Structure**:
```python
[
    {
        "event_id": int,
        "event_name": str,
        "event_date": date,
        "recipes_complete": int,
        "recipes_total": int,
        "packages_pending": int,
        "packages_assembled": int,
        "packages_delivered": int,
        "packages_total": int,
        "actual_cost": Decimal,
        "planned_cost": Decimal,
        "is_complete": bool
    }
]
```

**Behavior**:
1. Query events with packages not all delivered
2. For each event, aggregate:
   - Recipe production progress
   - Package status counts
   - Cost totals
3. Sort by event_date ascending
4. Return list

---

### get_recipe_cost_breakdown()

Get detailed cost breakdown by recipe for an event.

**Signature**:
```python
def get_recipe_cost_breakdown(event_id: int) -> List[Dict[str, Any]]
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| event_id | int | Yes | Event to get breakdown for |

**Returns**: List of recipe cost details

**Response Structure**:
```python
[
    {
        "recipe_id": int,
        "recipe_name": str,
        "batches_required": int,
        "batches_produced": int,
        "actual_cost": Decimal,
        "planned_cost": Decimal,
        "variance": Decimal,  # actual - planned
        "variance_percent": float  # (actual - planned) / planned * 100
    }
]
```

---

### can_assemble_package()

Check if a package can be marked as assembled.

**Signature**:
```python
def can_assemble_package(assignment_id: int) -> Dict[str, Any]
```

**Returns**:
```python
{
    "can_assemble": bool,
    "missing_recipes": [
        {
            "recipe_id": int,
            "recipe_name": str,
            "batches_required": int,
            "batches_produced": int,
            "batches_missing": int
        }
    ]
}
```

---

## Custom Exceptions

```python
class InsufficientInventoryError(Exception):
    """Raised when pantry doesn't have enough ingredients."""
    def __init__(self, ingredient_slug: str, needed: Decimal, available: Decimal):
        self.ingredient_slug = ingredient_slug
        self.needed = needed
        self.available = available

class InvalidStatusTransitionError(Exception):
    """Raised when package status transition is not allowed."""
    def __init__(self, current: PackageStatus, target: PackageStatus):
        self.current = current
        self.target = target

class IncompleteProductionError(Exception):
    """Raised when trying to assemble package with incomplete production."""
    def __init__(self, assignment_id: int, missing_recipes: List[Dict]):
        self.assignment_id = assignment_id
        self.missing_recipes = missing_recipes
```
