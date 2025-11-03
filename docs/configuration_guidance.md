# Seasonal Baking Tracker - Configuration & Design Guidance

## Purpose
This document provides real-world data extracted from the user's existing baking inventory spreadsheet to inform the design and default configuration of the Seasonal Baking Tracker application.

---

## Ingredient Categories (from actual usage)

Based on analysis of the user's multi-year baking inventory spreadsheet, the following ingredient categories are actively used:

### Primary Categories (High-Level Organization)
1. **Oils/Butters** - Various fats used in baking
2. **Nuts** - All nut types and preparations
3. **Spices** - Spices and flavorings (some sourced from Penzys)
4. **Chocolate/Candies** - Chocolate chips, bars, callets, and candy pieces

### Secondary Categories (Subcategories within columns)
5. **Flour** - All flour types and blends
6. **Sugar** - All sugar types and sweeteners
7. **Dried Fruits** - Raisins, currants, cherries, cranberries, freeze-dried fruits
8. **Extracts** - Vanilla, almond, peppermint, etc.
9. **Syrups** - Corn syrup, maple syrup, molasses, golden syrup
10. **Cocoa Powders** - Various cocoa powder brands and types
11. **Alcohol** - Baking spirits and liqueurs
12. **Misc** - Miscellaneous baking supplies (baking spray, gelatin, yeast, condensed milk, etc.)

### Design Implications
- **Default Categories**: The application should come pre-configured with these 12 categories
- **Category Management**: Users must be able to add, rename, or delete categories
- **Category Assignment**: Each ingredient must be assigned to exactly one category
- **Filtering**: Inventory and shopping list views should filter by category
- **Sorting**: Within categories, ingredients should be sortable alphabetically or by quantity

---

## Finished Goods Categories (from actual usage)

Based on the "Items List" tab, the user organizes finished baked goods into these categories:

### Finished Goods Categories
1. **Cookies** - All cookie varieties
2. **Cakes** - All cake varieties (including mini cakes)
3. **Candies** - Confections like truffles, fudge, bark

### Actual Finished Goods Examples

**Cookies (15 varieties tracked):**
- Jumbles
- Almond Biscotti
- Hazelnut Biscotti
- Magic Bars
- Mocha-Toffee Truffles (note: categorized as cookie, not candy)
- Snickerdoodle Sables
- Anzac
- Holiday Blossoms
- Gingerbread Chai
- Cookie Butter Snickerdoodles
- Nutella Snowballs
- Hamantaschen (3 varieties: Fig filling, Poppy filling, Frangipane & Cardamom)

**Cakes (8 varieties tracked):**
- Eggnog
- Sour Cream Chocolate
- Orange Poppy
- Fruitcake
- Pear Honey Rosemary
- Pumpkin Butterscotch
- Lemon Lavender
- Roasted Strawberry

**Candies (3 varieties tracked):**
- Truffles
- Fudge
- Peppermint Bark

### Design Implications
- **Default Categories**: Pre-configure with Cookies, Cakes, and Candies
- **Category Management**: Allow users to add custom categories (e.g., "Breads", "Bars")
- **Recipe Source Tracking**: Many items reference "SG-Binder" as source - ensure recipe source field is prominent
- **Multi-Year Tracking**: User tracks recipes across years (note "2024 - BFS Nov-Dec" source)

---

## Observed Data Patterns & Requirements

### Ingredient Tracking Patterns
Based on the 2025 spreadsheet tab, ingredients are tracked with:

1. **Brand Specificity**: Many ingredients include brand names
   - Examples: "Costco Almonds", "Penzys Dutch Processed Cocoa", "Callebaut Callets"
   - **Design Impact**: Brand field should be prominent and searchable

2. **Multiple Units Simultaneously**:
   - **Purchase Unit Examples**: Bag, Box, Bar, Bottle, Can, Jar, Packet
   - **Weight/Volume Examples**: lb, oz, g, kg, cup, tsp, tbsp, ml, l
   - **Observation**: Same ingredient shows both (e.g., "1 Bag, 25 lb" for flour)
   - **Design Impact**: Confirm support for showing both purchase unit count AND equivalent weight/volume

3. **Partial Quantities**:
   - Examples from spreadsheet: "0.5 Bag", "0.75 Bag", "1.25 Bags", "0.5 Bottle"
   - **Design Impact**: Decimal inputs required, not just integers

