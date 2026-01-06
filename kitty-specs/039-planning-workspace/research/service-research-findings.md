# Service Research Findings for PlanningService Facade

## Overview

This document summarizes research on existing services in `src/services/` to support planning a new PlanningService facade with modules for batch calculation, shopping list generation, feasibility checking, and progress tracking.

**Working Directory:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/039-planning-workspace`

---

## Session Management Pattern (CRITICAL)

All services follow a consistent session management pattern that prevents SQLAlchemy object detachment issues:

```python
def operation(..., session=None):
    """Accept optional session parameter."""
    if session is not None:
        return _operation_impl(..., session)
    with session_scope() as session:
        return _operation_impl(..., session)
```

**Key Rules:**
1. Multi-step operations MUST share a session
2. Service functions that may be called from other services MUST accept `session=None`
3. When calling another service function within a transaction, ALWAYS pass the session
4. Never return ORM objects from `session_scope()` if they'll be modified later

---

## Service: inventory_item_service.py

**Purpose:** Manages inventory items with FIFO consumption and stock level queries.

### Key Functions

#### `get_total_quantity(ingredient_slug: str) -> Dict[str, Decimal]`
Returns total available quantity for an ingredient across all inventory items.
- **Returns:** `{"quantity": Decimal, "unit": str}`
- **Used for:** Stock level checks in feasibility calculations

#### `consume_fifo(slug: str, quantity: Decimal, unit: str, dry_run: bool = False, session=None) -> Dict`
Consumes inventory using FIFO (First In, First Out) strategy.
- **Parameters:**
  - `slug`: Ingredient slug
  - `quantity`: Amount to consume
  - `unit`: Unit of measurement
  - `dry_run`: If True, simulates consumption without committing (CRITICAL for planning)
  - `session`: Optional SQLAlchemy session
- **Returns:**
  ```python
  {
      "consumed": Decimal,       # Amount actually consumed
      "breakdown": List[Dict],   # Per-item consumption details
      "shortfall": Decimal,      # Amount that couldn't be fulfilled
      "satisfied": bool,         # True if fully satisfied
      "total_cost": Decimal      # Cost of consumed items
  }
  ```
- **Used for:** Batch production, assembly, shopping list generation

#### `list_inventory_items(ingredient_slug: str = None, include_zero_qty: bool = False) -> List[Dict]`
Lists inventory items, optionally filtered by ingredient.
- **Returns:** List of inventory item dictionaries with quantity, unit, cost info

#### `get_inventory_item(item_id: int) -> Dict`
Gets a single inventory item by ID.

---

## Service: recipe_service.py

**Purpose:** Manages recipes including nested recipe support and ingredient aggregation.

### Key Functions

#### `get_aggregated_ingredients(recipe_id: int, multiplier: float = 1.0, session=None) -> List[Dict]`
**CRITICAL FOR PLANNING** - Aggregates all ingredients needed for a recipe, handling nested recipes.
- **Parameters:**
  - `recipe_id`: Recipe to aggregate
  - `multiplier`: Scale factor (e.g., 2.0 for double batch)
  - `session`: Optional SQLAlchemy session
- **Returns:**
  ```python
  [
      {
          "ingredient_id": int,
          "ingredient_slug": str,
          "ingredient_name": str,
          "quantity": Decimal,      # Total quantity needed
          "unit": str,
          "sources": List[Dict]     # Where this ingredient comes from (direct or nested)
      }
  ]
  ```
- **Handles:** Nested recipes up to 3 levels, circular reference prevention
- **Used for:** Shopping list generation, feasibility checking

#### `get_recipe(recipe_id: int) -> Dict`
Gets recipe details including yield information.
- **Returns:** Recipe dict with `id`, `name`, `slug`, `yield_quantity`, `yield_unit`, `category`, etc.

#### `list_recipes(category: str = None) -> List[Dict]`
Lists all recipes, optionally filtered by category.

#### `get_recipe_by_slug(slug: str) -> Dict`
Gets recipe by slug identifier.

---

## Service: batch_production_service.py

**Purpose:** Manages batch production runs with feasibility checking and inventory consumption.

### Key Functions

#### `check_can_produce(recipe_id: int, num_batches: int, scale_factor: float = 1.0, session=None) -> Dict`
**CRITICAL FOR PLANNING** - Checks if sufficient inventory exists for production.
- **Parameters:**
  - `recipe_id`: Recipe to check
  - `num_batches`: Number of batches to produce
  - `scale_factor`: Scale factor per batch
  - `session`: Optional SQLAlchemy session
- **Returns:**
  ```python
  {
      "can_produce": bool,
      "missing": [
          {
              "ingredient_slug": str,
              "ingredient_name": str,
              "needed": Decimal,
              "available": Decimal,
              "shortfall": Decimal,
              "unit": str
          }
      ]
  }
  ```
- **Uses:** `get_aggregated_ingredients()` internally with `dry_run=True` FIFO simulation

#### `record_batch_production(recipe_id: int, num_batches: int, scale_factor: float = 1.0, notes: str = None, event_id: int = None, session=None) -> Dict`
Records a batch production run, consuming inventory via FIFO.
- **Parameters:**
  - `recipe_id`, `num_batches`, `scale_factor`: Production details
  - `notes`: Optional production notes
  - `event_id`: Optional event linkage for tracking
  - `session`: Optional SQLAlchemy session
- **Returns:**
  ```python
  {
      "production_run_id": int,
      "recipe_id": int,
      "num_batches": int,
      "yield_quantity": Decimal,
      "yield_unit": str,
      "ingredients_consumed": List[Dict],
      "total_cost": Decimal
  }
  ```

#### `get_production_run(run_id: int) -> Dict`
Gets details of a specific production run.

#### `list_production_runs(recipe_id: int = None, event_id: int = None) -> List[Dict]`
Lists production runs with optional filtering.

---

## Service: assembly_service.py

**Purpose:** Manages assembly of finished goods from recipes and packaging materials.

### Key Functions

#### `check_can_assemble(finished_good_id: int, quantity: int, session=None) -> Dict`
**CRITICAL FOR PLANNING** - Checks if assembly is feasible.
- **Parameters:**
  - `finished_good_id`: Finished good to assemble
  - `quantity`: Number of units to assemble
  - `session`: Optional SQLAlchemy session
- **Returns:**
  ```python
  {
      "can_assemble": bool,
      "missing_components": [
          {
              "component_type": str,  # "recipe" or "packaging"
              "name": str,
              "needed": Decimal,
              "available": Decimal,
              "shortfall": Decimal,
              "unit": str
          }
      ]
  }
  ```

#### `record_assembly(finished_good_id: int, quantity: int, notes: str = None, event_id: int = None, session=None) -> Dict`
Records an assembly run.
- **Parameters:**
  - `finished_good_id`, `quantity`: Assembly details
  - `notes`: Optional notes
  - `event_id`: Optional event linkage
  - `session`: Optional SQLAlchemy session
- **Returns:**
  ```python
  {
      "assembly_run_id": int,
      "finished_good_id": int,
      "quantity": int,
      "components_consumed": List[Dict],
      "packaging_consumed": List[Dict],
      "total_cost": Decimal
  }
  ```

#### `get_assembly_run(run_id: int) -> Dict`
Gets details of a specific assembly run.

#### `list_assembly_runs(finished_good_id: int = None, event_id: int = None) -> List[Dict]`
Lists assembly runs with optional filtering.

---

## Service: event_service.py

**Purpose:** Manages events with production/assembly targets and progress tracking.

### Key Functions for Planning Integration

#### `get_recipe_needs(event_id: int) -> List[Dict]`
Gets batch counts needed per recipe for an event.
- **Returns:** List of recipes with target batch counts

#### `get_shopping_list(event_id: int, include_packaging: bool = True) -> Dict`
**CRITICAL FOR PLANNING** - Generates shopping list for an event.
- **Parameters:**
  - `event_id`: Event to generate list for
  - `include_packaging`: Whether to include packaging materials
- **Returns:**
  ```python
  {
      "ingredients": [
          {
              "ingredient_slug": str,
              "ingredient_name": str,
              "total_needed": Decimal,
              "in_stock": Decimal,
              "to_purchase": Decimal,
              "unit": str,
              "product_recommendations": List[Dict]  # Suggested products to buy
          }
      ],
      "packaging": [...] if include_packaging else None
  }
  ```

#### `set_production_target(event_id: int, recipe_id: int, target_batches: int) -> Dict`
Sets production target for a recipe at an event.

#### `get_production_progress(event_id: int) -> Dict`
Gets production progress across all recipe targets.
- **Returns:**
  ```python
  {
      "targets": [
          {
              "recipe_id": int,
              "recipe_name": str,
              "target_batches": int,
              "produced_batches": int,
              "progress_percent": float
          }
      ],
      "overall_progress": float
  }
  ```

#### `set_assembly_target(event_id: int, finished_good_id: int, target_quantity: int) -> Dict`
Sets assembly target for a finished good at an event.

#### `get_assembly_progress(event_id: int) -> Dict`
Gets assembly progress across all finished good targets.

#### `get_event_overall_progress(event_id: int) -> Dict`
**CRITICAL FOR PLANNING** - Gets aggregated progress summary.
- **Returns:**
  ```python
  {
      "production_progress": float,
      "assembly_progress": float,
      "overall_progress": float,
      "status": str  # "not_started", "in_progress", "complete"
  }
  ```

---

## Service: finished_good_service.py

**Purpose:** Manages finished goods (assembled products).

### Key Functions

#### `get_finished_good(finished_good_id: int) -> Dict`
Gets finished good details including components.

#### `list_finished_goods(category: str = None) -> List[Dict]`
Lists all finished goods.

#### `get_finished_good_components(finished_good_id: int) -> Dict`
Gets component breakdown for a finished good.
- **Returns:**
  ```python
  {
      "recipes": [{"recipe_id": int, "quantity": Decimal, ...}],
      "packaging": [{"packaging_id": int, "quantity": int, ...}]
  }
  ```

---

## Database Layer (database.py)

### Session Management

#### `session_scope() -> Generator[Session, None, None]`
Transactional context manager for write operations.
```python
with session_scope() as session:
    # All operations in single transaction
    # Commits on success, rolls back on exception
