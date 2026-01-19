# Bug Fix: F031 Incomplete Hierarchy UI Implementation

**Bug ID:** BUG_F031_HIERARCHY_UI  
**Created:** 2025-12-30  
**Priority:** HIGH  
**Status:** READY FOR IMPLEMENTATION  
**Related Feature:** F031 (Ingredient Hierarchy)

---

## Problem Statement

The F031 Ingredient Hierarchy feature is partially implemented:
- ✅ **Schema complete:** `parent_ingredient_id`, `hierarchy_level` fields exist
- ✅ **Import/Export complete:** Handles hierarchy data correctly
- ✅ **Product edit form:** Uses hierarchical ingredient selection
- ❌ **UI incomplete:** Multiple tabs/forms still use deprecated `category` field

**Impact:** Users cannot effectively manage or view the ingredient hierarchy, making the feature unusable despite backend support.

---

## Affected Components

### 1. Ingredients Tab (`ingredients_tab.py`)

**Current State:**
- Shows "Category" column in data grid
- Category dropdown filter

**Required State:**
- Show three hierarchy columns: "Root Category (L0)", "Subcategory (L1)", "Ingredient (L2)"
- Replace category filter with hierarchy navigation/filter

**Location:** `/Users/kentgale/Vaults-repos/bake-tracker/src/ui/ingredients_tab.py`

---

### 2. Ingredient Edit Form (`ingredient_form.py` or similar)

**Current State:**
- Shows "Category" dropdown (deprecated field)

**Required State:**
- Show three dropdowns for hierarchy selection:
  - "Root Category (L0)" - populated with L0 ingredients
  - "Subcategory (L1)" - populated with children of selected L0
  - "Ingredient (L2)" - populated with children of selected L1
- Cascading selection (L1 depends on L0, L2 depends on L1)
- Validation: Only L2 ingredients can be leaf ingredients (have products/used in recipes)

**Location:** Check for ingredient creation/edit dialog

---

### 3. Products Tab (`products_tab.py`)

**Current State:**
- Category dropdown filter (deprecated)

**Required State:**
- Hierarchical ingredient filter with three levels
- Show full ingredient path in product list (e.g., "Chocolate → Dark Chocolate → Semi-Sweet Chips")

**Location:** `/Users/kentgale/Vaults-repos/bake-tracker/src/ui/products_tab.py`

---

### 4. Inventory Tab (`inventory_tab.py`)

**Current State:**
- Category dropdown filter (deprecated)
- Displays "Category" column

**Required State:**
- Hierarchical ingredient filter
- Display full ingredient hierarchy path in grid
- Remove deprecated category column

**Location:** `/Users/kentgale/Vaults-repos/bake-tracker/src/ui/inventory_tab.py`

---

### 5. Inventory Edit Form (Add/Edit Inventory Dialog)

**Current State:**
- Shows greyed-out "Category" and "Ingredient" dropdowns (read-only display)

**Required State:**
- Show three greyed-out fields displaying hierarchy:
  - "Root Category (L0)" - read-only, shows L0 ancestor
  - "Subcategory (L1)" - read-only, shows L1 ancestor
  - "Ingredient (L2)" - read-only, shows selected ingredient
- Fields should be non-editable but informative

**Location:** Check for inventory add/edit dialog

---

## Detailed Requirements

### Requirement 1: Ingredients Tab - Grid Display

**Current:**
```
| Name                     | Category  | Products | Actions |
|--------------------------|-----------|----------|---------|
| Semi-Sweet Chocolate     | Chocolate | 3        | [Edit]  |
```

**Required:**
```
| Root (L0)  | Subcategory (L1) | Ingredient (L2)         | Products | Actions |
|------------|------------------|-------------------------|----------|---------|
| Chocolate  | Dark Chocolate   | Semi-Sweet Chocolate    | 3        | [Edit]  |
| Flour      | All-Purpose      | King Arthur AP Flour    | 2        | [Edit]  |
```

**Implementation Notes:**
- If ingredient is L0 or L1, show empty cells for child levels
- Use `get_ancestors()` from `ingredient_hierarchy_service.py` to populate columns
- Clicking column header should sort by that hierarchy level

---

### Requirement 2: Ingredients Tab - Filter/Search

**Current:**
- Category dropdown: `["All Categories", "Chocolate", "Flour", ...]`

**Required Option A - Cascading Dropdowns:**
```
Root (L0): [All ▼] [Chocolate] [Flour] [Sugar] ...
Subcategory (L1): [All ▼] [Dark Chocolate] [Milk Chocolate] ... (filtered by L0)
Ingredient (L2): [All ▼] [Semi-Sweet Chips] [Bittersweet Chips] ... (filtered by L1)
```

**Required Option B - Tree Filter (Simpler for Phase 2):**
```
Filter by Hierarchy Level: [All Levels ▼]
  - All Levels
  - Root Categories Only (L0)
  - Subcategories Only (L1)  
  - Leaf Ingredients Only (L2)

Search: [________________] (searches across all levels)
```