4. **Large Package Sizes**:
   - Flour: 25 lb bags
   - Sugar: 25 lb bags
   - Chocolate callets: 22 lb bags, 6.6 lb bags
   - **Design Impact**: Need to handle large conversion factors

5. **Multi-Year Inventory**:
   - Spreadsheet has tabs for 2021, 2022, 2023, 2024, 2025
   - **Design Impact**: Confirm year-over-year comparison features are priority

### Specific Ingredient Examples (for testing/demo data)

**Flour Category:**
- All Purpose (25 lb bag)
- Bread (5 lb bag)
- Cake (box)
- Almond Flour (2 lb bag)
- Pastry Flour (5 lb bag)
- Coconut Flour (5 lb bag)

**Sugar Category:**
- White Sugar (25 lb bag)
- Light Brown Sugar (2 lb bag)
- Dark Brown Sugar (2 lb bag)
- Confectioner's Sugar (7 lb bag)
- Turbinado Raw Sugar (24 oz bag)

**Chocolate/Candies Category:**
- Callebaut Callets (22 lb bag)
- Nestle Semi Sweet Chips (72 oz bag)
- Hershey's Special Dark Chips (12 oz bag)
- Guittard Milk Chocolate Disks (12 oz bag)

---

## Configuration Recommendations for Implementation

### Phase 1 - Database Seeding
When initializing the database, pre-populate with:

1. **Ingredient Categories** (12 default categories listed above)
2. **Finished Goods Categories** (3 default: Cookies, Cakes, Candies)
3. **Unit Types** (both purchase and recipe units):
   - Weight: oz, lb, g, kg
   - Volume: tsp, tbsp, cup, ml, l
   - Count: bag, box, bar, bottle, can, jar, packet, each
4. **Standard Conversion Factors** (for common conversions):
   - 1 lb = 16 oz
   - 1 kg = 1000 g
   - 1 cup = 16 tbsp
   - 1 tbsp = 3 tsp
   - etc.

### Phase 2 - UI Defaults
1. **Category Dropdowns**: Show all 12 ingredient categories by default
2. **Finished Goods Dropdowns**: Show 3 default categories
3. **Unit Dropdowns**: Organize by type (weight, volume, count) for clarity
4. **Forms**: Make brand field visible and easy to fill

### Phase 3 - Sample/Test Data
Consider including a few sample ingredients for testing:
- 1 from each category
- Mix of purchase unit types
- Various conversion scenarios

---

## User Workflow Observations

Based on the spreadsheet structure, the user's workflow appears to be:

1. **Annual Inventory Review**: Review previous year's ending inventory
2. **Quantity Updates**: Update quantities for consumed/purchased items
3. **Planning**: Reference "Items List" to decide what to make
4. **Multi-Column Layout**: User comfortable with 4-column repeating structure (Category, Amount, Pkg, Weight)

### UI Design Guidance
- **Table Views**: User is accustomed to tabular data with repeating column patterns
- **Compact Information**: Comfortable seeing many items on screen at once
- **Category Grouping**: Natural to group items by category in display
- **Quick Scanning**: Needs to scan inventory quickly - consider visual grouping

---

## Questions for Developer (Claude Code)

1. **Category Management UI**: Should category CRUD be in settings/admin area or main navigation?

2. **Default Data**: Should we include the 12 ingredient categories and 3 finished goods categories as migration/seed data, or allow user to create from scratch?

3. **Unit Conversion Helper**: Should we build an interactive calculator for users to determine conversion factors (e.g., "I have a 50 lb bag, how many cups is that?")?

4. **Brand Field**: Should brand be:
   - Optional text field on ingredient form?
   - Separate dropdown with auto-complete?
   - Part of ingredient name?

5. **Multi-Year View**: Priority for seeing historical inventory across years? Or focus on current year first?

---

## Summary for Implementation

**Critical Design Elements:**
1. ✅ Support 12 ingredient categories (extensible)
2. ✅ Support 3 finished goods categories (extensible)
3. ✅ Brand field for ingredients
4. ✅ Decimal quantity support (0.5, 0.75, 1.25, etc.)
5. ✅ Purchase unit + recipe unit display
6. ✅ Large package size support (up to 100+ lbs)
7. ✅ Category-based filtering and organization

**User Experience Priorities:**
1. Fast inventory updates (minimal clicks)
2. Clear category organization
3. Easy searching (by name, brand, category)
4. Quick visual scanning of inventory levels
5. Multi-year comparison capability

This configuration data should guide the implementation of constants, default values, and UI organization throughout the application.