```

#### `get_db_session() -> Generator[Session, None, None]`
Read-only session context (deprecated in favor of session_scope).

---

## Exception Patterns (exceptions.py)

### Base Classes
- `ServiceError` - Base for service-layer errors
- `ServiceException` - Alternative base class

### Domain-Specific Exceptions
- `ValidationError` - Input validation failures
- `DatabaseError` - Database operation failures
- `NotFoundError` - Entity not found
- `InsufficientInventoryError` - Not enough stock for operation
- `CircularReferenceError` - Circular recipe references detected

### Pattern
```python
try:
    result = service_operation(...)
except InsufficientInventoryError as e:
    # Handle specific case
except ServiceError as e:
    # Handle general service error
```

---

## Naming Conventions

1. **Function names:** `verb_noun` pattern (e.g., `get_recipe`, `list_inventory_items`, `check_can_produce`)
2. **Check functions:** `check_can_*` returns feasibility dict
3. **Record functions:** `record_*` performs operation and returns result
4. **Progress functions:** `get_*_progress` returns progress tracking dict
5. **Parameters:** `session=None` always last parameter
6. **Returns:** Always dictionaries, never raw ORM objects

---

## Recommendations for PlanningService Facade

### Architecture

```
PlanningService (Facade)
|-- BatchCalculationModule
|   |-- Uses: recipe_service.get_aggregated_ingredients()
|   |-- Uses: batch_production_service.check_can_produce()
|
|-- ShoppingListModule
|   |-- Uses: event_service.get_shopping_list()
|   |-- Uses: inventory_item_service.get_total_quantity()
|
|-- FeasibilityModule
|   |-- Uses: batch_production_service.check_can_produce()
|   |-- Uses: assembly_service.check_can_assemble()
|
|-- ProgressTrackingModule
    |-- Uses: event_service.get_production_progress()
    |-- Uses: event_service.get_assembly_progress()
    |-- Uses: event_service.get_event_overall_progress()
