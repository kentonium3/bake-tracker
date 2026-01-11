# F048: Materials UI Rebuild - Match Ingredients Exactly

**Version**: 1.0
**Priority**: HIGH  
**Effort**: 4-6 hours
**Type**: UI Rebuild

---

## Executive Summary

Current Materials UI violates F047's "parallel ingredients exactly" principle:
- ❌ Single Materials tab (should be 3 tabs like Ingredients/Products/Pantry)
- ❌ Collapsible tree view (should be grid listing)
- ❌ Mixed listings (should be separate views)

This spec rebuilds Materials UI to exactly match Ingredients UI structure.

---

## Problem Statement

**Current State (WRONG):**
```
Materials Tab (Single)
├─ Left Panel: Hierarchy Tree (collapsible)
├─ Right Panel: Products List
└─ Bottom: Units Section
```

**Target State (CORRECT - matches ingredients):**
```
Materials Tab
├─ Search/Filter Bar (L0/L1 cascading dropdowns)
├─ Grid listing (flat view with columns)
├─ Tree/Flat toggle
└─ Action buttons

Material Products Tab (NEW)
├─ Search/Filter by Material
├─ Grid listing (products)
└─ Action buttons
```

---

## CRITICAL: Study These Files FIRST

**Before writing ANY code, spec-kitty MUST read and understand:**

1. **src/ui/ingredients_tab.py** - Complete reference implementation
   - Tab structure and layout
   - Search/filter patterns
   - Grid vs Tree view toggle
   - Cascading L0/L1 dropdowns
   - Button placement and state management
   - Tree widget configuration

2. **src/ui/products_tab.py** (if exists) - Product listing patterns
   - How products are listed
   - Filter by ingredient pattern
   - CRUD operations

3. **Current src/ui/materials_tab.py** - What needs to be replaced
   - Understand current services used
   - Preserve business logic
   - Replace ONLY the UI structure

**DO NOT START IMPLEMENTATION WITHOUT READING THESE FILES**

---

## Architecture Requirements

### Pattern Matching Rules

Materials UI **MUST** match Ingredients UI in these exact aspects:

1. **Tab Structure**: Same 3-tab pattern
2. **Widget Types**: Same CustomTkinter widgets
3. **Layout Grid**: Same grid configuration
4. **Filter Bar**: Same search + cascading dropdowns
5. **View Toggle**: Same Flat/Tree segmented button
6. **Action Buttons**: Same button layout and states
7. **Tree Columns**: Same column structure (L0, L1, Name, Density → equivalent)
8. **Status Bar**: Same status bar pattern
9. **Selection Handling**: Same selection callbacks
10. **Form Dialogs**: Same dialog structure

### Services to Use

Materials tab must use these services (parallel to ingredient services):
- `material_catalog_service` (matches `ingredient_service`)
- `material_product_service` (matches `product_service`)
- `material_unit_service` (matches unit-related services)
- `supplier_service` (shared)

---

## Detailed UI Specifications

### Tab 1: Materials Catalog Tab

**Purpose**: Manage material definitions (parallel to Ingredients tab)

**Layout Pattern**: EXACTLY match ingredients_tab.py structure

```
┌─ MATERIALS ────────────────────────────────────────────────────────────┐
│                                              [+ Add Material ▼]        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ Search: [____________]  Category: [All ▼]  Subcategory: [All ▼]       │
│         Level: [All Levels ▼]  [Flat|Tree]  [Clear]                   │
│                                                                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ [+ Add Material]  [✏️ Edit]  (disabled until selection)                │
│                                                                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ Category (L0)  │ Subcategory (L1) │ Material Name │ Default Unit      │
│────────────────┼──────────────────┼───────────────┼──────────────────│
│ Boxes          │ Window Boxes     │ 10x10 Cake    │ each             │
│ Bags           │ Transparent      │ Cello Medium  │ each             │
│ Ribbon         │ Curling          │ 3/16" Width   │ linear_inches    │
│                                                                         │
│ (Grid with sortable columns, scrollable, 600px+ height)               │
│                                                                         │
├────────────────────────────────────────────────────────────────────────┤
│ Status: 23 materials loaded                                            │
└────────────────────────────────────────────────────────────────────────┘
```

