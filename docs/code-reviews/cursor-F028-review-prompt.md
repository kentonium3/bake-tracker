# Cursor Code Review Prompt - Feature 028: Purchase Tracking & Enhanced Costing

## Role

You are a senior software engineer performing an independent code review of Feature 028 (purchase-tracking-enhanced). This feature implements Purchase entity as a first-class transaction record linking products to suppliers with temporal pricing context, enabling price suggestions and accurate FIFO cost calculations.

## Feature Summary

**Core Changes:**
1. New price suggestion functions in `purchase_service.py` (`get_last_price_at_supplier()`, `get_last_price_any_supplier()`)
2. Updated `add_to_inventory()` signature with required `supplier_id` and `unit_price` parameters
3. Atomic Purchase record creation within inventory addition
4. `InventoryItem.unit_cost` populated from `Purchase.unit_price` for FIFO calculations
5. UI updates: Supplier dropdown, price entry field, and price hints in Add Inventory dialog
6. Zero-price confirmation warning and negative price validation
7. Migration script to link existing InventoryItems to Purchase records
8. FIFO verification tests ensuring cost calculations use purchase prices

**Scope:**
- Service layer: `purchase_service.py`, `inventory_item_service.py`, `recipe_service.py`
- Model layer: `purchase.py` (unit_cost property alias)
- UI layer: `inventory_tab.py` (supplier dropdown, price field, price hints)
- Migration: `src/services/migration/f028_migration.py`, `f028_validation.py`
- Tests: Updated tests across `test_recipe_service.py`, `test_production_service.py`, `test_packaging_service.py`, `test_product_recommendation_service.py`, `test_models.py`, `test_import_export_service.py`, integration tests

## Files to Review

### Service Layer (WP01-WP02)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/services/purchase_service.py`
  - `get_last_price_at_supplier(product_id, supplier_id, session=None)` - returns most recent purchase price for product at specific supplier
  - `get_last_price_any_supplier(product_id, session=None)` - returns most recent purchase price for product at any supplier (fallback)
  - `record_purchase()` - verify uses `unit_price` field, creates/finds supplier correctly
  - `get_purchase_history()` - verify supplier name filtering uses proper join

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/services/inventory_item_service.py`
  - `add_to_inventory()` - must require `supplier_id: int` and `unit_price: Decimal` parameters
  - Atomic Purchase record creation within same transaction
  - `InventoryItem.unit_cost` set from `unit_price` parameter
  - `InventoryItem.purchase_id` FK linkage to created Purchase

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/services/recipe_service.py`
  - ValidationError must use list format: `raise ValidationError(["message"])`

### Model Layer

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/models/purchase.py`
  - `unit_cost` property alias for `unit_price` (backward compatibility)
  - `total_cost` computed property (`unit_price * quantity_purchased`)
  - Verify `unit_price` is the stored column, not `unit_cost`

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/models/inventory_item.py`
  - `purchase_id` FK exists (nullable, ON DELETE RESTRICT)
  - `purchase` relationship to Purchase exists

### UI Layer (WP03)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/ui/inventory_tab.py`
  - Supplier dropdown populated from `get_active_suppliers()`, sorted alphabetically
  - Price entry field with decimal validation
  - Price hint label with dynamic update on supplier selection
  - `on_supplier_change` callback fetches/displays price suggestions
  - Price hint format: "(last paid: $X.XX on YYYY-MM-DD)" or "(last paid: $X.XX at Supplier on YYYY-MM-DD)"
  - Zero-price confirmation warning dialog (FR-007)
  - Negative price validation error (FR-008)
  - Dialog submission calls `add_to_inventory()` with `supplier_id` and `unit_price`

