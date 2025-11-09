# Current Development Priorities

**Last Updated:** 2025-11-09
**Active Branch:** `main`
**Target Version:** 0.4.0

---

## High-Level Status

**Completed:**
- ✅ Phase 1: Foundation (MVP) - Ingredients, Recipes, Unit Conversions
- ✅ Phase 2: Finished Goods & Bundles
- ✅ Phase 3b: Event Planning (Events, Recipients, Packages)
- ✅ Import/Export Specification v2.0 (Ingredient/Variant architecture)
- ✅ Test Data Conversion Tool (v1.0 → v2.0 format)
- ✅ Phase 4 Items 1-6: Models renamed, spec fields added, migration script ready
- ✅ Phase 4 Service Layer: All 4 services implemented and tested (Feature 002)

**Current Focus:**
- 🔄 Phase 4: UI updates (My Ingredients, My Pantry tabs)
- 🔄 Phase 4: Migration execution and testing

**Next Up:**
- Phase 4: Service layer integration with existing UI
- Phase 5: Production Tracking
- Phase 6: Reporting & Polish

---

## Phase 4: Ingredient/Variant Refactor - Detailed Status

### ✅ Completed (Items 1-6)

**Models & Schema:**
- Renamed Product → Ingredient
- Renamed ProductVariant → Variant
- Renamed PurchaseHistory → Purchase
- Added industry standard fields (FoodOn, FDC, GTIN, allergens - all nullable)
- Created supporting models (IngredientAlias, IngredientCrosswalk, VariantPackaging)
- Added UUID support to BaseModel
- Dual FK support in RecipeIngredient (legacy + new)

**Migration Support:**
- Full migration script created (`src/utils/migrate_to_ingredient_variant.py`)
- Dry-run support for testing
- UUID population logic
- RecipeIngredient FK update logic

**Import/Export:**
- Import/export spec updated to v2.0
- Test data conversion script created (`convert_v1_to_v2.py`)
- Working v2.0 test data (83 ingredients, 20 recipes, 15 finished goods)

### ✅ Completed (Items 7-10) - Feature 002 Service Layer

**Service Layer** (Completed 2025-11-09):
```
✅ 1. IngredientService - Catalog CRUD operations with slug-based lookup
✅ 2. VariantService - Brand/package management with preferred variant support
✅ 3. PantryService - Inventory tracking with FIFO consumption algorithm
✅ 4. PurchaseService - Price history and trending with linear regression analysis
```

**Infrastructure** (Completed 2025-11-09):
- ✅ Service exceptions hierarchy (ServiceError, NotFound, Validation, DatabaseError)
- ✅ session_scope() context manager for transaction management
- ✅ Slug generation utility with Unicode normalization
- ✅ Input validation utilities for ingredient and variant data

**Testing** (Completed 2025-11-09):
- ✅ 16/16 integration tests passing (100%)
- ✅ test_inventory_flow.py - Complete ingredient→variant→pantry workflow (6 tests)
- ✅ test_fifo_scenarios.py - FIFO consumption edge cases (6 tests)
- ✅ test_purchase_flow.py - Purchase tracking and price analysis (4 tests)

**Key Features Delivered:**
- ✅ FIFO inventory consumption with unit conversion
- ✅ Density-based unit conversions (g/ml to g/cup)
- ✅ Price trend analysis with linear regression
- ✅ Preferred variant logic with atomic toggle
- ✅ Eager loading preventing DetachedInstanceError
- ✅ Decimal precision for all monetary values

### ⏳ Pending (Items 11+)

**Business Logic Integration** (Not Started):
- Update RecipeService - FIFO cost calculations
- Update EventService - Variant-aware shopping lists
- Multi-brand recommendations in shopping lists

**UI Updates** (Not Started):
```
New Tabs:
- "My Ingredients" tab (catalog management)
- "My Pantry" tab (inventory by variant, FIFO tracking)

Updated Components:
- Recipe ingredient selector (ingredients, not variants)
- Shopping list with variant recommendations
- Inventory dashboard (aggregate by ingredient)
```

**Migration & Validation** (Not Started):
- Run migration on test data (dry-run first)
- Validate cost calculations match v0.3.0
- Shopping list generation tests with new services
- UI integration tests

---

## Immediate Next Steps (Priority Order)

### 1. UI Implementation - "My Ingredients" Tab

**Create New Tab:**
```python
# src/ui/ingredients_tab.py (NEW - replaces old inventory_tab.py)
Features:
- Ingredient catalog management (generic ingredients, not products)
- Search and filter by category
- Add/Edit/Delete ingredients
- View variants for each ingredient
- Industry standard fields (optional: FoodOn, FDC, allergens)
- Unit conversion management
```

