---
work_package_id: "WP06"
subtasks:
  - "T038"
  - "T039"
  - "T040"
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
title: "Assembly Consumption - User Story 6"
phase: "Phase 2 - Integration"
lane: "doing"
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

# Work Package Prompt: WP06 - Assembly Consumption - User Story 6

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Implement material consumption during assembly with inventory decrements and historical snapshots.

**User Story**: As a baker, I need to record which specific materials I used during assembly so I have accurate cost records and inventory decrements.

**Success Criteria:**
- Generic material placeholders resolved via inline dropdown
- Material consumption creates snapshot records
- Inventory decrements atomically with consumption
- Assembly blocked when inventory insufficient (no bypass)
- Historical queries return snapshot data, not current catalog

## Context & Constraints

**Reference Documents:**
- `kitty-specs/047-materials-management-system/spec.md` - User Story 6
- `kitty-specs/047-materials-management-system/contracts/material_consumption_service.md` - Service interface
- `src/services/assembly_service.py` - Existing service to integrate with
- `src/models/production_consumption.py` - Pattern for consumption snapshots

**Clarifications (from spec):**
- "Block the save entirely until inventory is corrected. No 'Record Anyway' bypass option."
- "Inline during assembly - each pending material shows a dropdown next to the quantity field."
- "Full snapshot (product_name, material_name, category_name, quantity, unit_cost, supplier_name)"

**Dependencies:**
- WP05 (Composition must support materials)
- WP04 (MaterialUnit service for calculations)

## Subtasks & Detailed Guidance

### Subtask T038 - Create MaterialConsumptionService
- **Purpose**: Core service for material consumption operations
- **File**: `src/services/material_consumption_service.py`
- **Parallel?**: No
- **Steps**:
  1. Create file with standard imports
  2. Import MaterialConsumption model
  3. Import material_unit_service for calculations
  4. Set up session parameter pattern per CLAUDE.md

### Subtask T039 - Implement get_pending_materials()
- **Purpose**: Find materials requiring resolution for a FinishedGood
- **File**: `src/services/material_consumption_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `get_pending_materials(finished_good_id, session=None)`
  2. Query Composition entries where `material_id IS NOT NULL` (generic placeholders)
  3. For each, get the Material and its available products
  4. Return list of dicts:
     ```python
     {
         'composition_id': int,
         'material_id': int,
         'material_name': str,
         'quantity_needed': float,  # component_quantity * assembly_quantity
         'available_products': [
             {'product_id': int, 'name': str, 'available_units': int, 'unit_cost': Decimal},
             ...
         ]
     }
     ```

### Subtask T040 - Implement validate_material_availability()
- **Purpose**: Check that all materials have sufficient inventory
- **File**: `src/services/material_consumption_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `validate_material_availability(finished_good_id, assembly_quantity, material_assignments=None, session=None)`
  2. Get all Composition entries with material components
  3. For MaterialUnit components: check available inventory >= needed
  4. For Material (generic) components: validate assignments provided and sufficient
  5. Return:
     ```python
     {
         'valid': bool,
         'errors': ['Material X has insufficient inventory (need 50, have 30)', ...],
         'material_requirements': [
             {
                 'composition_id': int,
                 'is_generic': bool,
                 'material_name': str,
                 'base_units_needed': float,
                 'available': float,
                 'sufficient': bool,
                 'assignments': [...]  # Only for generic
             },
             ...
         ]
     }
     ```

### Subtask T041 - Implement record_material_consumption()
- **Purpose**: Create consumption records with full snapshots
- **File**: `src/services/material_consumption_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `record_material_consumption(assembly_run_id, finished_good_id, assembly_quantity, material_assignments=None, session=None)`
  2. First validate availability (raise if insufficient)
  3. For each material component:
     - Get products to consume (specific or from assignments)
     - Create MaterialConsumption record with snapshot fields:
       - product_name, material_name, subcategory_name, category_name, supplier_name
     - Decrement product.current_inventory
  4. Return list of created MaterialConsumption records
- **Critical**: All operations must be atomic (same transaction)

### Subtask T042 - Integrate with assembly_service.py
- **Purpose**: Hook material consumption into assembly workflow
- **File**: `src/services/assembly_service.py`
- **Parallel?**: No
- **Steps**:
  1. Find `record_assembly()` function
  2. After food/unit consumption, call `record_material_consumption()`
  3. Pass material_assignments from UI if provided
  4. Ensure assembly fails if material consumption fails

### Subtask T043 - Implement Inventory Decrement Logic
- **Purpose**: Decrease product inventory when materials consumed
- **File**: `src/services/material_consumption_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `_decrement_inventory(product, base_units_consumed, session)`
  2. Validate `product.current_inventory >= base_units_consumed`
  3. Update `product.current_inventory -= base_units_consumed`
  4. Ensure change persists (same session)
