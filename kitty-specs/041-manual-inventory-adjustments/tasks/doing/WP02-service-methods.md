---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Service Methods Implementation"
phase: "Phase 1 - Service Layer (Claude)"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: ""
history:
  - timestamp: "2026-01-07T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Service Methods Implementation

## Objectives & Success Criteria

- Implement `manual_adjustment()` function per contract specification
- Implement `get_depletion_history()` function for retrieving depletion records
- All validation rules enforced (quantity > 0, <= current, notes for OTHER)
- Cost calculated correctly (quantity * unit_cost)
- Session parameter support per CLAUDE.md pattern

**Success**: Service methods can be called and return correct results; validation errors raised for invalid input.

## Context & Constraints

**Reference Documents**:
- Contract: `kitty-specs/041-manual-inventory-adjustments/contracts/inventory_adjustment_service.py`
- CLAUDE.md: Session Management section (CRITICAL pattern to follow)
- Constitution: `.kittify/memory/constitution.md` (Principle II: Data Integrity)
- Existing service: `src/services/inventory_item_service.py`

**Constraints**:
- Use `session=None` pattern for transaction composability
- Hardcode `created_by` as `"desktop-user"`
- InventoryDepletion records are immutable after creation
- Cost must be calculated at depletion time using item's unit_cost

**Dependencies**:
- WP01 must be complete (DepletionReason enum and InventoryDepletion model)

## Subtasks & Detailed Guidance

### Subtask T005 - Implement manual_adjustment()

**Purpose**: Core function for recording manual inventory depletions.

**Steps**:
1. Open `src/services/inventory_item_service.py`
2. Add imports at top:
```python
from ..models.inventory_depletion import InventoryDepletion
from ..models.enums import DepletionReason
```
3. Implement function per contract:

```python
def manual_adjustment(
    inventory_item_id: int,
    quantity_to_deplete: Decimal,
    reason: DepletionReason,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> InventoryDepletion:
    """
    Manually adjust inventory by recording a depletion.

    Creates an immutable InventoryDepletion audit record and updates
    the InventoryItem quantity atomically.

    Args:
        inventory_item_id: ID of the InventoryItem to adjust
        quantity_to_deplete: Amount to reduce (must be positive, <= current quantity)
        reason: DepletionReason enum value
        notes: Optional explanation (REQUIRED when reason is OTHER)
        session: Optional SQLAlchemy session for transaction composability

    Returns:
        InventoryDepletion: The created depletion record

    Raises:
        InventoryItemNotFound: If inventory_item_id doesn't exist
        ValidationError: If quantity/notes validation fails
    """
    def _do_adjustment(sess: Session) -> InventoryDepletion:
        # Implementation here (see T006, T007)
        pass

    # Session pattern per CLAUDE.md
    if session is not None:
        return _do_adjustment(session)
    else:
        with session_scope() as sess:
            return _do_adjustment(sess)
```

**Files**: `src/services/inventory_item_service.py`
**Parallel?**: No - foundation for T006, T007

### Subtask T006 - Implement validation logic

**Purpose**: Enforce business rules before allowing depletion.

**Steps**:
Inside `_do_adjustment()`:

```python
def _do_adjustment(sess: Session) -> InventoryDepletion:
    # Validate quantity is positive
    if quantity_to_deplete <= Decimal("0"):
        raise ServiceValidationError(["Quantity to deplete must be positive"])

    # Validate notes for OTHER reason
    if reason == DepletionReason.OTHER and not notes:
        raise ServiceValidationError(["Notes are required when reason is OTHER"])

    # Get inventory item
    item = (
        sess.query(InventoryItem)
        .options(joinedload(InventoryItem.product))
        .filter_by(id=inventory_item_id)
        .first()
    )
    if not item:
        raise InventoryItemNotFound(inventory_item_id)

    # Validate quantity doesn't exceed available
    current_qty = Decimal(str(item.quantity))
    if quantity_to_deplete > current_qty:
        raise ServiceValidationError([
            f"Cannot deplete {quantity_to_deplete}: only {current_qty} available"
        ])

    # Continue to T007 (cost calculation and record creation)
```

