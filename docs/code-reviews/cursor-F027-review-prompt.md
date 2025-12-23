# Cursor Code Review Prompt - Feature 027: Product Catalog Management

## Role

You are a senior software engineer performing an independent code review of Feature 027 (product-catalog-management). This feature enables bakers to manage a product catalog with supplier tracking, purchase history, and product visibility controls.

## Feature Summary

**Core Changes:**
1. New `Supplier` model for tracking stores/vendors
2. New `Purchase` model for recording purchase transactions
3. Updated `Product` model with `is_hidden` and `preferred_supplier_id` fields
4. Updated `InventoryItem` model with `purchase_id` FK
5. New `supplier_service.py` with CRUD and soft-delete operations
6. New `product_catalog_service.py` with search, filter, and purchase history
7. New `ProductsTab` UI with searchable/filterable grid
8. New `AddProductDialog` and `ProductDetailDialog` for CRUD operations
9. Updated `import_export_service.py` for new entities
10. Migration script `migrate_f027.py` for existing data transformation

**Scope:**
- Model layer: `supplier.py`, `purchase.py`, `product.py`, `inventory_item.py`
- Service layer: `supplier_service.py`, `product_catalog_service.py`, `import_export_service.py`
- UI layer: `products_tab.py`, `add_product_dialog.py`, `product_detail_dialog.py`, `main_window.py`
- Migration: `scripts/migrate_f027.py`
- Tests: `test_supplier_model.py`, `test_purchase_model.py`, `test_supplier_service.py`, `test_product_catalog_service.py`, `test_import_export_027.py`, `test_f027_migration.py`

## Files to Review

### Model Layer (WP01-WP02)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/models/supplier.py`
  - New model with `name`, `city`, `state`, `zip_code`, `street_address`, `notes`, `is_active`
  - `display_name` property returning "Name (City, ST)"
  - `purchases` relationship to Purchase model

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/models/purchase.py`
  - New model with `product_id`, `supplier_id`, `purchase_date`, `unit_price`, `quantity_purchased`, `notes`
  - FKs with ON DELETE RESTRICT for both product and supplier
  - Relationships to Product and Supplier

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/models/product.py`
  - New `is_hidden` column (Boolean, default False)
  - New `preferred_supplier_id` FK with ON DELETE SET NULL
  - `preferred_supplier` relationship to Supplier

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/models/inventory_item.py`
  - New `purchase_id` FK with ON DELETE RESTRICT (nullable for migration)
  - `purchase` relationship to Purchase

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/models/__init__.py`
  - Verify `Supplier` and `Purchase` are exported

### Service Layer (WP03-WP04)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/services/supplier_service.py`
  - `create_supplier(name, city, state, zip_code, ...)` - create new supplier
  - `get_supplier(supplier_id)` - get by ID
  - `get_all_suppliers()` - list all suppliers
  - `get_active_suppliers()` - list only is_active=True
  - `update_supplier(supplier_id, ...)` - update fields
  - `deactivate_supplier(supplier_id)` - soft delete (is_active=False)
  - `reactivate_supplier(supplier_id)` - restore (is_active=True)
  - `delete_supplier(supplier_id)` - permanent delete (raises if has purchases)
  - `has_purchases(supplier_id)` - check for dependencies

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/services/product_catalog_service.py`
  - `create_product(...)` - create new product
  - `get_product(product_id)` - get by ID
  - `get_product_with_last_price(product_id)` - get with latest purchase price
  - `get_all_products(include_hidden=False)` - list products with optional hidden
  - `search_products(query, ...)` - search by name with filters
  - `update_product(product_id, ...)` - update fields
  - `hide_product(product_id)` - soft delete (is_hidden=True)
  - `unhide_product(product_id)` - restore (is_hidden=False)
  - `delete_product(product_id)` - permanent delete (raises if has dependencies)
  - `has_dependencies(product_id)` - check for purchases/inventory
  - `get_purchase_history(product_id)` - list purchases sorted by date DESC
  - `record_purchase(product_id, supplier_id, ...)` - create Purchase record

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/services/import_export_service.py`
  - `export_suppliers_to_json()` - export Supplier records
  - `import_suppliers_from_json(data)` - import Supplier records
  - `export_purchases_to_json()` - export Purchase records with supplier_id FK
  - `import_purchases_from_json(data)` - import Purchase records
  - Version bumped to 3.5 with suppliers/purchases support

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/services/__init__.py`
  - Verify `supplier_service` and `product_catalog_service` are exported

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/services/exceptions.py`
  - Check for any new exception classes

