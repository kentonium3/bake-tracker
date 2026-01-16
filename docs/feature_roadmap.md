# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2026-01-16
**Workflow:** Spec-Kitty driven development

---

## Executive Summary

**Current Status**: F052-F054 complete. F055 (UI Navigation Cleanup) is next.

**Recent Milestone**: F052 (Hierarchy Admin), F053 (Context-Rich Export), F054 (CLI Parity) all merged

**Test Suite**: 2336 tests

**Next Step**: F055 (UI Navigation Cleanup), then User Testing Round 2

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
| 042 | UI Polish & Layout Fixes | MERGED | Dashboard header compaction (13-17 lines → 1-2 lines), legacy stats widget removal, data grid expansion (20+ rows visible), nested tabview cleanup in MAKE mode, ingredient hierarchy column fixes. |
| 043 | Purchases Tab Implementation | MERGED | Purchases tab CRUD operations in PURCHASE mode, purchase history tracking, supplier integration, cost tracking per purchase. |
| 044 | Finished Units Yield Type Management | MERGED | Yield type authoring moved to Recipe Edit form, Finished Units tab converted to read-only catalog with recipe filter, double-click navigation to Recipe Edit, cascade delete on recipe deletion, per-recipe name uniqueness validation. |
| 045 | Cost Architecture Refactor | MERGED | "Costs on Instances, Not Definitions" principle. Removed stored `unit_cost`/`total_cost` from FinishedUnit/FinishedGood/Composition. Costs now calculated dynamically from ProductionRun/AssemblyRun history. Snap-and-store at transaction time. |
| 046 | Finished Goods, Bundles & Assembly Tracking | MERGED | Added `calculate_current_cost()` methods to FinishedUnit/FinishedGood. Fixed Composition/Package model methods. Fixed assembly_service cost capture. Dynamic cost calculation from production history. |
| 047 | Materials Management System | MERGED | Comprehensive materials management paralleling ingredient system. Material/MaterialProduct/MaterialCategory/MaterialSubcategory models. Non-edible materials (ribbon, boxes, bags) properly separated from ingredients. |
| 048 | Materials UI Rebuild | MERGED | Rebuilt Materials UI to match Ingredients pattern. 3-tab grid structure (Categories, Subcategories, Materials). Consistent with established UI patterns. |
| 049 | Import/Export Phase 1 | MERGED | Complete 16-entity backup capability. Context-rich exports for all catalog entities. Materials catalog import support. Enhanced import service with FK resolution. |
| 050 | Supplier Slug Support | MERGED | Added supplier_slug field for stable FK references. Import/export uses slugs instead of IDs. Backward-compatible with existing data. |
| 051 | Import/Export UI Rationalization | MERGED | Unified import dialog with consistent workflow. Purpose-based import selection (Catalog, Backup, Context-Rich). Improved error handling and log file generation. |
| 052 | Ingredient/Material Hierarchy Admin | MERGED | Hierarchy Admin tab in CATALOG mode for managing ingredient and material taxonomies. Display name management, category/subcategory editing. |
| 053 | Context-Rich Export Fixes | MERGED | File prefix "view_" → "aug_", added Products and Material Products to exports, multi-select checkboxes, "All" option, fixed button text. |
| 054 | CLI Import/Export Parity | MERGED | 16 new CLI commands for backup/restore, catalog, and aug (context-rich) operations. Full Materials support (4 entity types), Supplier CLI, Purchase CLI. Achieves CLI parity with UI for AI-assisted workflows. |

---

## In Progress

| # | Name | Priority | Status |
|---|------|----------|--------|
| 055 | UI Navigation Cleanup | P1 | NEXT |

---

## Next Up

| # | Name | Priority | Status | Notes |
|---|------|----------|--------|-------|
| - | User Testing Round 2 | P0 | PENDING | After F055 complete |

---

## Foundational Workflows (F042-F051)