```

### Key Integration Points

1. **Batch Calculation:**
   - Call `get_aggregated_ingredients(recipe_id, multiplier)` for ingredient needs
   - Use `check_can_produce()` with `dry_run` behavior for simulation

2. **Shopping List Generation:**
   - `event_service.get_shopping_list()` already provides comprehensive shopping list
   - Consider wrapping with additional filtering/formatting

3. **Feasibility Checking:**
   - Combine `check_can_produce()` and `check_can_assemble()` results
   - Provide unified feasibility view across production and assembly

4. **Progress Tracking:**
   - `get_event_overall_progress()` provides aggregated view
   - Consider adding time-based projections

### Session Management for Facade

The facade should follow the same session pattern:
```python
class PlanningService:
    def comprehensive_plan(self, event_id: int, session=None) -> Dict:
        if session is not None:
            return self._comprehensive_plan_impl(event_id, session)
        with session_scope() as session:
            return self._comprehensive_plan_impl(event_id, session)

    def _comprehensive_plan_impl(self, event_id: int, session) -> Dict:
        # Pass session to all service calls
        shopping = get_shopping_list(event_id, session=session)
        progress = get_event_overall_progress(event_id, session=session)
        # ... combine results
```

---

## Summary

The existing services provide a solid foundation for the PlanningService facade:

| Module | Primary Service Dependencies |
|--------|------------------------------|
| Batch Calculation | recipe_service, batch_production_service |
| Shopping List | event_service, inventory_item_service |
| Feasibility | batch_production_service, assembly_service |
| Progress Tracking | event_service |

Key patterns to maintain:
- Optional `session=None` parameter on all public functions
- Return dictionaries, not ORM objects
- Use `dry_run=True` for simulations
- Comprehensive error handling with domain-specific exceptions