### UI Layer (WP05-WP07)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/ui/products_tab.py`
  - Products grid with columns: Name, Brand, Ingredient, Category, Preferred Supplier, Last Price
  - Search box (by product name)
  - Filter by Category dropdown
  - Filter by Supplier dropdown
  - "Show Hidden" checkbox
  - "Add Product" button
  - Double-click opens ProductDetailDialog
  - Grid refresh on product changes

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/ui/forms/add_product_dialog.py`
  - Add/Edit mode based on `product_id` parameter
  - Fields: Product Name, Brand (optional), Package Unit, Package Quantity, Ingredient dropdown, Preferred Supplier dropdown
  - Category auto-populated from Ingredient selection
  - Validation for required fields
  - Save creates/updates product

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/ui/forms/product_detail_dialog.py`
  - Display product information (name, brand, ingredient, category, package, supplier, last price)
  - Edit button opens AddProductDialog in edit mode
  - Hide/Unhide button toggles is_hidden
  - Delete button with dependency check (offers hide if blocked)
  - Purchase history grid sorted by date (newest first)
  - Empty state message when no purchases

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/ui/main_window.py`
  - Verify Products tab is added to main window

### Migration Script (WP09)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/scripts/migrate_f027.py`
  - `--dry-run` mode for safe preview
  - `backup_current_data()` - exports to JSON before changes
  - `create_unknown_supplier()` - creates Unknown supplier (ID=1, state="XX")
  - `transform_inventory_to_purchases()` - creates Purchase from inventory_items with unit_cost
  - `link_items_to_purchases()` - sets purchase_id on inventory_items
  - `initialize_product_fields()` - sets is_hidden=False, preferred_supplier_id=None
  - `validate_transformation()` - FK integrity and record count checks
  - `execute_migration()` - destructive operation: delete DB, recreate, import
  - Rollback instructions in docstring

### Test Files

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/tests/models/test_supplier_model.py`
  - Model tests for Supplier

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/tests/models/test_purchase_model.py`
  - Model tests for Purchase

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/tests/services/test_supplier_service.py`
  - Unit tests for supplier_service

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/tests/services/test_product_catalog_service.py`
  - Unit tests for product_catalog_service

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/tests/services/test_import_export_service.py`
  - Tests for import/export with new entities

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/tests/integration/test_import_export_027.py`
  - Integration tests for F027 import/export

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/tests/migration/__init__.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/src/tests/migration/test_f027_migration.py`
  - 27 unit tests for migration transformation functions

### Specification Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/kitty-specs/027-product-catalog-management/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/kitty-specs/027-product-catalog-management/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/kitty-specs/027-product-catalog-management/data-model.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management/kitty-specs/027-product-catalog-management/quickstart.md`

## Review Checklist

### 1. Model Layer - Schema Changes

