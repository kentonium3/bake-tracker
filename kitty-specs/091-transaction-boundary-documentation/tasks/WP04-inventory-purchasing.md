---
work_package_id: WP04
title: Inventory & Purchasing Services
lane: "for_review"
dependencies: [WP01]
base_branch: 091-transaction-boundary-documentation-WP01
base_commit: ea54478c184557f13c16ab46b637a8903d9343c6
created_at: '2026-02-03T04:50:34.263271+00:00'
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 2 - Documentation
assignee: ''
agent: ''
shell_pid: "22568"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T04:37:19Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Inventory & Purchasing Services

## Objectives & Success Criteria

**Goal**: Add transaction boundary documentation to inventory and purchasing service files.

**Success Criteria**:
- [ ] All public functions in `inventory_item_service.py` have "Transaction boundary:" section
- [ ] All public functions in `purchase_service.py` have "Transaction boundary:" section
- [ ] Existing docs (consume_fifo, record_purchase) verified and enhanced if needed

**Implementation Command**:
```bash
spec-kitty implement WP04 --base WP01
```

**Parallel-Safe**: Yes - but complex; assign to Claude

## Context & Constraints

**References**:
- Templates: `kitty-specs/091-transaction-boundary-documentation/research/docstring_templates.md`
- Existing docs: `consume_fifo` (lines 304-326), `record_purchase` (lines 74-126)

**Key Constraints**:
- These services have the MOST MULTI functions
- Some functions already have excellent documentation - preserve and standardize
- Many `_impl` functions - document transaction inheritance pattern

## Subtasks & Detailed Guidance

### Subtask T011 – Document inventory_item_service.py (~19 functions)

**Purpose**: Add transaction boundary documentation to all public functions.

**Files**:
- Edit: `src/services/inventory_item_service.py`

**Functions to document**:

| Function | Type | Template | Notes |
|----------|------|----------|-------|
| `add_to_inventory` | MULTI | Pattern C | Creates Purchase + InventoryItem atomically |
| `get_inventory_items` | READ | Pattern A | |
| `get_total_quantity` | MULTI | Pattern C | Calls get_ingredient + get_inventory_items |
| `consume_fifo` | MULTI | Pattern C | **ALREADY DOCUMENTED** - verify |
| `get_expiring_soon` | READ | Pattern A | |
| `update_inventory_item` | SINGLE | Pattern B | |
| `update_inventory_supplier` | MULTI | Pattern C | Updates or creates Purchase |
| `update_inventory_quantity` | MULTI | Pattern C | Multiple methods for calculating |
| `delete_inventory_item` | SINGLE | Pattern B | |
| `get_inventory_value` | READ | Pattern A | |
| `get_recent_products` | READ | Pattern A | |
| `get_recent_ingredients` | READ | Pattern A | |
| `manual_adjustment` | MULTI | Pattern C | Creates InventoryDepletion + updates item |
| `get_depletion_history` | READ | Pattern A | |

**For `consume_fifo` - Verify existing documentation**:
The function already has excellent documentation (lines 304-326). Verify it includes:
- [ ] "Transaction boundary:" phrase
- [ ] Atomicity guarantee statement
- [ ] Steps executed atomically list
- [ ] CRITICAL note about session passing

If missing any, enhance to match Pattern C template.

**Example for add_to_inventory**:
```python
def add_to_inventory(product_id: int, quantity: float, ..., session: Optional[Session] = None):
    """
    Add inventory from a purchase.

    Transaction boundary: ALL operations in single session (atomic).
    Atomicity guarantee: Either ALL steps succeed OR entire operation rolls back.
    Steps executed atomically:
    1. Create or find Purchase record for supplier/date
    2. Create InventoryItem linked to Purchase
    3. Update product's last purchase date

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.

    Args:
        ...
        session: Optional session for transactional composition

    Returns:
        Created InventoryItem instance

    Raises:
        ...
    """
```

