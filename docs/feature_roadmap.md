# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2025-12-30
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
| 031 | Ingredient Hierarchy | MERGED | Schema support (parent_ingredient_id, hierarchy_level), import/export support, hierarchical ingredient selection in product edit form. |
| 032 | Ingredient Hierarchy UI Completion | MERGED | UI implementation across all tabs: hierarchy columns, cascading dropdowns, filters, read-only displays. Replaced deprecated category field. |
| 033 | Ingredient Hierarchy Gap Analysis | MERGED | Comprehensive analysis of F031+F032 implementation revealing 55% incomplete (schema 100%, services 60%, UI 30%, validation 10%). Identified 5 critical blockers, missing service methods, broken cascading logic. Provides roadmap for completion. |

---

## In Progress

*No features currently in progress.*

---

## Planned Features

| # | Name | Priority | Dependencies | Status |
|---|------|----------|--------------|--------|
| 034 | Recipe Redesign | HIGH | F031, F032, F033 | Ready |
| 035 | UI Mode Restructure | HIGH | Phase 2 Architecture | Ready |
| 036 | Purchase Workflow & AI Assist | HIGH | F035 | Ready |
| 037 | Finished Goods Inventory | MEDIUM | F034 | Ready |
| 038 | Packaging & Distribution | LOW | User testing complete | Blocked |

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
24. ~~**Feature 031** - Ingredient Hierarchy~~ ✅ COMPLETE
25. ~~**Feature 032** - Ingredient Hierarchy UI Completion~~ ✅ COMPLETE
26. ~~**Feature 033** - Ingredient Hierarchy Gap Analysis~~ ✅ COMPLETE
27. **Feature 034** - Recipe Redesign
28. **Feature 035** - UI Mode Restructure
29. **Feature 036** - Purchase Workflow & AI Assist
30. **Feature 037** - Finished Goods Inventory
31. **Feature 038** - Packaging & Distribution

---

## Feature Descriptions

### Feature 033: Ingredient Hierarchy Gap Analysis

**Status:** COMPLETE ✅ (Merged 2025-12-30)

**Dependencies:** Features 031 (Ingredient Hierarchy), 032 (Ingredient Hierarchy UI Completion)

**Problem:** F031+F032 implementation incomplete and inconsistent (~45% complete overall). Schema exists but critical gaps across service layer (60%), UI layer (30%), and validation (10%). Five critical blockers prevent production readiness: wrong mental model in edit form, incorrect tab display, zero edit validation, broken cascading filters, and Product edit form hang.

**Solution:** Comprehensive gap analysis documenting all implementation deficiencies against requirements, providing roadmap for completion.

**Delivered:**

**Gap Analysis:**
1. **Requirement Coverage Analysis:** 
   - Mapped all 23 functional requirements to implementation status
   - Identified completion rates per layer (Schema 100%, Services 60%, UI 30%, Validation 10%)
   - Documented 15+ missing service methods
   - Listed 20+ broken UI behaviors

