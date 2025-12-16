# Unit Codes Reference for Bake Tracker

**Standard:** UN/CEFACT Recommendation 20 (UNECE Rec 20)
**Source:** https://unece.org/trade/uncefact/cl-recommendations
**Purpose:** Standardized unit codes for food inventory, recipes, and purchasing

---

## Mass (Weight) Units

| Code | Name | Symbol | Notes |
|------|------|--------|-------|
| KGM | kilogram | kg | SI base unit for mass |
| GRM | gram | g | 1/1000 kilogram |
| MGM | milligram | mg | 1/1000 gram |
| LBR | pound | lb | 453.59237 grams (avoirdupois) |
| ONZ | ounce (avoirdupois) | oz | **Weight ounce** - 28.349523 grams |

---

## Volume (Liquid) Units

| Code | Name | Symbol | Notes |
|------|------|--------|-------|
| LTR | litre | L, l | SI accepted unit |
| MLT | millilitre | mL, ml | 1/1000 litre |
| OZA | fluid ounce (US) | fl oz | **Liquid ounce** - 29.5735 mL |
| GLL | gallon (US) | gal | 3.785411784 litres |
| QT | quart (US liquid) | qt | 0.946352946 litres |
| PTL | pint (US liquid) | pt | 0.473176473 litres |
| G94 | cup (US) | cup | 236.588 mL (8 fl oz) |
| G24 | tablespoon (US) | tbsp | 14.7868 mL |
| G25 | teaspoon (US) | tsp | 4.92892 mL |

---

## Count/Piece Units

| Code | Name | Symbol | Notes |
|------|------|--------|-------|
| C62 | one | - | Dimensionless count (generic "each") |
| H87 | piece | pc | Individual item |
| DZN | dozen | doz | 12 units |
| EA | each | ea | Commonly used alias for C62 |

---

## Package Units (for purchasing)

| Code | Name | Symbol | Notes |
|------|------|--------|-------|
| BG | bag | bag | Flexible container |
| BX | box | box | Rigid rectangular container |
| CA | can | can | Cylindrical metal container |
| JR | jar | jar | Glass/plastic container with lid |
| BT | bottle | btl | Narrow-necked container |
| CT | carton | ctn | Paperboard container |
| PK | package | pkg | Generic package |
| CS | case | case | Shipping container (multiple units) |
| TB | tube | tube | Cylindrical squeezable container |
| TN | tin | tin | Metal container |

---

## Key Disambiguation: oz vs fl oz

**CRITICAL:** The standard resolves the common "oz" ambiguity:

| Common Usage | Correct Code | Full Name | Measurement Type |
|--------------|--------------|-----------|------------------|
| "oz" (weight) | **ONZ** | ounce (avoirdupois) | Mass |
| "oz" (liquid) | **OZA** | fluid ounce (US) | Volume |
| "fl oz" | **OZA** | fluid ounce (US) | Volume |

**Rule:** In bake tracker, always use the 3-character code to eliminate ambiguity.

---

## Implementation Recommendations

### Database Schema

```python
# In unit-related models
class UnitCode:
    code: str        # UN/CEFACT code (e.g., "GRM", "ONZ", "OZA")
    name: str        # Full name (e.g., "gram", "ounce (avoirdupois)")
    symbol: str      # Display symbol (e.g., "g", "oz", "fl oz")
    category: str    # "mass", "volume", "count", "package"
```

### Import File Format

Per import_export_specification.md v3.4:

```json
{
  "products": [
    {
      "ingredient_slug": "all_purpose_flour",
      "brand": "King Arthur",
      "package_unit": "LBR",
      "package_unit_quantity": 25.0
    }
  ]
}
```

### UI Display Mapping

For user-friendly display, map codes to familiar symbols:

| Code | Display (US) | Display (Metric) |
|------|--------------|------------------|
| GRM | g | g |
| KGM | kg | kg |
| LBR | lb | lb |
| ONZ | oz | oz |
| OZA | fl oz | fl oz |
| G94 | cup | cup |
| G24 | tbsp | tbsp |
| G25 | tsp | tsp |
| MLT | mL | mL |
| LTR | L | L |

### Alias Support for Import

Accept common aliases and normalize to standard codes:

```python
UNIT_ALIASES = {
    # Mass
    "g": "GRM", "gram": "GRM", "grams": "GRM",
    "kg": "KGM", "kilogram": "KGM", "kilograms": "KGM",
    "lb": "LBR", "lbs": "LBR", "pound": "LBR", "pounds": "LBR",
    "oz": "ONZ", "ounce": "ONZ", "ounces": "ONZ",  # Default to weight
    
    # Volume
    "ml": "MLT", "milliliter": "MLT", "millilitre": "MLT",
    "l": "LTR", "liter": "LTR", "litre": "LTR",
    "fl oz": "OZA", "floz": "OZA", "fluid ounce": "OZA",
    "cup": "G94", "cups": "G94", "c": "G94",
    "tbsp": "G24", "tablespoon": "G24", "tablespoons": "G24", "T": "G24",
    "tsp": "G25", "teaspoon": "G25", "teaspoons": "G25", "t": "G25",
    "qt": "QT", "quart": "QT", "quarts": "QT",
    "pt": "PTL", "pint": "PTL", "pints": "PTL",
    "gal": "GLL", "gallon": "GLL", "gallons": "GLL",
    
    # Count
    "each": "EA", "ea": "EA", "piece": "H87", "pc": "H87",
    "dozen": "DZN", "doz": "DZN",
    
    # Package
    "bag": "BG", "box": "BX", "can": "CA", "jar": "JR",
    "bottle": "BT", "carton": "CT", "case": "CS",
}
```

---

## Conversion Factors (Built-in)

Standard conversions that don't require ingredient-specific density:

### Mass Conversions
| From | To | Factor |
|------|-----|--------|
| KGM | GRM | 1000 |
| LBR | GRM | 453.59237 |
| ONZ | GRM | 28.349523 |
| LBR | ONZ | 16 |

### Volume Conversions
| From | To | Factor |
|------|-----|--------|
| LTR | MLT | 1000 |
| GLL | LTR | 3.785411784 |
| QT | MLT | 946.352946 |
| PTL | MLT | 473.176473 |
| G94 | MLT | 236.588 |
| OZA | MLT | 29.5735 |
| G24 | MLT | 14.7868 |
| G25 | MLT | 4.92892 |
| G94 | G24 | 16 |
| G24 | G25 | 3 |

---

## Notes

1. **US vs Imperial:** This reference uses US customary units. UK imperial units differ (e.g., UK pint = 568.261 mL vs US pint = 473.176 mL). UN/CEFACT has separate codes for UK units if needed.

2. **Metric Preference:** For new data entry, prefer metric units (GRM, MLT, LTR) as they're unambiguous and internationally consistent.

3. **Package vs Content:** Distinguish between:
   - `purchase_unit`: How item is bought (BG = bag, BX = box)
   - `purchase_quantity`: Amount per package in base units
   - `recipe_unit`: How ingredient is measured in recipes (G94 = cup)

4. **Validation:** Import should validate that unit codes exist in the reference table before accepting data.

---

**Document Version:** 1.0
**Created:** 2025-12-16
**Standard Reference:** UN/CEFACT Recommendation 20, Revision 17 (2021)