**Validation**:
- [ ] All 19 functions documented
- [ ] consume_fifo documentation verified/enhanced

---

### Subtask T012 – Document purchase_service.py (~26 functions)

**Purpose**: Add transaction boundary documentation to all public functions.

**Files**:
- Edit: `src/services/purchase_service.py`

**Functions to document**:

| Function | Type | Template | Notes |
|----------|------|----------|-------|
| `record_purchase` | MULTI | Pattern C | **ALREADY DOCUMENTED** - verify |
| `get_purchase` | READ | Pattern A | |
| `get_purchase_history` | READ | Pattern A | |
| `get_most_recent_purchase` | READ | Pattern A | Calls get_product |
| `calculate_average_price` | READ | Pattern A | |
| `detect_price_change` | MULTI | Pattern C | Calls calculate_average_price |
| `get_price_trend` | READ | Pattern A | |
| `get_last_price_at_supplier` | READ | Pattern A | |
| `get_last_price_any_supplier` | READ | Pattern A | |
| `delete_purchase` | MULTI | Pattern C | Deletes inventory items + purchase |
| `get_purchases_filtered` | READ | Pattern A | |
| `get_remaining_inventory` | READ | Pattern A | |
| `can_edit_purchase` | READ | Pattern A | |
| `can_delete_purchase` | READ | Pattern A | |
| `update_purchase` | MULTI | Pattern C | Updates multiple fields + linked items |
| `get_purchase_usage_history` | READ | Pattern A | |

**For _impl functions**:
Document with note about session inheritance:
```python
def _record_purchase_impl(data, session: Session):
    """
    Implementation of record_purchase.

    Transaction boundary: Inherits session from caller.
    This function MUST be called with an active session - it does not
    create its own session_scope(). All operations execute within the
    caller's transaction boundary.

    Args:
        data: Purchase data
        session: Required session (inherited from record_purchase)
    """
```

**Validation**:
- [ ] All 26 functions documented
- [ ] record_purchase documentation verified/enhanced

---

### Subtask T013 – Verify consume_fifo documentation is complete

**Purpose**: Ensure existing documentation matches template exactly.

**Steps**:
1. Read current docstring at lines 304-326
2. Compare against Pattern C template
3. If missing elements, add them
4. Ensure "Transaction boundary:" phrase is present

**Expected elements**:
- [ ] "Transaction boundary:" phrase
- [ ] "Atomicity guarantee:" statement
- [ ] "Steps executed atomically:" numbered list
- [ ] "CRITICAL:" note about session passing
- [ ] Proper Args/Returns/Raises sections

---

### Subtask T014 – Verify record_purchase documentation is complete

**Purpose**: Ensure existing documentation matches template exactly.

**Steps**:
1. Read current docstring at lines 74-126
2. Compare against Pattern C template
3. If missing elements, add them

**Expected elements**:
Same as T013.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| High MULTI count (21 functions) | Focus on step documentation accuracy |
| Existing docs incomplete | Verify against template, enhance if needed |
| _impl pattern confusion | Document session inheritance clearly |

## Definition of Done Checklist

- [ ] inventory_item_service.py: All 19 public functions documented
- [ ] purchase_service.py: All 26 public functions documented
- [ ] consume_fifo: Documentation verified complete
- [ ] record_purchase: Documentation verified complete
- [ ] _impl functions document session inheritance
- [ ] Tests still pass: `pytest src/tests -v -k "inventory or purchase"`

## Review Guidance

**Reviewers should verify**:
1. Existing excellent docs preserved
2. MULTI functions have accurate step lists
3. _impl functions explain session inheritance
4. No functional changes

## Activity Log

- 2026-02-03T04:37:19Z – system – lane=planned – Prompt created.
- 2026-02-03T05:00:27Z – unknown – shell_pid=22568 – lane=for_review – Ready for review: Added transaction boundary docs to inventory_item_service.py (14 functions) and purchase_service.py (16 functions)
