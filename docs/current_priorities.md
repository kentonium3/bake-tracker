# Current Development Priorities

**Last Updated:** 2025-12-01
**Active Branch:** `main`
**Target Version:** 0.5.0

---

## High-Level Status

**Completed:**
- ✅ Phase 1: Foundation (MVP) - Ingredients, Recipes, Unit Conversions
- ✅ Phase 2: Finished Goods & Bundles (original architecture)
- ✅ Phase 3b: Event Planning (Events, Recipients, Packages) - *now disabled*
- ✅ Import/Export Specification v2.0 (Ingredient/Variant architecture)
- ✅ Test Data Conversion Tool (v1.0 → v2.0 format)
- ✅ Phase 4: Complete Ingredient/Variant Refactor (Features 002 + 003)
- ✅ Feature 004: FinishedUnit Model Refactoring (two-tier hierarchy)

**Current Focus:**
- 🔄 Recipe FIFO cost integration
- 🔄 Event/Package architecture restoration

**Next Up:**
- Phase 5: Production Tracking
- Phase 6: Reporting & Polish

---

## Phase 4: Ingredient/Variant Refactor - ✅ COMPLETE

### ✅ Completed (All Items)

**Models & Schema:**
- Renamed Product → Ingredient
- Renamed ProductVariant → Variant
- Renamed PurchaseHistory → Purchase
- Added industry standard fields (FoodOn, FDC, GTIN, allergens - all nullable)
- Created supporting models (IngredientAlias, IngredientCrosswalk, VariantPackaging)
- Added UUID support to BaseModel
- Dual FK support in RecipeIngredient (legacy + new)

**Service Layer** (Feature 002 - Complete):
```
✅ IngredientService - 469 lines, catalog CRUD with slug-based lookup
✅ VariantService - 469 lines, brand/package management with preferred variant
✅ PantryService - 502 lines, FIFO consumption algorithm
✅ PurchaseService - 541 lines, price history with linear regression
```

**UI Layer** (Feature 003 - Complete):
```
✅ ingredients_tab.py - 1387 lines, ingredient catalog management
✅ pantry_tab.py - 1442 lines, inventory display with FIFO interface
✅ migration_wizard.py - Migration UI with dry-run preview
```

**Infrastructure:**
- ✅ Service exceptions hierarchy (ServiceError, NotFound, Validation, DatabaseError)
- ✅ session_scope() context manager for transaction management
- ✅ Slug generation utility with Unicode normalization
- ✅ Input validation utilities for ingredient and variant data

**Testing:**
- ✅ 16/16 integration tests passing (100%)
- ✅ test_inventory_flow.py - Complete ingredient→variant→pantry workflow
- ✅ test_fifo_scenarios.py - FIFO consumption edge cases
- ✅ test_purchase_flow.py - Purchase tracking and price analysis

---

## Feature 004: FinishedUnit Model Refactoring - ✅ COMPLETE

**Merged to main:** Commit `d8017e4` (2025-11-20)

**Models Created:**
- ✅ FinishedUnit - Individual consumable items (renamed from original FinishedGood)
- ✅ FinishedGood - Assembled packages with component tracking
- ✅ Composition - Junction model for hierarchical assemblies
- ✅ AssemblyType - Assembly categorization enum

**Services Created:**
- ✅ finished_unit_service.py - 36KB, unit CRUD and inventory
- ✅ finished_good_service.py - 58KB, assembly management
- ✅ composition_service.py - 54KB, hierarchy traversal
- ✅ ui_compatibility_service.py - 19KB, transition support

**UI Updates:**
- ✅ finished_units_tab.py - 27KB, unit management
- ✅ finished_goods_tab.py - 15KB, updated for new model
- ✅ finished_unit_form.py - 18KB
- ✅ finished_good_form.py - 18KB

---

## ⚠️ Event/Package Models (Disabled)