**Status**: ✅ ALL COMPLETE
**Rationale**: End-to-end workflow testing now possible

| # | Name | Priority | Status |
|---|------|----------|--------|
| 042 | UI Polish & Layout Fixes | P0 - BLOCKING | ✅ COMPLETE |
| 043 | Purchases Tab Implementation | P1 - FOUNDATIONAL | ✅ COMPLETE |
| 044 | Finished Units Yield Type Management | P1 - FOUNDATIONAL | ✅ COMPLETE |
| 045 | Cost Architecture Refactor | P0 - FOUNDATIONAL | ✅ COMPLETE |
| 046 | Finished Goods, Bundles & Assembly Tracking | P1 - FOUNDATIONAL | ✅ COMPLETE |
| 047 | Materials Management System | P1 - FOUNDATIONAL | ✅ COMPLETE |
| 048 | Materials UI Rebuild | P1 - FOUNDATIONAL | ✅ COMPLETE |
| 049 | Import/Export Phase 1 | P1 - FOUNDATIONAL | ✅ COMPLETE |
| 050 | Supplier Slug Support | P1 - FOUNDATIONAL | ✅ COMPLETE |
| 051 | Import/Export UI Rationalization | P1 - FOUNDATIONAL | ✅ COMPLETE |

**Completed** (2026-01-08 through 2026-01-13):
- ✅ F042: Dashboard headers compacted, stats widgets removed, data grids expanded
- ✅ F043: Purchases tab CRUD operations, supplier integration
- ✅ F044: Yield types managed in Recipe Edit, Finished Units tab is read-only catalog
- ✅ F045: "Costs on Instances, Not Definitions" - removed stored cost fields from definition models
- ✅ F046: Dynamic cost calculation methods, fixed assembly cost capture
- ✅ F047: Materials management system paralleling ingredients
- ✅ F048: Materials UI rebuilt to match Ingredients 3-tab pattern
- ✅ F049: Complete 16-entity backup, context-rich exports, materials import
- ✅ F050: Supplier slug support for stable FK references
- ✅ F051: Unified import dialog with purpose-based selection

**Ready For**: F055 (UI Navigation Cleanup), then User Testing Round 2

---

## Deferred Features (F0XX Queue)

**Rationale**: Moved to F0XX numbering to avoid constant renumbering as new features are inserted

| Original # | Name | New # | Status | Spec File |
|------------|------|-------|--------|-----------|
| (old F042) | Shelf Life & Freshness Tracking | F0XX | Deferred | `_F0XX_shelf_life_freshness_tracking.md` |
| (old F043) | Purchase Workflow Monitoring | F0XX | Deferred (service layer in F040) | `_F0XX_purchase_workflow_monitoring.md` |
| (old F044) | Advanced Finished Goods | F0XX | May not be needed after F045 | `_F0XX_advanced_finished_goods.md` |
| (old F045) | Packaging & Distribution | F0XX | Deferred to Phase 4 | (no spec yet) |
| - | Shopping Lists Tab | F0XX | Deferred (originally planned as F048) | (no spec yet) |
| - | Assembly Workflows | F0XX | Deferred (originally planned as F049) | (no spec yet) |

**F0XX Rationale**: "Future queue, specific number TBD" - avoids renumbering churn as new features are inserted during foundational work

**Note**: Original F047-F049 plans (Shopping Lists, Assembly Workflows) were deferred as materials management and import/export improvements took priority based on user testing feedback

---

## Implementation Order

**Phase 0: Recent Completions** ✅
1. ~~**Feature 037** - Recipe Redesign~~ ✅
2. ~~**Feature 038** - UI Mode Restructure~~ ✅
3. ~~**Feature 039** - Planning Workspace~~ ✅
4. ~~**Feature 040** - Import/Export System Upgrade (v4.0)~~ ✅
5. ~~**Feature 041** - Manual Inventory Adjustments~~ ✅
6. ~~**USER TESTING ROUND 1**~~ ✅ (2026-01-07)

