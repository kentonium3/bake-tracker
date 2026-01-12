---
work_package_id: "WP05"
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
title: "Inventory Adjustment Import"
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

# Work Package Prompt: WP05 - Inventory Adjustment Import

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Extend `transaction_import_service.py` with inventory adjustment import for spoilage, waste, and corrections.

**Success Criteria**:
- SC-007: Inventory adjustment import decreases quantities correctly
- SC-008: Positive adjustment attempts rejected 100% of the time with clear error
- FR-019: System MUST support inventory adjustment imports
- FR-020: System MUST validate adjustments have negative quantities only
- FR-021: System MUST require reason code (spoilage, waste, correction, other)
- FR-022: System MUST prevent adjustments that would create negative inventory

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/049-import-export-phase1/spec.md` (User Story 5)
- Plan: `kitty-specs/049-import-export-phase1/plan.md`
- Import spec: `docs/design/spec_import_export.md` (Appendix J)

**Adjustment Import JSON Schema**:
```json
{
  "schema_version": "4.0",
  "import_type": "adjustments",
  "created_at": "2026-01-12T09:15:00Z",
  "source": "bt_mobile",
  "adjustments": [
    {
      "product_slug": "flour_all_purpose_king_arthur_5lb",
      "adjusted_at": "2026-01-12T09:10:12Z",
      "quantity": -2.5,
      "reason_code": "spoilage",
      "notes": "Found mold, discarding"
    }
  ]
}
```

**Allowed Reason Codes**:
- `spoilage` - Product went bad
- `waste` - Spilled, burned, or otherwise wasted
- `correction` - Count was wrong, adjusting to match physical
- `other` - Other reason (notes should explain)

**FIFO Rule**: When multiple inventory items exist for a product, adjust the oldest first.

---

## Subtasks & Detailed Guidance

### Subtask T038 - Add `import_adjustments()` function

**Purpose**: Main entry point for adjustment imports.

**Steps**:
1. Add to `src/services/transaction_import_service.py`:
```python
ALLOWED_REASON_CODES = {"spoilage", "waste", "correction", "other"}

def import_adjustments(file_path: str, dry_run: bool = False) -> ImportResult:
    """
    Import inventory adjustments from JSON file.

    Decreases inventory quantities for spoilage, waste, and corrections.
    Only negative quantities allowed (increases must be purchases).

    Args:
        file_path: Path to JSON file with adjustments
        dry_run: If True, validate without committing

    Returns:
        ImportResult with counts and any errors
    """
    result = ImportResult()

    with open(file_path) as f:
        data = json.load(f)

    # Validate schema
    if data.get("schema_version") != "4.0":
        result.add_error("file", file_path, "Unsupported schema version")
        return result

    if data.get("import_type") not in ("adjustments", "inventory_updates"):
        result.add_error("file", file_path, "Wrong import type")
        return result

    with session_scope() as session:
        for adj_data in data.get("adjustments", []):
            process_adjustment(adj_data, session, result)

        if not result.failed and not dry_run:
            session.commit()
        else:
            session.rollback()

    return result
```

**Files**: `src/services/transaction_import_service.py`

### Subtask T039 - Validate negative quantities only

**Purpose**: Reject positive or zero quantities.

**Steps**:
1. Add validation:
```python
quantity = adj_data.get("quantity", 0)

if quantity >= 0:
    result.add_error(
        "adjustments",
        adj_data.get("product_slug", "unknown"),
        f"Invalid quantity {quantity}: adjustments must be negative",
        suggestion="Inventory increases must be done via purchase import"
    )
    continue
```
2. This is the inverse of purchase validation (T030)

**Files**: `src/services/transaction_import_service.py`

### Subtask T040 - Require reason_code field

**Purpose**: Ensure every adjustment has a reason for audit trail.

**Steps**:
1. Check for presence:
```python
reason_code = adj_data.get("reason_code")

if not reason_code:
    result.add_error(
        "adjustments",
        adj_data.get("product_slug", "unknown"),
        "Missing reason_code field",
        suggestion=f"Valid codes: {', '.join(ALLOWED_REASON_CODES)}"
    )
    continue
```

**Files**: `src/services/transaction_import_service.py`

### Subtask T041 - Validate reason_code against allowed list

**Purpose**: Only accept known reason codes.

**Steps**:
1. Validate against allowed set:
```python
if reason_code not in ALLOWED_REASON_CODES:
    result.add_error(
        "adjustments",
        adj_data.get("product_slug", "unknown"),
        f"Invalid reason_code '{reason_code}'",
        suggestion=f"Valid codes: {', '.join(ALLOWED_REASON_CODES)}"
    )
    continue
```

**Files**: `src/services/transaction_import_service.py`

### Subtask T042 - Resolve product_slug and find InventoryItem (FIFO)

**Purpose**: Find the oldest inventory item to adjust.

**Steps**:
1. Resolve product:
```python
product_slug = adj_data.get("product_slug")
product = session.query(Product).filter_by(slug=product_slug).first()