### Migration Scripts (WP04)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/services/migration/f028_migration.py`
  - Creates Purchase records for InventoryItems with NULL purchase_id
  - Finds/creates "Unknown" supplier (name='Unknown', state='XX')
  - Links InventoryItem.purchase_id to new Purchase records
  - Sets unit_cost if NULL (0.00 fallback with warning)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/services/migration/f028_validation.py`
  - Validates no InventoryItem has NULL purchase_id after migration
  - Validates Purchase.product_id matches InventoryItem.product_id
  - Record count validation

### Test Files

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/tests/services/test_purchase_service.py`
  - Tests for `get_last_price_at_supplier()` and `get_last_price_any_supplier()`

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/tests/services/test_inventory_item_service.py`
  - Tests for updated `add_to_inventory()` with new signature

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/tests/services/test_recipe_service.py`
  - All `add_to_inventory()` calls updated with `supplier_id` and `unit_price`
  - Uses `sample_supplier` fixture

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/tests/services/test_production_service.py`
  - All `add_to_inventory()` calls updated

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/tests/services/test_packaging_service.py`
  - All `add_to_inventory()` calls updated
  - `test_supplier` fixture present

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/tests/services/test_product_recommendation_service.py`
  - All `add_to_inventory()` calls updated
  - `test_supplier` fixture present
  - Purchase creation uses correct fields (`unit_price`, `supplier_id`)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/tests/test_models.py`
  - `TestPurchaseModel::test_create_purchase` uses new schema (`supplier_id`, `unit_price`)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/tests/services/test_import_export_service.py`
  - Version assertions updated to "3.5"

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/tests/integration/test_purchase_flow.py`
  - Integration tests for purchase workflow

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/src/tests/integration/test_packaging_flow.py`
  - Version assertion updated to "3.5"

### Data Files

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/test_data/sample_data.json`
  - Version should be "3.5"

### Specification Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/kitty-specs/028-purchase-tracking-enhanced/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/kitty-specs/028-purchase-tracking-enhanced/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/kitty-specs/028-purchase-tracking-enhanced/data-model.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/kitty-specs/028-purchase-tracking-enhanced/tasks.md`

## Review Checklist

### 1. Price Suggestion Functions (WP01)

- [ ] `get_last_price_at_supplier(product_id, supplier_id, session=None)` exists in purchase_service.py
- [ ] Returns dict with `unit_price`, `purchase_date`, `supplier_id` when history exists
- [ ] Returns `None` when no purchase history for product/supplier combination
- [ ] `get_last_price_any_supplier(product_id, session=None)` exists
- [ ] Returns dict with `unit_price`, `purchase_date`, `supplier_id`, `supplier_name` when history exists
- [ ] Returns `None` when no purchase history for product at any supplier
- [ ] Both functions follow `session=None` pattern per CLAUDE.md
- [ ] Query uses `ORDER BY purchase_date DESC LIMIT 1`
- [ ] Unit tests exist for both functions with various scenarios

### 2. Inventory-Purchase Integration (WP02)

- [ ] `add_to_inventory()` signature includes `supplier_id: int` as required parameter
- [ ] `add_to_inventory()` signature includes `unit_price: Decimal` as required parameter
- [ ] Purchase record created atomically within `add_to_inventory()`
- [ ] `InventoryItem.purchase_id` set to link records
- [ ] `InventoryItem.unit_cost` populated from `unit_price`
- [ ] Single session transaction (both records or neither)
- [ ] `purchase_date` defaults to today if not provided
- [ ] Unit tests verify Purchase creation and linkage

### 3. UI Updates (WP03)

- [ ] Supplier dropdown exists in Add Inventory dialog
- [ ] Dropdown populated from `get_active_suppliers()`
- [ ] Suppliers sorted alphabetically by display_name
- [ ] Price entry field exists with decimal validation
- [ ] Price hint label updates dynamically on supplier selection
- [ ] `on_supplier_change` callback fetches price suggestions
- [ ] Price hint format correct: "(last paid: $X.XX on YYYY-MM-DD)"
- [ ] Fallback price hint includes supplier name: "(last paid: $X.XX at Supplier on YYYY-MM-DD)"
- [ ] Zero-price shows confirmation warning (CTkMessagebox)
- [ ] Negative price shows validation error, prevents submission
- [ ] Dialog submission includes `supplier_id` and `unit_price`

### 4. Migration Scripts (WP04)

