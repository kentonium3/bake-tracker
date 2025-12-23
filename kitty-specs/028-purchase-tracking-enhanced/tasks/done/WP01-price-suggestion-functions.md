---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
title: "Price Suggestion Service Functions"
phase: "Phase 1 - Service Layer"
lane: "done"
assignee: ""
agent: "system"
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

# Work Package Prompt: WP01 - Price Suggestion Service Functions

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Add two price suggestion query functions to `purchase_service.py` that enable price hints in the UI when users select a product/supplier combination.

**Success Criteria**:
- `get_last_price_at_supplier()` returns most recent purchase price for a product at a specific supplier
- `get_last_price_any_supplier()` returns most recent purchase price for a product at any supplier (fallback)
- Both functions return None when no purchase history exists
- Both functions follow the `session=None` pattern per CLAUDE.md
- Unit tests achieve >70% coverage on these functions

**User Story**: US2 (Price Suggestion from Purchase History) - Foundation

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/028-purchase-tracking-enhanced/spec.md` - FR-004, FR-005, FR-006
- `kitty-specs/028-purchase-tracking-enhanced/plan.md` - Section 1.1
- `kitty-specs/028-purchase-tracking-enhanced/data-model.md` - Purchase entity
- `.kittify/memory/constitution.md` - Session management pattern

**Existing Infrastructure**:
- `src/models/purchase.py` - Purchase model with product_id, supplier_id, unit_price, purchase_date
- `src/services/purchase_service.py` - Existing service (has record_purchase, get_purchase_history)
- Model helpers: `get_most_recent_price()`, `get_average_price()` already exist in purchase.py

**Constraints**:
- Must use `session=None` pattern for composability
- Return dict format, not ORM objects (avoids detachment issues)
- Performance: < 1 second response time (local SQLite)

---

## Subtasks & Detailed Guidance

### Subtask T001 - Implement `get_last_price_at_supplier()`

**Purpose**: Enable price suggestion when user selects a specific product/supplier combination.

**Steps**:
1. Add function to `src/services/purchase_service.py`
2. Query Purchase table: `product_id = X AND supplier_id = Y ORDER BY purchase_date DESC LIMIT 1`
3. Return dict with: `unit_price`, `purchase_date`, `supplier_id`
4. Return `None` if no matching purchase exists

**Function Signature**:
```python
def get_last_price_at_supplier(
    product_id: int,
    supplier_id: int,
    session: Optional[Session] = None
) -> Optional[Dict[str, Any]]:
    """
    Get last purchase price for product at specific supplier.

    Args:
        product_id: Product ID
        supplier_id: Supplier ID
        session: Optional database session

    Returns:
        Dict with unit_price (Decimal as str), purchase_date (ISO str), supplier_id
        None if no purchase history at this supplier
    """
```

**Implementation Pattern** (follow existing service patterns):
```python
def get_last_price_at_supplier(...):
    if session is not None:
        return _get_last_price_at_supplier_impl(product_id, supplier_id, session)
    with session_scope() as session:
        return _get_last_price_at_supplier_impl(product_id, supplier_id, session)

def _get_last_price_at_supplier_impl(product_id, supplier_id, session):
    purchase = (
        session.query(Purchase)
        .filter(Purchase.product_id == product_id)
        .filter(Purchase.supplier_id == supplier_id)
        .order_by(Purchase.purchase_date.desc())
        .first()
    )
    if not purchase:
        return None
    return {
        "unit_price": str(purchase.unit_price),
        "purchase_date": purchase.purchase_date.isoformat(),
        "supplier_id": purchase.supplier_id,
    }
```

**Files**: `src/services/purchase_service.py`
**Parallel?**: Yes - independent function

---

### Subtask T002 - Implement `get_last_price_any_supplier()`

**Purpose**: Fallback price suggestion when no history exists at selected supplier.

**Steps**:
1. Add function to `src/services/purchase_service.py`
2. Query Purchase table: `product_id = X ORDER BY purchase_date DESC LIMIT 1`
3. Include supplier_name in return for hint display
4. Return `None` if no purchase history exists

**Function Signature**:
```python
def get_last_price_any_supplier(
    product_id: int,
    session: Optional[Session] = None
) -> Optional[Dict[str, Any]]:
    """
    Get last purchase price for product at any supplier.
    Used as fallback when no history at selected supplier.

    Args:
        product_id: Product ID
        session: Optional database session

    Returns:
        Dict with unit_price, purchase_date, supplier_id, supplier_name
        None if no purchase history exists
    """
