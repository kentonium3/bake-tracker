# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2025-12-20
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

---

## In Progress

*No features currently in progress.*

---

## Planned Features

| # | Name | Priority | Dependencies | Status |
|---|------|----------|--------------|--------|
| 025 | Packaging & Distribution | LOW | User testing complete | Blocked |

---

## Implementation Order

**Current:** None - awaiting user testing

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
18. **Feature 025** - Packaging & Distribution

---

## Feature Descriptions

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

### Feature 025: Packaging & Distribution

**Status:** Blocked (awaiting user testing completion)

**Scope:** PyInstaller executable, Inno Setup installer, Windows distribution.

---

## Key Decisions

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