**Key Implementation Details:**

1. **Search/Filter Bar** (row 1):
   - Search entry: 200px wide, "Search materials..."
   - Category dropdown: L0 filter, 150px, cascades to Subcategory
   - Subcategory dropdown: L1 filter, 150px, disabled until L0 selected
   - Level filter: 160px, "All Levels / Root Categories (L0) / Subcategories (L1) / Leaf Materials (L2)"
   - View toggle: CTkSegmentedButton, ["Flat", "Tree"], 100px
   - Clear button: 60px, resets all filters

2. **Action Buttons** (row 2):
   - "+ Add Material": 150px wide, 36px height, always enabled
   - "✏️ Edit": 120px wide, 36px height, disabled until selection
   - Button frame: transparent background
   - Spacing: 10px (PADDING_MEDIUM) between buttons

3. **Materials Grid** (row 3):
   - ttk.Treeview with columns: ("l0", "l1", "name", "default_unit")
   - Column widths: l0=150, l1=150, name=200, default_unit=100
   - Sortable headers (click to sort)
   - Single selection mode
   - Double-click opens edit dialog
   - Shows hierarchy path in L0/L1 columns based on level

4. **Status Bar** (row 4):
   - Left-aligned label
   - 30px height
   - Shows count and filter status

**Grid Configuration:**
```python
self.grid_columnconfigure(0, weight=1)
self.grid_rowconfigure(0, weight=0)  # Title
self.grid_rowconfigure(1, weight=0)  # Search/filter
self.grid_rowconfigure(2, weight=0)  # Action buttons
self.grid_rowconfigure(3, weight=1)  # Materials grid
self.grid_rowconfigure(4, weight=0)  # Status bar
```

**Tree View Mode** (when toggle = "Tree"):
- Hide grid container
- Show MaterialTreeWidget (parallel to IngredientTreeWidget)
- Allow hierarchy navigation
- Disable level filter when in tree mode

### Tab 2: Material Products Tab (NEW)

**Purpose**: Manage purchasable material products (parallel to Products tab)

**Layout Pattern**: Match products_tab.py if it exists, otherwise create parallel to ingredients tab

```
┌─ MATERIAL PRODUCTS ────────────────────────────────────────────────────┐
│                                         [+ Add Material Product ▼]     │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ Search: [____________]  Material: [All Materials ▼]  [Clear]          │
│                                                                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ [+ Add Product]  [✏️ Edit]  [Record Purchase]  [Adjust Inventory]     │
│                                                                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ Material        │ Product Name           │ Inventory │ Unit Cost │ Supplier │
│─────────────────┼───────────────────────┼───────────┼──────────┼──────────│
│ Ribbon 3/16"    │ Amazon Assorted 120m   │ 4,724"   │ $0.0016  │ Amazon   │
│ Box 10x10       │ Webstaurant 100pk      │ 85 ea    │ $1.23    │ Webst... │
│ Bag Cello Med   │ Wishes for Santa 100ct │ 100 ea   │ $0.18    │ PaperM...│
│                                                                         │
│ (Grid with sortable columns, scrollable)                              │
│                                                                         │
├────────────────────────────────────────────────────────────────────────┤
│ Status: 26 material products loaded                                    │
└────────────────────────────────────────────────────────────────────────┘
```

**Key Implementation Details:**

1. **Filter Bar**:
   - Search entry: 200px
   - Material filter: dropdown of all materials, 200px
   - Clear button: 60px

2. **Action Buttons**:
   - "+ Add Product": always enabled (opens material product form)
   - "✏️ Edit": disabled until selection
   - "Record Purchase": disabled until selection
   - "Adjust Inventory": disabled until selection

