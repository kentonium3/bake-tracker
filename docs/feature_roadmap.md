# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2026-01-06
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
| 033 | Ingredient Hierarchy Gap Analysis - Phase 1 | MERGED | Fixed ingredient edit form (parent selection vs level dropdown), fixed ingredients tab display (hierarchy path), implemented core validation (can_change_parent, get_product_count, get_child_count). Phases 2-4 pending as F034-F036. |
| 034 | Ingredient Hierarchy Phase 2 (Integration Fixes) | MERGED | Fixed cascading filters in Product/Inventory tabs, debugged product edit hang, verified recipe integration with cascading selectors and L2-only validation. |
| 035 | Ingredient Hierarchy Phase 3 (Deletion Protection) | MERGED | Deletion protection service (blocks if Products/Recipes/Children reference), snapshot denormalization (preserves historical names), cascade delete for Alias/Crosswalk, field normalization (name→display_name), UI error messages with counts. 9 new tests. |
| 036 | Ingredient Hierarchy Phase 4 (Comprehensive Testing) | MERGED | Full test suite execution (1469 tests, 100% pass rate), manual UI validation (cascading selectors, deletion protection), gap analysis updated to 100% complete. Closes F033-F036 ingredient hierarchy implementation. |
| 037 | Recipe Redesign | MERGED | Template/snapshot architecture, yield modes (fixed/scaled), base/variant relationships, recipe components with cycle detection, historical cost accuracy via immutable snapshots. |
| 038 | UI Mode Restructure | MERGED | 5-mode workflow (CATALOG/PLAN/SHOP/PRODUCE/OBSERVE), mode-specific dashboards, consistent tab layouts, keyboard shortcuts (Ctrl+1-5). |
| 039 | Planning Workspace | MERGED | Automatic batch calculation, Event→FinishedGoods→Recipes workflow, ingredient aggregation with FIFO costing, assembly feasibility validation, batch optimization (15% waste threshold). |

---

## In Progress

| # | Name | Priority | Dependencies | Status |
|---|------|----------|--------------|--------|
| 040 | Import/Export System Upgrade (v4.0) | **CRITICAL (P0)** | F037 ✅, F039 ✅ | 📝 Ready for Implementation |

---

## Planned Features

| # | Name | Priority | Dependencies | Status |
|---|------|----------|--------------|--------|
| 041 | Manual Inventory Adjustments | MEDIUM | F040 (bulk adjustments) | Spec Complete (_F040 → _F041) |
| 042 | Shelf Life & Freshness Tracking | MEDIUM | Ingredient/Inventory models ✅ | Spec Complete (_F041 → _F042) |
| 043 | Purchase Workflow UI & Monitoring | MEDIUM | F040 ✅ | Needs Rewrite (_F042 → _F043) |
| 044 | Finished Goods Inventory | LOW | F037 ✅ | Spec Complete (_F043 → _F044) |
| 045 | Packaging & Distribution | LOW | User testing complete | Blocked |

---

## Implementation Order

**Current:** F040 (Import/Export System Upgrade) - CRITICAL PATH

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
26. ~~**Feature 033** - Ingredient Hierarchy Gap Analysis - Phase 1~~ ✅ COMPLETE
27. ~~**Feature 034** - Ingredient Hierarchy Phase 2 (Integration Fixes)~~ ✅ COMPLETE
28. ~~**Feature 035** - Ingredient Hierarchy Phase 3 (Deletion Protection)~~ ✅ COMPLETE
29. ~~**Feature 036** - Ingredient Hierarchy Phase 4 (Comprehensive Testing)~~ ✅ COMPLETE
30. ~~**Feature 037** - Recipe Redesign~~ ✅ COMPLETE
31. ~~**Feature 038** - UI Mode Restructure~~ ✅ COMPLETE
32. ~~**Feature 039** - Planning Workspace~~ ✅ COMPLETE
33. **Feature 040** - Import/Export System Upgrade (v4.0) ⚙️ **CURRENT - CRITICAL PATH**
34. **Feature 041** - Manual Inventory Adjustments (NEXT - awaiting F040)
35. **Feature 042** - Shelf Life & Freshness Tracking
36. **Feature 043** - Purchase Workflow UI & Monitoring (needs spec rewrite)
37. **Feature 044** - Finished Goods Inventory
38. **Feature 045** - Packaging & Distribution

---

## Feature Descriptions

### Feature 040: Import/Export System Upgrade (v4.0)

**Status:** 📝 Ready for Implementation (Specification Complete 2026-01-06)