**Phase 1: UI Polish & Initial Foundations** ✅
7. ~~**Feature 042** - UI Polish & Layout Fixes~~ ✅ (2026-01-08)
8. ~~**Feature 043** - Purchases Tab Implementation~~ ✅ (2026-01-09)
9. ~~**Feature 044** - Finished Units Yield Type Management~~ ✅ (2026-01-09)

**Phase 2: Remaining Foundational Workflows** ✅
10. ~~**Feature 045** - Cost Architecture Refactor~~ ✅ (2026-01-09)
11. ~~**Feature 046** - Finished Goods, Bundles & Assembly Tracking~~ ✅ (2026-01-10)
12. ~~**Feature 047** - Materials Management System~~ ✅ (2026-01-11)
13. ~~**Feature 048** - Materials UI Rebuild~~ ✅ (2026-01-11)
14. ~~**Feature 049** - Import/Export Phase 1~~ ✅ (2026-01-12)
15. ~~**Feature 050** - Supplier Slug Support~~ ✅ (2026-01-12)
16. ~~**Feature 051** - Import/Export UI Rationalization~~ ✅ (2026-01-13)

**Phase 3: Polish & Final Fixes** 🎯 CURRENT
17. ~~**Feature 052** - Ingredient/Material Hierarchy Admin~~ ✅ (2026-01-15)
18. ~~**Feature 053** - Context-Rich Export Fixes~~ ✅ (2026-01-15)
19. ~~**Feature 054** - CLI Import/Export Parity~~ ✅ (2026-01-15)
20. **Feature 055** - UI Navigation Cleanup (NEXT)
21. **USER TESTING ROUND 2** - Complete Plan → Shop → Make → Assemble → Deliver cycle
22. Prioritize F0XX features based on user feedback
23. Plan Phase 4 (web migration) architecture

---

## Success Criteria

### After F042 (UI Polish) - COMPLETE ✅
- ✅ User can browse ingredients/products effectively (20+ rows visible)
- ✅ Mode navigation feels professional and polished
- ✅ Stats display accurate data
- ✅ Filters work consistently across tabs (match Product Catalog pattern)
- ✅ Headers compact (3-4 lines max across all modes)

### After F043 (Purchases Tab) - COMPLETE ✅
- ✅ Purchases tab functional in PURCHASE mode
- ✅ Purchase history tracking with supplier integration
- ✅ CRUD operations for purchase records
- ✅ Cost tracking per purchase

### After F044 (Finished Units) - COMPLETE ✅
- ✅ Yield types defined inline in Recipe Edit form
- ✅ Finished Units tab shows read-only catalog of all yield types
- ✅ Double-click navigates to parent recipe for editing
- ✅ Recipe filter enables browsing by recipe
- ✅ Validation prevents duplicate names within same recipe

### After F045 (Cost Architecture Refactor) - COMPLETE ✅
- ✅ Cost calculations accurate and consistent across all views
- ✅ FIFO costing properly integrated with new architecture
- ✅ Foundation in place for F046-F048 workflows
- ✅ "Costs on Instances, Not Definitions" principle implemented
- ✅ Stored cost fields removed from definition models

### After F046 (Finished Goods & Assembly Tracking) - COMPLETE ✅
- ✅ `calculate_current_cost()` methods on FinishedUnit/FinishedGood
- ✅ Composition/Package model methods fixed for dynamic costs
- ✅ Assembly service captures actual costs (not hardcoded zeros)
- ✅ 1774 tests pass, all cost calculations verified

### After F047 (Materials Management System) - COMPLETE ✅
- ✅ Material/MaterialProduct/MaterialCategory/MaterialSubcategory models implemented
- ✅ Non-edible materials properly separated from ingredients
- ✅ Materials can be used in assemblies

