# Work Packages: Product Catalog Management

**Inputs**: Design documents from `kitty-specs/027-product-catalog-management/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, quickstart.md

**Tests**: Unit tests required for service layer (>70% coverage target per Constitution IV).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Development Approach**: Sequential with review gates - complete each phase before starting next.

---

## Phase 1: Schema & Models

### Work Package WP01: Supplier Model (Priority: P0)

**Goal**: Create Supplier SQLAlchemy model with all attributes, constraints, and indexes.
**Independent Test**: Model imports correctly; can create/query suppliers in test database.
**Prompt**: `tasks/planned/WP01-supplier-model.md`

#### Included Subtasks
- [X] T001 Create `src/models/supplier.py` with Supplier class inheriting BaseModel
- [X] T002 Add all columns: name, street_address, city, state, zip_code, notes, is_active
- [X] T003 Add check constraints for state (uppercase, 2 chars)
- [X] T004 Add indexes: idx_supplier_name_city, idx_supplier_active
- [X] T005 Update `src/models/__init__.py` to export Supplier
- [X] T006 Write basic model tests in `src/tests/models/test_supplier_model.py`

#### Implementation Notes
- Follow existing BaseModel pattern (includes id, uuid, created_at, updated_at)
- State constraint: `CheckConstraint("state = UPPER(state) AND LENGTH(state) = 2")`
- is_active defaults to True for soft delete pattern

#### Dependencies
- None (starting package)

#### Risks & Mitigations
- State validation edge cases → test with various inputs

---

### Work Package WP02: Purchase Model & Product Updates (Priority: P0)

**Goal**: Create Purchase model and add new columns to Product and InventoryAddition.
**Independent Test**: All models import correctly; relationships validate; existing tests pass.
**Prompt**: `tasks/planned/WP02-purchase-model-and-product-updates.md`

#### Included Subtasks
- [X] T007 Create `src/models/purchase.py` with Purchase class
- [X] T008 Add Purchase columns: product_id, supplier_id, purchase_date, unit_price, quantity_purchased, notes
- [X] T009 Add Purchase FK relationships with RESTRICT on delete
- [X] T010 Add Purchase indexes: product, supplier, date, product_date composite
- [X] T011 [P] Modify `src/models/product.py`: add preferred_supplier_id (FK, SET NULL), is_hidden
- [X] T012 [P] Modify `src/models/inventory_addition.py`: add purchase_id (FK, RESTRICT)
- [X] T013 Update `src/models/__init__.py` to export Purchase
- [X] T014 Write model tests in `src/tests/models/test_purchase_model.py`
- [X] T015 Update existing test fixtures to handle new columns

#### Implementation Notes
- Purchase has no updated_at (immutable after creation per data-model.md)
- Product.preferred_supplier_id: nullable FK with ON DELETE SET NULL
- InventoryAddition.purchase_id: required FK (migration will populate)
- Run full test suite after changes to catch regressions

#### Parallel Opportunities
- T011 (Product updates) and T012 (InventoryAddition updates) can proceed in parallel

#### Dependencies
- Depends on WP01 (Supplier model must exist for FKs)

#### Risks & Mitigations
- Existing test breakage → T015 addresses fixture updates
- FK constraint errors → ensure Supplier model is imported first

---

## Phase 2: Service Layer

### Work Package WP03: Supplier Service (Priority: P1)

**Goal**: Implement supplier_service.py with full CRUD and soft delete operations.
**Independent Test**: All supplier service tests pass with >70% coverage.
**Prompt**: `tasks/planned/WP03-supplier-service.md`

#### Included Subtasks
- [X] T016 Create `src/services/supplier_service.py` with session pattern
- [X] T017 Implement `create_supplier(name, city, state, zip_code, ...)`
- [X] T018 Implement `get_supplier(supplier_id)` and `get_supplier_by_uuid(uuid)`
- [X] T019 Implement `get_all_suppliers(include_inactive=False)`
- [X] T020 Implement `get_active_suppliers()` for dropdowns
- [X] T021 Implement `update_supplier(supplier_id, **kwargs)`
- [X] T022 Implement `deactivate_supplier(supplier_id)` with cascade to products
- [X] T023 Implement `reactivate_supplier(supplier_id)`
- [X] T024 Implement `delete_supplier(supplier_id)` with dependency check
- [X] T025 Add SupplierNotFoundError to `src/services/exceptions.py`
- [X] T026 Update `src/services/__init__.py` to export supplier_service
- [X] T027 Write tests in `src/tests/services/test_supplier_service.py`

#### Implementation Notes
- All functions MUST accept `session: Optional[Session] = None` per CLAUDE.md
- deactivate_supplier must clear preferred_supplier_id on affected products (FR-009)
- delete_supplier must check for purchases before allowing deletion

#### Dependencies
- Depends on WP01 (Supplier model)

#### Risks & Mitigations
- Session detachment → follow pattern strictly, pass session to nested calls

---

### Work Package WP04: Product Catalog Service (Priority: P1)

**Goal**: Implement product_catalog_service.py with CRUD, filtering, purchase history.
**Independent Test**: All product service tests pass with >70% coverage.
**Prompt**: `tasks/planned/WP04-product-catalog-service.md`

#### Included Subtasks
- [X] T028 Create `src/services/product_catalog_service.py` with session pattern
- [X] T029 Implement `get_products(include_hidden=False, ingredient_id=None, category=None, supplier_id=None, search=None)`
- [X] T030 Implement `get_product_with_last_price(product_id)`
- [X] T031 Implement `create_product(product_name, ingredient_id, package_unit, package_quantity, ...)`
- [X] T032 Implement `update_product(product_id, **kwargs)`
- [X] T033 Implement `hide_product(product_id)` and `unhide_product(product_id)`
- [X] T034 Implement `delete_product(product_id)` with dependency check
- [X] T035 Implement `get_purchase_history(product_id)` sorted by date DESC
- [X] T036 Implement `create_purchase(product_id, supplier_id, purchase_date, unit_price, quantity)`
- [X] T037 Implement `get_products_by_category(category)` via ingredient join
- [X] T038 Write tests in `src/tests/services/test_product_catalog_service.py`

#### Implementation Notes
- All functions MUST accept `session: Optional[Session] = None`
- get_products returns dicts with last_price from most recent purchase
- delete_product checks for purchases AND inventory before allowing
- Search is case-insensitive LIKE on product_name

#### Parallel Opportunities
- Can start T028-T034 while WP03 completes (stub supplier lookups initially)

#### Dependencies
- Depends on WP02 (Purchase model, Product updates)
- Depends on WP03 (for supplier lookups)

#### Risks & Mitigations
- Performance on large catalogs → add appropriate indexes (done in WP02)

---

## Phase 3: UI Layer

### Work Package WP05: Products Tab Frame (Priority: P1)

**Goal**: Create main Products tab with grid, filters, and search.
**Independent Test**: Tab renders; grid displays products; filters work.
**Prompt**: `tasks/planned/WP05-products-tab-frame.md`

#### Included Subtasks
- [X] T039 Create `src/ui/products_tab.py` extending CTkFrame
- [X] T040 Add toolbar: Add Product button, Manage Suppliers button
- [X] T041 Add filter controls: Ingredient dropdown, Category dropdown, Supplier dropdown
- [X] T042 Add search box with real-time filtering
- [X] T043 Add "Show Hidden" checkbox
- [X] T044 Create product grid (Treeview) with columns: Name, Ingredient, Category, Supplier, Last Price, Last Purchase
- [X] T045 Implement grid refresh from product_catalog_service
- [X] T046 Add double-click handler to open product detail
- [X] T047 Add context menu: Edit, Hide/Unhide, Delete
- [X] T048 Modify `src/ui/main_window.py` to add Products tab

#### Implementation Notes
- Follow existing tab patterns (inventory_tab.py, recipes_tab.py)
- Grid uses CTkTreeview or equivalent from existing codebase
- Hidden products displayed grayed out when "Show Hidden" checked
- Last Price column shows "N/A" if no purchase history

#### Dependencies
- Depends on WP04 (product_catalog_service)

#### Risks & Mitigations
- Grid performance with many products → lazy loading if needed

---

### Work Package WP06: Add Product Dialog (Priority: P1)

**Goal**: Create dialog for adding and editing products.
**Independent Test**: Dialog opens; can create new product; validation works.
**Prompt**: `tasks/planned/WP06-add-product-dialog.md`

#### Included Subtasks
- [X] T049 Create `src/ui/forms/add_product_dialog.py` extending CTkToplevel
- [X] T050 Add form fields: product_name, ingredient dropdown, package_unit, package_quantity
- [X] T051 Add optional preferred_supplier dropdown (active suppliers only)
- [X] T052 Implement ingredient selection auto-populating category display
- [X] T053 Add validation: required fields, positive quantity
- [X] T054 Implement Save button calling product_catalog_service
- [X] T055 Implement Cancel button
- [X] T056 Support edit mode (pre-populate fields from existing product)

#### Implementation Notes
- Follow existing dialog patterns (add_inventory_dialog.py)
- Ingredient dropdown populated from ingredient_service
- Supplier dropdown shows only active suppliers (FR-010)
- Edit mode passed via constructor parameter

#### Parallel Opportunities
- Can develop in parallel with WP07 once WP05 establishes tab frame

#### Dependencies
- Depends on WP04 (product_catalog_service)

#### Risks & Mitigations
- Dropdown population performance → cache ingredient list

---

### Work Package WP07: Product Detail Dialog (Priority: P2)

**Goal**: Create dialog showing product details and purchase history.
**Independent Test**: Dialog opens from grid; shows product info; displays purchase history.
**Prompt**: `tasks/planned/WP07-product-detail-dialog.md`

#### Included Subtasks
- [X] T057 Create `src/ui/forms/product_detail_dialog.py` extending CTkToplevel
- [X] T058 Add product info section: name, ingredient, category, package info, preferred supplier
- [X] T059 Add Edit button opening AddProductDialog in edit mode
- [X] T060 Add Hide/Unhide button with state toggle
- [X] T061 Add Delete button with confirmation and dependency check
- [X] T062 Create purchase history grid (date, supplier, price, quantity)
- [X] T063 Show "No purchase history" message when empty
- [X] T064 Sort purchase history by date descending (newest first)

#### Implementation Notes
- Purchase history from product_catalog_service.get_purchase_history()
- Delete button disabled/hidden if product has purchases or inventory
- Hide button changes to Unhide when viewing hidden product

#### Parallel Opportunities
- Can develop in parallel with WP06

#### Dependencies
- Depends on WP04 (product_catalog_service)

#### Risks & Mitigations
- Large purchase history → pagination if needed (likely not for holiday baking scale)

---

## Phase 4: Integration & Migration

### Work Package WP08: Import/Export Updates (Priority: P2)

**Goal**: Update import_export_service to handle Supplier and Purchase entities.
**Independent Test**: Export includes new entities; import restores them correctly.
**Prompt**: `tasks/planned/WP08-import-export-updates.md`

#### Included Subtasks
- [X] T065 Update `export_all_to_json_v3()` to include suppliers
- [X] T066 Update `export_all_to_json_v3()` to include purchases
- [X] T067 Update `export_all_to_json_v3()` to include new product fields (preferred_supplier_id, is_hidden)
- [X] T068 Update `export_all_to_json_v3()` to include new inventory_addition fields (purchase_id)
- [X] T069 Update `import_all_from_json_v3()` to handle suppliers
- [X] T070 Update `import_all_from_json_v3()` to handle purchases
- [X] T071 Update `import_all_from_json_v3()` to handle new product/inventory fields
- [X] T072 Ensure import order: suppliers → products → purchases → inventory_additions
- [X] T073 Write integration tests in `src/tests/integration/test_product_catalog.py`

#### Implementation Notes
- Import order critical for FK resolution
- Handle missing purchase_id gracefully during transition period
- Preserve existing import/export functionality for backward compatibility

#### Dependencies
- Depends on WP02 (models), WP04 (services)

#### Risks & Mitigations
- Import order issues → explicit ordering in import function

---

### Work Package WP09: Migration Transformation (Priority: P2)

**Goal**: Create migration script to transform existing data for new schema.
**Independent Test**: Migration preserves all data; creates Unknown supplier; links purchases.
**Prompt**: `tasks/planned/WP09-migration-transformation.md`

#### Included Subtasks
- [X] T074 Create migration script `scripts/migrate_f027.py`
- [X] T075 Export current data to JSON backup
- [X] T076 Create "Unknown" supplier for historical data
- [X] T077 Transform inventory_additions: create Purchase records from price_paid
- [X] T078 Link inventory_additions to new Purchase records
- [X] T079 Add is_hidden=False to all products
- [X] T080 Validate transformation: count records, verify FK integrity
- [X] T081 Create rollback instructions in script comments
- [X] T082 Write migration validation tests

#### Implementation Notes
- Per Constitution VI: export → delete DB → recreate → import transformed
- Unknown supplier: name="Unknown", city="Unknown", state="XX", zip="00000"
- Each inventory_addition with price_paid becomes one Purchase record
- purchase_date = addition_date, unit_price = price_paid, quantity_purchased = 1

#### Dependencies
- Depends on WP08 (import/export must handle new entities)

#### Risks & Mitigations
- Data loss → backup before migration; validate counts before/after
- Null price_paid → default to 0.00 with warning log

---

## Dependency & Execution Summary

```
Phase 1 (Sequential):
  WP01 → WP02

