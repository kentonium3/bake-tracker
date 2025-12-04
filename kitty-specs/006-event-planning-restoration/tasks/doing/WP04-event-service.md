---
work_package_id: "WP04"
subtasks:
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
title: "Event Service Implementation"
phase: "Phase 2 - Services Layer"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "8297"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-03"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Event Service Implementation

## Objectives & Success Criteria

- Implement EventService with event CRUD and year filtering
- Implement assignment operations (assign packages to recipients)
- Implement aggregation calculations (recipe needs, shopping list, summary)
- Integrate with PantryService for shopping list calculations

**Success Criteria**:
- All methods from contracts/event_service.md implemented
- Year filtering works correctly (FR-020)
- Recipe needs aggregates across all assignments (FR-025)
- Shopping list shows shortfall with pantry integration (FR-026)
- Unit tests pass with >70% coverage

## Context & Constraints

**Architecture Decision**: Per research decision D4, rewrite service from scratch. The existing service imports non-existent Bundle.

**Key Documents**:
- `kitty-specs/006-event-planning-restoration/contracts/event_service.md` - Full interface specification
- `kitty-specs/006-event-planning-restoration/data-model.md` - Cost calculation flow
- `kitty-specs/006-event-planning-restoration/quickstart.md` - Usage examples

**Dependencies**: Requires WP03 complete (PackageService for cost calculations).

## Subtasks & Detailed Guidance

### Subtask T023 - Create `src/services/event_service.py` with basic structure

**Purpose**: Set up the service file with proper imports and class structure.

**Steps**:
1. Create `src/services/event_service.py`
2. Add imports:
   ```python
   from decimal import Decimal
   from typing import Optional, List
   from datetime import date
   from sqlalchemy.orm import Session
   from src.models import Event, EventRecipientPackage, Recipient, Package
   from src.services.package_service import PackageService
   from src.services.pantry_service import PantryService  # For shopping list
   ```
3. Create EventService class following patterns from other services

**Files**: `src/services/event_service.py`

### Subtask T024 - Implement get_event_by_id, get_event_by_name, get_all_events, get_events_by_year

**Purpose**: Basic read operations for events.

**Steps**:
1. Implement get_event_by_id (indexed lookup)
2. Implement get_event_by_name (indexed lookup)
3. Implement get_all_events ordered by event_date descending
4. Implement get_events_by_year (FR-020):
   ```python
   def get_events_by_year(year: int) -> List[Event]:
       return session.query(Event).filter(Event.year == year).order_by(Event.event_date.desc()).all()
   ```

**Files**: `src/services/event_service.py`

### Subtask T025 - Implement get_available_years for year filter dropdown

**Purpose**: Populate year filter dropdown in UI.

**Steps**:
1. Implement get_available_years:
   ```python
   def get_available_years() -> List[int]:
       years = session.query(Event.year).distinct().order_by(Event.year.desc()).all()
       return [y[0] for y in years]
   ```

**Files**: `src/services/event_service.py`

### Subtask T026 - Implement create_event, update_event, delete_event

**Purpose**: CRUD operations for events.

**Steps**:
1. Implement create_event (FR-019):
   ```python
   def create_event(name: str, event_date: date, year: int, notes: str = None) -> Event:
       if not name or not name.strip():
           raise ValueError("Event name is required")
       event = Event(name=name, event_date=event_date, year=year, notes=notes)
       session.add(event)
       session.commit()
       return event
   ```
2. Implement update_event (FR-021)
3. Implement delete_event with cascade option (FR-022):
   ```python
   def delete_event(event_id: int, cascade_assignments: bool = False) -> bool:
       event = get_event_by_id(event_id)
       if not event:
           return False
       if event.event_recipient_packages and not cascade_assignments:
           raise EventHasAssignmentsError(f"Event {event_id} has {len(event.event_recipient_packages)} assignments")
       # Cascade delete handled by relationship if cascade_assignments=True
       session.delete(event)
       session.commit()
       return True
   ```

**Files**: `src/services/event_service.py`

### Subtask T027 - Implement assign_package_to_recipient, update_assignment, remove_assignment

**Purpose**: Manage recipient-package assignments (FR-024).

