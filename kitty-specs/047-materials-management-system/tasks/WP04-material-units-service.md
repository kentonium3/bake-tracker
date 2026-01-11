---
work_package_id: "WP04"
subtasks:
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
title: "Material Units Service - User Story 3"
phase: "Phase 1 - Core Services"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Material Units Service - User Story 3

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Implement MaterialUnit management with availability and cost calculations.

**User Story**: As a baker, I need to define how much material goes into each assembly (e.g., "6 inches of ribbon") so the system can calculate inventory and costs correctly.

**Success Criteria:**
- Can create MaterialUnits defining consumption amounts
- Available inventory aggregates correctly across all products
- Current cost calculated as weighted average times quantity_per_unit
- All acceptance scenarios from spec.md User Story 3 pass

## Context & Constraints

**Reference Documents:**
- `kitty-specs/047-materials-management-system/spec.md` - User Story 3 acceptance scenarios
- `kitty-specs/047-materials-management-system/contracts/material_unit_service.md` - Service interface
- `kitty-specs/047-materials-management-system/data-model.md` - MaterialUnit entity

**Key Formulas:**
- Available inventory: `floor(sum(product.current_inventory) / quantity_per_unit)`
- Current cost: `weighted_avg_cost * quantity_per_unit`

**Dependencies:**
- WP01 (models)
- WP03 (inventory must exist to calculate availability)

## Subtasks & Detailed Guidance

### Subtask T024 - MaterialUnit CRUD Operations
- **Purpose**: Create, read, update, delete for MaterialUnit
- **File**: `src/services/material_unit_service.py`
- **Parallel?**: No
- **Steps**:
  1. Create file with standard imports
  2. Implement `create_unit(material_id, name, quantity_per_unit, slug=None, description=None, session=None)`
  3. Validate quantity_per_unit > 0
  4. Auto-generate slug if not provided
  5. Implement `get_unit(unit_id=None, slug=None, session=None)`
  6. Implement `list_units(material_id=None, session=None)`
  7. Implement `update_unit(unit_id, name=None, description=None, session=None)` - cannot change quantity_per_unit
  8. Implement `delete_unit(unit_id, session=None)` - validate not used in Composition

### Subtask T025 - Implement get_available_inventory()
- **Purpose**: Calculate how many complete units are available
- **File**: `src/services/material_unit_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `get_available_inventory(unit_id, session=None)`
  2. Get the MaterialUnit
  3. Get all products for the unit's material
  4. Sum `product.current_inventory` across all products
  5. Divide by `unit.quantity_per_unit`
  6. Return `floor()` of result (complete units only)
- **Example**:
  ```python
  # Material has 1200 inches total inventory
  # MaterialUnit is "6-inch ribbon" (quantity_per_unit = 6)
  # Available = floor(1200 / 6) = 200 units
  ```

### Subtask T026 - Implement get_current_cost()
- **Purpose**: Calculate cost for one MaterialUnit
- **File**: `src/services/material_unit_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `get_current_cost(unit_id, session=None)`
  2. Get the MaterialUnit
  3. Get all products for the unit's material
  4. Calculate weighted average cost across products (weighted by current_inventory)
  5. Multiply by `unit.quantity_per_unit`
  6. Return Decimal result
- **Example**:
  ```python
  # Product A: 800 inches at $0.10/inch
  # Product B: 400 inches at $0.14/inch
  # Weighted avg = (800*0.10 + 400*0.14) / 1200 = $0.1133/inch
  # Unit is 6 inches: cost = 6 * 0.1133 = $0.68
  ```