- [ ] `f028_migration.py` exists in `src/services/migration/`
- [ ] `f028_validation.py` exists in `src/services/migration/`
- [ ] Migration finds/creates "Unknown" supplier (state='XX')
- [ ] Migration creates Purchase records for InventoryItems with NULL purchase_id
- [ ] Migration sets InventoryItem.purchase_id and unit_cost
- [ ] Validation confirms no NULL purchase_id after migration
- [ ] Validation confirms FK integrity (product_id match)

### 5. FIFO and Testing (WP05)

- [ ] FIFO in `consume_fifo()` uses `InventoryItem.unit_cost`
- [ ] `unit_cost` populated from Purchase.unit_price via add_to_inventory
- [ ] Integration test exists for FIFO with purchase-linked inventory
- [ ] Purchase history queries work correctly (sorted by date DESC)
- [ ] All existing tests pass (1067+ tests)
- [ ] No broken tests from signature changes

### 6. Model Updates

- [ ] `Purchase.unit_cost` property exists (alias for `unit_price`)
- [ ] `Purchase.total_cost` property exists (computed: `unit_price * quantity_purchased`)
- [ ] `Purchase` constructor uses `unit_price` not `unit_cost`
- [ ] Test files create Purchase with `unit_price` field

### 7. Test Updates Pattern

- [ ] Tests using `add_to_inventory()` include `supplier_id` parameter
- [ ] Tests using `add_to_inventory()` include `unit_price` parameter (Decimal)
- [ ] `sample_supplier` or `test_supplier` fixture used where needed
- [ ] No `update_inventory_item(id, {"unit_cost": X})` calls remain (cost comes from Purchase)
- [ ] Purchase creation in tests uses `unit_price` not `unit_cost`
- [ ] Export/import version assertions use "3.5"

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced

# Activate virtual environment
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify modules import correctly
python3 -c "
from src.services.purchase_service import (
    get_last_price_at_supplier,
    get_last_price_any_supplier,
    record_purchase,
    get_purchase_history
)
from src.services.inventory_item_service import add_to_inventory
from src.models.purchase import Purchase
print('All modules import successfully')

# Verify Purchase model has unit_cost property
p = Purchase.__new__(Purchase)
p.unit_price = 5.99
p.quantity_purchased = 2
print(f'unit_cost property: {hasattr(Purchase, \"unit_cost\")}')
"

# Verify price suggestion functions exist
grep -n "def get_last_price_at_supplier" src/services/purchase_service.py
grep -n "def get_last_price_any_supplier" src/services/purchase_service.py

# Verify add_to_inventory signature
grep -A5 "def add_to_inventory" src/services/inventory_item_service.py | head -10

# Verify Purchase model properties
grep -n "def unit_cost\|def total_cost" src/models/purchase.py

# Verify migration scripts exist
ls -la src/services/migration/f028_*.py

# Verify UI components
grep -n "supplier_dropdown\|price_field\|price_hint" src/ui/inventory_tab.py | head -15

# Verify session parameter pattern
grep -n "session=None" src/services/purchase_service.py | head -5
grep -n "session=None" src/services/inventory_item_service.py | head -5

# Verify sample_data.json version
grep '"version"' test_data/sample_data.json

# Run ALL tests to verify no regressions
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -30

# Check specific test files
PYTHONPATH=. python3 -m pytest src/tests/services/test_purchase_service.py -v --tb=short
PYTHONPATH=. python3 -m pytest src/tests/services/test_inventory_item_service.py -v --tb=short
PYTHONPATH=. python3 -m pytest src/tests/services/test_recipe_service.py -v --tb=short

# Check test coverage for purchase_service
PYTHONPATH=. python3 -m pytest src/tests/services/test_purchase_service.py -v --cov=src.services.purchase_service --cov-report=term-missing
```

## Key Implementation Patterns

### Session Management Pattern (per CLAUDE.md)
```python
def get_last_price_at_supplier(product_id: int, supplier_id: int, session=None):
    """Accept optional session parameter."""
    if session is not None:
        return _get_last_price_at_supplier_impl(product_id, supplier_id, session)
    with session_scope() as session:
        return _get_last_price_at_supplier_impl(product_id, supplier_id, session)
