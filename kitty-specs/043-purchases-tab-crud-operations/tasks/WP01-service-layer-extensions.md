---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Service Layer Extensions"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-08T22:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Service Layer Extensions

## Objectives & Success Criteria

Extend `PurchaseService` with 6 new methods to support the Purchases tab CRUD operations:

1. **get_purchases_filtered()** - Main list query with date range, supplier, and search filters
2. **get_remaining_inventory()** - Calculate FIFO remaining quantity for a purchase
3. **can_edit_purchase()** - Validate if edit is allowed (quantity >= consumed)
4. **can_delete_purchase()** - Check if any depletions exist
5. **update_purchase()** - Apply edits and recalculate FIFO costs
6. **get_purchase_usage_history()** - Get depletions with recipe info

**Success Criteria**:
- All 6 methods implemented with correct session management pattern
- Unit tests pass with >70% coverage on new methods
- Methods can be called from Python REPL with test data

## Context & Constraints

**Reference Documents**:
- `kitty-specs/043-purchases-tab-crud-operations/data-model.md` - Full method signatures
- `kitty-specs/043-purchases-tab-crud-operations/research.md` - Session management pattern
- `.kittify/memory/constitution.md` - Principle II (Data Integrity & FIFO)

**Key Constraints**:
- All methods MUST accept `session: Optional[Session] = None` parameter
- Follow the inner `_impl()` function pattern (see research.md)
- Date range default is "last_30_days" per clarification
- Quantity allows 1 decimal place per clarification

**Existing Code**:
- `src/services/purchase_service.py` - Extend this file
- `src/tests/unit/test_purchase_service.py` - Add tests here

## Subtasks & Detailed Guidance

### Subtask T001 - Implement get_purchases_filtered()

**Purpose**: Main query for purchase list with filters.

**Signature**:
```python
def get_purchases_filtered(
    date_range: str = "last_30_days",
    supplier_id: Optional[int] = None,
    search_query: Optional[str] = None,
    session: Optional[Session] = None
) -> List[Dict]:
```

**Steps**:
1. Add method to `PurchaseService` class
2. Create inner `_impl(sess: Session)` function
3. Calculate date cutoff based on `date_range`:
   - "last_30_days" → `date.today() - timedelta(days=30)`
   - "last_90_days" → 90 days
   - "last_year" → 365 days
   - "all_time" → None (no cutoff)
4. Build SQLAlchemy query joining Purchase → Product → Supplier
5. Apply filters: date cutoff, supplier_id, search (ilike on product.display_name)
6. Order by purchase_date DESC
7. For each purchase, call `get_remaining_inventory()` to compute remaining
8. Return list of dicts with fields per data-model.md

**Files**: `src/services/purchase_service.py`
**Parallel?**: Yes (independent method)

### Subtask T002 - Implement get_remaining_inventory()

**Purpose**: Calculate remaining quantity from a purchase (FIFO tracking).

**Signature**:
```python
def get_remaining_inventory(
    purchase_id: int,
    session: Optional[Session] = None
) -> Decimal:
```

**Steps**:
1. Query Purchase by ID
2. Sum `current_quantity` across all linked `inventory_items`
3. Return total as Decimal (0 if no items or fully consumed)

**Files**: `src/services/purchase_service.py`
**Parallel?**: Yes

### Subtask T003 - Implement can_edit_purchase()

**Purpose**: Validate if quantity edit is allowed.

**Signature**:
```python
def can_edit_purchase(
    purchase_id: int,
    new_quantity: Decimal,
    session: Optional[Session] = None
) -> Tuple[bool, str]:
```

**Steps**:
1. Query Purchase with inventory_items
2. Calculate total consumed: sum of all depletions across inventory items
3. Calculate new total units: `new_quantity * product.package_unit_quantity`
4. If `new_total < consumed`: return `(False, f"Cannot reduce below {consumed} (already consumed)")`
5. Otherwise: return `(True, "")`

**Files**: `src/services/purchase_service.py`
**Parallel?**: Yes

### Subtask T004 - Implement can_delete_purchase()

**Purpose**: Check if any inventory has been consumed.

**Signature**:
```python
def can_delete_purchase(
    purchase_id: int,
    session: Optional[Session] = None
) -> Tuple[bool, str]:
```

**Steps**:
1. Query Purchase with inventory_items and their depletions
2. If any depletions exist:
   - Calculate total consumed
   - Get list of recipe names from production runs
   - Return `(False, f"Cannot delete - {consumed} {unit} already used in: {recipes}")`
3. Otherwise: return `(True, "")`

**Files**: `src/services/purchase_service.py`
**Parallel?**: Yes