- [ ] `Supplier` model exists with columns: id, uuid, name, city, state, zip_code, street_address, notes, is_active, created_at, updated_at
- [ ] `Supplier.display_name` property returns "Name (City, ST)"
- [ ] `Supplier.purchases` relationship to Purchase exists
- [ ] `Purchase` model exists with columns: id, uuid, product_id, supplier_id, purchase_date, unit_price, quantity_purchased, notes, created_at, updated_at
- [ ] `Purchase.product_id` FK has ON DELETE RESTRICT
- [ ] `Purchase.supplier_id` FK has ON DELETE RESTRICT
- [ ] `Product.is_hidden` column exists (Boolean, default False)
- [ ] `Product.preferred_supplier_id` FK exists with ON DELETE SET NULL
- [ ] `Product.preferred_supplier` relationship to Supplier exists
- [ ] `InventoryItem.purchase_id` FK exists (nullable, ON DELETE RESTRICT)
- [ ] `InventoryItem.purchase` relationship to Purchase exists
- [ ] `Supplier` and `Purchase` exported from `src/models/__init__.py`

### 2. Supplier Service - Core Functions

- [ ] `create_supplier()` creates supplier with all fields
- [ ] `get_supplier()` returns supplier by ID
- [ ] `get_all_suppliers()` returns all suppliers
- [ ] `get_active_suppliers()` returns only is_active=True suppliers
- [ ] `update_supplier()` updates specified fields
- [ ] `deactivate_supplier()` sets is_active=False and clears preferred_supplier_id on products
- [ ] `reactivate_supplier()` sets is_active=True
- [ ] `delete_supplier()` removes supplier (raises ValueError if has purchases)
- [ ] `has_purchases()` returns True if supplier has any purchases
- [ ] All functions accept optional `session=None` parameter (per CLAUDE.md)

### 3. Product Catalog Service - Core Functions

- [ ] `create_product()` creates product with all fields
- [ ] `get_product()` returns product by ID
- [ ] `get_product_with_last_price()` returns product with last purchase price
- [ ] `get_all_products()` returns products, optionally including hidden
- [ ] `search_products()` filters by name, category, supplier, include_hidden
- [ ] `update_product()` updates specified fields
- [ ] `hide_product()` sets is_hidden=True
- [ ] `unhide_product()` sets is_hidden=False
- [ ] `delete_product()` removes product (raises ValueError if has dependencies)
- [ ] `has_dependencies()` checks for purchases or inventory items
- [ ] `get_purchase_history()` returns purchases sorted by date DESC
- [ ] `record_purchase()` creates Purchase record
- [ ] All functions accept optional `session=None` parameter (per CLAUDE.md)

### 4. Import/Export Service Updates

- [ ] `export_suppliers_to_json()` exports all suppliers
- [ ] `import_suppliers_from_json()` imports suppliers with dedup handling
- [ ] `export_purchases_to_json()` exports purchases with supplier_id FK
- [ ] `import_purchases_from_json()` imports purchases, resolving FKs
- [ ] Export version is 3.5 or higher
- [ ] Backward compatibility: import handles missing suppliers/purchases keys
- [ ] Products export includes is_hidden and preferred_supplier_id
- [ ] InventoryItems export includes purchase_id

### 5. UI - Products Tab

- [ ] Products grid displays with appropriate columns
- [ ] Search by product name works (case-insensitive partial match)
- [ ] Filter by Category dropdown works
- [ ] Filter by Supplier dropdown shows only active suppliers
- [ ] "Show Hidden" checkbox toggles hidden product visibility
- [ ] Hidden products display with visual distinction (grayed out)
- [ ] "Add Product" button opens AddProductDialog
- [ ] Double-click product opens ProductDetailDialog
- [ ] Grid refreshes after add/edit/hide/delete operations

### 6. UI - Add Product Dialog

- [ ] Dialog title changes for Add vs Edit mode
- [ ] All form fields present: Product Name*, Brand, Package Unit*, Package Quantity*, Ingredient*, Preferred Supplier
- [ ] Required fields marked with asterisk
- [ ] Ingredient dropdown populated from ingredient_service
- [ ] Category auto-populates when ingredient selected
- [ ] Supplier dropdown shows only active suppliers
- [ ] Validation prevents empty required fields
- [ ] Validation prevents invalid package quantity
- [ ] Save creates product in add mode
- [ ] Save updates product in edit mode
- [ ] Cancel closes without saving
- [ ] Edit mode pre-populates all fields

