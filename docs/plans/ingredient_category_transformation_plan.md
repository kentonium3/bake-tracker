# Ingredient & Category Transformation Plan

## Overview

This plan covers applying two data transformations:
1. **Category Rationalization** - Reduce 20 categories to 12 standardized categories (Phase 1)
2. **Ingredient Consolidation** - Merge 22 fine-grained ingredients into generalized versions (Phase 2)

## Decisions (Finalized 2024-12-24)

| Question | Decision |
|----------|----------|
| Missing target ingredients | **Rename existing variant** to become canonical |
| Special case mappings | **Apply as specified** in category_mapping.json |
| Implementation approach | **Direct edits** (no scripts) |

### Canonical Renames (3 ingredients)

| Current Slug | Rename To | Other Sources (delete after FK update) |
|--------------|-----------|----------------------------------------|
| `almonds_whole` | `almonds` | almonds_sliced, almonds_slivered |
| `cornmeal_medium` | `cornmeal` | cornmeal_coarse, cornmeal_fine |
| `food_coloring_gel` | `food_coloring` | food_coloring_liquid, food_coloring_powder |

## Source Files

- `test_data/ingredient_consolidation_mapping.json` - 22 slug-to-slug mappings
- `test_data/category_mapping.json` - Category mappings with special cases

## Current State (Verified 2024-12-24)

| Check | Result |
|-------|--------|
| Dev DB snapshots | 0 (safe to delete ingredients) |
| Prod DB snapshots | 0 (safe to delete ingredients) |
| Current categories | 20 (matches "before" count) |

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

**Action:** Rename these 3 variants to become the canonical target (see Decisions section above).

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

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| FK constraint violations | Run in transaction, rollback on error |
| Recipe breakage | Run full test suite before production |
| Import/export drift | Re-export all catalogs after changes |

---

## Detailed Execution Steps

### FK Relationship Audit (Verified 2024-12-24)

| Table | FK Column | On Delete | Current Rows | Notes |
|-------|-----------|-----------|--------------|-------|
| `products` | `ingredient_id` | CASCADE | has data | Updated before delete |
| `recipe_ingredients` | `ingredient_id` | RESTRICT | has data | Updated before delete |
| `ingredient_aliases` | `ingredient_id` | CASCADE | 0 | No data to lose |
| `ingredient_crosswalks` | `ingredient_id` | CASCADE | 0 | No data to lose |
| `snapshot_ingredients` | `ingredient_id` | RESTRICT | 0 | Won't block delete |

**Integrity approach:** All SQL wrapped in transactions with explicit COMMIT. On any error, ROLLBACK before retrying.

### Pre-flight

```bash
# Backup databases
cp data/bake_tracker.db data/bake_tracker.db.backup-$(date +%Y%m%d)
cp ~/Documents/BakeTracker/bake_tracker.db ~/Documents/BakeTracker/bake_tracker.db.backup-$(date +%Y%m%d)
```

### Phase 1: Category Rationalization

#### Step 1.1: Dev DB - Bulk category updates
```sql
-- Run as single transaction
BEGIN TRANSACTION;

-- Standard mappings (categories that just need renaming)
UPDATE ingredients SET category = 'Decorations & Candies' WHERE category = 'Candies & Decorations';
UPDATE ingredients SET category = 'Chocolate & Cocoa' WHERE category = 'Chocolate & Candies';
UPDATE ingredients SET category = 'Dairy & Eggs' WHERE category = 'Dairy';
UPDATE ingredients SET category = 'Flours & Starches' WHERE category = 'Flours & Meals';
UPDATE ingredients SET category = 'Fruits & Dried Fruits' WHERE category = 'Fruits';
UPDATE ingredients SET category = 'Liquids & Liquors' WHERE category = 'Liquids';
UPDATE ingredients SET category = 'Spices & Extracts' WHERE category = 'Spices & Flavorings';
UPDATE ingredients SET category = 'Chocolate & Cocoa' WHERE category = 'baking_chocolate';
UPDATE ingredients SET category = 'Spices & Extracts' WHERE category = 'extracts_flavorings';
UPDATE ingredients SET category = 'Flours & Starches' WHERE category = 'flour';
UPDATE ingredients SET category = 'Spices & Extracts' WHERE category = 'spices';
UPDATE ingredients SET category = 'Sugars & Sweeteners' WHERE category = 'sugar_sweeteners';
```