3. **Products Grid**:
   - Columns: ("material_name", "product_name", "inventory", "unit_cost", "supplier")
   - Sortable headers
   - Format inventory with units (e.g., "4,724 inches", "100 each")
   - Format cost as currency

4. **Grid Configuration**:
   - Same as Materials tab

### Dialog: Material Form

**Purpose**: Add/Edit material (parallel to IngredientFormDialog)

```
┌─ Add Material ──────────────────────────────────────────┐
│                                                          │
│ Name*:  [Box Window Cake 10x10_____________________]   │
│                                                          │
│ Parent Material (determines level):                     │
│                                                          │
│ Root Category (L0):  [Boxes               ▼]           │
│ Subcategory (L1):    [Window Boxes        ▼]           │
│                                                          │
│ Level: L2 (Leaf Material)                  (computed)   │
│                                                          │
│ Default Unit*:  [each                      ▼]          │
│                 (dropdown: each, linear_inches, ...)    │
│                                                          │
│ Notes: [_______________________________________________] │
│                                                          │
│ Grid: 2 columns (label: 120px, input: flexible)        │
│ Padding: 15px all sides, 8px between rows              │
│                                                          │
│ [Delete]                        [Cancel] [Save]         │
└──────────────────────────────────────────────────────────┘
```

**Key Details**:
- Name field: Required, 200px+ width
- Cascading L0/L1 dropdowns (match ingredient form exactly)
- Level display: Computed from parent selection (read-only label)
- Default unit: Dropdown with material-appropriate units
- Delete button: Left side, only when editing
- Cancel/Save: Right side

### Dialog: Material Product Form

**Purpose**: Add/Edit material product

```
┌─ Add Material Product ──────────────────────────────────┐
│                                                          │
│ Material*:  [Box Window Cake 10x10        ▼]           │
│                                                          │
│ Product Name*: [Amazon 10x10 Box 25pk________________]  │
│                                                          │
│ Package Details:                                         │
│   Quantity per package: [25____]  [each    ▼]          │
│                                                          │
│ Supplier: [Amazon                          ▼]           │
│ SKU:      [B07XYZ123_________________________]          │
│                                                          │
│ Notes: [____________________________________________]    │
│                                                          │
│ [Delete]                        [Cancel] [Save]         │
└──────────────────────────────────────────────────────────┘
```

### Dialog: Record Material Purchase

```
┌─ Record Material Purchase ──────────────────────────────┐
│                                                          │
│ Material Product*: [Amazon 10x10 Box 25pk  ▼]          │
│                                                          │
│ Package Details:                                         │
│   Units per package:  [25____] each                     │
│   Packages purchased: [4_____]                          │
│   Total units:        100 each          (calculated)    │
│                                                          │
│ Cost:                                                    │
│   Total cost:    $[123.45____]                          │
│   Unit cost:     $1.23              (calculated)        │
│                                                          │
│ Purchase date: [2026-01-11_]  [📅]                      │
│ Notes: [____________________________________________]    │
│                                                          │
│ Validation: Real-time, show errors below fields         │
│ Calculate totals on blur/change events                  │
│                                                          │
│                             [Cancel] [Record Purchase]   │
└──────────────────────────────────────────────────────────┘
```

**Validation**:
- Disable submit until all required fields valid
- Show error labels below invalid fields (red, size 10)
- Calculate unit cost automatically
- Calculate total units automatically

---

## Implementation Guidelines

### Phase 1: Tab Structure (2 hours)

1. **Study reference files** (30 min):
   - Read ingredients_tab.py completely
   - Note all widget types and configurations
   - Understand grid layout patterns
   - Study filter/search implementation

2. **Create materials_tab.py skeleton** (30 min):
   - Copy overall structure from ingredients_tab
   - Rename classes (MaterialsTab)
   - Update service imports
   - Set up grid configuration

3. **Create material_products_tab.py** (1 hour):
   - If products_tab.py exists, copy structure
   - Otherwise, adapt from ingredients_tab
   - Configure for material products

### Phase 2: Materials Tab Implementation (2 hours)