### After F048 (Materials UI Rebuild) - COMPLETE ✅
- ✅ Materials UI matches Ingredients 3-tab pattern
- ✅ Categories, Subcategories, Materials tabs with grids
- ✅ Consistent filtering and CRUD operations

### After F049 (Import/Export Phase 1) - COMPLETE ✅
- ✅ Complete 16-entity backup capability
- ✅ Context-rich exports for all catalog entities
- ✅ Materials catalog import support

### After F050 (Supplier Slug Support) - COMPLETE ✅
- ✅ Supplier slugs used for stable FK references in import/export
- ✅ Products reference suppliers by slug, not ID

### After F051 (Import/Export UI Rationalization) - COMPLETE ✅
- ✅ Unified import dialog with purpose-based selection
- ✅ Consistent workflow across Catalog, Backup, Context-Rich imports
- ✅ Improved error handling and log generation

### After F052 (Hierarchy Admin) - COMPLETE ✅
- [x] Hierarchy Admin tab in CATALOG mode
- [x] Display name management for ingredients and materials
- [x] Category/subcategory display name management
- [x] Taxonomy structure management

### After F053 (Context-Rich Export Fixes) - COMPLETE ✅
- [x] Files exported with "aug_" prefix
- [x] Products and Material Products exportable
- [x] Multi-select with checkboxes
- [x] "All" option to export all entity types
- [x] Button text reads "Export Context-Rich File"

### After F054 (CLI Import/Export Parity) - COMPLETE ✅
- [x] Backup/restore CLI commands operational
- [x] Catalog import/export via CLI
- [x] Context-rich "aug" CLI commands
- [x] All 16 entities accessible via CLI
- [x] Materials CLI commands (4 entity types)
- [x] Supplier CLI commands
- [x] Purchase CLI commands
- [x] CLI parity with UI achieved
- [x] AI-assisted workflows fully supported
- [x] Mobile JSON ingestion enabled

### After F055 (UI Navigation Cleanup)
- [ ] Modes ordered: Observe, Catalog, Plan, Purchase, Make, Deliver
- [ ] Catalog menu restructured with logical groupings
- [ ] Purchase menu reordered: Inventory, Purchases, Shopping Lists
- [ ] Broken top section removed
- [ ] Tree view removed from Catalog/Inventory
- [ ] Deliver mode placeholder present

### Ready for User Testing Round 2
- [x] F052 complete
- [ ] F055 complete
- [ ] User can complete Plan → Shop → Make → Assemble → Deliver cycle
- [ ] All tabs in all modes functional and polished
- [ ] Materials properly managed separate from ingredients
- [ ] Import/export system complete and intuitive (UI + CLI)
- [ ] CLI enables AI workflows and mobile integration

### Ready for F0XX (Future Features)
- User provides feedback on F0XX priorities
- Mode structure validated with complete workflows
- System ready for Phase 4 (web migration) planning

---

## Key Decisions

### 2026-01-16 (Post-F055 Bug Fix Session)
- **10 User Testing Issues Resolved**: All issues from continued user testing fixed and pushed
- **Cascade Delete Protection Added**: Critical safety feature for import/export system
  - UI shows warning dialog with affected record counts before proceeding
  - CLI rejects risky imports by default, requires `--force` flag to override
  - Protects against accidental data loss when importing ingredients without products or materials without material_products
- **RESTRICT Constraint Detection Added**: Prevents import failures before they happen
  - Detects ingredients referenced by recipes that would cause database RESTRICT violation
  - Shows actionable remediation options (add ingredients, include recipes, or delete affected recipes)
  - Separate warning sections: CASCADE (orange, data loss) vs RESTRICT (red, import will fail)
- **Backup Directory Preference**: Separate from import/export directory for better workflow
- **Import Flow Reordered**: Type-first, file-second is more natural (app needs type to know which directory to open)
- **Reason Code Default**: "CORRECTION" default for inventory adjustments reduces import friction
- **Test Suite**: 2336 tests passing

