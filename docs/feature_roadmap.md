# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2025-12-12
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

---

## In Progress

**Feature 019: Unit Conversion Simplification** - Removing redundant `Ingredient.recipe_unit` and `UnitConversion` table. The 4-field density model (Feature 010) makes these vestigial.

---

## Planned Features

| # | Name | Priority | Dependencies | Status |
|---|------|----------|--------------|--------|
| 019 | Unit Conversion Simplification | HIGH | Constitution v1.2.0 | In Progress |
| 020 | Packaging & Distribution | LOW | User testing complete | Blocked |

---

## Implementation Order

**Current:** Feature 019 - Unit Conversion Simplification

1. ~~**TD-001** - Clean foundation before adding new entities~~ ✅ COMPLETE
2. ~~**Feature 011** - Packaging materials, extend Composition for packaging~~ ✅ COMPLETE
3. ~~**Feature 012** - Nested recipes (sub-recipes as recipe components)~~ ✅ COMPLETE
4. ~~**Feature 013** - BatchProductionService, AssemblyService, consumption ledgers~~ ✅ COMPLETE
5. ~~**Feature 014** - Production UI, Record Production/Assembly dialogs~~ ✅ COMPLETE
6. ~~**Feature 016** - Event-Centric Production Model~~ ✅ COMPLETE
7. ~~**BUGFIX** - Session Management Remediation~~ ✅ COMPLETE
8. ~~**Feature 017** - Reporting and Event Planning~~ ✅ COMPLETE
9. ~~**Feature 018** - Event Production Dashboard~~ ✅ COMPLETE
10. **Feature 019** - Unit Conversion Simplification ← CURRENT
11. **Feature 020** - Packaging & Distribution

---

## Feature Descriptions

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

**Status:** In Progress

**Problem:** Redundant unit conversion mechanisms:
- `Ingredient.recipe_unit` - vestigial field; recipes declare their own units in RecipeIngredient
- `UnitConversion` table - values derivable from 4-field density on Ingredient

**Solution:** Remove both. The 4-field density model (Feature 010) is the canonical source.

**Scope:**
- Delete `Ingredient.recipe_unit` column
- Delete `UnitConversion` model and table
- Update import/export spec v3.2 → v3.3
- Update catalog import proposal
- Convert test data files

**Specification:** `docs/feature_019_unit_simplification.md`

---

## Key Decisions

### 2025-12-14
- **Constitution v1.2.0:** Updated Principle VI from "Migration Safety" to "Schema Change Strategy (Desktop Phase)". For single-user desktop app, export/reset/import cycle replaces migration scripts.
- **Feature 019 Defined:** Unit Conversion Simplification - remove redundant `recipe_unit` and `UnitConversion` table.
- **Feature Renumbering:** Packaging & Distribution moved to Feature 020.
- **Catalog Import Impact:** Feature proposal at `docs/feature_proposal_catalog_import.md` requires update to remove UnitConversion references.

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
- 2025-12-14: Constitution v1.2.0 (schema change strategy). Feature 019 (Unit Conversion Simplification) defined. Packaging & Distribution moved to Feature 020.
