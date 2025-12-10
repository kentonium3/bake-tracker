---
work_package_id: "WP05"
subtasks:
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
title: "Assembly Service - Core"
phase: "Phase 3 - Assembly"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T17:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Assembly Service - Core

## Objectives & Success Criteria

Implement the core AssemblyService with:
- `check_can_assemble(finished_good_id, quantity)` - Availability check for components
- `record_assembly(...)` - Record assembly with component/packaging consumption

**Success Criteria**:
- [ ] check_can_assemble returns accurate availability for FinishedUnits and packaging
- [ ] record_assembly atomically: decrements FU inventory, consumes packaging, increments FG inventory
- [ ] All operations complete within single transaction (rollback on any failure)
- [ ] Nested FinishedGood components handled correctly
- [ ] Packaging consumed via FIFO from inventory

## Context & Constraints

**Reference Documents**:
- `kitty-specs/013-production-inventory-tracking/contracts/assembly_service.py` - Service interface
- `kitty-specs/013-production-inventory-tracking/data-model.md` - Entity definitions
- `src/models/composition.py` - Composition BOM model
- `src/models/finished_good.py` - FinishedGood model

**Composition Model Structure** (from composition.py):
```python
# Composition links a parent (assembly_id or package_id) to components
# Components can be: finished_unit_id, finished_good_id, or packaging_product_id
# Exactly one component type is non-null per row
```

**Key Integration Points**:
```python
# Query Composition for a FinishedGood's components
compositions = session.query(Composition).filter(
    Composition.assembly_id == finished_good_id
).all()

# For each composition:
#   - If finished_unit_id: check FinishedUnit.inventory_count
#   - If finished_good_id: check FinishedGood.inventory_count (nested)
#   - If packaging_product_id: check via consume_fifo dry_run
```

**Constraints**:
- Must query Composition to discover components
- FinishedUnit consumption: direct decrement of inventory_count
- Packaging consumption: use consume_fifo (packaging products link to ingredients)
- Nested FinishedGood: decrement FinishedGood.inventory_count

## Subtasks & Detailed Guidance

### Subtask T023 - Create assembly_service.py structure
- **Purpose**: Establish module structure with imports and docstrings
- **File**: `src/services/assembly_service.py`
- **Parallel?**: No (prerequisite for other subtasks)

**Steps**:
1. Create new file with module docstring
2. Add imports:
   ```python
   from typing import Dict, Any, List, Optional, Literal
   from decimal import Decimal
   from datetime import datetime

   from sqlalchemy.orm import joinedload

   from src.models import (
       AssemblyRun, AssemblyFinishedUnitConsumption, AssemblyPackagingConsumption,
       FinishedGood, FinishedUnit, Composition, Product
   )
   from src.services.database import session_scope
   from src.services import inventory_item_service
   ```
3. Add type definitions for results
4. Add placeholder function signatures

### Subtask T024 - Implement check_can_assemble()
- **Purpose**: Verify component availability before assembly
- **File**: `src/services/assembly_service.py`
- **Parallel?**: No (depends on T023)

**Function Signature**:
```python
def check_can_assemble(
    finished_good_id: int,
    quantity: int,
    *,
    session=None
) -> Dict[str, Any]:
```

**Implementation Steps**:
1. Validate FinishedGood exists (raise FinishedGoodNotFoundError if not)
2. Query Composition for this FinishedGood's components:
   ```python
   compositions = session.query(Composition).filter(
       Composition.assembly_id == finished_good_id
   ).all()
   ```
3. For each composition, check availability:

   **For FinishedUnit components**:
   ```python
   if comp.finished_unit_id:
       fu = session.get(FinishedUnit, comp.finished_unit_id)
       needed = comp.component_quantity * quantity
       if fu.inventory_count < needed:
           missing.append({
               "component_type": "finished_unit",
               "component_id": fu.id,
               "component_name": fu.display_name,
               "needed": needed,
               "available": fu.inventory_count
           })
   ```

   **For FinishedGood components (nested)**:
   ```python
   if comp.finished_good_id:
       nested_fg = session.get(FinishedGood, comp.finished_good_id)
       needed = comp.component_quantity * quantity
       if nested_fg.inventory_count < needed:
           missing.append({...})
   ```

   **For packaging products**:
   ```python
   if comp.packaging_product_id:
       product = session.get(Product, comp.packaging_product_id)
       # Get ingredient slug from product
       ingredient_slug = product.ingredient.slug
       needed = comp.component_quantity * quantity
       result = inventory_item_service.consume_fifo(ingredient_slug, needed, dry_run=True)
       if not result["satisfied"]:
           missing.append({
               "component_type": "packaging",
               "component_id": product.id,
               "component_name": product.name,
               "needed": needed,
               "available": result["consumed"],
               "unit": product.ingredient.recipe_unit
           })
   ```

4. Return structured result:
   ```python
   {"can_assemble": len(missing) == 0, "missing": missing}
   ```

