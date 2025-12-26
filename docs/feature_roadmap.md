# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2025-12-26
**Workflow:** Spec-Kitty driven development

---

## Completed Features

| # | Name | Status | Notes |
|---|------|--------|-------|
| 001 | System Health Check | ABANDONED | Scope mismatch - multi-tenant features inappropriate for local desktop app |
| 002 | Phase 4 Services (Part 1) | MERGED | IngredientService, ProductService |
| 003 | Phase 4 Services (Part 2) | MERGED | InventoryItemService, PurchaseService |
| 004 | Phase 4 UI | PARTIAL | ingredients_tab.py, inventory_tab.py complete; **Assembly UI incomplete** |
| 005 | Recipe FIFO Cost Integration | MERGED | RecipeService calculates costs using FIFO from InventoryItemService |
| 006 | Event Planning Restoration | MERGED | Re-enabled Bundle -> Package -> Event chain with Ingredient/Product architecture |
| 007 | Shopping List Product Integration | MERGED | EventService shopping lists with product-aware brand recommendations |
| 008 | Production Tracking | MERGED | Phase 5: Record finished goods production, mark packages assembled/delivered |
| 009 | UI Import/Export | MERGED | File menu import/export dialogs. 7 bug fixes applied 2025-12-04. |
| 010 | User-Friendly Density Input | MERGED | 4-field density model. 8 post-merge bugs fixed 2025-12-05. |
| TD-001 | Schema Cleanup | MERGED | Variant→Product, PantryItem→InventoryItem, dual FK fix, display_name. |
| 011 | Packaging & BOM Foundation | MERGED | Packaging materials in Composition, `is_packaging` flag on Ingredient. |
| 012 | Nested Recipes | MERGED | RecipeComponent model, recursive cost calculation, ingredient aggregation. |
| 013 | Production & Inventory Tracking | MERGED | BatchProductionService, AssemblyService, FIFO consumption ledgers. 51 tests. Bug fixes 2025-12-10. |
| 014 | Production UI | MERGED | Record Production/Assembly dialogs, availability checking, FinishedUnits/FinishedGoods tabs with production actions. |
| 015 | *(skipped)* | - | Spec-kitty assigned 016 due to aborted prior 015 attempt |
| 016 | Event-Centric Production Model | MERGED | Event-production linkage, targets, progress tracking, fulfillment workflow. 65+ service tests. |
| 017 | Reporting & Event Planning | MERGED | CSV exports, event reports, cost analysis, recipient history, dashboard enhancements. |
| 018 | Event Production Dashboard | MERGED | Mission control view, progress visualization, fulfillment tracking, quick actions. |
| 019 | Unit Conversion Simplification | MERGED | Removed redundant `recipe_unit` and `UnitConversion` table. 4-field density is canonical. |
| 020 | Enhanced Data Import | MERGED | Separate catalog import from transactional data. ADD_ONLY and AUGMENT modes. |
| 021 | Field Naming Consistency | MERGED | purchase_unit→package_unit, purchase_quantity→package_unit_quantity, pantry→inventory cleanup. |
| 022 | Unit Reference Table & UI Constraints | MERGED | Database-backed unit management with UI enforcement. |
| 023 | Product Name Differentiation | MERGED | Added product_name field, updated import/export for dependent entities, fixed 20 test failures. |
| 024 | Unified Import Error Handling | MERGED | Standardized error display/logging across unified and catalog imports. ImportResultsDialog for all imports, log files, error suggestions. |
| 025 | Production Loss Tracking | MERGED | Loss quantity/category tracking, yield balance constraint, ProductionLoss table, UI auto-calculation, cost breakdown, waste analytics. |
| 026 | Deferred Packaging Decisions | MERGED | Generic packaging at planning time, deferred material assignment, EventPackagingRequirement and EventPackagingAssignment tables, assembly definition with material assignment interface. |
| 027 | Product Catalog Management | MERGED | Products tab with CRUD operations, filtering, purchase history. Supplier entity, preferred_supplier on Product, is_hidden flag. |
| 028 | Purchase Tracking & Enhanced Costing | MERGED | Purchase entity, price history queries, FIFO using Purchase.unit_price, InventoryAddition.purchase_id FK, supplier dropdown in Add Inventory dialog. |
| 029 | Streamlined Inventory Entry | MERGED | Type-ahead filtering, recency intelligence, session memory, inline product creation, smart defaults, enhanced price display. |
| 030 | Enhanced Export/Import System | MERGED | Coordinated exports with manifest validation, denormalized views for AI augmentation, interactive FK resolution, skip-on-error mode, mid-import cancellation handling. |

