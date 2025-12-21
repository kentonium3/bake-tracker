# Ingredient Slug Mapping - Missing Ingredients

**Purpose:** This document maps original product reference slugs to standardized ingredient slugs for the 30 missing ingredients.

**Action Required:** Claude Code must update `products_import.json` to replace old slugs with new slugs before re-importing products.

---

## Slug Changes Required

### Chocolate Products (6 changes)

| Original Slug | New Slug | Reasoning |
|---------------|----------|-----------|
| `drops_special_dark` | `chocolate_kisses_dark` | Industry standard: "kisses" for foil-wrapped chocolate drops |
| `chips_special_dark` | `chocolate_chips_dark` | Industry standard: "dark" for special dark chocolate chips |
| `chocolate_chips_espresso` | *(no change)* | Already industry standard |
| `chocolate_chips_semi_sweet_allergen_free` | *(no change)* | Already industry standard |
| `cocoa_powder` | `cocoa_powder_natural` | USDA standard: specify natural vs Dutch-processed |
| `covered_candy_milk_chocolate` | `chocolate_coating_milk` | Industry standard: "coating" for candy melts/coating chocolate |

**Products Affected:**
- Hershey's (drops_special_dark) → chocolate_kisses_dark
- Hershey's (chips_special_dark) → chocolate_chips_dark
- Hershey's (cocoa_powder) → cocoa_powder_natural
- Nestlé (chocolate_chips_espresso) - no change
- Nestlé (chocolate_chips_semi_sweet_allergen_free) - no change
- Cadbury (covered_candy_milk_chocolate) → chocolate_coating_milk
- Mars (covered_candy_milk_chocolate) → chocolate_coating_milk

---

### Extracts (9 changes)

| Original Slug | New Slug | Reasoning |
|---------------|----------|-----------|
| `coffee_extract` | `extract_coffee` | USDA pattern: "extract, [flavor]" |
| `chocolate_extract` | `extract_chocolate` | USDA pattern: "extract, [flavor]" |
| `mint_extract` | `extract_mint` | USDA pattern: "extract, [flavor]" |
| `coconut_extract` | `extract_coconut` | USDA pattern: "extract, [flavor]" |
| `raspberry_extract` | `extract_raspberry` | USDA pattern: "extract, [flavor]" |
| `vanilla_extract_mexican` | `extract_vanilla_mexican` | USDA pattern: "extract, vanilla, [origin]" |
| `vanilla_extract_oak_aged` | `extract_vanilla_oak_aged` | USDA pattern: "extract, vanilla, [type]" |
| `vanilla_extract_spiced` | `extract_vanilla_spiced` | USDA pattern: "extract, vanilla, [type]" |
| `vanilla_powder` | `vanilla_powder_pure` | Clarity: distinguish from extract blend |
| `vanilla_powder_with_extract` | `vanilla_powder_extract_blend` | Clarity: more descriptive name |

**Products Affected:**
- Flavor Organics (coffee_extract) → extract_coffee
- Flavor Organics (chocolate_extract) → extract_chocolate
- McCormick (chocolate_extract) → extract_chocolate
- McCormick (mint_extract) → extract_mint
- McCormick (coconut_extract) → extract_coconut
- McCormick (raspberry_extract) → extract_raspberry
- Penzeys (vanilla_extract_mexican) → extract_vanilla_mexican
- Heilala (vanilla_extract_oak_aged) → extract_vanilla_oak_aged
- Heilala (vanilla_extract_spiced) → extract_vanilla_spiced
- Heilala (vanilla_powder) → vanilla_powder_pure
- Heilala (vanilla_powder_with_extract) → vanilla_powder_extract_blend

---

### Flour/Sweeteners (2 changes)

| Original Slug | New Slug | Reasoning |
|---------------|----------|-----------|
| `flour_almond` | *(no change)* | Already industry standard |
| `stevia_sweetener` | `sweetener_stevia` | USDA pattern: "sweetener, [type]" |

**Products Affected:**
- King Arthur (flour_almond) - no change
- Truvia (stevia_sweetener) → sweetener_stevia

---

### Spices (13 changes)