#### Step 1.2: Dev DB - Special case mappings (Other / Misc items)
```sql
-- Fats & Oils
UPDATE ingredients SET category = 'Fats & Oils' WHERE slug IN ('biscoff_spread', 'nutella', 'cocoa_butter');

-- Fruits & Dried Fruits
UPDATE ingredients SET category = 'Fruits & Dried Fruits' WHERE slug = 'glaze_apricot';

-- Decorations & Candies
UPDATE ingredients SET category = 'Decorations & Candies' WHERE slug IN ('malted_milk_balls', 'pretzels', 'baking_wafers_vanilla');

-- Flours & Starches
UPDATE ingredients SET category = 'Flours & Starches' WHERE slug IN ('oats_quick', 'oats_rolled');

-- Dairy & Eggs
UPDATE ingredients SET category = 'Dairy & Eggs' WHERE slug = 'powdered_milk_malted';

-- Chocolate & Cocoa
UPDATE ingredients SET category = 'Chocolate & Cocoa' WHERE slug = 'baking_wafers_chocolate';

-- Additives & Thickeners (remaining Other / Misc)
UPDATE ingredients SET category = 'Additives & Thickeners' WHERE category = 'Other / Misc';

COMMIT;
-- If any error occurs, run: ROLLBACK;
```

#### Step 1.3: Validate Dev DB
```sql
-- Should return exactly 12 categories
SELECT category, COUNT(*) as count FROM ingredients GROUP BY category ORDER BY category;

-- Should return 0 rows (no old categories remain)
SELECT DISTINCT category FROM ingredients
WHERE category IN ('Candies & Decorations', 'Chocolate & Candies', 'Dairy',
                   'Flours & Meals', 'Fruits', 'Liquids', 'Other / Misc',
                   'Spices & Flavorings', 'baking_chocolate', 'extracts_flavorings',
                   'flour', 'spices', 'sugar_sweeteners');
```

#### Step 1.4: Apply same SQL to Production DB
(Same SQL as Steps 1.1-1.3)

#### Step 1.5: Update JSON files
- `test_data/ingredients_catalog.json` - Update category field for all affected ingredients
- `test_data/sample_data.json` - Update category field in ingredients array

---

### Phase 2: Ingredient Consolidation

#### Step 2.1: Rename canonical ingredients (Dev DB)
```sql
-- Run ALL of Phase 2 as single transaction
BEGIN TRANSACTION;

-- Rename the 3 variants that become canonical targets
UPDATE ingredients SET slug = 'almonds', display_name = 'Almonds' WHERE slug = 'almonds_whole';
UPDATE ingredients SET slug = 'cornmeal', display_name = 'Cornmeal' WHERE slug = 'cornmeal_medium';
UPDATE ingredients SET slug = 'food_coloring', display_name = 'Food Coloring' WHERE slug = 'food_coloring_gel';

-- (Transaction continues in Step 2.2)
```