**Integration:**
- Use `ingredient_service.py` for all operations
- Use `variant_service.py` for variant management
- Replace old inventory_tab.py references in main_window.py

### 2. UI Implementation - "My Pantry" Tab

**Create New Tab:**
```python
# src/ui/pantry_tab.py (NEW)
Features:
- Pantry inventory by variant (lot tracking)
- FIFO consumption interface
- Add pantry items with purchase date, location, expiration
- View total quantity by ingredient (aggregated across variants)
- Expiring soon alerts
- Consumption history
```

**Integration:**
- Use `pantry_service.py` for all operations
- Use `purchase_service.py` for price history
- Add to main_window.py tabbed interface

### 3. Run Migration (After UI Ready)

**Test Migration Process:**
```bash
# 1. Dry run first
cd bake-tracker
PYTHONPATH=. venv/Scripts/python.exe -c "
from src.utils.migrate_to_ingredient_variant import run_full_migration
from src.services.database import get_session
run_full_migration(get_session(), dry_run=True)
"

# 2. Review output, verify no errors

# 3. Run actual migration
PYTHONPATH=. venv/Scripts/python.exe -c "
from src.utils.migrate_to_ingredient_variant import run_full_migration
from src.services.database import get_session
run_full_migration(get_session(), dry_run=False)
"
```

### 4. Update Recipe & Event Services

**Integrate with New Services:**
```python
# Update src/services/recipe_service.py
- Use ingredient_service instead of direct Ingredient queries
- Implement FIFO cost calculation using pantry_service.consume_fifo()
- Update recipe cost calculation to use variant pricing

# Update src/services/event_service.py
- Use ingredient_service for shopping lists
- Use variant_service for brand recommendations
- Integrate preferred variant logic into shopping lists
```

### 5. Testing & Validation

**Test Coverage:**
- Service layer unit tests
- FIFO consumption logic tests
- Cost calculation validation (old vs new)
- UI integration tests
- End-to-end workflow tests

---

## Key Design Documents

**For Implementation:**
- `docs/schema_v0.4_design.md` - Complete Phase 4 schema design
- `docs/ingredient_industry_standards.md` - External standard field definitions
- `docs/import_export_specification.md` - Data format (v2.0)

**For Context:**
- `docs/development_status.md` - Complete project history
- `docs/architecture.md` - System architecture
- `docs/schema_v0.3.md` - Current production schema

**Archived (Reference Only):**
- `docs/archive/pause_point.md` - Historical pause point
- `docs/archive/refactor_status.md` - Historical refactor status

---

## Success Criteria for Phase 4

**Must Have:**
- ✅ Ingredient/Variant separation working (models & services complete)
- ✅ Multiple brands/sources per ingredient (VariantService complete)
- ✅ Preferred variant logic (atomic toggle implemented)
- ✅ FIFO costing accurate (consume_fifo() tested with 6 scenarios)
- ✅ Pantry lot tracking (PantryItem with purchase_date, location)
- ⏳ Migration from v0.3.0 preserves all data (script ready, execution pending)
- ⏳ Cost calculations match v0.3.0 (pending migration execution)

**Testing Checklist:**
- ✅ Create ingredient with 2+ variants (VariantService tests)
- ✅ Add pantry items with different purchase dates (PantryService tests)
- ✅ Calculate cost - verify FIFO order (test_fifo_scenarios.py - 6 tests passing)
- [ ] Create recipe using ingredient (not variant) - UI pending
- [ ] Generate shopping list - verify variant recommendations - UI pending
- [ ] Migrate v0.3.0 data - verify preservation
- [ ] Compare costs (old vs new) - verify match

---

## Known Blockers

**None Currently** - Ready to proceed with service layer implementation

**Future Considerations:**
- UPC validation algorithm (defer to later phase)
- FoodOn ID population (requires curated subset or API)
- Mobile app integration (deferred)

---

## Quick Reference Commands

**Run Tests:**
```bash
cd bake-tracker
venv/Scripts/pytest.exe src/tests/ -v
```

**Import Test Data:**
```bash
PYTHONPATH=. venv/Scripts/python.exe -m src.utils.load_test_data examples/test_data_v2.json
```

**Export Current Data:**
```bash
PYTHONPATH=. venv/Scripts/python.exe -m src.utils.export_test_data my_backup.json
```

---

**For Spec-Kitty Task Generation:**
- Focus on Service Layer (Items 1-4 above)
- Reference `schema_v0.4_design.md` for detailed specs
- Use existing service patterns in `src/services/` as templates
- Follow TDD: write tests first, then implementation
