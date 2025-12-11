# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2025-12-11
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

---

## In Progress

| # | Name | Priority | Status |
|---|------|----------|--------|
| 016 | Event-Centric Production Model | **CRITICAL** | ACCEPTANCE PENDING |

**Note:** Feature 016 implementation complete. Awaiting `/spec-kitty.accept` and `/spec-kitty.merge`.

---

## Planned Features

| # | Name | Priority | Dependencies | Status |
|---|------|----------|--------------|--------|
| 017 | Reporting & Event Planning | MEDIUM | 016 | **BLOCKED** |
| 018 | Event Production Dashboard | MEDIUM | 016 | **BLOCKED** |
| 019 | Packaging & Distribution | LOW | - | - |

---

## Implementation Order

**Current:** Feature 016 (Event-Centric Production Model) - ACCEPTANCE PENDING

1. ~~**TD-001** - Clean foundation before adding new entities~~ ✅ COMPLETE
2. ~~**Feature 011** - Packaging materials, extend Composition for packaging~~ ✅ COMPLETE
3. ~~**Feature 012** - Nested recipes (sub-recipes as recipe components)~~ ✅ COMPLETE
4. ~~**Feature 013** - BatchProductionService, AssemblyService, consumption ledgers~~ ✅ COMPLETE
5. ~~**Feature 014** - Production UI, Record Production/Assembly dialogs~~ ✅ COMPLETE
6. **Feature 016** - Event-Centric Production Model ← **ACCEPTANCE PENDING**
7. **BUGFIX** - Session Management Remediation (critical foundation fix post-016)
8. **Feature 017/018** - Reporting and Event Dashboard (blocked on 016)
9. **Feature 019** - Packaging & Distribution

---

## Feature Descriptions

### Feature 016: Event-Centric Production Model (CRITICAL)

**Status:** Implementation complete, acceptance pending

**Problem:** The current architecture conflates three distinct concerns:
1. **Definition** - What IS a Cookie Gift Box? (FinishedGood + Composition) ✅ Works
2. **Inventory** - How many EXIST globally? (inventory_count) ✅ Works
3. **Commitment** - How many are FOR Christmas 2025? ❌ **MISSING**

ProductionRun and AssemblyRun have no `event_id` FK. When a user records "made 2 batches of cookies," the system cannot link that production to a specific event. This breaks:
- Event progress tracking ("Am I on track for Christmas?")
- Planned vs actual reporting
- Multi-event planning (Christmas + Easter prep overlap)

**Scope (Schema v0.6):**
- Add `event_id` (nullable FK) to ProductionRun and AssemblyRun
- New `EventProductionTarget` table (event_id, recipe_id, target_batches)
- New `EventAssemblyTarget` table (event_id, finished_good_id, target_quantity)
- Add `fulfillment_status` ENUM to EventRecipientPackage (pending/ready/delivered)
- Service methods for target management and progress calculation
- UI: Event selector in Record Production/Assembly dialogs, Targets tab in Event detail

**Design Document:** `docs/design/schema_v0.6_design.md`
**Spec-Kitty Artifacts:** `kitty-specs/016-event-centric-production/`

---

### BUGFIX: Session Management Remediation (Post-016)

**Status:** Specification complete, implementation pending

**Problem:** Code review during Feature 016 revealed critical architectural flaw: nested `session_scope()` calls cause SQLAlchemy objects to become detached, resulting in silent data loss.

**Impact:** 5 test failures were caused by this issue in `batch_production_service.py`. The same pattern exists unfixed in `assembly_service.py`.

**Scope:**
- Fix `assembly_service.py` to pass session through call chain (same fix as batch_production)
- Fix `check_can_produce()` and `check_can_assemble()` to use session parameter
- Add rollback tests for multi-step operations

**Specification:** `docs/design/session_management_remediation_spec.md`

**Note:** This is a bug fix, not a feature. Will be implemented via direct bugfix branch after Feature 016 merge.

---

### Feature 017: Reporting & Event Planning (BLOCKED on 016)

**Rationale:** Cannot implement accurate event reporting without event-production linkage from Feature 016.

**Planned Scope:**
- Shopping list CSV export
- Event summary reports (planned vs actual)
- Cost analysis views
- Recipient history reports
- Dashboard enhancements

---

### Feature 018: Event Production Dashboard (BLOCKED on 016)

**Rationale:** Requires event progress tracking from Feature 016.

**Planned Scope:**
- "Where do I stand for Christmas 2025?" view
- Progress bars per recipe/finished good
- Fulfillment status tracking
- Multi-event overview

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

### 2025-12-11
- **Session Management Bug:** Code review revealed critical nested session_scope issue. Created remediation spec. Will be fixed via bugfix branch after Feature 016 merge.
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
- 2025-12-11: Feature 016 implementation complete, acceptance pending. Session management bug discovered during code review; remediation spec created. Feature 015 confirmed skipped. Features renumbered: 017 (Reporting), 018 (Dashboard), 019 (Packaging).