1. **Search/Filter Bar** (30 min):
   - Copy from ingredients_tab
   - Update labels ("materials" not "ingredients")
   - Wire to material services

2. **Materials Grid** (45 min):
   - Copy grid setup from ingredients_tab
   - Update columns for materials
   - Implement sorting

3. **Tree View** (45 min):
   - Create or adapt MaterialTreeWidget
   - Implement view toggle
   - Match ingredient tree behavior

### Phase 3: Material Products Tab (1.5 hours)

1. **Products Listing** (45 min):
   - Grid with material filter
   - Action buttons
   - Selection handling

2. **Product Forms** (45 min):
   - Material product form dialog
   - Purchase recording dialog
   - Inventory adjustment dialog

### Phase 4: Integration & Testing (30 min)

1. Test all CRUD operations
2. Test filters and search
3. Test view toggle
4. Verify exact match to ingredients patterns

---

## Success Criteria

### Functional Requirements

- [ ] Materials tab matches ingredients tab layout exactly
- [ ] Material Products tab exists and functions
- [ ] Search/filter works with cascading dropdowns
- [ ] Flat/Tree view toggle works
- [ ] All CRUD operations work
- [ ] Import dialog has Materials checkbox (separate fix)
- [ ] Selection state management matches ingredients
- [ ] Status bar updates correctly

### Visual Requirements

- [ ] Same grid configuration
- [ ] Same widget types
- [ ] Same spacing/padding
- [ ] Same button layout
- [ ] Same column headers
- [ ] Same fonts/colors
- [ ] Same form dialog structure

### Code Quality

- [ ] No code duplication (use shared components)
- [ ] Consistent naming (Material vs Ingredient)
- [ ] Services called correctly
- [ ] Error handling matches ingredients
- [ ] Comments explain deviations (if any)

---

## Files to Modify/Create

**Modify:**
- `src/ui/materials_tab.py` - Complete rebuild following ingredients_tab.py

**Create:**
- `src/ui/material_products_tab.py` - New tab (parallel to products_tab.py if exists)
- `src/ui/widgets/material_tree_widget.py` - If needed for tree view

**Reference (DO NOT MODIFY):**
- `src/ui/ingredients_tab.py` - THE PATTERN TO FOLLOW
- `src/ui/products_tab.py` - Secondary pattern reference

---

## Constitutional Compliance

✅ **Principle I: Data Integrity** - UI changes only, no data model changes
✅ **Principle II: Future-Proof Architecture** - Matches ingredient pattern for consistency
✅ **Principle III: Layered Architecture** - UI layer only, services unchanged
✅ **Principle IV: Separation of Concerns** - Clear UI/service separation maintained
✅ **Principle V: User-Centric Design** - Consistent UX with ingredients
✅ **Principle VI: Pragmatic Aspiration** - Fixes critical UX issue without over-engineering

---

## Risks & Mitigations

**Risk 1**: Current Materials tab has business logic to preserve
**Mitigation**: Extract service calls before rebuilding, re-integrate after

**Risk 2**: MaterialTreeWidget doesn't exist
**Mitigation**: Copy IngredientTreeWidget pattern or skip tree view initially

**Risk 3**: Breaking existing materials data
**Mitigation**: UI-only changes, data models unchanged, test thoroughly

**Risk 4**: Cascading dropdown logic complex
**Mitigation**: Copy exact implementation from ingredients_tab.py

---

## Notes for Spec-Kitty

**CRITICAL REMINDERS:**

1. **READ INGREDIENTS_TAB.PY FIRST** - Don't write code until you've studied it
2. **COPY, DON'T INVENT** - When in doubt, copy the ingredient pattern exactly
3. **MATERIALS NOT INGREDIENTS** - Remember to rename variables/services appropriately
4. **TEST EACH PHASE** - Don't move to next phase until current phase works
5. **ASK IF UNCLEAR** - If ingredient pattern unclear, ask before implementing

**This is not a greenfield project - it's matching an existing pattern.**

---

**END OF SPECIFICATION**
