# Current Development Priorities

**Last Updated:** 2025-11-08
**Active Branch:** `feature/product-pantry-refactor`
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

**Current Focus:**
- 🔄 Phase 4: Ingredient/Variant Refactor (Items 7+)
- 🔄 Documentation consolidation and organization

**Next Up:**
- Phase 4 Service Layer implementation
- Phase 4 UI updates (My Ingredients, My Pantry tabs)
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

### ⏳ Pending (Items 7+)

**Service Layer** (Not Started):
```
Priority Order:
1. IngredientService - Catalog CRUD operations
2. VariantService - Brand/package management
3. PantryService - Inventory tracking with FIFO
4. PurchaseService - Price history and trending
5. Update RecipeService - FIFO cost calculations
6. Update EventService - Variant-aware shopping lists
```

**Business Logic** (Not Started):
- FIFO cost calculation integration
- Multi-brand support (preferred variant logic)
- Price trend analysis
- Shopping list variant recommendations

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

**Testing & Validation** (Not Started):
- Run migration on test data (dry-run first)
- Validate cost calculations match v0.3.0
- Shopping list generation tests
- UI integration tests

---

## Immediate Next Steps (Priority Order)

### 1. Service Layer Implementation

**Start with IngredientService:**
```python
# src/services/ingredient_service.py
class IngredientService:
    - create_ingredient(data) -> Ingredient
    - get_ingredient(slug) -> Ingredient
    - search_ingredients(query, category) -> List[Ingredient]
    - update_ingredient(slug, data) -> Ingredient
    - delete_ingredient(slug) -> bool (check dependencies)
```

**Then VariantService:**
```python
# src/services/variant_service.py
class VariantService:
    - create_variant(ingredient_slug, data) -> Variant
    - get_variants_for_ingredient(ingredient_slug) -> List[Variant]
    - set_preferred_variant(variant_id) -> Variant
    - update_variant(variant_id, data) -> Variant
    - delete_variant(variant_id) -> bool
```

**Then PantryService:**
```python
# src/services/pantry_service.py
class PantryService:
    - add_to_pantry(variant_id, quantity, purchase_date, location) -> PantryItem
    - get_pantry_items(ingredient_slug, location) -> List[PantryItem]
    - get_total_quantity(ingredient_slug) -> float
    - consume_fifo(ingredient_slug, quantity) -> (consumed, breakdown)
    - get_expiring_soon(days) -> List[PantryItem]
```

### 2. Run Migration (After Services)

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

### 3. Build UI Components

**Order of Implementation:**
1. "My Ingredients" tab (manage catalog)
2. "My Pantry" tab (track inventory)
3. Update recipe ingredient selector
4. Update shopping list display

### 4. Testing & Validation

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
- ✅ Ingredient/Variant separation working
- ✅ Multiple brands/sources per ingredient
- ✅ Preferred variant logic
- ✅ FIFO costing accurate
- ✅ Pantry lot tracking
- ✅ Migration from v0.3.0 preserves all data
- ✅ Cost calculations match v0.3.0

**Testing Checklist:**
- [ ] Create ingredient with 2+ variants
- [ ] Add pantry items with different purchase dates
- [ ] Create recipe using ingredient (not variant)
- [ ] Calculate cost - verify FIFO order
- [ ] Generate shopping list - verify variant recommendations
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