**Steps**:
1. Implement assign_package_to_recipient:
   ```python
   def assign_package_to_recipient(event_id: int, recipient_id: int, package_id: int,
                                    quantity: int = 1, notes: str = None) -> EventRecipientPackage:
       # Validate all IDs exist
       erp = EventRecipientPackage(
           event_id=event_id, recipient_id=recipient_id, package_id=package_id,
           quantity=quantity, notes=notes
       )
       session.add(erp)
       session.commit()
       return erp
   ```
2. Implement update_assignment
3. Implement remove_assignment

**Files**: `src/services/event_service.py`

### Subtask T028 - Implement get_event_assignments, get_recipient_assignments_for_event

**Purpose**: Query operations for assignments.

**Steps**:
1. Implement get_event_assignments:
   ```python
   def get_event_assignments(event_id: int) -> List[EventRecipientPackage]:
       return session.query(EventRecipientPackage).filter(
           EventRecipientPackage.event_id == event_id
       ).all()
   ```
2. Implement get_recipient_assignments_for_event

**Files**: `src/services/event_service.py`

### Subtask T029 - Implement get_event_total_cost, get_event_recipient_count, get_event_package_count

**Purpose**: Basic aggregation methods.

**Steps**:
1. Implement get_event_total_cost using PackageService:
   ```python
   def get_event_total_cost(event_id: int) -> Decimal:
       assignments = get_event_assignments(event_id)
       total = Decimal("0")
       for erp in assignments:
           package_cost = PackageService.calculate_package_cost(erp.package_id)
           total += package_cost * erp.quantity
       return total
   ```
2. Implement get_event_recipient_count (unique recipients)
3. Implement get_event_package_count (sum of quantities)

**Files**: `src/services/event_service.py`

### Subtask T030 - Implement get_event_summary (FR-027)

**Purpose**: Complete summary for Summary tab.

**Steps**:
1. Implement get_event_summary:
   ```python
   def get_event_summary(event_id: int) -> dict:
       assignments = get_event_assignments(event_id)
       cost_by_recipient = {}

       for erp in assignments:
           recipient_name = erp.recipient.name
           assignment_cost = PackageService.calculate_package_cost(erp.package_id) * erp.quantity
           cost_by_recipient[recipient_name] = cost_by_recipient.get(recipient_name, Decimal("0")) + assignment_cost

       return {
           "total_cost": get_event_total_cost(event_id),
           "recipient_count": get_event_recipient_count(event_id),
           "package_count": get_event_package_count(event_id),
           "assignment_count": len(assignments),
           "cost_by_recipient": [
               {"recipient_name": name, "cost": cost}
               for name, cost in cost_by_recipient.items()
           ]
       }
   ```

**Files**: `src/services/event_service.py`
**Performance**: <2s for 50 assignments (SC-004)

### Subtask T031 - Implement get_recipe_needs (FR-025)

**Purpose**: Calculate batch counts needed for all recipes.

**Steps**:
1. Implement get_recipe_needs:
   ```python
   from math import ceil

   def get_recipe_needs(event_id: int) -> List[dict]:
       assignments = get_event_assignments(event_id)
       recipe_totals = {}  # recipe_id -> total units needed
       recipe_info = {}    # recipe_id -> {name, items_per_batch}

       for erp in assignments:
           package = erp.package
           for pfg in package.package_finished_goods:
               fg = pfg.finished_good
               # Traverse compositions to get FinishedUnits
               for composition in fg.components:
                   if composition.finished_unit_id:
                       fu = composition.finished_unit
                       recipe_id = fu.recipe_id
                       units = composition.component_quantity * pfg.quantity * erp.quantity
                       recipe_totals[recipe_id] = recipe_totals.get(recipe_id, 0) + units
                       recipe_info[recipe_id] = {
                           "name": fu.recipe.name,
                           "items_per_batch": fu.items_per_batch
                       }

       result = []
       for recipe_id, total_units in recipe_totals.items():
           info = recipe_info[recipe_id]
           batches = ceil(total_units / info["items_per_batch"])
           result.append({
               "recipe_id": recipe_id,
               "recipe_name": info["name"],
               "total_units_needed": total_units,
               "batches_needed": batches,
               "items_per_batch": info["items_per_batch"]
           })
       return result
   ```

