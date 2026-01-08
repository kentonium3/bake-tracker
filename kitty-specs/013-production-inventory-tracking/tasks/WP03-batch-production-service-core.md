---
work_package_id: WP03
title: Batch Production Service - Core
lane: done
history:
- timestamp: '2025-12-09T17:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 2 - Core Services
review_status: ''
reviewed_by: ''
shell_pid: '17130'
subtasks:
- T009
- T010
- T011
- T012
- T013
---

# Work Package Prompt: WP03 - Batch Production Service - Core

## Objectives & Success Criteria

Implement the core BatchProductionService with:
- `check_can_produce(recipe_id, num_batches)` - Availability check using dry-run FIFO
- `record_batch_production(...)` - Record production with FIFO consumption and inventory updates

**Success Criteria**:
- [ ] check_can_produce returns accurate availability with missing ingredient details
- [ ] record_batch_production atomically: consumes ingredients, increments FinishedUnit, creates records
- [ ] All operations complete within single transaction (rollback on any failure)
- [ ] Nested recipes handled via get_aggregated_ingredients()
- [ ] Per-unit cost calculated correctly (total_cost / actual_yield)

## Context & Constraints

**Reference Documents**:
- `kitty-specs/013-production-inventory-tracking/contracts/batch_production_service.py` - Service interface
- `kitty-specs/013-production-inventory-tracking/data-model.md` - Entity definitions
- `kitty-specs/013-production-inventory-tracking/quickstart.md` - Implementation patterns
- `src/services/inventory_item_service.py:225` - consume_fifo() function
- `src/services/recipe_service.py:1426` - get_aggregated_ingredients() function

**Key Integration Points**:
```python
# Availability check (dry run - no mutation)
result = inventory_item_service.consume_fifo(ingredient_slug, quantity, dry_run=True)
# Returns: {consumed, breakdown, shortfall, satisfied, total_cost}

# Get aggregated ingredients for nested recipes
ingredients = recipe_service.get_aggregated_ingredients(recipe_id)
# Returns: List of ingredient requirements

# Actual FIFO consumption
result = inventory_item_service.consume_fifo(ingredient_slug, quantity, dry_run=False)
```

**Constraints**:
- Must use session_scope() for transaction management
- User specifies finished_unit_id (recipe has 1:N relationship with FinishedUnits)
- Must validate finished_unit belongs to specified recipe
- actual_yield can be 0 (failed batch - ingredients still consumed)

## Subtasks & Detailed Guidance

### Subtask T009 - Create batch_production_service.py structure
- **Purpose**: Establish module structure with imports and docstrings
- **File**: `src/services/batch_production_service.py`
- **Parallel?**: No (prerequisite for other subtasks)

**Steps**:
1. Create new file with comprehensive module docstring
2. Add imports:
   ```python
   from typing import Dict, Any, List, Optional
   from decimal import Decimal
   from datetime import datetime

   from sqlalchemy.orm import joinedload

   from src.models import ProductionRun, ProductionConsumption, Recipe, FinishedUnit
   from src.services.database import session_scope
   from src.services import inventory_item_service
   from src.services.recipe_service import get_aggregated_ingredients
   ```
3. Add type definitions (MissingIngredient, AvailabilityResult, ProductionResult)
4. Add placeholder function signatures

### Subtask T010 - Implement check_can_produce()
- **Purpose**: Verify ingredient availability before production without mutating inventory
- **File**: `src/services/batch_production_service.py`
- **Parallel?**: No (depends on T009)

**Function Signature**:
```python
def check_can_produce(
    recipe_id: int,
    num_batches: int,
    *,
    session=None
) -> Dict[str, Any]:
```

**Implementation Steps**:
1. Validate recipe exists (raise RecipeNotFoundError if not)
2. Get aggregated ingredients via get_aggregated_ingredients(recipe_id)
3. For each ingredient:
   - Calculate required quantity: ingredient.quantity * num_batches
   - Call consume_fifo(ingredient_slug, required_qty, dry_run=True)
   - If not satisfied, add to missing list with needed/available quantities
4. Return structured result:
   ```python
   {
       "can_produce": len(missing) == 0,
       "missing": [
           {"ingredient_slug": "flour", "ingredient_name": "All-Purpose Flour",
            "needed": Decimal("4.0"), "available": Decimal("2.0"), "unit": "cups"}
       ]
   }
   ```

**Edge Cases**:
- Recipe with no ingredients: return can_produce=True, missing=[]
- Nested recipe: get_aggregated_ingredients handles flattening
- Unit conversion: consume_fifo handles conversion internally

### Subtask T011 - Implement record_batch_production()
- **Purpose**: Record batch production with full FIFO consumption and inventory updates
- **File**: `src/services/batch_production_service.py`
- **Parallel?**: No (depends on T009, T010)