#### Step 2.2: Update FK references for sources → targets (Dev DB)
```sql
-- (Continuing transaction from Step 2.1)
-- For each source ingredient, update FKs to point to target, then delete source

-- almonds_sliced, almonds_slivered → almonds
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'almonds')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'almonds_sliced');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'almonds')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'almonds_sliced');
DELETE FROM ingredients WHERE slug = 'almonds_sliced';

UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'almonds')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'almonds_slivered');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'almonds')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'almonds_slivered');
DELETE FROM ingredients WHERE slug = 'almonds_slivered';

-- cornmeal_coarse, cornmeal_fine → cornmeal
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cornmeal')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cornmeal_coarse');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cornmeal')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cornmeal_coarse');
DELETE FROM ingredients WHERE slug = 'cornmeal_coarse';

UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cornmeal')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cornmeal_fine');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cornmeal')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cornmeal_fine');
DELETE FROM ingredients WHERE slug = 'cornmeal_fine';

-- food_coloring_liquid, food_coloring_powder → food_coloring
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'food_coloring')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'food_coloring_liquid');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'food_coloring')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'food_coloring_liquid');
DELETE FROM ingredients WHERE slug = 'food_coloring_liquid';

UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'food_coloring')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'food_coloring_powder');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'food_coloring')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'food_coloring_powder');
DELETE FROM ingredients WHERE slug = 'food_coloring_powder';

-- canola_oil → oil_canola (target exists)
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'oil_canola')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'canola_oil');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'oil_canola')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'canola_oil');
DELETE FROM ingredients WHERE slug = 'canola_oil';

-- olive_oil → oil_olive (target exists)
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'oil_olive')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'olive_oil');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'oil_olive')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'olive_oil');
DELETE FROM ingredients WHERE slug = 'olive_oil';

-- cherries_candied_green, cherries_candied_red → candied_cherries (target exists)
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'candied_cherries')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cherries_candied_green');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'candied_cherries')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cherries_candied_green');
DELETE FROM ingredients WHERE slug = 'cherries_candied_green';

UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'candied_cherries')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cherries_candied_red');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'candied_cherries')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cherries_candied_red');
DELETE FROM ingredients WHERE slug = 'cherries_candied_red';

-- cinnamon_ground_ceylon → cinnamon_ground (target exists)
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cinnamon_ground')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cinnamon_ground_ceylon');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cinnamon_ground')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cinnamon_ground_ceylon');
DELETE FROM ingredients WHERE slug = 'cinnamon_ground_ceylon';

-- cinnamon_sticks_indonesian → cinnamon_sticks (target exists)
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cinnamon_sticks')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cinnamon_sticks_indonesian');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cinnamon_sticks')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'cinnamon_sticks_indonesian');
DELETE FROM ingredients WHERE slug = 'cinnamon_sticks_indonesian';

-- espresso_powder_instant → espresso_powder (target exists)
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'espresso_powder')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'espresso_powder_instant');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'espresso_powder')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'espresso_powder_instant');
DELETE FROM ingredients WHERE slug = 'espresso_powder_instant';

-- pecans_chopped, pecans_halves → pecans (target exists)
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pecans')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pecans_chopped');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pecans')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pecans_chopped');
DELETE FROM ingredients WHERE slug = 'pecans_chopped';

UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pecans')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pecans_halves');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pecans')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pecans_halves');
DELETE FROM ingredients WHERE slug = 'pecans_halves';

-- pepper_black_tellicherry → pepper_black_ground (target exists)
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pepper_black_ground')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pepper_black_tellicherry');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pepper_black_ground')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'pepper_black_tellicherry');
DELETE FROM ingredients WHERE slug = 'pepper_black_tellicherry';

-- sesame_seeds_black, sesame_seeds_white → sesame_seeds (target exists)
UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'sesame_seeds')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'sesame_seeds_black');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'sesame_seeds')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'sesame_seeds_black');
DELETE FROM ingredients WHERE slug = 'sesame_seeds_black';

UPDATE products SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'sesame_seeds')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'sesame_seeds_white');
UPDATE recipe_ingredients SET ingredient_id = (SELECT id FROM ingredients WHERE slug = 'sesame_seeds')
  WHERE ingredient_id = (SELECT id FROM ingredients WHERE slug = 'sesame_seeds_white');
DELETE FROM ingredients WHERE slug = 'sesame_seeds_white';

COMMIT;
-- If any error occurs, run: ROLLBACK;
```

#### Step 2.3: Validate Dev DB
```sql
-- Verify no source slugs remain
SELECT slug FROM ingredients WHERE slug IN (
  'almonds_sliced', 'almonds_slivered', 'almonds_whole',
  'canola_oil', 'olive_oil',
  'cherries_candied_green', 'cherries_candied_red',
  'cinnamon_ground_ceylon', 'cinnamon_sticks_indonesian',
  'cornmeal_coarse', 'cornmeal_fine', 'cornmeal_medium',
  'espresso_powder_instant',
  'food_coloring_gel', 'food_coloring_liquid', 'food_coloring_powder',
  'pecans_chopped', 'pecans_halves',
  'pepper_black_tellicherry',
  'sesame_seeds_black', 'sesame_seeds_white'
);
-- Should return 0 rows

-- Verify canonical targets exist
SELECT slug FROM ingredients WHERE slug IN (
  'almonds', 'cornmeal', 'food_coloring',
  'oil_canola', 'oil_olive', 'candied_cherries',
  'cinnamon_ground', 'cinnamon_sticks', 'espresso_powder',
  'pecans', 'pepper_black_ground', 'sesame_seeds'
);
-- Should return 12 rows
```

#### Step 2.4: Run test suite
```bash
pytest src/tests -v
```

#### Step 2.5: Apply same SQL to Production DB
(Same SQL as Steps 2.1-2.3)

#### Step 2.6: Update JSON files
- `test_data/ingredients_catalog.json` - Remove source ingredients, update renamed slugs
- `test_data/products_catalog.json` - Update ingredient_slug references
- `test_data/sample_data.json` - Update ingredients and products arrays
- `test_data/inventory.json` - Update ingredient_slug if present