| Original Slug | New Slug | Reasoning |
|---------------|----------|-----------|
| `cinnamon_ground_ceylon` | *(no change)* | Already industry standard |
| `cinnamon_sticks_indonesia` | `cinnamon_sticks_indonesian` | Grammar: "Indonesian" (adjective form) |
| `nutmeg_ground_east_india` | `nutmeg_ground_east_indian` | USDA standard: "East Indian" (not "East India") |
| `nutmeg_ground_west_india` | `nutmeg_ground_west_indian` | USDA standard: "West Indian" (not "West India") |
| `allspice_whole` | *(no change)* | Already industry standard |
| `pepper_black_ground_tellicherry` | `pepper_black_tellicherry` | Simplification: "ground" implied by context |
| `chinese_five_spice` | `spice_blend_chinese_five_spice` | USDA pattern: "spice blend, [name]" |
| `mulling_spices` | `spice_blend_mulling` | USDA pattern: "spice blend, [name]" |
| `lavender` | `lavender_culinary` | Clarity: culinary vs decorative lavender |
| `poppy_seeds_blue` | *(no change)* | Already industry standard |
| `sesame_seeds_india_black` | `sesame_seeds_black` | Simplification: origin less important than color |
| `sesame_seeds_white` | *(no change)* | Already industry standard |

**Products Affected:**
- Penzeys (cinnamon_ground_ceylon) - no change
- Penzeys (cinnamon_sticks_indonesia) → cinnamon_sticks_indonesian
- Penzeys (nutmeg_ground_east_india) → nutmeg_ground_east_indian (2 products)
- Penzeys (nutmeg_ground_west_india) → nutmeg_ground_west_indian
- Penzeys (allspice_whole) - no change
- Penzeys (pepper_black_ground_tellicherry) → pepper_black_tellicherry
- Penzeys (chinese_five_spice) → spice_blend_chinese_five_spice
- Penzeys (mulling_spices) → spice_blend_mulling
- Penzeys (lavender) → lavender_culinary
- Penzeys (poppy_seeds_blue) - no change
- Penzeys (sesame_seeds_india_black) → sesame_seeds_black
- Penzeys (sesame_seeds_white) - no change

---

## Summary Statistics

**Total Slugs:** 30
**Slugs Changed:** 20
**Slugs Unchanged:** 10

**Changes by Category:**
- Chocolate: 4 of 6 changed
- Extracts: 9 of 9 changed
- Flour/Sweeteners: 1 of 2 changed
- Spices: 6 of 13 changed

---

## Implementation Steps for Claude Code

### Step 1: Rename Product Import File
**Rename:** `products_import.json` → `products_catalog.json`
- Rationale: Parallel naming with `ingredients_catalog.json`
- Update any references in documentation

### Step 2: Update products_catalog.json
**Find/replace** each "Original Slug" with "New Slug" in ingredient_slug field:
- Products affected: 34 total (some ingredients used by multiple products)
- Verify count of replacements matches expected (see "Products Affected" sections)
- Ensure no unintended replacements

### Step 3: User Deletes Database
**User action:** Delete `bake_tracker.db`
- Rationale: Clean slate avoids FK mismatches with old slugs
- Fresh import with standardized naming throughout

### Step 4: Import Sequence (User Executes)
```bash
# 1. Import base ingredients catalog
python -m src.cli.catalog_import test_data/ingredients_catalog.json --mode add

# 2. Import missing ingredients
python -m src.cli.catalog_import test_data/ingredients_missing.json --mode add

# 3. Import complete product catalog
python -m src.cli.catalog_import test_data/products_catalog.json --mode add
```

### Expected Results:
- ✅ ~450+ base ingredients imported
- ✅ 30 missing ingredients imported
- ✅ 156 products imported (0 errors, 0 skipped on fresh DB)
- ✅ Complete pantry catalog ready for workflow testing

---

## Rationale: Industry Standard Naming

**USDA FoodData Central Pattern:**
- Primary descriptor first: "Extract, vanilla" not "vanilla_extract"
- Specifics second: "Cinnamon, ground, Ceylon" not "ceylon_cinnamon_ground"
- Consistent ordering: [base], [form], [variety/origin]

**Benefits:**
- Alphabetical grouping (all extracts together)
- Clear hierarchy (chocolate chips → chocolate_chips_dark, chocolate_chips_espresso)
- Future-proof (easy to add chocolate_chips_white, chocolate_chips_butterscotch)
- Searchable (filter by "extract_" prefix)

**Exceptions Made:**
- Kept common short forms: `flour_almond` (not `flour_almond_blanched`)
- Kept product-specific terms: `vanilla_powder_pure` (clearer than `powder_vanilla_pure`)
- Kept familiar patterns: `sweetener_stevia` follows existing sugar_sweeteners category