**Priority:** **CRITICAL (P0 - BLOCKS USER TESTING)**

**Dependencies:** F037 Recipe Redesign ✅, F039 Planning Workspace ✅

**Problem:** F037 and F039 introduced schema changes that break current import/export system (v3.6). Cannot import recipes with new yield modes/variants structure, cannot configure events with output_mode, sample data files outdated, BT Mobile workflows undefined. Result: **Cannot proceed with user testing** of F037/F038/F039.

**Solution:** Upgrade import/export to v4.0 schema with three-part implementation:

**Part 1: Core Schema Upgrade (F037/F039)**
- Recipe import/export with yield modes, base ingredients, variants
- Event import/export with output_mode, EventAssemblyTarget
- Schema version bump to 4.0, no backward compatibility

**Part 2: BT Mobile Purchase Import**
- JSON schema for UPC-based purchases from BT Mobile app
- UPC → Product matching with resolution UI for unknown codes
- Auto-create InventoryItem records from purchases
- Service layer only (no BT Mobile app development)

**Part 3: BT Mobile Inventory Updates**
- JSON schema for percentage-based inventory corrections
- Percentage → Quantity calculation algorithm
- FIFO inventory item selection and adjustment
- Physical count correction via InventoryDepletion records

**Deliverables:**
- `import_all_from_json_v4()` with new recipe/event schemas
- `import_purchases_from_bt_mobile()` for purchase workflow
- `import_inventory_updates_from_bt_mobile()` for inventory corrections
- Updated sample_data files (v4.0 schema)
- Unknown UPC resolution dialog
- CLI + programmatic interfaces

**Implementation Phases:**
1. Core Schema Updates (12-16 hours): F037/F039 import/export, schema v4.0
2. BT Mobile Workflows (10-14 hours): Purchase/inventory import handlers
3. Testing & Documentation (8-12 hours): Unit/integration tests, sample data

**Blocks:** User testing of F037/F038/F039, sample data imports

**Effort:** 36-49 hours (4.5-6 working days)

**Design Document:** `docs/design/F040_import_export_upgrade.md`

---

### Feature 037: Recipe Redesign

**Status:** COMPLETE ✅ (Merged 2026-01-06)

**Dependencies:** F031 Ingredient Hierarchy ✅, F036 Testing ✅

**Problem:** Recipe changes retroactively corrupted historical production costs. No base/variant relationships (duplicate recipes for similar items). No batch scaling (3x recipe requires 3 separate production runs).

**Solution:** Template/snapshot architecture with immutable production instances.

**Delivered:**
- Recipe snapshots captured at production time (immutable, linked to ProductionRun)
- Yield modes: fixed (absolute quantities) and scaled (multiplier-based)
- Base/variant relationships via self-referential base_recipe_id FK
- Recipe components (sub-recipes) with cycle detection and depth limits
- Historical cost accuracy via snapshot-based calculations
- Service layer: snapshot creation, variant management, cost calculations
- UI: Recipe list with base/variant tree view, scaling inputs on production form

**Impact:** Preserves historical accuracy (production costs reflect actual recipes used), simplifies variant management, enables scaling workflows, supports recipe evolution tracking.

**Design Document:** `docs/design/F037_recipe_redesign.md`

---

### Feature 038: UI Mode Restructure

**Status:** COMPLETE ✅ (Merged 2026-01-06)

**Dependencies:** None (UI-only reorganization, no schema changes)

**Problem:** Flat 11-tab navigation with no workflow guidance, inconsistent tab layouts, no state visibility, unclear entry points.

**Solution:** 5-mode workflow architecture organizing UI by work activity (not entity type).

**Delivered:**
- Mode containers: CATALOG, PLAN, SHOP, PRODUCE, OBSERVE
- Mode-specific dashboards with quick stats, recent activity, quick actions
- Tab reorganization into appropriate modes
- Standard tab layout: consistent header/search/filter/actions/grid pattern
- Navigation: Horizontal mode switcher, keyboard shortcuts (Ctrl+1-5)
- Bundle terminology aligned (Bundle=FinishedGood throughout UI)

**Mode Organization:**
- **CATALOG**: Ingredients, Products, Recipes, Finished Units, Finished Goods, Packages
- **PLAN**: Events, Planning Workspace
- **SHOP**: Shopping Lists, Purchases (future), My Pantry
- **PRODUCE**: Production Runs, Assembly, Packaging (future)
- **OBSERVE**: Dashboard, Event Status, Reports

**Impact:** Reduces "Where do I start?" confusion, provides workflow guidance, improves state visibility, standardizes UI patterns.

