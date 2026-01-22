---
work_package_id: "WP03"
subtasks:
  - "T009"
  - "T010"
  - "T011"
title: "Core Service - Validation and Mutation"
phase: "Phase 2 - Core Service"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "12436"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: ["WP01", "WP02"]
history:
  - timestamp: "2026-01-21T19:33:38Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2026-01-22T02:16:09Z"
    lane: "doing"
    agent: "claude-opus"
    shell_pid: "7745"
    action: "Started implementation"
  - timestamp: "2026-01-22T02:23:30Z"
    lane: "for_review"
    agent: "claude-opus"
    shell_pid: "7745"
    action: "Ready for review"
  - timestamp: "2026-01-22T02:40:14Z"
    lane: "done"
    agent: "claude-opus"
    shell_pid: "12436"
    action: "Review passed"
---

# Work Package Prompt: WP03 - Core Service - Validation and Mutation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

Depends on WP01 (model) and WP02 (query patterns established).

---

## Objectives & Success Criteria

- ✅ `check_availability()` returns availability status with shortage info if insufficient
- ✅ `validate_consumption()` validates without modifying, returns validation result
- ✅ `adjust_inventory()` modifies inventory AND creates audit record atomically
- ✅ Negative inventory is prevented (raises exception before modification)
- ✅ Invalid reasons are rejected
- ✅ Notes required when reason is "adjustment"
- ✅ All functions work with and without session parameter

## Context & Constraints

**Reference Documents**:
- `kitty-specs/061-finished-goods-inventory-service/plan.md` - Return value patterns
- `kitty-specs/061-finished-goods-inventory-service/data-model.md` - FinishedGoodsAdjustment model
- `kitty-specs/061-finished-goods-inventory-service/research.md` - Session patterns

**Key Constraints**:
- Use helper function session pattern
- Return dicts, not ORM objects
- Create audit record in SAME session as inventory update
- Validate BEFORE modification (never leave inconsistent state)

---

## Subtasks & Detailed Guidance

### Subtask T009 - Implement check_availability()

**Purpose**: Check if a quantity is available for consumption without modifying anything.

**Steps**:
1. Open `src/services/finished_goods_inventory_service.py`
2. Replace the `_check_availability_impl` stub with full implementation
3. Validate item_type is "finished_unit" or "finished_good"
4. Query the appropriate model by item_id
5. Compare `inventory_count` with requested `quantity`
6. Return result dict with availability status

**Files**:
- `src/services/finished_goods_inventory_service.py` (modify, ~30 lines)

**Return Value Pattern**:
```python
# When available
{
    "available": True,
    "item_type": "finished_unit",
    "item_id": 1,
    "requested": 5,
    "current_count": 24
}

# When insufficient
{
    "available": False,
    "item_type": "finished_unit",
    "item_id": 1,
    "requested": 30,
    "current_count": 24,
    "shortage": 6
}
```

**Edge Cases**:
- Item not found → raise ValueError("Item not found: finished_unit/1")
- Invalid item_type → raise ValueError("Invalid item_type: ...")
- Quantity <= 0 → raise ValueError("Quantity must be positive")

**Validation**:
- [ ] Returns correct dict structure
- [ ] Calculates shortage correctly
- [ ] Raises on invalid inputs
- [ ] Works with and without session

---

### Subtask T010 - Implement validate_consumption()

**Purpose**: Validate a consumption request without modifying inventory. Used for pre-flight checks in UI.

**Steps**:
1. Implement `_validate_consumption_impl`
2. This is similar to check_availability but with a different return structure
3. Validate item exists, quantity is positive, and sufficient inventory
4. Return validation result with detailed error messages if invalid

**Files**:
- `src/services/finished_goods_inventory_service.py` (modify, ~35 lines)

**Return Value Pattern**:
```python
# When valid
{
    "valid": True,
    "item_type": "finished_unit",
    "item_id": 1,
    "quantity": 5,
    "current_count": 24,
    "remaining_after": 19
}

# When invalid
{
    "valid": False,
    "item_type": "finished_unit",
    "item_id": 1,
    "quantity": 30,
    "current_count": 24,
    "error": "Insufficient inventory: need 30, have 24",
    "shortage": 6
}
```

**Validation**:
- [ ] Returns valid=True when sufficient inventory
- [ ] Returns valid=False with error message when insufficient
- [ ] Calculates remaining_after correctly
- [ ] Works with and without session

---

### Subtask T011 - Implement adjust_inventory()

**Purpose**: The core mutation function that adjusts inventory and creates an audit trail record.

**Steps**:
1. Implement `_adjust_inventory_impl`
2. Validate inputs:
   - item_type is valid
   - item exists
   - reason is in FINISHED_GOODS_ADJUSTMENT_REASONS
   - notes provided when reason is "adjustment"
3. Calculate new_count = current + quantity
4. Validate new_count >= 0 (BEFORE any modification)
5. Update the item's inventory_count
6. Create FinishedGoodsAdjustment record in same session
7. Flush to get adjustment ID
8. Return result dict