2. **Critical Blocker Identification:**
   - Blocker 1: Ingredient edit form uses wrong mental model (level dropdown vs parent selection)
   - Blocker 2: Ingredients tab shows flat list with deprecated fields instead of hierarchical view
   - Blocker 3: Zero edit validation prevents orphaning products/recipes
   - Blocker 4: Cascading filters broken (L1 doesn't update when L0 changes)
   - Blocker 5: Product edit form hangs on open

3. **Implementation Roadmap:**
   - 4-phase plan with effort estimates (50-72 hours total)
   - Phase 1: Critical fixes (edit form, tab display, validation) - 20-26 hours
   - Phase 2: Integration fixes (cascading filters, product edit, recipe verification) - 12-20 hours
   - Phase 3: Polish & auto-update (slug generation, cascading updates) - 10-14 hours
   - Phase 4: Comprehensive testing - 8-12 hours

4. **Missing Service Methods Documented:**
   ```python
   # Validation Services
   can_change_parent(ingredient_id, new_parent_id) → (bool, str)
   get_product_count(ingredient_id) → int
   get_recipe_usage_count(ingredient_id) → int
   get_child_count(ingredient_id) → int
   
   # Auto-Update Services
   update_ingredient_hierarchy(ingredient_id, new_parent_id)
   update_related_products(ingredient_id)
   update_related_recipes(ingredient_id)
   
   # Slug Generation
   generate_unique_slug(display_name, session) → str
   validate_slug_unique(slug, exclude_id, session) → bool
   ```

5. **Acceptance Checklist:**
   - 9 must-have items (blocking)
   - 6 should-have items (high priority)
   - 3 nice-to-have items (can defer)

**Impact:** Provides actionable roadmap for completing ingredient hierarchy implementation. Estimated 7-10 working days to reach production-ready state. Serves as specification input for subsequent implementation features.

**Design Document:** `/docs/design/F033_ingredient_hierarchy_gap_analysis.md`

---

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

**Test Coverage:**
- 47 service-layer tests covering all import/export scenarios
- 11 integration tests for FK resolution workflows
- Manual testing of UI import wizard with missing entities

**Design Document:** `docs/design/F030_enhanced_export_import.md`

---

### Feature 029: Streamlined Inventory Entry

**Status:** COMPLETE ✅ (Merged 2025-12-25)

**Problem:** Adding inventory after shopping trips is tedious. Massive product dropdown requires excessive scrolling. No filtering, sorting, or recency intelligence. Blank defaults force repetitive data entry. No way to quickly add unknown products. Price display doesn't show when product was last purchased.

**Solution:** Type-ahead filtering, recency intelligence, session memory, inline product creation, smart defaults, enhanced price display.

**Delivered:**
- Type-ahead product filter (live search as you type)
- Recency sort (recently added products appear first in session)
- Session memory (maintains filter/product selection across multiple adds)
- Inline product creation button (add unknown products without leaving dialog)
- Smart date default (today's date)
- Smart supplier default (last supplier used for this product)
- Enhanced price display (shows last purchase price with date/supplier)
- Quantity validation (prevents negative/zero entries)
- Auto-focus on quantity after product selection
- Status messages for user feedback

**Workflow Improvement:** "I just shopped at Costco with 20 items" now takes ~2 minutes instead of ~15 minutes.

**Design Document:** `docs/design/F029_streamlined_inventory_entry.md`

---

### Feature 028: Purchase Tracking & Enhanced Costing

**Status:** COMPLETE ✅ (Merged 2025-12-24)

**Dependencies:** Features 027 (Product Catalog Management)

**Problem:** No way to track when/where products were purchased or at what price. FIFO costing uses placeholder $0 values. Cannot analyze price trends or supplier costs over time.

**Solution:** Purchase entity for price history, FIFO using actual purchase prices, supplier dropdown in Add Inventory dialog.

**Delivered:**
- New `Purchase` entity (links to Product, Supplier, purchase_date, unit_price, quantity, total_cost)
- InventoryAddition table now has `purchase_id` FK
- FIFO consumption uses `Purchase.unit_price` instead of placeholder $0
- Add Inventory dialog includes supplier dropdown
- Service layer: `PurchaseService` with CRUD operations
- Price history queries for trending analysis
- Supplier cost analysis capabilities

**Impact:** Accurate costing for production runs, shopping list price estimates, and cost trend analysis.

**Design Document:** `docs/design/F028_purchase_tracking_enhanced_costing.md`

---

### Feature 027: Product Catalog Management

**Status:** COMPLETE ✅ (Merged 2025-12-24)

**Problem:** No UI for managing product catalog. Products scattered across dialogs without centralized view. Cannot filter, search, or view purchase history. No way to mark products as hidden or set preferred products.

**Solution:** Dedicated Products tab with CRUD operations, filtering, purchase history.

**Delivered:**
- Products tab with searchable grid (product name, brand, ingredient, supplier, package size)
- Filter by ingredient (hierarchical dropdown)
- Add/Edit/Delete product operations
- Purchase history view per product (dates, quantities, prices, suppliers)
- New `Supplier` entity with name and notes fields
- `preferred_supplier` field on Product
- `is_hidden` flag on Product (for discontinued items)
- Inline product creation from Inventory dialog

**Design Document:** `docs/design/F027_product_catalog_management.md`

---

### Feature 026: Deferred Packaging Decisions

**Status:** COMPLETE ✅ (Merged 2025-12-23)

**Problem:** Event planning forces premature commitment to specific packaging materials. Food decisions (recipes, quantities) happen first. Packaging aesthetics decided later. Current system requires specific materials upfront, blocking natural workflow.

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

### 2025-12-30
- **Feature 031 Complete:** Ingredient Hierarchy schema and services merged. Three-tier taxonomy (L0/L1/L2), self-referential parent_ingredient_id, hierarchy_level field, ingredient_hierarchy_service.py with tree operations.
- **Feature 032 Complete:** Ingredient Hierarchy UI Completion merged. Replaced all deprecated category UI with hierarchy columns/filters across Ingredients, Products, and Inventory tabs. Cascading dropdowns in edit forms, read-only hierarchy display.
- **Feature 033 Complete:** Ingredient Hierarchy Gap Analysis. Comprehensive analysis revealing F031+F032 implementation 55% incomplete. Identified 5 critical blockers, documented missing service methods, mapped all requirements to implementation status. Provides 50-72 hour roadmap for completion (4 phases). Serves as specification for subsequent implementation work.
- **Phase 2 Architecture Complete:** Five comprehensive design specifications created for Phase 2 requirements:
  - **F031 (Ingredient Hierarchy):** Three-tier hierarchical taxonomy (L0/L1/L2), leaf-only product assignment, AI-assisted migration from flat categories. Blocks recipe redesign.
  - **F034 (Recipe Redesign):** Template/snapshot architecture for immutable production history, base/variant relationships via self-referential FK, simple scaling (1x/2x/3x multiplier). Depends on F031, F033.
  - **F035 (UI Mode Restructure):** 5-mode workflow organization (CATALOG/PLAN/SHOP/PRODUCE/OBSERVE), consistent tab layouts, mode-specific dashboards. UI-only, no schema changes.
  - **F036 (Purchase Workflow & AI Assist):** Multi-channel purchase capture (manual/CSV/AI Studio), UPC matching with learned mappings, batch file import for Phase 2, real-time API for Phase 3. Depends on F035.
  - **F037 (Finished Goods Inventory):** Service layer architecture for inventory management and validation. Data model exists, UI deferred to Phase 3. Depends on F034.
- **Feature Renumbering:** Original F031 (Packaging & Distribution) moved to F038. Gap analysis inserted as F033, subsequent features renumbered F034-F037.
- **Implementation Ready:** All specs include data models, service layers, UI mockups (where applicable), flow diagrams, gap analysis, constitutional compliance checks, and complexity estimates.

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
- 2025-12-30: **Phase 2 Architecture Complete.** Added Features 031-036 design specs (Ingredient Hierarchy, Recipe Redesign, UI Mode Restructure, Purchase Workflow & AI Assist, Finished Goods Inventory). F031 and F032 implemented and merged (Ingredient Hierarchy backend + UI). F033 gap analysis complete (comprehensive implementation analysis revealing 55% completion, 5 critical blockers identified, 50-72 hour roadmap provided). Original F031 (Packaging & Distribution) renumbered to F038. Remaining planned features renumbered: Recipe Redesign (F034), UI Mode Restructure (F035), Purchase Workflow (F036), Finished Goods Inventory (F037).
