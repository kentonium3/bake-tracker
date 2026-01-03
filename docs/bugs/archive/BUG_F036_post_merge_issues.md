# Bug Report: Post-F036 Merge Issues

**Date Created:** 2026-01-02  
**Reporter:** Kent  
**Feature Context:** F036 (Ingredient Hierarchy Phase 4 - Testing)  
**Status:** NEW  
**Severity:** HIGH (Issue 2 & 3), MEDIUM (Issue 1)

---

## Summary

Three issues discovered during initial user testing after F036 merge and acceptance. Two are high-severity functionality gaps/errors, one is medium-severity UX issue.

---

## Issue 1: Ingredient Tab - Hierarchy Display Unreadable

**Severity:** MEDIUM (UX issue - not blocking but degrades user experience)  
**Component:** `ingredients_tab.py` - Hierarchy display columns  
**Priority:** P2 (fix after critical issues)

### Problem Description

The Ingredients tab displays the ingredient hierarchy as a single concatenated string column (e.g., "Baking > Flour > All-Purpose Flour"). This format is difficult to read because:
- Items don't align vertically
- Hierarchy levels are visually inconsistent
- Hard to scan for items at specific levels (e.g., "show me all L1 subcategories")

### Expected Behavior

Separate display columns for each hierarchy level, matching the pattern already implemented in Product and Inventory tabs:
- Column 1: L0 (Root Category) - e.g., "Baking"
- Column 2: L1 (Subcategory) - e.g., "Flour"
- Column 3: L2 (Ingredient) - e.g., "All-Purpose Flour"

**Note:** Do NOT duplicate L2 as a separate "Name" column. The three hierarchy columns replace the name column entirely.

### Current Behavior

Single column shows concatenated path:
```
Hierarchy Path
--------------
Baking > Flour > All-Purpose Flour
Baking > Flour > Bread Flour
Baking > Sugar > Granulated Sugar
Chocolate > Dark Chocolate > Semi-Sweet Chocolate Chips
```

### Desired Behavior

Three separate columns (like Product/Inventory tabs):
```
L0          | L1               | L2
------------|------------------|---------------------------
Baking      | Flour            | All-Purpose Flour
Baking      | Flour            | Bread Flour
Baking      | Sugar            | Granulated Sugar
Chocolate   | Dark Chocolate   | Semi-Sweet Chocolate Chips
```

### Screenshots/Evidence

*User testing observation - no screenshot available*

### Acceptance Criteria

- [ ] Ingredients tab shows three separate columns: L0, L1, L2
- [ ] Columns align vertically for easy scanning
- [ ] No duplicate "Name" column
- [ ] Sorting works on each individual column
- [ ] Filtering still works with new column structure
- [ ] Matches visual pattern from Product/Inventory tabs

### Files to Modify

- `src/ui/ingredients_tab.py` - Update column definitions and data binding
- Possibly `src/services/ingredient_hierarchy_service.py` if data retrieval needs adjustment

### Estimated Effort

2-3 hours (simple column restructure)

---

## Issue 2: Product Edit Form - Missing Cascading Hierarchy Selectors

**Severity:** HIGH (functionality gap - blocks intended UX)  
**Component:** Product edit form - Ingredient selection  
**Priority:** P1 (fix before Issue 1)

### Problem Description

The Product edit form's ingredient selection presents a single dropdown containing a flat list of all L2 ingredients. This was supposed to use cascading hierarchy selectors (L0 → L1 → L2) like other forms in the application.

This appears to be a gap from F034 (Phase 2 - Integration Fixes) that was either:
- Not implemented during F034
- Implemented but accidentally reverted
- Scoped out of F034 and missed in subsequent phases

### Expected Behavior

Ingredient selection should use cascading dropdowns:
1. **L0 Dropdown:** Select root category (e.g., "Baking", "Chocolate", "Dairy")
2. **L1 Dropdown:** Populates with subcategories based on L0 selection (e.g., "Flour", "Sugar")
3. **L2 Dropdown:** Populates with leaf ingredients based on L1 selection (e.g., "All-Purpose Flour", "Bread Flour")

This pattern should match:
- Recipe creation form (verified working in F034)
- Inventory add dialog (verified working)
- Product/Inventory tab filters (fixed in F034)

### Current Behavior

Single long dropdown showing all L2 ingredients in flat list:
```
[ Select Ingredient ▼ ]
  All-Purpose Flour
  Bread Flour
  Cake Flour
  Granulated Sugar
  Brown Sugar
  Semi-Sweet Chocolate Chips
  Milk Chocolate Chips
  ... (hundreds more)
```

