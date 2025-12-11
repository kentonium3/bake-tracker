# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2025-12-10
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
| 013 | Production & Inventory Tracking | MERGED | BatchProductionService, AssemblyService, FIFO consumption ledgers. 51 tests. Bug fixes 2025-12-10: transaction atomicity, timestamp consistency, packaging validation. |
| 014 | Production & Assembly Recording UI | MERGED | Record Production/Assembly dialogs, Summary tab integration. |

---

## In Progress

| # | Name | Status | Notes |
|---|------|--------|-------|
| 016 | Event-Centric Production Model | IN PROGRESS | Linking production to events, progress tracking, fulfillment workflow. |

---

## Planned Features

| # | Name | Priority | Dependencies |
|---|------|----------|--------------|
| 015 | Reporting Enhancements | LOW | - |
| 017 | Future TBD | LOW | - |

---

## Implementation Order

**Current:** Feature 016 in progress

1. ~~**TD-001** - Clean foundation before adding new entities~~ ✅ COMPLETE
2. ~~**Feature 011** - Packaging materials, extend Composition for packaging~~ ✅ COMPLETE
3. ~~**Feature 012** - Nested recipes (sub-recipes as recipe components)~~ ✅ COMPLETE
4. ~~**Feature 013** - BatchProductionService, AssemblyService, consumption ledgers~~ ✅ COMPLETE
5. ~~**Feature 014** - Production UI, completes Feature 004's missing assembly UI~~ ✅ COMPLETE
6. **Feature 016** - Event-centric production model, progress tracking ← IN PROGRESS
7. **Feature 015** - Reporting enhancements (based on user feedback)

---

## Feature Descriptions

### Feature 012: Nested Recipes

**Rationale:** User testing revealed recipes can be hierarchical. A frosted layer cake recipe calls for sub-recipes (chocolate cake layers, vanilla cake layers, frosting, filling). A soup may call for a stock recipe. This must be addressed before production tracking to avoid rework.

**Scope:**
- New `RecipeComponent` junction model (recipe_id, component_recipe_id, quantity, unit, notes)
- Update Recipe model with `sub_recipes` relationship
- Recursive recipe cost calculation
- Recursive ingredient aggregation for shopping lists
- Recipe UI: ability to add sub-recipes as components
- Import/export support for nested recipes

**Technical Notes:**
- Same pattern as Composition (polymorphic components)
- Shopping list aggregation must traverse recipe hierarchy
- Cost calculation must sum sub-recipe costs

### Feature 016: Event-Centric Production Model

**Rationale:** User needs to plan production specifically for events (Christmas 2025, Easter bake sale) and track progress toward completion. This requires linking production and assembly runs to events and providing explicit targets.

**Scope:**
- Add `event_id` FK to ProductionRun and AssemblyRun (nullable for standalone production)
- New EventProductionTarget and EventAssemblyTarget tables for explicit per-event targets
- Progress calculation (produced/assembled vs target) with percentage display
- FulfillmentStatus enum on EventRecipientPackage with sequential workflow (pending→ready→delivered)
- UI: Event selector dropdown in Record Production/Assembly dialogs
- UI: Targets tab in Event Detail window with progress bars
- UI: Fulfillment status column in package assignments with dropdown
- Import/export support for new entities and fields

**Technical Notes:**
- Service layer methods accept optional event_id
- Progress aggregates runs where event_id matches target's event
- Sequential workflow enforced at service layer

---

## Key Decisions

### 2025-12-06
- **Packaging:** Use Ingredient with `is_packaging` flag (not separate entity)
- **FIFO:** Inventory only; simple counts for FinishedUnit/FinishedGood
- **Holiday Season:** Full refactor - production 50% complete, no time pressure
- **Feature 004 Gap:** Assembly UI missing; will be addressed in Feature 014

### 2025-12-08
- **Nested Recipes:** Insert as Feature 012 before production tracking to avoid rework on shopping list aggregation and cost calculation

---

## Technical Debt

### TD-001: Schema Cleanup
**Status:** COMPLETE ✅
**Prompt:** docs/TD-001-schema-cleanup-prompt.md

Part A: Variant → Product, fix dual FK ✅
Part B: Ingredient.name → Ingredient.display_name ✅

**Changes (2025-12-07):**
- Renamed Variant model → Product
- Renamed PantryItem model → InventoryItem
- Renamed PantryService → InventoryItemService
- Renamed InventoryService → IngredientCrudService
- Renamed VariantPackaging → ProductPackaging
- Updated all UI to use "Product" terminology
- Removed obsolete migration wizard and test utilities
- All 421 tests pass

---

## Document History

- 2025-12-03: Initial creation
- 2025-12-04: Features 006-009 complete; TD-001 documented
- 2025-12-05: Feature 010 complete; 8 bugs fixed
- 2025-12-06: Workflow gap analysis; TD-001 started; Features 011-015 defined
- 2025-12-07: TD-001 complete; full terminology cleanup (Variant→Product, Pantry→Inventory)
- 2025-12-08: Feature 011 in progress; Feature 012 (Nested Recipes) inserted; features renumbered 012→013, 013→014, 014→015, 015→016
- 2025-12-09: Features 011, 012, 013 complete. Full service layer for production tracking now in place (BatchProductionService, AssemblyService with 51 tests, 91% coverage). Ready for Feature 014 (Production UI).
- 2025-12-10: Feature 013 bug fixes from independent code review: (1) Transaction atomicity - FIFO consumption now uses caller's session for atomic rollback, (2) Timestamp consistency - standardized to naive UTC, (3) Packaging validation - `is_packaging` flag check added, (4) Rollback tests added to both services. Known limitation documented: nested FinishedGood consumption lacks ledger entries (see docs/known_limitations.md).
- 2025-12-10: Feature 014 (Production & Assembly Recording UI) complete and merged.
- 2025-12-11: Feature 016 (Event-Centric Production Model) in progress - WP01-WP09 complete, WP10 (documentation) in progress.