**Recommendation:** Start with **Option B** (simpler), upgrade to Option A in Phase 3.

---

### Requirement 3: Ingredient Edit Form - Hierarchy Selection

**UI Mockup:**
```
┌─ Edit Ingredient ──────────────────────────────────────┐
│                                                         │
│  Ingredient Name: [Semi-Sweet Chocolate Chips_______]  │
│                                                         │
│  Hierarchy Position:                                   │
│                                                         │
│  Root Category (L0):    [Chocolate ▼]                  │
│                         (All-Purpose, Baking, ...)     │
│                                                         │
│  Subcategory (L1):      [Dark Chocolate ▼]             │
│                         (Filtered by L0 selection)     │
│                                                         │
│  Ingredient Level (L2): ○ This is a leaf ingredient    │
│                         ○ This is a subcategory        │
│                                                         │
│  Recipe Unit: [oz ▼]                                   │
│  Density: [Enabled ☑]                                  │
│  ...                                                   │
│                                                         │
│  [Cancel]  [Save]                                      │
└─────────────────────────────────────────────────────────┘
```

**Logic:**
- L0 dropdown: Shows all `hierarchy_level = 0` ingredients
- L1 dropdown: Shows children of selected L0 (`parent_ingredient_id = L0.id`)
- L2 radio: Determines if this ingredient is leaf (L2) or mid-tier (L1)
- Validation: If "leaf ingredient" selected, must have L1 parent

**Edge Cases:**
- Creating new L0: Both dropdowns empty/disabled
- Creating new L1: L0 dropdown enabled, L1 empty/disabled
- Creating new L2: Both dropdowns enabled

---

### Requirement 4: Products Tab - Filter by Hierarchy

**Current:**
```
Category: [All Categories ▼]
```

**Required:**
```
Ingredient Hierarchy:
  Root (L0):       [All ▼]
  Subcategory (L1): [All ▼] (filtered by L0)
  Ingredient (L2):  [All ▼] (filtered by L1)
```

**Product List Display:**
```
| Product Name            | Ingredient Path                        | Brand      |
|-------------------------|----------------------------------------|------------|
| Nestle Toll House Chips | Chocolate → Dark → Semi-Sweet Chips    | Nestle     |
| KA AP Flour 25lb        | Flour → All-Purpose → KA AP Flour      | King Arthur|
```

---

### Requirement 5: Inventory Tab - Display & Filter

**Similar to Products Tab:**
- Replace category filter with hierarchy filters
- Display full ingredient path in grid
- Show hierarchy columns instead of flat category

---

### Requirement 6: Inventory Edit Form - Read-Only Hierarchy Display

**Current:**
```
Category:   [Chocolate ▼] (greyed out)
Ingredient: [Semi-Sweet Chocolate ▼] (greyed out)
```

**Required:**
```
Ingredient Hierarchy (Read-Only):
  Root (L0):       Chocolate
  Subcategory (L1): Dark Chocolate
  Ingredient (L2):  Semi-Sweet Chocolate Chips
```

**Implementation:** Use read-only labels/text fields showing hierarchy path from `get_ancestors()`

---

## Service Layer Support

### Available Services (Already Implemented)

From `ingredient_hierarchy_service.py`:

```python
def get_ancestors(ingredient_id: int) -> List[Ingredient]:
    """Get ancestry chain from root to ingredient."""
    
def get_children(ingredient_id: int) -> List[Ingredient]:
    """Get direct children of ingredient."""
    
def get_root_ingredients() -> List[Ingredient]:
    """Get all L0 ingredients."""
    
def get_hierarchy_path(ingredient_id: int) -> str:
    """Get formatted path like 'Chocolate → Dark Chocolate → Semi-Sweet Chips'"""
```

**Usage Example:**
```python
# For grid display
ancestors = get_ancestors(ingredient.id)
root_name = ancestors[0].display_name if len(ancestors) > 0 else ""
sub_name = ancestors[1].display_name if len(ancestors) > 1 else ""
leaf_name = ingredient.display_name

# For filter population
l0_ingredients = get_root_ingredients()
l1_ingredients = get_children(selected_l0_id) if selected_l0_id else []
```

---

## Testing Requirements

### Unit Tests
- ✅ Service layer tests already exist (per F031 spec)

### UI Tests (Manual - Critical)

**Test Case 1: Ingredients Tab - Grid Display**
- [ ] Open Ingredients tab
- [ ] Verify three hierarchy columns visible (L0, L1, L2)
- [ ] Verify deprecated "Category" column removed
- [ ] Verify hierarchy data displays correctly for all ingredients
- [ ] Verify sorting by each hierarchy level works

**Test Case 2: Ingredients Tab - Filter**
- [ ] Hierarchy level filter shows correct options
- [ ] Filtering by L0 shows only L0 ingredients
- [ ] Filtering by L2 shows only leaf ingredients
- [ ] Search works across all hierarchy levels

**Test Case 3: Ingredient Edit Form - Create L0**
- [ ] Create new root category (e.g., "Spices")
- [ ] Both L0 and L1 dropdowns disabled/empty
- [ ] Save succeeds, creates L0 ingredient