### Screenshots/Evidence

*User testing observation - no screenshot available*

### Root Cause Analysis Needed

**Questions to investigate:**
1. Was cascading selector implementation included in F034 scope?
2. Check F034 commit history - was it implemented then removed?
3. Review F034 gap analysis document - was Product edit form listed as completed?
4. Check if product edit form uses different component than recipe form

**Hypothesis:** Product edit form may have been overlooked in F034's cascading selector fixes because it was already "working" (showing ingredients) even though it wasn't using the cascading pattern.

### Acceptance Criteria

- [ ] Product edit form shows three cascading dropdowns (L0, L1, L2)
- [ ] L1 dropdown updates when L0 selection changes
- [ ] L2 dropdown updates when L1 selection changes
- [ ] Only L2 ingredients are selectable (L0/L1 should not be assignable to products)
- [ ] Selected ingredient persists when editing existing product
- [ ] Cascading logic matches recipe creation form implementation
- [ ] Event handler guards prevent infinite loops
- [ ] Validation prevents selecting L0/L1 ingredients

### Files to Modify

- `src/ui/dialogs/product_edit_dialog.py` - Replace single dropdown with cascading component
- Possibly reuse cascading selector component from recipe/inventory forms
- `src/services/product_service.py` - Verify save logic handles cascading selection correctly

### Related Issues

- Possibly related to Issue 3 (save error) - incorrect ingredient data structure

### Estimated Effort

4-6 hours (implement cascading dropdowns, add event handlers, test thoroughly)

---

## Issue 3: Product Edit Form - Save Error on Ingredient Re-selection

**Severity:** HIGH (data corruption risk - prevents saving products)  
**Component:** Product edit form - Save operation  
**Priority:** P0 (fix immediately - blocks workflow)

### Problem Description

When editing an existing product and re-selecting the same ingredient that was already assigned, the save operation fails with error:

```
"Failed to save product: 'NoneType' is not subscriptable"
```

### Steps to Reproduce

1. Open existing product in edit form
   - Product already has an ingredient assigned (e.g., "All-Purpose Flour")
