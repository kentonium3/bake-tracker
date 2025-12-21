# Claude Code Prompt: Complete Pantry Catalog Setup

## Context

We have 30 missing ingredients preventing 34 products from importing. I've created standardized ingredient definitions and identified 20 ingredient slug changes needed to align with USDA naming conventions.

## Your Tasks

### Task 1: Rename Product Import File

**Action:** Rename the file for parallel naming with `ingredients_catalog.json`

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/test_data
mv products_import.json products_catalog.json
```

**Verify:** Confirm `products_catalog.json` exists and `products_import.json` is removed.

---

### Task 2: Update Ingredient Slug References in products_catalog.json

**File:** `test_data/products_catalog.json`

**Action:** Perform 20 find/replace operations to standardize ingredient slugs. These changes align with USDA FoodData Central naming conventions.

**Find/Replace Operations:**

1. `"ingredient_slug": "drops_special_dark"` → `"ingredient_slug": "chocolate_kisses_dark"`
2. `"ingredient_slug": "chips_special_dark"` → `"ingredient_slug": "chocolate_chips_dark"`
3. `"ingredient_slug": "cocoa_powder"` → `"ingredient_slug": "cocoa_powder_natural"`
4. `"ingredient_slug": "covered_candy_milk_chocolate"` → `"ingredient_slug": "chocolate_coating_milk"`
5. `"ingredient_slug": "coffee_extract"` → `"ingredient_slug": "extract_coffee"`
6. `"ingredient_slug": "chocolate_extract"` → `"ingredient_slug": "extract_chocolate"`
7. `"ingredient_slug": "mint_extract"` → `"ingredient_slug": "extract_mint"`
8. `"ingredient_slug": "coconut_extract"` → `"ingredient_slug": "extract_coconut"`
9. `"ingredient_slug": "raspberry_extract"` → `"ingredient_slug": "extract_raspberry"`
10. `"ingredient_slug": "vanilla_extract_mexican"` → `"ingredient_slug": "extract_vanilla_mexican"`
11. `"ingredient_slug": "vanilla_extract_oak_aged"` → `"ingredient_slug": "extract_vanilla_oak_aged"`
12. `"ingredient_slug": "vanilla_extract_spiced"` → `"ingredient_slug": "extract_vanilla_spiced"`
13. `"ingredient_slug": "vanilla_powder"` → `"ingredient_slug": "vanilla_powder_pure"`
14. `"ingredient_slug": "vanilla_powder_with_extract"` → `"ingredient_slug": "vanilla_powder_extract_blend"`
15. `"ingredient_slug": "stevia_sweetener"` → `"ingredient_slug": "sweetener_stevia"`
16. `"ingredient_slug": "cinnamon_sticks_indonesia"` → `"ingredient_slug": "cinnamon_sticks_indonesian"`
17. `"ingredient_slug": "nutmeg_ground_east_india"` → `"ingredient_slug": "nutmeg_ground_east_indian"`
18. `"ingredient_slug": "nutmeg_ground_west_india"` → `"ingredient_slug": "nutmeg_ground_west_indian"`
19. `"ingredient_slug": "pepper_black_ground_tellicherry"` → `"ingredient_slug": "pepper_black_tellicherry"`
20. `"ingredient_slug": "chinese_five_spice"` → `"ingredient_slug": "spice_blend_chinese_five_spice"`
21. `"ingredient_slug": "mulling_spices"` → `"ingredient_slug": "spice_blend_mulling"`
22. `"ingredient_slug": "lavender"` → `"ingredient_slug": "lavender_culinary"`
23. `"ingredient_slug": "sesame_seeds_india_black"` → `"ingredient_slug": "sesame_seeds_black"`

**Important Notes:**
- Some slugs appear in multiple product records (total ~34 replacements across all products)
- Verify JSON syntax remains valid after all replacements
- Count total replacements to ensure all instances were updated

**Verification Steps:**
1. Open `products_catalog.json` and search for old slug patterns (should find 0 matches)
2. Validate JSON syntax: `python -m json.tool test_data/products_catalog.json > /dev/null`
3. Report count of replacements made

---

### Task 3: Delete Existing Database

**Action:** Delete the current database to start fresh with standardized naming

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker
rm bake_tracker.db
```

**Verify:** Confirm `bake_tracker.db` is deleted:
```bash
ls -la bake_tracker.db  # Should return "No such file or directory"
```

**Rationale:** The existing database has 122 products referencing old ingredient slugs. Deleting ensures no foreign key mismatches when we import with standardized naming.

---

## Completion Report

After completing all tasks, provide a summary report:

```
✅ File Rename:
   - products_import.json → products_catalog.json

✅ Slug Updates:
   - Total replacements made: [count]
   - JSON validation: [pass/fail]
   - Old slugs remaining: [count - should be 0]

✅ Database Deletion:
   - bake_tracker.db deleted: [yes/no]

Status: Ready for import sequence
```

---

## What Happens Next (User Will Execute)

After you complete these tasks, I will run the following import sequence:

```bash
# 1. Import base ingredients catalog (~450+ ingredients)
python -m src.cli.catalog_import test_data/ingredients_catalog.json --mode add

# 2. Import missing ingredients (30 new ingredients)
python -m src.cli.catalog_import test_data/ingredients_missing.json --mode add

# 3. Import complete product catalog (156 products)
python -m src.cli.catalog_import test_data/products_catalog.json --mode add
```

**Expected Result:** 156 products imported with 0 errors, complete pantry catalog ready for workflow testing.

---

## Reference Files

- **Ingredient Definitions:** `test_data/ingredients_missing.json` (30 new ingredients - already created)
- **Mapping Documentation:** `test_data/ingredient_slug_mapping.md` (detailed rationale for all changes)
- **Implementation Summary:** `test_data/IMPLEMENTATION_SUMMARY.md` (complete overview)
- **Error Log:** Import error log showing the 34 failed products (user has this)

---

## Questions to Confirm Before Starting

1. Should I proceed with all 3 tasks (rename, update slugs, delete DB)?
2. Do you want me to create a backup of products_import.json before renaming?
3. Should I validate the updated JSON syntax after making changes?