### 2026-01-15 (F052-F054 Complete, F055 Next)
- **F052 MERGED**: Ingredient/Material Hierarchy Admin - taxonomy management in CATALOG mode
- **F053 MERGED**: Context-Rich Export Fixes - file prefix changed to "aug_", added Products/Material Products, multi-select checkboxes, "All" option
- **F054 MERGED**: CLI Import/Export Parity - 16 new CLI commands achieving full UI parity for AI-assisted workflows
- **F055 Next**: UI Navigation Cleanup - mode reordering, menu restructuring, Deliver placeholder
- **Renumbering**: Original F053 (UI Navigation Cleanup) → F055
- **Spec-Kitty Bug Filed**: Symlink merge bug confirmed and reported to GitHub (worktree symlinks overwrite main repo files)

### 2026-01-13 (Foundational Work Complete)
- **All Foundational Features Complete**: F042-F051 merged, covering UI polish, materials management, and import/export rationalization
- **Scope Evolution**: Original F047-F049 plans (Shopping Lists, Assembly Workflows) deferred as materials and import/export took priority
- **Import/Export Mature**: 16-entity backup, supplier slugs, unified UI, context-rich exports all operational
- **Ready for User Testing Round 2**: Full Plan → Shop → Make → Assemble → Deliver cycle can be tested
- **Repository Cleanup**: Removed obsolete scripts/, templates/, docs/workflows/ directories and archived resolved bugs

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
- 2026-01-09: **F043 COMPLETE** - Purchases Tab Implementation merged:
  - Purchases tab CRUD operations in PURCHASE mode
  - Purchase history tracking with supplier integration
  - Note: Feature number skipped during spec-kitty upgrade (v0.6.4 → v0.10.12)
- 2026-01-09: **F044 COMPLETE** - Finished Units Yield Type Management merged:
  - Yield type authoring moved to Recipe Edit form (inline YieldTypeRow widgets)
  - Finished Units tab converted to read-only catalog with recipe filter
  - Double-click navigation opens parent recipe for editing
  - Cascade delete: yield types auto-delete when recipe is deleted
  - Per-recipe name uniqueness validation (case-insensitive)
  - Cursor code review completed, 5 fixes applied before merge
  - 1774 tests pass, all integration scenarios verified
  - F042-F044 now complete
- 2026-01-09: **F045 INSERTED** - Cost Architecture Refactor:
  - Inserted new F045 to address cost calculation foundation issues
  - Renumbered: Finished Goods (F045→F046), Shopping Lists (F046→F047), Assembly (F047→F048)
  - F045 spec in development by Claude Desktop
- 2026-01-09: **F045 COMPLETE** - Cost Architecture Refactor merged:
  - "Costs on Instances, Not Definitions" principle implemented
  - Removed stored `unit_cost`/`total_cost` from FinishedUnit, FinishedGood, Composition
  - Costs now calculated dynamically from ProductionRun/AssemblyRun history
  - Placeholder code left for F046 to implement dynamic calculation methods
- 2026-01-10: **F046 COMPLETE** - Finished Goods, Bundles & Assembly Tracking merged:
  - Added `calculate_current_cost()` methods to FinishedUnit and FinishedGood models
  - Fixed Composition model methods (`get_component_cost`, `get_total_cost`)
  - Fixed Package model methods (`calculate_cost`, `get_cost_breakdown`, `get_line_cost`)
  - Fixed assembly_service to capture actual costs instead of hardcoded zeros
  - Cursor code review completed, no blockers found
  - 1774 tests pass, all 4 work packages approved
  - F042-F046 now complete, F047-F048 remaining
- 2026-01-10: **F047 INSERTED** - Materials Management System:
  - Inserted new F047 for materials management
  - Renumbered: Shopping Lists (F047→F048), Assembly Workflows (F048→F049)
  - F047 spec in development by Claude Desktop
