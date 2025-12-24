# Ingredient & Category Transformation Plan

## Overview

This plan covers applying two data transformations:
1. **Ingredient Consolidation** - Merge 22 fine-grained ingredients into generalized versions
2. **Category Rationalization** - Reduce 20 categories to 12 standardized categories

## Source Files

- `test_data/ingredient_consolidation_mapping.json` - 22 slug-to-slug mappings
- `test_data/category_mapping.json` - Category mappings with special cases

---

## Part 1: Category Rationalization (Simpler - Do First)

### What Changes

Update `Ingredient.category` field for all affected ingredients.

**Mapping (20 → 12 categories):**
| Old Category | New Category |
|-------------|--------------|
| Candies & Decorations | Decorations & Candies |
| Chocolate & Candies | Chocolate & Cocoa |
| Dairy | Dairy & Eggs |
| Flours & Meals | Flours & Starches |
| Fruits | Fruits & Dried Fruits |
| Liquids | Liquids & Liquors |
| Other / Misc | See special_cases |
| Spices & Flavorings | Spices & Extracts |
| baking_chocolate | Chocolate & Cocoa |
| extracts_flavorings | Spices & Extracts |
| flour | Flours & Starches |
| spices | Spices & Extracts |
| sugar_sweeteners | Sugars & Sweeteners |

**Special Cases (Other / Misc items):**
- `biscoff_spread`, `nutella`, `cocoa_butter` → Fats & Oils
- `glaze_apricot` → Fruits & Dried Fruits
- `malted_milk_balls`, `pretzels`, `baking_wafers_vanilla` → Decorations & Candies
- `oats_quick`, `oats_rolled` → Flours & Starches
- `powdered_milk_malted` → Dairy & Eggs
- `baking_wafers_chocolate` → Chocolate & Cocoa
- Rest → Additives & Thickeners

### Transformation Steps

1. **Update JSON catalog files:**
   - `test_data/ingredients_catalog.json` - Update category field
   - `test_data/sample_data.json` - Update category field in ingredients array

2. **Update Development DB:**
   ```sql
   UPDATE ingredients SET category = 'New Category' WHERE category = 'Old Category';
   UPDATE ingredients SET category = 'Fats & Oils' WHERE slug = 'biscoff_spread';
   -- etc for special cases
   ```

3. **Update Production DB:**
   - Same SQL as dev DB

### Validation

- Count ingredients per category before/after
- Verify all 12 new categories exist
- Verify no old category names remain

---

## Part 2: Ingredient Consolidation (Complex - FK Dependencies)

### What Changes

Merge ingredients by updating foreign key references, then deactivate/delete old ingredients.

**Consolidations (22 mappings):**
| Old Slug | New Slug |
|----------|----------|
| almonds_sliced | almonds |
| almonds_slivered | almonds |
| almonds_whole | almonds |
| canola_oil | oil_canola |
| cherries_candied_green | candied_cherries |
| cherries_candied_red | candied_cherries |
| cinnamon_ground_ceylon | cinnamon_ground |
| cinnamon_sticks_indonesian | cinnamon_sticks |
| cornmeal_coarse | cornmeal |
| cornmeal_fine | cornmeal |
| cornmeal_medium | cornmeal |
| espresso_powder_instant | espresso_powder |
| food_coloring_gel | food_coloring |
| food_coloring_liquid | food_coloring |
| food_coloring_powder | food_coloring |
| olive_oil | oil_olive |
| pecans_chopped | pecans |
| pecans_halves | pecans |
| pepper_black_tellicherry | pepper_black_ground |
| sesame_seeds_black | sesame_seeds |
| sesame_seeds_white | sesame_seeds |

### FK Dependencies (Must Update in Order)

| Table | Column | On Delete | Action |
|-------|--------|-----------|--------|
| products | ingredient_id | CASCADE | Update to target ingredient |
| recipe_ingredients | ingredient_id | RESTRICT | Update to target ingredient |
| ingredient_aliases | ingredient_id | CASCADE | Keep or delete |
| ingredient_crosswalks | ingredient_id | CASCADE | Keep or delete |
| snapshot_ingredients | ingredient_id | RESTRICT | **Problem: Historical data** |

### Critical Issue: SnapshotIngredient

`SnapshotIngredient` has `RESTRICT` delete behavior and represents historical point-in-time data. Options:

1. **Keep old ingredients** - Mark as inactive instead of deleting
2. **Update snapshots** - Change historical references (loses granularity)
3. **Add ingredient_slug** - Store slug in snapshot for historical reference

**Recommendation:** Option 1 - Keep old ingredients as inactive. This preserves historical data integrity.

