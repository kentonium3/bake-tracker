---
work_package_id: "WP03"
subtasks:
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
title: "Supplier Service"
phase: "Phase 2 - Service Layer"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "50566"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-22T14:35:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Supplier Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Implement supplier_service.py with full CRUD and soft delete operations.

**Success Criteria**:
- [ ] All supplier service functions work correctly
- [ ] Session pattern followed per CLAUDE.md
- [ ] Deactivate cascade clears product preferred_supplier_id (FR-009)
- [ ] Delete checks for purchase history dependencies
- [ ] Test coverage >70%

## Context & Constraints

**Reference Documents**:
- Session Management: `CLAUDE.md` (CRITICAL - read before coding)
- Spec requirements: FR-007 through FR-010
- Existing services: `src/services/ingredient_service.py` for pattern reference

**Critical Pattern** (from CLAUDE.md):
```python
def some_function(..., session: Optional[Session] = None):
    if session is not None:
        return _some_function_impl(..., session)
    with session_scope() as session:
        return _some_function_impl(..., session)
```

## Subtasks & Detailed Guidance

### T016 – Create supplier_service.py with session pattern

**Purpose**: Establish service file with correct session handling.

**Steps**:
1. Create `src/services/supplier_service.py`
2. Add imports:
```python
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from src.models import Supplier, Product
from src.services.database import session_scope
from src.services.exceptions import SupplierNotFoundError
```
3. Add module docstring explaining the service

**Files**: `src/services/supplier_service.py` (NEW)

### T017 – Implement create_supplier

**Purpose**: Create new supplier with validation.

**Steps**:
```python
def create_supplier(
    name: str,
    city: str,
    state: str,
    zip_code: str,
    street_address: Optional[str] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict[str, Any]:
    """Create a new supplier."""
    if session is not None:
        return _create_supplier_impl(name, city, state, zip_code, street_address, notes, session)
    with session_scope() as session:
        return _create_supplier_impl(name, city, state, zip_code, street_address, notes, session)

def _create_supplier_impl(..., session: Session) -> Dict[str, Any]:
    # Validate state (uppercase, 2 chars)
    state = state.upper()
    if len(state) != 2:
        raise ValueError("State must be a 2-letter code")

    supplier = Supplier(
        name=name,
        city=city,
        state=state,
        zip_code=zip_code,
        street_address=street_address,
        notes=notes
    )
    session.add(supplier)
    session.flush()
    return supplier.to_dict()
```

**Notes**:
- Validate state format in service layer (SQLite CHECK may not enforce on insert)
- Return dict, not ORM object (prevents detachment issues)

### T018 – Implement get_supplier and get_supplier_by_uuid

**Purpose**: Retrieve single supplier by ID or UUID.

**Steps**:
```python
def get_supplier(supplier_id: int, session: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Get supplier by ID. Returns None if not found."""
    ...

def get_supplier_by_uuid(uuid: str, session: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Get supplier by UUID. Returns None if not found."""
    ...
```

**Notes**:
- Return None for not found (let caller decide to raise)
- Return dict via to_dict()

### T019 – Implement get_all_suppliers

**Purpose**: Retrieve all suppliers with optional inactive filter.

**Steps**:
```python
def get_all_suppliers(
    include_inactive: bool = False,
    session: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """Get all suppliers, optionally including inactive."""
    ...
    query = session.query(Supplier)
    if not include_inactive:
        query = query.filter(Supplier.is_active == True)
    return [s.to_dict() for s in query.order_by(Supplier.name).all()]
```

### T020 – Implement get_active_suppliers

**Purpose**: Convenience method for dropdown population (FR-010).

**Steps**:
```python
def get_active_suppliers(session: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Get active suppliers for dropdowns."""
    return get_all_suppliers(include_inactive=False, session=session)
```

### T021 – Implement update_supplier

**Purpose**: Update supplier attributes.

**Steps**:
```python
def update_supplier(
    supplier_id: int,
    session: Optional[Session] = None,
    **kwargs
) -> Dict[str, Any]:
    """Update supplier attributes. Raises SupplierNotFoundError if not found."""
    ...
    # Validate state if provided
    if "state" in kwargs:
        kwargs["state"] = kwargs["state"].upper()
        if len(kwargs["state"]) != 2:
            raise ValueError("State must be a 2-letter code")

    # Update allowed fields
    allowed_fields = {"name", "city", "state", "zip_code", "street_address", "notes"}
    for key, value in kwargs.items():
        if key in allowed_fields:
            setattr(supplier, key, value)
    session.flush()
    return supplier.to_dict()
```

### T022 – Implement deactivate_supplier with cascade