- **Notes**: Called from record_material_consumption(), not exposed directly

### Subtask T044 - Block Assembly When Inventory Insufficient
- **Purpose**: Enforce strict inventory validation per clarifications
- **File**: `src/services/material_consumption_service.py`
- **Parallel?**: No
- **Steps**:
  1. In `record_material_consumption()`:
     - Call `validate_material_availability()` first
     - If `valid == False`, raise `ValidationError` with error messages
     - Do NOT provide bypass option
  2. Ensure clear error message: "Cannot record assembly: Material X has insufficient inventory (need 50, have 30)"

### Subtask T045 - Service Tests
- **Purpose**: Achieve >70% coverage
- **File**: `src/tests/test_material_consumption_service.py`
- **Parallel?**: Yes
- **Steps**:
  1. Test get_pending_materials returns generic materials
  2. Test validate_material_availability passes with sufficient inventory
  3. Test validate_material_availability fails with insufficient inventory
  4. Test record_material_consumption creates snapshots
  5. Test inventory decrements correctly
  6. Test assembly blocked when insufficient inventory
  7. Test generic material assignments work

### Subtask T046 - Export Service
- **Purpose**: Make service available
- **File**: `src/services/__init__.py`
- **Parallel?**: No
- **Steps**:
  1. Add import for material_consumption_service
  2. Add to `__all__`

## Test Strategy

```python
import pytest
from src.services.material_consumption_service import (
    get_pending_materials, validate_material_availability,
    record_material_consumption
)

def test_get_pending_materials(db_session, fg_with_generic_material):
    """Returns list of materials needing resolution."""
    pending = get_pending_materials(fg_with_generic_material.id, session=db_session)

    assert len(pending) == 1
    assert pending[0]['material_name'] == "Cellophane Bag"
    assert len(pending[0]['available_products']) > 0

def test_validate_insufficient_inventory(db_session, fg_with_materials, low_inventory):
    """Validation fails when inventory insufficient."""
    result = validate_material_availability(
        fg_with_materials.id,
        assembly_quantity=100,  # More than available
        session=db_session
    )

    assert result['valid'] is False
    assert 'insufficient inventory' in result['errors'][0].lower()

def test_record_consumption_creates_snapshot(db_session, assembly_run, fg_with_material_unit):
    """Consumption record includes snapshot fields."""
    consumptions = record_material_consumption(
        assembly_run_id=assembly_run.id,
        finished_good_id=fg_with_material_unit.id,
        assembly_quantity=10,
        session=db_session
    )

    assert len(consumptions) == 1
    assert consumptions[0].product_name is not None
    assert consumptions[0].material_name is not None
    assert consumptions[0].category_name is not None

def test_inventory_decrements(db_session, assembly_run, fg_with_material_unit, sample_product):
    """Inventory decreases after consumption."""
    original_inventory = sample_product.current_inventory

    record_material_consumption(
        assembly_run_id=assembly_run.id,
        finished_good_id=fg_with_material_unit.id,
        assembly_quantity=10,
        session=db_session
    )

    db_session.refresh(sample_product)
    assert sample_product.current_inventory < original_inventory

def test_assembly_blocked_insufficient_inventory(db_session, assembly_run, fg_with_materials):
    """Assembly raises error when inventory insufficient."""
    with pytest.raises(ValidationError) as exc_info:
        record_material_consumption(
            assembly_run_id=assembly_run.id,
            finished_good_id=fg_with_materials.id,
            assembly_quantity=9999,  # Way more than available
            session=db_session
        )

    assert 'insufficient inventory' in str(exc_info.value).lower()
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Partial consumption failure | Use single transaction; rollback on any error |
| Snapshot data integrity | Capture all names at consumption time, not lazy load |
| Concurrent assembly | Database transaction isolation handles conflicts |
| Generic resolution complexity | Clear validation before consumption |

## Definition of Done Checklist

- [ ] get_pending_materials returns materials needing resolution
- [ ] validate_material_availability checks all material components
- [ ] record_material_consumption creates snapshot records
- [ ] Inventory decrements atomically
- [ ] Assembly blocked when inventory insufficient (no bypass)
- [ ] Integration with assembly_service.py complete
- [ ] Tests achieve >70% coverage
- [ ] Service exported in `__init__.py`

## Review Guidance

**Reviewer should verify:**
1. Snapshot fields capture ALL names (product, material, subcategory, category, supplier)
2. No bypass option exists for insufficient inventory
3. Transaction atomicity - all or nothing
4. Generic material assignments validated correctly

## Activity Log

- 2026-01-10T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-10T22:03:05Z – claude – lane=doing – Starting assembly consumption implementation