- 2026-01-11: **F047 COMPLETE** - Materials Management System merged:
  - Material/MaterialProduct/MaterialCategory/MaterialSubcategory models
  - Non-edible materials (ribbon, boxes, bags) properly separated from ingredients
  - Materials can be used in assemblies
- 2026-01-11: **F048 COMPLETE** - Materials UI Rebuild merged:
  - Materials UI rebuilt to match Ingredients 3-tab pattern
  - Categories, Subcategories, Materials tabs with consistent grids
  - Note: Feature scope changed from "Shopping Lists" to "Materials UI Rebuild"
- 2026-01-12: **F049 COMPLETE** - Import/Export Phase 1 merged:
  - Complete 16-entity backup capability
  - Context-rich exports for all catalog entities
  - Materials catalog import support
  - Note: Feature scope changed from "Assembly Workflows" to "Import/Export Phase 1"
- 2026-01-12: **F050 COMPLETE** - Supplier Slug Support merged:
  - Added supplier_slug field for stable FK references
  - Import/export uses slugs instead of IDs
- 2026-01-13: **F051 COMPLETE** - Import/Export UI Rationalization merged:
  - Unified import dialog with purpose-based selection (Catalog, Backup, Context-Rich)
  - Improved error handling and log file generation
  - All foundational features (F042-F051) now complete
  - Ready for User Testing Round 2
- 2026-01-15: **F052-F054 COMPLETE** - Hierarchy Admin, Context-Rich Export, CLI Parity:
  - F052 merged: Hierarchy Admin tab for ingredient/material taxonomy management
  - F053 merged: file prefix (view→aug), added Products/Material Products, multi-select checkboxes, "All" option
  - F054 merged: 16 new CLI commands for backup/restore, catalog, and aug operations achieving full UI parity
  - Renumbered: Original UI Navigation Cleanup (F053→F055)
  - Spec-Kitty symlink merge bug confirmed and filed as GitHub issue
  - Next: F055 (UI Navigation Cleanup), then User Testing Round 2
- 2026-01-16: **POST-F055 BUG FIX SESSION** - User testing identified 10 issues, all resolved:
  - `e320e3c` fix: Restore supplier FK resolution during product import (suppliers missing after backup restore)
  - `3ee8d51` fix: Add Close button to Hierarchy Admin windows (no way to exit)
  - `50a06db` fix: Double-click on recipe grid opens edit dialog (was showing unhelpful detail modal)
  - `d44ab01` feat: Add separate backup directory preference and reorder import flow (backup location separate from import/export, type-first workflow)
  - `17d2573` feat: Rename Adjustments to Inventory, default reason_code to CORRECTION
  - `1e127e1` fix: Full backup export now uses backup directory preference
  - `731137c` fix: Increase Export dialog height for Context-Rich options
  - `280d01a` feat: Add cascade delete warning for backup restore imports (warns when importing ingredients without products)
  - `a5a7abb` feat: Add cascade delete protection to CLI (rejects risky imports, --force to override)
  - Import/export system now has comprehensive FK cascade protection in both UI and CLI
  - `e11f78c` feat: Add RESTRICT constraint detection for import risk warnings (ingredients used by recipes)
  - `579e748` fix: Add materials_tab to refresh methods after import (materials grid empty after restore)
  - `9cee888` refactor: Restructure Recipe edit form for better UX:
    - Combined Yield Information and Yield Types into single section
    - YieldQty and YieldUnit now on same line (related fields)
    - Yield Types (FinishedUnits) moved directly below yield qty/unit
    - Prep Time moved below Sub-Recipes section
    - Removed Cost Summary section (costs only meaningful at ProductionRun instantiation)
    - Net ~100 line reduction
  - `6bc36ff` fix: Default Production Ready checkbox to checked (new recipes assumed ready)
  - `75532e1` fix: Remove extra frame backgrounds from Ingredients/Materials tabs (fg_color="transparent")
  - `0826502` fix: Include is_production_ready in recipe export/import (field was missing, defaults to True for backward compatibility)