### Subtask T027 - Implement preview_consumption()
- **Purpose**: Preview what products would be consumed for a given quantity
- **File**: `src/services/material_unit_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `preview_consumption(unit_id, quantity_needed, session=None)`
  2. Calculate total base units needed: `quantity_needed * unit.quantity_per_unit`
  3. Get all products with inventory for the material
  4. Allocate proportionally across products based on current_inventory
  5. Return dict with:
     - can_fulfill: bool
     - quantity_needed: int
     - available: int
     - shortage: int (0 if can_fulfill)
     - allocations: list of {product_id, product_name, base_units_consumed, unit_cost, total_cost}
     - total_cost: Decimal
- **Notes**: This is read-only; does not modify inventory

### Subtask T028 - Service Tests
- **Purpose**: Achieve >70% coverage
- **File**: `src/tests/test_material_unit_service.py`
- **Parallel?**: Yes
- **Steps**:
  1. Create fixtures for material with multiple products
  2. Test create_unit with valid data
  3. Test get_available_inventory calculation
  4. Test get_current_cost calculation
  5. Test preview_consumption with sufficient inventory
  6. Test preview_consumption with insufficient inventory
  7. Test edge cases: no products, zero inventory

### Subtask T029 - Export Service
- **Purpose**: Make service available
- **File**: `src/services/__init__.py`
- **Parallel?**: No
- **Steps**:
  1. Add import for material_unit_service
  2. Add to `__all__`

## Test Strategy

```python
import pytest
from decimal import Decimal
from src.services.material_unit_service import (
    create_unit, get_available_inventory, get_current_cost, preview_consumption
)

@pytest.fixture
def material_with_products(db_session):
    """Material with two products totaling 1200 inches."""
    # Create hierarchy, then products with inventory
    # Product A: 800 inches at $0.10/inch
    # Product B: 400 inches at $0.14/inch
    ...

def test_available_inventory(db_session, material_with_products):
    """Available inventory aggregates across products."""
    unit = create_unit(
        material_id=material_with_products.id,
        name="6-inch ribbon",
        quantity_per_unit=6,
        session=db_session
    )

    available = get_available_inventory(unit.id, session=db_session)
    assert available == 200  # floor(1200 / 6)

def test_current_cost_weighted(db_session, material_with_products):
    """Cost is weighted average times quantity_per_unit."""
    unit = create_unit(
        material_id=material_with_products.id,
        name="6-inch ribbon",
        quantity_per_unit=6,
        session=db_session
    )

    cost = get_current_cost(unit.id, session=db_session)
    # Weighted avg = (800*0.10 + 400*0.14) / 1200 = 0.1133
    # Cost = 6 * 0.1133 = 0.68
    assert cost == Decimal("0.68")

def test_preview_consumption_sufficient(db_session, material_with_products, sample_unit):
    """Preview shows allocation when inventory sufficient."""
    preview = preview_consumption(sample_unit.id, quantity_needed=50, session=db_session)

    assert preview['can_fulfill'] is True
    assert preview['shortage'] == 0
    assert len(preview['allocations']) == 2  # Both products used
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| No products for material | Return 0 inventory, 0 cost |
| All products have 0 inventory | Return 0 inventory, handle division by zero |
| Rounding errors | Use floor() for available inventory; Decimal for costs |
| preview_consumption allocation | Use proportional allocation, handle remainders |

## Definition of Done Checklist

- [ ] MaterialUnit CRUD operations complete
- [ ] get_available_inventory aggregates correctly
- [ ] get_current_cost uses weighted average
- [ ] preview_consumption shows allocation plan
- [ ] Edge cases handled (no products, zero inventory)
- [ ] Tests achieve >70% coverage
- [ ] Service exported in `__init__.py`

## Review Guidance

**Reviewer should verify:**
1. Available inventory uses floor() not round()
2. Cost calculation uses inventory-weighted average
3. preview_consumption does NOT modify inventory
4. Delete validation checks Composition usage

## Activity Log

- 2026-01-10T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-10T20:50:00Z – claude – lane=doing – Starting material unit service implementation
- 2026-01-10T20:55:58Z – claude – lane=for_review – All 34 tests passing. CRUD, availability calc with floor(), weighted cost calc, preview_consumption complete
- 2026-01-11T01:06:31Z – claude – lane=done – Review passed: MaterialUnit CRUD, availability with floor(), weighted cost calculation. 34 tests passing.