---

## In Progress

*No features currently in progress.*

---

## Planned Features

| # | Name | Priority | Dependencies | Status |
|---|------|----------|--------------|--------|
| 031 | Packaging & Distribution | LOW | User testing complete | Blocked |

---

## Implementation Order

**Current:** None - awaiting next feature

1. ~~**TD-001** - Clean foundation before adding new entities~~ ✅ COMPLETE
2. ~~**Feature 011** - Packaging materials, extend Composition for packaging~~ ✅ COMPLETE
3. ~~**Feature 012** - Nested recipes (sub-recipes as recipe components)~~ ✅ COMPLETE
4. ~~**Feature 013** - BatchProductionService, AssemblyService, consumption ledgers~~ ✅ COMPLETE
5. ~~**Feature 014** - Production UI, Record Production/Assembly dialogs~~ ✅ COMPLETE
6. ~~**Feature 016** - Event-Centric Production Model~~ ✅ COMPLETE
7. ~~**BUGFIX** - Session Management Remediation~~ ✅ COMPLETE
8. ~~**Feature 017** - Reporting and Event Planning~~ ✅ COMPLETE
9. ~~**Feature 018** - Event Production Dashboard~~ ✅ COMPLETE
10. ~~**Feature 019** - Unit Conversion Simplification~~ ✅ COMPLETE
11. ~~**Feature 020** - Enhanced Data Import~~ ✅ COMPLETE
12. ~~**Feature 021** - Field Naming Consistency~~ ✅ COMPLETE
13. ~~**TD-002** - Unit Standardization~~ ✅ COMPLETE
14. ~~**TD-003** - Catalog Import Test Schema Mismatch~~ ✅ COMPLETE
15. ~~**Feature 022** - Unit Reference Table & UI Constraints~~ ✅ COMPLETE
16. ~~**Feature 023** - Product Name Differentiation~~ ✅ COMPLETE
17. ~~**Feature 024** - Unified Import Error Handling~~ ✅ COMPLETE
18. ~~**Feature 025** - Production Loss Tracking~~ ✅ COMPLETE
19. ~~**Feature 026** - Deferred Packaging Decisions~~ ✅ COMPLETE
20. ~~**Feature 027** - Product Catalog Management~~ ✅ COMPLETE
21. ~~**Feature 028** - Purchase Tracking & Enhanced Costing~~ ✅ COMPLETE
22. ~~**Feature 029** - Streamlined Inventory Entry~~ ✅ COMPLETE
23. ~~**Feature 030** - Enhanced Export/Import System~~ ✅ COMPLETE
24. **Feature 031** - Packaging & Distribution

---

## Feature Descriptions

### Feature 030: Enhanced Export/Import System

**Status:** COMPLETE ✅ (Merged 2025-12-26)

**Dependencies:** Features 027 (Product Catalog Management), 028 (Purchase Tracking & Enhanced Costing)

**Problem:** Current export/import system has critical gaps blocking AI-assisted data augmentation and efficient test data management. Monolithic exports difficult to process, no AI-friendly formats for UPC enrichment, no FK resolution strategy, missing entities force manual creation loops, no validation feedback before import failures.

**Solution:** Coordinated export/import system with denormalized views for AI augmentation and interactive FK resolution for missing entities.

**Delivered:**

