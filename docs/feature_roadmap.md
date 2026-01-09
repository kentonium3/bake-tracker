# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2026-01-08
**Workflow:** Spec-Kitty driven development

---

## Executive Summary

**Current Status**: Post-user testing pivot to foundational workflows

**Recent Milestone**: F037-F041 complete (Recipe Redesign, UI Mode Restructure, Planning Workspace, Import/Export v4.0, Manual Inventory Adjustments)

**User Testing Outcome**: Mode structure validated ✅, but blocking UI issues discovered + missing foundational features identified

**New Direction**: Fix UI issues (F042), then implement foundational workflows (F043-F047) before previously planned features

**Timeline**: ~3 weeks for foundational work, then user testing round 2

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
| 038 | UI Mode Restructure | MERGED | 5-mode workflow (CATALOG/PLAN/PURCHASE/MAKE/OBSERVE), mode-specific dashboards, consistent tab layouts, keyboard shortcuts (Ctrl+1-5). Mode names: Shop→Purchase, Produce→Make. |
| 039 | Planning Workspace | MERGED | Automatic batch calculation, Event→FinishedGoods→Recipes workflow, ingredient aggregation with FIFO costing, assembly feasibility validation, batch optimization (15% waste threshold). |
| 040 | Import/Export System Upgrade (v4.0) | MERGED | Schema v4.0 with F037/F039 fields, BT Mobile purchase import (UPC matching, resolution dialog), BT Mobile inventory updates (FIFO, percentage calculation), atomic rollback. 10 work packages, 1721 tests. |
| 041 | Manual Inventory Adjustments | MERGED | Individual inventory corrections via UI dialog, depletion reason tracking (SPOILAGE, GIFT, CORRECTION, AD_HOC_USAGE), validation preventing negative inventory, audit trail, complementary to F040 bulk adjustments. |

---

## In Progress

| # | Name | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 042 | UI Polish & Layout Fixes | **P0 - BLOCKING** | 14-20 hours (2-3 days) | ✅ URGENT FIX COMPLETE |

**F042 Urgent Fix Applied** (2026-01-08):
- ✅ Dashboard headers compacted (13-17 lines → 1-2 lines)
- ✅ Legacy vertical stats widgets removed from all dashboards
- ✅ Stats display inline in header only via `_format_inline_stats()`
- ✅ Data grids now expand to fill available vertical space (20+ rows visible)
- ✅ Removed redundant "Production Runs"/"Assembly Runs" nested tabview in MAKE mode
- ✅ Inventory tab: separate L0/L1/L2 columns (already implemented)
- ✅ Ingredients tab: hierarchy names now display in correct columns by level
- ✅ Cascading filters match Product Catalog pattern

**Deferred to Tech Debt** (TD-007):
- Ingredient edit form hierarchy level safeguards (low priority)

**F042 Scope**: Layout fixes, header compaction, filter consistency, mode renames (Shop→Purchase, Produce→Make)

---

## Foundational Workflows (F043-F047)

**Status**: Required before previously planned features
**Rationale**: Cannot test end-to-end workflows without these foundations

| # | Name | Priority | Effort | Dependencies |
|---|------|----------|--------|--------------|
| 043 | Purchases Tab Implementation | P1 - FOUNDATIONAL | 12-16 hours | F042 ✅ |
| 044 | Finished Units Functionality & UI | P1 - FOUNDATIONAL | 16-20 hours | F042 ✅ |
| 045 | Finished Goods Functionality & UI | P1 - FOUNDATIONAL | 20-24 hours | F044 ✅ |
| 046 | Shopping Lists Tab Implementation | P1 - FOUNDATIONAL | 12-16 hours | F042 ✅, F045 ✅ |
| 047 | Assembly Workflows | P1 - FOUNDATIONAL | 24-30 hours | F045 ✅ |

**Total Foundational Work**: 84-106 hours (10-13 days, ~3 weeks)

**Missing Functionality** (discovered in user testing):
- Purchase history/entry (Purchases tab not implemented)
- Finished Units definition (buttons go nowhere)
- Finished Goods definition (buttons go nowhere)
- Shopping list generation/export (tab not implemented)
- Assembly recording (tab not implemented)

**Blocks**: Complete Plan → Shop → Make → Assemble → Deliver workflow testing

---

## Deferred Features (F0XX Queue)

**Rationale**: Moved to F0XX numbering to avoid constant renumbering as new features are inserted

| Original # | Name | New # | Status | Spec File |
|------------|------|-------|--------|-----------|
| F042 | Shelf Life & Freshness Tracking | F0XX | Deferred | `_F0XX_shelf_life_freshness_tracking.md` |
| F043 | Purchase Workflow Monitoring | F0XX | Deferred (service layer in F040) | `_F0XX_purchase_workflow_monitoring.md` |
| F044 | Advanced Finished Goods | F0XX | May not be needed after F045 | `_F0XX_advanced_finished_goods.md` |
| F045 | Packaging & Distribution | F0XX | Deferred to Phase 3 | (no spec yet) |

**F0XX Rationale**: "Future queue, specific number TBD" - avoids renumbering churn as new features are inserted during foundational work

---

## Implementation Order

**Phase 0: Recent Completions** ✅
1. ~~**Feature 037** - Recipe Redesign~~ ✅
2. ~~**Feature 038** - UI Mode Restructure~~ ✅
3. ~~**Feature 039** - Planning Workspace~~ ✅
4. ~~**Feature 040** - Import/Export System Upgrade (v4.0)~~ ✅
5. ~~**Feature 041** - Manual Inventory Adjustments~~ ✅
6. ~~**USER TESTING ROUND 1**~~ ✅ (2026-01-07)