**Function Signature**:
```python
def record_batch_production(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    *,
    produced_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    session=None
) -> Dict[str, Any]:
```

**Implementation Steps**:
1. Start session_scope() transaction
2. Validate recipe exists
3. Validate finished_unit exists and belongs to recipe:
   ```python
   finished_unit = session.get(FinishedUnit, finished_unit_id)
   if not finished_unit or finished_unit.recipe_id != recipe_id:
       raise FinishedUnitRecipeMismatchError(...)
   ```
4. Get aggregated ingredients
5. Calculate expected_yield: num_batches * finished_unit.items_per_batch (if applicable)
6. Initialize tracking variables:
   ```python
   total_ingredient_cost = Decimal("0.0000")
   consumption_records = []
   ```
7. For each ingredient:
   - Calculate required quantity
   - Call consume_fifo(ingredient_slug, qty, dry_run=False)
   - If not satisfied, raise InsufficientInventoryError
   - Accumulate total_cost
   - Create consumption record dict
8. Increment FinishedUnit.inventory_count:
   ```python
   finished_unit.inventory_count += actual_yield
   ```
9. Calculate per_unit_cost:
   ```python
   per_unit_cost = total_ingredient_cost / actual_yield if actual_yield > 0 else Decimal("0.0000")
   ```
10. Create ProductionRun record
11. Create ProductionConsumption records for each ingredient
12. Commit transaction (session_scope handles this)
13. Return ProductionResult dict

**Transaction Safety**:
- All operations within single session_scope
- Any exception causes automatic rollback
- No partial consumption possible

### Subtask T012 - Add custom exceptions
- **Purpose**: Define clear exception types for error handling
- **File**: `src/services/batch_production_service.py` (top of file)
- **Parallel?**: Yes (can be done alongside T009)

**Exceptions to Define**:
```python
class RecipeNotFoundError(Exception):
    def __init__(self, recipe_id: int):
        self.recipe_id = recipe_id
        super().__init__(f"Recipe with ID {recipe_id} not found")

class FinishedUnitNotFoundError(Exception):
    def __init__(self, finished_unit_id: int):
        self.finished_unit_id = finished_unit_id
        super().__init__(f"FinishedUnit with ID {finished_unit_id} not found")

class FinishedUnitRecipeMismatchError(Exception):
    def __init__(self, finished_unit_id: int, recipe_id: int):
        self.finished_unit_id = finished_unit_id
        self.recipe_id = recipe_id
        super().__init__(f"FinishedUnit {finished_unit_id} does not belong to Recipe {recipe_id}")

class InsufficientInventoryError(Exception):
    def __init__(self, ingredient_slug: str, needed: Decimal, available: Decimal):
        self.ingredient_slug = ingredient_slug
        self.needed = needed
        self.available = available
        super().__init__(f"Insufficient {ingredient_slug}: need {needed}, have {available}")
```

### Subtask T013 - Update services __init__.py
- **Purpose**: Export new service module
- **File**: `src/services/__init__.py`
- **Parallel?**: No (depends on T009-T012)

**Steps**:
1. Add import for batch_production_service module (or specific functions)
2. Verify import works: `from src.services import batch_production_service`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Transaction not atomic | Use single session_scope for all operations |
| Division by zero on per_unit_cost | Check actual_yield > 0 before division |
| FIFO returns unexpected structure | Validate consume_fifo return format in tests |
| Nested recipe aggregation fails | get_aggregated_ingredients is tested in Feature 012 |

## Definition of Done Checklist

- [ ] T009: Module structure created with all imports
- [ ] T010: check_can_produce() implemented and handles all scenarios
- [ ] T011: record_batch_production() implemented with full transaction logic
- [ ] T012: All custom exceptions defined
- [ ] T013: Service exported from __init__.py
- [ ] Can call check_can_produce() and get accurate results
- [ ] Can call record_batch_production() and see inventory changes
- [ ] `tasks.md` updated with status change

## Review Guidance

**Reviewer Checklist**:
- [ ] Single session_scope wraps all mutations in record_batch_production
- [ ] FinishedUnit.recipe_id validation present
- [ ] per_unit_cost handles actual_yield=0
- [ ] consume_fifo called with dry_run=False for actual consumption
- [ ] ProductionConsumption records created for each ingredient
- [ ] Exception messages are clear and include relevant IDs

## Activity Log

- 2025-12-09T17:30:00Z - system - lane=planned - Prompt created.
- 2025-12-10T03:48:09Z – claude – shell_pid=15592 – lane=doing – Implementation complete - batch_production_service with check_can_produce, record_batch_production
- 2025-12-10T03:48:10Z – claude – shell_pid=15592 – lane=for_review – Ready for review - 95.40% test coverage
- 2025-12-10T03:53:39Z – claude-reviewer – shell_pid=17130 – lane=done – Review approved: check_can_produce, record_batch_production with FIFO consumption - 95.40% coverage