**Design Document:** `docs/design/F038_ui_mode_restructure.md`

---

### Feature 039: Planning Workspace

**Status:** COMPLETE ✅ (Merged 2026-01-06)

**Dependencies:** F037 Recipe Redesign ✅, F038 UI Mode Restructure ✅

**Problem:** THE CORE VALUE PROPOSITION - Automatic batch calculation solves Marianne's Christmas 2024 underproduction issue. Manual batch calculations consistently lead to errors causing event shortfalls.

**Solution:** Event-scoped planning workspace with automatic batch calculation from Event → FinishedGoods → Recipes → Inventory → Production workflow.

**Delivered:**
- Event.output_mode field (BULK_COUNT, BUNDLED, PACKAGED)
- Automatic batch calculation with 15% waste threshold optimization
- Ingredient aggregation across all recipes with FIFO cost estimation
- Assembly feasibility validation (check component availability)
- Shopping list generation with missing ingredients
- Production plan with optimal batch counts
- Service layer: PlanningService with batch optimization algorithm
- UI: Wizard-style interface (Calculate → Shop → Produce → Assemble phases)

**Key Algorithm:** 
```
Required: 150 cookies
Recipe yield: 48 cookies/batch
Initial: 150 ÷ 48 = 3.125 batches
Waste: 0.125 × 48 = 6 cookies (12.5% waste) ✓ Under threshold
Result: Make 3 batches (144 cookies, -6 shortfall acceptable)
```

**Impact:** Eliminates manual calculation errors, prevents underproduction for events, provides confidence in planning accuracy, reduces waste through optimization.

**Design Document:** `docs/design/F039_PLANNING_WORKSPACE_SPEC.md`

---

### Feature 041: Manual Inventory Adjustments

**Status:** Spec Complete (awaiting F040 implementation)

**Dependencies:** F040 Import/Export Upgrade ✅ (bulk adjustments)

**Problem:** Real-world inventory changes occur outside app (spoilage, gifts, corrections, ad hoc usage). System only tracks automatic depletions. Inventory drifts from reality, planning becomes unreliable.

**Solution:** Manual adjustment UI for individual inventory corrections, complementary to F040 bulk adjustments.

**Planned Deliverables:**
- [Adjust] button on inventory items
- Adjustment dialog with depletion reason selection
- Reasons: SPOILAGE, GIFT, CORRECTION, AD_HOC_USAGE, OTHER
- Validation: prevent negative inventory, notes required for OTHER
- Integration with existing InventoryDepletion model
- Audit trail: who, when, why, how much, notes

**Relationship to F040:**
- F040 handles **bulk** adjustments via JSON import (scan 20 items, import)
- F041 handles **individual** adjustments via UI dialog (click one item)
- Both use same InventoryDepletion model
- Complementary workflows, no conflict

**Effort:** 8-12 hours (1-1.5 days)

**Design Document:** `docs/design/_F041_MANUAL_INVENTORY_ADJUSTMENTS_SPEC.md` (renamed from _F040)

---

### Feature 042: Shelf Life & Freshness Tracking

**Status:** Spec Complete

**Dependencies:** Ingredient/Inventory models ✅

**Planned:** Enhanced expiration tracking with shelf life intelligence.

**Design Document:** `docs/design/_F042_shelf_life_freshness_tracking.md` (renamed from _F041)

---

### Feature 043: Purchase Workflow UI & Monitoring

**Status:** Needs Spec Rewrite (reduced scope from original _F042)

**Dependencies:** F040 Import/Export Upgrade ✅ (service layer complete)

**Problem:** Original spec had significant overlap with F040. Service layer now implemented in F040.

**New Scope (UI layer only):**
- File monitoring (auto-detect purchase/inventory JSON files in sync folder)
- Manual UI purchase entry form
- CSV import channel for bulk purchases
- Purchase history UI and reporting
- Integration with F040 import handlers (service layer)

**Effort:** 15-20 hours (UI layer only)

**Design Document:** `docs/design/_F043_purchase_workflow_ai_assist.md` (needs rewrite, renamed from _F042)

---

### Feature 044: Finished Goods Inventory

**Status:** Spec Complete

**Dependencies:** F037 Recipe Redesign ✅

**Planned:** Service layer for finished goods inventory management and validation.

**Design Document:** `docs/design/_F044_finished_goods_inventory.md` (renamed from _F043)

---

### Feature 045: Packaging & Distribution

**Status:** Blocked (awaiting user testing completion)

**Scope:** PyInstaller executable, Inno Setup installer, Windows distribution.

---

## Key Decisions