**Export Capabilities:**
1. **Coordinated Normalized Exports** (complete DB rebuild):
   - Export manifest with metadata, checksums, dependencies, import order
   - Individual entity files with FK resolution fields (id + slug/name)
   - ZIP archive option
   - Configurable output directory

2. **Denormalized View Exports** (AI augmentation):
   - `view_products.json` - Products with ingredient/supplier context
   - `view_inventory.json` - Inventory with product/purchase context
   - `view_purchases.json` - Purchases with product/supplier context
   - Standard persistent filenames (working files for export → edit → import cycle)

**Import Capabilities:**
1. **Import Normalized Files** (standard restore):
   - Manifest validation with checksum verification (warn-and-prompt on mismatch)
   - FK resolution via slug/name when IDs differ
   - Modes: `merge` (update existing, add new) or `skip_existing` (only new)
   - Dry-run mode (CLI only)

2. **Import Denormalized Views** (AI augmentation):
   - Auto-detect file type, extract normalized updates from context
   - Apply updates to appropriate tables only
   - Preserve referential integrity

3. **Interactive FK Resolution**:
   - **CLI:** Fail-fast default, `--interactive` flag for resolution
   - **UI:** Interactive resolution wizard (default)
   - Options: Create entity, map to existing, skip record
   - Entity types: Suppliers, Ingredients, Products
   - Dependency chain handling (Ingredient before Product)
   - Referential integrity validation

4. **Skip-on-Error Mode**:
   - `--skip-on-error` flag: Skip records with FK errors, import valid ones
   - Log skipped records to `import_skipped_{timestamp}.json`
   - Report: X imported, Y skipped

5. **Mid-Import Cancellation Handling**:
   - User can cancel during interactive FK resolution
   - Prompt: Keep partial work or rollback all changes
   - Smart defaults: <10% progress suggests rollback, >90% suggests keep
   - Shows summary: imported count, created entities
   - CLI flags: `--rollback-on-cancel`, `--keep-on-cancel`

**User Impact:**
- **AI augmentation workflow enabled:** Export products → AI fills UPC codes → Import with merge
- **New supplier workflow:** AI generates purchases from "Wilson's Farm" → Interactive resolution creates supplier → Purchases imported
- **Test data management:** Coordinated exports enable safe schema migrations
- **Error recovery:** Skip-on-error logs problematic records for later correction
- **Safe cancellation:** Mid-import cancel with informed decision on partial work

**Key Features:**
- Standard filenames for denormalized views (not timestamped)
- FK resolution via slug/name (portable across environments)
- Interactive entity creation during import (Suppliers, Ingredients, Products)
- Validation before database writes
- Round-trip guarantee: export → import → verify identical
- Graceful cancellation with transaction integrity

**Design Document:** `docs/design/F030_enhanced_export_import.md`

---

### Feature 031: Packaging & Distribution

**Status:** Blocked (awaiting user testing completion)

**Scope:** PyInstaller executable, Inno Setup installer, Windows distribution.

---

### Feature 029: Streamlined Inventory Entry

**Status:** COMPLETE ✅ (Merged 2025-12-25)

**Dependencies:** Features 027 (Product Catalog Management), 028 (Purchase Tracking & Enhanced Costing)

**Problem:** Current inventory entry workflow creates significant friction for the primary use case: adding 20+ items after a shopping trip. Too many clicks (4-5 dropdown selections per item), long ingredient list (hundreds of items), no session memory (must select "Costco" 20 times), product creation breaks flow (modal switching), no price recall ("What did I pay last time?").

**Solution:** Transform inventory entry from tedious data entry into intelligent, flow-optimized experience using enhanced ingredient-first workflow with type-ahead, recency ranking, session memory, and inline product creation.

**Delivered:**
- Type-ahead filtering on Category/Ingredient/Product dropdowns (1-2 char thresholds, contains matching)
- Recency intelligence: Recent/frequent items marked with ⭐ and sorted to top (last 30 days OR 3+ uses in 90 days)
- Session memory: Last supplier/category pre-selected (persists until app restart)
- Inline product creation: Collapsible accordion form within dialog (no modal switching)
- Smart defaults: Package unit by category (Baking→lb, Chocolate→oz)
- Enhanced price display: Inline hint "(last paid: $X.XX on MM/DD)" with fallback to different supplier
- Validation warnings: >$100 price, decimal quantities for count units
- Tab/Enter/Escape navigation