### 7. UI - Product Detail Dialog

- [ ] Product info section displays all fields correctly
- [ ] Edit button opens AddProductDialog in edit mode
- [ ] Hide/Unhide button toggles is_hidden and updates button text
- [ ] Delete button confirms before action
- [ ] Delete blocked with message if product has dependencies
- [ ] Delete prompts to hide instead if blocked
- [ ] Purchase history grid displays when purchases exist
- [ ] Purchase history sorted by date (newest first)
- [ ] "No purchase history" message when empty
- [ ] Close button closes dialog

### 8. Migration Script

- [ ] `--dry-run` flag shows what would happen without changes
- [ ] Backup created BEFORE any transformation
- [ ] Unknown supplier created with ID=1 and state="XX"
- [ ] Purchases created from inventory_items with unit_cost
- [ ] inventory_items linked to new Purchase records via purchase_id
- [ ] Products get is_hidden=False and preferred_supplier_id=None
- [ ] Validation checks record counts and FK integrity
- [ ] Validation runs BEFORE any destructive changes
- [ ] Rollback instructions documented in docstring
- [ ] execute_migration() deletes DB, recreates schema, imports data

### 9. Test Coverage

- [ ] Supplier model tests exist and pass
- [ ] Purchase model tests exist and pass
- [ ] supplier_service tests exist and pass (>70% coverage)
- [ ] product_catalog_service tests exist and pass (>70% coverage)
- [ ] Import/export integration tests for F027 entities pass
- [ ] Migration transformation tests pass (27 tests)
- [ ] All tests pass with no failures

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/027-product-catalog-management

# Activate virtual environment
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify modules import correctly
python3 -c "
from src.models.supplier import Supplier
from src.models.purchase import Purchase
from src.models.product import Product
from src.models.inventory_item import InventoryItem
from src.services.supplier_service import (
    create_supplier, get_supplier, get_all_suppliers, get_active_suppliers,
    update_supplier, deactivate_supplier, reactivate_supplier, delete_supplier,
    has_purchases
)
from src.services.product_catalog_service import (
    create_product, get_product, get_product_with_last_price, get_all_products,
    search_products, update_product, hide_product, unhide_product, delete_product,
    has_dependencies, get_purchase_history, record_purchase
)
print('All modules import successfully')
"

# Verify Supplier model
grep -n "class Supplier" src/models/supplier.py
grep -n "is_active\|display_name" src/models/supplier.py | head -10

# Verify Purchase model
grep -n "class Purchase" src/models/purchase.py
grep -n "product_id\|supplier_id\|ON DELETE" src/models/purchase.py | head -10

# Verify Product updates
grep -n "is_hidden\|preferred_supplier_id" src/models/product.py | head -10

# Verify InventoryItem updates
grep -n "purchase_id" src/models/inventory_item.py | head -5

# Verify supplier_service functions
grep -n "^def " src/services/supplier_service.py | head -15

# Verify product_catalog_service functions
grep -n "^def " src/services/product_catalog_service.py | head -20

# Verify session parameter pattern
grep -n "session=None" src/services/supplier_service.py | head -5
grep -n "session=None" src/services/product_catalog_service.py | head -5

# Verify import/export version
grep -n "version" src/services/import_export_service.py | head -5

# Verify import/export handles suppliers and purchases
grep -n "suppliers\|purchases" src/services/import_export_service.py | head -15

# Verify UI files exist
ls -la src/ui/products_tab.py
ls -la src/ui/forms/add_product_dialog.py
ls -la src/ui/forms/product_detail_dialog.py

# Verify migration script
grep -n "^def " scripts/migrate_f027.py | head -15

# Run all model tests
python3 -m pytest src/tests/models/test_supplier_model.py src/tests/models/test_purchase_model.py -v

