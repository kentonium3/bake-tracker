---
work_package_id: "WP02"
subtasks:
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Inventory-Purchase Service Integration"
phase: "Phase 1 - Service Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-22T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Inventory-Purchase Service Integration

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Update `inventory_item_service.add_to_inventory()` to atomically create Purchase records alongside InventoryItem records, establishing the core linkage required by F028.

**Success Criteria**:
- `add_to_inventory()` accepts new required parameters: `supplier_id` and `unit_price`
- Every inventory addition creates a corresponding Purchase record
- `InventoryItem.purchase_id` is set to link the records
- `InventoryItem.unit_cost` is populated from `unit_price` for FIFO calculations
- Operation is atomic (both records created or neither)
- Unit tests verify the integration

**User Story**: US1 (Add Inventory with Supplier Selection) - Foundation
**Functional Requirements**: FR-001, FR-013, FR-014, FR-015

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/028-purchase-tracking-enhanced/spec.md` - FR-001, FR-013, FR-015
- `kitty-specs/028-purchase-tracking-enhanced/plan.md` - Section 1.2
- `kitty-specs/028-purchase-tracking-enhanced/data-model.md` - InventoryItem, Purchase entities
- `CLAUDE.md` - Session management critical section

**Existing Infrastructure**:
- `src/services/inventory_item_service.py` - Has `add_to_inventory()` function
- `src/models/inventory_item.py` - Has `purchase_id` FK (nullable), `unit_cost` field
- `src/models/purchase.py` - Full Purchase model ready for use

**Constraints**:
- Must maintain single session for atomicity (CRITICAL per CLAUDE.md)
- `purchase_date` defaults to today when not provided (FR-013)
- Notes stored on InventoryItem, not Purchase (FR-014)
- 1:1 relationship between Purchase and InventoryItem (FR-015)

---

## Subtasks & Detailed Guidance

### Subtask T004 - Update `add_to_inventory()` Signature

**Purpose**: Add required parameters for Purchase creation.

**Steps**:
1. Open `src/services/inventory_item_service.py`
2. Locate `add_to_inventory()` function
3. Add new required parameters: `supplier_id: int`, `unit_price: Decimal`
4. Add optional parameter: `purchase_date: Optional[date] = None`
5. Update docstring with new parameters

**New Signature**:
```python
from decimal import Decimal
from datetime import date
from typing import Optional, Dict, Any

