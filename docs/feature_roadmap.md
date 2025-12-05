# Feature Roadmap

**Created:** 2025-12-03
**Last Updated:** 2025-12-04
**Workflow:** Spec-Kitty driven development

---

## Completed Features

| # | Name | Status | Notes |
|---|------|--------|-------|
| 001 | System Health Check | ABANDONED | Scope mismatch - multi-tenant features inappropriate for local desktop app |
| 002 | Phase 4 Services (Part 1) | MERGED | IngredientService, VariantService |
| 003 | Phase 4 Services (Part 2) | MERGED | PantryService, PurchaseService |
| 004 | Phase 4 UI | MERGED | ingredients_tab.py, pantry_tab.py |
| 005 | Recipe FIFO Cost Integration | MERGED | RecipeService calculates costs using FIFO from PantryService |
| 006 | Event Planning Restoration | MERGED | Re-enabled Bundle -> Package -> Event chain with Ingredient/Variant architecture |
| 007 | Shopping List Variant Integration | MERGED | EventService shopping lists with variant-aware brand recommendations |
| 008 | Production Tracking | MERGED | Phase 5: Record finished goods production, mark packages assembled/delivered |
| 009 | UI Import/Export | MERGED | File menu import/export dialogs. 7 bug fixes applied 2025-12-04. |

---

## In Progress

| # | Name | Priority | Description |
|---|------|----------|-------------|
| 010 | User-Friendly Density Input | HIGH | Restore 4-field density (volume_value, volume_unit, weight_value, weight_unit) for intuitive entry like 1 cup = 4.5 oz |

---

## Planned Features

| # | Name | Priority | Description |
|---|------|----------|-------------|
| 011 | Reporting Enhancements | LOW | Phase 6: Dashboard improvements, CSV exports, recipient history reports. |
| 012 | Packaging & Distribution | LOW | Inno Setup installer creation, code signing evaluation. |

---

## Implementation Order

**Current:** 010 (User-Friendly Density Input)
**Next:** User Testing -> 011/012 based on feedback

1. **010 - User-Friendly Density Input** (HIGH) - IN PROGRESS
   - Restore usability regression from refactoring
   - Enables intuitive density entry without metric calculations
   - Spec: docs/feature-010-user-friendly-ingredient.md

2. **User Testing Checkpoint**
   - Run local build with wife
   - Validate end-to-end workflow: Ingredients -> Recipes -> Bundles -> Packages -> Events -> Production
   - Gather feedback on gaps and usability issues

3. **011, 012** - Prioritize based on user testing feedback

---

## Notes

- **Import/Export:** Feature 009 now fully functional. Tested with 79-record sample_data.json successfully.
- **User Testing Priority:** Getting real-world usage feedback is next priority after 010.
- **Spec-Kitty Workflow:** All features follow: specify -> plan -> tasks -> implement -> review -> accept -> merge
- **No Alembic:** Schema changes handled via export/reimport. App will be rewritten as web app for multi-user.

---

## Document History

- 2025-12-03: Initial creation based on project state assessment and roadmap discussion
- 2025-12-04: Features 006, 007, 008, 009 marked complete; TD-001 expanded
- 2025-12-04: Feature 010 (Density Input) started; renumbered 010->011, 011->012

---

## Technical Debt

### TD-001: Schema Cleanup - Naming, Legacy Columns, and Attribute Consistency
**Priority:** Medium  
**Status:** Planned

**Issues:**
1. RecipeIngredient has dual FKs: ingredient_id (legacy, unused) and ingredient_new_id (current)
2. Table naming is confusing: products table holds Ingredient model, variants table holds Variant model
3. Inconsistent name attributes across models

**Part A: Table and Model Renaming (user-specified):**
- ingredients table = generic representation (All-Purpose Flour)
- products table = purchasable items with brand/package (King Arthur 25lb bag)

Tasks:
1. Drop legacy ingredients table (if empty/unused)
2. Rename products table -> ingredients
3. Rename variants table -> products
4. Drop ingredient_id column from recipe_ingredients
5. Rename ingredient_new_id -> ingredient_id in recipe_ingredients
6. Update model class names: Variant -> Product
7. Update all code references, imports, and relationships
8. Update import/export service field mappings

**Part B: Attribute Naming Consistency:**

Pattern: Models with slug use display_name; models without slug use name

| Model | Has slug | Current | Target |
|-------|----------|---------|--------|
| Ingredient | Yes | name | display_name |
| FinishedGood | Yes | display_name | display_name (ok) |
| FinishedUnit | Yes | display_name | display_name (ok) |
| Recipe | No | name | name (ok) |
| Package | No | name | name (ok) |
| Recipient | No | name | name (ok) |
| Event | No | name | name (ok) |

Tasks:
1. Rename Ingredient.name -> Ingredient.display_name
2. Update all code references (services, UI, import/export)
3. Update sample_data.json to use display_name for ingredients

**Migration Strategy:**
- Export data using current import/export
- Apply schema changes to models
- Update sample_data.json field names if needed
- Delete database
- Restart app (recreates tables)
- Reimport data

---

## Feature 009 Bug Fixes (2025-12-04)

Seven bugs identified and fixed during user testing:

| Bug | Issue | Fix |
|-----|-------|-----|
| 1 | RecipeIngredient used wrong FK | ingredient_id -> ingredient_new_id |
| 2 | PackageFinishedGood field mismatch | Added package_slug support |
| 3 | Composition FinishedUnit lookup failed | Added recipe_slug fallback chain |
| 4 | Event missing year | Extract year from event_date |
| 5 | EventRecipientPackage field mismatch | Added event_slug, package_slug support |
| 6 | ProductionRecord field mismatch | Added event_slug, recipe_slug support |
| 7 | Detached session error on events load | Added lazy=joined to relationships |

**Result:** 79/79 records import successfully from test_data/sample_data.json
