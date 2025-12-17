# Claude Code Prompt: UI Improvements - Ingredients and Products Listings

## Context

Refer to `.kittify/memory/constitution.md` for project principles.

User testing revealed significant usability issues with the Ingredients and Products listing views. These need immediate attention to make the app functional for testing with a large catalog (~60+ ingredients, 20+ products).

## Part A: Ingredients Listing Fixes

**Location:** Ingredients tab/view in main UI

### Current Problems

1. **Only shows ~4 items at a time** — Display density far too low for hundreds of items
2. **Scroll bar moves content in large jumps** — Not granular enough for navigation
3. **Category shown inline with name** — Wastes space, not useful
4. **Random order** — No apparent sort order
5. **No search/filter capability** — Can't find specific ingredients

### Required Fixes

#### A.1: Increase Display Density
- Show significantly more items in view (target: 15-20+ visible rows)
- Reduce row height / padding
- Use compact font size appropriate for data tables

#### A.2: Fix Scroll Behavior
- Scroll should move content smoothly, line by line
- Not in large page-sized jumps
- Standard scrollbar behavior expected

#### A.3: Reorganize Columns
Current (assumed): Name with category inline
Proposed columns:
| Category | Name | Density (if set) | Notes |
Or simpler:
| Category | Name |

- Remove inline category from name
- Category as its own sortable column
- Consider making density optional/collapsible

#### A.4: Default Sort Order
- Sort alphabetically by Name (ascending) as default
- Or sort by Category, then Name within category

#### A.5: Search/Sort/Filter Controls
Add toolbar or header controls:
- **Search box** — Filter by name (type-ahead, case-insensitive)
- **Category dropdown** — Filter to show only selected category (or "All")
- **Column header sorting** — Click column header to sort asc/desc

### Mockup
```
+----------------------------------------------------------+
| Search: [___________] | Category: [All Categories ▼]     |
+----------------------------------------------------------+
| Category          | Name                    | Density    |
+----------------------------------------------------------+
| Chocolate & Cocoa | Chocolate chips, Milk   | 1 cup=6oz  |
| Chocolate & Cocoa | Chocolate chips, Semi   | 1 cup=6oz  |
| Chocolate & Cocoa | Cocoa powder, Dutch     | 1 cup=3.8oz|
| Dairy & Eggs      | Butter, Salted          | 1 cup=8oz  |
| Dairy & Eggs      | Butter, Unsalted        | 1 cup=8oz  |
| Dairy & Eggs      | Cream, Heavy            | 1 cup=8.4oz|
| ... (15+ more visible rows)                              |
+----------------------------------------------------------+
```

---

## Part B: Products Listing Fixes

**Location:** Products tab/view (likely showing inventory/products)

### Current Problems

1. **Scroll bar doesn't move contents** — Broken scrolling
2. **Location column not needed** — Remove or hide
3. **No search/filter capability** — Can't find specific products
4. **"Consume Ingredient" button mislabeled** — Should reference Products, not Ingredients
5. **Product name shows brand + package size concatenated** — Confusing
6. **"Quantity" column unclear** — Doesn't convey remaining inventory well

### Required Fixes

#### B.1: Fix Scroll Behavior
- Scrollbar must actually scroll the content
- Debug why scrolling is broken

#### B.2: Remove Location Column
- Remove or hide the Location column (not useful for this view)

#### B.3: Search/Sort/Filter Controls
Same pattern as Ingredients:
- **Search box** — Filter by ingredient name or brand
- **Category dropdown** — Filter by ingredient category
- **Column header sorting**

#### B.4: Fix Button Label
- Change "Consume Ingredient" → "Consume Product" or "Record Usage"

#### B.5: Reorganize Columns
Current (problematic): Product Name (brand + package concatenated), Quantity, Location

Proposed columns:
| Ingredient | Brand | Package | Remaining |

Where:
- **Ingredient** — The ingredient's display name (e.g., "All-Purpose Wheat Flour")
- **Brand** — Brand name (e.g., "King Arthur")
- **Package** — `package_unit_quantity` + `package_unit` (e.g., "25 lb")
- **Remaining** — See B.6 below

#### B.6: Improve Quantity Display
The "Quantity" concept is confusing. User needs to understand:
- How many whole/partial packages remain
- Total quantity in base units

**Proposed "Remaining" column format:**
```
2.5 pkg (62.5 lb)
```
Or with more detail:
```
2 full + 0.5 partial = 62.5 lb
```

**Simpler alternative:**
Show two sub-columns:
| Packages | Total Qty |
| 2.5      | 62.5 lb   |

**Implementation note:** 
- Packages = `SUM(inventory_item.quantity)` where quantity is in package units
- Total Qty = Packages × `product.package_unit_quantity` in `product.package_unit`

### Mockup
```
+------------------------------------------------------------------+
| Search: [___________] | Category: [All Categories ▼]             |
+------------------------------------------------------------------+
| Ingredient              | Brand        | Package | Remaining     |
+------------------------------------------------------------------+
| All-Purpose Wheat Flour | King Arthur  | 25 lb   | 2.5 pkg (62.5 lb) |
| Butter, Unsalted        | Costco       | 1 lb    | 4 pkg (4 lb)  |
| Chocolate chips, Semi   | Nestle       | 12 oz   | 3 pkg (36 oz) |
| Sugar, Granulated       | Domino       | 25 lb   | 1.2 pkg (30 lb) |
| ...                                                               |
+------------------------------------------------------------------+
| [Add Product] [Record Usage] [Edit] [Delete]                     |
+------------------------------------------------------------------+
```

---

## Files to Investigate

- `src/ui/tabs/ingredients_tab.py` or similar
- `src/ui/tabs/products_tab.py` or `inventory_tab.py`
- Look for Treeview/Listbox widgets and their configuration
- Check scroll binding and row height settings

## Testing

### Part A (Ingredients)
1. Load app with 60+ ingredients
2. Verify 15+ rows visible without scrolling
3. Verify smooth line-by-line scrolling
4. Verify search filters list as you type
5. Verify category dropdown filters correctly
6. Verify column header click sorts

### Part B (Products)
1. Verify scrolling works
2. Verify Location column removed
3. Verify columns show: Ingredient, Brand, Package, Remaining
4. Verify "Remaining" shows packages + total (e.g., "2.5 pkg (62.5 lb)")
5. Verify button says "Record Usage" not "Consume Ingredient"
6. Verify search/filter works

## Deliverables

1. Improved Ingredients listing with dense display, working scroll, search/sort/filter
2. Improved Products listing with fixed scroll, correct columns, clear quantity display
3. All existing tests pass

## Priority

HIGH — These views are currently unusable for testing with realistic data volumes.