2. Make a change (e.g., add missing `product_name` field)
3. Click Save → **Succeeds** ✅
4. Re-open same product in edit form
5. Re-select the same ingredient from dropdown (even though it's already selected)
6. Click Save → **Fails** ❌ with error: `'NoneType' is not subscriptable`

### Expected Behavior

- Re-selecting the same ingredient should be a no-op (no change to save)
- Or: Should save successfully without error
- Save operation should handle "no change" case gracefully

### Current Behavior

Save fails with Python error indicating code is trying to subscript (access index of) a `None` value.

### Error Analysis

**Error:** `'NoneType' is not subscriptable`

**Likely Causes:**
1. **Ingredient value is None:** Dropdown returns `None` when ingredient hasn't actually changed
2. **Missing null check:** Code assumes ingredient is always tuple/list: `ingredient[0]` or `ingredient['id']`
3. **Event handler issue:** Change event fires with `None` value when selection is "refreshed" but not changed
4. **Data structure mismatch:** Code expects `(id, name)` tuple but gets `None` or scalar value

**Code locations to investigate:**
- `src/ui/dialogs/product_edit_dialog.py` - Save button handler, ingredient change event
- `src/services/product_service.py` - `update_product()` method
- Ingredient dropdown binding logic - what value does it return?

### Test Cases

#### Test Case 1: Edit product without changing ingredient
**Steps:**
1. Open product with ingredient already assigned
2. Change only `product_name` field
3. Click Save
**Expected:** Success
**Actual:** ✅ Success (works)

#### Test Case 2: Edit product and re-select same ingredient
**Steps:**
1. Open product with ingredient already assigned
2. Change `product_name` field
3. Re-select same ingredient from dropdown
4. Click Save
**Expected:** Success
**Actual:** ❌ Fails with `'NoneType' is not subscriptable`

#### Test Case 3: Edit product and select different ingredient
**Steps:**
1. Open product with "All-Purpose Flour" assigned
2. Change ingredient to "Bread Flour"
3. Click Save
**Expected:** Success
**Actual:** *Needs testing - unknown status*

### Acceptance Criteria

- [ ] Can save product without changing ingredient (already works)
- [ ] Can save product after re-selecting same ingredient (currently fails)
- [ ] Can save product after changing to different ingredient
- [ ] Error handling shows user-friendly message (not Python stack trace)
- [ ] Null checks prevent `'NoneType' is not subscriptable` errors
- [ ] Event handlers handle "no change" case gracefully

### Debug Checklist

1. [ ] Add logging to ingredient dropdown change event
2. [ ] Add logging to save button handler - what value does ingredient have?
3. [ ] Check if ingredient is `None`, empty tuple `()`, or scalar value
4. [ ] Add null checks before subscripting ingredient value
5. [ ] Test all three test cases above
6. [ ] Verify fix doesn't break "change ingredient" workflow

### Files to Modify

- `src/ui/dialogs/product_edit_dialog.py` - Add null checks in save handler
- `src/services/product_service.py` - Defensive coding for `update_product()`
- Possibly ingredient dropdown binding logic

### Estimated Effort

2-4 hours (debug, add null checks, test all scenarios)

---

## Combined Fix Strategy

### Fix Order (by priority)

1. **Issue 3 first (P0):** Blocking - users cannot save products reliably
2. **Issue 2 second (P1):** Functionality gap - needed for proper UX
3. **Issue 1 last (P2):** Polish - improves readability but not blocking

### Recommended Approach

**Option A: Single hotfix branch**
- Fix all three issues in one branch
- Test together to ensure no interactions
- Single PR for review
- Estimated total effort: 8-13 hours

**Option B: Separate fixes (recommended)**
- Fix Issue 3 immediately (emergency hotfix) - 2-4 hours
- Fix Issue 2 as feature branch (cascading selectors) - 4-6 hours
- Fix Issue 1 as separate UX improvement - 2-3 hours
- Allows faster deployment of critical fix (Issue 3)
- Reduces risk of introducing new bugs

### Testing After Fixes

Re-run relevant F036 test cases:
- [ ] Product CRUD operations (create, edit, save, delete)
- [ ] Ingredient assignment workflows
- [ ] Cascading selector behavior
- [ ] Ingredient tab display and filtering
- [ ] No regressions in recipe/inventory forms

---

## Notes

- All three issues discovered during initial user testing session with Kent
- F036 was marked complete and merged before these issues were found
- Issues suggest F034 (Phase 2) may not have fully addressed Product edit form
- May need to review F034 acceptance criteria and gap analysis document

---

## Related Documents

- `/docs/design/F033-F036_ingredient_hierarchy_gap_analysis.md` - Phase 2, 3, 4 specifications
- `/docs/requirements/req_ingredients.md` - Ingredient hierarchy requirements
- F034 implementation (check commit history)
- F036 test results (if documented)

---

## Status Updates

*Updates will be added here as issues are investigated and fixed*

**2026-01-03** - Issue 3 investigated: Root cause identified. `_is_updating_ui` guard in `_on_ingredient_change()` prevents `self.selected_ingredient` from being set during `_load_product()`. When user clicks Save without explicitly re-selecting ingredient, `self.selected_ingredient` is `None`, causing `None["id"]` error.

**2026-01-03** - Issue 3 fixed: Two changes to `src/ui/forms/add_product_dialog.py`:
1. In `_load_product()`: Set `self.selected_ingredient` directly after finding ingredient match (bypasses event handler guard)
2. In `_on_save()`: Added defensive null check with fallback to get ingredient from dropdown if `self.selected_ingredient` is None

**2026-01-03** - Issue 2 investigated: Recipe form uses flat dropdown + browse button pattern (not cascading dropdowns). The browse button opens `IngredientSelectionDialog` with tree widget for hierarchical navigation. This is a better UX than cascading dropdowns.

**2026-01-03** - Issue 2 fixed: Added browse button to product edit form (`src/ui/forms/add_product_dialog.py`):
1. Added "..." browse button next to ingredient dropdown
2. Browse button opens `IngredientSelectionDialog` (reused from recipe_form.py)
3. Tree widget allows hierarchical browsing with L0→L1→L2 navigation
4. Selected ingredient updates dropdown and hierarchy display
5. Matches recipe form pattern exactly

**2026-01-03** - Issue 1 fixed: Updated Ingredients tab to show separate L0/L1/Name columns (`src/ui/ingredients_tab.py`):
1. Changed columns from `("hierarchy_path", "name", "density")` to `("l0", "l1", "name", "density")`
2. Column headers: "Category (L0)", "Subcategory (L1)", "Name", "Density"
3. Updated `_build_hierarchy_path_cache()` to return `{"l0": str, "l1": str}` dict instead of concatenated string
4. Updated `_update_ingredient_display()` to use separate L0/L1 values
5. Updated `_apply_filters()` sorting to handle new l0/l1 column names
6. Now sortable by L0 or L1 column independently

**2026-01-03** - All fixes tested and merged

---

**END OF BUG REPORT**