**Purpose**: Soft delete supplier and cascade to products (FR-009).

**Steps**:
```python
def deactivate_supplier(supplier_id: int, session: Optional[Session] = None) -> Dict[str, Any]:
    """Deactivate supplier and clear preferred_supplier_id on affected products."""
    ...
    supplier.is_active = False

    # FR-009: Clear preferred_supplier_id on products
    affected_products = session.query(Product).filter(
        Product.preferred_supplier_id == supplier_id
    ).all()
    for product in affected_products:
        product.preferred_supplier_id = None

    session.flush()
    return supplier.to_dict()
```

**Critical**: This implements FR-009 - must clear product references when deactivating.

### T023 – Implement reactivate_supplier

**Purpose**: Restore inactive supplier.

**Steps**:
```python
def reactivate_supplier(supplier_id: int, session: Optional[Session] = None) -> Dict[str, Any]:
    """Reactivate a previously deactivated supplier."""
    ...
    supplier.is_active = True
    session.flush()
    return supplier.to_dict()
```

### T024 – Implement delete_supplier with dependency check

**Purpose**: Hard delete supplier only if no purchases exist.

**Steps**:
```python
def delete_supplier(supplier_id: int, session: Optional[Session] = None) -> bool:
    """Delete supplier if no purchases exist. Returns True if deleted."""
    ...
    # Check for purchases
    from src.models import Purchase
    purchase_count = session.query(Purchase).filter(
        Purchase.supplier_id == supplier_id
    ).count()

    if purchase_count > 0:
        raise ValueError(f"Cannot delete supplier with {purchase_count} purchases. Deactivate instead.")

    session.delete(supplier)
    session.flush()
    return True
```

### T025 – Add SupplierNotFoundError

**Purpose**: Custom exception for missing suppliers.

**Steps**:
1. Open `src/services/exceptions.py`
2. Add:
```python
class SupplierNotFoundError(Exception):
    """Raised when a supplier is not found."""
    pass
```

**Files**: `src/services/exceptions.py` (MODIFY)

### T026 – Update services __init__.py

**Purpose**: Export supplier_service module.

**Steps**:
1. Add import: `from . import supplier_service`
2. Add to `__all__`: `"supplier_service"`

**Files**: `src/services/__init__.py` (MODIFY)

### T027 – Write supplier service tests

**Purpose**: Achieve >70% coverage on supplier_service.

**Steps**:
Create `src/tests/services/test_supplier_service.py`:
- `test_create_supplier_success`
- `test_create_supplier_validates_state`
- `test_get_supplier_by_id`
- `test_get_supplier_not_found`
- `test_get_all_suppliers_excludes_inactive`
- `test_get_all_suppliers_includes_inactive`
- `test_get_active_suppliers`
- `test_update_supplier`
- `test_deactivate_supplier_clears_product_references`
- `test_reactivate_supplier`
- `test_delete_supplier_success`
- `test_delete_supplier_with_purchases_fails`

**Files**: `src/tests/services/test_supplier_service.py` (NEW)

**Commands**:
```bash
pytest src/tests/services/test_supplier_service.py -v --cov=src.services.supplier_service
```

## Test Strategy

**Coverage Target**: >70% for supplier_service.py

**Key Test Scenarios**:
- Happy path CRUD
- State validation (lowercase, wrong length)
- Deactivate cascade (verify products updated)
- Delete blocked when purchases exist

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Always return dicts, not ORM objects |
| Cascade not applied | Test specifically verifies product.preferred_supplier_id cleared |
| Circular import | Import Purchase inside function if needed |

## Definition of Done Checklist

- [ ] All service functions implemented with session pattern
- [ ] State validation in create/update
- [ ] Deactivate cascade clears product.preferred_supplier_id
- [ ] Delete checks for purchases before allowing
- [ ] SupplierNotFoundError added to exceptions
- [ ] Service exported in __init__.py
- [ ] Tests pass with >70% coverage

## Review Guidance

**Key Checkpoints**:
1. Every function accepts `session: Optional[Session] = None`
2. Every function uses the if/else session pattern
3. Deactivate explicitly clears Product.preferred_supplier_id
4. Delete raises error if purchases exist
5. Run coverage report to verify >70%

## Activity Log

- 2025-12-22T14:35:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-22T20:50:47Z – claude – shell_pid=50566 – lane=doing – Started implementation
- 2025-12-22T20:56:04Z – claude – shell_pid=50566 – lane=for_review – Implementation complete: 29 supplier service tests pass (85.7% coverage), all functions follow session pattern per CLAUDE.md, FR-009 cascade implemented
