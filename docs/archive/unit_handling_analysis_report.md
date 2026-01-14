# Unit Handling Analysis Report

**Date:** 2025-12-16
**Analyst:** Claude Code
**Scope:** Bake-tracker codebase unit handling analysis

---

## 1. Summary

The codebase correctly distinguishes between weight ounce ("oz") and fluid ounce ("fl oz"), with "oz" mapping to weight (28.3495g) and "fl oz" to volume (29.5735ml). Units are stored as free-form strings with application-level validation, but **the import service does not validate units during import**, creating a significant gap where invalid or ambiguous units could enter the database. The sample data uses "oz" correctly in weight contexts only.

---

## 2. Unit Storage Model

### Schema Pattern

Units are stored as **free-form strings** (VARCHAR/String columns) with no database-level constraints:

| Model | Field | Column Type | Purpose |
|-------|-------|-------------|---------|
| `Product` | `package_unit` | String(50) | Unit for product packages (lb, oz, bag) |
| `Ingredient` | `density_volume_unit` | String(20) | Volume unit for density conversion |
| `Ingredient` | `density_weight_unit` | String(20) | Weight unit for density conversion |
| `RecipeIngredient` | `unit` | String(50) | Unit for recipe ingredient quantities |
| `Recipe` | `yield_unit` | String(50) | Unit for recipe yield (cookies, servings) |
| `FinishedUnit` | `item_unit` | String(50) | Unit name for discrete items |
| `ProductionConsumption` | `unit` | String(50) | Unit for consumption tracking |
| `AssemblyPackagingConsumption` | `unit` | String(50) | Unit for packaging consumption |

### No Database Constraints

- No ENUM or CHECK constraints on unit columns
- No foreign key to a units reference table
- Validation is purely at application layer

---

## 3. Unit Values Found

### Defined Constants (`src/utils/constants.py`)

| Category | Units | Type Mapping |
|----------|-------|--------------|
| **Weight** | oz, lb, g, kg | "weight" |
| **Volume** | tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal | "volume" |
| **Count** | each, count, piece, dozen | "count" |
| **Package** | bag, box, bar, bottle, can, jar, packet, container, package, case | "package" |

### Conversion Factors (`src/services/unit_converter.py`)

| Unit | Base Conversion |
|------|-----------------|
| **oz** | 28.3495 grams (weight) |
| **fl oz** | 29.5735 ml (volume) |
| lb | 453.592 grams |
| cup | 236.588 ml |
| tsp | 4.92892 ml |
| tbsp | 14.7868 ml |

### Sample Data Usage (`test_data/sample_data.json`)

| Field Context | Unit Values | Count |
|---------------|-------------|-------|
| `unit` (recipe ingredients) | cup | 22 |
| `unit` (recipe ingredients) | tsp | 13 |
| `package_unit` | lb | 9 |
| `package_unit` | oz | 4 |
| `density_weight_unit` | oz | 6 |
| `density_volume_unit` | cup | 6 |
| `yield_unit` | cookies, brownies, pieces, cups | 7 total |

---

## 4. Ambiguity Issues

### "oz" vs "fl oz" Handling

The codebase **correctly** distinguishes between weight and fluid ounces:

| File | Location | "oz" Meaning | Evidence |
|------|----------|--------------|----------|
| `constants.py:28` | WEIGHT_UNITS | Weight ounce | Listed in weight category |
| `constants.py:41` | VOLUME_UNITS | Fluid ounce | Listed as "fl oz" |
| `constants.py:75` | UNIT_TYPE_MAP | Weight | `"oz": "weight"` |
| `constants.py:85` | UNIT_TYPE_MAP | Volume | `"fl oz": "volume"` |
| `unit_converter.py:30` | WEIGHT_TO_GRAMS | Weight | `"oz": 28.3495` (grams) |
| `unit_converter.py:40` | VOLUME_TO_ML | Volume | `"fl oz": 29.5735` (ml) |

### Sample Data "oz" Context Analysis

All "oz" usages in sample_data.json are in **weight-appropriate contexts**:

| Line | Context | Field | Ingredient Type | Correct? |
|------|---------|-------|-----------------|----------|
| 14 | All-Purpose Flour | density_weight_unit | Dry/weight | ✅ Yes |
| 24 | White Sugar | density_weight_unit | Dry/weight | ✅ Yes |
| 34 | Brown Sugar | density_weight_unit | Dry/weight | ✅ Yes |
| 44 | Semi-Sweet Choc Chips | density_weight_unit | Solid/weight | ✅ Yes |
| 60 | Pecans | density_weight_unit | Dry/weight | ✅ Yes |
| 70 | Walnuts | density_weight_unit | Dry/weight | ✅ Yes |
| 140 | Nestle Toll House | package_unit | Chocolate chips | ✅ Yes |
| 179 | Penzeys Dutch Process | package_unit | Cocoa powder | ✅ Yes |
| 189 | McCormick | package_unit | Vanilla extract | ⚠️ Ambiguous |
| 207 | Morton | package_unit | Salt | ✅ Yes |