**Phase 1: UI Polish (Week 1)** 🎯 CURRENT
7. **Feature 042** - UI Polish & Layout Fixes → 2026-01-10

**Phase 2: Foundational Workflows (Weeks 2-4)**
8. **Feature 043** - Purchases Tab Implementation → 2026-01-12
9. **Feature 044** - Finished Units Functionality & UI → 2026-01-15
10. **Feature 045** - Finished Goods Functionality & UI → 2026-01-18
11. **Feature 046** - Shopping Lists Tab Implementation → 2026-01-20
12. **Feature 047** - Assembly Workflows → 2026-01-24

**Phase 3: User Testing Round 2** (Week 5+)
13. **USER TESTING ROUND 2** - Complete Plan → Make → Assemble → Deliver cycle → 2026-01-27+
14. Prioritize F0XX features based on user feedback
15. Plan Phase 3 (web migration) architecture

---

## Success Criteria

### After F042 (UI Polish)
- ✅ User can browse ingredients/products effectively (20+ rows visible)
- ✅ Mode navigation feels professional and polished
- ✅ Stats display accurate data
- ✅ Filters work consistently across tabs (match Product Catalog pattern)
- ✅ Headers compact (3-4 lines max across all modes)

### After F043-F047 (Foundational Workflows)
- ✅ User can complete Plan → Shop → Make → Assemble → Deliver cycle
- ✅ All tabs in all modes functional (no dead buttons)
- ✅ Purchases, Finished Units, Finished Goods, Shopping Lists, Assembly all operational
- ✅ Event planning can use defined finished goods
- ✅ Production cycle can be completed end-to-end

### Ready for F0XX (Future Features)
- ✅ Foundational workflows solid and tested
- ✅ User provides feedback on F0XX priorities
- ✅ Mode structure validated with complete workflows
- ✅ System ready for Phase 3 (web migration) planning

---

## Key Decisions

### 2026-01-07 (Post-User Testing Pivot)
- **User Testing Round 1 Complete**: Tested F037-F041 feature group. Mode structure validated ✅, but blocking UI issues discovered.
- **Blocking Issues Identified**: 
  - Ingredient/Product grids only 2 rows high (unmanageable)
  - Hierarchy columns concatenated (should be separate)
  - Stats showing "0" (calculation bug)
  - Headers way too large (ALL modes)
  - Filters "very odd" (should match Product Catalog)
- **Missing Foundational Features**: Purchases, Finished Units, Finished Goods, Shopping Lists, Assembly tabs not implemented or non-functional
- **Pivot Decision**: Fix UI issues (F042) before implementing foundational workflows (F043-F047)
- **Feature Renumbering**: 
  - F042: UI Polish & Layout Fixes (NEW - P0 BLOCKING)
  - F043-F047: Foundational workflows (NEW - P1 REQUIRED)
  - Old F042-F045: Moved to F0XX queue (deferred)
- **F0XX Numbering Introduced**: "Future queue, specific number TBD" to avoid constant renumbering
- **Timeline**: ~3 weeks for foundational work, then user testing round 2
- **User Feedback**: "Mode-based organization works well" ✅, "UI issues are distracting" ⚠️

### 2026-01-06
- **Feature 037-039 Complete**: Recipe Redesign, UI Mode Restructure, Planning Workspace operational
- **Feature 040 Complete**: Import/Export v4.0 with BT Mobile workflows
- **Feature 041 Complete**: Manual Inventory Adjustments
- **Ready for User Testing**: F037-F041 feature group complete

---

## Technical Debt

### TD-001: Schema Cleanup
**Status:** COMPLETE ✅

### TD-002: Unit Standardization
**Status:** COMPLETE ✅

### TD-003: Catalog Import Test Schema Mismatch
**Status:** COMPLETE ✅

### TD-006: Deprecate expiration_date Field
**Status:** OPEN
**Priority:** Medium
**Document:** `docs/technical-debt/TD-006_expiration_date_deprecated.md`
**Related:** F0XX Shelf Life & Freshness Tracking

---

## Document History

- 2025-12-03: Initial creation
- 2025-12-04 through 2025-12-25: Progressive feature completions
- 2025-12-26: Feature 030 complete
- 2025-12-30: Phase 2 Architecture Complete (F031-F032)
- 2026-01-02: F033 Phase 1, F034 complete
- 2026-01-03: F035-F036 complete, ingredient hierarchy 100% complete
- 2026-01-05: F037-F038 in progress, F039 prioritized
- 2026-01-06: F037-F039 complete and merged, F040 specification complete
- 2026-01-07: **MAJOR PIVOT** - F040-F041 complete, user testing round 1 complete, blocking UI issues identified, roadmap restructured:
  - F042: UI Polish & Layout Fixes (NEW - P0)
  - F043-F047: Foundational workflows (NEW - P1)
  - Old F042-F045: Moved to F0XX queue (deferred)
  - F0XX numbering introduced for future features
  - Timeline: ~3 weeks for foundational work
- 2026-01-08: **F042 URGENT FIX** - Critical layout issues resolved:
  - Removed legacy vertical stats widgets from all dashboards (base_dashboard.py)
  - Headers compacted from 13-17 lines to 1-2 lines
  - Data grids now expand properly (20+ rows visible)
  - Removed redundant nested tabview in MAKE Production Dashboard
  - Fixed ingredients tab hierarchy display (names in correct columns by level)
  - Logged TD-007 for ingredient edit form safeguards (deferred)
