# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2025-12-24
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

---

## In Progress

*No features currently in progress.*

---

## Planned Features

| # | Name | Priority | Dependencies | Status |
|---|------|----------|--------------|--------|
| 029 | Streamlined Inventory Entry | HIGH | Features 027, 028 | Ready |
| 030 | Enhanced Export/Import System | HIGH | Features 027, 028 | Ready |
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
22. **Feature 029** - Streamlined Inventory Entry
23. **Feature 030** - Enhanced Export/Import System
24. **Feature 031** - Packaging & Distribution

---

## Feature Descriptions

### Feature 030: Enhanced Export/Import System

**Status:** READY 📋

**Dependencies:** Features 027 (Product Catalog Management), 028 (Purchase Tracking & Enhanced Costing)

**Problem:** Current export/import system has critical gaps blocking AI-assisted data augmentation and efficient test data management. Monolithic exports difficult to process, no AI-friendly formats for UPC enrichment, no FK resolution strategy, missing entities force manual creation loops, no validation feedback before import failures.

**Solution:** Coordinated export/import system with denormalized views for AI augmentation and interactive FK resolution for missing entities.

**Scope:**

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
   - Manifest validation, checksum verification
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

**User Impact:**
- **AI augmentation workflow enabled:** Export products → AI fills UPC codes → Import with merge
- **New supplier workflow:** AI generates purchases from "Wilson's Farm" → Interactive resolution creates supplier → Purchases imported
- **Test data management:** Coordinated exports enable safe schema migrations
- **Error recovery:** Skip-on-error logs problematic records for later correction

**Key Features:**
- Standard filenames for denormalized views (not timestamped)
- FK resolution via slug/name (portable across environments)
- Interactive entity creation during import (Suppliers, Ingredients, Products)
- Validation before database writes
- Round-trip guarantee: export → import → verify identical

**Design Document:** `docs/design/F031_enhanced_export_import.md`

**Estimated Effort:** 16-20 hours

---

### Feature 029: Streamlined Inventory Entry

**Status:** READY 📋

**Dependencies:** Features 027 (Product Catalog Management), 028 (Purchase Tracking & Enhanced Costing)

**Problem:** Current inventory entry workflow creates significant friction for the primary use case: adding 20+ items after a shopping trip. Too many clicks (4-5 dropdown selections per item), long ingredient list (hundreds of items), no session memory (must select "Costco" 20 times), product creation breaks flow (modal switching), no price recall ("What did I pay last time?").

**Solution:** Transform inventory entry from tedious data entry into intelligent, flow-optimized experience using enhanced ingredient-first workflow with type-ahead, recency ranking, session memory, and inline product creation.

**Scope:**
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

### Feature 031: Packaging & Distribution

**Status:** Blocked (awaiting user testing completion)

**Scope:** PyInstaller executable, Inno Setup installer, Windows distribution.

---

### Feature 026: Deferred Packaging Decisions

**Status:** COMPLETE ✅ (Merged 2025-12-22)