**Files**: `src/services/inventory_item_service.py`
**Parallel?**: No - builds on T005

### Subtask T007 - Implement cost calculation

**Purpose**: Calculate and record the cost impact of the depletion.

**Steps**:
Continue inside `_do_adjustment()`:

```python
    # Calculate cost (quantity * unit_cost)
    unit_cost = Decimal(str(item.unit_cost)) if item.unit_cost else Decimal("0")
    cost = quantity_to_deplete * unit_cost

    # Create depletion record
    depletion = InventoryDepletion(
        inventory_item_id=inventory_item_id,
        quantity_depleted=quantity_to_deplete,
        depletion_reason=reason.value,
        depletion_date=datetime.now(),
        notes=notes,
        cost=cost,
        created_by="desktop-user",
    )
    sess.add(depletion)

    # Update inventory item quantity
    item.quantity = float(current_qty - quantity_to_deplete)

    sess.flush()
    return depletion
```

**Files**: `src/services/inventory_item_service.py`
**Parallel?**: No - builds on T006

### Subtask T008 - Implement get_depletion_history()

**Purpose**: Retrieve depletion history for an inventory item.

**Steps**:
```python
def get_depletion_history(
    inventory_item_id: int,
    session: Optional[Session] = None,
) -> List[InventoryDepletion]:
    """
    Get depletion history for an inventory item.

    Args:
        inventory_item_id: ID of the InventoryItem
        session: Optional SQLAlchemy session

    Returns:
        List[InventoryDepletion]: Depletion records ordered by depletion_date DESC
    """
    def _do_query(sess: Session) -> List[InventoryDepletion]:
        return (
            sess.query(InventoryDepletion)
            .filter(InventoryDepletion.inventory_item_id == inventory_item_id)
            .order_by(InventoryDepletion.depletion_date.desc())
            .all()
        )

    if session is not None:
        return _do_query(session)
    else:
        with session_scope() as sess:
            return _do_query(sess)
```

**Files**: `src/services/inventory_item_service.py`
**Parallel?**: No - follows T007

### Subtask T009 - Add session parameter support

**Purpose**: Ensure both functions follow CLAUDE.md session management pattern.

**Steps**:
1. Review both functions follow the pattern:
   - Accept `session: Optional[Session] = None`
   - If session provided, use it directly (caller owns transaction)
   - If session is None, create session_scope() (function owns transaction)
2. Verify imports include:
```python
from typing import List, Optional
from sqlalchemy.orm import Session
```

**Files**: `src/services/inventory_item_service.py`
**Parallel?**: No - verification of T005-T008

## Test Strategy

Manual verification at this stage (formal tests in WP03):
```python
# Quick verification
from decimal import Decimal
from src.models.enums import DepletionReason
from src.services.inventory_item_service import manual_adjustment

# Should work with valid data
depletion = manual_adjustment(
    inventory_item_id=1,  # Must exist
    quantity_to_deplete=Decimal("1.0"),
    reason=DepletionReason.SPOILAGE,
    notes="Test"
)
print(f"Created depletion: {depletion.id}")
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Session detachment anti-pattern | Silent data loss | Follow CLAUDE.md pattern exactly |
| Floating point precision in cost | Inaccurate costs | Use Decimal throughout |
| Race condition on quantity check | Negative inventory | Single-user desktop; not a concern |

## Definition of Done Checklist

- [ ] `manual_adjustment()` implemented per contract
- [ ] Validation: quantity > 0 enforced
- [ ] Validation: quantity <= current quantity enforced
- [ ] Validation: notes required for OTHER reason
- [ ] Cost calculated as quantity * unit_cost
- [ ] InventoryDepletion record created with all fields
- [ ] InventoryItem.quantity updated atomically
- [ ] `get_depletion_history()` returns records DESC by date
- [ ] Both functions accept session parameter

## Review Guidance

- Verify session pattern matches CLAUDE.md exactly
- Check all validation error messages are user-friendly
- Verify cost calculation uses Decimal, not float
- Check created_by is "desktop-user"

## Activity Log

- 2026-01-07T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-07T16:54:05Z – claude – shell_pid= – lane=doing – Moved to doing
