---
work_package_id: "WP04"
subtasks:
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
title: "Purchase Transaction Import"
phase: "Phase 3 - Wave 2"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "13882"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2026-01-12T16:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Purchase Transaction Import

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Create new `transaction_import_service.py` with purchase import functionality for BT Mobile workflow.

**Success Criteria**:
- SC-006: Purchase import increases inventory quantities correctly
- FR-015: System MUST support purchase transaction imports
- FR-016: System MUST validate purchases have positive quantities
- FR-017: System MUST update inventory and recalculate costs after purchase import
- FR-018: System MUST detect and skip duplicate purchases

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/049-import-export-phase1/spec.md` (User Story 4)
- Plan: `kitty-specs/049-import-export-phase1/plan.md`
- Import spec: `docs/design/spec_import_export.md` (Appendix I)
- Existing: `src/services/import_export_service.py` (for ImportResult)

**Purchase Import JSON Schema**:
```json
{
  "schema_version": "4.0",
  "import_type": "purchases",
  "created_at": "2026-01-12T14:30:00Z",
  "source": "bt_mobile",
  "supplier": "Costco Waltham MA",
  "purchases": [
    {
      "product_slug": "flour_all_purpose_king_arthur_5lb",
      "purchased_at": "2026-01-12T14:15:23Z",
      "unit_price": 7.99,
      "quantity_purchased": 2,
      "supplier": "Costco",
      "notes": "Weekly shopping"
    }
  ]
}
```

**Key Difference from Catalog Import**:
- Transaction imports are NOT idempotent
- Each import creates new records (not merge/update)
- Duplicate detection prevents double-import
- Side effects: creates InventoryItem, updates costs

---

## Subtasks & Detailed Guidance

### Subtask T029 - Create `transaction_import_service.py`

**Purpose**: New service file for transaction (non-catalog) imports.

**Steps**:
1. Create `src/services/transaction_import_service.py`
2. Add imports:
```python
"""
Transaction Import Service - Import purchases and adjustments from JSON.

Handles non-catalog imports that create transaction records and
modify inventory state. Unlike catalog imports, these are not idempotent.
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from src.services.database import session_scope
from src.services.import_export_service import ImportResult
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.inventory_item import InventoryItem
from src.models.supplier import Supplier
```
3. Create main function skeleton:
```python
def import_purchases(file_path: str, dry_run: bool = False) -> ImportResult:
    """
    Import purchase transactions from JSON file.

    Creates Purchase and InventoryItem records, updates costs.
    Detects and skips duplicate purchases.

    Args:
        file_path: Path to JSON file with purchases
        dry_run: If True, validate without committing

    Returns:
        ImportResult with counts and any errors
    """
    result = ImportResult()
    # Implementation...
    return result
```

**Files**: `src/services/transaction_import_service.py` (NEW)

### Subtask T030 - Validate positive quantities

**Purpose**: Reject purchases with zero or negative quantities.

**Steps**:
1. Add validation in import loop:
```python
for purchase_data in data.get("purchases", []):
    quantity = purchase_data.get("quantity_purchased", 0)

    if quantity <= 0:
        result.add_error(
            "purchases",
            purchase_data.get("product_slug", "unknown"),
            f"Invalid quantity {quantity}: purchases must have positive quantities",
            suggestion="Use inventory adjustments for negative quantities"
        )
        continue
```
2. Clear error message explaining positive-only rule

**Files**: `src/services/transaction_import_service.py`

### Subtask T031 - Resolve product_slug to Product record

**Purpose**: Find Product by slug, error if not found.

**Steps**:
1. Query product:
```python
product_slug = purchase_data.get("product_slug")
if not product_slug:
    result.add_error("purchases", "unknown", "Missing product_slug field")
    continue

product = session.query(Product).filter_by(slug=product_slug).first()
if not product:
    result.add_error(
        "purchases",
        product_slug,
        f"Product '{product_slug}' not found in database",
        suggestion="Ensure product exists in catalog before importing purchases"
    )
    continue
```
2. Consider batch lookup for performance with many purchases

**Files**: `src/services/transaction_import_service.py`

### Subtask T032 - Create Purchase record

**Purpose**: Create Purchase entity for each valid transaction.

**Steps**:
1. Resolve or create supplier:
```python
def resolve_supplier(name: str, session) -> Optional[Supplier]:
    """Find or create supplier by name."""
    if not name:
        return None
    supplier = session.query(Supplier).filter_by(name=name).first()
    if not supplier:
        supplier = Supplier(name=name)
        session.add(supplier)
        session.flush()
    return supplier
```
2. Create purchase:
```python
supplier = resolve_supplier(
    purchase_data.get("supplier") or data.get("supplier"),
    session
)

purchase = Purchase(
    product_id=product.id,
    supplier_id=supplier.id if supplier else None,
    purchase_date=parse_datetime(purchase_data.get("purchased_at")),
    quantity_purchased=Decimal(str(quantity)),
    unit_price=Decimal(str(purchase_data.get("unit_price", 0))),
    notes=purchase_data.get("notes")
)
session.add(purchase)
session.flush()  # Get purchase.id for InventoryItem
```

**Files**: `src/services/transaction_import_service.py`

### Subtask T033 - Create InventoryItem record

**Purpose**: Create inventory entry linked to purchase.

**Steps**:
1. Create InventoryItem:
```python
inventory_item = InventoryItem(
    product_id=product.id,
    purchase_id=purchase.id,
    current_quantity=purchase.quantity_purchased,
    purchase_date=purchase.purchase_date,
    unit_cost=purchase.unit_price
)
session.add(inventory_item)
```
2. This represents the physical inventory from the purchase

**Files**: `src/services/transaction_import_service.py`

### Subtask T034 - Recalculate weighted average costs

**Purpose**: Update product's average cost after purchase.

**Steps**:
1. Calculate new weighted average:
```python
def update_product_average_cost(product: Product, session):
    """Recalculate weighted average cost from inventory items."""
    items = session.query(InventoryItem).filter(
        InventoryItem.product_id == product.id,
        InventoryItem.current_quantity > 0
    ).all()

    total_value = sum(i.current_quantity * i.unit_cost for i in items)
    total_quantity = sum(i.current_quantity for i in items)

    if total_quantity > 0:
        product.average_cost = total_value / total_quantity
```
2. Call after creating inventory item

**Files**: `src/services/transaction_import_service.py`

### Subtask T035 - Implement duplicate detection

**Purpose**: Skip purchases that appear to be duplicates.

**Steps**:
1. Define duplicate criteria: (product_slug, date, unit_price)
```python
def is_duplicate_purchase(product_id: int, purchase_date: datetime, unit_price: Decimal, session) -> bool:
    """Check if purchase appears to be a duplicate."""
    existing = session.query(Purchase).filter(
        Purchase.product_id == product_id,
        Purchase.purchase_date == purchase_date,
        Purchase.unit_price == unit_price
    ).first()
    return existing is not None
```
2. Skip with warning (not error):
```python
if is_duplicate_purchase(product.id, purchase_date, unit_price, session):
    result.add_skip(
        "purchases",
        product_slug,
        f"Duplicate purchase detected (same product, date, price)",
        suggestion="This purchase may have been imported previously"
    )
    continue
```

**Files**: `src/services/transaction_import_service.py`

### Subtask T036 - Return ImportResult with counts

**Purpose**: Provide accurate result reporting.

**Steps**:
1. Track counts throughout:
```python
result.add_success("purchases")  # After successful create
result.add_skip(...)             # For duplicates
result.add_error(...)            # For validation failures
```
2. Commit or rollback based on dry_run:
```python
if dry_run:
    session.rollback()
else:
    session.commit()
```
3. Return result with summary

**Files**: `src/services/transaction_import_service.py`

### Subtask T037 - Add unit tests

**Purpose**: Comprehensive tests for purchase import.

**Steps**:
1. Create `src/tests/services/test_transaction_import_service.py`
2. Add tests:
   - `test_import_purchases_creates_records()`
   - `test_import_purchases_creates_inventory_items()`
   - `test_import_purchases_rejects_negative_quantity()`
   - `test_import_purchases_rejects_unknown_product()`
   - `test_import_purchases_skips_duplicates()`
   - `test_import_purchases_updates_average_cost()`
   - `test_import_purchases_dry_run_no_commit()`

**Files**: `src/tests/services/test_transaction_import_service.py` (NEW)

---

## Test Strategy

**Unit Tests** (required):
- Test successful purchase creation
- Test inventory item linkage
- Test validation rejections
- Test duplicate detection
- Test cost recalculation

**Run Tests**:
```bash
./run-tests.sh src/tests/services/test_transaction_import_service.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Duplicate false positives | Use three-field combination for detection |
| Cost calculation errors | Verify against existing services |
| Partial import on error | Atomic transaction - rollback all on failure |

---

## Definition of Done Checklist

- [ ] `transaction_import_service.py` created
- [ ] `import_purchases()` function implemented
- [ ] Positive quantity validation
- [ ] Product slug resolution with clear errors
- [ ] Purchase and InventoryItem records created
- [ ] Weighted average cost updated
- [ ] Duplicate detection working
- [ ] All unit tests pass

## Review Guidance

**Reviewers should verify**:
1. Transaction atomicity (all-or-nothing)
2. Duplicate detection criteria reasonable
3. Error messages actionable
4. Cost calculations accurate

---

## Activity Log

- 2026-01-12T16:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-12T17:49:42Z – unknown – lane=for_review – Implemented import_purchases() with composite slug resolution, positive quantity validation, duplicate detection, Purchase/InventoryItem creation, and 26 unit tests passing
- 2026-01-12T22:00:00Z – claude – shell_pid=13882 – lane=done – Approved: All 21 purchase tests pass. Positive quantity validation, duplicate detection, supplier resolution working correctly.