Phase 2 (Can start WP03/WP04 in parallel after Phase 1):
  WP03 ──┐
         ├──→ Phase 3
  WP04 ──┘

Phase 3 (WP06/WP07 can parallel after WP05):
  WP05 → WP06 ──┐
         WP07 ──┴──→ Phase 4

Phase 4 (Sequential):
  WP08 → WP09
```

**MVP Scope**: WP01-WP06 (Models, Services, Products Tab, Add Product Dialog)
- Delivers core product management capability
- WP07 (Detail Dialog) and WP08-WP09 (Migration) can follow

---

## Subtask Index (Reference)

| Subtask | Summary | Work Package | Phase | Parallel? |
|---------|---------|--------------|-------|-----------|
| T001-T006 | Supplier model | WP01 | 1 | No |
| T007-T015 | Purchase model & Product updates | WP02 | 1 | T011,T012 |
| T016-T027 | Supplier service | WP03 | 2 | No |
| T028-T038 | Product catalog service | WP04 | 2 | No |
| T039-T048 | Products tab frame | WP05 | 3 | No |
| T049-T056 | Add product dialog | WP06 | 3 | Yes (with WP07) |
| T057-T064 | Product detail dialog | WP07 | 3 | Yes (with WP06) |
| T065-T073 | Import/export updates | WP08 | 4 | No |
| T074-T082 | Migration transformation | WP09 | 4 | No |

**Total**: 82 subtasks across 9 work packages in 4 phases