# Run all service tests
python3 -m pytest src/tests/services/test_supplier_service.py src/tests/services/test_product_catalog_service.py -v

# Run import/export tests
python3 -m pytest src/tests/integration/test_import_export_027.py -v

# Run migration tests
python3 -m pytest src/tests/migration/test_f027_migration.py -v

# Run ALL tests to check for regressions
python3 -m pytest src/tests -v --tb=short 2>&1 | tail -50

# Check test coverage for services
python3 -m pytest src/tests/services/test_supplier_service.py -v --cov=src.services.supplier_service --cov-report=term-missing
python3 -m pytest src/tests/services/test_product_catalog_service.py -v --cov=src.services.product_catalog_service --cov-report=term-missing
```

## Key Implementation Patterns

### Session Management Pattern (per CLAUDE.md)
```python
def some_function(..., session=None):
    """Accept optional session parameter."""
    if session is not None:
        return _impl(..., session)
    with session_scope() as session:
        return _impl(..., session)
```

### Soft Delete Pattern
```python
# For Supplier
def deactivate_supplier(supplier_id, session=None):
    supplier.is_active = False
    # Also clear preferred_supplier_id on products referencing this supplier

# For Product
def hide_product(product_id, session=None):
    product.is_hidden = True
```

### Dependency Check Pattern
```python
def delete_product(product_id, session=None):
    if has_dependencies(product_id, session=session):
        raise ValueError("Cannot delete product with purchase history or inventory")
    # Proceed with delete
```

### Migration Unknown Supplier Pattern
```python
unknown_supplier = {
    "id": 1,  # Reserved ID
    "uuid": "00000000-0000-0000-0000-000000000001",
    "name": "Unknown",
    "state": "XX",  # Intentionally invalid
}
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F027-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 027 - Product Catalog Management

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 027-product-catalog-management
**Branch:** 027-product-catalog-management

## Summary

[Brief overview of findings]

## Verification Results

### Module Import Validation
- supplier.py: [PASS/FAIL]
- purchase.py: [PASS/FAIL]
- product.py (updates): [PASS/FAIL]
- inventory_item.py (updates): [PASS/FAIL]
- supplier_service.py: [PASS/FAIL]
- product_catalog_service.py: [PASS/FAIL]
- import_export_service.py: [PASS/FAIL]
- products_tab.py: [PASS/FAIL]
- add_product_dialog.py: [PASS/FAIL]
- product_detail_dialog.py: [PASS/FAIL]
- migrate_f027.py: [PASS/FAIL]

### Test Results
- Model tests: [X passed, Y failed]
- Service tests: [X passed, Y failed]
- Integration tests: [X passed, Y failed]
- Migration tests: [X passed, Y failed]
- Full test suite: [X passed, Y skipped, Z failed]

### Service Coverage
- supplier_service: [XX%]
- product_catalog_service: [XX%]

### Code Pattern Validation
- Session parameter pattern: [present/missing in which files]
- Soft delete pattern (Supplier.is_active): [present/missing]
- Soft delete pattern (Product.is_hidden): [present/missing]
- Dependency check before delete: [present/missing]
- FK ON DELETE behaviors: [correct/issues found]
- Import/export version: [version number]

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
| src/models/supplier.py | [status] | [notes] |
| src/models/purchase.py | [status] | [notes] |
| src/models/product.py | [status] | [notes] |
| src/models/inventory_item.py | [status] | [notes] |
| src/services/supplier_service.py | [status] | [notes] |
| src/services/product_catalog_service.py | [status] | [notes] |
| src/services/import_export_service.py | [status] | [notes] |
| src/ui/products_tab.py | [status] | [notes] |
| src/ui/forms/add_product_dialog.py | [status] | [notes] |
| src/ui/forms/product_detail_dialog.py | [status] | [notes] |
| scripts/migrate_f027.py | [status] | [notes] |