```

### add_to_inventory New Signature
```python
def add_to_inventory(
    product_id: int,
    quantity: Decimal,
    supplier_id: int,  # NEW - required
    unit_price: Decimal,  # NEW - required
    purchase_date: Optional[date] = None,
    notes: Optional[str] = None,
    session=None
) -> InventoryItem:
    # Create Purchase record first
    # Create InventoryItem with purchase_id and unit_cost
```

### Purchase Model Properties
```python
class Purchase(BaseModel):
    unit_price = Column(Numeric(10, 4), nullable=False)  # Stored column

    @property
    def unit_cost(self) -> Decimal:
        """Alias for unit_price (backward compatibility)."""
        return self.unit_price

    @property
    def total_cost(self) -> Decimal:
        """Computed total cost."""
        return self.unit_price * Decimal(str(self.quantity_purchased))
```

### Test Fixture Pattern
```python
@pytest.fixture
def sample_supplier(test_db):
    """Create a test supplier for F028."""
    from src.services import supplier_service
    result = supplier_service.create_supplier(
        name="Test Supplier",
        city="Boston",
        state="MA",
        zip_code="02101",
    )
    class SupplierObj:
        def __init__(self, data):
            self.id = data["id"]
    return SupplierObj(result)
```

### Test add_to_inventory Pattern
```python
# OLD (broken):
lot = inventory_item_service.add_to_inventory(
    product_id=product.id, quantity=Decimal("5.0"), purchase_date=date(2025, 1, 1)
)
inventory_item_service.update_inventory_item(lot.id, {"unit_cost": 0.10})

# NEW (correct):
lot = inventory_item_service.add_to_inventory(
    product_id=product.id, quantity=Decimal("5.0"),
    supplier_id=sample_supplier.id, unit_price=Decimal("0.10"),
    purchase_date=date(2025, 1, 1)
)
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/028-purchase-tracking-enhanced/docs/code-reviews/cursor-F028-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 028 - Purchase Tracking & Enhanced Costing

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 028-purchase-tracking-enhanced
**Branch:** 028-purchase-tracking-enhanced

## Summary

[Brief overview of findings]

## Verification Results

### Module Import Validation
- purchase_service.py (price suggestion functions): [PASS/FAIL]
- inventory_item_service.py (add_to_inventory update): [PASS/FAIL]
- purchase.py (unit_cost property): [PASS/FAIL]
- inventory_tab.py (UI updates): [PASS/FAIL]
- f028_migration.py: [PASS/FAIL]
- f028_validation.py: [PASS/FAIL]

### Test Results
- Full test suite: [X passed, Y skipped, Z failed]
- Purchase service tests: [X passed, Y failed]
- Inventory item service tests: [X passed, Y failed]
- Recipe service tests: [X passed, Y failed]

### Service Coverage
- purchase_service: [XX%]
- inventory_item_service: [XX%]

### Code Pattern Validation
- Session parameter pattern: [present/missing in which files]
- add_to_inventory signature updated: [correct/issues found]
- Purchase.unit_cost property: [present/missing]
- Purchase.total_cost property: [present/missing]
- Test fixtures (sample_supplier): [present where needed/missing]

## Findings

### Critical Issues
[Any blocking issues that must be fixed]

### Warnings
[Non-blocking concerns]

### Observations
[General observations about code quality]

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/services/purchase_service.py | [status] | [notes] |
| src/services/inventory_item_service.py | [status] | [notes] |
| src/services/recipe_service.py | [status] | [notes] |
| src/models/purchase.py | [status] | [notes] |
| src/ui/inventory_tab.py | [status] | [notes] |
| src/services/migration/f028_migration.py | [status] | [notes] |
| src/services/migration/f028_validation.py | [status] | [notes] |
| src/tests/services/test_recipe_service.py | [status] | [notes] |
| src/tests/services/test_production_service.py | [status] | [notes] |
| src/tests/services/test_packaging_service.py | [status] | [notes] |
| src/tests/services/test_product_recommendation_service.py | [status] | [notes] |
| src/tests/test_models.py | [status] | [notes] |
| test_data/sample_data.json | [status] | [notes] |

