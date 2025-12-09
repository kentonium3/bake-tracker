# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2025-12-08
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

---

## In Progress

| # | Name | Priority | Description |
|---|------|----------|-------------|
| 011 | Packaging & BOM Foundation | HIGH | Packaging materials, extend Composition for packaging consumption |

---

## Planned Features

| # | Name | Priority | Dependencies |
|---|------|----------|--------------|
| 012 | Nested Recipes | HIGH | 011 |
| 013 | Production & Inventory Tracking | HIGH | 012 |
| 014 | Production UI | HIGH | 013 |
| 015 | Reporting Enhancements | LOW | - |
| 016 | Packaging & Distribution | LOW | - |

---

## Implementation Order

**Current:** Feature 011 (Packaging & BOM Foundation) - in progress via spec-kitty

1. ~~**TD-001** - Clean foundation before adding new entities~~ ✅ COMPLETE
2. **Feature 011** - Packaging materials, extend Composition for packaging ← IN PROGRESS
3. **Feature 012** - Nested recipes (sub-recipes as recipe components)
4. **Feature 013** - BATCH entity, production services, consumption recording
5. **Feature 014** - Production UI, completes Feature 004's missing assembly UI
6. **Feature 015/016** - Based on user feedback

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