```

**Implementation Notes**:
- Join with Supplier to get supplier_name for the hint
- Use `Supplier.display_name` property or construct from name/city/state

**Files**: `src/services/purchase_service.py`
**Parallel?**: Yes - independent function

---

### Subtask T003 - Write Unit Tests

**Purpose**: Ensure price suggestion functions work correctly in all scenarios.

**Test Cases** (create in `src/tests/services/test_purchase_service.py`):

```python
class TestPriceSuggestionFunctions:
    """Test suite for F028 price suggestion functions."""

    def test_get_last_price_at_supplier_with_history(self, session, product_with_purchases):
        """Returns most recent price when history exists."""
        # Setup: product with 3 purchases at Costco
        result = get_last_price_at_supplier(product_id, supplier_id, session=session)
        assert result is not None
        assert result["supplier_id"] == supplier_id
        # Verify it's the most recent purchase

    def test_get_last_price_at_supplier_no_history(self, session, product_without_purchases):
        """Returns None when no history at supplier."""
        result = get_last_price_at_supplier(product_id, supplier_id, session=session)
        assert result is None

    def test_get_last_price_at_supplier_different_supplier(self, session, product_with_purchases_at_other_supplier):
        """Returns None when history exists at different supplier."""
        # Product has purchases at Wegmans, not Costco
        result = get_last_price_at_supplier(product_id, costco_id, session=session)
        assert result is None

    def test_get_last_price_any_supplier_with_history(self, session, product_with_purchases):
        """Returns most recent price from any supplier."""
        result = get_last_price_any_supplier(product_id, session=session)
        assert result is not None
        assert "supplier_name" in result

    def test_get_last_price_any_supplier_no_history(self, session, product_without_purchases):
        """Returns None when no purchase history exists."""
        result = get_last_price_any_supplier(product_id, session=session)
        assert result is None

    def test_get_last_price_any_supplier_multiple_suppliers(self, session, product_with_multi_supplier_purchases):
        """Returns most recent regardless of supplier."""
        # Most recent is at Wegmans, older at Costco
        result = get_last_price_any_supplier(product_id, session=session)
        assert result["supplier_name"] == "Wegmans"  # Or display_name format
```

**Files**: `src/tests/services/test_purchase_service.py`
**Parallel?**: Yes - can be written alongside implementation

**Test Fixtures Needed**:
- `product_with_purchases`: Product with Purchase records
- `product_without_purchases`: Product with no Purchase records
- Supplier fixtures (Costco, Wegmans)

---

## Test Strategy

**Required Coverage**: >70% on new functions

**Run Tests**:
```bash
pytest src/tests/services/test_purchase_service.py -v --cov=src/services/purchase_service
```

**Fixtures**: Use existing test database patterns; create Purchase records with known dates/prices.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Purchase model field names differ | Verify model structure before implementation |
| Session detachment issues | Return dict, not ORM objects |
| Performance with large history | LIMIT 1 + index on (product_id, purchase_date) |

---

## Definition of Done Checklist

- [ ] `get_last_price_at_supplier()` implemented and working
- [ ] `get_last_price_any_supplier()` implemented and working
- [ ] Both functions follow session=None pattern
- [ ] Unit tests written and passing
- [ ] Test coverage >70% on new code
- [ ] No regressions in existing tests

---

## Review Guidance

**Verification Checkpoints**:
1. Functions return correct dict format (not ORM objects)
2. None returned appropriately when no history
3. Most recent purchase selected (not oldest)
4. Tests cover happy path + edge cases
5. Session pattern matches CLAUDE.md guidance

---

## Activity Log

- 2025-12-22T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks.
- 2025-12-23T14:20:36Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-23T21:23:55Z – system – shell_pid= – lane=done – Moved to done