## Architecture Assessment

### Layered Architecture
[Assessment of UI -> Services -> Models dependency flow]

### Session Management
[Assessment of session=None parameter pattern per CLAUDE.md]

### FIFO Cost Flow
[Assessment of Purchase.unit_price -> InventoryItem.unit_cost -> consume_fifo() flow]

### Backward Compatibility
[Assessment of unit_cost property alias, nullable purchase_id for migration]

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: Supplier dropdown in Add Inventory | [PASS/FAIL] | [evidence] |
| FR-002: Supplier sorted alphabetically | [PASS/FAIL] | [evidence] |
| FR-003: Price entry field with validation | [PASS/FAIL] | [evidence] |
| FR-004: Price suggestion on supplier select | [PASS/FAIL] | [evidence] |
| FR-005: Fallback price (any supplier) | [PASS/FAIL] | [evidence] |
| FR-006: Price hint format correct | [PASS/FAIL] | [evidence] |
| FR-007: Zero-price confirmation warning | [PASS/FAIL] | [evidence] |
| FR-008: Negative price validation error | [PASS/FAIL] | [evidence] |
| FR-009: Purchase record created with inventory | [PASS/FAIL] | [evidence] |
| FR-010: FIFO uses purchase-linked unit_cost | [PASS/FAIL] | [evidence] |
| FR-011: Migration links existing inventory | [PASS/FAIL] | [evidence] |
| FR-012: Migration creates Unknown supplier | [PASS/FAIL] | [evidence] |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Price Suggestion Functions | [PASS/FAIL] | [notes] |
| WP02: Inventory-Purchase Integration | [PASS/FAIL] | [notes] |
| WP03: UI Supplier Dropdown and Price Entry | [PASS/FAIL] | [notes] |
| WP04: Migration and Validation Scripts | [PASS/FAIL] | [notes] |
| WP05: FIFO Verification and Testing | [PASS/FAIL] | [notes] |

## Test Coverage Assessment

| Test File | Tests | Coverage | Notes |
|-----------|-------|----------|-------|
| test_purchase_service.py | [count] | [%] | [notes] |
| test_inventory_item_service.py | [count] | [%] | [notes] |
| test_recipe_service.py | [count] | N/A | [notes] |
| test_production_service.py | [count] | N/A | [notes] |
| test_packaging_service.py | [count] | N/A | [notes] |
| test_product_recommendation_service.py | [count] | N/A | [notes] |
| test_models.py | [count] | N/A | [notes] |

## Migration Script Assessment

| Check | Status | Notes |
|-------|--------|-------|
| Unknown supplier created (state=XX) | [PASS/FAIL] | [notes] |
| Purchases from inventory_items | [PASS/FAIL] | [notes] |
| purchase_id FK linkage | [PASS/FAIL] | [notes] |
| unit_cost populated | [PASS/FAIL] | [notes] |
| Validation confirms no NULL purchase_id | [PASS/FAIL] | [notes] |
| FK integrity check | [PASS/FAIL] | [notes] |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing with pytest-cov for coverage
- The worktree is isolated from main branch at `.worktrees/028-purchase-tracking-enhanced`
- Layered architecture: UI -> Services -> Models -> Database
- Session management pattern: functions accept `session=None` per CLAUDE.md
- This feature updates the Purchase model and inventory workflow
- `unit_price` is the stored column; `unit_cost` is a backward-compatible property alias
- `total_cost` is a computed property, not stored
- Migration strategy: create Purchase records for existing InventoryItems with NULL purchase_id
- Unknown supplier uses state="XX" (intentionally invalid)
- 70%+ coverage target for service layer
- All existing tests must pass (no regressions) - currently 1067 passed, 12 skipped
- Export/import version is "3.5"