if not product:
    result.add_error(
        "adjustments",
        product_slug,
        f"Product '{product_slug}' not found"
    )
    continue
```
2. Find inventory items in FIFO order:
```python
inventory_items = session.query(InventoryItem).filter(
    InventoryItem.product_id == product.id,
    InventoryItem.current_quantity > 0
).order_by(InventoryItem.purchase_date.asc()).all()

if not inventory_items:
    result.add_error(
        "adjustments",
        product_slug,
        "No inventory found for product",
        suggestion="Cannot adjust inventory that doesn't exist"
    )
    continue
```

**Files**: `src/services/transaction_import_service.py`

### Subtask T043 - Prevent adjustments exceeding available inventory

**Purpose**: Cannot create negative inventory quantities.

**Steps**:
1. Calculate total available:
```python
total_available = sum(i.current_quantity for i in inventory_items)
adjustment_amount = abs(Decimal(str(quantity)))  # quantity is negative

if adjustment_amount > total_available:
    result.add_error(
        "adjustments",
        product_slug,
        f"Adjustment amount ({adjustment_amount}) exceeds available inventory ({total_available})",
        suggestion="Cannot reduce inventory below zero"
    )
    continue
```

**Files**: `src/services/transaction_import_service.py`

### Subtask T044 - Create adjustment record

**Purpose**: Create audit record for the adjustment.

**Steps**:
1. Use existing model (likely InventoryDepletion or similar):
```python
from src.models.inventory_depletion import InventoryDepletion

# Create depletion record for each affected inventory item
depletion = InventoryDepletion(
    inventory_item_id=inventory_item.id,
    quantity_depleted=amount_from_this_item,
    depletion_date=parse_datetime(adj_data.get("adjusted_at")),
    depletion_reason=reason_code,
    related_entity_type="adjustment_import",
    notes=adj_data.get("notes")
)
session.add(depletion)
```
2. Check existing model for exact field names

**Files**: `src/services/transaction_import_service.py`

### Subtask T045 - Update InventoryItem.current_quantity

**Purpose**: Decrease inventory following FIFO.

**Steps**:
1. Implement FIFO deduction:
```python
remaining_to_adjust = adjustment_amount

for inv_item in inventory_items:  # Already ordered by purchase_date asc
    if remaining_to_adjust <= 0:
        break

    available = inv_item.current_quantity
    amount_from_this = min(available, remaining_to_adjust)

    inv_item.current_quantity -= amount_from_this
    remaining_to_adjust -= amount_from_this

    # Create depletion record for this portion
    create_depletion_record(inv_item, amount_from_this, adj_data, session)
```
2. This drains oldest inventory first

**Files**: `src/services/transaction_import_service.py`

### Subtask T046 - Add unit tests for adjustment import

**Purpose**: Comprehensive tests for adjustment functionality.

**Steps**:
1. Add to `src/tests/services/test_transaction_import_service.py`:
   - `test_import_adjustments_decreases_inventory()`
   - `test_import_adjustments_rejects_positive_quantity()`
   - `test_import_adjustments_rejects_zero_quantity()`
   - `test_import_adjustments_requires_reason_code()`
   - `test_import_adjustments_rejects_invalid_reason_code()`
   - `test_import_adjustments_prevents_negative_inventory()`
   - `test_import_adjustments_uses_fifo()`
   - `test_import_adjustments_creates_depletion_records()`

**Files**: `src/tests/services/test_transaction_import_service.py`

---

## Test Strategy

**Unit Tests** (required):
- Test negative-only validation
- Test reason code validation
- Test FIFO ordering
- Test negative inventory prevention
- Test depletion record creation

**Run Tests**:
```bash
./run-tests.sh src/tests/services/test_transaction_import_service.py -v -k adjustment
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FIFO edge cases | Test with multiple inventory items |
| Decimal precision | Use Decimal for all quantity math |
| Missing depletion model | Check existing models first |

---

## Definition of Done Checklist

- [ ] `import_adjustments()` function implemented
- [ ] Negative quantity validation (rejects positive/zero)
- [ ] Reason code required and validated
- [ ] FIFO inventory selection working
- [ ] Negative inventory prevented
- [ ] Depletion/adjustment records created
- [ ] Inventory quantities updated
- [ ] All unit tests pass

## Review Guidance

**Reviewers should verify**:
1. Positive quantities rejected 100% (SC-008)
2. FIFO ordering correct
3. Depletion records have audit trail
4. Error messages clear and actionable

---

## Activity Log

- 2026-01-12T16:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-12T17:48:07Z – unknown – lane=for_review – Implemented import_adjustments() with FIFO inventory selection, negative quantity validation, reason_code validation, prevents exceeding available inventory, creates InventoryDepletion audit records. Added comprehensive unit tests.
- 2026-01-12T22:05:00Z – claude – shell_pid=13882 – lane=done – Approved: All 19 adjustment tests pass. Negative-only validation, FIFO ordering, reason code validation (now case-insensitive with DAMAGED added), depletion records created correctly.