**Files**:
- `src/services/finished_goods_inventory_service.py` (modify, ~70 lines)

**Implementation Pattern**:
```python
def _adjust_inventory_impl(item_type, item_id, quantity, reason, notes, session):
    # Validate reason
    if reason not in FINISHED_GOODS_ADJUSTMENT_REASONS:
        raise ValueError(f"Invalid reason: {reason}. Must be one of: {FINISHED_GOODS_ADJUSTMENT_REASONS}")

    # Validate notes for "adjustment" reason
    if reason == "adjustment" and not notes:
        raise ValueError("Notes are required when reason is 'adjustment'")

    # Get the item
    if item_type == "finished_unit":
        item = session.query(FinishedUnit).filter_by(id=item_id).first()
    elif item_type == "finished_good":
        item = session.query(FinishedGood).filter_by(id=item_id).first()
    else:
        raise ValueError(f"Invalid item_type: {item_type}")

    if not item:
        raise ValueError(f"Item not found: {item_type}/{item_id}")

    # Calculate and validate new count
    previous_count = item.inventory_count
    new_count = previous_count + quantity

    if new_count < 0:
        raise ValueError(
            f"Adjustment would result in negative inventory: "
            f"{previous_count} + {quantity} = {new_count}"
        )

    # Update inventory
    item.inventory_count = new_count

    # Create audit record
    adjustment = FinishedGoodsAdjustment(
        finished_unit_id=item_id if item_type == "finished_unit" else None,
        finished_good_id=item_id if item_type == "finished_good" else None,
        quantity_change=quantity,
        previous_count=previous_count,
        new_count=new_count,
        reason=reason,
        notes=notes
    )
    session.add(adjustment)
    session.flush()  # Get the ID

    return {
        "success": True,
        "item_type": item_type,
        "item_id": item_id,
        "previous_count": previous_count,
        "new_count": new_count,
        "quantity_change": quantity,
        "reason": reason,
        "adjustment_id": adjustment.id
    }
```

**Edge Cases**:
- Negative quantity that would result in negative inventory → raise ValueError BEFORE modification
- Invalid reason → raise ValueError
- Missing notes for "adjustment" reason → raise ValueError
- Item not found → raise ValueError

**Validation**:
- [ ] Creates audit record for every adjustment
- [ ] Audit record has correct FK (only one set)
- [ ] Prevents negative inventory
- [ ] Validates reason against FINISHED_GOODS_ADJUSTMENT_REASONS
- [ ] Requires notes for "adjustment" reason
- [ ] Returns adjustment_id in result
- [ ] Works with and without session

---

## Test Strategy

No tests in this WP - tests are in WP07.

Manual validation:
```python
from src.services import finished_goods_inventory_service as fg_inv

# Test availability check
result = fg_inv.check_availability("finished_unit", 1, 5)
print(f"Available: {result['available']}")

# Test validation
result = fg_inv.validate_consumption("finished_unit", 1, 5)
print(f"Valid: {result['valid']}")

# Test adjustment (with existing test data)
result = fg_inv.adjust_inventory(
    "finished_unit", 1, 10, "production",
    notes="Test production run"
)
print(f"Adjusted: {result['previous_count']} -> {result['new_count']}")
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Race conditions | Session isolation; DB CHECK constraint is backup |
| Audit record without inventory update | Same session, flush together |
| Invalid state on error | Validate BEFORE any modification |

---

## Definition of Done Checklist

- [ ] T009: check_availability implemented with correct return structure
- [ ] T010: validate_consumption implemented with validation details
- [ ] T011: adjust_inventory implemented with audit trail
- [ ] All functions validate inputs before modification
- [ ] All functions work with session=None (own transaction)
- [ ] All functions work with session provided (caller's transaction)
- [ ] Negative inventory prevented with clear error message
- [ ] Invalid reasons rejected
- [ ] Notes required for "adjustment" reason

---

## Review Guidance

**Key checkpoints**:
1. adjust_inventory creates audit record in SAME session
2. Validation happens BEFORE any modification
3. Return values match plan.md patterns exactly
4. Session pattern is correct (helper function approach)
5. All edge cases handled with appropriate exceptions

---

## Activity Log

- 2026-01-21T19:33:38Z - system - lane=planned - Prompt created.
- 2026-01-22T02:16:09Z - claude-opus - shell_pid=7745 - lane=doing - Started implementation via workflow command
- 2026-01-22T02:23:30Z - claude-opus - shell_pid=7745 - lane=for_review - Ready for review: Implemented check_availability, validate_consumption, and adjust_inventory. All functions validate inputs before modification, prevent negative inventory, and create audit records in same session. All 2581 tests pass.
- 2026-01-22T02:39:30Z - claude-opus - shell_pid=12436 - lane=doing - Started review via workflow command
- 2026-01-22T02:40:14Z - claude-opus - shell_pid=12436 - lane=done - Review passed: All 3 validation/mutation functions correctly implemented. check_availability returns availability with shortage. validate_consumption validates without modifying. adjust_inventory creates audit record in same session with all validations BEFORE modification. Session pattern correct. All 2581 tests pass.