### Subtask T005 - Implement update_purchase()

**Purpose**: Apply edits and recalculate FIFO costs.

**Signature**:
```python
def update_purchase(
    purchase_id: int,
    updates: Dict[str, Any],
    session: Optional[Session] = None
) -> Purchase:
```

**Steps**:
1. Query Purchase
2. Validate: if "product_id" in updates and different, raise ValueError
3. If "quantity_purchased" in updates, call `can_edit_purchase()` to validate
4. Apply field updates: purchase_date, quantity_purchased, unit_price, supplier_id, notes
5. If unit_price changed:
   - Recalculate `unit_cost` on linked InventoryItems
   - `unit_cost = new_unit_price / product.package_unit_quantity`
6. If quantity changed:
   - Calculate consumed quantity
   - Adjust `current_quantity` on InventoryItems proportionally
7. Return updated Purchase

**Files**: `src/services/purchase_service.py`
**Parallel?**: Yes
**Notes**: Most complex method; test thoroughly

### Subtask T006 - Implement get_purchase_usage_history()

**Purpose**: Get consumption history for View Details dialog.

**Signature**:
```python
def get_purchase_usage_history(
    purchase_id: int,
    session: Optional[Session] = None
) -> List[Dict]:
```

**Steps**:
1. Query Purchase → inventory_items → depletions → production_runs → recipes
2. For each depletion, build dict:
   - depletion_id
   - depleted_at (datetime)
   - recipe_name (from production_run.recipe.display_name)
   - quantity_used (abs of quantity_depleted)
   - cost (quantity * unit_cost at depletion time)
3. Order by depleted_at ASC
4. Return list of dicts

**Files**: `src/services/purchase_service.py`
**Parallel?**: Yes

### Subtask T007 - Add Unit Tests

**Purpose**: Verify all new methods work correctly.

**Test Cases** (minimum):
```python
# get_purchases_filtered
def test_get_purchases_filtered_default_30_days():
def test_get_purchases_filtered_by_supplier():
def test_get_purchases_filtered_by_search():
def test_get_purchases_filtered_empty_results():

# get_remaining_inventory
def test_get_remaining_inventory_unconsumed():
def test_get_remaining_inventory_partially_consumed():
def test_get_remaining_inventory_fully_consumed():

# can_edit_purchase
def test_can_edit_purchase_allowed():
def test_can_edit_purchase_blocked_below_consumed():

# can_delete_purchase
def test_can_delete_purchase_allowed_no_depletions():
def test_can_delete_purchase_blocked_has_depletions():

# update_purchase
def test_update_purchase_price_recalculates_costs():
def test_update_purchase_quantity_adjusts_inventory():
def test_update_purchase_rejects_product_change():

# get_purchase_usage_history
def test_get_purchase_usage_history_with_depletions():
def test_get_purchase_usage_history_empty():
```

**Files**: `src/tests/unit/test_purchase_service.py`
**Parallel?**: No (depends on T001-T006)

## Test Strategy

**Required Coverage**: >70% on new methods

**Test Fixtures Needed**:
- Purchase with no consumption (deletable, fully editable)
- Purchase with partial consumption (not deletable, quantity constrained)
- Purchase with full consumption (not deletable)
- Multiple purchases across date ranges
- Purchases from different suppliers

**Commands**:
```bash
pytest src/tests/unit/test_purchase_service.py -v
pytest src/tests/unit/test_purchase_service.py -v --cov=src/services/purchase_service
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session management bugs | Follow documented pattern exactly; use inner `_impl()` function |
| FIFO calculation errors | Create fixtures with known consumed quantities; verify math |
| Query performance | Use eager loading for relationships; add indices if needed |

## Definition of Done Checklist

- [ ] All 6 methods implemented in purchase_service.py
- [ ] All methods follow session management pattern
- [ ] Unit tests pass
- [ ] >70% coverage on new methods
- [ ] Methods callable from Python REPL
- [ ] No linting errors (flake8, mypy)

## Review Guidance

- Verify session pattern is correct (inner _impl function, conditional scope)
- Check FIFO calculations against expected values
- Ensure all query filters work correctly
- Verify error messages are specific and actionable

## Activity Log

- 2026-01-08T22:30:00Z - system - lane=planned - Prompt created.
- 2026-01-09T03:26:43Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-09T03:38:26Z – unknown – lane=for_review – All 6 service methods implemented with session management pattern. 30 unit tests added, all 45 tests pass.
- 2026-01-09T04:56:26Z – agent – lane=doing – Started review via workflow command
- 2026-01-09T04:58:04Z – unknown – lane=done – Review passed: All 6 methods implemented with session management pattern, 45 tests pass
