# Claude Code Prompt: Fix import_v3.json and Update Spec Categories

## Context

Refer to `.kittify/memory/constitution.md` for project principles.

A new import file `test_data/import_v3.json` was generated to support user testing with a comprehensive ingredient catalog. Analysis found several issues that must be fixed before import will succeed.

Reference documents:
- `docs/design/import_export_specification.md` — v3.4 spec (authoritative)
- `docs/research/ingredient_taxonomy_research.md` — category strategy
- `src/utils/constants.py` — valid units

## Task 1: Fix import_v3.json

**File:** `test_data/import_v3.json`

### Fix 1.1: Version Header
- Change `"version": "3.5"` → `"version": "3.4"`

### Fix 1.2: Rename Field
- For ALL ingredients: rename `display_name` → `name`
- The spec requires `name` as the display name field

### Fix 1.3: Remove Extra Spaces
- All ingredient `name` values have multiple consecutive spaces (e.g., `"All-purpose   Wheat   Flour"`)
- Replace multiple spaces with single space
- Trim leading/trailing whitespace

### Fix 1.4: Add Missing Ingredients
Three products reference ingredients that don't exist. Add these ingredients:

```json
{
  "slug": "olive_oil",
  "name": "Olive Oil",
  "category": "Fats & Oils",
  "description": "Olive oil",
  "density_volume_value": 1.0,
  "density_volume_unit": "cup",
  "density_weight_value": 7.68,
  "density_weight_unit": "oz"
},
{
  "slug": "canola_oil",
  "name": "Canola Oil",
  "category": "Fats & Oils",
  "description": "Canola oil",
  "density_volume_value": 1.0,
  "density_volume_unit": "cup",
  "density_weight_value": 7.68,
  "density_weight_unit": "oz"
},
{
  "slug": "lard",
  "name": "Lard",
  "category": "Fats & Oils",
  "description": "Lard",
  "density_volume_value": 1.0,
  "density_volume_unit": "cup",
  "density_weight_value": 7.68,
  "density_weight_unit": "oz"
}
```

### Fix 1.5: Invalid Unit - Wegman's Maple Syrup
The product with `"brand": "Wegman's"` and `"ingredient_slug": "maple_syrup"` uses `"package_unit": "jug"`.

"jug" is not a valid unit. Change to:
```json
{
  "ingredient_slug": "maple_syrup",
  "brand": "Wegman's",
  "package_size": "1 gal jug",
  "package_type": "jug",
  "package_unit": "gal",
  "package_unit_quantity": 1.0,
  "is_preferred": false,
  "notes": "1 gallon jug"
}
```

Note: Move "jug" to `package_type` (descriptive) and use `"gal"` for `package_unit` (measurement). Adjust `package_unit_quantity` accordingly. If actual size is unknown, use 1 gallon as reasonable default for a jug.

### Fix 1.6: Liquid Products Using Weight "oz"
These products use `"oz"` (weight) but are liquids that should use `"fl oz"` (fluid ounce):

1. **Costco maple syrup** (`ingredient_slug": "maple_syrup"`, `"brand": "Costco"`)
   - Change `"package_unit": "oz"` → `"package_unit": "fl oz"`
   
2. **Costco honey** (`"ingredient_slug": "honey"`, `"brand": "Costco"`)
   - Change `"package_unit": "oz"` → `"package_unit": "fl oz"`

## Task 2: Update Spec Appendix A

**File:** `docs/design/import_export_specification.md`

The spec's Appendix A lists outdated ingredient categories. Update to reflect the expanded taxonomy.

### Current (outdated):
```
Flour, Sugar, Dairy, Oils/Butters, Nuts, Spices,
Chocolate/Candies, Cocoa Powders, Dried Fruits,
Extracts, Syrups, Alcohol, Misc
```

### Replace with:
```
Flours & Meals, Sugars & Sweeteners, Fats & Oils, Dairy & Eggs,
Leaveners, Chocolate & Cocoa, Candies & Decorations, Nuts & Seeds,
Spices & Flavorings, Additives & Thickeners, Liquids, Fruits, Misc
```

This aligns with the taxonomy research in `docs/research/ingredient_taxonomy_research.md`.

## Validation

After making changes:

1. Verify `import_v3.json` is valid JSON (no syntax errors)
2. Verify all ingredients have `name` field (not `display_name`)
3. Verify no ingredient names have consecutive spaces
4. Verify these slugs exist in ingredients: `olive_oil`, `canola_oil`, `lard`
5. Verify no products use `"jug"` as `package_unit`
6. Verify Costco maple syrup and honey use `"fl oz"` not `"oz"`
7. Count total ingredients and products and report

## Deliverables

1. Updated `test_data/import_v3.json` with all fixes applied
2. Updated `docs/design/import_export_specification.md` with expanded categories
3. Summary of changes made (counts)

## Out of Scope

- Adding recipes, events, or other entities to import file
- UI changes for large ingredient lists (separate feature)
- Validating density values for accuracy