During Feature 004 refactoring, the following models were disabled due to cascading dependencies:

| Model | Status | Reason |
|-------|--------|--------|
| Bundle | **Removed** | Replaced by Composition model |
| Package, PackageBundle | **Disabled** | Depended on Bundle |
| Event, EventRecipientPackage | **Disabled** | Depended on Package |

**Impact:**
- Events tab (`events_tab.py`) - May be non-functional
- Packages tab (`packages_tab.py`) - May be non-functional
- Bundles tab (`bundles_tab.py`) - Deprecated

**Resolution:** Requires new feature to restore or redesign event planning architecture using the new FinishedGood/Composition model.

---

## Immediate Next Steps (Priority Order)

### 1. Recipe FIFO Cost Integration
Update RecipeService to use the new pantry architecture:
- Use ingredient_service instead of direct Ingredient queries
- Implement FIFO cost calculation using pantry_service.consume_fifo()
- Update recipe cost calculation to use variant pricing

### 2. Event/Package Architecture Restoration
Design and implement event planning using new models:
- Determine if Package concept maps to FinishedGood assemblies
- Update or replace EventService for new architecture
- Restore or redesign Events tab functionality

### 3. Phase 5: Production Tracking
- Batch production workflow
- Yield tracking and variance analysis
- Production scheduling

---

## Success Criteria for Phase 4 - ✅ ACHIEVED

**Must Have:**
- ✅ Ingredient/Variant separation working (models & services complete)
- ✅ Multiple brands/sources per ingredient (VariantService complete)
- ✅ Preferred variant logic (atomic toggle implemented)
- ✅ FIFO costing accurate (consume_fifo() tested with 6 scenarios)
- ✅ Pantry lot tracking (PantryItem with purchase_date, location)
- ✅ My Ingredients tab (1387 lines)
- ✅ My Pantry tab (1442 lines)
- ⏳ Migration from v0.3.0 preserves all data (script ready, execution pending)

**Testing Checklist:**
- ✅ Create ingredient with 2+ variants (VariantService tests)
- ✅ Add pantry items with different purchase dates (PantryService tests)
- ✅ Calculate cost - verify FIFO order (test_fifo_scenarios.py)
- ✅ My Ingredients tab CRUD operations
- ✅ My Pantry tab FIFO consumption interface
- [ ] Create recipe using ingredient (not variant) - integration pending
- [ ] Generate shopping list - variant recommendations - integration pending

---

## Known Issues

**Event/Package Disabled:**
- Models commented out in `src/models/__init__.py`
- Services may fail if Event/Package features are accessed
- Requires architectural decision on restoration approach

**Feature 004 Task Files:**
- Some task files remain in non-done lanes despite merge
- Acknowledged as complete; gaps treated as bugs if discovered

---

## Key Design Documents

**For Implementation:**
- `docs/schema_v0.4_design.md` - Phase 4 schema design
- `docs/ingredient_industry_standards.md` - External standard fields
- `docs/import_export_specification.md` - Data format (v2.0)

**For Context:**
- `docs/development_status.md` - Complete project history
- `docs/architecture.md` - System architecture
- `kitty-specs/004-finishedunit-model-refactoring/` - Feature 004 design docs

---

## Quick Reference Commands

**Run Tests:**
```bash
cd bake-tracker
source venv/bin/activate  # macOS/Linux
pytest src/tests/ -v
```

**Import Test Data:**
```bash
PYTHONPATH=. python -m src.utils.load_test_data examples/test_data_v2.json
```

**Run Application:**
```bash
python src/main.py
```

---

## Spec-Kitty Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| 001 | Abandoned | Scope inappropriate for local app |
| 002 | ✅ Complete | Service layer, clean state |
| 003 | ✅ Complete | Phase 4 UI, clean state |
| 004 | ✅ Complete | FinishedUnit refactoring, merged |

**Ready for new features via `/spec-kitty.specify`**