def add_to_inventory(
    product_id: int,
    quantity: float,
    supplier_id: int,              # NEW - required
    unit_price: Decimal,           # NEW - required
    added_date: Optional[date] = None,
    expiration_date: Optional[date] = None,
    purchase_date: Optional[date] = None,  # NEW - optional, defaults to today
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Add inventory item with linked Purchase record.

    Creates an atomic transaction:
    1. Creates Purchase record with product, supplier, price, date
    2. Creates InventoryItem with purchase_id linkage
    3. Sets InventoryItem.unit_cost for FIFO calculations

    Args:
        product_id: Product ID
        quantity: Quantity to add
        supplier_id: Supplier ID where purchased (required)
        unit_price: Price per unit (required)
        added_date: Date added to inventory (defaults to today)
        expiration_date: Optional expiration date
        purchase_date: Date of purchase (defaults to today)
        notes: Optional notes (stored on InventoryItem)
        session: Optional database session

    Returns:
        Dict containing created InventoryItem data

    Raises:
        ValueError: If supplier_id or product_id invalid
    """
```

**Files**: `src/services/inventory_item_service.py`
**Parallel?**: No - must complete before T005

---

### Subtask T005 - Implement Atomic Purchase Creation

**Purpose**: Create Purchase record within the same transaction as InventoryItem.

**Steps**:
1. Inside `_add_to_inventory_impl()` (or equivalent), create Purchase first
2. Use the same session for both operations
3. Set `purchase_date = purchase_date or date.today()`
4. Create Purchase with: product_id, supplier_id, purchase_date, unit_price, quantity_purchased=quantity
5. Flush to get Purchase.id
6. Create InventoryItem with `purchase_id=purchase.id`

**Implementation Pattern**:
```python
from src.models import Purchase, InventoryItem
from datetime import date

def _add_to_inventory_impl(
    product_id: int,
    quantity: float,
    supplier_id: int,
    unit_price: Decimal,
    added_date: Optional[date],
    expiration_date: Optional[date],
    purchase_date: Optional[date],
    notes: Optional[str],
    session: Session
) -> Dict[str, Any]:
    # Default dates
    actual_purchase_date = purchase_date or date.today()
    actual_added_date = added_date or date.today()

    # Validate supplier exists
    supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise ValueError(f"Supplier with id {supplier_id} not found")

    # Validate product exists
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Product with id {product_id} not found")

    # Create Purchase record FIRST (same session)
    purchase = Purchase(
        product_id=product_id,
        supplier_id=supplier_id,
        purchase_date=actual_purchase_date,
        unit_price=unit_price,
        quantity_purchased=int(quantity),  # Purchase tracks package units
        notes=None,  # Notes stored on InventoryItem per FR-014
    )
    session.add(purchase)
    session.flush()  # Get purchase.id

    # Create InventoryItem with purchase linkage
    inventory_item = InventoryItem(
        product_id=product_id,
        quantity=quantity,
        unit_cost=float(unit_price),  # For FIFO calculations
        purchase_id=purchase.id,      # Link to Purchase
        added_date=actual_added_date,
        expiration_date=expiration_date,
        notes=notes,                  # User notes here
    )
    session.add(inventory_item)
    session.flush()

    return inventory_item.to_dict()
```

**Critical**: Must use single session - do NOT create nested `session_scope()` calls!

**Files**: `src/services/inventory_item_service.py`
**Parallel?**: No - sequential after T004

---

### Subtask T006 - Set InventoryItem.unit_cost from Purchase

**Purpose**: Ensure FIFO calculations work by populating unit_cost field.

**Steps**:
1. In T005 implementation, set `unit_cost=float(unit_price)`
2. Verify `InventoryItem.unit_cost` field exists and accepts float
3. This enables existing FIFO logic to work without modification

**Verification**:
- Check `src/services/inventory_item_service.py` - `consume_fifo()` uses `item.unit_cost`
- The existing FIFO logic should work unchanged once unit_cost is populated

**Files**: `src/services/inventory_item_service.py` (part of T005)
**Parallel?**: No - part of T005

---

### Subtask T007 - Write/Update Tests for `add_to_inventory()`

**Purpose**: Verify the integration works correctly.

**Test Cases** (in `src/tests/services/test_inventory_item_service.py`):

```python
class TestAddToInventoryWithPurchase:
    """Test suite for F028 inventory-purchase integration."""

    def test_add_to_inventory_creates_purchase(self, session, test_product, test_supplier):
        """Adding inventory creates linked Purchase record."""
        result = add_to_inventory(
            product_id=test_product.id,
            quantity=10.0,
            supplier_id=test_supplier.id,
            unit_price=Decimal("8.99"),
            session=session
        )

        # Verify InventoryItem created
        assert result is not None
        item_id = result["id"]

        # Verify Purchase created
        item = session.query(InventoryItem).get(item_id)
        assert item.purchase_id is not None

        purchase = session.query(Purchase).get(item.purchase_id)
        assert purchase is not None
        assert purchase.product_id == test_product.id
        assert purchase.supplier_id == test_supplier.id
        assert purchase.unit_price == Decimal("8.99")

    def test_add_to_inventory_sets_unit_cost(self, session, test_product, test_supplier):
        """InventoryItem.unit_cost is set from unit_price."""
        result = add_to_inventory(
            product_id=test_product.id,
            quantity=5.0,
            supplier_id=test_supplier.id,
            unit_price=Decimal("12.50"),
            session=session
        )

        item = session.query(InventoryItem).get(result["id"])
        assert item.unit_cost == 12.50

    def test_add_to_inventory_defaults_purchase_date_to_today(self, session, test_product, test_supplier):
        """Purchase date defaults to today when not provided."""
        result = add_to_inventory(
            product_id=test_product.id,
            quantity=1.0,
            supplier_id=test_supplier.id,
            unit_price=Decimal("5.00"),
            session=session
        )

        item = session.query(InventoryItem).get(result["id"])
        purchase = session.query(Purchase).get(item.purchase_id)
        assert purchase.purchase_date == date.today()

    def test_add_to_inventory_invalid_supplier_raises(self, session, test_product):
        """Invalid supplier_id raises ValueError."""
        with pytest.raises(ValueError, match="Supplier"):
            add_to_inventory(
                product_id=test_product.id,
                quantity=1.0,
                supplier_id=99999,  # Non-existent
                unit_price=Decimal("5.00"),
                session=session
            )

    def test_add_to_inventory_invalid_product_raises(self, session, test_supplier):
        """Invalid product_id raises ValueError."""
        with pytest.raises(ValueError, match="Product"):
            add_to_inventory(
                product_id=99999,  # Non-existent
                quantity=1.0,
                supplier_id=test_supplier.id,
                unit_price=Decimal("5.00"),
                session=session
            )

    def test_add_to_inventory_stores_notes_on_item(self, session, test_product, test_supplier):
        """Notes are stored on InventoryItem, not Purchase."""
        result = add_to_inventory(
            product_id=test_product.id,
            quantity=1.0,
            supplier_id=test_supplier.id,
            unit_price=Decimal("5.00"),
            notes="Test note",
            session=session
        )

        item = session.query(InventoryItem).get(result["id"])
        purchase = session.query(Purchase).get(item.purchase_id)

        assert item.notes == "Test note"
        assert purchase.notes is None  # FR-014
```

**Files**: `src/tests/services/test_inventory_item_service.py`
**Parallel?**: Yes - can be written alongside implementation

---

## Test Strategy

**Required Coverage**: >70% on modified functions

**Run Tests**:
```bash
pytest src/tests/services/test_inventory_item_service.py -v --cov=src/services/inventory_item_service
```

**Fixtures Needed**:
- `test_product`: Product fixture
- `test_supplier`: Supplier fixture
- Database session fixture

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing callers break | UI will be updated in WP03 |
| Session detachment | Use single session, no nested session_scope() |
| Decimal/float conversion | Use float() for unit_cost, str() for return dicts |
| Transaction rollback | Atomic within single session |

---

## Definition of Done Checklist

- [ ] `add_to_inventory()` signature updated with new params
- [ ] Purchase record created atomically
- [ ] InventoryItem.purchase_id set correctly
- [ ] InventoryItem.unit_cost populated from unit_price
- [ ] purchase_date defaults to today
- [ ] Notes stored on InventoryItem, not Purchase
- [ ] Unit tests written and passing
- [ ] No regressions in existing tests

---

## Review Guidance

**Verification Checkpoints**:
1. Single session used for both Purchase and InventoryItem creation
2. No nested session_scope() calls (critical!)
3. Validation for supplier_id and product_id
4. unit_cost set correctly for FIFO
5. Tests cover happy path + error cases

---

## Activity Log

- 2025-12-22T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks.