### Schema Issue: Ingredient Missing `is_active` Field

The `Ingredient` model does NOT have an `is_active` field (Supplier does). Options:

1. **Add `is_active` to Ingredient model** - Requires schema migration
2. **Move to IngredientLegacy table** - Already exists for this purpose
3. **Delete if no snapshots reference** - Check before delete, keep if referenced

**Recommendation:** Check if `IngredientLegacy` is appropriate, or add `is_active` field.

### Current State Check

```
Dev DB Snapshots: 0
Production DB Snapshots: 0
```

**Since no snapshots exist**, we can safely delete old ingredients after updating FK references. The RESTRICT constraint won't block us.

### Transformation Steps

#### Pre-requisite: Ensure Target Ingredients Exist

**Checked - 3 targets need creation:**

| Target Slug | Status | Sources to Merge |
|-------------|--------|------------------|
| almonds | **MISSING** | almonds_sliced, almonds_slivered, almonds_whole |
| cornmeal | **MISSING** | cornmeal_coarse, cornmeal_fine, cornmeal_medium |
| food_coloring | **MISSING** | food_coloring_gel, food_coloring_liquid, food_coloring_powder |

**9 targets already exist:** candied_cherries, cinnamon_ground, cinnamon_sticks, espresso_powder, oil_canola, oil_olive, pecans, pepper_black_ground, sesame_seeds

**Action:** Create the 3 missing ingredients before consolidation, inheriting properties from one of the source ingredients (e.g., use `almonds_whole` as template for `almonds`).

#### Step 1: Update JSON Files

For each mapping `old_slug → new_slug`:

1. In `ingredients_catalog.json`:
   - Keep target ingredient
   - Remove source ingredients (or mark inactive)

2. In `products_catalog.json`:
   - Update `ingredient_slug` field from old to new

3. In `sample_data.json`:
   - Update ingredients array
   - Update products array (ingredient_slug references)

4. In `inventory.json`:
   - Update ingredient_slug in inventory_items (if present)

#### Step 2: Update Development DB

```sql
-- For each consolidation, run in order:

-- 1. Get IDs
SELECT id FROM ingredients WHERE slug = 'almonds_sliced';  -- old_id
SELECT id FROM ingredients WHERE slug = 'almonds';         -- new_id

-- 2. Update Products
UPDATE products SET ingredient_id = {new_id} WHERE ingredient_id = {old_id};

-- 3. Update RecipeIngredients
UPDATE recipe_ingredients SET ingredient_id = {new_id} WHERE ingredient_id = {old_id};

-- 4. Delete old ingredient (safe - no snapshots reference it)
DELETE FROM ingredients WHERE id = {old_id};
```

**Note:** Since no InventorySnapshots exist, we can safely DELETE instead of marking inactive.

#### Step 3: Update Production DB

Same SQL as dev DB.

### Validation

- Count products per ingredient before/after
- Verify no recipes reference inactive ingredients
- Verify inventory lookups still work
- Run test suite

---

## Execution Order

1. **Backup all databases**
   ```bash
   cp data/bake_tracker.db data/bake_tracker.db.backup
   cp ~/Documents/BakeTracker/bake_tracker.db ~/Documents/BakeTracker/bake_tracker.db.backup
   ```

2. **Category Rationalization**
   - Update JSON files
   - Update dev DB
   - Validate
   - Update production DB
   - Validate

3. **Ingredient Consolidation**
   - Create missing target ingredients if needed
   - Update JSON files
   - Update dev DB
   - Run test suite
   - Update production DB
   - Validate

4. **Re-export catalogs**
   - Export fresh `ingredients_catalog.json`
   - Export fresh `products_catalog.json`
   - Export fresh `sample_data.json`

---

## Scripts Needed

1. **apply_category_mapping.py** - Applies category changes to DB
2. **apply_ingredient_consolidation.py** - Handles FK updates and deactivation
3. **validate_transformations.py** - Verifies data integrity post-transformation

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| FK constraint violations | Run in transaction, rollback on error |
| Missing target ingredients | Pre-create before consolidation |
| Historical snapshot data loss | Mark inactive instead of delete |
| Recipe breakage | Run full test suite before production |
| Import/export drift | Re-export all catalogs after changes |

---

## Questions for User

1. **Target ingredient creation**: Should missing targets (e.g., generic `almonds`) be created, or should we pick an existing specific one as the canonical?

2. **Inactive vs Delete**: Confirm preference to mark consolidated ingredients as `is_active=False` rather than delete?

3. **Snapshot handling**: Accept that historical snapshots will reference inactive ingredients?