## Architecture Assessment

### Layered Architecture
[Assessment of UI -> Services -> Models dependency flow]

### Session Management
[Assessment of session=None parameter pattern per CLAUDE.md]

### Error Handling
[Assessment of ValueError for dependency violations]

### Backward Compatibility
[Assessment of default is_hidden=False, nullable FKs for migration]

## User Story Verification

| User Story | Status | Evidence |
|------------|--------|----------|
| US-1: View and search products | [PASS/FAIL] | [evidence] |
| US-2: Add new products | [PASS/FAIL] | [evidence] |
| US-3: Manage suppliers | [PASS/FAIL] | [evidence] |
| US-4: View product details and purchase history | [PASS/FAIL] | [evidence] |
| US-5: Edit products | [PASS/FAIL] | [evidence] |
| US-6: Hide and unhide products | [PASS/FAIL] | [evidence] |
| US-7: Track purchases when adding inventory | [PASS/FAIL] | [evidence] |

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: Product creation | [PASS/FAIL] | [evidence] |
| FR-002: Preferred supplier | [PASS/FAIL] | [evidence] |
| FR-003: Hide products | [PASS/FAIL] | [evidence] |
| FR-004: Prevent delete with history | [PASS/FAIL] | [evidence] |
| FR-005: Delete without dependencies | [PASS/FAIL] | [evidence] |
| FR-006: Filterable product grid | [PASS/FAIL] | [evidence] |
| FR-007: Supplier creation | [PASS/FAIL] | [evidence] |
| FR-008: Deactivate suppliers | [PASS/FAIL] | [evidence] |
| FR-009: Clear preferred_supplier on deactivate | [PASS/FAIL] | [evidence] |
| FR-010: Hide inactive in dropdowns | [PASS/FAIL] | [evidence] |
| FR-011: Purchase record on inventory add | [PASS/FAIL] | [evidence] |
| FR-012: Purchase history display | [PASS/FAIL] | [evidence] |
| FR-013: Last purchase price | [PASS/FAIL] | [evidence] |
| FR-014-018: Filtering/searching | [PASS/FAIL] | [evidence] |
| FR-019-021: Referential integrity | [PASS/FAIL] | [evidence] |

## Test Coverage Assessment

| Test File | Tests | Coverage | Notes |
|-----------|-------|----------|-------|
| test_supplier_model.py | [count] | N/A | [notes] |
| test_purchase_model.py | [count] | N/A | [notes] |
| test_supplier_service.py | [count] | [%] | [notes] |
| test_product_catalog_service.py | [count] | [%] | [notes] |
| test_import_export_027.py | [count] | N/A | [notes] |
| test_f027_migration.py | [count] | N/A | [notes] |

## Migration Script Assessment

| Check | Status | Notes |
|-------|--------|-------|
| Dry-run mode works | [PASS/FAIL] | [notes] |
| Backup created first | [PASS/FAIL] | [notes] |
| Unknown supplier (ID=1, state=XX) | [PASS/FAIL] | [notes] |
| Purchases from inventory_items | [PASS/FAIL] | [notes] |
| purchase_id FK linkage | [PASS/FAIL] | [notes] |
| Product field initialization | [PASS/FAIL] | [notes] |
| Validation before destructive ops | [PASS/FAIL] | [notes] |
| Rollback instructions documented | [PASS/FAIL] | [notes] |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing with pytest-cov for coverage
- The worktree is isolated from main branch
- Layered architecture: UI -> Services -> Models -> Database
- Session management pattern: functions accept `session=None` per CLAUDE.md
- This feature adds two new models (Supplier, Purchase) and updates two existing models (Product, InventoryItem)
- Migration strategy: export-delete-import (per Constitution VI)
- Unknown supplier uses reserved ID=1 and intentionally invalid state="XX"
- 70%+ coverage target for service layer
- All existing tests must pass (no regressions)