**Test Case 4: Ingredient Edit Form - Create L1**
- [ ] Create new subcategory under existing L0
- [ ] L0 dropdown shows all roots, can select parent
- [ ] L1 dropdown disabled (this IS the L1)
- [ ] Save succeeds, creates L1 with correct parent

**Test Case 5: Ingredient Edit Form - Create L2**
- [ ] Create new leaf ingredient
- [ ] L0 dropdown shows roots, select "Chocolate"
- [ ] L1 dropdown updates with children of Chocolate
- [ ] Select L1, mark as leaf ingredient
- [ ] Save succeeds, creates L2 with correct hierarchy

**Test Case 6: Ingredient Edit Form - Edit Existing**
- [ ] Edit existing L2 ingredient
- [ ] Dropdowns pre-populated with current hierarchy
- [ ] Can change parent (move to different subcategory)
- [ ] Save updates hierarchy correctly

**Test Case 7: Products Tab - Filter**
- [ ] Hierarchy filters work (L0 → L1 → L2 cascading)
- [ ] Product list shows full ingredient path
- [ ] Filtering by L0 shows all products under that hierarchy

**Test Case 8: Inventory Tab - Display**
- [ ] Hierarchy columns visible instead of category
- [ ] Inventory items show correct ingredient paths
- [ ] Filter by hierarchy works

**Test Case 9: Inventory Edit Form - Read-Only Display**
- [ ] Add Inventory dialog shows hierarchy (not category)
- [ ] All three levels displayed correctly
- [ ] Fields are read-only (not editable)

**Test Case 10: Validation - Leaf-Only Products**
- [ ] Attempt to assign product to L0 ingredient → should fail
- [ ] Attempt to assign product to L1 ingredient → should fail
- [ ] Assign product to L2 ingredient → should succeed

---

## Implementation Plan

### Phase 1: Ingredients Tab (High Priority)
1. Update grid to show L0/L1/L2 columns
2. Implement hierarchy filter (use simple level filter for Phase 2)
3. Test grid display and filtering

### Phase 2: Ingredient Edit Form (High Priority)
1. Replace category dropdown with L0/L1 selection + leaf flag
2. Implement cascading dropdown logic
3. Add validation (leaf ingredients must have parent)
4. Test create/edit workflows for L0/L1/L2

### Phase 3: Products Tab (Medium Priority)
1. Add hierarchy filter
2. Update product list to show ingredient path
3. Test filtering and display

### Phase 4: Inventory Tab (Medium Priority)
1. Update grid columns
2. Add hierarchy filter
3. Test display and filtering

### Phase 5: Inventory Edit Form (Low Priority)
1. Update to show hierarchy read-only fields
2. Test display in add/edit dialogs

### Phase 6: Comprehensive Testing
1. Run all manual test cases
2. Verify deprecated category field no longer used anywhere
3. User testing with Marianne (hierarchical browsing workflow)

---

## Acceptance Criteria

### Must Have (Phase 1-2)
- [ ] Ingredients tab shows L0/L1/L2 columns, not category
- [ ] Ingredient edit form uses hierarchy selection, not category dropdown
- [ ] Can create L0, L1, and L2 ingredients via edit form
- [ ] Hierarchy validation enforced (leaf ingredients have parents)
- [ ] No UI references to deprecated "category" field in Ingredients tab

### Should Have (Phase 3-4)
- [ ] Products tab filters by hierarchy, not category
- [ ] Inventory tab displays hierarchy, not category
- [ ] Product/inventory lists show full ingredient paths

### Nice to Have (Phase 5)
- [ ] Inventory edit form shows read-only hierarchy fields

### Overall Success
- [ ] All deprecated "category" UI elements removed
- [ ] Users can navigate ingredient hierarchy efficiently
- [ ] Hierarchy structure visible and understandable in all tabs
- [ ] No regressions in existing functionality

---

## Estimated Effort

- **Phase 1 (Ingredients Tab):** 4-6 hours
- **Phase 2 (Ingredient Edit Form):** 6-8 hours
- **Phase 3 (Products Tab):** 3-4 hours
- **Phase 4 (Inventory Tab):** 3-4 hours
- **Phase 5 (Inventory Edit Form):** 2-3 hours
- **Phase 6 (Testing):** 4-6 hours

**Total:** 22-31 hours (3-4 working days)

---

## Related Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/docs/func-spec/F031_ingredient_hierarchy.md` - Original feature spec
- `/Users/kentgale/Vaults-repos/bake-tracker/.kittify/memory/constitution.md` - Architectural principles

---

## Notes

**Key Insight:** This is not a "bug" in the traditional sense, but rather **incomplete feature implementation**. The backend is complete; the UI needs to catch up.

**Why This Matters:** Without hierarchy UI, users cannot leverage the three-tier taxonomy. The feature exists in the database but is invisible/unusable to users.

**Migration Note:** Some ingredients may still have `category` field populated from legacy data. This is fine - the field is deprecated but not removed. UI should ignore it and use hierarchy fields only.