### Potential Ambiguity: Vanilla Extract (line 189)

```json
{
  "ingredient_slug": "vanilla_extract",
  "brand": "McCormick",
  "package_size": "16 oz bottle",
  "package_unit": "oz",
  "package_unit_quantity": 16.0
}
```

**Issue:** Vanilla extract is a liquid, typically measured in fluid ounces. Using "oz" here could cause:
- Incorrect density-based conversions
- User confusion about actual volume

**Should be:** `"package_unit": "fl oz"` for accuracy

### No Inconsistent Representations Found

- No "cups" vs "cup" inconsistencies
- No "ounce" vs "oz" inconsistencies
- No "c" abbreviation usage
- Units are consistently lowercase

---

## 5. Validation Gaps

### Validation Functions Exist But Are Underutilized

**`src/utils/validators.py`:**
- `validate_unit()` - validates against ALL_UNITS list ✅
- `validate_product_data()` - calls `validate_unit()` for `package_unit` ✅

**However, the import service does NOT use these validators:**

```python
# src/services/import_export_service.py:2293-2303
product = Product(
    ingredient_id=ingredient.id,
    brand=brand,
    package_unit=prod_data.get("package_unit"),  # NO VALIDATION!
    package_unit_quantity=prod_data.get("package_unit_quantity"),
    ...
)
```

### Import Validation Status

| Entity | Unit Field | Validation on Import |
|--------|------------|---------------------|
| Products | `package_unit` | ❌ None |
| Recipes | `yield_unit` | ❌ None |
| Recipe Ingredients | `unit` | ❌ None |
| Ingredients | `density_*_unit` | ❌ None |

### What Happens with Invalid Units?

1. **Import:** Invalid units are accepted without error
2. **Runtime:** Unit converter returns `("unknown", 0.0, "error message")` for invalid units
3. **Conversions:** Fail silently or return zero
4. **Cost calculations:** May produce incorrect results

---

## 6. Recommendations

### Priority 1: Critical (Import Validation)

1. **Add unit validation to import service**
   - Validate `package_unit` against ALL_UNITS before creating Product records
   - Validate `unit` in recipe ingredients
   - Validate density units (`density_volume_unit`, `density_weight_unit`)
   - Return clear error messages for invalid units

2. **Fix vanilla extract sample data**
   - Change `"package_unit": "oz"` to `"package_unit": "fl oz"` in sample_data.json line 189
   - Review other liquid ingredients for correct unit usage

### Priority 2: High (Ambiguity Prevention)

3. **Add "oz" context warnings in UI**
   - When user enters "oz" for liquid-category ingredients, prompt: "Did you mean 'fl oz' (fluid ounce)?"
   - Consider ingredient category to suggest appropriate unit type

4. **Document unit conventions**
   - Add to user documentation: "oz" = weight ounce, "fl oz" = fluid ounce
   - Update import specification with unit disambiguation guidance

### Priority 3: Medium (Future-Proofing)

5. **Consider UN/CEFACT code adoption**
   - Per `docs/design/unit_codes_reference.md`, consider migration to 3-letter codes
   - ONZ (weight ounce) vs OZA (fluid ounce) removes all ambiguity
   - Add alias mapping layer to accept both old and new formats

6. **Add units reference table (optional)**
   - Create database table with valid units
   - Would enable: database-level constraints, unit metadata, localized display names
   - Migration complexity may not be justified for single-user desktop app

### Priority 4: Low (Cleanup)

7. **Normalize existing unit representations**
   - Audit database for any non-standard unit values
   - Create migration script to normalize if needed

---

## Appendix A: File References

| File | Relevant Lines | Content |
|------|----------------|---------|
| `src/utils/constants.py` | 27-105 | Unit lists and type mappings |
| `src/services/unit_converter.py` | 27-53 | Conversion tables |
| `src/utils/validators.py` | 141-158, 428-431 | Unit validation functions |
| `src/services/import_export_service.py` | 2293-2307 | Product import (no validation) |
| `test_data/sample_data.json` | 14, 189 | Example oz usage |
| `docs/design/unit_codes_reference.md` | - | Target UN/CEFACT standard |

---

## Appendix B: Complete Unit Inventory

### All Valid Units (from constants.py)

```
Weight:  oz, lb, g, kg
Volume:  tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal
Count:   each, count, piece, dozen
Package: bag, box, bar, bottle, can, jar, packet, container, package, case
```

### Type Detection Logic

```python
# From unit_converter.py
def get_unit_type(unit: str) -> str:
    if unit.lower() in WEIGHT_TO_GRAMS:  # oz, lb, g, kg
        return "weight"
    elif unit.lower() in VOLUME_TO_ML:   # tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal
        return "volume"
    elif unit.lower() in COUNT_TO_ITEMS: # each, count, piece, dozen
        return "count"
    return "unknown"
```

---

**Report Status:** Complete
**Next Action:** Review recommendations with project owner