### 2026-01-06
- **Feature 037-039 Complete:** Recipe Redesign, UI Mode Restructure, and Planning Workspace all merged to main. Major milestone: automatic batch calculation (THE core value proposition) now operational.
- **Feature 040 Specification Complete:** Import/Export System Upgrade (v4.0) specification created. Three-part solution: (1) Core schema upgrade for F037/F039, (2) BT Mobile purchase import, (3) BT Mobile inventory updates. CRITICAL PATH - blocks user testing.
- **Feature Reconciliation:** Analyzed overlap between Import/Export upgrade and existing specs. Key findings:
  - _F040 Manual Inventory Adjustments: NO CONFLICT - complementary features (bulk vs individual adjustments)
  - _F042 Purchase Workflow: SIGNIFICANT OVERLAP - split into F040 (service layer) and F043 (UI layer)
- **Spec File Renumbering Required:**
  - _F040 → _F041 (Manual Inventory Adjustments)
  - _F041 → _F042 (Shelf Life & Freshness Tracking)  
  - _F042 → _F043 (Purchase Workflow - needs rewrite for reduced scope)
  - _F043 → _F044 (Finished Goods Inventory)
- **Implementation Priority:** F040 is P0 CRITICAL PATH - must complete before user testing can proceed on F037/F038/F039.

### 2026-01-05
- **Feature 037 & 038 In Progress:** Recipe Redesign and UI Mode Restructure both entered Spec-Kitty implementation phase.
- **Planning Workspace Priority:** Identified as CRITICAL (P0) - THE core value proposition for automatic batch calculation solving Marianne's underproduction problem.
- **Feature Renumbering:** Inserted Planning Workspace as F039, renumbering subsequent features:
  - Planning Workspace: NEW → F039 (CRITICAL P0 - next spec)
  - Manual Inventory Adjustments: NEW → F040
  - Shelf Life & Freshness Tracking: F041 → F041 (no change)
  - Purchase Workflow & AI Assist: F039 → F042
  - Finished Goods Inventory: F040 → F043
  - Packaging & Distribution: F041 → F044
- **Spec File Naming:** Existing specs _F039, _F040 will need renumbering to _F042, _F043 respectively.
- **Architecture Validation:** Confirmed Bundle concept correctly modeled as FinishedGood (two-tier hierarchy: FinishedUnit from recipes → FinishedGood assemblies). No schema changes needed for F038.

### 2026-01-03
- **Feature 035 Complete:** Ingredient Hierarchy Phase 3 (Deletion Protection) merged. Deletion protection service blocks when Products/Recipes/Children reference ingredient, cascade delete for Alias/Crosswalk, snapshot denormalization preserves historical names. 9 new tests.
- **Feature 036 Complete:** Ingredient Hierarchy Phase 4 (Comprehensive Testing) merged. Full test suite execution (1469 passed, 0 failed), manual UI validation for cascading selectors and deletion protection, gap analysis updated to 100% complete.
- **F033-F036 Ingredient Hierarchy Implementation Complete:** All 4 phases merged. Overall completion: 100%. System production-ready with:
  - 3-level hierarchy (L0→L1→L2) with cascading selectors
  - Leaf-only validation for recipes and products
  - Deletion protection with accurate count messages
  - All 23 functional requirements verified
- **Bug Found During Testing:** Production database missing `snapshot_ingredients` columns (`ingredient_name_snapshot`, `parent_l1_name_snapshot`, `parent_l0_name_snapshot`). Fixed via ALTER TABLE.
- **Next Feature Ready:** F037 (Recipe Redesign) unblocked, dependencies satisfied.

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
- 2025-12-04 through 2025-12-25: Progressive feature completions
- 2025-12-26: Feature 030 complete. Four-feature product/inventory/import sequence complete.
- 2025-12-30: Phase 2 Architecture Complete. F031-F032 merged. F033 gap analysis created.
- 2026-01-02: F033 Phase 1 complete. F034 complete. Feature renumbering.
- 2026-01-03: F035-F036 complete. F033-F036 ingredient hierarchy 100% complete. System production-ready.
- 2026-01-05: F037-F038 in progress. F039 prioritized as CRITICAL (P0). Feature renumbering.
- 2026-01-06: **F037-F039 Complete and Merged.** Major milestone: Recipe Redesign, UI Mode Restructure, and Planning Workspace operational. **F040 Import/Export System Upgrade specification complete** - CRITICAL PATH blocking user testing. Feature reconciliation completed: _F040 through _F043 require renumbering, _F042 requires spec rewrite for reduced scope.
