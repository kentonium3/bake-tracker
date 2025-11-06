# Bake Tracker - Development Pause Point

**Date:** 2025-11-06
**Branch:** `feature/product-pantry-refactor`
**Status:** Planning complete, implementation paused
**Next Project:** Intentional (returning to bake-tracker later)

---

## What Was Accomplished

### 1. Architecture Decision: Ingredient/Variant Model ✅

**Problem Solved:** Current `Ingredient` model conflates multiple concerns:
- Generic ingredient definition (what is flour?)
- Brand/package specifics (King Arthur 25 lb bag)
- Current inventory (1.5 bags on hand)
- Purchase history (bought for $15.99 on Nov 1)

**Solution Designed:** Separation into distinct entities:

```
Ingredient (Generic concept)
└─ Variant (Specific version: brand+package OR source)
   ├─ PantryItem (Current stock on hand)
   └─ Purchase (Price history for FIFO costing)
```

### 2. Terminology Decision: Ingredient/Variant (Not Product) ✅

**Why "Ingredient" instead of "Product":**
- Handles commercial products (Domino Sugar 5 lb bag)
- Handles non-commercial sources (farm stand tomatoes, butcher's chicken)
- Domain-appropriate for baking application
- Clearer than "GenericProduct"

**Final Model Names:**
- `Ingredient` (not Product or GenericProduct)
- `Variant` (not ProductVariant)
- `PantryItem` (unchanged)
- `Purchase` (renamed from PurchaseHistory)

### 3. Spec Integration: Food Industry Standards ✅

**Incorporated from `ingredient_data_model_spec.md`:**
- FoodOn IDs (primary taxonomy)
- USDA FDC IDs (nutrition data)
- GS1 GTIN (UPC codes)
- LanguaL facets (descriptive terms)
- FoodEx2 codes (EU regulatory)
- Packaging hierarchy support

**Strategy:** "Future-proof schema, present-simple implementation"
- Add ALL spec fields to models NOW (as nullable)
- Populate ONLY required fields initially
- "Light up" additional fields in future iterations

### 4. Key Decisions Made ✅

1. **Pantry Item Merging:** Always create separate lots (Option A)
   - Each purchase = new PantryItem record
   - FIFO tracking with distinct purchase dates
   - UI groups by variant but shows individual items

2. **Location Field:** In database, hidden in UI
   - Default: "Main Pantry"
   - Future feature when location management added

3. **Unit Conversions:** Support chained conversions
   - Enable lb→oz→cup type paths
   - Product-specific density via `density_g_per_ml`

4. **FIFO Costing:** Primary cost calculation strategy
   - Matches physical consumption flow
   - Natural fit for lot tracking
   - Accurate when prices fluctuate

5. **UUID Primary Keys:** Adopt from spec
   - Distributed-system ready
   - API-friendly
   - Merge/sync friendly

---

## Models Designed (Not Yet Implemented)

### Core Models

#### Ingredient
```python
class Ingredient(BaseModel):
    # REQUIRED NOW:
    id = UUID
    name = String(200)  # "All-Purpose Flour"
    slug = String (unique)  # "all_purpose_flour"
    category = String(100)  # "Flour"

    # FUTURE READY (add but leave NULL):
    foodon_id = String (nullable)
    fdc_ids = ARRAY(String) (nullable)
    langual_terms = ARRAY(String) (nullable)
    density_g_per_ml = Numeric (nullable)
    moisture_pct = Numeric (nullable)
    allergens = ARRAY(String) (nullable)
```

#### Variant
```python
class Variant(BaseModel):
    # REQUIRED NOW:
    id = UUID
    ingredient_id = UUID (FK)
    source_description = String  # "Domino 5 lb bag" or "Farm stand"
    preferred = Boolean

    # COMMERCIAL FIELDS (nullable):
    brand_name = String (nullable)
    gtin = String (nullable)
    net_content_value = Numeric (nullable)
    net_content_uom = String (nullable)

    # FUTURE READY:
    brand_owner = String (nullable)
    gpc_brick_code = String (nullable)
    country_of_sale = String (nullable)
    off_id = String (nullable)
```

#### PantryItem
```python
class PantryItem(BaseModel):
    id = UUID
    variant_id = UUID (FK)
    qty_on_hand = Numeric
    qty_uom = String
    purchase_date = Date  # For FIFO
    location = String (default="Main Pantry")

    # FUTURE READY:
    lot_or_batch = String (nullable)
    best_by = Date (nullable)
    opened_at = DateTime (nullable)
```

#### Purchase
```python
class Purchase(BaseModel):
    id = UUID
    variant_id = UUID (FK)
    purchased_at = DateTime
    unit_price = Numeric
    purchase_qty = Numeric
    purchase_uom = String
    retailer = String (nullable)
    notes = Text (nullable)
```

### Supporting Models (Create but Don't Use Yet)

#### IngredientAlias
```python
class IngredientAlias(BaseModel):
    id = UUID
    ingredient_id = UUID (FK)
    alias = String  # "AP flour", "plain flour"
    locale = String (nullable)  # "en-US"
```

#### IngredientCrosswalk
```python
class IngredientCrosswalk(BaseModel):
    id = UUID
    ingredient_id = UUID (FK)
    system = String  # "FOODON", "FDC", "FOODEx2"
    code = String
    meta = JSONB (nullable)
```

#### VariantPackaging
```python
class VariantPackaging(BaseModel):
    id = UUID
    variant_id = UUID (FK)
    packaging_level = String  # "each", "case", "pallet"
    packaging_type_code = String (nullable)
    packaging_material_code = String (nullable)
    qty_of_next_lower_level = Integer (nullable)
    dimensions_l_w_h_uom = JSONB (nullable)
    gross_weight_value_uom = JSONB (nullable)
```

---

## Implementation Plan (When Resuming)

### Phase 1: Schema + Minimal Implementation (2-3 weeks)

**Week 1: Model Updates**
- Update existing models with new field names
- Add UUID columns alongside Integer IDs
- Add all spec fields (nullable)
- Create new supporting tables

**Week 2: Data Migration**
- UUID generation and FK updates
- Migrate Ingredient → Ingredient + Variant + PantryItem
- Populate only required fields
- Validate cost calculations match

**Week 3: Minimal UI**
- "My Ingredients" tab (name, category only)
- "My Pantry" tab (variant, qty, date)
- Recipe ingredient selector (ingredients, not variants)

### What Gets Implemented Immediately

**Ingredient/Variant Separation:**
- ✅ Multiple brands/sources per ingredient
- ✅ Preferred variant logic
- ✅ Brand-agnostic recipes

**FIFO Costing:**
- ✅ Purchase records with dates
- ✅ FIFO consumption by purchase_date
- ✅ Cost breakdown per lot

**Pantry Management:**
- ✅ Multiple pantry items per variant (lots)
- ✅ Quantity tracking by unit
- ✅ Purchase date tracking

### What's Available for Future

**Phase 2 (Light Up Fields):**
- GTIN entry (optional)
- Best-by dates
- Lot/batch tracking
- Location management
- IngredientAlias for autocomplete

**Phase 3 (Enrichment):**
- FoodOn IDs (manual entry)
- FDC nutrition links
- Allergen warnings
- IngredientCrosswalk entries

**Phase 4 (Ingestion):**
- FoodOn subset import
- FDC API integration
- Open Food Facts sync
- Automated crosswalk generation

---

## Files Ready for Implementation

### Documentation (Complete)
- ✅ `docs/REFACTOR_PRODUCT_PANTRY.md` - Full design spec (updated to Ingredient/Variant)
- ✅ `docs/REFACTOR_STATUS.md` - Detailed status with examples (updated)
- ✅ `docs/ingredient_data_model_spec.md` - Industry standard fields spec
- ✅ `docs/ingredient_taxonomy_research.md` - Taxonomy research

### Models (Created, Not Yet Updated with Spec)
- ⚠️ `src/models/product.py` → Needs rename to `ingredient.py`
- ⚠️ `src/models/product_variant.py` → Needs rename to `variant.py`
- ⚠️ `src/models/purchase_history.py` → Needs rename to `purchase.py`
- ✅ `src/models/pantry_item.py` - Mostly correct, needs UUID
- ⚠️ `src/models/unit_conversion.py` - Needs refactoring per spec

### Models to Create
- ❌ `src/models/ingredient_alias.py`
- ❌ `src/models/ingredient_crosswalk.py`
- ❌ `src/models/variant_packaging.py`
- ❌ `src/models/unit.py`

### Services (Not Yet Created)
- ❌ `src/services/ingredient_service.py`
- ❌ `src/services/variant_service.py`
- ❌ `src/services/pantry_service.py`
- ❌ `src/services/purchase_service.py`
- ⚠️ `src/services/recipe_service.py` - Needs FIFO costing update

### Migration Script (Not Yet Created)
- ❌ `src/utils/migrate_to_ingredient_variant.py`

---

## Current Repository State

**Main Branch (`main`):**
- v0.3.0 stable and ready for Marianne's testing
- `BakeTracker_v0.3.0_Windows.zip` packaged
- Full import/export for all 7 entity types
- Database: `bake_tracker.db` with consistent naming

**Feature Branch (`feature/product-pantry-refactor`):**
- Initial models created (need renaming to Ingredient/Variant)
- RecipeIngredient updated for dual FK support
- FIFO logic implemented in pantry_item module
- Documentation complete with Ingredient/Variant terminology

**Not Yet on Feature Branch:**
- Spec-compliant field additions (foodon_id, gtin, etc.)
- UUID migration
- Supporting tables (IngredientAlias, IngredientCrosswalk, VariantPackaging)
- Unit system refactoring

---

## Key Files to Read When Resuming

**Start here:**
1. `docs/PAUSE_POINT.md` (this file) - Quick context
2. `docs/REFACTOR_STATUS.md` - Detailed status with code examples
3. `docs/REFACTOR_PRODUCT_PANTRY.md` - Full design document

**Reference specs:**
1. `docs/ingredient_data_model_spec.md` - Industry standard fields
2. `docs/ingredient_taxonomy_research.md` - Taxonomy background

**Existing models to update:**
1. `src/models/product.py` → rename to `ingredient.py`, add spec fields
2. `src/models/product_variant.py` → rename to `variant.py`, add spec fields
3. `src/models/pantry_item.py` → update field names, add UUID
4. `src/models/purchase_history.py` → rename to `purchase.py`, update fields

---

## Questions Answered (For Reference)

### Q: How do different package sizes work?
**A:** Different packages = different Variants

Example:
- Ingredient: "White Crystal Sugar"
  - Variant #1: "Domino 25 lb bag"
  - Variant #2: "Domino 5 lb bag"
  - Variant #3: "Wegmans 5 lb bag"

### Q: What about non-commercial sources?
**A:** Variant model handles both commercial and non-commercial

Examples:
- Farm stand: `Variant(source_description="Main St Farm Stand", brand_name=None)`
- Butcher: `Variant(source_description="Joe's Butcher - boneless", brand_name=None)`
- Bulk bin: `Variant(source_description="Wegmans bulk bin", brand_name=None)`

### Q: Why "Ingredient" instead of "Product"?
**A:** Domain clarity and flexibility
- "Product" implies commercial/packaged
- "Ingredient" handles commercial AND non-commercial
- Natural for baking domain
- Simpler than "GenericProduct"

### Q: How does FIFO costing work?
**A:** Consume from oldest PantryItems first

```python
# Recipe needs 10 cups flour
# PantryItem #1: 8 cups @ $15.99 (purchased 2024-10-01)
# PantryItem #2: 92 cups @ $17.99 (purchased 2024-11-01)
# Cost: (8 × cost_per_cup_#1) + (2 × cost_per_cup_#2)
```

### Q: What fields are required vs optional?
**A:** Minimal required, most optional

Required now:
- Ingredient: name, slug, category
- Variant: ingredient_id, source_description
- PantryItem: variant_id, qty_on_hand, qty_uom, purchase_date
- Purchase: variant_id, purchased_at, unit_price, purchase_qty, purchase_uom

Optional (future ready):
- Ingredient: foodon_id, fdc_ids, langual_terms, density, allergens
- Variant: brand_name, gtin, net_content, gpc_brick_code
- PantryItem: lot_or_batch, best_by, opened_at
- Supporting tables: All (create but don't populate)

---

## Next Steps When Resuming

1. **Pull feature branch:** `git checkout feature/product-pantry-refactor`

2. **Rename model files:**
   ```bash
   git mv src/models/product.py src/models/ingredient.py
   git mv src/models/product_variant.py src/models/variant.py
   git mv src/models/purchase_history.py src/models/purchase.py
   ```

3. **Update model classes:** Add spec fields (foodon_id, gtin, etc.) as nullable

4. **Create new models:** IngredientAlias, IngredientCrosswalk, VariantPackaging

5. **UUID migration:** Add UUID columns, populate, update FKs

6. **Data migration script:** `migrate_to_ingredient_variant.py`

7. **Minimal UI:** My Ingredients tab, My Pantry tab

8. **FIFO service:** Update recipe costing with new models

---

## Dependencies & Setup

**Python Environment:**
```bash
cd C:\Users\Kent\Vaults-repos\bake-tracker
venv\Scripts\activate
```

**Database:**
- Development: `C:\Users\Kent\Documents\BakeTracker\bake_tracker.db`
- Test laptop: `C:\Users\Marianne\Documents\BakeTracker\bake_tracker.db`

**Branch:**
```bash
git checkout feature/product-pantry-refactor
git pull origin feature/product-pantry-refactor
```

---

## Testing Strategy (When Implementing)

**Migration Validation:**
1. Export v0.3.0 data to JSON
2. Run migration script
3. Verify all Ingredients migrated to Ingredient+Variant
4. Verify RecipeIngredient.ingredient_id populated
5. Test cost calculations (old vs new should match)
6. Test shopping list generation

**FIFO Testing:**
1. Create ingredient with 2 variants
2. Add 3 pantry items with different purchase dates
3. Create recipe using that ingredient
4. Calculate cost - verify FIFO order (oldest consumed first)
5. Verify cost breakdown by lot

**UI Testing:**
1. Create new ingredient (name, category only)
2. Add variant (brand, package)
3. Add to pantry (qty, unit, date)
4. Create recipe using ingredient
5. Generate shopping list

---

## Blocked Items (Future)

**Blocked on data ingestion:**
- FoodOn ID population (need curated subset or API)
- FDC nutrition links (need API integration)
- GTIN validation (need GS1 algorithm)
- LanguaL facets (need taxonomy import)

**Blocked on UI complexity:**
- IngredientAlias autocomplete
- VariantPackaging hierarchy view
- Multi-location pantry management
- Allergen warnings

**Blocked on external services:**
- Open Food Facts sync
- GS1 data feeds
- Recipe ingestion from websites

---

## Success Criteria (v0.4.0 Release)

**Must Have:**
- ✅ Ingredient/Variant separation working
- ✅ Multiple brands/sources per ingredient
- ✅ Preferred variant logic
- ✅ FIFO costing accurate
- ✅ Pantry lot tracking
- ✅ All spec fields in schema (even if nullable)
- ✅ Migration from v0.3.0 preserves all data
- ✅ Cost calculations match v0.3.0

**Nice to Have:**
- GTIN entry (optional)
- Best-by dates (optional)
- IngredientAlias table (create but don't use)

**Deferred to v0.5.0+:**
- FoodOn/FDC enrichment
- Allergen warnings
- Location management UI
- Unit master table

---

## Contact / Handoff

**When resuming:**
- Read this file first (PAUSE_POINT.md)
- Review REFACTOR_STATUS.md for detailed examples
- Check ingredient_data_model_spec.md for field definitions
- Start with model renaming and spec field additions

**Questions to address when resuming:**
1. UUID library preference? (Python uuid.uuid4() recommended)
2. Slug auto-generation logic? (name.lower().replace(' ', '_'))
3. GTIN validation strictness? (Defer to Phase 2)

---

**Status:** ⏸️ PAUSED - Documentation complete, ready to resume implementation
**Branch:** `feature/product-pantry-refactor`
**Last Updated:** 2025-11-06
**Next Project:** Intentional
**Return Context:** Start with model renaming, add spec fields, implement UUID migration