**User Impact:**
- Reduces 15-20 minutes data entry to 5 minutes target
- "I just shopped at Costco with 20 items" → efficient bulk entry workflow
- Eliminates repetitive selections (supplier remembered across items)
- Reduces cognitive load (recent items appear first, type-ahead reduces scrolling)

**Design Document:** `docs/design/F029_streamlined_inventory_entry.md`

---

### Feature 028: Purchase Tracking & Enhanced Costing

**Status:** COMPLETE ✅ (Merged 2025-12-24)

**Problem:** No purchase history or supplier tracking, static price data without context, FIFO limited by lack of transaction records, price volatility invisible ($300 → $600 chocolate chips example).

**Solution:** Purchase entity as first-class transaction record linking products to suppliers with temporal pricing context. FIFO cost calculation updated to use Purchase.unit_price.

**Delivered:**
- New Purchase table (product_id, supplier_id, purchase_date, unit_price, quantity_purchased, notes)
- InventoryAddition.purchase_id FK (replaces price_paid field)
- New `purchase_service.py` with query-only operations (get, history, price suggestions)
- `inventory_service.add_inventory()` creates Purchase records inline (transaction owner)
- Purchase history queries (by product, supplier, date range)
- Price suggestion queries (last paid at supplier, fallback to any supplier)
- FIFO cost calculation uses Purchase.unit_price via InventoryAddition.purchase relationship
- Add Inventory dialog: Supplier dropdown (alphabetically sorted)
- Price field pre-fills from last purchase at selected supplier
- Price hint: "(last paid: $X.XX on MM/DD)" or "(last paid: $X.XX at [Supplier] on MM/DD)" for fallback
- Validation: Warn if price >$100, allow $0.00 with confirmation

**User Impact:**
- Tracks "What did I pay for chocolate chips last time?" ($300 → $450 → $600 trend visible)
- Enables supplier-based purchasing decisions ("Costco is cheaper for bulk chocolate")
- Provides accurate FIFO costing (purchase transaction context, not static price)
- Price suggestions reduce data entry friction
- Supplier selection in Add Inventory dialog

**Design Document:** `docs/design/F028_purchase_tracking_enhanced_costing.md`

---

### Feature 027: Product Catalog Management

**Status:** COMPLETE ✅ (Merged 2025-12-24)

**Problem:** Product and inventory management workflows had critical gaps blocking effective user testing. Cannot add products independently, forced ingredient-first entry blocks inventory addition, no price history tracking for FIFO costing, no product catalog maintenance tools.

**Solution:** Three-feature implementation: (027) Product Catalog Management foundation with Products tab, CRUD operations, filtering, purchase history display; (028) Purchase Tracking & Enhanced Costing with Purchase entity, Supplier entity, price history; (029) Streamlined Inventory Entry with enhanced workflow, type-ahead, inline creation, price suggestions.

**Delivered:**
- Products tab with comprehensive filtering (ingredient, category, supplier, show hidden checkbox)
- Product detail view shows all fields, purchase history, Hide/Delete actions
- Add Product form with validation, preferred supplier selection
- Supplier CRUD operations (create, list, deactivate)
- Referential integrity: Cannot delete product if purchases/inventory exist (offer Hide instead)
- Search products by name (case-insensitive, partial match, combines with filters)

**User Impact:**
- Enables "I just shopped at Costco with 20 items" workflow (unblocked from ingredient-first constraint)
- Tracks supplier relationships (preferred supplier per product)
- Provides foundation for purchase tracking (Feature 028)
- Unblocks user testing with realistic product catalog

**Design Document:** `docs/design/F027_product_catalog_management.md`

---

### Feature 026: Deferred Packaging Decisions