**Problem:** When planning events, food decisions precede packaging aesthetic decisions. Current system forces premature commitment to specific packaging designs (e.g., snowflake vs holly bags) when only generic requirements are known (e.g., need 6" cellophane bags).

**Solution:** Allow planning with generic packaging products, deferring specific material selection until later in the workflow:
- Event planning: Select generic packaging product (e.g., "Cellophane Bags 6x10")
- System shows: Available inventory across variants, estimated cost (average price)
- Decision timing: Anytime from planning through assembly (assembly forces decision)
- Material assignment: Quick assign interface or full assignment screen
- Cost updates: Estimated (generic) → Actual (assigned)

**Delivered:**
- Radio button UI: "Specific material" vs "Generic product" selection
- EventPackagingRequirement and EventPackagingAssignment tables
- Production dashboard indicator for pending packaging decisions
- Assembly definition screen with material assignment interface
- Assembly progress enforcement with "Record Anyway" bypass option
- Shopping list shows generic products until materials assigned
- Dynamic cost estimates (average for generic, actual for assigned)

**Edge Cases Covered:**
- Change of plans during assembly (boxes → bags)
- Insufficient inventory at assignment time
- Multiple refinement stages
- Shopping before final assignment
- Backfill scenarios for fast-moving kitchen

**User Validation:** All acceptance criteria validated with primary stakeholder (Marianne). Covers all discussed real-world scenarios.

**Design Document:** `docs/design/F026-deferred-packaging-decisions.md`

---

### Feature 027: Product Catalog Management

**Status:** COMPLETE ✅ (Merged 2025-12-24)

**Problem:** Product and inventory management workflows had critical gaps blocking effective user testing. Cannot add products independently, forced ingredient-first entry blocks inventory addition, no price history tracking for FIFO costing, no product catalog maintenance tools.

**Solution:** Three-feature implementation: (027) Product Catalog Management foundation with Products tab, CRUD operations, filtering, purchase history display; (028) Purchase Tracking & Enhanced Costing with Purchase entity, Supplier entity, price history; (029) Streamlined Inventory Entry with enhanced workflow, type-ahead, inline creation, price suggestions.

**Scope (Feature 027):**
- New Products tab with grid view and filters (ingredient, category, supplier, search)
- Product CRUD operations with referential integrity checks
- Hide/unhide products (preserve history)
- Product detail view with purchase history table
- New Supplier table (name, street_address, city, state, zip, notes, is_active)
- Product.preferred_supplier_id and Product.is_hidden fields
- Foundation for Purchase entity (Feature 028)

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

**Migration Strategy:** Export/reset/import cycle. No Purchase records yet (Feature 028).

**Design Document:** `docs/design/F027_product_catalog_management.md`

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

**Migration:**
- Export/reset/import cycle
- One Purchase per existing InventoryAddition
- purchase_date = addition.addition_date
- supplier_id = 1 ("Unknown Supplier" created in F027 migration)
- unit_price = addition.price_paid
- quantity_purchased = addition.quantity
- Accept imperfect historical data (all purchases assigned to Unknown Supplier)

**User Impact:**
- Tracks "What did I pay for chocolate chips last time?" ($300 → $450 → $600 trend visible)
- Enables supplier-based purchasing decisions ("Costco is cheaper for bulk chocolate")
- Provides accurate FIFO costing (purchase transaction context, not static price)
- Price suggestions reduce data entry friction
- Supplier selection in Add Inventory dialog

**Design Document:** `docs/design/F028_purchase_tracking_enhanced_costing.md`

---

### Feature 025: Production Loss Tracking

**Status:** COMPLETE ✅ (Merged 2025-12-21)

**Problem:** Baked goods production involves real-world failures (burnt, broken, contaminated, dropped). Current system cannot distinguish between successful production and losses, preventing cost accounting for waste and analytics on loss trends. Lost batches must be remade to fulfill event requirements - no workflow to loop back to production for replacement batches.

**Solution:** Add explicit production loss tracking with:
- Loss quantity and category (burnt/broken/contaminated/dropped/wrong_ingredients/other)
- Production status enum (COMPLETE/PARTIAL_LOSS/TOTAL_LOSS)
- Yield balance constraint: actual_yield + loss_quantity = expected_yield
- Separate ProductionLoss table for detailed loss records and analytics
- UI auto-calculates loss quantity from expected vs actual yield
- Cost breakdown showing good units vs lost units
- Remake workflow: Event Production Dashboard shows shortfall, user initiates replacement batches

**Delivered:**
- Schema: production_status, loss_quantity, loss_notes on ProductionRun
- New ProductionLoss model with loss_category, per_unit_cost, total_loss_cost, notes
- Service layer: record_production() accepts loss parameters with yield balance validation
- UI: RecordProductionDialog expandable loss details section (auto-expands when loss detected)
- UI: ProductionHistoryTable shows loss quantity and status columns with color coding
- Reporting: Loss summaries by category, recipe loss rates, waste cost analysis
- Migration: Export/reset/import cycle, historical data defaulted to COMPLETE/0 loss

**Design Document:** `docs/design/F025_production_loss_tracking.md`
**Spec-Kitty Artifacts:** `kitty-specs/025-production-loss-tracking/`

---

### Feature 024: Unified Import Error Handling

**Status:** COMPLETE ✅ (Merged 2025-12-20)

**Problem:** Import error handling was inconsistent between unified import and catalog import:
- **Unified Import:** Scrollable dialog with copy-to-clipboard, log files written to `docs/user_testing/`
- **Catalog Import:** Basic messageboxes, errors truncated to 5, no logging, rich `suggestion` field not displayed

**Solution:** Standardize error display across both import systems:
- Use `ImportResultsDialog` for all imports (scrollable, copyable)
- Write log files for catalog imports (matching unified import format)
- Display structured error suggestions when available
- Show relative paths (not absolute) for log file locations

**Delivered:**
- Catalog import uses `ImportResultsDialog` instead of messageboxes
- All errors displayed (not truncated to 5)
- Log files written to `docs/user_testing/import_YYYY-MM-DD_HHMMSS.log`
- Error suggestions displayed clearly in dialog and logs
- Relative paths shown in UI (not absolute)
- Consistent user experience across import types

**Specification:** `docs/design/F024_unified_import_error_handling.md`

---

### Feature 023: Product Name Differentiation

**Status:** COMPLETE ✅ (Merged 2025-12-19)

**Problem:** Current unique constraint `(ingredient_id, brand, package_size, package_unit)` cannot distinguish product variants with identical packaging:
- Lindt 3.5oz bars at different cacao percentages (70% vs 85%)
- Sugar-free vs regular versions of same product
- Dairy variants (whole milk vs 2% vs skim)

**Solution:** Add `product_name` field for human-readable product differentiation.

**Scope:**
- Add `product_name VARCHAR(200) NULL` column to Product table
- Update unique constraint to include product_name: `(ingredient_id, brand, product_name, package_size, package_unit)`
- Maintain backward compatibility (nullable for existing products)
- Enable AI-assisted backfilling of product names
- Support mobile barcode scanning workflow for web phase

**Web Phase Alignment:**
This change directly enables critical mobile inventory management:
- GTIN lookup returns complete product info including readable product_name
- Mobile app displays clear differentiation: "Ghirardelli 60% Cacao 3.5oz bar"
- User confirms or edits before adding to inventory
- Reduces manual data entry friction (adoption blocker)

**Migration Strategy:** Export/reset/import cycle (Constitution VI)

**Complexity Justification:**
- **Future-Proof Schema:** Aligns with GS1 industry practices; enables barcode workflow
- **User-Centric Design:** Clear product identification; critical for mobile UX
- **Pragmatic Aspiration:** Desktop nullable/optional; Web critical for adoption

---

### Feature 022: Unit Reference Table & UI Constraints

**Status:** COMPLETE ✅

**Problem:** Units were stored as free-form strings with application-level validation only. While TD-002 added import validation, the UI still allowed arbitrary unit entry.

**Solution:** Database-backed unit reference table with UI enforcement.

**Delivered:**
- Created `units` reference table with columns: `code`, `name`, `symbol`, `category`, `uncefact_code` (nullable)
- Seeded table with valid units from `src/utils/constants.py`
- Updated UI unit inputs to use dropdowns/comboboxes populated from units table
- Added application-level validation against reference table
- Maintained backward compatibility with existing data

**Reference Documents:**
- `docs/design/unit_codes_reference.md` - UN/CEFACT standard reference
- `docs/research/unit_handling_analysis_report.md` - Current state analysis
- `docs/technical-debt/TD-002_unit_standardization.md` - Prerequisite work

---

### Feature 021: Field Naming Consistency

**Status:** COMPLETE ✅ (Merged 2025-12-16)

**Problem:** Two naming inconsistencies created confusion:
1. **Purchase vs Package:** `purchase_unit` and `purchase_quantity` on Product describe package characteristics, not purchase transactions.
2. **Pantry remnants:** "Pantry" terminology should have been fully replaced by "Inventory" but remnants remained.

**Delivered:**
- Renamed `purchase_unit` → `package_unit`
- Renamed `purchase_quantity` → `package_unit_quantity`
- Replaced all "pantry" occurrences with "inventory"
- Updated schema, models, services, UI, import/export, docs, tests

---

### Feature 020: Enhanced Data Import

**Status:** COMPLETE ✅ (Merged 2025-12-16)

**Problem:** Current unified import conflates two fundamentally different data types:
- **Catalog Data** (Ingredients, Products, Recipes) - slowly changing reference data
- **Transactional Data** (Purchases, Inventory, Events) - user-specific activity

This prevents safe catalog expansion without risking user data.

**Solution:** Separate import pathways with explicit modes:
- `ADD_ONLY` - Create new records, skip existing (default)
- `AUGMENT` - Update NULL fields on existing records (ingredients/products only)

**Delivered:**
- New `import_catalog` CLI command
- Catalog-specific JSON format (v1.0)
- FK validation before import
- Dry-run preview mode
- Preserved existing unified import/export for development workflow

**Specification:** `docs/enhanced_data_import.md`

---

### Feature 019: Unit Conversion Simplification

**Status:** COMPLETE ✅ (Merged 2025-12-14)

**Problem:** Redundant unit conversion mechanisms:
- `Ingredient.recipe_unit` - vestigial field; recipes declare their own units in RecipeIngredient
- `UnitConversion` table - values derivable from 4-field density on Ingredient

**Solution:** Remove both. The 4-field density model (Feature 010) is the canonical source.

**Delivered:**
- Deleted `Ingredient.recipe_unit` column
- Deleted `UnitConversion` model and table
- Updated import/export spec v3.2 → v3.3
- Converted test data files
- Constitution v1.2.0: Schema changes via export/reset/import (no migration scripts)

**Specification:** `docs/feature_019_unit_simplification.md`

---

### Feature 018: Event Production Dashboard

**Status:** COMPLETE ✅ (Merged 2025-12-12)

**Rationale:** Builds on Feature 016's event progress tracking to provide a comprehensive "mission control" view.

**Delivered:**
- "Where do I stand for Christmas 2025?" consolidated view
- Progress bars per recipe/finished good
- Fulfillment status tracking with visual indicators
- Multi-event overview (compare progress across events)
- Quick actions (jump to record production, view shopping list)

**Spec-Kitty Artifacts:** `kitty-specs/018-event-production-dashboard/`

---

### Feature 017: Reporting & Event Planning

**Status:** COMPLETE ✅ (Merged 2025-12-12)

**Rationale:** With event-production linkage complete (Feature 016), accurate event reporting is now possible.

**Delivered:**
- Shopping list CSV export
- Event summary reports (planned vs actual)
- Cost analysis views
- Recipient history reports
- Dashboard enhancements

**Spec-Kitty Artifacts:** `kitty-specs/017-reporting-event-planning/`

---

### Feature 016: Event-Centric Production Model

**Status:** COMPLETE ✅ (Merged 2025-12-11)

**Problem Solved:** The architecture previously conflated three distinct concerns:
1. **Definition** - What IS a Cookie Gift Box? (FinishedGood + Composition) ✅
2. **Inventory** - How many EXIST globally? (inventory_count) ✅
3. **Commitment** - How many are FOR Christmas 2025? ✅ **NOW WORKS**

**Delivered (Schema v0.6):**
- Added `event_id` (nullable FK) to ProductionRun and AssemblyRun
- New `EventProductionTarget` table (event_id, recipe_id, target_batches)
- New `EventAssemblyTarget` table (event_id, finished_good_id, target_quantity)
- Added `fulfillment_status` ENUM to EventRecipientPackage (pending/ready/delivered)
- Service methods for target management and progress calculation
- UI: Event selector in Record Production/Assembly dialogs
- UI: Targets tab in Event detail with progress bars
- UI: Fulfillment status column with sequential workflow

**Design Document:** `docs/design/schema_v0.6_design.md`
**Spec-Kitty Artifacts:** `kitty-specs/016-event-centric-production/`

---

### BUGFIX: Session Management Remediation

**Status:** COMPLETE ✅ (2025-12-11)

**Problem Solved:** Code review during Feature 016 revealed critical architectural flaw: nested `session_scope()` calls cause SQLAlchemy objects to become detached, resulting in silent data loss.

**Delivered:**
- Fixed `assembly_service.py` to pass session through call chain
- Fixed `check_can_produce()` and `check_can_assemble()` to use session parameter
- Rollback tests already existed (TestTransactionAtomicity, TestAssemblyTransactionAtomicity)
- All 680 tests pass

**Specification:** `docs/design/session_management_remediation_spec.md`

---

### Feature 012: Nested Recipes

**Status:** COMPLETE ✅

**Rationale:** User testing revealed recipes can be hierarchical. A frosted layer cake recipe calls for sub-recipes (chocolate cake layers, vanilla cake layers, frosting, filling).

**Scope (Delivered):**
- `RecipeComponent` junction model (recipe_id, component_recipe_id, quantity, unit, notes)
- Recursive recipe cost calculation
- Recursive ingredient aggregation for shopping lists
- Recipe UI: ability to add sub-recipes as components
- Import/export support for nested recipes

---

## Key Decisions

### 2025-12-24
- **Feature Renumbering:** Enhanced Export/Import System moved from F031 to F030. Packaging & Distribution moved from F030 to F031.
- **Feature 030 Defined:** Enhanced Export/Import System specification complete. Coordinated export/import with denormalized views for AI augmentation, interactive FK resolution, skip-on-error mode.
- **Feature 026 Complete:** Deferred Packaging Decisions merged. Generic packaging at planning time, deferred material assignment, EventPackagingRequirement and EventPackagingAssignment tables, assembly definition with material assignment interface.
- **Feature 027 Complete:** Product Catalog Management merged. Products tab with CRUD operations, filtering, purchase history display, Supplier entity, preferred_supplier on Product, is_hidden flag.
- **Feature 028 Complete:** Purchase Tracking & Enhanced Costing merged. Purchase entity, price history queries, FIFO using Purchase.unit_price, InventoryAddition.purchase_id FK, supplier dropdown in Add Inventory dialog, price suggestions.
- **Feature 029 Ready:** Streamlined Inventory Entry specification complete. Enhanced ingredient-first workflow with type-ahead, recency ranking, session memory, inline product creation.
- **Three-Feature Product/Inventory Sequence Complete:** F027 (foundation) + F028 (data model) + F029 (workflow) addresses complete "I just shopped at Costco with 20 items" use case. F027 & F028 merged, F029 ready for implementation.

### 2025-12-21
- **Feature 025 Complete:** Production Loss Tracking merged. Tracks burnt/broken/contaminated/dropped losses, yield balance constraint, ProductionLoss table for analytics, UI auto-calculation, expandable loss details section, cost breakdown, waste reporting.
- **Feature 026 Defined:** Deferred Packaging Decisions - validated user story for staged packaging selection workflow. Allows generic packaging requirements at planning time with deferred material assignment. All acceptance criteria validated with Marianne.
- **Feature Numbering:** 025 = Production Loss Tracking (complete), 026 = Deferred Packaging Decisions (ready), 027 = Packaging & Distribution (blocked).

### 2025-12-20
- **Feature 024 Complete:** Unified Import Error Handling merged. Standardized error display/logging across unified and catalog imports.
- **Data Cleanup:** Added 30 missing ingredients with industry-standard USDA naming. Updated product slugs for consistency. Database reset and fresh import with complete catalogs (ingredients + products).
- **Web Migration Notes:** Documented API-based inventory management approach for web phase supporting multiple input modes (UI, mobile barcode, CSV import, future OCR/integrations).

### 2025-12-19
- **Feature 023 Complete:** Product Name Differentiation merged. Added `product_name` field to Product table for variant distinction.
- **Database Reset:** DB deleted for fresh import with updated schema and data (ingredients_catalog.json, sample_data.json).
- **Feature 022 Status Corrected:** Unit Reference Table & UI Constraints confirmed complete (previously mismarked as planned).
- **Feature 024 Defined:** Unified Import Error Handling - standardize error display/logging across unified and catalog imports. Use `ImportResultsDialog` everywhere, write logs for catalog imports, display error suggestions, show relative paths.
- **Feature Renumbering:** Unified Import Error Handling = Feature 024 (ready), Packaging & Distribution = Feature 025 (blocked).

### 2025-12-16
- **Feature 020 Complete:** Enhanced Data Import merged. Separate catalog import from transactional data.
- **Feature 021 Complete:** Field Naming Consistency merged. purchase_unit→package_unit, pantry→inventory.
- **TD-002 Complete:** Unit Standardization - import validation, sample data fixes, audit script.
- **TD-003 Complete:** Fixed test_catalog_import_service.py schema mismatch (19 tests).
- **Feature 023 Defined:** Unit Reference Table & UI Constraints - database-backed unit management.
- **Renumbering:** Packaging & Distribution moved to Feature 024.

### 2025-12-14
- **Feature 019 Complete:** Unit Conversion Simplification merged. Removed `recipe_unit` and `UnitConversion` table.
- **Feature 020 Defined:** Enhanced Data Import - separate catalog from transactional data import.
- **Renumbering:** Packaging & Distribution moved to Feature 021.

### 2025-12-15
- **Feature 021 Defined:** Field Naming Consistency - fix purchase_unit/purchase_quantity and remaining pantry references.
- **Renumbering:** Packaging & Distribution moved to Feature 022.

### 2025-12-12
- **Feature 018 Complete:** Event Production Dashboard merged. Mission control view, progress visualization, fulfillment tracking.
- **Feature 017 Complete:** Reporting & Event Planning merged. CSV exports, event reports, cost analysis, recipient history, dashboard enhancements.

### 2025-12-11
- **Feature 016 Complete:** Event-Centric Production Model merged. 10 work packages, 65+ service tests.
- **Session Management Bug:** Code review revealed critical nested session_scope issue. Created remediation spec. Will be fixed via bugfix branch.
- **Feature Numbering:** Confirmed Feature 015 was skipped (aborted prior attempt). Feature 016 is Event-Centric Production Model. Renumbered subsequent features (017, 018, 019).

### 2025-12-10
- **Event-Production Linkage Gap:** Identified critical structural flaw - production runs not linked to events. Created Feature 016 (Event-Centric Production Model) as priority fix before reporting features.

### 2025-12-08
- **Nested Recipes:** Insert as Feature 012 before production tracking to avoid rework on shopping list aggregation and cost calculation

### 2025-12-06
- **Packaging:** Use Ingredient with `is_packaging` flag (not separate entity)
- **FIFO:** Inventory only; simple counts for FinishedUnit/FinishedGood
- **Holiday Season:** Full refactor - production 50% complete, no time pressure
- **Feature 004 Gap:** Assembly UI missing; addressed in Feature 014

---

## Technical Debt

### TD-001: Schema Cleanup
**Status:** COMPLETE ✅
**Prompt:** docs/TD-001-schema-cleanup-prompt.md

Part A: Variant → Product, fix dual FK ✅
Part B: Ingredient.name → Ingredient.display_name ✅

### TD-002: Unit Standardization
**Status:** COMPLETE ✅
**Prompt:** docs/technical-debt/TD-002_unit_standardization.md

- Fixed sample_data.json (vanilla extract oz → fl oz)
- Added import validation for all unit fields
- Created audit_units.py script
- All tests passing

### TD-003: Catalog Import Test Schema Mismatch
**Status:** COMPLETE ✅
**Prompt:** docs/technical-debt/TD-003_catalog_import_test_schema_mismatch.md

- Fixed 19 test failures in test_catalog_import_service.py
- Updated purchase_unit → package_unit field references

---

## Document History

- 2025-12-03: Initial creation
- 2025-12-04: Features 006-009 complete; TD-001 documented
- 2025-12-05: Feature 010 complete; 8 bugs fixed
- 2025-12-06: Workflow gap analysis; TD-001 started; Features 011-015 defined
- 2025-12-07: TD-001 complete; full terminology cleanup (Variant→Product, Pantry→Inventory)
- 2025-12-08: Feature 011 in progress; Feature 012 (Nested Recipes) inserted; features renumbered
- 2025-12-09: Features 011, 012, 013 complete. Full service layer for production tracking.
- 2025-12-10: Feature 013 bug fixes. Feature 014 complete. Feature 016 created for Event-Centric Production Model.
- 2025-12-11: Feature 016 implementation complete and merged. Session management bug discovered during code review; remediation spec created. Feature 015 confirmed skipped. Features renumbered: 017 (Reporting), 018 (Dashboard), 019 (Packaging).
- 2025-12-12: Feature 017 (Reporting & Event Planning) complete and merged. Feature 018 (Event Production Dashboard) complete and merged. Entered user testing phase.
- 2025-12-14: Constitution v1.2.0 (schema change strategy). Feature 019 (Unit Conversion Simplification) complete and merged. Feature 020 (Enhanced Data Import) defined. Packaging & Distribution moved to Feature 021.
- 2025-12-16: Features 020, 021 complete and merged. TD-002, TD-003 complete. Feature 023 (Unit Reference Table & UI Constraints) defined. Packaging & Distribution moved to Feature 024.
- 2025-12-19: Feature 023 (Product Name Differentiation) complete and merged. Database reset for fresh import with updated schema. Feature 024 (Unified Import Error Handling) defined. Feature renumbering: 024 = Unified Import Error Handling (ready), 025 = Packaging & Distribution (blocked).
- 2025-12-20: Feature 024 (Unified Import Error Handling) complete and merged. Added 30 missing ingredients with USDA naming standards. Database reset and complete catalog import (ingredients + products). Web migration notes updated for API-based inventory management.
- 2025-12-21: Feature 025 (Production Loss Tracking) defined. Design document created. Feature 025 implementation complete and merged. Features renumbered: 025 = Production Loss Tracking (complete), 026 = Deferred Packaging Decisions (ready), 027 = Packaging & Distribution (blocked).
- 2025-12-22: Feature 026 (Deferred Packaging Decisions) assumed complete. Feature 027 (Product Catalog Management) defined with comprehensive specification. Three-feature product/inventory workflow sequence: 027 (Product Catalog Management - foundation), 028 (Purchase Tracking & Enhanced Costing - data model), 029 (Streamlined Inventory Entry - workflow). Features renumbered: 026 = Deferred Packaging Decisions (complete), 027 = Product Catalog Management (ready), 028/029 = Purchase/Inventory features (planned), 030 = Packaging & Distribution (blocked).
- 2025-12-24: Features 026, 027, 028 complete and merged. Feature 030 (Enhanced Export/Import System) defined with comprehensive specification. Feature renumbering: Enhanced Export/Import moved from F031 to F030, Packaging & Distribution moved from F030 to F031. F029 (Streamlined Inventory Entry) ready, F030 (Enhanced Export/Import) ready.