### Subtask T025 - Implement record_assembly()
- **Purpose**: Record assembly with full component consumption
- **File**: `src/services/assembly_service.py`
- **Parallel?**: No (depends on T023, T024)

**Function Signature**:
```python
def record_assembly(
    finished_good_id: int,
    quantity: int,
    *,
    assembled_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    session=None
) -> Dict[str, Any]:
```

**Implementation Steps**:
1. Start session_scope() transaction
2. Validate FinishedGood exists
3. Query Composition components
4. Initialize tracking:
   ```python
   total_component_cost = Decimal("0.0000")
   fu_consumptions = []
   pkg_consumptions = []
   ```
5. For each composition, consume:

   **For FinishedUnit components**:
   ```python
   if comp.finished_unit_id:
       fu = session.get(FinishedUnit, comp.finished_unit_id)
       needed = int(comp.component_quantity * quantity)
       if fu.inventory_count < needed:
           raise InsufficientFinishedUnitError(fu.id, needed, fu.inventory_count)

       # Capture cost before decrementing
       unit_cost = fu.unit_cost or Decimal("0.0000")
       cost = unit_cost * needed

       fu.inventory_count -= needed
       total_component_cost += cost

       fu_consumptions.append({
           "finished_unit_id": fu.id,
           "quantity_consumed": needed,
           "unit_cost_at_consumption": unit_cost,
           "total_cost": cost
       })
   ```

   **For FinishedGood components (nested)**:
   ```python
   if comp.finished_good_id:
       nested_fg = session.get(FinishedGood, comp.finished_good_id)
       needed = int(comp.component_quantity * quantity)
       if nested_fg.inventory_count < needed:
           raise InsufficientFinishedGoodError(...)
       nested_fg.inventory_count -= needed
       # Add to fu_consumptions with special handling or separate tracking
   ```

   **For packaging products**:
   ```python
   if comp.packaging_product_id:
       product = session.get(Product, comp.packaging_product_id)
       ingredient_slug = product.ingredient.slug
       needed = Decimal(str(comp.component_quantity * quantity))

       result = inventory_item_service.consume_fifo(ingredient_slug, needed, dry_run=False)
       if not result["satisfied"]:
           raise InsufficientPackagingError(product.id, needed, result["consumed"])

       total_component_cost += result["total_cost"]
       pkg_consumptions.append({
           "product_id": product.id,
           "quantity_consumed": needed,
           "unit": product.ingredient.recipe_unit,
           "total_cost": result["total_cost"]
       })
   ```

6. Increment FinishedGood.inventory_count:
   ```python
   finished_good.inventory_count += quantity
   ```
7. Calculate per_unit_cost:
   ```python
   per_unit_cost = total_component_cost / quantity
   ```
8. Create AssemblyRun record
9. Create consumption ledger records
10. Commit and return result

### Subtask T026 - Add custom exceptions
- **Purpose**: Define clear exception types for assembly errors
- **File**: `src/services/assembly_service.py` (top of file)
- **Parallel?**: Yes

**Exceptions to Define**:
```python
class FinishedGoodNotFoundError(Exception):
    def __init__(self, finished_good_id: int):
        self.finished_good_id = finished_good_id
        super().__init__(f"FinishedGood with ID {finished_good_id} not found")

class InsufficientFinishedUnitError(Exception):
    def __init__(self, finished_unit_id: int, needed: int, available: int):
        self.finished_unit_id = finished_unit_id
        self.needed = needed
        self.available = available
        super().__init__(f"Insufficient FinishedUnit {finished_unit_id}: need {needed}, have {available}")

class InsufficientPackagingError(Exception):
    def __init__(self, product_id: int, needed: Decimal, available: Decimal):
        self.product_id = product_id
        self.needed = needed
        self.available = available
        super().__init__(f"Insufficient packaging product {product_id}: need {needed}, have {available}")
```

### Subtask T027 - Update services __init__.py
- **Purpose**: Export new service module
- **File**: `src/services/__init__.py`
- **Parallel?**: No (depends on T023-T026)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Composition query complexity | Test with various component configurations |
| Packaging product to ingredient mapping | Verify Product.ingredient relationship exists |
| Integer vs Decimal for quantities | FU uses int, packaging uses Decimal |
| Nested FG recursion | Handle one level of nesting; deeper nesting is edge case |

## Definition of Done Checklist

- [ ] T023: Module structure created
- [ ] T024: check_can_assemble() handles all component types
- [ ] T025: record_assembly() with full transaction logic
- [ ] T026: Custom exceptions defined
- [ ] T027: Service exported
- [ ] Can check assembly availability
- [ ] Can record assembly with inventory changes
- [ ] `tasks.md` updated

## Review Guidance

**Reviewer Checklist**:
- [ ] All three component types handled (finished_unit, finished_good, packaging)
- [ ] Packaging uses consume_fifo, not direct inventory decrement
- [ ] Integer quantities for FinishedUnit, Decimal for packaging
- [ ] Single transaction for all operations

## Activity Log

- 2025-12-09T17:30:00Z - system - lane=planned - Prompt created.