**Files**: `src/services/event_service.py`
**Note**: Must traverse: assignments -> packages -> finished_goods -> compositions -> finished_units -> recipes

### Subtask T032 - Implement get_shopping_list (FR-026)

**Purpose**: Calculate ingredients needed with pantry comparison.

**Steps**:
1. Implement get_shopping_list:
   ```python
   def get_shopping_list(event_id: int) -> List[dict]:
       recipe_needs = get_recipe_needs(event_id)
       ingredient_totals = {}  # ingredient_id -> quantity needed
       ingredient_info = {}    # ingredient_id -> {name, unit}

       for recipe_need in recipe_needs:
           recipe = RecipeService.get_recipe_by_id(recipe_need["recipe_id"])
           for ri in recipe.recipe_ingredients:
               ing_id = ri.ingredient_id
               # Scale quantity by batches needed
               qty = ri.quantity * recipe_need["batches_needed"]
               ingredient_totals[ing_id] = ingredient_totals.get(ing_id, Decimal("0")) + qty
               ingredient_info[ing_id] = {
                   "name": ri.ingredient.name,
                   "unit": ri.unit
               }

       result = []
       for ing_id, qty_needed in ingredient_totals.items():
           info = ingredient_info[ing_id]
           qty_on_hand = PantryService.get_on_hand_quantity(ing_id)
           shortfall = max(Decimal("0"), qty_needed - qty_on_hand)
           result.append({
               "ingredient_id": ing_id,
               "ingredient_name": info["name"],
               "unit": info["unit"],
               "quantity_needed": qty_needed,
               "quantity_on_hand": qty_on_hand,
               "shortfall": shortfall
           })
       return result
   ```

**Files**: `src/services/event_service.py`
**FR Reference**: FR-029 (PantryService integration)

### Subtask T033 - Create custom exception classes

**Purpose**: Define service-specific exceptions.

**Steps**:
1. Create exceptions:
   ```python
   class EventNotFoundError(Exception):
       pass

   class EventHasAssignmentsError(Exception):
       pass

   class RecipientNotFoundError(Exception):
       pass

   class DuplicateAssignmentError(Exception):
       pass
   ```

**Files**: `src/services/event_service.py` or `src/services/exceptions.py`
**Parallel**: Can proceed alongside other subtasks

### Subtask T034 - Write unit tests in `src/tests/test_event_service.py`

**Purpose**: Achieve >70% coverage per constitution.

**Steps**:
1. Create `src/tests/test_event_service.py`
2. Write tests for:
   - Event CRUD operations
   - Year filtering (FR-020)
   - Assignment operations (FR-024)
   - Cost calculations (verify FIFO chain)
   - Recipe needs aggregation (FR-025)
   - Shopping list with pantry integration (FR-026)
   - Cascade delete behavior (FR-022)
3. Use pytest fixtures for test data
4. Mock PantryService.get_on_hand_quantity for shopping list tests

**Files**: `src/tests/test_event_service.py`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Recipe needs traversal complexity | Use eager loading, batch queries |
| PantryService integration | Mock for tests, verify integration manually |
| Performance with 50+ assignments | Profile and optimize, use caching |

## Definition of Done Checklist

- [ ] All methods from contract implemented
- [ ] Exception classes created
- [ ] Year filtering works (FR-020)
- [ ] Recipe needs aggregation correct (FR-025)
- [ ] Shopping list shows shortfall (FR-026)
- [ ] Summary includes all required fields (FR-027)
- [ ] Unit tests pass with >70% coverage
- [ ] Performance: <2s for 50 assignments (SC-004)
- [ ] `tasks.md` updated with status change

## Review Guidance

- Verify recipe needs aggregation is correct (units across multiple packages)
- Check shopping list shortfall calculation
- Test cascade delete with assignments
- Performance test with 50 assignments

## Activity Log

- 2025-12-03 - system - lane=planned - Prompt created.
- 2025-12-04T02:35:08Z – claude – shell_pid=8297 – lane=doing – Started implementation