**Status:** COMPLETE ✅ (Merged 2025-12-22)

**Problem:** When planning events, food decisions precede packaging aesthetic decisions. Current system forces premature commitment to specific packaging designs (e.g., snowflake vs holly bags) when only generic requirements are known (e.g., need 6" cellophane bags).

**Solution:** Allow planning with generic packaging products, deferring specific material selection until later in the workflow.

**Delivered:**
- Radio button UI: "Specific material" vs "Generic product" selection
- EventPackagingRequirement and EventPackagingAssignment tables
- Production dashboard indicator for pending packaging decisions
- Assembly definition screen with material assignment interface
- Assembly progress enforcement with "Record Anyway" bypass option
- Shopping list shows generic products until materials assigned
- Dynamic cost estimates (average for generic, actual for assigned)

**Design Document:** `docs/design/F026-deferred-packaging-decisions.md`

---

### Feature 025: Production Loss Tracking

**Status:** COMPLETE ✅ (Merged 2025-12-21)

**Problem:** Baked goods production involves real-world failures (burnt, broken, contaminated, dropped). Current system cannot distinguish between successful production and losses, preventing cost accounting for waste and analytics on loss trends.

**Solution:** Add explicit production loss tracking with yield balance constraint, ProductionLoss table for analytics, UI auto-calculation, and cost breakdown.

**Delivered:**
- Schema: production_status, loss_quantity, loss_notes on ProductionRun
- New ProductionLoss model with loss_category, per_unit_cost, total_loss_cost, notes
- Service layer: record_production() accepts loss parameters with yield balance validation
- UI: RecordProductionDialog expandable loss details section (auto-expands when loss detected)
- UI: ProductionHistoryTable shows loss quantity and status columns with color coding
- Reporting: Loss summaries by category, recipe loss rates, waste cost analysis

**Design Document:** `docs/design/F025_production_loss_tracking.md`

---

### Feature 024: Unified Import Error Handling

**Status:** COMPLETE ✅ (Merged 2025-12-20)

**Problem:** Import error handling was inconsistent between unified import and catalog import.

**Delivered:**
- Catalog import uses `ImportResultsDialog` instead of messageboxes
- All errors displayed (not truncated to 5)
- Log files written to `docs/user_testing/import_YYYY-MM-DD_HHMMSS.log`
- Error suggestions displayed clearly in dialog and logs
- Consistent user experience across import types

---

### Feature 023: Product Name Differentiation

**Status:** COMPLETE ✅ (Merged 2025-12-19)

**Problem:** Current unique constraint `(ingredient_id, brand, package_size, package_unit)` cannot distinguish product variants with identical packaging.

**Solution:** Add `product_name` field for human-readable product differentiation.

---

### Feature 022: Unit Reference Table & UI Constraints

**Status:** COMPLETE ✅

**Solution:** Database-backed unit reference table with UI enforcement.

---

### Feature 021: Field Naming Consistency

**Status:** COMPLETE ✅ (Merged 2025-12-16)

**Delivered:**
- Renamed `purchase_unit` → `package_unit`
- Renamed `purchase_quantity` → `package_unit_quantity`
- Replaced all "pantry" occurrences with "inventory"

---

### Feature 020: Enhanced Data Import

**Status:** COMPLETE ✅ (Merged 2025-12-16)

**Solution:** Separate import pathways with explicit modes: `ADD_ONLY` and `AUGMENT`.

---

### Feature 019: Unit Conversion Simplification

**Status:** COMPLETE ✅ (Merged 2025-12-14)

**Solution:** Remove redundant `recipe_unit` and `UnitConversion` table. The 4-field density model is canonical.

---

### Feature 018: Event Production Dashboard

**Status:** COMPLETE ✅ (Merged 2025-12-12)

**Delivered:**
- "Where do I stand for Christmas 2025?" consolidated view
- Progress bars per recipe/finished good
- Fulfillment status tracking with visual indicators

---

### Feature 017: Reporting & Event Planning

**Status:** COMPLETE ✅ (Merged 2025-12-12)

**Delivered:**
- Shopping list CSV export
- Event summary reports (planned vs actual)
- Cost analysis views
- Recipient history reports

---

### Feature 016: Event-Centric Production Model

**Status:** COMPLETE ✅ (Merged 2025-12-11)

**Delivered:**
- Added `event_id` (nullable FK) to ProductionRun and AssemblyRun
- New `EventProductionTarget` and `EventAssemblyTarget` tables
- Added `fulfillment_status` ENUM to EventRecipientPackage
- Service methods for target management and progress calculation

---

### Feature 012: Nested Recipes

**Status:** COMPLETE ✅

**Delivered:**
- `RecipeComponent` junction model
- Recursive recipe cost calculation
- Recursive ingredient aggregation for shopping lists

---

## Key Decisions

### 2025-12-26
- **Feature 030 Complete:** Enhanced Export/Import System merged. Coordinated exports with manifest validation, denormalized views for AI augmentation, interactive FK resolution, skip-on-error mode, mid-import cancellation handling with smart defaults.
- **Four-Feature Product/Inventory/Import Sequence Complete:** F027 (Product Catalog Management) + F028 (Purchase Tracking & Enhanced Costing) + F029 (Streamlined Inventory Entry) + F030 (Enhanced Export/Import) all merged. Complete AI-assisted data augmentation workflow now operational.

### 2025-12-25
- **Feature 029 Complete:** Streamlined Inventory Entry merged. Type-ahead filtering, recency intelligence, session memory, inline product creation, smart defaults, enhanced price display.
- **Feature 030 In Progress:** Enhanced Export/Import System implementation started. Coordinated export/import with denormalized views for AI augmentation, interactive FK resolution, skip-on-error mode.
- **Three-Feature Product/Inventory Sequence Complete:** F027 (Product Catalog Management - foundation) + F028 (Purchase Tracking & Enhanced Costing - data model) + F029 (Streamlined Inventory Entry - workflow) all merged. Complete "I just shopped at Costco with 20 items" use case fully operational.

### 2025-12-24
- **Feature Renumbering:** Enhanced Export/Import System moved from F031 to F030. Packaging & Distribution moved from F030 to F031.
- **Feature 030 Defined:** Enhanced Export/Import System specification complete. Coordinated export/import with denormalized views for AI augmentation, interactive FK resolution, skip-on-error mode.
- **Feature 026 Complete:** Deferred Packaging Decisions merged.
- **Feature 027 Complete:** Product Catalog Management merged.
- **Feature 028 Complete:** Purchase Tracking & Enhanced Costing merged.

### 2025-12-21
- **Feature 025 Complete:** Production Loss Tracking merged.

### 2025-12-20
- **Feature 024 Complete:** Unified Import Error Handling merged.

### 2025-12-19
- **Feature 023 Complete:** Product Name Differentiation merged.

### 2025-12-16
- **Feature 020 Complete:** Enhanced Data Import merged.
- **Feature 021 Complete:** Field Naming Consistency merged.

### 2025-12-14
- **Feature 019 Complete:** Unit Conversion Simplification merged.

### 2025-12-12
- **Feature 018 Complete:** Event Production Dashboard merged.
- **Feature 017 Complete:** Reporting & Event Planning merged.

### 2025-12-11
- **Feature 016 Complete:** Event-Centric Production Model merged.

---

## Technical Debt

### TD-001: Schema Cleanup
**Status:** COMPLETE ✅

### TD-002: Unit Standardization
**Status:** COMPLETE ✅

### TD-003: Catalog Import Test Schema Mismatch
**Status:** COMPLETE ✅

---

## Document History

- 2025-12-03: Initial creation
- 2025-12-04 through 2025-12-25: Progressive feature completions (see detailed history above)
- 2025-12-26: Feature 030 (Enhanced Export/Import System) complete and merged. Four-feature product/inventory/import sequence (F027+F028+F029+F030) complete. AI-assisted data augmentation workflow fully operational.
